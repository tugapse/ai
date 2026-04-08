## 1. Architectural Role
Manages how Large Language Model (LLM) output tokens are printed to the console based on the print mode, handling buffering for 'line' and 'every_x_tokens' modes.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `OutputPrinter` | Class | Manages LLM output token printing based on print mode. |
| `process_and_print` | Method | Processes a single formatted token and prints it based on the configured mode. |
| `flush_buffers` | Method | Prints any remaining content in buffers at the end of the stream. |
| `process_token` | Method | Processes a single formatted token and returns the string to be printed, or None if nothing is ready to be printed yet (due to buffering). |

## 3. Execution Logic & Flow
- **Initialization**: The `OutputPrinter` class is initialized with a `print_mode` and `tokens_per_print`. It sets up buffers and initializes counters.
- **Data Path**: Tokens are processed through the `process_token` method, which determines how they are buffered and printed based on the `print_mode`. The `process_and_print` method then outputs the processed token.
- **Conditional Branching**: The key decision points are based on the `print_mode`:
  - For `token` mode, the token is returned directly.
  - For `line` mode, tokens are buffered until a newline is encountered, at which point the buffered line is returned.
  - For `every_x_tokens` mode, tokens are buffered until the specified number of tokens is reached, at which point the buffered tokens are returned.
  - For `line_or_x_tokens` mode, tokens are buffered until either a newline is encountered or the specified number of tokens is reached, at which point the buffered tokens are returned.

## 4. Resource Dependencies
- **Standard Libraries**: None
- **Internal Modules**: `functions` (aliased as `func`)
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: `tokens_per_print` defaults to 5.
- **Environment Lookups**: None