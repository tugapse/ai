## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **VectorMemory** | [/src/ai/modules/vector_memory/vector_memory.py](/AgentDocs/ai/modules/vector_memory/vector_memory.md) |

The `VectorMemory` component provides a long-term memory system for AI agents by utilizing vector embeddings and a vector database. It is responsible for transforming raw text into high-dimensional vectors, storing them with rich metadata, and performing intelligent retrieval based on a weighted scoring mechanism that considers relevance, importance, and recency.

This component serves as a core cognitive layer within the application architecture. It enables the agent to move beyond short-term context windows by providing a persistent "knowledge base" of past interactions and observations. It integrates with the LLM layer to perform "reflection"a process where recent memories are synthesized into high-level, actionable insights that are then re-archived as permanent knowledge.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `VectorMemory` | Class | The primary controller for the memory lifecycle. Manages embedding, storage, retrieval, and reflection. |
| `VectorMemory.__init__(...)` | Method | Initializes the system with a `session_id`, optional `llm`, and weights for scoring (`recency`, `importance`, `relevance`). |
| `VectorMemory.add_memory(content, source, memory_type)` | Method | Processes, embeds, and stores a new memory in the vector database. |
| `VectorMemory.retrieve_memories(query, top_k)` | Method | Performs a similarity search and returns a ranked list of memory contents based on weighted scores. |
| `VectorMemory.trigger_reflection(lookback_k)` | Method | Synthesizes recent memories into high-level insights using the LLM and stores them as new 'reflection' memories. |
| `EmbeddingProvider` | Abstract Class | Interface for text-to-vector conversion. |
| `LanguageModelProvider` | Abstract Class | Interface for LLM-based tasks like importance rating and synthesis. |
| `VectorDBProvider` | Abstract Class | Interface for vector database operations (upsert/query). |
| `SentenceTransformerEmbeddingProvider` | Class | Implementation of `EmbeddingProvider` using `sentence-transformers`. |
| `LLMProvider` | Class | Implementation of `LanguageModelProvider` using a `BaseModel`. |
| `ChromaDBProvider` | Class | Implementation of `VectorDBProvider` using `ChromaDB`. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **Scoring Algorithm:** Retrieval uses a multi-factor ranking system: `final_score = (W_r * recency) + (W_i * importance) + (W_v * relevance)`. Recency is calculated using an exponential decay model based on the time elapsed since the memory was last accessed.
    - **Reflection Loop:** The `trigger_reflection` method pulls a broad window of recent memories, sends them to the LLM with a synthesis prompt, and iterates through the resulting bullet points to save them as new memories of type `reflection`.
    - **Hashing:** Memory IDs are generated using SHA-256 hashes of the content to ensure uniqueness and idempotency.
- **Side Effects:**
    - **Filesystem:** Writes persistent vector data to the specified `db_path` via ChromaDB. It also writes LLM interaction logs to `/logs/memory_output_active.md`.
    - **Network/Process:** Executes LLM calls via the `ask` function, which may involve external API calls or local model inference.
- **Error Handling:**
    - If `sentence-transformers` or `chromadb` are missing, an `ImportError` is raised during initialization.
    - LLM importance rating failures default to a score of `5`.
    - LLM execution failures are caught, logged via `func.error`, and return empty strings to prevent system crashes.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No specific environment variables are explicitly required by this module, though the `db_path` and `session_id` are passed during instantiation.

**Module Dependencies:**
- **Standard/External:** `os`, `time`, `re`, `hashlib`, `typing`, `abc`, `sentence-transformers`, `chromadb`.
- **Internal:**
    - [/ai/functions](/AgentDocs/ai/functions.md)
    - [/ai/chat/chat.md](/AgentDocs/ai/chat/chat.md)
    - [/ai/core/llms/base_llm.md](/AgentDocs/ai/core/llms/base_llm.md)
    - [/ai/direct.md](/AgentDocs/ai/direct.md)
    - [/ai/modules/vector_memory/memory_tools.md](/AgentDocs/ai/modules/vector_memory/memory_tools.md)