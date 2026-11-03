## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **OutputPrinter** | [src/ai/extras/output_printer.py](/AgentDocs/ai/extras/output_printer.md) |

The `OutputPrinter` component is responsible for managing the real-time display of Large Language Model (LLM) output tokens to the console. It provides abstraction over how tokens are presented to the user, allowing for different streaming behaviors such as immediate token printing, line-buffered printing, or chunked printing based on token counts.

This component serves as a utility within the UI/presentation layer of the application. It is designed to smooth out the visual experience of streaming text, preventing "jittery" console updates by buffering content until specific logical boundaries (like newlines or token thresholds) are met. It is particularly useful when integrating with modules that require synchronized text output, such as voice modules or terminal-based UIs.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `OutputPrinter(print_mode: str = "token", tokens_per_print: int = 5)` | Class | Initializes the printer with a specific mode (`token`, `line`, `every_x_tokens`, or `line_or_x_tokens`) and a buffer threshold. |
| `process_and_print(token_to_display: str) -> None` | Method | Processes a single token and immediately outputs it to the console via `func.out` if the buffering criteria are met. |
| `flush_buffers() -> None` | Method | Forces the printing of any remaining content currently held in the internal buffers. |
| `process_token(token_to_display: str) -> str \| None` | Method | Internal logic handler that manages buffer accumulation and returns a string only when a print threshold is reached. |
| `flush() -> str \| None` | Method | Returns the remaining buffered content as a string (clearing buffers) to allow other modules (e.g., Voice Modules) to capture the final text stream. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The class maintains internal state via `line_buffer`, `token_buffer`, and `buffered_token_count`. Depending on the `print_mode`, it implements different accumulation strategies:
    - `token`: Zero buffering; returns input immediately.
    - `line`: Accumulates text until a `\n` character is detected, then returns the accumulated lines.
    - `every_x_tokens`: Accumulates text until `buffered_token_count` reaches `tokens_per_print`.
    - `line_or_x_tokens`: A hybrid mode that triggers an output if either a newline is detected or the token threshold is reached.
- **Side Effects:** 
    - Performs synchronous I/O operations by calling `func.out` with `flush=True` to write to the standard output.
    - Logs warnings to the console via `func.log` if an invalid `print_mode` is provided.
- **Error Handling:** If an unknown `print_mode` is passed during initialization, the component defaults to `token` mode and logs a warning via the internal function utility.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** Python standard library.
- **Internal:**
    - [ai.functions](/AgentDocs/ai/functions.md)  Used for outputting text (`out`) and logging warnings (`log`).