## 1. Architectural Role
Provides a centralized mechanism for locating, reading, and processing system prompt files from explicit paths, template directories, or built-in fallbacks, while applying template injection.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `DEFAULT_SYSTEM_PROMPT` | Constant | Provides a hardcoded fallback string if no files are found for the "default" setting. |
| `PromptLoader` | Class | Acts as a stateless utility container for prompt loading logic. |
| `load_system_prompt` | Static Method | Orchestrates the resolution of file paths, file reading, and template processing. |

## 3. Execution Logic & Flow
- **Initialization**: The module defines a constant `DEFAULT_SYSTEM_PROMPT` and the `PromptLoader` class structure upon import.
- **Data Path**: `system_file_setting` (str) $\rightarrow$ Path Resolution Logic $\rightarrow$ `system_prompt_content` (str) $\rightarrow$ `TemplateInjection` processing $\rightarrow$ Final processed prompt (str).
- **Conditional Branching**:
    1. **Check `system_file_setting` presence**: If null/empty, logs absence and proceeds to injection with empty content.
    2. **Explicit Path Check**: If `os.path.exists(system_file_setting)` is true, uses provided path.
    3. **Template Directory Resolution**: If explicit path fails, attempts to find file in `config.get(ProgramSetting.PATHS_SYSTEM_TEMPLATES)`.
        - Appends `.md` extension if missing.
        - If directory is missing in config, defaults to `root/system`.
    4. **Built-in Default Check**: If `system_file_setting` is "default", attempts to locate `repo_root/templates/system/default.md`.
    5. **Fallback Logic**: 
        - If "default" was requested but file not found $\rightarrow$ uses `DEFAULT_SYSTEM_PROMPT`.
        - If any other file is requested but not found $\rightarrow$ uses empty string.
    6. **Template Injection**: Passes the resulting string into `TemplateInjection.replace_system_template()`.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `pathlib.Path`, `typing.Optional`
- **Internal Modules**: `functions` (as `func`), `services.config_helper` (`ProgramConfig`, `ProgramSetting`), `core.template_injection.TemplateInjection`

## 5. Configuration & Environment
- **Hardcoded Constants**: `DEFAULT_SYSTEM_PROMPT = "You are a helpful AI assistant."`
- **Environment Lookups**: 
    - `config.get(ProgramSetting.PATHS_SYSTEM_TEMPLATES)`: Retrieves the system templates directory path.
    - `func.get_root_directory()`: Used to construct a default path if config is missing.
    - `Path(__file__).resolve()`: Used to calculate the repository root for built-in templates.