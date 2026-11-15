## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| ThinkingAnimationHandler | ai/extras/think_parser |

This component, `ThinkingAnimationHandler`, is responsible for parsing and managing the display state related to LLM "thinking" tags (`<think>...</think>`) within a streaming output. Its primary responsibility is to intercept raw tokens, detect the start and end of thinking blocks, and manage the presentation of indicators (dots, spinners, or progress bars) to provide visual feedback to the user during LLM processing.

It functions as a specialized state machine/utility layer within the application architecture. It interfaces with the streaming input stream, maintains internal state regarding active thinking sessions, and relies on the [ThinkingLogManager](/ai/extras/thinking_log_manager.md) to handle logging aspects when thinking is active.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `ThinkingAnimationHandler` | Class | Handles display and state management for LLM "thinking" tags. |
| `process_token_and_thinking_state` | Method | Processes a raw token string to update the thinking state and determine output content. Returns (is_thinking_active, content_to_display). |
| `get_max_thinking_indicator_length` | Method | Calculates the maximum required length for the thinking indicator line, used for clearing the line correctly. |
| `print_think` | Method | Prints the thinking message using the configured output mechanism via `ai.functions`. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The handler operates as a state machine driven by incoming tokens. It uses regex patterns to identify `<think>` start and end tags. When a start tag is found, it transitions to an active state and begins drawing an indicator. While active, it increments a counter and calls `_draw_animation_frame()` to update the visual indicator in place using carriage returns. Upon finding an end tag, it resets the state. If the display is disabled, it bypasses all state logic and passes raw tokens through.
- **Side Effects:** The code interacts with the console/standard output via `func.out` when `show_animation` is true, causing terminal drawing side effects (printing, clearing lines). It also interacts with the external state managed by the [ThinkingLogManager](/ai/extras/thinking_log_manager.md) to log thinking events.
- **Error Handling:** The logic relies heavily on regex matching. If the end tag is encountered while not in an active state, it attempts to strip the tag without erroring. No explicit `try...except` blocks are present for external resource errors.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `re`
- **Internal:** [ai.functions](/ai/functions.md), [ThinkingLogManager](/ai/extras/thinking_log_manager.md)