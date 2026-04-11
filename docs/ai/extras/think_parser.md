

## 1. Architectural Role  
Manages display and state transitions for LLM "thinking" indicators via tag parsing and animation rendering.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `ThinkingAnimationHandler` | Class | Coordinates thinking state, animation rendering, and tag parsing for LLM output |  
| `__init__` | Method | Initializes handler with display flags, mode, and logging integration |  
| `process_token_and_thinking_state` | Method | Processes raw tokens, updates thinking state, and returns display content |  
| `_draw_animation_frame` | Method | Renders spinner, progress bar, or dots animation based on configured mode |  
| `get_max_thinking_indicator_length` | Method | Calculates maximum width for clearing animation lines |  
| `print_think` | Method | Outputs formatted thinking indicators to terminal |  

## 3. Execution Logic & Flow  
- **Initialization**: Sets `enable_display`, `mode`, and injects `ThinkingLogManager` instance; initializes state flags and counters  
- **Data Path**: Raw tokens  accumulated buffer  regex tag detection  state transitions  animation rendering  output content  
- **Conditional Branching**:  
  - Detects `</think>` tags to terminate thinking state  
  - Detects `<think>` tags to activate thinking state  
  - Triggers animation rendering during active thinking  
  - Routes non-tag content to output buffer  

## 4. Resource Dependencies  
- **Standard Libraries**: `re`  
- **Internal Modules**: `functions`, `extras.thinking_log_manager`  
- **External Packages**: None  

## 5. Configuration & Environment  
- **Hardcoded Constants**:  
  - `SPINNER_CHARS` = ["|", "/", "-", "\\"]  
  - `PROGRESS_BAR_LENGTH` = 5  
  - `MAX_UNTILL_THINK_DRAW` = 3  
- **Environment Lookups**: None