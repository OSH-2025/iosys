import asyncio
import datetime
import logging
import os  # For accessing environment variables (safer for API keys)
import threading
import warnings  # To suppress potential deprecation warnings
import json  # For parsing LLM responses
import re  # For basic text cleaning (regular expressions)
from openai import AsyncOpenAI
from typing import Optional, TypedDict, Union

from fs import CHANGE_TYPE, FileSystemNode, IOSYSFileSystem
from parser import IOSYSParser
from utils.logger import IOSYSLogger


warnings.filterwarnings("ignore", message="pkg_resources is deprecated as an API.*")
import jieba  # noqa: E402

jieba.setLogLevel(logging.ERROR)

logger = IOSYSLogger("KG")

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


class IOSYSKnowledgeGraph:
    tasks: dict[str, Union["IOSYSKnowledgeGraphTask", bool]]

    def __init__(
        self,
        fs: IOSYSFileSystem,
        parser: IOSYSParser,
        llm: AsyncOpenAI,
        chunk_size: int = 300,
        overlap: int = 30,
        system_prompt: str = extraction_system_prompt,
        user_prompt_template: str = extraction_user_prompt_template,
    ):
        self.llm = llm
        self.parser = parser
        self.llm_api_key = os.environ["LLM_API_KEY"]
        self.llm_model = os.environ["KG_LLM_MODEL_NAME"]
        self.llm_api_base = os.environ["LLM_BASE_URL"]
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.system_prompt = system_prompt
        self.user_prompt_template = user_prompt_template
        self.tasks = {}

        fs.on_change.append(self.on_fs_change)

    async def on_fs_change(self, node: FileSystemNode, type: CHANGE_TYPE):
        if type == "metadata":
            return

        n = node  # type: FileSystemNode | None
        while n is not None:
            task = self.tasks.pop(n.path, None)
            if isinstance(task, IOSYSKnowledgeGraphTask):
                if task.result is not None:
                    node.update_meta(knowledge_graph=None)
            n = n.parent()

    def spawn_task(self, node: FileSystemNode):
        logger.info(f"Spawning knowledge graph task for {node.path}")

        tasks = []  # type: list[IOSYSKnowledgeGraphTask]
        dir_nodes = []  # type: list[FileSystemNode]

        def create_tasks(n: FileSystemNode):
            for child in n.children():
                create_tasks(child)
            if n.get_meta("type") == "directory":
                self.tasks[n.path] = False  # Mark directory as in progress
                dir_nodes.append(n)
            else:
                task = IOSYSKnowledgeGraphTask(n, self)
                self.tasks[n.path] = task
                tasks.append(task)

        create_tasks(node)

        loop = asyncio.new_event_loop()

        def run_async_tasks_in_thread():
            async def main_async_coroutine():
                await asyncio.gather(*[task.generate() for task in tasks])
                loop.stop()

                for dir_node in dir_nodes:
                    self.tasks[dir_node.path] = True  # Mark directories as done

                logger.info(f"Knowledge graph tasks completed for {node.path}")

            asyncio.run_coroutine_threadsafe(main_async_coroutine(), loop)
            loop.run_forever()

        async_thread = threading.Thread(target=run_async_tasks_in_thread, daemon=True)
        async_thread.start()

    def get_result(self, node: FileSystemNode):
        result = []  # type: list[KnowledgeGraphTriplet]

        def extend_result(n: FileSystemNode):
            if n.get_meta("type") != "directory":
                task = self.tasks.get(n.path)
                assert task is not None, f"Task for {n.path} not found."
                if isinstance(task, bool):
                    assert task, f"Task for {n.path} is not done."
                else:
                    assert task.result is not None, (
                        f"Task for {n.path} is not finished."
                    )
                    result.extend(task.result)

            for child in n.children():
                extend_result(child)

        extend_result(node)

        return result

    def status_dict(self):
        status = {}
        for path, task in self.tasks.items():
            if task is True:
                status[path] = {
                    "status": "done",
                    "done_at": datetime.datetime.now().timestamp(),
                }
            elif task is False:
                status[path] = {"status": "in_progress"}
            else:
                status[path] = task.status_dict()
        return status


class KnowledgeGraphTriplet(TypedDict):
    subject: str
    predicate: str
    object: str


