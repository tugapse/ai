## 1. Architectural Role
Acts as a service-oriented interface layer that exposes long-term memory capabilities (retrieval and synthesis) as executable tools for an agent registry.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `MemoryTools` | Class | Orchestrates interaction between the agent and the `vector_memory` instance. |
| `__init__` | Method | Assigns an external `vector_memory_instance` to the class state. |
| `get_tools` | Method | Returns a dictionary mapping string identifiers to internal method references. |
| `query_memory` | Method | Executes semantic searches via `vector_memory.retrieve_memories` based on provided query strings. |
| `trigger_reflection` | Method | Commands the `vector_memory` instance to perform high-level architectural synthesis. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. The `MemoryTools` instance is instantiated.
    2. The `vector_memory` attribute is assigned the provided `vector_memory_instance` (or `None`).
- **Data Path**:
    - **Query Flow**: `kwargs` (input) $\rightarrow$ `query_memory` $\rightarrow$ extraction of `query` and `top_k` $\rightarrow$ `vector_memory.retrieve_memories` $\rightarrow$ `memories` (list) $\rightarrow$ structured `Dict` (output).
    - **Reflection Flow**: `trigger_reflection` $\rightarrow$ `vector_memory.trigger_reflection()` $\rightarrow$ status `Dict` (output).
- **Conditional Branching**:
    - **Memory Availability**: If `self.vector_memory` is falsy, both `query_memory` and `trigger_reflection` return a `FAILED` status.
    - **Query Validation**: In `query_memory`, if neither `query` nor `search` keys exist in `kwargs`, a `FAILED` status is returned.
    - **Result Presence**: In `query_memory`, if `memories` is empty, a `SUCCESS` status is returned with an empty list and a "No matches found" note.
    - **Error Handling**: Any exception during execution is caught, logged via `func.error`, and returned as a `FAILED` status containing the error string.

## 4. Resource Dependencies
- **Standard Libraries**: `typing` (`Dict`, `Any`, `Optional`, `Callable`)
- **Internal Modules**: `functions` (aliased as `func`), `tools.agent_tools` (aliased as `tool`)
- **External Packages**: None explicitly imported (relies on passed `vector_memory_instance`)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `top_k` default value: `3`
- **Environment Lookups**: None