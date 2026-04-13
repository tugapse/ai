import time
import re
import hashlib
from typing import Any, List, Optional, Dict
from abc import ABC, abstractmethod
import functions as func
from .memory_tools import MemoryTools

# External dependencies
try:
    from sentence_transformers import SentenceTransformer
    import chromadb
except ImportError:
    func.error("Missing dependencies: pip install sentence-transformers chromadb")
    SentenceTransformer = None
    chromadb = None

class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        pass

class LanguageModelProvider(ABC):
    """Abstract base class for language model providers."""
    @abstractmethod
    def rate_importance(self, text: str) -> int:
        pass

    @abstractmethod
    def summarize_and_reflect(self, memories: List[str]) -> List[str]:
        pass

class VectorDBProvider(ABC):
    """Abstract base class for vector database providers."""
    @abstractmethod
    def upsert(self, memory_id: str, vector: List[float], metadata: Dict[str, Any]):
        pass

    @abstractmethod
    def query(self, vector: List[float], top_k: int) -> List[Dict[str, Any]]:
        pass

class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using sentence-transformers."""
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        if SentenceTransformer is None:
            raise ImportError("sentence-transformers is not installed.")
        func.log(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> List[float]:
        return self.model.encode(text).tolist()

class LLMProvider(LanguageModelProvider):
    """Language model provider using the project's LLMConnector."""
    def __init__(self, connector: Any):
        self.connector = connector

    def rate_importance(self, text: str) -> int:
        """Rates the importance of information on a scale of 1-10."""
        prompt = {
            "instruction": "Rate the importance of this information for an AI to remember (1-10). Respond with only an integer.",
            "task_context": text
        }
        response = self.connector.send_raw_request(prompt, system_prompt="/no_think Response must be a single integer.")
        try:
            match = re.search(r'\d+', response)
            return int(match.group(0)) if match else 5
        except:
            return 5

    def summarize_and_reflect(self, memories: List[str]) -> List[str]:
        """Synthesizes raw memories into high-level insights."""
        memories_str = "\n".join(f"- {m}" for m in memories)
        prompt = {
            "instruction": "Synthesize these memories into high-level insights. Output a bulleted list where each line is one insight.",
            "task_context": memories_str
        }
        response = self.connector.send_raw_request(prompt, system_prompt="You are a reflection engine. Output only the list.")
        return [line.strip('- ').strip() for line in response.split('\n') if line.strip().startswith('-')]

class ChromaDBProvider(VectorDBProvider):
    """Vector database provider using ChromaDB."""
    def __init__(self, path: str, session_id: str = "default"):
        if chromadb is None:
            raise ImportError("chromadb is not installed.")
        self.client = chromadb.PersistentClient(path=path)
        session_hash = hashlib.md5(session_id.encode()).hexdigest()
        collection_name = f"s_{session_hash}"
        func.log(f"Initializing ChromaDB: {collection_name}")
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def upsert(self, memory_id: str, vector: List[float], metadata: Dict[str, Any]):
        self.collection.upsert(ids=[memory_id], embeddings=[vector], metadatas=[metadata])

    def query(self, vector: List[float], top_k: int) -> List[Dict[str, Any]]:
        results = self.collection.query(query_embeddings=[vector], n_results=top_k)
        if not results or not results['ids'][0]: return []
        
        output = []
        for i in range(len(results['ids'][0])):
            similarity = 1.0 - results['distances'][0][i] if results['distances'] else 0.0
            output.append({'id': results['ids'][0][i], 'score': similarity, 'metadata': results['metadatas'][0][i]})
        return output

class VectorMemory:
    """
    Manages an agent's long-term memory via vector search and LLM-guided reflection.
    """

    def __init__(
        self,
        session_id: str,
        connector: Any | None = None,
        db_path: str = "./agent_ltm_db",
        recency_weight: float = 1.0,
        importance_weight: float = 1.0,
        relevance_weight: float = 1.0,
    ):
        self.db = ChromaDBProvider(path=db_path, session_id=session_id)
        self.embedder = SentenceTransformerEmbeddingProvider()
        self.llm = LLMProvider(connector) if connector else None
        
        self.recency_weight = recency_weight
        self.importance_weight = importance_weight
        self.relevance_weight = relevance_weight
        
        # Link tools for Orchestrator integration
        self.tools = MemoryTools(self)

    def add_memory(self, content: str, source: str, memory_type: str = "observation"):
        """Enriches and archives a new memory with a persistent SHA-256 ID."""
        if not content: return
        
        importance = self.llm.rate_importance(content) if self.llm else 5
        vector = self.embedder.embed(content)
        
        # Persistent ID across restarts
        memory_id = hashlib.sha256(content.encode()).hexdigest()
        
        metadata = {
            "content": content,
            "source": source,
            "type": memory_type,
            "created_at": time.time(),
            "last_accessed_at": time.time(),
            "importance": importance,
        }
        
        self.db.upsert(memory_id=memory_id, vector=vector, metadata=metadata)
        func.log(f"Memory Archived: {content[:40]}... (ID: {memory_id[:8]})")

    def retrieve_memories(self, query: str, top_k: int = 5) -> List[str]:
        """Retrieves memories using a composite score of relevance, recency, and importance."""
        if not query: return []
        
        query_vector = self.embedder.embed(query)
        results = self.db.query(vector=query_vector, top_k=top_k * 3)
        
        ranked_results = []
        for res in results:
            recency = self._calculate_recency_score(res['metadata']['last_accessed_at'])
            importance = res['metadata']['importance'] / 10.0
            relevance = res['score']

            final_score = (
                self.recency_weight * recency +
                self.importance_weight * importance +
                self.relevance_weight * relevance
            )
            ranked_results.append((final_score, res['metadata']['content']))
            
        ranked_results.sort(key=lambda x: x[0], reverse=True)
        return [content for score, content in ranked_results[:top_k]]

    def trigger_reflection(self):
        """Synthesizes recent high-importance memories into distilled insights."""
        if not self.llm: return

        recent = self.retrieve_memories("Identify key technical events and patterns.", top_k=25)
        if not recent: return

        insights = self.llm.summarize_and_reflect(recent)
        for insight in insights:
            self.add_memory(insight, source="SELF_REFLECTION", memory_type="reflection")

    @staticmethod
    def _calculate_recency_score(last_accessed_at: float, decay_factor: float = 0.99) -> float:
        """Calculates temporal decay score based on hours since access."""
        hours = (time.time() - last_accessed_at) / 3600
        return decay_factor ** hours