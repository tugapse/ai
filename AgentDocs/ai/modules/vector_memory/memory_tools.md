## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **MemoryTools** | [src/ai/modules/vector_memory/memory_tools.py](/AgentDocs/ai/modules/vector_memory/memory_tools.md) |

The `MemoryTools` class provides a service-oriented interface for managing an agent's long-term memory (LTM). It acts as a bridge between the active agent and a persistent ChromaDB vector store, allowing the agent to perform semantic searches and trigger knowledge synthesis.

This component is a specialized toolset designed to be registered within the agent's tool registry. It solves the problem of context window limitations by providing a mechanism to recall specific technical context or historical data without requiring the agent to re-scan physical files or maintain massive amounts of raw data in the immediate prompt context.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `MemoryTools(vector_memory_instance)` | Class | Initializes the toolset with a provided `VectorMemory` instance. |
| `get_tools()` | Method | Returns a dictionary mapping tool names (`query_memory`, `trigger_reflection`) to their respective callable methods for registry integration. |
| `query_memory(**kwargs)` | Method | Performs a semantic search against the vector store. Accepts `query` (or `search`) and `top_k` (integer) parameters. Returns a status dictionary with retrieved results. |
| `trigger_reflection(**kwargs)` | Method | Commands the underlying `VectorMemory` to synthesize recent observations into structured, permanent architectural insights. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The class functions as a wrapper around a `VectorMemory` instance. `query_memory` extracts search parameters from keyword arguments and delegates the retrieval to the `vector_memory.retrieve_memories` method. `trigger_reflection` is a pass-through command that initiates a consolidation cycle within the vector storage layer.
- **Side Effects:** 
    - **Logging:** Executes logging via `ai.functions` for tool execution starts and errors.
    - **State Mutation:** `trigger_reflection` triggers an external process that modifies the state of the persistent vector database by archiving new insights.
- **Error Handling:** Both primary methods are wrapped in `try-except` blocks. If the `vector_memory` instance is missing or if an exception occurs during execution, the methods return a dictionary with `{"status": "FAILED", "error": <error_message>}` rather than raising unhandled exceptions, ensuring agent stability.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `typing` (Dict, Any, Optional, Callable).
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.tools.agent_tools](/AgentDocs/ai/tools/agent_tools.md)