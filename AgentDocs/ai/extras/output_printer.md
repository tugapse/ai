## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **OutputPrinter** | [src/ai/extras/output_printer.py](/src/ai/extras/output_printer.py) |

The `OutputPrinter` class is a specialized utility designed to manage the streaming display of Large Language Model (LLM) output tokens to the console. It provides controlled buffering mechanisms to prevent fragmented or jittery text output, which is common during real-time token streaming.

This component acts as a presentation layer utility within the broader AI orchestration system. It is primarily used to transform raw, individual token streams into more readable formatssuch as printing only complete lines or grouping tokens into specific chunksthereby improving the user experience during live inference.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `OutputPrinter(print_mode: str = "token", tokens_per_print: int = 5)` | Class | Initializes the printer with a specific mode (`token`, `line`, `every_x_tokens`, or `line_or_x_tokens`) and a buffering threshold. |
| `process_and_print(token_to_display: str) -> None` | Method | Processes a single token and immediately outputs it to the console via `func.out` if the buffering logic allows. |
| `flush_buffers() -> None` | Method | Forcefully prints any content remaining in the internal buffers to ensure no text is lost at the end of a stream. |
| `process_token(token_to_display: str) -> str \| None` | Method | The core logic engine that determines if a token (or group of tokens) satisfies the current `print_mode` requirements to be returned for printing. |
| `flush() -> str \| None` | Method | Returns the remaining buffered content as a string without clearing it immediately (intended for downstream consumption like Voice Modules), while also handling buffer cleanup. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The component utilizes internal string buffers (`line_buffer`, `token_buffer`) and a counter (`buffered_token_count`) to manage state. 
    - `token` mode: Immediate pass-through.
    - `line` mode: Buffers text until a newline character `\n` is detected, then returns all preceding lines.
    - `every_x_tokens` mode: Buffers text until the `buffered_token_count` reaches `tokens_per_print`.
    - `line_or_x_tokens` mode: A hybrid approach that triggers an output if either a newline is detected OR the token count threshold is met.
- **Side Effects:** 
    - Performs synchronous I/O by calling `func.out` with `flush=True` during `process_and_print` and `flush_buffers`.
    - Mutates internal buffer states during token processing.
- **Error Handling:** If an invalid `print_mode` is provided, the component logs a warning via `func.log` and falls back to the `token` mode (immediate pass-through) to prevent stream interruption.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** None identified.
- **Internal:**
    - [ai.functions](/AgentDocs/ai/functions.md)