import time
import re
import hashlib
from typing import Any
from abc import ABC, abstractmethod
import functions as func


# pip install sentence-transformers chromadb
try:
    from sentence_transformers import SentenceTransformer
    import chromadb
except ImportError:
    print("Please install sentence-transformers and chromadb: pip install sentence-transformers chromadb")
    SentenceTransformer = None
    chromadb = None

class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        pass

class LanguageModelProvider(ABC):
    """Abstract base class for language model providers."""
    @abstractmethod
    def rate_importance(self, text: str) -> int:
        pass

    @abstractmethod
    def summarize_and_reflect(self, memories: list[str]) -> list[str]:
        pass

class VectorDBProvider(ABC):
    """Abstract base class for vector database providers."""
    @abstractmethod
    def upsert(self, memory_id: str, vector: list[float], metadata: dict[str, Any]):
        pass

    @abstractmethod
    def query(self, vector: list[float], top_k: int) -> list[dict[str, Any]]:
        pass

class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using sentence-transformers."""
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        if SentenceTransformer is None:
            raise ImportError("sentence-transformers is not installed.")
        func.log(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> list[float]:
        return self.model.encode(text).tolist()

class LLMProvider(LanguageModelProvider):
    """Language model provider using the project's LLMConnector."""
    def __init__(self, connector: Any):
        self.connector = connector

    def rate_importance(self, text: str) -> int:
        func.debug(f"Rating importance for: '{text[:50]}...'")
        prompt = (
            "On a scale from 1 to 10, where 1 is trivial and 10 is critically important, "
            "rate the importance of the following piece of information for an AI agent to remember.\n"
            "Respond with only a single integer.\n\n"
            f"Information: \"{text}\"\n\n"
            "Importance (1-10):"
        )
        system_prompt = "You are a helpful assistant that provides only a single integer in response."
        
        response = self.connector.send_raw_request(
            {"task_context": prompt, "instruction": "Provide only a single integer."},
            system_prompt=system_prompt
        )
        
        try:
            match = re.search(r'\d+', response)
            if match:
                importance = int(match.group(0))
                func.debug(f"Rated importance as: {importance}")
                return importance
        except (ValueError, TypeError):
            pass
        func.debug("Failed to rate importance, falling back to 5.")
        return 5  # Fallback

    def summarize_and_reflect(self, memories: list[str]) -> list[str]:
        func.log("Synthesizing memories into new insights...")
        memories_str = "\n".join(f"- {m}" for m in memories)
        prompt = (
            "Read the following recent memories of an AI agent. "
            "Synthesize them into a few high-level insights or conclusions. "
            "What are the key takeaways? What patterns are emerging? What should be the focus now?\n\n"
            "Recent Memories:\n"
            f"{memories_str}\n\n"
            "Respond with a bulleted list of your key insights. Each insight should be a new memory."
        )
        system_prompt = (
            "You are a reflection engine for an AI agent. Your task is to synthesize "
            "raw memories into higher-level insights. Output only the insights as a bulleted list."
        )
        
        response = self.connector.send_raw_request(
            {"task_context": prompt, "instruction": "Provide a bulleted list of insights."},
            system_prompt=system_prompt
        )
        
        insights = [line.strip('- ').strip() for line in response.split('\n') if line.strip().startswith('-')]
        func.log(f"Generated {len(insights)} new insights from reflection.")
        return [i for i in insights if i]

class ChromaDBProvider(VectorDBProvider):
    """Vector database provider using ChromaDB."""
    def __init__(self, path: str = "./memory_db", session_id: str = "default"):
        """
        Initializes the ChromaDBProvider for a specific session.

        Args:
            path (str): The path to the persistent database directory.
            session_id (str): A unique identifier for the session. Memories will be
                              isolated to a collection based on this ID.
        """
        if chromadb is None:
            raise ImportError("chromadb is not installed.")
        self.client = chromadb.PersistentClient(path=path)
        # Use a hash of the session_id to guarantee a valid collection name.
        session_hash = hashlib.md5(session_id.encode()).hexdigest()
        collection_name = f"s_{session_hash}"
        func.log(f"Initializing ChromaDB collection '{collection_name}' at path '{path}'")
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def upsert(self, memory_id: str, vector: list[float], metadata: dict[str, Any]):
        func.debug(f"Upserting memory ID '{memory_id}' into ChromaDB.")
        self.collection.upsert(ids=[memory_id], embeddings=[vector], metadatas=[metadata])

    def query(self, vector: list[float], top_k: int) -> list[dict[str, Any]]:
        func.debug(f"Querying ChromaDB for {top_k} nearest neighbors.")
        results = self.collection.query(query_embeddings=[vector], n_results=top_k)
        if not results or not results.get('ids') or not results['ids'][0]:
            func.debug("ChromaDB query returned no results.")
            return []
        
        output = []
        for i in range(len(results['ids'][0])):
            similarity = 1.0 - results['distances'][0][i] if results['distances'] else 0.0
            output.append({'id': results['ids'][0][i], 'score': similarity, 'metadata': results['metadatas'][0][i]})
        func.debug(f"ChromaDB query found {len(output)} results.")
        return output

