## 1. Architectural Role
The `UIOrchestrator` class serves as the central management layer for the assistant's visual feedback systems. It orchestrates the interaction between thought process visualization, token-buffered output streaming, and console formatting. By aggregating the [extras/thinking_log_manager.md](extras/thinking_log_manager.md), [extras/output_printer.md](extras/output_printer.md), [extras/handler_manager.md](extras/handler_manager.md), and [extras/console.md](extras/console.md) components, it provides a unified interface for the [services/stream_orchestrator.md](services/stream_orchestrator.md) to manage the user's terminal experience.

## 2. Environment & Configuration
**Environment Lookups:**
- `PRINT_MODE` (via `config.get`)  Determines the text streaming strategy (e.g., "line_or_x_tokens").
- `TOKEN_PER_PRINT` (via `config.get`)  Sets the chunk size for token buffering.
- `THINKING_MODE` (via `config.get`)  Defines the visual style for thought processes (e.g., "progressbar").
- `ENABLE_THINKING_DISPLAY` (via `config.get`)  Boolean flag to toggle visibility of internal reasoning.

**Hardcoded Constants:**
- `tokens_per_print` (Default: `50`)  Default buffer size if not specified in config.
- `show_thinking_animation` (Default: `True`)  Forces animation of thinking states.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `UIOrchestrator` | Class | Orchestrates the lifecycle of UI/UX feedback components. |
| `initialize` | Method | Instantiates and configures the log manager, printer, and handler manager using `ProgramConfig`. |
| `reset_turn` | Method | Flushes buffers and clears token formatting to prepare for a new interaction. |
| `get_components` | Method | Returns a dictionary containing the `printer`, `handler`, and `formatter` for external consumption. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. `__init__` sets core components (`log_manager`, `printer`, `handler`, `formatter`) to `None` or default instances.
    2. `initialize` executes the setup sequence:
        - Creates `ThinkingLogManager` with the provided `log_filepath`.
        - Creates `OutputPrinter` using configured print modes and token thresholds.
        - Creates `HandlerManager` to link logs with progress bar animations.
- **Data Path**:
    - **Input**: `ProgramConfig` settings $\rightarrow$ **Processing**: Component instantiation via `initialize()` $\rightarrow$ **Output**: A dictionary of active UI tools via `get_components()`.
- **Conditional Branching**:
    - `reset_turn` checks if `self.printer` is instantiated before attempting to call `flush_buffers()`.

## 5. Resource Dependencies
- **Standard Libraries**: `typing`
- **Internal Modules**: 
    - [services/config_helper.md](services/config_helper.md)
    - [extras/thinking_log_manager.md](extras/thinking_log_manager.md)
    - [extras/output_printer.md](extras/output_printer.md)
    - [extras/handler_manager.md](extras/handler_manager.md)
    - [extras/console.md](extras/console.md)
    - [functions.md](functions.md)
- **External Packages**: None identified.