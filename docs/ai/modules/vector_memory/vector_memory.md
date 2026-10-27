## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | VectorMemory |
| Source file | vector_memory.py |

The **VectorMemory** component serves as the Long-Term Memory (LTM) subsystem of the agent, providing a mechanism for persistent storage, semantic retrieval, and cognitive synthesis of information. It bridges the gap between transient conversational context and permanent knowledge by transforming raw observations into structured, vector-embedded data points.

**Functional Mission**
The primary responsibility of **VectorMemory** is to manage the lifecycle of information through three distinct phases: archival (embedding and storing observations), retrieval (semantic querying with multi-factor ranking), and reflection (distilling raw data into high-level insights). It solves the problem of context window limitations and information decay by ensuring that only the most relevant, important, and recent information is surfaced during agent reasoning.

**System Context & Integration**
This component acts as a specialized data provider for the agent's cognitive loop. It integrates with [BaseModel](/docs/ai/core/llms/base_llm.md) via the `LLMProvider` to perform semantic importance rating and recursive reflection. It utilizes [MemoryTools](/docs/ai/modules/vector_memory/memory_tools.md) to expose its capabilities to the agent's toolset. When the agent requires historical context, **VectorMemory** performs a weighted retrieval process, combining semantic relevance, temporal recency, and importance scores to return a curated list of memories.

- **INTERNAL REFERENCES**: 
    - [MemoryTools](/docs/ai/modules/vector_memory/memory_tools.md)
    - [BaseModel](/docs/ai/core/llms/base_llm.md)
    - [ChatRoles](/docs/ai/chat/chat.md)
    - [ask](/docs/ai/direct.md)

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `model_name` (Default: `'all-MiniLM-L6-v2'`)  The identifier for the SentenceTransformer embedding model.
- `db_path` (Default: `"./agent_ltm_db"`)  The local filesystem path for the ChromaDB persistent storage.
- `decay_factor` (Default: `0.99`)  The multiplier used in the exponential decay calculation for recency scoring.
- `importance_default` (Default: `5`)  The fallback importance score when LLM evaluation fails.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `EmbeddingProvider` | Class (ABC) | Abstract interface for text-to-vector transformation. |
| `LanguageModelProvider` | Class (ABC) | Abstract interface for LLM-based cognitive tasks (rating/summarization). |
| `VectorDBProvider` | Class (ABC) | Abstract interface for vector database operations (upsert/query). |
| `SentenceTransformerEmbeddingProvider` | Class | Concrete implementation of embedding using `sentence-transformers`. |
| `LLMProvider` | Class | Concrete implementation of cognitive logic using an injected `BaseModel`. |
| `ChromaDBProvider` | Class | Concrete implementation of vector storage using `chromadb`. |
| `VectorMemory` | Class | The primary orchestrator managing the memory lifecycle and retrieval logic. |
| `add_memory` | Method | Encapsulates content into metadata, embeds it, and persists it to the DB. |
| `retrieve_memories` | Method | Performs semantic search and applies weighted ranking (recency/importance/relevance). |
| `trigger_reflection` | Method | Executes a synthesis loop to convert recent memories into permanent insights. |
| `_calculate_recency_score` | Method | Computes a temporal decay score based on the time elapsed since last access. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. Instantiates `ChromaDBProvider` with a session-specific hashed collection name.
    2. Initializes `SentenceTransformerEmbeddingProvider` for embeddings.
    3. Sets up `LLMProvider` if a `BaseModel` is provided.
    4. Configures weighting coefficients for the retrieval algorithm.
- **Data Path (Archival)**: 
    `Input Content` $\rightarrow$ `LLM Importance Rating` $\rightarrow$ `SentenceTransformer Embedding` $\rightarrow$ `SHA256 ID Generation` $\rightarrow$ `Metadata Construction` $\rightarrow$ `ChromaDB Upsert`.
- **Data Path (Retrieval)**: 
    `Query String` $\rightarrow$ `Query Embedding` $\rightarrow$ `ChromaDB Vector Search` $\rightarrow$ `Score Calculation (Recency $\times$ W + Importance $\times$ W + Relevance $\times$ W)` $\rightarrow$ `Ranked Content List`.
- **Conditional Branching**:
    - **LLM Failure**: If `rate_importance` or `summarize_and_reflect` fails, the system defaults to a neutral importance score (5) or returns empty lists to prevent execution crashes.
    - **Dependency Check**: During `VectorMemory` init, it attempts to import `sentence_transformers` and `chromadb`, logging an error if missing.
    - **Reflection Threshold**: `trigger_reflection` only proceeds if the retrieved recent memory count is $\ge 5$.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `time`, `re`, `hashlib`, `typing`, `abc`
- **Internal Modules**: 
    - [ai.functions](/docs/ai/functions.md)
    - [ai.chat.chat.ChatRoles](/docs/ai/chat/chat.md)
    - [ai.core.llms.base_llm.BaseModel](/docs/ai/core/llms/base_llm.md)
    - [ai.direct.ask](/docs/ai/direct.md)
    - [ai.modules.vector_memory.memory_tools.MemoryTools](/docs/ai/modules/vector_memory/memory_tools.md)
- **External Packages**: `sentence-transformers`, `chromadb`