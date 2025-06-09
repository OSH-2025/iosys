import os
from typing import cast
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import VectorParams, Distance
import asyncio

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.embeddings.utils import EmbedType
from llama_index.core.base.response.schema import Response
from llama_index.core import Document
from llama_index.core.llms.llm import LLM
from llama_index.vector_stores.qdrant import QdrantVectorStore

from parser import IOSYSParsedFile


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
        qdrant_client = AsyncQdrantClient(path=qdrant_path)
        vector_store = QdrantVectorStore(
            aclient=qdrant_client,
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
            self.init_task = asyncio.create_task(
                qdrant_client.create_collection(
                    collection_name="iosys",
                    vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
                )
            )
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
        await self.index.ainsert(
            Document(
                doc_id=path,
                text=parsed.brief_text,
            )
        )

    async def update_node(self, path: str, parsed: IOSYSParsedFile):
        await self._ensure_initialized()
        print(f"[VectorIndex]: Updating node for {path}")
        await self.index.arefresh_ref_docs(
            [
                Document(
                    doc_id=path,
                    text=parsed.brief_text,
                )
            ]
        )

    async def delete_node(self, path: str):
        await self._ensure_initialized()
        await self.index.adelete_nodes([path])

    async def query_nodes(self, query: str):
        await self._ensure_initialized()
        engine = self.index.as_query_engine(llm=self.llm, use_async=True)
        print(f"[VectorIndex]: Querying nodes with query: {query}")
        result = await engine.aquery(query)
        return cast(Response, result)
