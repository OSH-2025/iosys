import pandas as pd  # For displaying data in tables
import os  # For accessing environment variables (safer for API keys)
import warnings  # To suppress potential deprecation warnings
import json  # For parsing LLM responses
import networkx as nx  # For creating and managing the graph data structure
import pandas as pd  # For displaying data in tables
import re  # For basic text cleaning (regular expressions)
import warnings  # To suppress potential deprecation warnings

import logging
from openai import OpenAI
from typing import Dict, Any, Callable, List

from jfs import IOSYSFileSystem, FileSystemNode
from rag import IOSYSRAG

# Configure settings for better display and fewer warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
pd.set_option("display.max_rows", 100)  # Show more rows in pandas tables
pd.set_option("display.max_colwidth", 150)  # Show more text width in pandas tables

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

    llm: OpenAI
    fs: IOSYSFileSystem
    rag: IOSYSRAG

    def __init__(
        self,
        llm: OpenAI,
        fs: IOSYSFileSystem,
        rag: IOSYSRAG,
        chunk_size: int = 300,
        overlap: int = 30,
        log_level: str = "INFO",
    ):
        self.llm = llm
        self.fs = fs
        self.rag = rag
        self.llm_api_key = os.environ["LLM_API_KEY"]
        self.llm_model = os.environ["LLM_MODEL_NAME"]
        self.llm_api_base = os.environ["LLM_BASE_URL"]
        self.chunk_size = chunk_size
        self.overlap = overlap

        # 设置日志级别
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"Invalid log level: {log_level}")
        logging.basicConfig(
            level=numeric_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )


