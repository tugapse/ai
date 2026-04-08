## 1. Architectural Role
Manages loading and processing of system prompt files.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `PromptLoader` | Class | Loads and processes system prompt files based on configuration and file settings. |
| `load_system_prompt` | Static Method | Reads and processes the content of a system prompt file. |

## 3. Execution Logic & Flow
- **Initialization**: No explicit initialization is performed.
- **Data Path**: 
  1. The method `load_system_prompt` is called with a `ProgramConfig` object and a `system_file_setting` string.
  2. It first checks if `system_file_setting` is provided and if it exists.
  3. If not, it checks if a system templates directory is specified in the configuration and if the file exists in that directory.
  4. If a valid file path is found, it reads the content of the file.
  5. If no valid file is found, it logs a warning.
  6. It then processes the content using `TemplateInjection` to replace system templates.
- **Conditional Branching**: 
  - Checks if `system_file_setting` is provided.
  - Checks if the file exists at the explicit path or in the templates directory.
  - Logs warnings if the file is not found.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `pathlib`, `typing`
- **Internal Modules**: `functions`, `config`, `core.template_injection`
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: None
- **Environment Lookups**: None