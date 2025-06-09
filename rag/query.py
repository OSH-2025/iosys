import os
from typing import cast
from qdrant_client import QdrantClient

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

    def __init__(self, llm: LLM):
        self.llm = llm
        self.embed_model = OpenAIEmbedding(
            api_base=os.environ.get("EMBEDDING_BASE_URL"),
            api_key=os.environ.get("EMBEDDING_API_KEY"),
            model="text-embedding-ada-002",
        )
        qdrant_client = QdrantClient(path=os.environ["QDRANT_PATH"])
        storage_context = StorageContext.from_defaults(
            vector_store=QdrantVectorStore(
                client=qdrant_client,
                collection_name="iosys",
            )
        )
        self.index = VectorStoreIndex(
            embed_model=self.embed_model,
            storage_context=storage_context,
            nodes=[],
        )

    async def create_node(self, path: str, parsed: IOSYSParsedFile):
        print(f"[VectorIndex]: Creating node for {path}")
        await self.index.ainsert(
            Document(
                doc_id=path,
                text=parsed.brief_text,
            )
        )

    async def update_node(self, path: str, parsed: IOSYSParsedFile):
        print(f"[VectorIndex]: Updating node for {path}")
        await self.index.aupdate_ref_doc(
            Document(
                doc_id=path,
                text=parsed.brief_text,
            )
        )

    async def delete_node(self, path: str):
        await self.index.adelete_nodes([path])

    async def query_nodes(self, query: str):
        engine = self.index.as_query_engine(llm=self.llm)
        print(f"[VectorIndex]: Querying nodes with query: {query}")
        result = await engine.aquery(query)
        return cast(Response, result)
