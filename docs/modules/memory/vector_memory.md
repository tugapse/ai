## 1. Architectural Role
Provides a long-term memory system that integrates vector embeddings for retrieval, a vector database for persistence, and LLM-driven reflection for synthesizing raw memories into high-level insights.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `EmbeddingProvider` | Class | Abstract base for text-to-vector conversion. |
| `LanguageModelProvider` | Class | Abstract base for importance rating and memory reflection. |
| `VectorDBProvider` | Class | Abstract base for vector storage and similarity querying. |
| `SentenceTransformerEmbeddingProvider` | Class | Implementation of `EmbeddingProvider` using `sentence-transformers`. |
| `LLMProvider` | Class | Implementation of `LanguageModelProvider` using a provided connector. |
| `ChromaDBProvider` | Class | Implementation of `VectorDBProvider` using `chromadb` with session-based collection hashing. |
| `VectorMemory` | Class | Orchestrator for memory lifecycle: adding, retrieving, and reflecting on memories. |
| `VectorMemory.add_memory` | Method | Processes content via LLM importance rating and embedding, then persists to DB. |
| `VectorMemory.retrieve_memories` | Method | Fetches and ranks memories using a weighted score of relevance, recency, and importance. |
| `VectorMemory.trigger_reflection` | Method | Extracts key patterns from recent memories and archives them as "reflection" type memories. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. `ChromaDBProvider` initializes a persistent client and creates/gets a collection based on an MD5 hash of the `session_id`.
    2. `SentenceTransformerEmbeddingProvider` loads the specified transformer model into memory.
    3. `VectorMemory` instantiates the DB provider, embedder, and optionally an `LLMProvider`, then initializes `MemoryTools`.
- **Data Path (Memory Addition)**: 
    `content` $\rightarrow$ `LLMProvider.rate_importance` $\rightarrow$ `SentenceTransformerEmbeddingProvider.embed` $\rightarrow$ SHA-256 Hash (ID generation) $\rightarrow$ `ChromaDBProvider.upsert`.
- **Data Path (Memory Retrieval)**: 
    `query` $\rightarrow$ `SentenceTransformerEmbeddingProvider.embed` $\rightarrow$ `ChromaDBProvider.query` $\rightarrow$ Composite Scoring (Recency $\times$ Weight + Importance $\times$ Weight + Relevance $\times$ Weight) $\rightarrow$ Sorted List of `content`.
- **Conditional Branching**:
    - **Dependency Check**: If `sentence-transformers` or `chromadb` are missing, imports are set to `None` and `ImportError` is raised during provider instantiation.
    - **LLM Availability**: `add_memory` and `trigger_reflection` check if `self.llm` is initialized before attempting importance rating or synthesis.
    - **Query Validation**: `retrieve_memories` returns an empty list immediately if the query string is empty.

## 4. Resource Dependencies
- **Standard Libraries**: `time`, `re`, `hashlib`, `typing`, `abc`
- **Internal Modules**: `functions`, `.memory_tools`
- **External Packages**: `sentence-transformers`, `chromadb`

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `all-MiniLM-L6-v2`: Default embedding model.
    - `5`: Default importance rating if LLM fails or is absent.
    - `0.99`: Default `decay_factor` for recency calculation.
    - `./agent_ltm_db`: Default database storage path.
    - `1.0`: Default weights for recency, importance, and relevance.