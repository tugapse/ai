## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **MemoryTools** | [src/ai/modules/vector_memory/memory_tools.py](/src/ai/modules/vector_memory/memory_tools.py) |

The `MemoryTools` class provides a service-oriented interface for managing an agent's long-term memory (LTM). It acts as a bridge between the active agent and a persistent ChromaDB vector store, allowing the agent to perform semantic searches and trigger knowledge synthesis.

This component is part of the vector memory module and is designed to be registered as a set of tools for an agent. Its primary responsibility is to mitigate context window overflow by allowing the agent to recall specific technical context or historical data via semantic queries rather than re-scanning all available files.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `MemoryTools(vector_memory_instance)` | Class | Initializes the toolset with a provided `VectorMemory` instance. |
| `get_tools()` | Method | Returns a dictionary mapping tool names (`query_memory`, `trigger_reflection`) to their respective callable methods for registry use. |
| `query_memory(**kwargs)` | Method | Performs a semantic search in LTM. Accepts `query` (str) and `top_k` (int). Returns a dictionary containing search results and status. |
| `trigger_reflection(**kwargs)` | Method | Triggers the `VectorMemory` instance to synthesize recent observations into high-level architectural insights and "Project DNA". |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - `query_memory` extracts search parameters from `kwargs`, defaulting `top_k` to 3. It delegates the heavy lifting to the `retrieve_memories` method of the injected `vector_memory` instance.
    - `trigger_reflection` is a pass-through method that invokes the `trigger_reflection` logic on the underlying `vector_memory` object.
- **Side Effects:** 
    - Interacts with the `vector_memory` instance, which typically involves I/O operations with a ChromaDB vector database.
    - Logs execution steps and errors via the `ai.functions` logging utility.
- **Error Handling:** 
    - Validates the presence of the `vector_memory` instance before execution.
    - Catches exceptions during tool execution, logging them via `func.error` and returning a dictionary with `status: "FAILED"` and the error message to prevent agent runtime crashes.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `typing` (Dict, Any, Optional, Callable).
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.tools.agent_tools](/AgentDocs/ai/tools/agent_tools.md)