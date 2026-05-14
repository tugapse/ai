## 1. Architectural Role
Orchestrates a single-turn LLM request by managing UI initialization, token streaming, real-time terminal rendering, and optional file persistence.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `_sanitize_token` | Func | Normalizes input tokens using NFKC and strips non-printable ASCII characters. |
| `ask` | Func | Executes the primary workflow: UI setup, message preparation, LLM streaming, and output handling. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Captures `start_time`.
    2. Loads/instantiates `ProgramConfig`.
    3. Initializes `UIOrchestrator` and sets `ThinkingAnimationHandler.THINKING_PREFIX`.
    4. Initializes UI components (`printer`, `handler`) and configures thinking animation visibility.
- **Data Path**: 
    1. **Input**: `input_message` (str or List[Dict]) is converted into a standard message format via `BaseModel.create_message`.
    2. **Processing**: `llm.chat` generates a stream of `raw_token` values.
    3. **Transformation**: `raw_token` $\rightarrow$ `_sanitize_token` $\rightarrow$ `handler.process_token_chain` $\rightarrow$ `content` (displayable string).
    4. **Output**: `content` is routed to `printer.process_and_print` (terminal) and `func.write_to_file` (disk).
- **Conditional Branching**:
    - If `input_message` is `str`, wrap in `ChatRoles.USER`.
    - If `write_to_file` and `output_filename` are provided, initialize/truncate the target file.
    - If `display_to_user` is true, trigger terminal printing.
    - If `write_to_file` and `content` exists, append content to disk using `func.FILE_MODE_APPEND`.
    - If `KeyboardInterrupt` occurs, abort the task and log the interruption.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `re`, `unicodedata`, `time`, `typing`
- **Internal Modules**: `functions`, `color`, `core.llms.base_llm`, `chat.chat`, `config`, `services.ui_orchestrator`, `extras.think_parser`
- **External Packages**: None explicitly imported (relies on internal abstractions)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `ThinkingAnimationHandler.THINKING_PREFIX = "Processing request"`
    - `func.FILE_MODE_APPEND` (used for file writing)
- **Environment Lookups**: 
    - `ProgramConfig.current` or `ProgramConfig.load()` (loads system configuration)