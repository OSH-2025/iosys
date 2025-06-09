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

from parser import IOSYSParsedFile


class IOSYSGraphEngine:
    llm: LLM
    graph_store: PropertyGraphStore
    local_graph_path: str | None
    revision: int = 0

    def __init__(self, llm: LLM):
        self.llm = llm
        self.local_graph_path = os.environ.get("USE_LOCAL_GRAPH_STORE")
        if self.local_graph_path:
            self.graph_store = SimplePropertyGraphStore()
            if os.path.exists(self.local_graph_path):
                with open(self.local_graph_path, "r") as f:
                    dumped = f.read()
                if dumped:
                    dumped = json.loads(dumped)
                    self.graph_store = SimplePropertyGraphStore.from_dict(dumped)
                    self.revision = dumped["revision"]
        else:
            self.graph_store = NebulaPropertyGraphStore(
                username=os.environ["NEBULA_USERNAME"],
                password=os.environ["NEBULA_PASSWORD"],
                url=os.environ["NEBULA_URL"],
                space=os.environ["NEBULA_SPACE"],
                overwrite=True,
            )

    async def create_node(self, path: str, parsed: IOSYSParsedFile):
        return await self.update_node(path, parsed)

    async def update_node(self, path: str, parsed: IOSYSParsedFile):
        try:
            self.graph_store.aupsert_nodes
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

    def to_dict(self):
        if not isinstance(self.graph_store, SimplePropertyGraphStore):
            raise NotImplementedError()
        dumped = self.graph_store.graph.model_dump(mode="json")
        dumped["revision"] = self.revision
        return dumped

    def commit(self):
        self.revision += 1
        if self.local_graph_path:
            with open(self.local_graph_path, "w") as f:
                f.write(json.dumps(self.to_dict(), indent=2))
