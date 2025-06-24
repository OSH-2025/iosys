import openai  # For LLM interaction
import json  # For parsing LLM responses
import networkx as nx  # For creating and managing the graph data structure
import ipycytoscape  # For interactive in-notebook graph visualization
import pandas as pd  # For displaying data in tables
import os  # For accessing environment variables (safer for API keys)
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
    """Agent 配置类"""

    llm: OpenAI
    fs: IOSYSFileSystem
    rag: IOSYSRAG

    def __init__(
        self,
        llm: OpenAI,
        fs: IOSYSFileSystem,
        rag: IOSYSRAG,
        log_level: str = "INFO",
    ):
        self.llm = llm
        self.fs = fs
        self.rag = rag
        self.llm_api_key = os.environ["LLM_API_KEY"]
        self.llm_model = os.environ["LLM_MODEL_NAME"]
        self.llm_api_base = os.environ["LLM_BASE_URL"]

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
        self.tool_configs = self._collect_tool_configs()
        self.tool_handlers = self._collect_tool_handlers()
        self.unstructured_text = ""

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
        raise NotImplementedError("This method should be implemented in subclasses.")
    
    def knowledge_graph_status(self):
        raise NotImplementedError("This method should be implemented in subclasses.")
