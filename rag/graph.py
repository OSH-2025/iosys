import os
import json

from llama_index.core.graph_stores import (
    PropertyGraphStore,
    SimplePropertyGraphStore,
    EntityNode,
    Relation,
)
from llama_index.graph_stores.nebula import NebulaPropertyGraphStore
from llama_index.core.llms.llm import LLM
from llama_index.llms.openai import OpenAI

from parser import IOSYSParsedFile


class IOSYSGraphEngine:
    llm: LLM
    graph_store: PropertyGraphStore
    local_graph_path: str | None
    revision: int = 0

    def __init__(self):
        self.llm = OpenAI(
            api_base=os.environ.get("LLM_BASE_URL"),
            api_key=os.environ.get("LLM_API_KEY"),
            model=os.environ.get("LLM_MODEL_NAME"),
        )

        self.local_graph_path = os.environ.get("USE_LOCAL_GRAPH_STORE")
        if self.local_graph_path:
            self.graph_store = SimplePropertyGraphStore()
            if os.path.exists(self.local_graph_path):
                with open(self.local_graph_path, "r") as f:
                    dumped = f.read()
                if dumped:
                    dumped = json.loads(dumped)
                    self.graph_store = SimplePropertyGraphStore.from_dict(dumped)
        else:
            self.graph_store = NebulaPropertyGraphStore(
                username=os.environ.get("NEBULA_USERNAME"),
                password=os.environ.get("NEBULA_PASSWORD"),
                url=os.environ.get("NEBULA_URL"),
                space=os.environ.get("NEBULA_SPACE"),
                overwrite=True,
            )

    async def update_file(self, path: str, parsed: IOSYSParsedFile):
        try:
            await self.graph_store.aupsert_nodes(
                [
                    EntityNode(
                        name=path,
                        label="file",
                        # properties=asdict(parsed),
                    )
                ]
            )
            if parsed.parent_path:
                await self.graph_store.aupsert_relations(
                    [
                        Relation(
                            source_id=parsed.parent_path,
                            label="contains",
                            target_id=path,
                        )
                    ]
                )
        except Exception as e:
            print(f"Error updating file {path}: ", e)
            return
        self.commit()

    async def delete_file(self, path: str):
        await self.graph_store.adelete(entity_names=[path])
        self.commit()

    def commit(self):
        self.revision += 1
        if self.local_graph_path:
            with open(self.local_graph_path, "w") as f:
                dumped = self.graph_store.graph.model_dump(mode="json")
                dumped["revision"] = self.revision
                f.write(json.dumps(dumped))
