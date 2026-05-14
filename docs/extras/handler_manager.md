## 1. Architectural Role
`HandlerManager` acts as a specialized middleware controller within the token processing pipeline, specifically designed to decouple "thought" processes from final user output. It encapsulates the logic required to intercept streaming tokens, delegating the determination of state (thinking vs. outputting) to [extras/think_parser.md](extras/think_parser.md) while utilizing [extras/thinking_log_manager.md](extras/thinking_log_manager.md) for telemetry. Its primary responsibility is to provide a boolean gate that suppresses raw model reasoning from the user interface while allowing sanitized content to pass through.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `thinking_mode` (Default: `"progressbar"`)  Determines the visual representation of the thinking state.
- `enable_thinking_display` (Default: `True`)  Toggles whether thinking processes are visible.
- `show_thinking_animation` (Default: `False`)  Toggles active animation rendering.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | `HandlerManager` | Orchestrates the transition between thinking states and content output. |
| `__init__` | Method | Initializes the `ThinkingAnimationHandler` with provided logging and display configurations. |
| `process_token_chain` | Method | Evaluates a single token/string to decide if it should be rendered to the user or suppressed as internal thought. |

## 4. Execution Logic & Flow
- **Initialization**: 
    - Receives an instance of `ThinkingLogManager`.
    - Instantiates `ThinkingAnimationHandler` using the provided `thinking_mode`, `enable_thinking_display`, and `show_thinking_animation` parameters.
- **Data Path**: 
    - **Input**: `initial_token` (str) passed to `process_token_chain`.
    - **Processing**: Token is passed to `self.thinking_handler.process_token_and_thinking_state`.
    - **Output**: Returns a `Tuple[bool, str, Optional[str]]`.
- **Conditional Branching**:
    - **IF `is_thinking` is True**: Returns `(False, "", None)` $\rightarrow$ Signals the UI to suppress output.
    - **IF `is_thinking` is False**: Returns `(True, content_from_thinking_handler, None)` $\rightarrow$ Signals the UI to display the token/content.

## 5. Resource Dependencies
- **Standard Libraries**: `typing` (Optional, Tuple)
- **Internal Modules**: 
    - [extras/think_parser.md](extras/think_parser.md)
    - [extras/thinking_log_manager.md](extras/thinking_log_manager.md)
- **External Packages**: None identified.