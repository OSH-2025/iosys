import os
import json

from llama_index.core.graph_stores import SimplePropertyGraphStore, EntityNode
from llama_index.core.llms.llm import LLM
from llama_index.llms.openai import OpenAI

from ..parser import IOSYSParsedFile


class IOSYSGraphEngine:
    llm: LLM
    graph_store: SimplePropertyGraphStore

    def __init__(self):
        self.llm = OpenAI(
            api_base=os.environ.get("LLM_BASE_URL"),
            api_key=os.environ.get("LLM_API_KEY"),
            model=os.environ.get("LLM_MODEL_NAME"),
        )
        self.graph_store = SimplePropertyGraphStore()

    def load(self, dumped: str):
        data = json.loads(dumped)
        self.graph_store = SimplePropertyGraphStore.from_dict(data)

    def dump(self):
        return self.graph_store.graph.model_dump_json()

    def update_file(self, id: str, parsed: IOSYSParsedFile):
        self.graph_store.graph.add_node(
            EntityNode(
                name=id,
                label="file",
                properties=parsed,
            )
        )
        # TODO: Link with parent directory if available

    def delete_file(self, id: str):
        self.graph_store.graph.delete_node(id)
