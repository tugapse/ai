## 1. Architectural Role
Provides a long-term memory subsystem utilizing vector embeddings and LLM-driven reflection to store, retrieve, and synthesize information via a ChromaDB backend.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `EmbeddingProvider` | Class (ABC) | Abstract interface for generating vector embeddings from text. |
| `LanguageModelProvider` | Class (ABC) | Abstract interface for importance rating and memory synthesis. |
| `VectorDBProvider` | Class (ABC) | Abstract interface for vector database upsert and query operations. |
| `SentenceTransformerEmbeddingProvider` | Class | Concrete implementation using `SentenceTransformer` for text embedding. |
| `LLMProvider` | Class | Concrete implementation using a `BaseModel` to rate importance and summarize memories. |
| `ChromaDBProvider` | Class | Concrete implementation managing `chromadb` persistent storage and similarity queries. |
| `VectorMemory` | Class | Orchestrator managing the lifecycle of memory addition, retrieval, and reflection. |
| `add_memory` | Method | Encapsulates text into a vector, assigns metadata/importance, and upserts to DB. |
| `retrieve_memories` | Method | Performs vector similarity search and applies weighted scoring (recency, importance, relevance). |
| `trigger_reflection` | Method | Synthesizes recent memories into high-level insights via LLM to optimize context. |
| `_calculate_recency_score` | Method | Computes temporal decay based on the time elapsed since last access. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. `VectorMemory` instantiates `ChromaDBProvider` (creating/accessing a collection via MD5 hashed `session_id`).
    2. `SentenceTransformerEmbeddingProvider` loads a transformer model (default: `all-MiniLM-L6-v2`).
    3. `LLMProvider` wraps the provided `BaseModel`.
    4. `MemoryTools` is initialized with the `VectorMemory` instance.
- **Data Path (Memory Ingestion)**: 
    `content` (str) $\rightarrow$ `LLMProvider.rate_importance` (int) $\rightarrow$ `SentenceTransformerEmbeddingProvider.embed` (List[float]) $\rightarrow$ `ChromaDBProvider.upsert` (Metadata + Vector) $\rightarrow$ Persistent Storage.
- **Data Path (Retrieval)**: 
    `query` (str) $\rightarrow$ `embedder.embed` (vector) $\rightarrow$ `db.query` (raw results) $\rightarrow$ `_calculate_recency_score` + `importance` + `relevance` weighting $\rightarrow$ Sorted `ranked_results` $\rightarrow$ `top_k` content strings.
- **Conditional Branching**:
    - **Dependency Check**: If `sentence-transformers` or `chromadb` are missing, `func.error` is called and providers are set to `None`.
    - **LLM Availability**: `add_memory` defaults importance to `5` if `self.llm` is `None`.
    - **Reflection Threshold**: `trigger_reflection` aborts if the retrieved memory count is $< 5$.
    - **LLM Error Handling**: `_execute_llm_call` catches exceptions and returns an empty string if the `ask` call fails.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `time`, `re`, `hashlib`, `typing`, `abc`
- **Internal Modules**: `functions` (as `func`), `chat.chat` (`ChatRoles`), `core.llms.base_llm` (`BaseModel`), `direct` (`ask`), `.memory_tools` (`MemoryTools`)
- **External Packages**: `sentence_transformers` (`SentenceTransformer`), `chromadb`

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `model_name`: `'all-MiniLM-L6-v2'`
    - `decay_factor`: `0.99`
    - `default_importance`: `5`
    - `output_filename`: `{root}/logs/memory_output_active.md`
- **Environment Lookups**: 
    - `func.get_root_directory()` is used to locate the log directory.