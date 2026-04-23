## 1. Architectural Role
Acts as a service-oriented tool wrapper that exposes `VectorMemory` capabilities (semantic retrieval and reflection) as a registry-compatible interface for an agent.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `MemoryTools` | Class | Encapsulates memory-related tool logic and manages the connection to a vector store. |
| `MemoryTools.__init__` | Method | Binds an optional `vector_memory_instance` to the toolset. |
| `MemoryTools.get_tools` | Method | Returns a dictionary mapping tool names (`query_memory`, `trigger_reflection`) to their method references. |
| `MemoryTools.query_memory` | Method | Performs semantic search against the vector store using a query string and `top_k` limit. |
| `MemoryTools.trigger_reflection` | Method | Commands the vector store to synthesize recent observations into permanent knowledge. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. `MemoryTools` is instantiated.
    2. The `vector_memory_instance` is assigned to `self.vector_memory`.
- **Data Path (query_memory)**: 
    1. **Input**: Receives `**kwargs` (expects `query` or `search` and optional `top_k`).
    2. **Validation**: Checks if `self.vector_memory` exists $\rightarrow$ Checks if a query string is present.
    3. **Processing**: Calls `self.vector_memory.retrieve_memories(query, top_k=top_k)`.
    4. **Output**: Returns a dictionary containing `status`, `results` (list of memories), and metadata.
- **Data Path (trigger_reflection)**:
    1. **Input**: Receives `**kwargs` (none required).
    2. **Validation**: Checks if `self.vector_memory` exists.
    3. **Processing**: Calls `self.vector_memory.trigger_reflection()`.
    4. **Output**: Returns a success/failure status dictionary.
- **Conditional Branching**:
    - **Availability Check**: If `self.vector_memory` is `None`, both tools return a `FAILED` status immediately.
    - **Query Resolution**: `query_memory` attempts to resolve the search term from either the `query` key or the `search` key.
    - **Result Handling**: If `retrieve_memories` returns an empty list, a specific "No matches found" note is returned.
    - **Error Handling**: All primary logic is wrapped in `try-except` blocks that route exceptions to `func.error` and return a `FAILED` status.

## 4. Resource Dependencies
- **Standard Libraries**: `typing` (`Dict`, `Any`, `Optional`, `Callable`)
- **Internal Modules**: `functions` (aliased as `func`)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `top_k` default value: `3`
- **Environment Lookups**: None