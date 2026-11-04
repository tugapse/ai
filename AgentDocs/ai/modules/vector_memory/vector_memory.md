## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **VectorMemory** | [src/ai/modules/vector_memory/vector_memory.py](/src/ai/modules/vector_memory/vector_memory.py) |

The `VectorMemory` component provides a long-term memory system for the agent, utilizing vector embeddings and a vector database to store, retrieve, and synthesize information. It solves the problem of information decay and context window limitations by allowing the agent to persist observations and reflections, then retrieve them based on semantic relevance, importance, and recency.

This component acts as a core cognitive service within the application architecture. It integrates with [BaseModel](/AgentDocs/ai/core/llms/base_llm.md) for semantic reasoning (rating importance and synthesizing insights) and utilizes [MemoryTools](/AgentDocs/ai/modules/vector_memory/memory_tools.md) to expose memory management capabilities to the agent.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `EmbeddingProvider` | Abstract Class | Interface for generating vector embeddings from text. |
| `LanguageModelProvider` | Abstract Class | Interface for LLM-based tasks like importance rating and synthesis. |
| `VectorDBProvider` | Abstract Class | Interface for interacting with a Vector Database (upsert/query). |
| `SentenceTransformerEmbeddingProvider` | Class | Implementation of `EmbeddingProvider` using `sentence-transformers`. |
| `LLMProvider` | Class | Implementation of `LanguageModelProvider` using a `BaseModel`. |
| `ChromaDBProvider` | Class | Implementation of `VectorDBProvider` using `chromadb`. |
| `VectorMemory` | Class | The primary controller managing the memory lifecycle. |
| `VectorMemory.add_memory()` | Method | Embeds and stores content with metadata (source, type, importance). |
| `VectorMemory.retrieve_memories()` | Method | Performs a weighted search (recency, importance, relevance) to return ranked memories. |
| `VectorMemory.trigger_reflection()` | Method | Synthesizes recent memories into high-level insights via the LLM. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **Retrieval Scoring:** Uses a weighted sum algorithm: `(recency_weight * recency) + (importance_weight * importance) + (relevance_weight * relevance)`. Recency is calculated using an exponential decay model based on the `last_accessed_at` timestamp.
    - **Reflection:** Pulls a large slice of recent memories and uses a specialized LLM prompt to extract new facts and preferences, which are then re-inserted into the database as `reflection` type memories.
    - **Embedding:** Uses `SentenceTransformer` to convert text into high-dimensional vectors for semantic search.
- **Side Effects:** 
    - **Filesystem:** Writes persistent vector data to the specified `db_path` via ChromaDB.
    - **Filesystem:** Writes LLM execution logs to `{root_directory}/logs/memory_output_active.md`.
    - **Network/LLM:** Makes calls to the underlying LLM provider via [ask](/AgentDocs/ai/direct.md).
- **Error Handling:** 
    - If `sentence-transformers` or `chromadb` are missing, an `ImportError` is raised or logged.
    - LLM importance rating failures default to a score of `5`.
    - LLM execution failures are caught, logged via `func.error`, and return an empty string.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No specific environment variables are required, though `db_path` is configurable during initialization.

**Module Dependencies:**
- **Standard/External:** `os`, `time`, `re`, `hashlib`, `typing`, `abc`, `sentence-transformers`, `chromadb`.
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.chat.chat.ChatRoles](/AgentDocs/ai/chat/chat.md)
    - [ai.core.llms.base_llm.BaseModel](/AgentDocs/ai/core/llms/base_llm.md)
    - [ai.direct.ask](/AgentDocs/ai/direct.md)
    - [ai.modules.vector_memory.memory_tools.MemoryTools](/AgentDocs/ai/modules/vector_memory/memory_tools.md)