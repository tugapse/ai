## 1. Architectural Role
Handles the injection of templates into the system prompt based on configuration settings.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `TemplateInjection` | Class | Manages the injection of templates into the system prompt. |
| `__init__` | Method | Initializes the `TemplateInjection` instance with system and task templates. |
| `replace_system_template` | Method | Replaces placeholders in the system template with injected content. |
| `_load_injection_template` | Method | Loads an injection template from a file. |

## 3. Execution Logic & Flow
- **Initialization**: The `__init__` method sets the `system_template` and `task_template` attributes. If no `system_template` is provided, it defaults to an empty string.
- **Data Path**: The `replace_system_template` method processes the `system_template` by replacing placeholders with content from injected templates. The `task_template` is not used in this method.
- **Conditional Branching**: The method iterates over a list of injection templates specified in the configuration. For each template, it checks if the template file exists and replaces the corresponding placeholder in the `system_template`.

## 4. Resource Dependencies
- **Standard Libraries**: `os`
- **Internal Modules**: `functions`
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: None
- **Environment Lookups**: `ProgramConfig.current.config.get("INJECT_TEMPLATES",[])` and `ProgramConfig.current.get(ProgramSetting.PATHS_INJECT_TEMPLATES)`