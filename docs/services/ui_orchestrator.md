## 1. Architectural Role
Acts as the central coordinator for visual feedback systems, managing the lifecycle of thinking logs, token-buffered console output, and UI state transitions.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `UIOrchestrator` | Class | Orchestrates the lifecycle and interaction of UI-related sub-components. |
| `__init__` | Method | Initializes the orchestrator with a `ProgramConfig` and sets up empty component placeholders. |
| `initialize` | Method | Instantiates and configures `ThinkingLogManager`, `OutputPrinter`, and `HandlerManager` using provided configuration. |
| `reset_turn` | Method | Resets the `ConsoleTokenFormatter` buffer and flushes the `OutputPrinter` buffers. |
| `get_components` | Method | Returns a dictionary containing the active `printer`, `handler`, and `formatter` instances. |

## 3. Execution Logic & Flow
- **Initialization**:
    1. `__init__` is called with a `ProgramConfig` object.
    2. Core component attributes (`log_manager`, `printer`, `handler`) are set to `None`.
    3. `formatter` is instantiated as a `ConsoleTokenFormatter`.
- **Data Path**:
    1. **Input**: `ProgramConfig` settings and `log_filepath` string.
    2. **Processing**: `initialize` maps config keys (`PRINT_MODE`, `TOKENS_PER_PRINT`, `THINKING_MODE`, `ENABLE_THINKING_DISPLAY`) to specific component constructors.
    3. **Output**: A dictionary of functional UI components via `get_components`.
- **Conditional Branching**:
    - **Component Availability**: `reset_turn` performs a null-check on `self.printer` before attempting to call `flush_buffers()`.
    - **Configuration Defaults**: `initialize` uses `.get()` with fallback values for all `ProgramSetting` lookups (e.g., defaulting `print_mode` to `"line_or_x_tokens"` and `tokens_per_print` to `50`).

## 4. Resource Dependencies
- **Standard Libraries**: `typing.Optional`
- **Internal Modules**: 
    - `services.config_helper` (`ProgramConfig`, `ProgramSetting`)
    - `extras.thinking_log_manager` (`ThinkingLogManager`)
    - `extras.output_printer` (`OutputPrinter`)
    - `extras.HandlerManager` (`HandlerManager`)
    - `extras.ConsoleTokenFormatter` (`ConsoleTokenFormatter`)
    - `functions` (`func`)
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `show_thinking_animation=True` (passed to `HandlerManager`)
- **Environment Lookups**:
    - `ProgramSetting.PRINT_MODE`
    - `ProgramSetting.TOKENS_PER_PRINT`
    - `ProgramSetting.THINKING_MODE`
    - `ProgramSetting.ENABLE_THINKING_DISPLAY`