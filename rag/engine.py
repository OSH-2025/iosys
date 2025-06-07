import os
import json

from llama_index.core.graph_stores import SimplePropertyGraphStore
from llama_index.core.llms.llm import LLM
from llama_index.llms.openai import OpenAI


class IOSYSQueryEngine:
    store: SimplePropertyGraphStore
    llm: LLM

    def __init__(self):
        self.graph_store = SimplePropertyGraphStore()
        self.llm = OpenAI(
            api_base=os.environ.get("LLM_BASE_URL"),
            api_key=os.environ.get("LLM_API_KEY"),
            model=os.environ.get("LLM_MODEL_NAME"),
        )

    def load(self, dumped: str):
        data = json.loads(dumped)
        self.store = SimplePropertyGraphStore.from_dict(data)

    def dump(self):
        return self.store.graph.model_dump_json()
