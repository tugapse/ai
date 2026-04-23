## 1. Architectural Role
Manages the detection, suppression, and visual animation of LLM `<think>` tags during token streaming to separate internal reasoning from final output.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ThinkingAnimationHandler` | Class | Orchestrates the state machine for thinking tag detection and animation rendering. |
| `process_token_and_thinking_state` | Method | Primary entry point; processes raw tokens to determine if they are part of a thinking block or displayable content. |
| `_draw_animation_frame` | Method | Renders the visual indicator based on the selected `mode` (`dots`, `spinner`, `progressbar`). |
| `get_max_thinking_indicator_length` | Method | Calculates the maximum character width of the animation for line-clearing purposes. |
| `print_think` | Method | Wrapper for `functions.out` to conditionally print animation frames if `show_animation` is enabled. |

## 3. Execution Logic & Flow
- **Initialization**: Sets display preferences (`enable_display`, `show_animation`), animation `mode`, and initializes state trackers (`_is_thinking_active`, `_has_thinking_intro_printed`, `_current_thinking_count`, and `_token_accumulation_buffer`).
- **Data Path**: `raw_token_string` $\rightarrow$ `_token_accumulation_buffer` $\rightarrow$ `CONTROL_CHARS_PATTERN` cleaning $\rightarrow$ Tag Pattern Matching $\rightarrow$ (Animation Frame OR Display String) $\rightarrow$ Return `(bool, str)`.
- **Conditional Branching**:
    1. **Display Disabled**: Immediately returns the buffer as display content.
    2. **End Tag Detection**: If `_is_thinking_active` is True, it clears the animation line, resets state, and returns trailing content.
    3. **Start Tag Detection**: If `_is_thinking_active` is False, it triggers the `ThinkingLogManager` header, prints the `THINKING_PREFIX`, and sets state to active.
    4. **Active Thinking**: Increments `_current_thinking_count`, logs the token via `_log_manager`, and calls `_draw_animation_frame`.
    5. **Normal/Partial Output**: If no partial tag is detected, it flushes the buffer for display; otherwise, it returns the raw token to prevent premature tag splitting.

## 4. Resource Dependencies
- **Standard Libraries**: `re`
- **Internal Modules**: `functions`, `extras.thinking_log_manager.ThinkingLogManager`
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**:
    - `SPINNER_CHARS`: `["|", "/", "-", "\\"]`
    - `PROGRESS_BAR_LENGTH`: `5`
    - `THINKING_PREFIX`: `"Thinking"`
    - `MAX_UNTILL_THINK_DRAW`: `3`
    - `THINK_START_PATTERN`: `\s*<think>\s*`
    - `THINK_END_PATTERN`: `\s*</think>\s*`
    - `CONTROL_CHARS_PATTERN`: `[\x00-\x09\x0B-\x1F\x7F]`
    - `PARTIAL_TAG_PATTERN`: `<th(?:in(?:k>)?|/th(?:ink>)?|i|n|k|/i|/n|/k)?`
- **Environment Lookups**: None