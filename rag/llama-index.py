import os
import re
import asyncio
import pandas as pd
from typing import Any, List, Callable, Optional, Union

import nest_asyncio
import networkx as nx
from dotenv import load_dotenv
from graspologic.partition import hierarchical_leiden

from llama_index.core import Document, PropertyGraphIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.async_utils import run_jobs
from llama_index.core.indices.property_graph.utils import default_parse_triplets_fn
from llama_index.core.graph_stores.types import EntityNode, KG_NODES_KEY, KG_RELATIONS_KEY, Relation
from llama_index.core.graph_stores import SimplePropertyGraphStore
from llama_index.core.llms.llm import LLM
from llama_index.core.llms import ChatMessage
from llama_index.core.prompts import PromptTemplate
from llama_index.core.prompts.default_prompts import DEFAULT_KG_TRIPLET_EXTRACT_PROMPT
from llama_index.core.schema import TransformComponent, BaseNode
from llama_index.core.query_engine import CustomQueryEngine
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

# Apply nest_asyncio to handle async operations
nest_asyncio.apply()

# Load environment variables
load_dotenv()

# Load sample news data
news = pd.read_csv(
    "https://raw.githubusercontent.com/tomasonjo/blog-datasets/main/news_articles.csv"
)[:50]

documents = [
    Document(text=f"{row['title']}: {row['text']}") for _, row in news.iterrows()
]

# Split documents into manageable chunks
splitter = SentenceSplitter(
    chunk_size=1024,
    chunk_overlap=20,
)
nodes = splitter.get_nodes_from_documents(documents)

# Configure LLM with explicit base_url
llm = OpenAI(
    api_base=os.environ.get("LLM_BASE_URL"),
    api_key=os.environ.get("LLM_API_KEY"),
    model=os.environ.get("LLM_MODEL_NAME"),
)

# Configure embedding model with explicit base_url  
embed_model = OpenAIEmbedding(
    api_base=os.environ.get("EMBEDDING_BASE_URL"),
    api_key=os.environ.get("EMBEDDING_API_KEY"),
    model="text-embedding-ada-002",
)

# Define extraction prompt template
KG_TRIPLET_EXTRACT_TMPL = """
Extract knowledge triplets from the following text. 
Format each entity as: entity_name: <name> entity_type: <type> entity_description: <description>
Format each relationship as: source_entity: <source> target_entity: <target> relation: <relation> relationship_description: <description>

Text: {text}

Extract at most {max_knowledge_triplets} triplets.
"""

# Define patterns for parsing extraction results
entity_pattern = (
    r"entity_name:\s*(.+?)\s*entity_type:\s*(.+?)\s*entity_description:\s*(.+?)\s*"
)
relationship_pattern = r"source_entity:\s*(.+?)\s*target_entity:\s*(.+?)\s*relation:\s*(.+?)\s*relationship_description:\s*(.+?)\s*"

def parse_fn(response_str: str) -> Any:
    """Parse LLM response to extract entities and relationships."""
    entities = re.findall(entity_pattern, response_str)
    relationships = re.findall(relationship_pattern, response_str)
    return entities, relationships

