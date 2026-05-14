## 1. Architectural Role

**Functional Mission**
The **OutputPrinter** class is responsible for managing the real-time presentation of LLM-generated tokens to the user interface. Its primary mission is to abstract the complexity of token-by-token streaming by implementing various buffering strategiessuch as line-based or frequency-based printingto ensure a smooth, readable, and non-jittery console output experience.

**System Context & Integration**
This component acts as a presentation-layer utility within the streaming pipeline. It sits between the raw token stream provided by LLM modules and the final output destination. It is designed to be utilized by higher-level orchestrators, such as the [Stream Orchestrator](/docs/services/stream_orchestrator.md), to control how text appears to the user. Furthermore, its `flush` mechanism provides a critical bridge to downstream modules, such as the [Voice Module](/docs/modules/voice/base_module.md), by ensuring that the complete, buffered text is captured for text-to-speech processing once the stream concludes.

## 2. Environment & Configuration

**Environment Lookups:**
No environment lookups identified.

**Hardcoded Constants:**
- `tokens_per_print` (Default: `5`)  Determines the threshold for the `every_x_tokens` and `line_or_x_tokens` printing modes.

## 3. Interface & API Surface

| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `OutputPrinter` | Class | Manages token buffering and conditional printing logic based on selected modes. |
| `process_and_print` | Method | Orchestrates the transformation of a token via `process_token` and executes the actual output via `func.out`. |
| `flush_buffers` | Method | Immediately pushes all currently buffered content to the console and clears buffers. |
| `process_token` | Method | The core logic engine; evaluates the current `print_mode` and determines if a string is ready to be released from the buffer. |
| `flush` | Method | Returns the remaining buffered content as a string for external consumption (e.g., Voice Modules) instead of printing it. |

## 4. Execution Logic & Flow

- **Initialization**: Sets the `print_mode` and `tokens_per_print`. Initializes `line_buffer` (string), `token_buffer` (string), and `buffered_token_count` (integer) to manage state across asynchronous token arrivals.
- **Data Path**: 
    1. **Input**: A single `token_to_display` string is passed to `process_and_print`.
    2. **Processing**: `process_token` appends the token to the appropriate buffer (`line_buffer` or `token_buffer`) and increments `buffered_token_count`.
    3. **Decision**: 
        - If `mode == "token"`: Returns token immediately.
        - If `mode == "line"`: Returns text only when a `\n` is detected, stripping the newline from the buffer.
        - If `mode == "every_x_tokens"`: Returns text only when `buffered_token_count` reaches `tokens_per_print`.
        - If `mode == "line_or_x_tokens"`: Returns text if a newline is detected OR if the token count threshold is met.
    4. **Output**: If a string is returned, it is passed to `func.out` with `flush=True`.
- **Conditional Branching**: 
    - **Unknown Mode**: If an invalid `print_mode` is provided, the system logs a warning via `func.log` and falls back to immediate "token" mode.
    - **Buffer Clearing**: Upon meeting a print condition (newline or count), the specific buffer and the `buffered_token_count` are reset to prevent duplicate output.

## 5. Resource Dependencies

- **Standard Libraries**: None identified.
- **Internal Modules**: 
    - [functions](/docs/functions.md)
- **External Packages**: None identified.