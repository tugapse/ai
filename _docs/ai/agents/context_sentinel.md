## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| ContextSentinel | ai/agents/context_sentinel |

This component is responsible for actively monitoring the computational context pressure within an AI agent's operational state. Its primary responsibility is to ensure the agent remains within safe token limits by intelligently compressing verbose tool outputs into dense, technical facts and archiving them to Long-Term Memory (LTM).

It functions as a critical service layer, sitting between the agent's execution loop and its memory management system. It interfaces with the [ai.functions](/ai/functions.md) and [ai.color](/ai/color.md) modules to perform memory surgery, ensuring that the agent's operational history remains efficient without losing critical observational data.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| ContextSentinel | Class | Monitors context pressure and performs distilled compression of tool outputs. |
| enforce_limits | Method | Calculates context pressure based on payload size and performs in-place memory surgery if the threshold is exceeded. Returns the modified payload and a boolean indicating if compression/pruning occurred. |
| _summarize_data | Method | Converts complex tool output into a dense, technical fact sheet using a sequential LLM call. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `enforce_limits` method calculates context pressure using a heuristic based on JSON serialization length versus a defined token limit. If the pressure exceeds the `threshold`, it iterates through received system messages. Heavy outputs are passed to `_summarize_data`, which uses an LLM call to distill the content into a fact sheet. This distilled fact is then archived in the `vector_memory` before the raw message is replaced with a summary object, and the agent's history is pruned to the last three turns.
- **Side Effects:** Interacts with the network via `self.connector.send_raw_request` to perform LLM distillation calls. Mutates external state by updating `agent_memory` objects and interacting with `vector_memory`.
- **Error Handling:** The pressure calculation includes a check (`if delta <= 0:`) to prevent division by zero errors.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `json`, `typing`
- **Internal:** [ai.functions](/ai/functions.md), [ai.color](/ai/color.md)