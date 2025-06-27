import pandas as pd  # For displaying data in tables
import os  # For accessing environment variables (safer for API keys)
import warnings  # To suppress potential deprecation warnings
import json  # For parsing LLM responses
import re  # For basic text cleaning (regular expressions)
import jieba
import logging
from openai import AsyncOpenAI
from typing import Dict, Any, Callable, List

from fs import IOSYSFileSystem, FileSystemNode
from utils.logger import IOSYSLogger

# Configure settings for better display and fewer warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
pd.set_option("display.max_rows", 100)  # Show more rows in pandas tables
pd.set_option("display.max_colwidth", 150)  # Show more text width in pandas tables
logger = IOSYSLogger("KG")
# jieba.setLogLevel(logging.INFO)

# --- System Prompt: Sets the context/role for the LLM ---
extraction_system_prompt = """
你是一位处理知识图谱提取的 AI 专家。我将用英文给出 Prompt，但你需要对处理文本中的语言保持原样，即不必翻译为英文后输出。
You are an AI expert specialized in knowledge graph extraction. 
Your task is to identify and extract factual Subject-Predicate-Object (SPO) triples from the given text.
Focus on accuracy and adhere strictly to the JSON output format requested in the user prompt.
Extract core entities and the most direct relationship.
"""

# --- User Prompt Template: Contains specific instructions and the text ---
extraction_user_prompt_template = """
Please extract Subject-Predicate-Object (S-P-O) triples from the text below. 对于文本中的名词、关系，如果原文使用中文表述，你生成的内容也应该为中文；即：不必将内容翻译为英文再输出。

如果节点和关系中出现用 $$ 括起来的公式，你需要将公式表达为不含 $$ 的文本形式，不使用 latex 语法，不必严谨表述，只要能大致看出公式形式即可。

我希望你提取的 Subject 和 Object 是具体的实体名称，而不是泛指的名词或代词，且应尽可能简单，在非必要时不带有多余的形容词。Predicate 应该是一个简短的动词或动词短语，描述实体之间的关系。

**重要**：当实体名称中出现“和”、“或”等连接词或顿号“、”时，你要将其视为并列关系进行处理，即当作两个对象，建立两个 tripet。

对于意义相近的词，可以用同一个词来表示，以提高知识的结构性。

**VERY IMPORTANT RULES:**
1.  **Output Format:** Respond ONLY with a single, valid JSON array. Each element MUST be an object with keys "subject", "predicate", "object".
2.  **JSON Only:** Do NOT include any text before or after the JSON array (e.g., no 'Here is the JSON:' or explanations). Do NOT use markdown ```json ... ``` tags.
3.  **Concise Predicates:** Keep the 'predicate' value concise (1-3 words, ideally 1-2). Use verbs or short verb phrases (e.g., 'discovered', 'was born in', 'won').
4.  **Lowercase:** ALL values for 'subject', 'predicate', and 'object' MUST be lowercase.
5.  **Pronoun Resolution:** Replace pronouns (she, he, it, her, etc.) with the specific lowercase entity name they refer to based on the text context (e.g., 'marie curie').
6.  **Specificity:** Capture specific details (e.g., 'nobel prize in physics' instead of just 'nobel prize' if specified).
7.  **Completeness:** Extract all distinct factual relationships mentioned.

**Text to Process:**
```text
{text_chunk}
```

**Required JSON Output Format Example:**
[
  {{ "subject": "marie curie", "predicate": "discovered", "object": "radium" }},
  {{ "subject": "marie curie", "predicate": "won", "object": "nobel prize in physics" }}
]

**Your JSON Output (MUST start with '[' and end with ']'):**
"""


class IOSYSKnowledgeGraphConfig:
    llm: AsyncOpenAI
    fs: IOSYSFileSystem

    def __init__(
        self,
        llm: AsyncOpenAI,
        chunk_size: int = 300,
        overlap: int = 30,
        log_level: str = "INFO",
        system_prompt: str = extraction_system_prompt,
        user_prompt_template: str = extraction_user_prompt_template,
    ):
        self.llm = llm
        self.llm_api_key = os.environ["LLM_API_KEY"]
        self.llm_model = os.environ["KG_LLM_MODEL_NAME"]
        self.llm_api_base = os.environ["LLM_BASE_URL"]
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.system_prompt = system_prompt
        self.user_prompt_template = user_prompt_template

        # 设置日志级别
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"Invalid log level: {log_level}")
        logging.basicConfig(
            level=numeric_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )


