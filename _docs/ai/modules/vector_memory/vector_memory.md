## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| VectorMemory | ai/modules/vector_memory/vector_memory |

This component is the central orchestrator for the system's long-term memory management. Its primary responsibility is to encapsulate the entire memory lifecycle: transforming raw text into dense vector embeddings, persistently storing these vectors in a database, retrieving relevant information based on similarity, and synthesizing high-level knowledge through reflection. It solves the problem of ephemeral context by creating a durable, searchable knowledge base for the agent.

It functions as a high-level service layer within the application architecture. It coordinates the functionality of specialized providers—such as [EmbeddingProvider](/ai/modules/vector_memory/vector_memory.md) implementations like [SentenceTransformerEmbeddingProvider](/ai/modules/vector_memory/vector_memory.md), the [VectorDBProvider](/ai/modules/vector_memory/vector_memory.md) implementation [ChromaDBProvider](/ai/modules/vector_memory/vector_memory.md), and the [LanguageModelProvider](/ai/modules/vector_memory/vector_memory.md) implementation [LLMProvider](/ai/modules/vector_memory/vector_memory.md)—to provide a unified, robust interface for memory operations.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| VectorMemory | Class | Manages the entire lifecycle of long-term memory, including embedding, storage, retrieval, and knowledge synthesis (reflection). |
| add_memory | Method | Processes new content, embeds it, scores it, and stores it in the vector database. |
| retrieve_memories | Method | Retrieves and ranks memories based on relevance, importance, and recency. |
| trigger_reflection | Method | Initiates the knowledge synthesis process by summarizing recent memories using the LLM. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `VectorMemory` class aggregates three primary components: an embedder (using `SentenceTransformerEmbeddingProvider`), a database interface (`ChromaDBProvider`), and an LLM interface (`LLMProvider`). Memory addition involves embedding content, retrieving an importance score from the LLM, and upserting the data into ChromaDB. Retrieval queries first embed the user input, then fetch candidates from ChromaDB, and finally ranks these candidates using a weighted formula combining similarity (relevance), LLM-derived importance, and a calculated recency score.
- **Side Effects:** The code extensively interacts with the filesystem by reading and writing to log files (via `ask` in `LLMProvider`), and it maintains persistent state within the vector database (ChromaDB).
- **Error Handling:** The `LLMProvider` implements fallback mechanisms for scoring (defaulting to 5) and handles general exceptions during LLM execution, logging the error and returning an empty string. The `VectorMemory` constructor attempts to catch `ImportError` if required dependencies are missing.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `time`, `re`, `hashlib`, `typing`, `abc`, `sentence-transformers`, `chromadb`.
- **Internal:** [ai.functions](/ai/functions.md), [ai.chat.chat](/ai/chat/chat.md), [ai.core.llms.base_llm](/ai/core/llms/base_llm.md), [ai.direct.ask](/ai/direct.md), [ai.modules.vector_memory.memory_tools](/ai/modules/vector_memory/memory_tools.md).