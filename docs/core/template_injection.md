## 1. Architectural Role
Provides a mechanism to dynamically inject external markdown template content into a system prompt by replacing predefined keys with file-based content.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `TemplateInjection` | Class | Orchestrates the loading and replacement of template placeholders within a system string. |
| `__init__` | Method | Initializes the instance with `system_template`, optional `task_template`, and optional `program` reference. |
| `replace_system_template` | Method | Iterates through configured injections to replace keys in the system template with loaded file content. |
| `_load_injection_template` | Method | Resolves the filesystem path for a template name and reads its content via `functions.read_file`. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Receives `system_template` (string) and `task_template` (optional string).
    2. Assigns `system_template` to `self.system_template` (defaults to empty string if None).
    3. Assigns `task_template` to `self.task_template`.
- **Data Path**: 
    `ProgramConfig` (Injection List) $\rightarrow$ `_load_injection_template` (File I/O) $\rightarrow$ `replace_system_template` (String Substitution) $\rightarrow$ Modified System Template.
- **Conditional Branching**:
    1. **Template Loading**: In `_load_injection_template`, the code checks `os.path.exists(filepath)`; if true, it returns file content; otherwise, it returns an empty string.
    2. **Injection Loop**: `replace_system_template` iterates over the list retrieved from `INJECT_TEMPLATES`; if the list is empty, the original `system_template` is returned unchanged.

## 4. Resource Dependencies
- **Standard Libraries**: `os`
- **Internal Modules**: `config` (`ProgramConfig`, `ProgramSetting`), `functions`

## 5. Configuration & Environment
- **Hardcoded Constants**: `.md` (used for file extension normalization).
- **Environment Lookups**: 
    - `ProgramConfig.current.config.get("INJECT_TEMPLATES")`: Retrieves the list of key-value pairs for injection.
    - `ProgramConfig.current.get(ProgramSetting.PATHS_INJECT_TEMPLATES)`: Retrieves the base directory path for template files.