class IOSYSKnowledgeGraph:
    def __init__(
        self, node: FileSystemNode, config: IOSYSKnowledgeGraphConfig, autoload=True
    ):
        self.config = config
        self.node = node
        self.llm_client = config.llm
        self.llm_model_name = config.llm_model
        self.llm_api_base = config.llm_api_base
        self.llm_api_key = config.llm_api_key
        self.llm_temperature = 0.0  # Default temperature for LLM responses
        self.llm_max_tokens = 4096
        self.tool_configs = self._collect_tool_configs()
        self.tool_handlers = self._collect_tool_handlers()
        self.unstructured_text = ""
        self.chunk_size = config.chunk_size
        self.overlap = config.overlap
        self.system_prompt = config.system_prompt
        self.user_prompt_template = config.user_prompt_template
        self.content = False
        self.done = False
        self.error = False
        self.error_message = ""
        if autoload:
            self.load()

    def _collect_tool_configs(self) -> List[Dict[str, Any]]:
        """自动收集所有注册的工具配置"""
        tools = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, "_tool_config"):
                tools.append(attr._tool_config)
        return tools

    def _collect_tool_handlers(self) -> Dict[str, Callable]:
        """自动收集所有工具处理函数"""
        handlers = {}
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, "_tool_name"):
                handlers[attr._tool_name] = attr
        return handlers

    def load(self):
        kg_data = self.node.get_meta("knowledge_graph", "{}")
        kg_dict = json.loads(str(kg_data))
        self.content = kg_dict.get("content", [])
        status = kg_dict.get("status", "not_generated")
        self.done = status == "done"
        self.error = status != "done"
        self.error_message = kg_dict.get("error_message", f"{self.node.path}:\n")
        if status == "not_generated":
            self.error_message = (
                f"{self.node.path}:\nNo knowledge graph content available."
            )

    async def chunk_to_raw_kg_json(self, text: str):
        user_prompt = extraction_user_prompt_template.format(text_chunk=text)
        llm_output = None

        response = await self.llm_client.chat.completions.create(
            model=self.llm_model_name,
            messages=[
                {"role": "system", "content": extraction_system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.llm_temperature,
            max_tokens=self.llm_max_tokens,
            # Request JSON output format - helps models that support it
            response_format={"type": "json_object"},
        )

        llm_output = str(response.choices[0].message.content).strip()

        # Parse JSON (if API call succeeded)
        parsed_json = None
        parsing_error = None
        if llm_output is not None:
            try:
                # Strategy 1: Direct parsing (ideal)
                parsed_data = json.loads(llm_output)

                # Handle if response_format={'type':'json_object'} returns a dict containing the list
                if isinstance(parsed_data, dict):
                    list_values = [
                        v for v in parsed_data.values() if isinstance(v, list)
                    ]
                    if len(list_values) == 1:
                        parsed_json = list_values[0]
                    else:
                        logger.error(f"LLM raw output: {llm_output}")
                        self.error_message += "JSON object received, but doesn't contain a single list of triples.\n"
                        raise ValueError(self.error_message)
                elif isinstance(parsed_data, list):
                    parsed_json = parsed_data
                else:
                    self.error_message += (
                        "Parsed JSON is not a list or expected dictionary wrapper.\n"
                    )
                    raise ValueError(self.error_message)

            except json.JSONDecodeError as json_err:
                parsing_error = f"JSONDecodeError: {json_err}. Trying regex fallback..."
                logger.warning(f"   {parsing_error}")
                # Strategy 2: Regex fallback for arrays potentially wrapped in text/markdown
                match = re.search(r"^\s*(\[.*?\])\s*$", llm_output, re.DOTALL)
                if match:
                    json_string_extracted = match.group(1)
                    logger.info("      Regex found potential JSON array structure.")
                    try:
                        parsed_json = json.loads(json_string_extracted)
                        logger.info(
                            "      Successfully parsed JSON from regex extraction."
                        )
                        parsing_error = None  # Clear previous error
                    except json.JSONDecodeError as nested_err:
                        parsing_error = f"JSONDecodeError after regex: {nested_err}"
                        self.error_message += f"      ERROR: Regex content is not valid JSON: {nested_err}\n"
                        logger.error(self.error_message)
                else:
                    parsing_error = "JSONDecodeError and Regex fallback failed."
                    self.error_message += (
                        "      ERROR: Regex could not find JSON array structure.\n"
                    )
                    logger.error(self.error_message)

            except ValueError as val_err:
                parsing_error = (
                    f"ValueError: {val_err}"  # Catches issues with unexpected structure
                )
                self.error_message += f"      ERROR: {parsing_error}\n"
                logger.error(self.error_message)
        return {"content": parsed_json, "error": parsing_error, "response": llm_output}

    def clear(self, update_meta: bool = True):
        """Clear the knowledge graph content and reset status."""
        self.done = False
        self.error = True
        self.error_message = f"{self.node.path}:\nNo knowledge graph content available."
        self.content = []
        if update_meta:
            self.node.update_meta(knowledge_graph=json.dumps(self.to_dict()))

    async def update(self):
        self.clear(False)
        self.error_message = f"{self.node.path}:\n"

        node = self.node
        logger.info(f"File {node.path} Starting knowledge graph extraction...")

        name = node.name
        content = ""
        # TODO: Read as text (Markitdown part)
        if name.endswith(".txt") and not name.endswith(".md"):
            content_bytes = node.read()
            content = content_bytes.decode("utf-8", errors="ignore")
        rawtext = f"**File: {node.path}**\n{content}\n\n"
        words = list(jieba.cut(rawtext))
        total_words = len(words)
        total_chunks = (total_words // (self.chunk_size - self.overlap)) + 1
        total_words = 0
        chunk_num = 0
        all_extracted_triples = []
        normalized_triples = []
        seen_triples = set()  # Tracks (subject, predicate, object) tuples

        for j in range(len(words)):
            chunk_num += 1
            end_index = min(self.chunk_size, len(words))
            chunk_text = " ".join(words[0:end_index])
            cut_index = max(end_index - self.overlap, 0)
            words = words[cut_index:]

            logger.info(
                f"File {node.path} is processing Chunk {chunk_num}/{total_chunks}"
            )
            try:
                raw_kg = await self.chunk_to_raw_kg_json(chunk_text)
                parsed_json = raw_kg.get("content", None)
            except Exception as e:
                error_message = str(e)
                logger.error(f"   ERROR during API call: {error_message}")

            if parsed_json is None:
                logger.error(f"--- JSON Parsing FAILED (Chunk {chunk_num}) --- ")
                logger.error(
                    f"   Final Parsing Error: {raw_kg.get('error', 'Unknown error')}"
                )
                logger.error("-" * 20)
            else:
                valid_triples_in_chunk = []
                if isinstance(parsed_json, list):
                    for item in parsed_json:
                        if isinstance(item, dict) and all(
                            k in item for k in ["subject", "predicate", "object"]
                        ):
                            if all(
                                isinstance(item[k], str)
                                for k in ["subject", "predicate", "object"]
                            ):
                                item["chunk"] = chunk_num  # Add source chunk info
                                valid_triples_in_chunk.append(item)
                else:
                    self.error_message += (
                        "   ERROR: Parsed data is not a list, cannot extract triples.\n"
                    )
                    logger.error(self.error_message)
                if valid_triples_in_chunk:
                    all_extracted_triples.extend(valid_triples_in_chunk)

            # Normalize, Filter, and De-duplicate Triples
            for i, triple in enumerate(all_extracted_triples):
                subject_raw = triple.get("subject")
                predicate_raw = triple.get("predicate")
                object_raw = triple.get("object")

                normalized_sub, normalized_pred, normalized_obj = None, None, None

                if not (
                    isinstance(subject_raw, str)
                    and isinstance(predicate_raw, str)
                    and isinstance(object_raw, str)
                ):
                    continue

                # 1. Normalize
                normalized_sub = subject_raw.strip().lower()
                normalized_pred = re.sub(
                    r"\s+", " ", predicate_raw.strip().lower()
                ).strip()
                normalized_obj = object_raw.strip().lower()

                # 2. Filter Empty
                if not (normalized_sub and normalized_pred and normalized_obj):
                    continue
                triple_identifier = (
                    normalized_sub,
                    normalized_pred,
                    normalized_obj,
                )

                # 3. De-duplicate
                if triple_identifier not in seen_triples:
                    normalized_triples.append(
                        {
                            "subject": normalized_sub,
                            "predicate": normalized_pred,
                            "object": normalized_obj,
                        }
                    )
                    seen_triples.add(triple_identifier)
            self.content = normalized_triples
            if len(words) <= self.overlap:
                break

        self.done = True
        self.error = False

        self.node.update_meta(knowledge_graph=json.dumps(self.to_dict()))

    def __str__(self) -> str:
        return str(self.to_dict())

    def status_string(self):
        if self.error:
            return {
                "status": "error",
                "message": self.error_message,
            }
        if self.done:
            return {
                "status": "done",
                "path": self.node.path,
                "content": self.content,
            }
        else:
            return {
                "status": "in_progress",
                "path": self.node.path,
            }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status_string(),
            "error_message": self.error_message,
            "content": self.content,
        }

    def status(self):
        return {"status": self.status_string(), "error_message": self.error_message}
