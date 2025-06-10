import os
from typing import cast
from qdrant_client import QdrantClient
from dataclasses import dataclass, asdict
import asyncio
from fnmatch import fnmatch

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.embeddings.utils import EmbedType
from llama_index.core.base.response.schema import Response
from llama_index.core import Document
from llama_index.core.llms.llm import LLM
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.schema import NodeRelationship, NodeWithScore

from parser import IOSYSParsedFile


@dataclass
class QueryResponse:
    response: str
    files: list[str]
    nodes: list[NodeWithScore]

    def to_dict(self):
        return {
            "response": self.response,
            "files": self.files,
        }


class IOSYSQueryEngine:
    llm: LLM
    embed_model: EmbedType
    index: VectorStoreIndex
    init_task: asyncio.Task | None = None

    def __init__(self, llm: LLM):
        self.llm = llm
        self.embed_model = OpenAIEmbedding(
            api_base=os.environ.get("EMBEDDING_BASE_URL"),
            api_key=os.environ.get("EMBEDDING_API_KEY"),
            model="text-embedding-ada-002",
        )
        qdrant_path = os.environ["QDRANT_DATABASE_PATH"]
        qdrant_exists = os.path.exists(qdrant_path)
        qdrant_client = QdrantClient(path=qdrant_path)
        vector_store = QdrantVectorStore(
            client=qdrant_client,
            collection_name="iosys",
        )
        if qdrant_exists:
            print("[VectorIndex]: Collection 'iosys' exists, using it.")
            self.index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store,
                embed_model=self.embed_model,
                use_async=True,
            )
        else:
            print("[VectorIndex]: Collection 'iosys' does not exist, creating it.")
            self.index = VectorStoreIndex(
                embed_model=self.embed_model,
                storage_context=StorageContext.from_defaults(
                    vector_store=vector_store,
                ),
                use_async=True,
                nodes=[],
            )

    async def _ensure_initialized(self):
        if self.init_task:
            await self.init_task
            self.init_task = None

    async def create_node(self, path: str, parsed: IOSYSParsedFile):
        await self._ensure_initialized()
        print(f"[VectorIndex]: Creating node for {path}")
        self.index.insert(
            Document(
                doc_id=path,
                text=parsed.brief_text,
            )
        )

    async def update_node(self, path: str, parsed: IOSYSParsedFile):
        await self._ensure_initialized()
        print(f"[VectorIndex]: Updating node for {path}")
        self.index.refresh_ref_docs(
            [
                Document(
                    doc_id=path,
                    text=parsed.brief_text,
                )
            ]
        )

    async def delete_node(self, path: str):
        await self._ensure_initialized()
        self.index.delete_nodes([path])

    async def query_nodes(
        self, query: str, include_glob: list[str], exclude_glob: list[str]
    ):
        print(f"[VectorIndex]: Querying nodes with query: {query}")

        def get_file_path(node: NodeWithScore):
            relation_node = node.node.relationships[NodeRelationship.SOURCE]
            return relation_node.node_id  # type: ignore

        def filter(path: str):
            return any(fnmatch(path, pattern) for pattern in include_glob) and not any(
                fnmatch(path, pattern) for pattern in exclude_glob
            )

        await self._ensure_initialized()
        engine = self.index.as_query_engine(llm=self.llm, use_async=True)
        result = cast(Response, engine.query(query))

        files = set()
        for node in result.source_nodes:
            file_path = get_file_path(node)
            if filter(file_path):
                files.add(file_path)

        return QueryResponse(
            response=result.response or "",
            files=list(files),
            nodes=result.source_nodes,
        )
