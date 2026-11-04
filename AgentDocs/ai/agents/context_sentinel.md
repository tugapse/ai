## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **ContextSentinel** | [src/ai/agents/context_sentinel.py](/src/ai/agents/context_sentinel.py) |

The `ContextSentinel` is a specialized utility designed to manage context window pressure within an agent's lifecycle. It monitors the volume of data in the current payload and, upon reaching a defined threshold, performs "memory surgery" to prevent context overflow. This is critical for maintaining stability when working with local GGUF engines or LLMs with finite token limits.

The component functions as a middleware-style monitor between tool execution and agent state updates. When high pressure is detected, it distills verbose tool outputs (such as large logs or code blocks) into dense technical fact sheets, archives these facts to Long-Term Memory (LTM) via a vector store, and prunes the active conversation history to ensure the agent remains focused and within its operational constraints.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ContextSentinel(connector, threshold=0.8, max_tokens=20000, buffer=1024)` | Class | Initializes the sentinel with an LLM connector for distillation, a pressure threshold, a hardware context limit, and a safety buffer. |
| `enforce_limits(agent_name, memory_manager, payload, vector_memory=None)` | Method | Calculates context pressure. If the threshold is exceeded, it summarizes heavy messages, archives them to `vector_memory`, and prunes `memory_manager` history. Returns a tuple of `(modified_payload, compression_occurred)`. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The sentinel uses a heuristic of 4 characters per token to estimate payload size. If `est_tokens / (max_tokens - buffer)` exceeds the `threshold`, the component iterates through `messages_received`. Any message with a `result` exceeding 2000 characters is passed to `_summarize_data`, which uses a specialized "Fact-Sheet Architect" prompt to extract signatures and logic while explicitly stripping raw source code.
- **Side Effects:** 
    - **LLM Calls:** Performs blocking requests via `self.connector.send_raw_request` to distill data.
    - **Memory Mutation:** Mutates the `agent_memory` object provided by the `memory_manager` by updating message contents and pruning the `history` list.
    - **Vector Storage:** If `vector_memory` is provided, it writes distilled observations to the vector store.
    - **Console Output:** Logs status updates to the console using color-coded formatting.
- **Error Handling:** The logic includes a safety check for `delta <= 0` (where `max_tokens` is less than or equal to the `buffer`) to prevent division by zero, returning the original payload unchanged in such cases.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `json`, `typing`.
- **Internal:**
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.color](/AgentDocs/ai/color.md)