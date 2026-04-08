## 1. Architectural Role
Handles display and state management for LLM "thinking" tags, including animation and logging.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ThinkingAnimationHandler` | Class | Manages the display and state of "thinking" tags in LLM output, including animation and logging. |
| `process_token_and_thinking_state` | Method | Processes incoming tokens to manage the "thinking" state and generate display content. |
| `print_think` | Method | Prints messages with optional animation. |
| `get_max_thinking_indicator_length` | Method | Calculates the maximum length of the thinking indicator. |
| `__init__` | Method | Initializes the handler with settings for display, animation mode, and logging. |

## 3. Execution Logic & Flow
- **Initialization**: Sets default values for display, animation mode, logging manager, and internal state variables.
- **Data Path**: 
  1. Accumulates raw token strings in `_token_accumulation_buffer`.
  2. Cleans the buffer of control characters.
  3. Checks for and processes `<think>` and `</think>` tags.
  4. Handles active thinking state by drawing animation frames.
  5. Returns the current thinking state and display content.
- **Conditional Branching**:
  - Checks for `<think>` and `</think>` tags to start and end thinking states.
  - Determines the animation mode and draws the appropriate frame.
  - Handles partial tags and normal output.

## 4. Resource Dependencies
- **Standard Libraries**: `re`
- **Internal Modules**: `functions as func`, `extras.thinking_log_manager`
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: 
  - `SPINNER_CHARS`
  - `PROGRESS_BAR_LENGTH`
  - `THINKING_PREFIX`
  - `MAX_UNTILL_THINK_DRAW`
- **Environment Lookups**: None