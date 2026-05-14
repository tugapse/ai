## 1. Architectural Role
Manages the detection, state transitions, and visual representation of LLM "thinking" blocks within a streaming token sequence.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ThinkingAnimationHandler` | Class | Orchestrates the lifecycle of thinking state detection and UI feedback. |
| `process_token_and_thinking_state` | Method | Primary entry point; consumes raw tokens, manages an accumulation buffer, and returns a tuple of `(is_thinking_active, display_content)`. |
| `_draw_animation_frame` | Method | Internal logic for rendering visual feedback based on the selected `mode`. |
| `get_max_thinking_indicator_length` | Method | Calculates the character width required to clear the animation line. |
| `print_think` | Method | Wrapper for `func.out` to handle actual terminal output if `show_animation` is enabled. |

## 3. Execution Logic & Flow
- **Initialization**: Sets up state variables: `_is_thinking_active` (bool), `_has_thinking_intro_printed` (bool), `_current_thinking_count` (int), and `_token_accumulation_buffer` (str); configures display modes and log manager links.
- **Data Path**: 
    1. **Input**: Receives `raw_token_string`.
    2. **Accumulation**: Appends input to `_token_accumulation_buffer`.
    3. **Cleaning**: Applies `CONTROL_CHARS_PATTERN` to create `cleaned_buffer`.
    4. **Pattern Matching**: Checks `cleaned_buffer` against `THINK_END_PATTERN`, `THINK_START_PATTERN`, and `PARTIAL_TAG_PATTERN`.
    5. **State Transformation**: 
        - If `</think>` is found: Sets `_is_thinking_active` to `False` and clears the animation line.
        - If `<think>` is found: Sets `_is_thinking_active` to `True` and triggers intro/logging.
        - If active: Increments `_current_thinking_count` and triggers `_draw_animation_frame`.
    6. **Output**: Returns `(bool, str)` where `str` is either the content to be printed to the user or an empty string if the token is part of the "thinking" process.
- **Conditional Branching**:
    - `enable_display`: If `False`, bypasses all logic and returns raw buffer.
    - `is_thinking_active`: Determines if the logic follows the "End Tag" check, "Start Tag" check, or "Active Thinking" animation path.
    - `PARTIAL_TAG_PATTERN`: Determines if the buffer contains an incomplete tag (e.g., `<th`), in which case the token is held in the buffer to prevent premature output.
    - `mode`: Branches `_draw_animation_frame` into `dots`, `spinner`, or `progressbar`.

## 4. Resource Dependencies
- **Standard Libraries**: `re`
- **Internal Modules**: `functions` (as `func`), `extras.thinking_log_manager` (as `ThinkingLogManager`)
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `SPINNER_CHARS`: `["|", "/", "-", "\\"]`
    - `PROGRESS_BAR_LENGTH`: `5`
    - `THINKING_PREFIX`: `"Thinking"`
    - `MAX_UNTILL_THINK_DRAW`: `3`
    - `THINK_START_PATTERN`: `re.compile(r"\s*<think>\s*")`
    - `THINK_END_PATTERN`: `re.compile(r"\s*</think>\s*")`
    - `CONTROL_CHARS_PATTERN`: `re.compile(r"[\x00-\x09\x0B-\x1F\x7F]")`
    - `PARTIAL_TAG_PATTERN`: `re.compile(r"<th(?:in(?:k>)?|/th(?:ink>)?|i|n|k|/i|/n|/k)?")`
- **Environment Lookups**: None