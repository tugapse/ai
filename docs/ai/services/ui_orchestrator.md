

## 1. Architectural Role  
Manages UI components for visual feedback, including thinking logs, token printing, and progress bar handling, ensuring consistent output formatting and interaction with the assistant's thought process.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `UIOrchestrator` | Class | Coordinates UI components for thought visualization, output printing, and handler logic. |  
| `__init__` | Method | Initializes core UI components with program configuration. |  
| `initialize` | Method | Sets up ThinkingLogManager, OutputPrinter, and HandlerManager based on configuration. |  
| `reset_turn` | Method | Clears formatting buffers and flushes output buffers for a new chat turn. |  
| `get_components` | Method | Returns printer, handler, and formatter for integration with StreamOrchestrator. |  

## 3. Execution Logic & Flow  
- **Initialization**: Loads configuration and initializes `log_manager`, `printer`, `handler`, and `formatter` with default values from `ProgramConfig`.  
- **Data Path**: Configuration parameters (e.g., `PRINT_MODE`, `THINKING_MODE`) drive the setup of output speed, logging behavior, and progress bar display.  
- **Conditional Branching**:  
  - `initialize` uses `config.get()` to select `print_mode` (e.g., `"line_or_x_tokens"`) and `thinking_mode` (e.g., `"progressbar"`).  
  - `HandlerManager` is configured with `enable_thinking_display` and `show_thinking_animation` flags.  

## 4. Resource Dependencies  
- **Internal Modules**: `ThinkingLogManager`, `OutputPrinter`, `HandlerManager`, `ConsoleTokenFormatter` (from `extras`).  
- **Config Dependencies**: `ProgramConfig` for retrieving `PRINT_MODE`, `TOKENS_PER_PRINT`, `THINKING_MODE`, and `ENABLE_THINKING_DISPLAY`.  

## 5. Configuration & Environment  
- **Hardcoded Constants**:  
  - Default `print_mode`: `"line_or_x_tokens"`  
  - Default `thinking_mode`: `"progressbar"`  
  - Default `enable_thinking_display`: `True`  
- **Environment Lookups**:  
  - `ProgramSetting.PRINT_MODE`  
  - `ProgramSetting.TOKENS_PER_PRINT`  
  - `ProgramSetting.THINKING_MODE`  
  - `ProgramSetting.ENABLE_THINKING_DISPLAY`