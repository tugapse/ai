import os
import time
import re
import hashlib
import threading
from typing import Any, List, Optional, Dict, Iterable
from abc import ABC, abstractmethod

import ai.functions as func
from ai.chat.chat import ChatRoles
from ai.core.llms.base_llm import BaseModel
from ai.modules.vector_memory.memory_tools import MemoryTools

DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Importance (1-10) per memory type, used unless LLM rating is enabled.
DEFAULT_IMPORTANCE: Dict[str, int] = {
    "decision": 8,
    "user_preference": 8,
    "reflection": 7,
    "fact": 6,
    "episode": 6,
    "distilled_observation": 5,
    "observation": 5,
    "communication": 4,
    "chat_turn": 3,
}

LTM_SCOPES = ("project", "session", "global")


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

    def embed_many(self, texts: List[str]) -> List[List[float]]:
        """Embeds several texts; providers may override with a batched implementation."""
        return [self.embed(t) for t in texts]


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
    def query(self, vector: List[float], top_k: int, where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Searches the database for memories most similar to the given query vector.

        :param vector: The query embedding vector.
        :param top_k: The maximum number of results to return.
        :param where: Optional metadata filter.
        :return: A list of dictionaries, each containing the ID, score, and metadata of a retrieved memory.
        """
        pass


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """
    Implements EmbeddingProvider using the sentence-transformers library.
    """
    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL):
        """
        Initializes the embedding provider by loading the specified sentence transformer model.

        :param model_name: The name of the sentence transformer model to use.
        :raises ImportError: If sentence-transformers is not installed.
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError("sentence-transformers is not installed. Run --install (Long Term Memory).") from e
        func.log(f"Loading embedding model: {model_name}")
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> List[float]:
        """
        Encodes the input text into a high-dimensional vector.

        :param text: The text string to embed.
        :return: The resulting embedding vector as a list of floats.
        """
        return self.model.encode(text).tolist()

    def embed_many(self, texts: List[str]) -> List[List[float]]:
        """Batched encoding (much faster than one call per text)."""
        if not texts:
            return []
        return [v.tolist() for v in self.model.encode(list(texts), batch_size=32)]


_EMBEDDERS: Dict[Any, EmbeddingProvider] = {}
_EMBEDDERS_LOCK = threading.Lock()


def get_embedder(model_name: str = DEFAULT_EMBEDDING_MODEL) -> EmbeddingProvider:
    """
    Returns a shared embedding provider for ``model_name`` (the model is loaded once per process).

    The cache is keyed by the provider class too, so tests that patch the class get a fresh mock.
    """
    key = (SentenceTransformerEmbeddingProvider, model_name)
    with _EMBEDDERS_LOCK:
        if key not in _EMBEDDERS:
            _EMBEDDERS[key] = SentenceTransformerEmbeddingProvider(model_name)
        return _EMBEDDERS[key]


class LLMProvider(LanguageModelProvider):
    """
    Implements LanguageModelProvider using a provided BaseModel (LLM).
    Handles prompting, rating, and knowledge synthesis via LLM calls.
    """
    def __init__(self, llm: Optional[BaseModel]):
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
            return max(1, min(10, int(match.group(0)))) if match else 5
        except Exception:
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
                "Analyze these memories of past work. Extract durable insights: decisions taken, "
                "facts about the project or the user, preferences, and lessons learned (what worked, what failed). "
                "Ignore conversational filler and anything already obvious. "
                "Output a bulleted list of concise, self-contained insights."
            ),
            "task_context": memories_str
        }
        response = self.send_raw_request(prompt, system_prompt="You are a memory synthesis engine. Output only the list.")
        return [line.strip().lstrip('-*').strip() for line in response.split('\n') if line.strip().startswith(('-', '*'))]

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
        if not self.llm:
            return ""

        from ai.direct import ask  # lazy: ai.direct imports modules that import this one

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