# GraphRAG Extractor Class
class GraphRAGExtractor(TransformComponent):
    """Extract triples from a graph using LLM."""

    llm: LLM
    extract_prompt: PromptTemplate
    parse_fn: Callable
    num_workers: int
    max_paths_per_chunk: int

    def __init__(
        self,
        llm: Optional[LLM] = None,
        extract_prompt: Optional[Union[str, PromptTemplate]] = None,
        parse_fn: Callable = default_parse_triplets_fn,
        max_paths_per_chunk: int = 10,
        num_workers: int = 4,
    ) -> None:
        """Initialize GraphRAG extractor."""
        from llama_index.core import Settings

        if isinstance(extract_prompt, str):
            extract_prompt = PromptTemplate(extract_prompt)

        super().__init__(
            llm=llm or Settings.llm,
            extract_prompt=extract_prompt or DEFAULT_KG_TRIPLET_EXTRACT_PROMPT,
            parse_fn=parse_fn,
            num_workers=num_workers,
            max_paths_per_chunk=max_paths_per_chunk,
        )

    @classmethod
    def class_name(cls) -> str:
        return "GraphExtractor"

    def __call__(
        self, nodes: List[BaseNode], show_progress: bool = False, **kwargs: Any
    ) -> List[BaseNode]:
        """Extract triples from nodes."""
        return asyncio.run(self.acall(nodes, show_progress=show_progress, **kwargs))

    async def _aextract(self, node: BaseNode) -> BaseNode:
        """Extract triples from a single node."""
        assert hasattr(node, "text")

        text = node.get_content(metadata_mode="llm")
        try:
            llm_response = await self.llm.apredict(
                self.extract_prompt,
                text=text,
                max_knowledge_triplets=self.max_paths_per_chunk,
            )
            entities, entities_relationship = self.parse_fn(llm_response)
        except ValueError:
            entities = []
            entities_relationship = []

        existing_nodes = node.metadata.pop(KG_NODES_KEY, [])
        existing_relations = node.metadata.pop(KG_RELATIONS_KEY, [])
        
        # Process entities
        metadata = node.metadata.copy()
        for entity, entity_type, description in entities:
            metadata["entity_description"] = description
            entity_node = EntityNode(
                name=entity, label=entity_type, properties=metadata
            )
            existing_nodes.append(entity_node)

        # Process relationships
        metadata = node.metadata.copy()
        for triple in entities_relationship:
            subj, rel, obj, description = triple
            subj_node = EntityNode(name=subj, properties=metadata)
            obj_node = EntityNode(name=obj, properties=metadata)
            metadata["relationship_description"] = description
            rel_node = Relation(
                label=rel,
                source_id=subj_node.id,
                target_id=obj_node.id,
                properties=metadata,
            )

            existing_nodes.extend([subj_node, obj_node])
            existing_relations.append(rel_node)

        node.metadata[KG_NODES_KEY] = existing_nodes
        node.metadata[KG_RELATIONS_KEY] = existing_relations
        return node

    async def acall(
        self, nodes: List[BaseNode], show_progress: bool = False, **kwargs: Any
    ) -> List[BaseNode]:
        """Extract triples from nodes asynchronously."""
        jobs = []
        for node in nodes:
            jobs.append(self._aextract(node))

        return await run_jobs(
            jobs,
            workers=self.num_workers,
            show_progress=show_progress,
            desc="Extracting paths from text",
        )

