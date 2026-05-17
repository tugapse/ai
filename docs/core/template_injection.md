## 1. Architectural Role

**Functional Mission**
The **TemplateInjection** class is responsible for the dynamic augmentation of system prompts through the programmatic replacement of predefined placeholders. Its core mission is to facilitate modular prompt engineering by allowing the system to inject external contentloaded from specialized markdown filesinto a base system template, ensuring that the LLM receives contextually enriched instructions without hardcoding complex strings.

**System Context & Integration**
This component acts as a middleware layer in the prompt construction pipeline. It sits between the raw configuration settings and the final prompt delivery to the LLM. By consuming configurations from `ProgramConfig` and utilizing file-system utilities via `functions`, it transforms static templates into dynamic, context-aware system instructions. This processed output is critical for downstream modules that require highly specific behavioral constraints or domain-specific knowledge injected directly into the model's system persona.

## 2. Environment & Configuration

**Environment Lookups:**
- `INJECT_TEMP_LATES` (via `ProgramConfig.get_current().config.get`)  Retrieves a list of injection key-value pairs defining which placeholders to replace.
- `PATHS_INJECT_TEMP_LATES` (via `ProgramConfig.get_current().get`)  Retrieves the directory path where injection markdown templates are stored.

**Hardcoded Constants:**
- `".md"` (Default: `".md"`)  Used to enforce the markdown file extension during template loading.

## 3. Interface & API Surface

| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `TemplateInjection` | Class | Orchestrates the lifecycle of template loading and placeholder substitution. |
| `__init__` | Method | Initializes the instance with a base `system_template`, an optional `task_template`, and an optional `program` reference. |
| `replace_system_template` | Method | Iterates through configured injections to perform string replacement on the `system_template`. |
| `_load_injection_template` | Method | Performs file I/O to read the content of a specific markdown template from the configured directory. |

## 4. Execution Logic & Flow

- **Initialization**: The class is instantiated with a `system_template` string. It stores the template and optionally accepts a `task_template` and a `program` object for stateful context.
- **Data Path**: 
    1. `replace_system_template` is invoked.
    2. The method fetches the list of injections from `ProgramConfig`.
    3. For each injection entry, the `key` (placeholder) and `value` (filename) are processed.
    4. `_load_injection_template` is called to resolve the filename into a full path and read the file content via `functions.read_file`.
    5. The `replaced_text` is updated by replacing the `key` with the loaded content.
    6. The final augmented string is returned.
- **Conditional Branching**: 
    - In `_load_injection_template`, the system checks `os.path.exists(filepath)`. If the file exists, it returns the content; otherwise, it returns an empty string to prevent execution failure.

## 5. Resource Dependencies

- **Standard Libraries**: `os`
- **Internal Modules**: 
    - [ProgramConfig](/docs/config.md)
    - [ProgramSetting](/docs/config.md)
    - [functions](/docs/functions.md)
- **External Packages**: None identified.