## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | TemplateInjection |
| Source file | template_injection.py |

The **TemplateInjection** component is responsible for the dynamic augmentation of system prompts through the injection of external template files. It acts as a middleware layer between static prompt definitions and the final string sent to a Large Language Model, allowing the system to modularize complex instructions, personas, or context constraints into manageable, file-based components.

**Functional Mission**
The primary responsibility of **TemplateInjection** is to automate the replacement of specific placeholders within a base system template with content retrieved from external Markdown files. This solves the problem of "prompt bloat" and hardcoded instruction sets by allowing developers to inject reusable logic or context dynamically based on the current program configuration.

**System Context & Integration**
This component integrates deeply with the configuration management system to determine which injections are required for a given execution context. It relies on [ProgramConfig](/docs/ai/config.md) to retrieve the `INJECT_TEMPLATES` list and the directory paths for template storage. Once the placeholders are replaced, the resulting string is typically passed downstream to LLM orchestration modules to form the complete system instruction.

- **INTERNAL REFERENCES**: [ProgramConfig](/docs/ai/config.md), [ProgramSetting](/docs/ai/config.md), [func](/docs/ai/functions.md).

## 2. Environment & Configuration
**Environment Lookups:**
- `INJECT_TEMPLATES` (via `ProgramConfig.get_current().config.get`)  A list of dictionaries containing `key` (placeholder) and `value` (filename) for template replacement.
- `PATHS_INJECT_TEMPLATES` (via `ProgramConfig.get_current().get`)  The filesystem path where injection `.md` files are stored.

**Hardcoded Constants:**
- `".md"` (Default: `".md"`)  Used to enforce the Markdown file extension during template loading.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `TemplateInjection` | Class | Orchestrates the lifecycle of template loading and string replacement. |
| `__init__` | Method | Initializes the component with base system and optional task templates. |
| `replace_system_template` | Method | Iterates through configured injections and performs string substitution on the system template. |
| `_load_injection_template` | Method | Handles filesystem I/O to read template content from the designated directory. |

## 4. Execution Logic & Flow
- **Initialization**: The class is instantiated with a `system_template` string. It optionally accepts a `task_template` and a `program` instance (though `program` is currently unused in the provided logic).
- **Data Path**: 
    1. `replace_system_template` is called.
    2. It fetches the `INJECT_TEMPLATES` list from [ProgramConfig](/docs/ai/config.md).
    3. For each injection entry, it calls `_load_injection_template`.
    4. `_load_injection_template` constructs a path by appending `.md` to the provided value and reads the file via [func.read_file](/docs/ai/functions.md).
    5. The placeholder `key` in the `replaced_text` is swapped with the file content.
    6. The final augmented string is returned.
- **Conditional Branching**: 
    - In `_load_injection_template`, an `os.path.exists` check is performed. If the template file is missing, it returns an empty string `""` instead of raising an error, preventing a total system crash during prompt construction.

## 5. Resource Dependencies
- **Standard Libraries**: `os`
- **Internal Modules**: 
    - [ProgramConfig](/docs/ai/config.md)
    - [ProgramSetting](/docs/ai/config.md)
    - [func](/docs/ai/functions.md)
- **External Packages**: None identified.