import os
import json

from llama_index.core.graph_stores import (SimplePropertyGraphStore, EntityNode)
from llama_index.core.llms.llm import LLM
from llama_index.llms.openai import OpenAI
from llama_index.core import VectorStoreIndex
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.embeddings.utils import EmbedType
from llama_index.core import Document

from ..parser import IOSYSParsedFile

class IOSYSQueryEngine:
    llm: LLM
    embed_model: EmbedType
    graph_store: SimplePropertyGraphStore
    index: VectorStoreIndex

    def __init__(self):
        self.llm = OpenAI(
            api_base=os.environ.get("LLM_BASE_URL"),
            api_key=os.environ.get("LLM_API_KEY"),
            model=os.environ.get("LLM_MODEL_NAME"),
        )
        self.embed_model =  OpenAIEmbedding(
            api_base=os.environ.get("EMBEDDING_BASE_URL"),
            api_key=os.environ.get("EMBEDDING_API_KEY"),
            model="text-embedding-ada-002",
        )
        self.graph_store = SimplePropertyGraphStore()
        self.index = VectorStoreIndex(
            embed_model=self.embed_model,
        )

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

        self.index.insert(
            document=Document(text=parsed.description)
        )

    def delete_file(self, id: str):
        self.graph_store.graph.delete_node(id)
    
    def query_files(self, query: str):
        return self.index.as_query_engine(llm=self.llm).query(query)