class IOSYSKnowledgeGraphTask:
    done_at: int
    result: Optional[list[KnowledgeGraphTriplet]]

    def __init__(self, node: FileSystemNode, config: IOSYSKnowledgeGraph):
        self.config = config
        self.node = node
        self.parser = config.parser
        self.llm_client = config.llm
        self.llm_model_name = config.llm_model
        self.llm_temperature = 0.0  # Default temperature for LLM responses
        self.llm_max_tokens = 4096
        self.unstructured_text = ""
        self.chunk_size = config.chunk_size
        self.overlap = config.overlap
        self.system_prompt = config.system_prompt
        self.user_prompt_template = config.user_prompt_template

        self.result = None
        self.error = ""
        self.progress = 0
        self.done_at = 0

        cache = node.get_meta("knowledge_graph")
        if cache:
            cache = json.loads(str(cache))
            self.done_at = cache.get("done_at", 0)
            if self.done_at:
                self.result = cache.get("result", None)
                if self.result is not None:
                    logger.info(f"Knowledge graph cache found for {node.path}.")

    async def chunk_to_raw_kg_json(self, text: str):
        user_prompt = self.user_prompt_template.format(text_chunk=text)
        llm_output = None

        response = await self.llm_client.chat.completions.create(
            model=self.llm_model_name,
            messages=[
                {"role": "system", "content": self.system_prompt},
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
                        self.error += "JSON object received, but doesn't contain a single list of triples.\n"
                        raise ValueError(self.error)
                elif isinstance(parsed_data, list):
                    parsed_json = parsed_data
                else:
                    self.error += (
                        "Parsed JSON is not a list or expected dictionary wrapper.\n"
                    )
                    raise ValueError(self.error)

            except json.JSONDecodeError as json_err:
                parsing_error = f"JSONDecodeError: {json_err}. Trying regex fallback..."
                logger.warning(f"   {parsing_error}")
                # Strategy 2: Regex fallback for arrays potentially wrapped in text/markdown
                match = re.search(r"^\s*(\[.*?\])\s*$", llm_output, re.DOTALL)
                if match:
                    json_string_extracted = match.group(1)
                    try:
                        parsed_json = json.loads(json_string_extracted)
                        parsing_error = None  # Clear previous error
                    except json.JSONDecodeError as nested_err:
                        parsing_error = f"JSONDecodeError after regex: {nested_err}"
                        self.error += f"      ERROR: Regex content is not valid JSON: {nested_err}\n"
                        logger.error(self.error)
                else:
                    parsing_error = "JSONDecodeError and Regex fallback failed."
                    self.error += (
                        "      ERROR: Regex could not find JSON array structure.\n"
                    )
                    logger.error(self.error)

            except ValueError as val_err:
                parsing_error = (
                    f"ValueError: {val_err}"  # Catches issues with unexpected structure
                )
                self.error += f"      ERROR: {parsing_error}\n"
                logger.error(self.error)
        return {"content": parsed_json, "error": parsing_error, "response": llm_output}

    async def generate(self):
        if self.result is not None and not self.error:
            return

        node = self.node
        logger.info(f"File {node.path} Starting knowledge graph extraction...")

        content = await self.parser.get_verbose_text(node)
        words = list(jieba.cut(content))
        total_words = len(words)
        total_chunks = (total_words // (self.chunk_size - self.overlap)) + 1
        total_words = 0
        chunk_num = 0
        all_extracted_triples = []
        normalized_triples = []  # type: list[KnowledgeGraphTriplet]
        seen_triples = set()  # Tracks (subject, predicate, object) tuples

        for _ in range(len(words)):
            chunk_num += 1
            end_index = min(self.chunk_size, len(words))
            chunk_text = " ".join(words[0:end_index])
            cut_index = max(end_index - self.overlap, 0)
            words = words[cut_index:]

            self.progress = int((chunk_num / total_chunks) * 100)
            try:
                raw_kg = await self.chunk_to_raw_kg_json(chunk_text)
                parsed_json = raw_kg.get("content", None)
            except Exception as e:
                self.error += str(e)
                return

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
                self.error += (
                    "   ERROR: Parsed data is not a list, cannot extract triples.\n"
                )
                return
            if valid_triples_in_chunk:
                all_extracted_triples.extend(valid_triples_in_chunk)

            # Normalize, Filter, and De-duplicate Triples
            for triple in all_extracted_triples:
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
            if len(words) <= self.overlap:
                break

        self.result = normalized_triples
        self.done_at = int(datetime.datetime.now().timestamp())

        if not self.error and self.result:
            self.node.update_meta(
                knowledge_graph=json.dumps(
                    {
                        "revision": 0,  # TODO:
                        "result": self.result,
                        "done_at": self.done_at,
                    },
                )
            )

    def __str__(self) -> str:
        return str(self.status_dict())

    def status_dict(self):
        if self.error:
            return {
                "status": "error",
                "message": self.error,
            }
        elif self.result is not None:
            return {
                "status": "done",
                "done_at": self.done_at,
            }
        else:
            return {
                "status": "in_progress",
                "progress": self.progress,
            }
