## 1. Architectural Role
Provides a buffered streaming mechanism to control the granularity and frequency of LLM token output to the console based on specific formatting strategies.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `OutputPrinter` | Class | Manages stateful buffers and logic for conditional token printing. |
| `__init__` | Method | Initializes print mode, token thresholds, and string/count buffers. |
| `process_and_print` | Method | Orchestrates the transformation of a token and immediate execution of `func.out`. |
| `flush_buffers` | Method | Force-prints all remaining content in buffers to the console. |
| `process_token` | Method | Evaluates a token against the `print_mode` logic to determine if a string should be returned. |
| `flush` | Method | Returns remaining buffered content as a string for external capture (e.g., Voice Module) without printing. |

## 3. Execution Logic & Flow
- **Initialization**: Sets `print_mode` (string), `tokens_per_print` (integer, minimum 1), `line_buffer` (empty string), `token_buffer` (empty string), and `buffered_token_count` (0).
- **Data Path**: 
    1. **Input**: Single `token_to_display` string passed to `process_and_print`.
    2. **Processing**: `process_token` appends the token to `line_buffer` or `token_buffer` and checks for exit conditions (newline character or `tokens_per_print` threshold).
    3. **Output**: If conditions are met, a substring is returned to `process_and_print`, which calls `func.out` with `flush=True`.
- **Conditional Branching**:
    - `print_mode == "token"`: Immediate return of input.
    - `print_mode == "line"`: Buffers until `\n` is detected; returns all content preceding the last newline.
    - `print_mode == "every_x_tokens"`: Buffers until `buffered_token_count` reaches `tokens_per_print`.
    - `print_mode == "line_or_x_tokens"`: Prioritizes newline detection (resets count); falls back to token count threshold if no newline is present.
    - `else` (Unknown Mode): Logs warning via `func.log` and defaults to immediate token return.

## 4. Resource Dependencies
- **Standard Libraries**: None.
- **Internal Modules**: `functions` (aliased as `func`).
- **External Packages**: None.

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - Default `tokens_per_print`: `5`.
    - Minimum `tokens_per_print` enforcement: `max(1, tokens_per_print)`.
- **Environment Lookups**: None.