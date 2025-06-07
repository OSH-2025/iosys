import os

from llama_index.core import VectorStoreIndex
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.embeddings.utils import EmbedType
from llama_index.core import Document

from parser import IOSYSParsedFile


class IOSYSQueryEngine:
    embed_model: EmbedType
    index: VectorStoreIndex

    def __init__(self):
        self.embed_model = OpenAIEmbedding(
            api_base=os.environ.get("EMBEDDING_BASE_URL"),
            api_key=os.environ.get("EMBEDDING_API_KEY"),
            model="text-embedding-ada-002",
        )
        self.index = VectorStoreIndex(
            embed_model=self.embed_model,
            nodes=[],
        )

    async def update_file(self, id: str, parsed: IOSYSParsedFile):
        await self.index.ainsert(
            document=Document(
                doc_id=id,
                text=parsed.brief_text,
            )
        )

    async def delete_file(self, id: str):
        await self.index.adelete(id)

    async def query_files(self, query: str):
        return await self.index.as_query_engine(llm=self.llm).aquery(query)