_CHROMA_CLIENTS: Dict[str, Any] = {}
_CHROMA_LOCK = threading.Lock()


def get_chroma_client(path: str):
    """Returns one shared PersistentClient per database path."""
    try:
        import chromadb
    except ImportError as e:
        raise ImportError("chromadb is not installed. Run --install (Long Term Memory).") from e
    path = os.path.abspath(path)
    with _CHROMA_LOCK:
        if path not in _CHROMA_CLIENTS:
            os.makedirs(path, exist_ok=True)
            _CHROMA_CLIENTS[path] = chromadb.PersistentClient(path=path)
        return _CHROMA_CLIENTS[path]


class ChromaDBProvider(VectorDBProvider):
    """
    Implements VectorDBProvider using ChromaDB for persistent vector storage.
    """
    def __init__(self, path: str, session_id: str = "default", collection_name: Optional[str] = None):
        """
        Initializes the ChromaDB client and collection.

        :param path: The directory path where the ChromaDB data will be stored.
        :param session_id: Scope key used to derive the collection name (when collection_name is not given).
        :param collection_name: Explicit collection name.
        :raises ImportError: If chromadb is not installed.
        """
        self.client = get_chroma_client(path)
        if not collection_name:
            collection_name = f"s_{hashlib.md5(session_id.encode()).hexdigest()}"
        self.collection_name = collection_name
        func.log(f"Initializing ChromaDB: {collection_name}")
        self.collection = self.client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})

    def upsert(self, memory_id: str, vector: List[float], metadata: Dict[str, Any]):
        """
        Inserts or replaces a memory record in the ChromaDB collection.

        :param memory_id: The unique ID of the memory.
        :param vector: The embedding vector.
        :param metadata: The associated metadata dictionary.
        """
        self.collection.upsert(ids=[memory_id], embeddings=[vector], metadatas=[metadata])

    def upsert_many(self, ids: List[str], vectors: List[List[float]], metadatas: List[Dict[str, Any]]):
        """Batched upsert."""
        if ids:
            self.collection.upsert(ids=ids, embeddings=vectors, metadatas=metadatas)

    def count(self) -> int:
        """Number of records in the collection."""
        try:
            return self.collection.count()
        except Exception:
            return 0

    def query(self, vector: List[float], top_k: int, where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Queries the ChromaDB to find the top K most similar memories to the input vector.

        :param vector: The query embedding vector.
        :param top_k: The number of top results to retrieve.
        :param where: Optional metadata filter (Chroma ``where`` syntax).
        :return: A list of dictionaries containing ID, similarity score, and metadata for each result.
        """
        total = self.count()
        if total == 0:
            return []
        kwargs: Dict[str, Any] = {"query_embeddings": [vector], "n_results": max(1, min(top_k, total))}
        if where:
            kwargs["where"] = where
        results = self.collection.query(**kwargs)
        if not results or not results['ids'] or not results['ids'][0]:
            return []

        output = []
        distances = results.get('distances')
        for i in range(len(results['ids'][0])):
            similarity = 1.0 - distances[0][i] if distances else 0.0
            output.append({'id': results['ids'][0][i], 'score': similarity, 'metadata': results['metadatas'][0][i]})
        return output

    def get(self, ids: Optional[List[str]] = None, where: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
        """Returns ``{id: metadata}`` for the given ids / filter (all records when both are None)."""
        kwargs: Dict[str, Any] = {"include": ["metadatas"]}
        if ids is not None:
            kwargs["ids"] = ids
        if where:
            kwargs["where"] = where
        res = self.collection.get(**kwargs)
        return {i: (m or {}) for i, m in zip(res.get("ids", []), res.get("metadatas", []) or [])}

    def update_metadata(self, ids: List[str], metadatas: List[Dict[str, Any]]):
        """Replaces the metadata of existing records."""
        if ids:
            self.collection.update(ids=ids, metadatas=metadatas)

    def delete(self, ids: Optional[List[str]] = None, where: Optional[Dict[str, Any]] = None):
        """Deletes records by id and/or metadata filter."""
        if not ids and not where:
            return
        kwargs: Dict[str, Any] = {}
        if ids:
            kwargs["ids"] = ids
        if where:
            kwargs["where"] = where
        self.collection.delete(**kwargs)


def resolve_ltm_scope(scope: Optional[str], session_id: str, workspace: Optional[str] = None) -> str:
    """
    Maps the LTM_SCOPE setting to the key that names the memory collection.

    - ``project`` (default): one memory per workspace folder, shared by all its sessions.
    - ``session``: one memory per session (the old behaviour).
    - ``global``: one memory for everything.
    """
    scope = (scope or "project").strip().lower()
    if scope == "session":
        return f"session:{session_id}"
    if scope == "global":
        return "global"
    return f"project:{os.path.abspath(workspace or os.getcwd())}"


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
        scope_key: Optional[str] = None,
        llm_importance: bool = False,
    ):
        """
        Initializes the VectorMemory system components.

        :param session_id: The current session id (stored with each memory).
        :param llm: An optional LLM instance used for reflection (and rating, when llm_importance is on).
        :param db_path: Path to the persistent vector database storage.
        :param recency_weight: Weight applied to the recency score during retrieval.
        :param importance_weight: Weight applied to the importance score during retrieval.
        :param relevance_weight: Weight applied to the similarity score during retrieval.
        :param scope_key: Key naming the collection (see resolve_ltm_scope). Defaults to the session id.
        :param llm_importance: Ask the LLM to rate each memory instead of using DEFAULT_IMPORTANCE.
        """
        self.session_id = session_id
        self.scope_key = scope_key or session_id
        self.db = ChromaDBProvider(path=db_path, session_id=self.scope_key)
        self.embedder = get_embedder()
        self.llm = LLMProvider(llm=llm) if llm else None
        self.llm_importance = llm_importance

        self.recency_weight = recency_weight
        self.importance_weight = importance_weight
        self.relevance_weight = relevance_weight
        self.new_memories = 0  # memories added since the last reflection
        self.tools = MemoryTools(self)

    def _importance(self, content: str, memory_type: str) -> int:
        if self.llm and self.llm_importance:
            return self.llm.rate_importance(content)
        return DEFAULT_IMPORTANCE.get(memory_type, 5)

    def add_memory(self, content: str, source: str, memory_type: str = "observation", metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Processes new content, embeds it, scores it, and stores it in the vector database.

        :param content: The raw text content of the memory.
        :param source: Where the content originated (e.g., 'chat', 'observation').
        :param memory_type: Categorization of the memory (see DEFAULT_IMPORTANCE).
        :param metadata: Extra scalar metadata to store.
        :return: The memory id, or None when nothing was stored.
        """
        if not content or not str(content).strip():
            return None
        content = str(content).strip()

        importance = self._importance(content, memory_type)
        vector = self.embedder.embed(content)
        memory_id = hashlib.sha256(content.encode()).hexdigest()
        now = time.time()

        record = {
            "content": content,
            "source": source,
            "type": memory_type,
            "session_id": self.session_id or "",
            "created_at": now,
            "last_accessed_at": now,
            "importance": importance,
        }
        for k, v in (metadata or {}).items():
            if isinstance(v, (str, int, float, bool)):
                record[k] = v

        self.db.upsert(memory_id=memory_id, vector=vector, metadata=record)
        self.new_memories += 1
        func.log(f"Memory Archived [{memory_type}]: {content[:40]}... (ID: {memory_id[:8]})")
        return memory_id

    @staticmethod
    def _type_filter(types: Optional[Iterable[str]]) -> Optional[Dict[str, Any]]:
        types = [t for t in (types or []) if t]
        if not types:
            return None
        if len(types) == 1:
            return {"type": types[0]}
        return {"type": {"$in": list(types)}}

    def search(self, query: str, top_k: int = 5, types: Optional[Iterable[str]] = None,
               min_relevance: float = 0.0, touch: bool = True) -> List[Dict[str, Any]]:
        """
        Retrieves and ranks memories based on relevance, importance, and recency.

        :param query: Text used to search for relevant memories.
        :param top_k: The number of final, ranked memories to return.
        :param types: Only return memories of these types.
        :param min_relevance: Drop candidates whose semantic similarity is below this value.
        :param touch: Update last_accessed_at of the returned memories.
        :return: Dicts with content, type, source, importance, relevance and score, best first.
        """
        if not query:
            return []

        query_vector = self.embedder.embed(query)
        results = self.db.query(vector=query_vector, top_k=top_k * 3, where=self._type_filter(types))

        ranked = []
        for res in results:
            meta = res.get('metadata') or {}
            relevance = res.get('score', 0.0)
            if relevance < min_relevance:
                continue
            recency = self._calculate_recency_score(meta.get('last_accessed_at', meta.get('created_at', time.time())))
            importance = float(meta.get('importance', 5)) / 10.0
            final_score = (
                self.recency_weight * recency +
                self.importance_weight * importance +
                self.relevance_weight * relevance
            )
            ranked.append({
                "id": res.get("id"),
                "content": meta.get("content", ""),
                "type": meta.get("type", ""),
                "source": meta.get("source", ""),
                "importance": meta.get("importance", 5),
                "relevance": round(relevance, 3),
                "score": round(final_score, 3),
                "_meta": meta,
            })

        ranked.sort(key=lambda x: x["score"], reverse=True)
        top = ranked[:top_k]

        if touch and top:
            now = time.time()
            try:
                ids = [r["id"] for r in top if r.get("id")]
                metas = [{**r["_meta"], "last_accessed_at": now} for r in top if r.get("id")]
                self.db.update_metadata(ids, metas)
            except Exception as e:
                func.debug(f"VectorMemory: could not update access time: {e}")

        for r in top:
            r.pop("_meta", None)
        return top

    def retrieve_memories(self, query: str, top_k: int = 5, types: Optional[Iterable[str]] = None,
                          min_relevance: float = 0.0) -> List[str]:
        """
        Same as search() but returns only the memory texts.

        :param query: The user query used to search for relevant memories.
        :param top_k: The number of final, ranked memories to return.
        :return: A list of the top K most relevant memory contents (strings).
        """
        return [r["content"] for r in self.search(query, top_k=top_k, types=types, min_relevance=min_relevance)]

    def trigger_reflection(self, lookback_k: int = 30) -> int:
        """
        Initiates the knowledge synthesis process. It retrieves recent memories and
        uses the LLM to distill them into high-level, permanent insights.

        :param lookback_k: The number of recent memories to pull for synthesis.
        :return: The number of insights stored.
        """
        if not self.llm:
            return 0

        recent = self.retrieve_memories("current context and recent interactions", top_k=lookback_k)

        if len(recent) < 5:
            return 0

        insights = self.llm.summarize_and_reflect(recent)
        for insight in insights:
            self.add_memory(insight, source="SELF_REFLECTION", memory_type="reflection")

        self.new_memories = 0
        func.log(f"Reflection Complete: Generated {len(insights)} high-level insights.")
        return len(insights)

    @staticmethod
    def _calculate_recency_score(last_accessed_at: float, decay_factor: float = 0.99) -> float:
        """
        Calculates a score based on how long ago a memory was last accessed,
        using an exponential decay model.

        :param last_accessed_at: The Unix timestamp of the last access.
        :param decay_factor: The factor determining the rate of decay (closer to 1 means slower decay).
        :return: A recency score between 0 and 1.
        """
        hours = max(0.0, (time.time() - last_accessed_at) / 3600)
        return decay_factor ** hours
