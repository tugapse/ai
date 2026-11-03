import os
import time
import re
import hashlib
from typing import Any, List, Optional, Dict
from abc import ABC, abstractmethod

import ai.functions as func
from ai.chat.chat import ChatRoles
from ai.core.llms.base_llm import BaseModel
from ai.direct import ask
from ai.modules.vector_memory.memory_tools import MemoryTools

SentenceTransformer = None
chromadb = None

class EmbeddingProvider(ABC):
    """
    Abstract base class defining the interface for generating vector embeddings from text.
    """
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """
        Generates a numerical vector representation for the given text.

        :param text: The input string to be embedded.
        :return: A list of floats representing the embedding vector.
        """
        pass

class LanguageModelProvider(ABC):
    """
    Abstract base class defining the interface for interacting with a Language Model
    for tasks like importance rating and knowledge synthesis.
    """
    @abstractmethod
    def rate_importance(self, text: str) -> int:
        """
        Asks the LLM to rate the importance of a piece of text on a scale of 1 to 10.

        :param text: The text content to be rated.
        :return: An integer representing the importance score.
        """
        pass

    @abstractmethod
    def summarize_and_reflect(self, memories: List[str]) -> List[str]:
        """
        Instructs the LLM to synthesize a list of concise, actionable insights from a collection of memories.

        :param memories: A list of raw memory strings to analyze.
        :return: A list of synthesized insight strings.
        """
        pass

class VectorDBProvider(ABC):
    """
    Abstract base class defining the interface for interacting with a Vector Database.
    """
    @abstractmethod
    def upsert(self, memory_id: str, vector: List[float], metadata: Dict[str, Any]):
        """
        Stores a new memory vector and its associated metadata in the database.

        :param memory_id: A unique identifier for the memory.
        :param vector: The numerical embedding vector.
        :param metadata: A dictionary containing descriptive information about the memory.
        """
        pass

    @abstractmethod
    def query(self, vector: List[float], top_k: int) -> List[Dict[str, Any]]:
        """
        Searches the database for memories most similar to the given query vector.

        :param vector: The query embedding vector.
        :param top_k: The maximum number of results to return.
        :return: A list of dictionaries, each containing the ID, score, and metadata of a retrieved memory.
        """
        pass

