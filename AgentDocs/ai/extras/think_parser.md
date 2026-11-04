## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **ThinkingAnimationHandler** | [src/ai/extras/think_parser.py](/src/ai/extras/think_parser.py) |

The `ThinkingAnimationHandler` is responsible for intercepting and managing LLM "thinking" tokens within a streaming response. It identifies specific XML-like tags (e.g., `<think>` and `</think>`) to distinguish between the model's internal reasoning process and its final output intended for the user.

This component acts as a UI/UX utility within the streaming pipeline. It provides visual feedback to the user through various animation modes (dots, spinners, or progress bars) while the model is in a "thinking" state, ensuring the interface remains dynamic and informative during high-latency reasoning phases.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ThinkingAnimationHandler(...)` | Class | Initializes the handler with display settings, animation modes, and an optional log manager. |
| `process_token_and_thinking_state(raw_token_string: str)` | Method | Processes a single incoming token. Returns a tuple of `(is_thinking_active: bool, display_content: str)`. |
| `get_max_thinking_indicator_length()` | Method | Calculates the character length required to clear the animation line from the terminal. |
| `print_think(message, **kargs)` | Method | Outputs the thinking status or animation frame to the console using the configured output function. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The handler uses regular expressions to monitor a buffer for start/end thinking tags and partial tag sequences. It maintains an internal state machine (`_is_thinking_active`) to determine whether incoming tokens should be treated as reasoning content (to be logged) or as final response content (to be displayed). Animation frames are calculated based on a token counter and the selected `mode`.
- **Side Effects:** 
    - **Console I/O:** Directly writes to the standard output (via `ai.functions.out`) to render animations and clear lines using ANSI escape codes (`\033[2K`).
    - **Logging:** If a `ThinkingLogManager` is provided, it writes reasoning tokens to the log manager during the active thinking state.
- **Error Handling:** The component handles partial tags (e.g., `<thi`) by buffering them to prevent premature output or incorrect state transitions. It uses a control character regex to clean the buffer of non-printable characters.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `re` (Regular Expressions).
- **Internal:**
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.extras.thinking_log_manager](/AgentDocs/ai/extras/thinking_log_manager.md)