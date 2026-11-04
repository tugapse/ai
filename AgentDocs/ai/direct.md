## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Direct AI Task Handler** | [src/ai/direct.py](/src/ai/direct.py) |

The `direct.py` module provides a high-level interface for executing single, direct LLM requests without the overhead of a full agentic loop. It is designed to facilitate straightforward "prompt-in, response-out" interactions while managing the complexities of streaming, UI feedback, and output persistence.

This component acts as a controller within the AI service layer. It orchestrates the interaction between a specific LLM implementation, the user interface via [UIOrchestrator](/ai/services/ui_orchestrator.md), and the system's logging and file-writing utilities. It is primarily used for tasks where a single response is required rather than iterative reasoning or tool use.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ask(llm, input_message, write_to_file=False, output_filename=None, hide_think_anim=False, print_output=True, stream=True)` | Function | Executes a single LLM request. It handles token sanitization, streaming output to the console, and optional file writing. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The module utilizes a streaming loop to consume tokens from the provided `BaseModel` instance. Each raw token is passed through `_sanitize_token`, which applies `NFKC` Unicode normalization and strips non-printable ASCII characters (excluding tabs and newlines). The sanitized content is then processed by a `handler` (retrieved from the UI orchestrator) to determine how it should be displayed to the user versus how it should be stored.
- **Side Effects:** 
    - **Filesystem:** Creates directories if `write_to_file` is enabled and `output_filename` is provided. It writes content to the specified file using append mode. It also initializes a log file `active_thinking_process.log` via the UI orchestrator.
    - **Console/UI:** Prints tokens to the standard output and manages "thinking" animations via the `ThinkingAnimationHandler`.
    - **Logging:** Records execution latency (first token latency and total execution time) and task status to the system logs.
- **Error Handling:** Specifically catches `KeyboardInterrupt` to allow for a graceful abort of the task, logging `[!] Task aborted.` before cleaning up the UI state.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No specific environment variables are directly accessed in this module, though it relies on `ProgramConfig` for system-wide settings.

**Module Dependencies:**
- **Standard/External:** `os`, `re`, `unicodedata`, `time`, `typing`.
- **Internal:**
    - [ai.functions](/ai/functions.md)
    - [ai.color](/ai/color.md)
    - [ai.core.llms.base_llm](/ai/core/llms/base_llm.md)
    - [ai.chat.chat](/ai/chat/chat.md)
    - [ai.config](/ai/config.md)
    - [ai.services.ui_orchestrator](/ai/services/ui_orchestrator.md)
    - [ai.extras.think_parser](/ai/extras/think_parser.md)