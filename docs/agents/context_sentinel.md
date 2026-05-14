## 1. Architectural Role
Manages context window pressure by distilling heavy tool outputs into technical fact sheets, archiving them to Long-Term Memory (LTM), and pruning conversation history to maintain operational stability.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ContextSentinel` | Class | Orchestrates context monitoring, data distillation, and memory pruning. |
| `__init__` | Method | Initializes thresholds, token limits, and safety buffers. |
| `enforce_limits` | Method | Calculates context pressure and executes memory surgery if the threshold is exceeded. |
| `_summarize_data` | Method | Performs a blocking LLM request to transform raw data into a dense technical summary. |

## 3. Execution Logic & Flow
- **Initialization**: An instance is created with a `connector` (LLM interface), a `threshold` (trigger percentage), `max_tokens` (hardware limit), and a `buffer` (safety margin).
- **Data Path**: 
    1. `enforce_limits` receives a `payload` (current state) and `agent_memory`.
    2. `est_tokens` is calculated via JSON serialization of the payload.
    3. If `pressure` > `threshold`, `_summarize_data` is invoked.
    4. `_summarize_data` sends a structured prompt to `self.connector.send_raw_request`.
    5. The resulting `distilled` string is sent to `vector_memory.add_memory`.
    6. The original `agent_memory.messages_received` entry is replaced with a summary object.
    7. `agent_memory.history` is sliced to the last 3 turns.
    8. A new `payload` is reconstructed from the pruned memory and returned.
- **Conditional Branching**:
    - **Pressure Check**: If `pressure < self.threshold`, the original `payload` is returned immediately with `False`.
    - **Content Heavy Check**: Inside the message loop, distillation only triggers if a `SYSTEM` message contains a `result` key with a JSON string length > 2000.
    - **Vector Memory Check**: Distillation results are only archived to `vector_memory` if the `vector_memory` argument is not `None`.

## 4. Resource Dependencies
- **Standard Libraries**: `json`, `typing`
- **Internal Modules**: `functions` (as `func`), `color` (as `Color`)
- **External Packages**: None explicitly imported (relies on passed `connector` and `memory_manager` interfaces)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `3.2`: Token estimation divisor (characters per token).
    - `2000`: Minimum character length for tool output distillation.
    - `3`: Number of conversation history turns retained after pruning.
    - `"SENTINEL_{agent_name}"`: Source identifier for vector memory.
- **Environment Lookups**: None.