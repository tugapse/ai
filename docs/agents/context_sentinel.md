## 1. Architectural Role

**Functional Mission**
The **ContextSentinel** is a specialized memory management agent designed to mitigate context window overflow in LLM-driven workflows. Its primary mission is to monitor "context pressure"the ratio of current payload size to the hardware's maximum token capacityand perform proactive "memory surgery" when thresholds are breached. It solves the problem of information loss and performance degradation by distilling heavy, raw tool outputs (such as logs or source code) into dense technical fact sheets before they are pruned from the active context.

**System Context & Integration**
This component acts as a gatekeeper between the active execution state and long-term storage. It integrates deeply with [memory_manager](/docs/agents/memory_manager.md) to manipulate agent history and utilizes [vector_memory](/docs/modules/memory/vector_memory.md) to archive distilled observations. By intercepting heavy payloads, it ensures that while the immediate conversation history is pruned to maintain a lean state, the critical technical insights are preserved in a searchable format, facilitating a seamless transition from short-term working memory to long-term knowledge retrieval.

## 2. Environment & Configuration

**Environment Lookups:**
No environment lookups identified.

**Hardcoded Constants:**
- `threshold` (Default: `0.8`)  The percentage of context usage that triggers the compression/archiving logic.
- `max_tokens` (Default: `20000`)  The hardware-defined context limit of the local GGUF engine.
- `buffer` (Default: `1024`)  A safety margin subtracted from `max_tokens` to prevent hitting hard limits.
- `est_tokens_divisor` (Default: `3.2`)  Heuristic multiplier used to estimate token count from character length.
- `distillation_size_threshold` (Default: `2000`)  Character length threshold for triggering distillation on tool results.
- `history_pruning_limit` (Default: `3`)  The number of recent turns retained in `agent_memory.history` after pruning.

## 3. Interface & API Surface

| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ContextSentinel` | Class | Orchestrates context monitoring, data distillation, and memory pruning. |
| `enforce_limits` | Method | Calculates pressure and executes in-place memory surgery (archiving and pruning). |
| `_summarize_data` | Method | Performs a sequential LLM call to transform raw data into a dense technical fact sheet. |

## 4. Execution Logic & Flow

- **Initialization**: The sentinel is instantiated with a `connector` (for LLM requests), a `threshold` for pressure detection, `max_tokens` for capacity limits, and a `buffer` for safety.
- **Data Path**: 
    1. **Input**: Receives a `payload` (current state), `agent_name`, `memory_manager`, and optional `vector_memory`.
    2. **Pressure Calculation**: Estimates tokens via `len(json.dumps(payload)) / 3.2` and compares against `max_tokens - buffer`.
    3. **Distillation (If Pressure > Threshold)**: 
        - Iterates through `agent_memory.messages_received`.
        - Identifies `SYSTEM` messages containing large `result` objects.
        - Sends raw data to `connector.send_raw_request` via `_summarize_data`.
        - Archives the distilled summary to `vector_memory`.
        - Replaces the heavy `result` in `agent_memory` with a lightweight summary and metadata.
    4. **Pruning**: Truncates `agent_memory.history` to the last 3 turns.
    5. **Output**: Returns a rebuilt, lean `payload` and a boolean flag indicating if surgery occurred.
- **Conditional Branching**:
    - If `pressure < threshold`: Returns the original payload immediately without modification.
    - If `vector_memory` is provided: Executes the archival step; otherwise, skips vector storage.
    - If `msg.get("from") == "SYSTEM"` and `len(json.dumps(msg["result"])) > 2000`: Triggers the distillation logic for that specific message.

## 5. Resource Dependencies

- **Standard Libraries**: `json`, `typing`
- **Internal Modules**: 
    - [functions](/docs/functions.md)
    - [color](/docs/color.md)
- **External Packages**: None identified.