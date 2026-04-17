## 1. Architectural Role
Provides a utility function to resolve, validate, and load JSON-based pipeline configurations and their associated agent prompt files from the filesystem.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `load_pipeline_config` | Function | Parses a pipeline JSON file and verifies the existence of all referenced prompt files, returning a dictionary of the configuration. |

## 3. Execution Logic & Flow
- **Initialization**: Appends the current file's directory to `sys.path` to ensure local module resolution.
- **Data Path**: `pipeline_file` (path) $\rightarrow$ `json.load()` $\rightarrow$ Prompt path validation $\rightarrow$ `config` (dict).
- **Conditional Branching**:
    1. **Path Resolution**: Checks if `pipeline_file` is absolute; if not, joins it with the `ROOT_DIRECTORY` from `prog.config`.
    2. **Existence Check**: If the resolved `pipeline_path` does not exist, logs an error via `func.error` and returns an empty dictionary.
    3. **Prompt Validation**: Iterates through `agents` in the config; if a `prompt_file` is defined, it resolves the path and checks for existence. If any prompt file is missing, logs an error and returns an empty dictionary.
    4. **Exception Handling**: Wraps the parsing process in a try-except block to catch JSON or IO errors, returning an empty dictionary on failure.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `sys`, `json`
- **Internal Modules**: `functions` (as `func`), `config.ProgramSetting`, `.tool_registry.ToolRegistry`, `.llm_connector.LLMConnector`, `.message_orchestrator.MessageOrchestrator`

## 5. Configuration & Environment
- **Hardcoded Constants**: None.
- **Environment Lookups**: `ProgramSetting.ROOT_DIRECTORY` (accessed via the `prog` object).