## 1. Architectural Role

**Functional Mission**
The **`vector_memory.py`** component serves as the Long-Term Memory (LTM) engine for the agent, providing a sophisticated mechanism for storing, retrieving, and synthesizing information. Its primary mission is to transform transient conversational data into structured, searchable knowledge by utilizing vector embeddings and semantic similarity, effectively solving the problem of context window limitations and information decay.

**System Context & Integration**
This module acts as a bridge between raw interaction data and high-level cognitive synthesis. It integrates with [BaseModel](/docs/core/llms/base_llm.md) to perform semantic reasoning (importance rating and reflection) and utilizes [MemoryTools](/docs/modules/memory/memory_tools.md) to expose its capabilities to the agent. Data flows from the chat interface into the `VectorMemory` via `add_memory`, is persisted in a ChromaDB instance, and is retrieved during query phases to augment the LLM's context. The `trigger_reflection` method provides a periodic distillation loop that converts raw observations into high-level "reflections," ensuring the memory remains dense and relevant.

## 2. Environment & Configuration

**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `model_name` (Default: `'all-MiniLM-L6-v2'`)  The identifier for the SentenceTransformer embedding model.
- `db_path` (Default: `"./agent_ltm_db"`)  The local filesystem path for ChromaDB persistence.
- `decay_factor` (Default: `0.99`)  The multiplier used in the exponential decay calculation for recency scoring.
- `importance_default` (Default: `5`)  The fallback importance score when LLM rating fails.

## 3. Interface & API Surface

| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `EmbeddingProvider` | Class (ABC) | Abstract interface for generating vector embeddings from text. |
| `LanguageModelProvider` | Class (ABC) | Abstract interface for LLM-driven cognitive tasks (rating/summarization). |
| `VectorDBProvider` | Class (ABC) | Abstract interface for vector database CRUD operations. |
| `SentenceTransformerEmbeddingProvider` | Class | Concrete implementation of `EmbeddingProvider` using `sentence-transformers`. |
| `LLMProvider` | Class | Concrete implementation of `LanguageModelProvider` using an injected `BaseModel`. |
| `ChromaDBProvider` | Class | Concrete implementation of `VectorDBProvider` using `chromadb`. |
| `VectorMemory` | Class | The primary orchestrator managing the lifecycle of memories and retrieval logic. |
| `add_memory` | Method | Encapsulates text into a vector, assigns importance, and persists to the DB. |
| `retrieve_memories` | Method | Performs a weighted semantic search combining recency, importance, and relevance. |
| `trigger_reflection` | Method | Executes a synthesis loop to distill recent memories into concise insights. |
| `_calculate_recency_score` | Method | Computes a decay score based on the time elapsed since last access. |

## 4. Execution Logic & Flow

- **Initialization**: 
    1. `VectorMemory` instantiates a `ChromaDBProvider` with a session-specific hashed collection name.
    2. Initializes `SentenceTransformerEmbeddingProvider` to load the local embedding model.
    3. If an LLM is provided, initializes `LLMProvider` to enable cognitive augmentation.
- **Data Path (Storage)**: 
    `Input Text` $\rightarrow$ `LLM Importance Rating` $\rightarrow$ `SentenceTransformer Embedding` $\rightarrow$ `Metadata Construction (timestamp, source, type)` $\rightarrow$ `ChromaDB Upsert`.
- **Data Path (Retrieval)**: 
    `Query String` $\rightarrow$ `Query Embedding` $\rightarrow$ `Vector DB Similarity Search` $\rightarrow$ `Weighted Scoring (Recency $\times$ W1 + Importance $\times$ W2 + Relevance $\times$ W3)` $\rightarrow$ `Ranked Content List`.
- **Conditional Branching**:
    - **LLM Availability**: If `self.llm` is `None`, importance defaults to `5` and reflection is skipped.
    - **Dependency Check**: If `sentence-transformers` or `chromadb` are missing, the module catches `ImportError` and logs a failure via `func.error`.
    - **Reflection Threshold**: `trigger_reflection` only proceeds if the retrieved recent memory count is $\ge 5$.

## 5. Resource Dependencies

- **Standard Libraries**: `os`, `time`, `re`, `hashlib`, `typing`, `abc`
- **Internal Modules**: 
    - [functions](/docs/functions.md)
    - [ChatRoles](/docs/chat/chat.md)
    - [BaseModel](/docs/core/llms/base_llm.md)
    - [ask](/docs/direct.md)
    - [MemoryTools](/docs/modules/memory/memory_tools.md)
- **External Packages**: `sentence-transformers`, `chromadb`