import os
from typing import cast
from qdrant_client import QdrantClient
import asyncio
from dotenv import load_dotenv

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.base.response.schema import Response
from llama_index.core import Document
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.qdrant import QdrantVectorStore

load_dotenv()

llm = OpenAI(
    api_base=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
    model=os.environ["LLM_MODEL_NAME"],
)


async def main():
    embed_model = OpenAIEmbedding(
        api_base=os.environ.get("EMBEDDING_BASE_URL"),
        api_key=os.environ.get("EMBEDDING_API_KEY"),
        model="text-embedding-ada-002",
    )
    qdrant_path = os.environ["QDRANT_DATABASE_PATH"]
    qdrant_exists = os.path.exists(qdrant_path)
    vector_store = QdrantVectorStore(
        client=QdrantClient(path=qdrant_path),
        collection_name="iosys",
    )
    if qdrant_exists:
        print("[VectorIndex]: Collection 'iosys' exists, using it.")
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            embed_model=embed_model,
            use_async=True,
        )
    else:
        print("[VectorIndex]: Collection 'iosys' does not exist, creating it.")
        index = VectorStoreIndex(
            embed_model=embed_model,
            storage_context=StorageContext.from_defaults(
                vector_store=vector_store,
            ),
            use_async=True,
            nodes=[],
        )

    async def create_node(path: str, parsed: str):
        print(f"[VectorIndex]: Creating node for {path}")
        index.insert(
            Document(
                doc_id=path,
                text=parsed,
            )
        )

    async def update_node(path: str, parsed: str):
        print(f"[VectorIndex]: Updating node for {path}")
        index.refresh_ref_docs(
            [
                Document(
                    doc_id=path,
                    text=parsed,
                )
            ]
        )

    async def delete_node(path: str):
        index.delete_nodes([path])

    async def query_nodes(query: str):
        engine = index.as_query_engine(llm=llm)
        print(f"[VectorIndex]: Querying nodes with query: {query}")
        result = engine.query(query)
        return cast(Response, result)

    print("Index initialized successfully.")
    await create_node("path/to/story 1", "This is a tree with three branches.")
    await create_node("path/to/story 2", "This is a stone of 19th century.")
    response = await query_nodes("Which story is about a tree?")
    print(f"Query response: {response.response} {response.source_nodes}")


if __name__ == "__main__":
    asyncio.run(main())

# x = [
#     NodeWithScore(
#         node=TextNode(
#             id_="c1fb9a82-7e1a-4890-970d-b9f1e598a7d1",
#             embedding=None,
#             metadata={},
#             excluded_embed_metadata_keys=[],
#             excluded_llm_metadata_keys=[],
#             relationships={
#                 "1": RelatedNodeInfo(
#                     node_id="path/to/story 1",
#                     node_type="4",
#                     metadata={},
#                     hash="4997cb33d7992d10429416bce8cced51ba5393213632f6d5c34ae668a35d293e",
#                 )
#             },
#             metadata_template="{key}: {value}",
#             metadata_separator="\n",
#             text="This is a tree with three branches.",
#             mimetype="text/plain",
#             start_char_idx=0,
#             end_char_idx=35,
#             metadata_seperator="\n",
#             text_template="{metadata_str}\n\n{content}",
#         ),
#         score=0.8396673161251369,
#     )
# ]
