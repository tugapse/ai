## 1. Architectural Role
The `OutputPrinter` class acts as a stream-processing middleware responsible for controlling the temporal granularity of LLM token output displayed to the user. It manages internal buffers to implement various printing strategiesranging from raw token streaming to line-buffered or frequency-based chunkingensuring that the console output remains readable and synchronized with other system components like [modules/voice/vibe_module.md](modules/voice/vibe_module.md) via its final state capture mechanism.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `print_mode` (Default: `"token"`)  Determines the buffering logic strategy.
- `tokens_per_print` (Default: `5`)  Sets the threshold for chunk-based output in `every_x_tokens` or `line_or_x_tokens` modes.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `OutputPrinter` | Class | Orchestrates token buffering and conditional printing logic. |
| `process_and_print` | Method | Executes the transformation of a token and immediately triggers the output via [functions.md](functions.md). |
| `flush_buffers` | Method | Forces the immediate printing of all remaining content in current buffers. |
| `process_token` | Method | The core logic engine; calculates whether a token (or group of tokens) meets the criteria for display based on `print_mode`. |
| `flush` | Method | Captures and returns buffered content as a string for external consumption (e.g., Voice Modules). |

## 4. Execution Logic & Flow
- **Initialization**: Sets the `print_mode` and `tokens_per_print` constraints; initializes `line_buffer`, `token_buffer`, and `buffered_token_count` to zero/empty states.
- **Data Path**: 
    1. `process_and_print` receives `token_to_display`.
    2. `process_token` appends the token to the appropriate internal buffer (`line_buffer` or `token_buffer`).
    3. Logic evaluates if a delimiter (`\n`) is present or if `buffered_token_count` meets the threshold.
    4. If criteria are met, a substring is returned; otherwise, `None` is returned.
    5. If a string is returned, `func.out` is called to write to the console.
- **Conditional Branching**:
    - `token`: Zero buffering; immediate return.
    - `line`: Buffers until `\n` is detected; returns all content preceding the newline.
    - `every_x_tokens`: Buffers until `buffered_token_count` reaches `tokens_per_print`.
    - `line_or_x_tokens`: Prioritizes newline detection; if no newline, falls back to the token count threshold.
    - `Unknown mode`: Logs a warning via `func.log` and reverts to `token` mode.

## 5. Resource Dependencies
- **Standard Libraries**: None identified.
- **Internal Modules**: 
    - [functions.md](functions.md)
- **External Packages**: None identified.