# GraphRAG Store Class
class GraphRAGStore(SimplePropertyGraphStore):
    """Enhanced property graph store with community detection and summarization."""
    
    def __init__(self):
        super().__init__()
        self.community_summary = {}
        self.max_cluster_size = 5

    def generate_community_summary(self, text):
        """Generate summary for a given text using an LLM."""
        messages = [
            ChatMessage(
                role="system",
                content=(
                    "You are provided with a set of relationships from a knowledge graph, each represented as "
                    "entity1->entity2->relation->relationship_description. Your task is to create a summary of these "
                    "relationships. The summary should include the names of the entities involved and a concise synthesis "
                    "of the relationship descriptions. The goal is to capture the most critical and relevant details that "
                    "highlight the nature and significance of each relationship. Ensure that the summary is coherent and "
                    "integrates the information in a way that emphasizes the key aspects of the relationships."
                ),
            ),
            ChatMessage(role="user", content=text),
        ]
        response = llm.chat(messages)
        clean_response = re.sub(r"^assistant:\s*", "", str(response)).strip()
        return clean_response

    def build_communities(self):
        """Build communities from the graph and summarize them."""
        nx_graph = self._create_nx_graph()
        community_hierarchical_clusters = hierarchical_leiden(
            nx_graph, max_cluster_size=self.max_cluster_size
        )
        community_info = self._collect_community_info(
            nx_graph, community_hierarchical_clusters
        )
        self._summarize_communities(community_info)

    def _create_nx_graph(self):
        """Convert internal graph representation to NetworkX graph."""
        nx_graph = nx.Graph()
        for node in self.graph.nodes.values():
            nx_graph.add_node(str(node))
        for relation in self.graph.relations.values():
            nx_graph.add_edge(
                relation.source_id,
                relation.target_id,
                relationship=relation.label,
                description=relation.properties.get("relationship_description", ""),
            )
        return nx_graph

    def _collect_community_info(self, nx_graph, clusters):
        """Collect detailed information for each node based on their community."""
        community_mapping = {item.node: item.cluster for item in clusters}
        community_info = {}
        for item in clusters:
            cluster_id = item.cluster
            node = item.node
            if cluster_id not in community_info:
                community_info[cluster_id] = []

            for neighbor in nx_graph.neighbors(node):
                if community_mapping[neighbor] == cluster_id:
                    edge_data = nx_graph.get_edge_data(node, neighbor)
                    if edge_data:
                        detail = f"{node} -> {neighbor} -> {edge_data['relationship']} -> {edge_data['description']}"
                        community_info[cluster_id].append(detail)
        return community_info

    def _summarize_communities(self, community_info):
        """Generate and store summaries for each community."""
        for community_id, details in community_info.items():
            details_text = "\n".join(details) + "."
            self.community_summary[community_id] = self.generate_community_summary(
                details_text
            )

    def get_community_summaries(self):
        """Return community summaries, building them if not already done."""
        if not self.community_summary:
            self.build_communities()
        return self.community_summary

# GraphRAG Query Engine Class
class GraphRAGQueryEngine(CustomQueryEngine):
    """Custom query engine for GraphRAG."""
    
    graph_store: GraphRAGStore
    llm: LLM

    def custom_query(self, query_str: str) -> str:
        """Process all community summaries to generate answers to a specific query."""
        community_summaries = self.graph_store.get_community_summaries()
        community_answers = [
            self.generate_answer_from_summary(community_summary, query_str)
            for _, community_summary in community_summaries.items()
        ]

        final_answer = self.aggregate_answers(community_answers)
        return final_answer

    def generate_answer_from_summary(self, community_summary, query):
        """Generate an answer from a community summary based on a given query using LLM."""
        prompt = (
            f"Given the community summary: {community_summary}, "
            f"how would you answer the following query? Query: {query}"
        )
        messages = [
            ChatMessage(role="system", content=prompt),
            ChatMessage(
                role="user",
                content="I need an answer based on the above information.",
            ),
        ]
        response = self.llm.chat(messages)
        cleaned_response = re.sub(r"^assistant:\s*", "", str(response)).strip()
        return cleaned_response

    def aggregate_answers(self, community_answers):
        """Aggregate individual community answers into a final, coherent response."""
        prompt = (
            "Combine the following intermediate answers into a final, concise response."
        )
        messages = [
            ChatMessage(role="system", content=prompt),
            ChatMessage(
                role="user",
                content=f"Intermediate answers: {community_answers}",
            ),
        ]
        final_response = self.llm.chat(messages)
        cleaned_final_response = re.sub(
            r"^assistant:\s*", "", str(final_response)
        ).strip()
        return cleaned_final_response

# Initialize components
kg_extractor = GraphRAGExtractor(
    llm=llm,
    extract_prompt=KG_TRIPLET_EXTRACT_TMPL,
    max_paths_per_chunk=2,
    parse_fn=parse_fn,
)

# Build graph index
index = PropertyGraphIndex(
    nodes=nodes,
    property_graph_store=GraphRAGStore(),
    kg_extractors=[kg_extractor],
    embed_model=embed_model,
    show_progress=True,
    
)

# Initialize query engine
query_engine = GraphRAGQueryEngine(graph_store=index.property_graph_store, llm=llm)

# Example query
if __name__ == "__main__":
    response = query_engine.query("What are news related to financial sector?")
    print(f"Response: {response}")
