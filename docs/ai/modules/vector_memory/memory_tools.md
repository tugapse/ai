## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | MemoryTools |
| Source file | memory_tools.py |

The **MemoryTools** class serves as a service-oriented interface layer that bridges the gap between an active agent and the persistent long-term memory (LTM) storage system. It acts as a specialized toolset that can be registered within an agent's capabilities, allowing the agent to perform semantic retrieval and high-level knowledge synthesis through standardized method calls.

**Functional Mission**
The primary responsibility of **MemoryTools** is to provide a controlled, high-level API for an agent to interact with a `VectorMemory` instance. It solves the problem of context window management by allowing the agent to "recall" specific technical details or "reflect" on recent activities to create structured knowledge, rather than relying on a continuous, unmanaged stream of raw conversation history.

**System Context & Integration**
This component functions as a bridge between the agentic logic and the [VectorMemory](/docs/ai/modules/vector_memory/vector_memory.md) module. It is designed to be consumed by the [Agent](/docs/ai/agents/agent.md) via a tool registry. When an agent encounters a need for historical context or needs to consolidate information, it invokes `query_memory` or `trigger_reflection`. The results of these operations are then fed back into the agent's context, facilitating a loop of observation, reflection, and retrieval.

- **INTERNAL REFERENCES**: [VectorMemory](/docs/ai/modules/vector_memory/vector_memory.md), [Agent](/docs/ai/agents/agent.md), [agent_tools](/docs/ai/tools/agent_tools.md).

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `top_k` (Default: `3`)  The default number of memory fragments to retrieve during a semantic search.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `MemoryTools` | Class | Orchestrates the mapping of memory-related actions to the underlying vector store. |
| `get_tools` | Method | Returns a dictionary mapping string identifiers to class methods for tool registry integration. |
| `query_memory` | Method | Performs semantic search within the vector store to retrieve specific historical context. |
| `trigger_reflection` | Method | Initiates a synthesis process in the vector memory to convert logs into structured insights. |

## 4. Execution Logic & Flow
- **Initialization**: The class is instantiated with an optional `vector_memory_instance`. If no instance is provided, the tools will be effectively disabled, returning error statuses upon execution.
- **Data Path (query_memory)**: 
    1. **Input**: Receives `kwargs` containing `query` (or `search`) and an optional `top_k`.
    2. **Validation**: Checks if `vector_memory` is present and if a query string exists.
    3. **Processing**: Passes the query and `top_k` integer to `self.vector_memory.retrieve_memories`.
    4. **Output**: Returns a dictionary containing `status`, `results` (list of memories), `query`, and `count`.
- **Data Path (trigger_reflection)**:
    1. **Input**: None required.
    2. **Validation**: Checks if `vector_memory` is present.
    3. **Processing**: Calls the `trigger_reflection()` method on the `vector_memory` instance.
    4. **Output**: Returns a success/failure dictionary with a status message.
- **Conditional Branching**:
    - If `self.vector_memory` is `None`, both methods return a `FAILED` status with an error message.
    - If `query_memory` finds no matches, it returns a `SUCCESS` status but with an empty results list and a helpful note.
    - Exception handling wraps both primary methods to catch and log errors via `func.error`.

## 5. Resource Dependencies
- **Standard Libraries**: `typing`
- **Internal Modules**: 
    - [ai.functions](/docs/ai/functions.md)
    - [ai.tools.agent_tools](/docs/ai/tools/agent_tools.md)
- **External Packages**: None identified.