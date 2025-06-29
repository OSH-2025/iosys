import os
import shutil
import time
import json
import datetime
from typing import List, Tuple, Optional
import traceback

from llama_index.core.graph_stores import (
    PropertyGraphStore,
    SimplePropertyGraphStore,
    EntityNode,
    Relation,
)
from llama_index.graph_stores.nebula import NebulaPropertyGraphStore
from llama_index.core.llms.llm import LLM

from fs import FileSystemNode


RECENT_TIME_SPAN = 2 * 60  # 2 minutes


class IOSYSGraphEngine:
    llm: LLM
    graph_store: PropertyGraphStore
    local_graph_path: str | None
    revision: int = int(time.time())

    recent_event: Optional[Tuple[str, float]] = None

    def __init__(self, llm: LLM):
        self.llm = llm
        self.local_graph_path = os.environ["USE_LOCAL_GRAPH_STORE"]
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
                    local_fs = os.environ["USE_LOCAL_FS"]
                    if os.path.exists(local_fs):
                        shutil.rmtree(local_fs)
                        os.makedirs(local_fs)
        else:
            self.graph_store = NebulaPropertyGraphStore(
                username=os.environ["NEBULA_USERNAME"],
                password=os.environ["NEBULA_PASSWORD"],
                url=os.environ["NEBULA_URL"],
                space=os.environ["NEBULA_SPACE"],
                overwrite=True,
            )

        self.graph_store.upsert_nodes(
            [
                EntityNode(
                    name="/",
                    label="directory",
                )
            ]
        )
        self.commit()

    async def create_file(self, node: FileSystemNode):
        return await self.update_file(node)

    async def update_file(self, node: FileSystemNode):
        try:
            await self.graph_store.aupsert_nodes(
                [
                    EntityNode(
                        name=node.path,
                        label="file",
                        # properties=asdict(parsed),
                    )
                ]
            )
            parent = node.parent()
            assert parent is not None, "Parent node must not be None"
            await self.graph_store.aupsert_relations(
                [
                    Relation(
                        source_id=parent.path,
                        label="contains",
                        target_id=node.path,
                    )
                ]
            )
            await self.connect_event(node.path, "updated")
            self.commit()
        except Exception as e:
            print(f"Error updating file {node.path}: ", e)
            raise e

    async def delete_file(self, path: str):
        try:
            # self.delete_llama_nodes(node_ids=[path])
            self.delete(ids=[path], entity_names=["file"])
            # await self.connect_event(path, "deleted")
            self.commit()
        except Exception as e:
            print(f"Error removing file {path}:")
            print(f"  Exception: {type(e).__name__}: {e}")
            print("  Full traceback:")
            traceback.print_exc()

            raise e

    def delete(
        self,
        entity_names: Optional[List[str]] = None,
        relation_names: Optional[List[str]] = None,
        properties: Optional[dict] = None,
        ids: Optional[List[str]] = None,
    ) -> None:
        """Delete matching data."""
        nodes = self.graph_store.get(properties=properties, ids=ids)
        for node in nodes:
            self.graph_store.graph.delete_node(node)  # type: ignore

    def delete_llama_nodes(
        self,
        node_ids: Optional[List[str]] = None,
        ref_doc_ids: Optional[List[str]] = None,
    ) -> None:
        """
        Delete llama-index nodes.

        Intended to delete any nodes in the graph store associated
        with the given llama-index node_ids or ref_doc_ids.
        """
        nodes = []

        # triplets = self.graph_store.graph.get_triplets() # type: ignore
        triplets = []
        try:
            # 安全地获取所有三元组
            for subj_id, rel_id, obj_id in self.graph_store.graph.triplets:  # type: ignore
                try:
                    assert isinstance(self.graph_store, SimplePropertyGraphStore)
                    # 检查节点是否存在
                    if (
                        subj_id in self.graph_store.graph.nodes  # type: ignore
                        and obj_id in self.graph_store.graph.nodes  # type: ignore
                    ):  # type: ignore
                        rel_key = self.graph_store.graph._get_relation_key(  # type: ignore
                            obj_id=obj_id, subj_id=subj_id, rel_id=rel_id
                        )

                        if rel_key in self.graph_store.graph.relations:  # type: ignore
                            triplet = (
                                self.graph_store.graph.nodes[subj_id],  # type: ignore
                                self.graph_store.graph.relations[rel_key],  # type: ignore
                                self.graph_store.graph.nodes[obj_id],  # type: ignore
                            )
                            triplets.append(triplet)
                    else:
                        print(
                            f"Warning: Missing nodes for triplet {subj_id}-{rel_id}-{obj_id}"
                        )
                except KeyError as e:
                    print(
                        f"Warning: KeyError when processing triplet {subj_id}-{rel_id}-{obj_id}: {e}"
                    )
                    continue
        except Exception as e:
            print(f"Error getting triplets: {e}")

        node_ids = node_ids or []
        triplets_ids = []
        for id_ in node_ids:
            for triplet in triplets:
                if triplet[1].source_id == id_:
                    triplets_ids.append(triplet[1].target_id)

        if len(triplets_ids) > 0:
            nodes.extend(self.graph_store.get(ids=triplets_ids))

        if len(node_ids) > 0:
            nodes.extend(self.graph_store.get(ids=node_ids))

        ref_doc_ids = ref_doc_ids or []
        for id_ in ref_doc_ids:
            nodes.extend(self.graph_store.get(properties={"ref_doc_id": id_}))

        if len(ref_doc_ids) > 0:
            nodes.extend(self.graph_store.get(ids=ref_doc_ids))

        for node in nodes:
            self.delete(ids=[node.id])

    async def create_directory(self, path: str, parent_path: str):
        return await self.update_directory(path, parent_path)

    async def update_directory(self, path: str, parent_path: str):
        try:
            await self.graph_store.aupsert_nodes(
                [
                    EntityNode(
                        name=path,
                        label="directory",
                    )
                ]
            )
            await self.graph_store.aupsert_relations(
                [
                    Relation(
                        source_id=parent_path,
                        label="contains",
                        target_id=path,
                    )
                ]
            )
            await self.connect_event(path, "created")
            self.commit()
        except Exception as e:
            print(f"Error creating directory {path}: ", e)
            raise e

    async def delete_directory(self, path: str):
        # raise NotImplementedError("Delete directory is not implemented yet.")
        try:
            self.delete_llama_nodes(node_ids=[path])
            # await self.connect_event(path, "deleted")
            self.commit()
        except Exception as e:
            print(f"Error removing file {path}:")
            print(f"  Exception: {type(e).__name__}: {e}")
            print("  Full traceback:")
            traceback.print_exc()
            raise e

    async def connect_event(self, path: str, label: str):
        current_time = time.time()
        if (
            self.recent_event
            and (current_time - self.recent_event[1]) < RECENT_TIME_SPAN
        ):
            event_name, _ = self.recent_event
        else:
            event_name = f"event_{datetime.datetime.now().strftime('%m-%d_%H:%M')}"
            await self.graph_store.aupsert_nodes(
                [
                    EntityNode(
                        name=event_name,
                        label="event",
                    )
                ]
            )

        self.recent_event = (event_name, current_time)
        await self.graph_store.aupsert_relations(
            [
                Relation(
                    source_id=event_name,
                    label=label,
                    target_id=path,
                )
            ]
        )

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
