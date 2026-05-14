## 1. Architectural Role
Acts as a service-oriented interface layer that exposes long-term memory (LTM) capabilities to an agent via a tool registry. It abstracts complex vector database operations into high-level semantic actions`query_memory` for retrieval and `trigger_reflection` for knowledge synthesisfacilitating interaction with the [modules/memory/vector_memory.md](modules/memory/vector_memory.md) instance. This component is essential for preventing context window overflow by allowing the agent to selectively recall distilled information rather than re-processing raw data.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `top_k` (Default: `3`)  The default number of memory fragments to retrieve during a semantic search.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `MemoryTools` | Class | Orchestrates the mapping of memory-related logic to the agent's tool registry. |
| `get_tools` | Method | Returns a dictionary mapping string identifiers (`query_memory`, `trigger_reflection`) to internal methods. |
| `query_memory` | Method | Performs semantic search via the vector memory instance to retrieve historical context. |
| `trigger_reflection` | Method | Commands the vector memory to execute a synthesis cycle, converting recent logs into structured knowledge. |

## 4. Execution Logic & Flow
- **Initialization**: Receives an optional `vector_memory_instance` and assigns it to `self.vector_memory`.
- **Data Path (query_memory)**: 
    1. Receives `**kwargs` containing `query` (or `search`) and `top_k`.
    2. Validates presence of `vector_memory` and the `query` string.
    3. Passes the string and integer `top_k` to `vector_memory.retrieve_memories`.
    4. Returns a structured dictionary containing the status, results, query string, and count.
- **Data Path (trigger_reflection)**:
    1. Validates `vector_memory` availability.
    2. Invokes `vector_memory.trigger_reflection()`.
    3. Returns a success/failure status message.
- **Conditional Branching**: 
    - If `vector_memory` is `None`, returns a `FAILED` status.
    - If `query` is missing in `query_memory`, returns a `FAILED` status.
    - If `retrieve_memories` returns an empty list, returns `SUCCESS` with a "No matches found" note.

## 5. Resource Dependencies
- **Standard Libraries**: `typing`
- **Internal Modules**: 
    - [functions](functions.md)
    - [tools/agent_tools.md](tools/agent_tools.md)
- **External Packages**: None identified.