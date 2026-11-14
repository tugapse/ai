## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| MemoryTools | ai/modules/vector_memory/memory_tools.md |

This component provides a service-oriented interface for managing an agent's long-term memory, primarily by acting as a wrapper around a persistent vector store implementation. Its core responsibility is to expose standardized methods for querying past knowledge and archiving new insights into the agent's memory bank.

As a service layer, `MemoryTools` sits between the core agent logic and the specific persistence mechanism (the `VectorMemory` instance). It centralizes memory operations, allowing other parts of the system to interact with memory using consistent methods like `query_memory` or `trigger_reflection` without needing direct knowledge of the underlying database or memory structure.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| MemoryTools | Class | Manages interaction with the vector memory system. |
| get_tools | Method | Maps internal memory methods to a dictionary suitable for external tool registration. |
| query_memory | Method | Retrieves relevant memory fragments based on a natural language query. |
| trigger_reflection | Method | Archives a summary of recent learning into long-term memory for future retrieval. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `query_memory` method validates the presence of a query and calls `self.vector_memory.retrieve_memories`. It handles the case where no memories are found, returning a specific success status with an empty list. `trigger_reflection` delegates directly to `self.vector_memory.trigger_reflection()`.
- **Side Effects:** Interacts with the external state managed by `self.vector_memory`, which is assumed to connect to a persistent ChromaDB vector store (reading/writing to persistent storage).
- **Error Handling:** Both public methods include robust `try...except` blocks. They catch general exceptions, log the failure using `ai.functions.error`, and return a standardized dictionary indicating a "FAILED" status along with the error message.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `typing`
- **Internal:** [ai.functions](/ai/functions.md), [ai.tools.base](/ai/tools/base.md)