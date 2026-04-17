## 1. Architectural Role
Provides a high-level execution wrapper for performing a single, direct LLM request with integrated UI orchestration, token sanitization, and optional file persistence.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `_sanitize_token` | Func | Normalizes unicode characters and strips non-ASCII/non-printable characters from tokens. |
| `ask` | Func | Orchestrates the end-to-end lifecycle of a single LLM query, including UI setup, streaming, and output handling. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Loads `ProgramConfig`.
    2. Instantiates `UIOrchestrator`.
    3. Sets `ThinkingAnimationHandler.THINKING_PREFIX` to "Processing request".
    4. Initializes UI components (`printer`, `handler`) and configures thinking animation visibility.
- **Data Path**: 
    1. **Input**: `input_message` (string or list) $\rightarrow$ converted to `messages` list via `BaseModel.create_message`.
    2. **Processing**: `llm.chat` generates a stream of `raw_token` $\rightarrow$ `_sanitize_token` $\rightarrow$ `handler.process_token_chain`.
    3. **Output**: Processed content is routed to `printer.process_and_print` and/or appended to a file via `func.write_to_file`.
- **Conditional Branching**:
    - **Input Type**: If `input_message` is `str`, it is wrapped in a list; otherwise, it is used as-is.
    - **File Output**: If `write_to_file` and `output_filename` are true, the directory is created and the file is initialized/appended.
    - **UI Visibility**: If `hide_think_anim` is true, the thinking animation is disabled.
    - **Output Routing**: If `print_output` is true, tokens are sent to the printer.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `re`, `unicodedata`, `time`, `typing`
- **Internal Modules**: `functions`, `color`, `core.llms.base_llm`, `core.chat`, `config`, `services.ui_orchestrator`, `extras.think_parser`

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `ThinkingAnimationHandler.THINKING_PREFIX = "Processing request"`
    - `log_filepath = "active_thinking_process.log"`
- **Environment Lookups**: Accesses `ProgramConfig.current` or `ProgramConfig.load()`.