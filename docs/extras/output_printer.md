## 1. Architectural Role
The `OutputPrinter` class manages the buffering and streaming of LLM output tokens to the console based on configurable print modes to control visual update frequency.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `OutputPrinter` | Class | Orchestrates token buffering and console output based on `print_mode`. |
| `__init__` | Method | Initializes print mode, token thresholds, and internal string/count buffers. |
| `process_and_print` | Method | High-level entry point that processes a token and immediately calls `func.out` if output is returned. |
| `flush_buffers` | Method | Forces immediate printing of all remaining buffered content to the console. |
| `process_token` | Method | Logic engine that determines if a token should be returned for printing or stored in a buffer. |
| `flush` | Method | Extracts and returns remaining buffered content as a string for external capture (e.g., Voice Module). |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Sets `print_mode` (default: `"token"`).
    2. Sets `tokens_per_print` (ensured minimum of 1).
    3. Initializes `line_buffer` (string), `token_buffer` (string), and `buffered_token_count` (integer) to empty/zero states.
- **Data Path**: `token_to_display` $\rightarrow$ `process_and_print()` $\rightarrow$ `process_token()` $\rightarrow$ (Buffer or Return String) $\rightarrow$ `func.out()`.
- **Conditional Branching**:
    - **`token`**: Returns token immediately.
    - **`line`**: Appends to `line_buffer`; returns content only when `\n` is detected.
    - **`every_x_tokens`**: Appends to `token_buffer`; returns content when `buffered_token_count` $\ge$ `tokens_per_print`.
    - **`line_or_x_tokens`**: Prioritizes `\n` detection; if no newline, returns content when `buffered_token_count` $\ge$ `tokens_per_print`.
    - **Unknown Mode**: Logs warning via `func.log` and defaults to `token` behavior.

## 4. Resource Dependencies
- **Standard Libraries**: None.
- **Internal Modules**: `functions` (aliased as `func`).
- **External Packages**: None.

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - Default `print_mode`: `"token"`
    - Default `tokens_per_print`: `5`
- **Environment Lookups**: None.