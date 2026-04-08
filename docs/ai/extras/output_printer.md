## Module Purpose
This file defines the `OutputPrinter` class, which is responsible for managing and printing Large Language Model (LLM) output tokens to the console according to specified print modes, including buffering for line-based or token-count-based output.

## Interface & Exports
*   `OutputPrinter` (Class): Manages the display of tokens, offering different modes for immediate or buffered printing.
    *   `__init__(self, print_mode: str = "token", tokens_per_print: int = 5)`: Initializes the printer with a specific mode and token buffer size.
    *   `process_and_print(self, token_to_display: str) -> None`: Processes a token and prints it if ready according to the current `print_mode`.
    *   `flush_buffers(self) -> None`: Empties and prints any remaining buffered content.
    *   `process_token(self, token_to_display: str) -> str`: Processes a token and returns the string to be printed, or `None` if buffering.

## Internal Logic
The `OutputPrinter` class buffers incoming tokens based on its `print_mode`.
*   In `"token"` mode, each token is returned immediately for printing.
*   In `"line"` mode, tokens are accumulated in `line_buffer` until a newline character (`\n`) is encountered, at which point the complete line(s) are returned, and the buffer retains any partial line.
*   In `"every_x_tokens"` mode, tokens are accumulated in `token_buffer` and `buffered_token_count` is incremented. When `buffered_token_count` reaches `tokens_per_print`, the entire `token_buffer` is returned, and both the buffer and count are reset.
*   In `"line_or_x_tokens"` mode, tokens are accumulated in `line_buffer` and `buffered_token_count`. Content is returned if a newline is found (prioritized) or if `buffered_token_count` reaches `tokens_per_print`. In either case, `line_buffer` and `buffered_token_count` are reset.
*   An unknown `print_mode` triggers a warning via `func.log` and defaults to `"token"` behavior.
The `process_and_print` method calls `process_token` and then uses `func.out` to print any non-`None` output string. `flush_buffers` ensures any remaining buffered content is printed at the end of a stream.

## Dependencies
*   `functions` (aliased as `func`): Imported for `func.out` (printing) and `func.log` (logging warnings).

## Constants & Environment
None identified in source.