class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """
    Implements EmbeddingProvider using the sentence-transformers library.
    """
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initializes the embedding provider by loading the specified sentence transformer model.

        :param model_name: The name of the sentence transformer model to use.
        :raises ImportError: If sentence-transformers is not installed.
        """
        if SentenceTransformer is None:
            raise ImportError("sentence-transformers is not installed.")
        func.log(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> List[float]:
        """
        Encodes the input text into a high-dimensional vector.

        :param text: The text string to embed.
        :return: The resulting embedding vector as a list of floats.
        """
        return self.model.encode(text).tolist()

class LLMProvider(LanguageModelProvider):
    """
    Implements LanguageModelProvider using a provided BaseModel (LLM).
    Handles prompting, rating, and knowledge synthesis via LLM calls.
    """
    def __init__(self, llm : Optional[BaseModel]):
        """
        Initializes the LLM provider with a specific LLM instance.

        :param llm: An optional instance of BaseModel to perform LLM operations.
        """
        self.llm = llm

    def rate_importance(self, text: str) -> int:
        """
        Requests the LLM to score the importance of the provided text.

        :param text: The text content to rate.
        :return: The integer importance score, defaulting to 5 on failure.
        """
        prompt = {
            "instruction": "Rate the importance of this information for long-term retention (1-10). Respond with only an integer.",
            "task_context": text
        }
        response = self.send_raw_request(prompt, system_prompt="/no_think Response must be a single integer.")
        try:
            match = re.search(r'\d+', response)
            return int(match.group(0)) if match else 5
        except:
            return 5

    def summarize_and_reflect(self, memories: List[str]) -> List[str]:
        """
        Uses the LLM to distill a list of concise insights from a set of raw memories.

        :param memories: A list of raw memory strings.
        :return: A list of synthesized, bulleted insight strings.
        """
        memories_str = "\n".join(f"- {m}" for m in memories)
        prompt = {
            "instruction": (
                "Analyze these recent memories. Extract NEW facts about the user, "
                "project updates, or specific preferences. Ignore conversational filler. "
                "Output a bulleted list of concise insights."
            ),
            "task_context": memories_str
        }
        response = self.send_raw_request(prompt, system_prompt="You are a memory synthesis engine. Output only the list.")
        return [line.strip('- ').strip() for line in response.split('\n') if line.strip().startswith('-')]
    
    def send_raw_request(self, payload: Dict[str, Any], system_prompt: str = "") -> str:
        """
        Constructs and executes a raw request to the underlying LLM.

        :param payload: Dictionary containing the instruction and context for the LLM.
        :param system_prompt: The system-level instruction to guide the LLM's behavior.
        :return: The raw string response received from the LLM.
        """
        messages = [
            BaseModel.create_message(ChatRoles.SYSTEM, system_prompt),
            BaseModel.create_message(ChatRoles.USER, 
                f"CONTEXT:\n{payload.get('task_context')}\n\n"
                f"INSTRUCTION:\n{payload.get('instruction')}"
            )
        ]
        return self._execute_llm_call(messages).strip()
    
    def _execute_llm_call(self, messages: List[Dict[str, str]]) -> str:
        """
        Handles the actual execution of the LLM call, managing file output and error handling.

        :param messages: The list of messages to send to the LLM.
        :return: The content read from the output file, or an empty string on failure.
        """
        if not self.llm: return ""
        
        output_filename = f"{func.get_root_directory()}/logs/memory_output_active.md"
        try:
            ask(
                self.llm, 
                messages, 
                hide_think_anim=True, 
                print_output=False, 
                print_mode="line", 
                output_filename=output_filename, 
                write_to_file=True,
                stream=True
            )
            
            if os.path.exists(output_filename):
                with open(output_filename, "r", encoding="utf-8") as f:
                    content = f.read()
                return content
            return ""
                
        except Exception as e:
            func.error(f"LLM Execution failed: {e}")
            return ""

class ChromaDBProvider(VectorDBProvider):
    """
    Implements VectorDBProvider using ChromaDB for persistent vector storage.
    """
    def __init__(self, path: str, session_id: str = "default"):
        """
        Initializes the ChromaDB client and collection for a specific session.

        :param path: The directory path where the ChromaDB data will be stored.
        :param session_id: A unique identifier for the session, used to name the collection.
        :raises ImportError: If chromadb is not installed.
        """
        if chromadb is None:
            raise ImportError("chromadb is not installed.")
        self.client = chromadb.PersistentClient(path=path)
        session_hash = hashlib.md5(session_id.encode()).hexdigest()
        collection_name = f"s_{session_hash}"
        func.log(f"Initializing ChromaDB: {collection_name}")
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def upsert(self, memory_id: str, vector: List[float], metadata: Dict[str, Any]):
        """
        Inserts a new memory record into the ChromaDB collection.

        :param memory_id: The unique ID of the memory.
        :param vector: The embedding vector.
        :param metadata: The associated metadata dictionary.
        """
        self.collection.upsert(ids=[memory_id], embeddings=[vector], metadatas=[metadata])

    def query(self, vector: List[float], top_k: int) -> List[Dict[str, Any]]:
        """
        Queries the ChromaDB to find the top K most similar memories to the input vector.

        :param vector: The query embedding vector.
        :param top_k: The number of top results to retrieve.
        :return: A list of dictionaries containing ID, similarity score, and metadata for each result.
        """
        results = self.collection.query(query_embeddings=[vector], n_results=top_k)
        if not results or not results['ids'][0]: return []
        
        output = []
        for i in range(len(results['ids'][0])):
            similarity = 1.0 - results['distances'][0][i] if results['distances'] else 0.0
            output.append({'id': results['ids'][0][i], 'score': similarity, 'metadata': results['metadatas'][0][i]})
        return output

class VectorMemory:
    """
    Manages the entire lifecycle of long-term memory, including embedding, storage,
    retrieval, and knowledge synthesis (reflection).
    """
    def __init__(
        self,
        session_id: str,
        llm: BaseModel | None = None,
        db_path: str = "./agent_ltm_db",
        recency_weight: float = 1.0,
        importance_weight: float = 1.0,
        relevance_weight: float = 1.0,
    ):
        """
        Initializes the VectorMemory system components.

        :param session_id: A unique identifier for the user or session.
        :param llm: An optional LLM instance used for rating and reflection.
        :param db_path: Path to the persistent vector database storage.
        :param recency_weight: Weight applied to the recency score during retrieval.
        :param importance_weight: Weight applied to the importance score during retrieval.
        :param relevance_weight: Weight applied to the similarity score during retrieval.
        """
        self.db = ChromaDBProvider(path=db_path, session_id=session_id)
        self.embedder = SentenceTransformerEmbeddingProvider()
        self.llm = LLMProvider(llm=llm) if llm else None
        
        self.recency_weight = recency_weight
        self.importance_weight = importance_weight
        self.relevance_weight = relevance_weight
        self.tools = MemoryTools(self)
        try:
            from sentence_transformers import SentenceTransformer
            import chromadb
            SentenceTransformer = SentenceTransformer
            chromadb = chromadb
        except ImportError:
            func.error("Missing dependencies: pip install sentence-transformers chromadb")


    def add_memory(self, content: str, source: str, memory_type: str = "observation"):
        """
        Processes new content, embeds it, scores it, and stores it in the vector database.

        :param content: The raw text content of the memory.
        :param source: Where the content originated (e.g., 'chat', 'observation').
        :param memory_type: Categorization of the memory (e.g., 'observation', 'reflection').
        """
        if not content: return
        
        importance = self.llm.rate_importance(content) if self.llm else 5
        vector = self.embedder.embed(content)
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
        """
        Retrieves and ranks memories based on relevance, importance, and recency.

        :param query: The user query used to search for relevant memories.
        :param top_k: The number of final, ranked memories to return.
        :return: A list of the top K most relevant memory contents (strings).
        """
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

    def trigger_reflection(self, lookback_k: int = 30):
        """
        Initiates the knowledge synthesis process. It retrieves recent memories and
        uses the LLM to distill them into high-level, permanent insights.

        :param lookback_k: The number of recent memories to pull for synthesis.
        """
        if not self.llm: return

        # Pull a broad slice of recent activity to synthesize
        recent = self.retrieve_memories("current context and recent interactions", top_k=lookback_k)
        
        if len(recent) < 5: 
            return

        insights = self.llm.summarize_and_reflect(recent)
        for insight in insights:
            # We save these as 'reflection' to distinguish them from raw data
            self.add_memory(insight, source="SELF_REFLECTION", memory_type="reflection")
        
        func.log(f"Reflection Complete: Generated {len(insights)} high-level insights.")

    @staticmethod
    def _calculate_recency_score(last_accessed_at: float, decay_factor: float = 0.99) -> float:
        """
        Calculates a score based on how long ago a memory was last accessed,
        using an exponential decay model.

        :param last_accessed_at: The Unix timestamp of the last access.
        :param decay_factor: The factor determining the rate of decay (closer to 1 means slower decay).
        :return: A recency score between 0 and 1.
        """
        hours = (time.time() - last_accessed_at) / 3600
        return decay_factor ** hours