## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Direct AI Interface** | [src/ai/direct.py](/src/ai/direct.py) |

The `direct.py` module provides a high-level interface for executing single, direct LLM requests without the overhead of a full agentic loop. It is designed to simplify the process of querying a language model while maintaining support for advanced features like streaming, real-time UI feedback, and automated file logging.

This component acts as a controller within the broader application architecture, bridging the gap between raw LLM capabilities and the user interface. It orchestrates the interaction between the [BaseModel](/ai/core/llms/base_llm.md) implementation, the [UIOrchestrator](/ai/services/ui_orchestrator.md), and the [ThinkingAnimationHandler](/ai/extras/think_parser.md) to ensure a seamless and informative user experience during model inference.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ask(llm, input_message, write_to_file=False, output_filename=None, hide_think_anim=False, print_output=True, stream=True)` | Function | Executes a single LLM request. It manages the lifecycle of the request, including token sanitization, UI animation, real-time printing, and optional file persistence. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The function `ask` initializes the UI environment and prepares the message payload (converting a single string to a structured message if necessary). It iterates over the generator returned by `llm.chat`. Each raw token is passed through `_sanitize_token`, which uses Unicode normalization (NFKC) and regex to strip non-printable ASCII characters. The sanitized tokens are then processed by a UI handler to determine how they should be displayed or stored.
- **Side Effects:** 
    - **Filesystem:** Creates directories if they do not exist and writes/appends content to the specified `output_filename`. It also initializes a log file `active_thinking_process.log` via the UI orchestrator.
    - **Console I/O:** Prints processed tokens to the standard output in real-time if `print_output` is enabled.
    - **Network/LLM:** Initiates a network or local process request to the provided LLM instance.
- **Error Handling:** Specifically catches `KeyboardInterrupt` to allow for graceful task abortion, logging a notification to the user via [func.log](/ai/functions.md).

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `ProgramConfig`  Loaded via [ProgramConfig.get_current()](/ai/config.md) to configure the UI and execution environment.

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