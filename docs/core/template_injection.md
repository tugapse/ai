## 1. Architectural Role
Manages the dynamic substitution of placeholders within system prompt templates by injecting content loaded from external Markdown files based on centralized configuration.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `TemplateInjection` | Class | Orchestrates the lifecycle of template loading and string replacement. |
| `__init__` | Method | Initializes the instance with base system and task templates. |
| `replace_system_template` | Method | Iterates through configured injections to perform string substitution on the system template. |
| `_load_injection_template` | Method | Resolves file paths and reads Markdown content from the filesystem. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. `system_template` is assigned (defaults to empty string if falsy).
    2. `task_template` is assigned.
    3. `program` instance is stored in state.
- **Data Path**: 
    1. **Input**: `self.system_template` (string) and `ProgramConfig.current.config["INJECT_TEMPLETES"]` (list of dicts).
    2. **Processing**: 
        - Loop through each injection dictionary.
        - Extract `key` (placeholder) and `value` (filename).
        - Call `_load_injection_template` to resolve `value` to a file path.
        - Use `functions.read_file` to fetch file content.
        - Execute `str.replace(key, content)` on the accumulator string.
    3. **Output**: A fully populated `replaced_text` string.
- **Conditional Branching**: 
    - Inside `_load_injection_template`: Checks `os.path.exists(filepath)`. If true, returns file content; if false, returns an empty string.

## 4. Resource Dependencies
- **Standard Libraries**: `os`
- **Internal Modules**: `config` (`ProgramConfig`, `ProgramSetting`), `functions`
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: `".md"` (extension suffix/replacement logic).
- **Environment Lookups**: 
    - `ProgramConfig.current.config["INJECT_TEMPLETES"]`
    - `ProgramConfig.current.get(ProgramSetting.PATHS_INJECT_TEMPLETES)`