## 1. Architectural Role
The [template_injection.py](src/ai/core/template_injection.py) module serves as a dynamic content augmentation engine responsible for modifying system prompt templates. It facilitates the injection of external markdown-based content into predefined placeholders within a base system template, allowing for modular and configurable prompt construction based on runtime configuration settings.

## 2. Environment & Configuration
**Environment Lookups:**
- `INJECT_TEMPPLATES` (via `ProgramConfig.current.config.get`)  Retrieves a list of key-value pairs defining which placeholders to replace and which template files to load.
- `PATHS_INJECT_TEMPPLATES` (via `ProgramConfig.current.get`)  Retrieves the filesystem directory path where injection markdown files are stored.

**Hardcoded Constants:**
- `.md` (Default: `.md`)  String suffix used to enforce markdown file extensions during template loading.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `TemplateInjection` | Class | Manages the lifecycle of template substitution and file-based injection. |
| `__init__` | Method | Initializes the instance with `system_template`, an optional `task_template`, and an optional `program` instance. |
| `replace_system_template` | Method | Iterates through configured injections to perform string replacement on the `system_template`. |
| `_load_injection_template` | Method | Handles filesystem I/O to read template content from the designated injection directory. |

## 4. Execution Logic & Flow
- **Initialization**: Stores the `system_template` and `task_template`. The state is prepared for subsequent string manipulation.
- **Data Path**: 
    1. **Input**: `system_template` (string) + `INJECT_TEMPPLATES` config list.
    2. **Processing**: `replace_system_template` loops through the config; for each entry, `_load_injection_template` performs a path join and filesystem read.
    3. **Output**: A fully concatenated `replaced_text` string where placeholders are swapped with file contents.
- **Conditional Branching**:
    - `os.path.exists(filepath)`: If the constructed path exists, the file is read via `functions.read_file`; otherwise, an empty string is returned to prevent injection failure.

## 5. Resource Dependencies
- **Standard Libraries**: `os`
- **Internal Modules**: 
    - [config](config.md)
    - [functions](functions.md)
    - [program](program.md)
- **External Packages**: None identified.