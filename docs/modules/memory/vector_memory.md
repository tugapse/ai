## 1. Architectural Role
`vector_memory.py` serves as the Long-Term Memory (LTM) engine, providing a high-density retrieval-augmented generation (RAG) subsystem. It orchestrates the transformation of raw conversational data into structured, vector-embedded knowledge using semantic similarity search. The module manages the lifecycle of a memoryfrom importance rating and embedding generation via `SentenceTransformer` to persistent storage in `ChromaDB` and periodic cognitive synthesis (reflection) to distill insights and prevent context window saturation. It relies on [base_llm.md](core/llms/base_llm.md) for semantic analysis and [memory_tools.md](modules/memory/memory_tools.md) for agentic interaction.

## 2. Environment & Configuration
**Environment Lookups:**
- `func.get_root_directory()`  Retrieves system root to define log paths for LLM execution.

**Hardcoded Constants:**
- `model_name` (Default: `'all-MiniLM-L6-v2'`)  The specific SentenceTransformer model used for vector generation.
- `db_path` (Default: `"./agent_ltm_db"`)  The local filesystem directory for persistent ChromaDB storage.
- `decay_factor` (Default: `0.99`)  The coefficient used in the exponential decay function for recency scoring.
- `memory_type` (Default: `"observation"`)  The default classification for new memory entries.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | Class defining the interface for converting text to high-dimensional vectors. |
| `LanguageModelProvider` | Class | Abstract interface for semantic importance rating and memory distillation. |
| `VectorDBProvider` | Class | Abstract interface for vector persistence (upsert) and similarity retrieval (query). |
| `SentenceTransformerEmbeddingProvider` | Class | Implementation of `EmbeddingProvider` using local transformer models. |
| `LLMProvider` | Class | Implementation of `LanguageModelProvider` using an LLM to perform qualitative analysis. |
| `ChromaDBProvider` | Class | Implementation of `VectorDBProvider` using a persistent ChromaDB collection. |
| `VectorMemory` | Class | The primary orchestrator managing embedding, storage, retrieval, and reflection logic. |
| `add_memory` | Func | Encapsulates content, generates embeddings/importance, and persists to DB. |
| `retrieve_memories` | Func | Performs vector similarity search combined with recency/importance heuristic scoring. |
| `trigger_reflection` | Func | Triggers the LLM to synthesize recent memories into high-level "reflection" insights. |

## 4. Execution Logic & Flow
- **Initialization**: 
    - Instantiates `ChromaDBProvider` with a session-specific hashed collection name.
    - Loads the `SentenceTransformer` model for embeddings.
    - Configures weight coefficients for the multi-factor ranking heuristic (recency, importance, relevance).
- **Data Path (Ingestion)**: 
    - Input: Raw string content $\rightarrow$ `LLMProvider.rate_importance` $\rightarrow$ `SentenceTransformerEmbeddingProvider.embed` $\rightarrow$ `ChromaDBProvider.upsert`.
- **Data Path (Retrieval)**: 
    - Input: Query string $\rightarrow$ Vector embedding $\rightarrow$ `ChromaDBProvider.query` (Similarity) $\rightarrow$ Heuristic Re-ranking (Recency $\times$ Importance $\times$ Relevance) $\rightarrow$ Sorted List of top-$k$ strings.
- **Conditional Branching**: 
    - If `llm` is provided, importance is dynamically rated; otherwise, defaults to `5`.
    - `trigger_reflection` only executes if the retrieved memory buffer exceeds the threshold ($k < 5$).
    - Error handling in `_execute_llm_call` falls back to empty strings if file I/O or LLM calls fail.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `time`, `re`, `hashlib`, `typing`, `abc`
- **Internal Modules**: 
    - [functions](functions.md)
    - [chat.chat](chat/chat.md)
    - [core.llms.base_llm](core/llms/base_llm.md)
    - [direct](direct.md)
    - [modules.memory.memory_tools](modules/memory/memory_tools.md)
- **External Packages**: `sentence-transformers`, `chromadb`