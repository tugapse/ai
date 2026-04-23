## 1. Architectural Role
The `PromptLoader` class provides a centralized mechanism for locating, reading, and processing system prompt files from either explicit paths or a configured templates directory, applying template injection before returning the final string.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `PromptLoader` | Class | Container for system prompt loading logic. |
| `load_system_prompt` | Static Method | Resolves the file path for a system prompt, reads its content, and processes it via `TemplateInjection`. |

## 3. Execution Logic & Flow
- **Initialization**: No instance state; the class operates via a static method.
- **Data Path**: `ProgramConfig` + `system_file_setting` $\rightarrow$ Path Resolution $\rightarrow$ File Read $\rightarrow$ `TemplateInjection` $\rightarrow$ Processed String.
- **Conditional Branching**:
    1. **Input Check**: If `system_file_setting` is empty, skip resolution and log missing configuration.
    2. **Explicit Path**: If `system_file_setting` exists as a valid path on disk, use it directly.
    3. **Template Directory**: If explicit path fails and `PATHS_SYSTEM_TEMPLATES` is configured:
        - Append `.md` extension if missing.
        - Check for existence within the templates directory.
    4. **Fallback**: If no path is resolved, log a warning and proceed with an empty string.
    5. **Processing**: Pass the resulting content (empty or populated) to `TemplateInjection.replace_system_template()`.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `pathlib`, `typing`
- **Internal Modules**: `functions`, `config`, `core.template_injection`
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: `.md` (File extension suffix).
- **Environment Lookups**: `ProgramSetting.PATHS_SYSTEM_TEMPLATES` (Accessed via `ProgramConfig`).