class IOSYSKnowledegeGraph:
    def __init__(self, config: IOSYSKnowledgeGraphConfig):
        self.config = config
        self.fs = config.fs
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
        self.knowledge_graph = None # TODO

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

    def get_unstructured_text(self, node: FileSystemNode) -> str:
        text = ""
        name = node.name
        # TODO: Check if the file is a text file
        pure_text = name.endswith(".txt") or name.endswith(".md")
        if pure_text:
            content = node.read()
            text += f"--- File: {name} ---\n{content}\n\n"
        for child in node.children():
            text += self.get_unstructured_text(child)
        return text

    def update_unstructured_text(self, new_text: str):
        """read all text files in the directory and merge them together"""
        self.unstructured_text = self.get_unstructured_text(self.fs.get_root())

    def generate_knowledge_graph(self):
        words = self.unstructured_text.split()
        total_words = len(words)
        chunks = []
        start_index = 0
        chunk_number = 1

        print("Starting chunking process...")

        while start_index < total_words:
            end_index = min(start_index + self.chunk_size, total_words)
            chunk_text = " ".join(words[start_index:end_index])
            chunks.append({"text": chunk_text, "chunk_number": chunk_number})

            next_start_index = start_index + self.chunk_size - self.overlap

            if next_start_index <= start_index:
                if end_index == total_words:
                    break  # Already processed the last part
                next_start_index = start_index + 1

            start_index = next_start_index
            chunk_number += 1

            # Safety break (optional)
            if chunk_number > total_words:  # Simple safety
                print("Warning: Chunking loop exceeded total word count, breaking.")
                break

        all_extracted_triples = []
        failed_chunks = []

        for chunk_index in range(len(chunks)):
            chunk_info = chunks[chunk_index]
            chunk_text = chunk_info["text"]
            chunk_num = chunk_info["chunk_number"]

            print(f"\n--- Processing Chunk {chunk_num}/{len(chunks)} --- ")

            # Format the User Prompt
            user_prompt = extraction_user_prompt_template.format(text_chunk=chunk_text)

            llm_output = None
            error_message = None

            try:
                response = self.llm_client.chat.completions.create(
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

            except Exception as e:
                error_message = str(e)
                print(f"   ERROR during API call: {error_message}")
                failed_chunks.append(
                    {
                        "chunk_number": chunk_num,
                        "error": f"API/Processing Error: {error_message}",
                        "response": "",
                    }
                )

            # Parse JSON (if API call succeeded)
            parsed_json = None
            parsing_error = None
            if llm_output is not None:
                print("Attempting to parse JSON from response...")
                try:
                    # Strategy 1: Direct parsing (ideal)
                    parsed_data = json.loads(llm_output)

                    # Handle if response_format={'type':'json_object'} returns a dict containing the list
                    if isinstance(parsed_data, dict):
                        print("   Detected dictionary response, attempting to extract list...")
                        list_values = [v for v in parsed_data.values() if isinstance(v, list)]
                        if len(list_values) == 1:
                            parsed_json = list_values[0]
                            print("      Successfully extracted list from dictionary.")
                        else:
                            raise ValueError(
                                "JSON object received, but doesn't contain a single list of triples."
                            )
                    elif isinstance(parsed_data, list):
                        parsed_json = parsed_data
                        print("   Successfully parsed JSON list directly.")
                    else:
                        raise ValueError(
                            "Parsed JSON is not a list or expected dictionary wrapper."
                        )

                except json.JSONDecodeError as json_err:
                    parsing_error = f"JSONDecodeError: {json_err}. Trying regex fallback..."
                    print(f"   {parsing_error}")
                    # Strategy 2: Regex fallback for arrays potentially wrapped in text/markdown
                    match = re.search(r"^\s*(\[.*?\])\s*$", llm_output, re.DOTALL)
                    if match:
                        json_string_extracted = match.group(1)
                        print("      Regex found potential JSON array structure.")
                        try:
                            parsed_json = json.loads(json_string_extracted)
                            print("      Successfully parsed JSON from regex extraction.")
                            parsing_error = None  # Clear previous error
                        except json.JSONDecodeError as nested_err:
                            parsing_error = f"JSONDecodeError after regex: {nested_err}"
                            print(f"      ERROR: Regex content is not valid JSON: {nested_err}")
                    else:
                        parsing_error = "JSONDecodeError and Regex fallback failed."
                        print("      ERROR: Regex could not find JSON array structure.")

                except ValueError as val_err:
                    parsing_error = (
                        f"ValueError: {val_err}"  # Catches issues with unexpected structure
                    )
                    print(f"   ERROR: {parsing_error}")

                # --- Show Parsed Result (or error) ---
                if parsed_json is not None:
                    print("--- Parsed JSON Data (Chunk {chunk_num}) ---")
                    print(json.dumps(parsed_json, indent=2))  # Pretty print the JSON
                    print("-" * 20)
                else:
                    print(f"--- JSON Parsing FAILED (Chunk {chunk_num}) --- ")
                    print(f"   Final Parsing Error: {parsing_error}")
                    print("-" * 20)
                    failed_chunks.append(
                        {
                            "chunk_number": chunk_num,
                            "error": f"Parsing Failed: {parsing_error}",
                            "response": llm_output,
                        }
                    )

            # Validate and Store Triples (if parsing succeeded)
            if parsed_json is not None:
                print("Validating structure and extracting triples...")
                valid_triples_in_chunk = []
                invalid_entries = []
                if isinstance(parsed_json, list):
                    for item in parsed_json:
                        if isinstance(item, dict) and all(
                            k in item for k in ["subject", "predicate", "object"]
                        ):
                            # Basic check: ensure values are strings (can be refined)
                            if all(
                                isinstance(item[k], str)
                                for k in ["subject", "predicate", "object"]
                            ):
                                item["chunk"] = chunk_num  # Add source chunk info
                                valid_triples_in_chunk.append(item)
                            else:
                                invalid_entries.append(
                                    {"item": item, "reason": "Non-string value"}
                                )
                        else:
                            invalid_entries.append(
                                {"item": item, "reason": "Incorrect structure/keys"}
                            )
                else:
                    print("   ERROR: Parsed data is not a list, cannot extract triples.")
                    invalid_entries.append({"item": parsed_json, "reason": "Not a list"})
                    # Also add to failed chunks if the overall structure was wrong
                    if not any(fc["chunk_number"] == chunk_num for fc in failed_chunks):
                        failed_chunks.append(
                            {
                                "chunk_number": chunk_num,
                                "error": "Parsed data not a list",
                                "response": llm_output,
                            }
                        )

            # --- Update Running Total (Visual Feedback) ---
            print(f"--- Running Total Triples Extracted: {len(all_extracted_triples)} --- ")
            print(f"--- Failed Chunks So Far: {len(failed_chunks)} --- ")

        print("\nFinished processing this chunk.")


        # Initialize lists and tracking variables
        normalized_triples = []
        seen_triples = set()  # Tracks (subject, predicate, object) tuples
        original_count = len(all_extracted_triples)
        empty_removed_count = 0
        duplicates_removed_count = 0

        processed_count = 0

        for i, triple in enumerate(all_extracted_triples):
            subject_raw = triple.get("subject")
            predicate_raw = triple.get("predicate")
            object_raw = triple.get("object")
            chunk_num = triple.get("chunk", "unknown")

            triple_valid = False
            normalized_sub, normalized_pred, normalized_obj = None, None, None

            if (
                isinstance(subject_raw, str)
                and isinstance(predicate_raw, str)
                and isinstance(object_raw, str)
            ):
                # 1. Normalize
                normalized_sub = subject_raw.strip().lower()
                normalized_pred = re.sub(r"\s+", " ", predicate_raw.strip().lower()).strip()
                normalized_obj = object_raw.strip().lower()

                # 2. Filter Empty
                if normalized_sub and normalized_pred and normalized_obj:
                    triple_identifier = (normalized_sub, normalized_pred, normalized_obj)

                    # 3. De-duplicate
                    if triple_identifier not in seen_triples:
                        normalized_triples.append(
                            {
                                "subject": normalized_sub,
                                "predicate": normalized_pred,
                                "object": normalized_obj,
                                "source_chunk": chunk_num,
                            }
                        )
                        seen_triples.add(triple_identifier)
                        triple_valid = True
                    else:
                        duplicates_removed_count += 1
                else:
                    empty_removed_count += 1
            else:
                empty_removed_count += 1  # Count non-string/missing as needing removal
            processed_count += 1

        print(f"\n... Finished processing {processed_count} triples.")

        knowledge_graph = nx.DiGraph()

        added_edges_count = 0
        update_interval = 5  # How often to print graph info update

        if not normalized_triples:
            print("Warning: No normalized triples to add to the graph.")
        else:
            for i, triple in enumerate(normalized_triples):
                subject_node = triple["subject"]
                object_node = triple["object"]
                predicate_label = triple["predicate"]

                # Nodes are added automatically when adding edges, but explicit calls are fine too
                # knowledge_graph.add_node(subject_node)
                # knowledge_graph.add_node(object_node)

                # Add the directed edge with the predicate as a 'label' attribute
                knowledge_graph.add_edge(subject_node, object_node, label=predicate_label)
                added_edges_count += 1

                # --- Visualize Graph Growth ---
                if (i + 1) % update_interval == 0 or (i + 1) == len(normalized_triples):
                    print(
                        f"\n--- Graph Info after adding Triple #{i + 1} --- ({subject_node} -> {object_node})"
                    )
                    try:
                        # Try the newer method first
                        print(nx.info(knowledge_graph))
                    except AttributeError:
                        # Fallback for different NetworkX versions
                        print(f"Type: {type(knowledge_graph).__name__}")
                        print(f"Number of nodes: {knowledge_graph.number_of_nodes()}")
                        print(f"Number of edges: {knowledge_graph.number_of_edges()}")
                    # For very large graphs, printing info too often can be slow. Adjust interval.
        self.knowledge_graph = knowledge_graph


    def knowledge_graph_status(self):
        raise NotImplementedError("This method should be implemented in subclasses.")
