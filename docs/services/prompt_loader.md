## 1. Architectural Role
[services/prompt_loader.py](services/prompt_loader.py) serves as the specialized retrieval and preparation engine for system instructions. It is responsible for resolving system prompt locations via a prioritized hierarchyexplicit paths, template directories, or built-in defaultsand subsequently performing template variable injection using [core/template_injection.md](core/template_injection.md) to produce a finalized string ready for LLM consumption.

## 2. Environment & Configuration
**Environment Lookups:**
- `PATHS_SYSTEM_TEMPLATES` (via `config.get`)  Retrieves the directory path configured for system prompt templates.

**Hardcoded Constants:**
- `DEFAULT_SYSTEM_PROMPT` (Default: `"You are a helpful AI assistant."`)  The fallback string used when no file is found and the user specifies "default".

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `PromptLoader` | Class | Container for static prompt resolution logic. |
| `load_system_prompt` | Func | Orchestrates the resolution, reading, and template injection of a system prompt based on provided config and settings. |

## 4. Execution Logic & Flow
- **Initialization**: Receives `ProgramConfig` and a `system_file_setting` string.
- **Data Path**: 
    1. **Input**: `system_file_setting` (Path or identifier).
    2. **Resolution**: 
        - Check if `system_file_setting` is a valid local file path.
        - If not, check the directory defined by `PATHS_SYSTEM_TEMPLATES` (appending `.md` if necessary).
        - If "default" is specified, attempt to locate the built-in repo template.
    3. **Processing**: 
        - Read file content via `func.read_file`.
        - Fallback to `DEFAULT_SYSTEM_PROMPT` if "default" was requested but no file was found.
        - Pass raw content through `TemplateInjection.replace_system_template()`.
    4. **Output**: Returns the processed/injected system prompt string.
- **Conditional Branching**:
    - **Path Resolution**: Prioritizes `os.path.exists(system_file_setting)` $\rightarrow$ `templates_dir` $\rightarrow$ `repo_root/templates/system/default.md`.
    - **Empty Content**: If no content is successfully loaded, logs a warning and proceeds with an empty string to the injection engine.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `pathlib`, `typing`
- **Internal Modules**: 
    - [functions](functions.md)
    - [services/config_helper.py](services/config_helper.md)
    - [core/template_injection.md](core/template_injection.md)
- **External Packages**: None identified.