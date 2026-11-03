## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **ContextSentinel** | [src/ai/agents/context_sentinel.py](/AgentDocs/ai/agents/context_sentinel.md) |

The `ContextSentinel` is a specialized monitoring component designed to manage context window pressure within AI agents. It prevents context overflow by calculating the estimated token usage of a payload and triggering automated "memory surgery" when a predefined threshold is reached.

Its primary responsibility is to perform distilled compression of heavy tool outputs. Instead of allowing verbose logs or code blocks to consume the context window, the Sentinel summarizes these outputs into dense technical facts, archives them to Long-Term Memory (LTM) via a vector store, and prunes the active conversation history to maintain operational efficiency.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ContextSentinel` | Class | The main controller for monitoring context pressure and performing distillation/pruning. |
| `__init__(connector, threshold=0.8, max_tokens=20000, buffer=1024)` | Constructor | Initializes the sentinel with an LLM connector, a pressure threshold, the hardware context limit, and a safety buffer. |
| `enforce_limits(agent_name, memory_manager, payload, vector_memory=None)` | Method | Evaluates context pressure. If the threshold is exceeded, it distills heavy messages, archives them to `vector_memory`, and prunes `memory_manager` history. Returns a tuple of `(modified_payload, compression_occurred)`. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The component uses a heuristic of 4 characters per token to estimate current context usage. When `pressure > threshold`, it iterates through `messages_received` in the agent's memory. If a `SYSTEM` message contains a `result` larger than 2000 characters, the `_summarize_data` method is invoked. This method uses a dedicated LLM prompt ("Fact-Sheet Architect") to extract signatures and logic while explicitly stripping raw source code.
- **Side Effects:** 
    - **LLM Calls:** Performs blocking requests via the `connector` to summarize data.
    - **Memory Mutation:** Directly modifies the `agent_memory` object by updating message results and truncating the `history` list to the last 3 turns.
    - **Vector Storage:** If `vector_memory` is provided, it writes distilled observations to the external vector store.
    - **Logging:** Outputs status updates to the console using `func.out`.
- **Error Handling:** If the calculated delta (available context) is zero or negative, the component logs a warning and returns the original payload without modification.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `json`, `typing`.
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.color](/AgentDocs/ai/color.md)