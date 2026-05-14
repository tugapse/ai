## 1. Architectural Role
`ContextSentinel` acts as a proactive context-management layer designed to prevent LLM context window overflow. It monitors token pressure using a heuristic approach, triggers a distillation process via an LLM connector to convert heavy tool outputs into dense technical facts, and archives these facts into [modules/memory/vector_memory.md](modules/memory/vector_memory.md) before pruning the active conversation history to maintain a lean, high-signal state for the agent.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `threshold` (Default: `0.8`)  Percentage of context utilization that triggers compression.
- `max_tokens` (Default: `20000`)  The hard hardware limit of the local engine.
- `buffer` (Default: `1024`)  Safety margin to prevent hitting hard limits.
- `est_tokens_divisor` (Default: `3.2`)  Heuristic character-to-token ratio.
- `distillation_size_threshold` (Default: `2000`)  Character length threshold for triggering tool output distillation.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ContextSentinel` | Class | Orchestrates context monitoring, distillation, and LTM archiving. |
| `enforce_limits` | Method | Calculates pressure and performs "memory surgery" (distillation + pruning) if threshold is exceeded. |
| `_summarize_data` | Method | Executes a blocking LLM call to transform raw data into a dense technical fact sheet. |

## 4. Execution Logic & Flow
- **Initialization**: Sets up the `connector` (LLM interface), `threshold` (trigger point), `max_tokens` (capacity), and `buffer` (safety margin).
- **Data Path**: 
    1. **Input**: `payload` (current state), `memory_manager` (agent state), `vector_memory` (archive target).
    2. **Pressure Calculation**: Estimates tokens via `len(json.dumps(payload)) / 3.2` and compares against `max_tokens - buffer`.
    3. **Decision**: If `pressure < threshold`, returns original payload immediately.
    4. **Distillation (If High Pressure)**: 
        - Iterates `agent_memory.messages_received`.
        - Identifies "SYSTEM" messages containing large `result` blocks.
        - Calls `_summarize_data` to generate a fact sheet.
        - Commits distilled content to `vector_memory`.
        - Replaces raw `result` with a `summary` and `metadata`.
    5. **Pruning**: Truncates `agent_memory.history` to the most recent 3 turns.
    6. **Output**: Rebuilds the `payload` with updated `recent_outcomes`, `messages_received`, and `conversation_history`.
- **Conditional Branching**: 
    - `pressure < self.threshold`: Skip all operations.
    - `len(json.dumps(msg["result"])) > 2000`: Only distill specific high-volume tool outputs.

## 5. Resource Dependencies
- **Standard Libraries**: `json`, `typing`
- **Internal Modules**: 
    - [functions](functions.md)
    - [color](color.md)
- **External Packages**: None identified.