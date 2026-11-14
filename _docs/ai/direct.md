## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| direct | /ai/direct.md |

This component, `direct`, serves as the primary synchronous interface for executing a single, direct query against a specified Language Model (LLM). Its core responsibility is to manage the entire lifecycle of an LLM interaction, from sending the input message to processing and outputting the received tokens. It handles the complexities of streaming, logging, and output persistence based on runtime configuration.

Architecturally, this module acts as a high-level service controller. It orchestrates the interaction between the `BaseModel` (the LLM provider), the `UIOrchestrator` for user feedback, and configuration management via `ProgramConfig`. It is responsible for translating user intent into a standardized LLM request flow and managing the resulting token stream for display or file saving.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| _sanitize_token | Function | Cleans and normalizes tokens by applying NFKC normalization and removing specific control characters, while preserving non-ASCII text. |
| ask | Function | Executes a single LLM request. Takes the LLM instance, input message (string or list), and various flags to control output behavior (file writing, streaming, printing, etc.). |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `ask` function initiates the request by setting up logging and UI components. It iterates over the LLM's streaming response (`llm.chat`). For each raw token, it sanitizes the token, applies an optional `on_token` callback, and processes the token chain via `handler.process_token_chain` to determine display output. If file writing is enabled, it appends the content to the specified file.
- **Side Effects:** Reads/writes to the filesystem (via `func.write_to_file` and logging), interacts with the UI orchestrator (`UIOrchestrator`), and potentially calls external network resources through the `llm.chat` method.
- **Error Handling:** It explicitly catches `KeyboardInterrupt` to allow for graceful task abortion and uses a `try...finally` block to ensure execution time logging occurs even if an interruption happens.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `re`, `unicodedata`, `time`, `typing`.
- **Internal:** [ai.functions](/ai/functions.md), [ai.color](/ai/color.md), [ai.core.llms.base_llm](/ai/core/llms/base_llm.md), [ai.chat.chat](/ai/chat/chat.md), [ai.config](/ai/config.md), [ai.services.ui_orchestrator](/ai/services/ui_orchestrator.md), [ai.extras.think_parser](/ai/extras/think_parser.md).