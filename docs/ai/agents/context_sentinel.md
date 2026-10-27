## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | ContextSentinel |
| Source file | context_sentinel.py |

The **ContextSentinel** serves as a proactive memory management layer designed to prevent context window overflow in LLM-driven agents. It monitors the "pressure" of the current payload by estimating token usage against a defined hardware limit, acting as a gatekeeper for the agent's cognitive capacity.

**Functional Mission**
The primary responsibility of the **ContextSentinel** is to perform "memory surgery" when context pressure exceeds a specific threshold. It solves the problem of information loss and model degradation caused by bloated context windows by distilling heavy tool outputs (such as raw code or logs) into dense technical fact sheets and archiving them to Long-Term Memory (LTM) before pruning the active conversation history.

**System Context & Integration**
This component sits within the agent execution loop, intercepting payloads before they are sent to the LLM. It integrates deeply with [Memory Manager](/docs/ai/agents/memory_manager.md) to access and modify agent state, and optionally interacts with [Vector Memory](/docs/ai/modules/vector_memory/vector_memory.md) to ensure distilled observations are persisted for future retrieval. By transforming raw, high-token data into summarized metadata, it facilitates a seamless transition from short-term active context to long-term semantic storage.

- **INTERNAL REFERENCES**: [Memory Manager](/docs/ai/agents/memory_manager.md), [Vector Memory](/docs/ai/modules/vector_memory/vector_memory.md), [Color](/docs/ai/color.md), [Functions](/docs/ai/functions.md).

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `threshold` (Default: `0.8`)  The percentage of context usage that triggers the compression logic.
- `max_tokens` (Default: `20000`)  The hardware context limit of the local GGUF engine.
- `buffer` (Default: `1024`)  Safety margin subtracted from `max_tokens` to prevent hitting hard limits.
- `3.2` (Heuristic)  Character-to-token estimation ratio used for pressure calculation.
- `2000` (Threshold)  Character length threshold for triggering distillation on tool results.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ContextSentinel` | Class | Orchestrates context monitoring, distillation, and pruning. |
| `enforce_limits` | Method | Calculates pressure and executes memory pruning/archiving if threshold is met. |
| `_summarize_data` | Method | Performs a blocking LLM call to convert raw data into a dense technical fact sheet. |

## 4. Execution Logic & Flow
- **Initialization**: Sets up the `connector` (LLM interface), `threshold`, `max_tokens`, and `buffer` to establish the operational boundaries for context management.
- **Data Path**: 
    1. **Input**: Receives `agent_name`, `memory_manager`, `payload`, and optional `vector_memory`.
    2. **Pressure Calculation**: Estimates tokens via `len(json.dumps(payload)) / 3.2` and compares against `max_tokens - buffer`.
    3. **Distillation (If Pressure > Threshold)**: 
        - Iterates through `messages_received`.
        - Identifies `SYSTEM` messages containing large `result` objects (> 2000 chars).
        - Calls `_summarize_data` to generate a technical summary.
        - If `vector_memory` is provided, archives the summary as `distilled_observation`.
        - Replaces the raw `result` in the agent's memory with a summarized metadata object.
    4. **Pruning**: Truncates `agent_memory.history` to the most recent 3 turns.
    5. **Output**: Returns a rebuilt `payload` containing the lean state and a boolean indicating if surgery was performed.
- **Conditional Branching**:
    - If `delta <= 0`: Logs a warning and returns the original payload.
    - If `pressure < threshold`: Returns the original payload without modification.
    - If `msg.get("from") == "SYSTEM"` and `result` is large: Triggers the distillation sub-routine.

## 5. Resource Dependencies
- **Standard Libraries**: `json`, `typing`
- **Internal Modules**: 
    - [Functions](/docs/ai/functions.md)
    - [Color](/docs/ai/color.md)
- **External Packages**: None identified.