# --- The Main VectorMemory Class ---

class VectorMemory:
    """
    Manages an agent's long-term memory using a vector database.

    This class handles the ingestion, retrieval, and synthesis of memories,
    allowing an agent to recall relevant information from its past.
    """

    def __init__(
        self,
        db_provider: VectorDBProvider,
        embedding_provider: EmbeddingProvider,
        llm_provider: LanguageModelProvider,
        recency_weight: float = 1.0,
        importance_weight: float = 1.0,
        relevance_weight: float = 1.0,
    ):
        """
        Initializes the VectorMemory.

        Args:
            db_provider: Client for the vector database (e.g., Chroma, Pinecone).
            embedding_provider: Client for generating text embeddings.
            llm_provider: Client for language model operations like rating and reflection.
            recency_weight: Weight for the recency score in retrieval.
            importance_weight: Weight for the importance score in retrieval.
            relevance_weight: Weight for the relevance (similarity) score in retrieval.
        """
        self.db = db_provider
        self.embedder = embedding_provider
        self.llm = llm_provider
        self.recency_weight = recency_weight
        self.importance_weight = importance_weight
        self.relevance_weight = relevance_weight

    def add_memory(self, content: str, source: str, memory_type: str = "observation"):
        """
        Adds a new memory to the database, enriched with metadata.

        Args:
            content (str): The text content of the memory.
            source (str): The origin of the memory (e.g., 'USER', 'AGENT_X', 'TOOL_Y').
            memory_type (str): The type of memory (e.g., 'observation', 'reflection').
        """
        if not content:
            return
            
        importance = self.llm.rate_importance(content)
        vector = self.embedder.embed(content)
        
        metadata = {
            "content": content,
            "source": source,
            "type": memory_type,
            "created_at": time.time(),
            "last_accessed_at": time.time(),
            "importance": importance,
        }
        
        # Using a hash of the content for a unique ID
        memory_id = str(hash(content))
        self.db.upsert(memory_id=memory_id, vector=vector, metadata=metadata)
        func.log(f"Added memory: '{content[:50]}...' (Importance: {importance})")

    def retrieve_memories(self, query: str, top_k: int = 5) -> list[str]:
        """
        Retrieves the most relevant memories based on a combination of
        recency, importance, and relevance to the query.
        """
        if not query:
            return []
        
        func.log(f"Retrieving {top_k} memories for query: '{query[:50]}...'")
        query_vector = self.embedder.embed(query)
        
        # Fetch more results than needed to allow for re-ranking
        results = self.db.query(vector=query_vector, top_k=top_k * 5)
        
        # Update last_accessed_at for retrieved memories (optional, but good for recency)
        # for res in results: self.db.update_metadata(res['id'], {'last_accessed_at': time.time()})

        # Re-rank based on the three key factors
        ranked_results = []
        for res in results:
            recency_score = self._calculate_recency_score(res['metadata']['last_accessed_at'])
            importance_score = res['metadata']['importance'] / 10.0  # Normalize
            relevance_score = res['score']  # Cosine similarity from DB

            final_score = (
                self.recency_weight * recency_score +
                self.importance_weight * importance_score +
                self.relevance_weight * relevance_score
            )
            ranked_results.append((final_score, res['metadata']['content']))
            
        # Sort by the final composite score in descending order
        ranked_results.sort(key=lambda x: x[0], reverse=True)
        
        retrieved = [content for score, content in ranked_results[:top_k]]
        func.log(f"Retrieved {len(retrieved)} relevant memories.")
        return retrieved

    def trigger_reflection(self):
        """
        Periodically runs a reflection process to synthesize new, high-level memories.
        """
        # This would involve fetching recent or important memories and prompting an LLM
        func.log("Triggering reflection...")
        recent_memories = self.retrieve_memories("What are the most important recent events?", top_k=50)
        
        if not recent_memories:
            func.log("Not enough memories to reflect on.")
            return

        new_insights = self.llm.summarize_and_reflect(recent_memories)
        
        for insight in new_insights:
            self.add_memory(insight, source="SELF_REFLECTION", memory_type="reflection")

    @staticmethod
    def _calculate_recency_score(last_accessed_at: float, decay_factor: float = 0.99) -> float:
        """Calculates a score based on how recently a memory was accessed."""
        hours_since_access = (time.time() - last_accessed_at) / 3600
        return decay_factor ** hours_since_access
