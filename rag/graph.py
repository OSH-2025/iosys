import os
from dataclasses import asdict

from llama_index.core.graph_stores import SimplePropertyGraphStore, EntityNode, Relation
from llama_index.core.llms.llm import LLM
from llama_index.llms.openai import OpenAI

from parser import IOSYSParsedFile


class IOSYSGraphEngine:
    llm: LLM
    graph_store: SimplePropertyGraphStore
    revision: int = 0

    def __init__(self):
        self.llm = OpenAI(
            api_base=os.environ.get("LLM_BASE_URL"),
            api_key=os.environ.get("LLM_API_KEY"),
            model=os.environ.get("LLM_MODEL_NAME"),
        )
        self.graph_store = SimplePropertyGraphStore()

    def load(self, dumped: str):
        self.graph_store = SimplePropertyGraphStore.from_dict(dumped)

    def dump(self):
        dumped = self.graph_store.graph.model_dump()
        dumped["revision"] = self.revision
        return dumped

    def update_file(self, id: str, parsed: IOSYSParsedFile):
        self.graph_store.graph.add_node(
            EntityNode(
                name=id,
                label="file",
                properties=asdict(parsed),
            )
        )
        if parsed.parent_id:
            print(parsed.parent_id,
                   "contains",
                    id,)
            self.graph_store.graph.add_relation(
                Relation(
                    source_id=parsed.parent_id,
                    label="contains",
                    target_id=id,
                )
            )
        self.revision += 1

    def delete_file(self, id: str):
        self.graph_store.graph.delete_node(id)
        self.revision += 1
