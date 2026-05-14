## 1. Architectural Role

**Functional Mission**
The **PromptLoader** component is responsible for the retrieval, resolution, and processing of system prompt templates used to define AI persona and behavior. Its core mission is to abstract the complexity of locating prompt fileswhether they are provided via explicit absolute paths, relative filenames within a configured templates directory, or built-in repository defaultsand ensuring the resulting string is processed through the template injection engine.

**System Context & Integration**
This component acts as a critical data provider for the LLM orchestration layer. It consumes configuration settings via [ProgramConfig](/docs/services/config_helper.md) to determine filesystem search paths and utilizes [TemplateInjection](/docs/core/template_injection.md) to transform raw file content into actionable system instructions. By resolving these prompts early in the execution flow, it provides the foundational context required by downstream modules to maintain consistent AI behavior.

## 2. Environment & Configuration
**Environment Lookups:**
- `PATHS_SYSTEM_TEMP_LATES` (via `config.get`)  Retrieves the directory path where system prompt templates are stored.

**Hardcoded Constants:**
- `DEFAULT_SYSTEM_PROMPT` (Default: `"You are a helpful AI assistant."`)  The fallback string used when no valid prompt file can be resolved for the "default" setting.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `PromptLoader` | Class | Static utility class for managing system prompt lifecycle. |
| `load_system_prompt` | Static Method | Orchestrates the lookup, file reading, and template injection of a system prompt based on a provided configuration and filename setting. |

## 4. Execution Logic & Flow
- **Initialization**: The method accepts a `ProgramConfig` object and a `system_file_setting` string. It initializes an empty `system_prompt_content` string and a `resolved_filepath` tracker.
- **Data Path**: 
    1. **Input**: A filename or path string (`system_file_setting`).
    2. **Resolution Phase**:
        - **Explicit Path**: If the input is a valid existing file path, it is used directly.
        - **Template Directory**: If not an explicit path, the system looks in the directory defined by `PATHS_SYSTEM_TEMP_LATES`. It automatically appends `.md` if the extension is missing.
        - **Built-in Default**: If the setting is `"default"`, it attempts to locate a specific `default.md` within the repository's `templates/system` directory.
    3. **Loading Phase**: The file content is read from the `resolved_filepath` using `func.read_file`.
    4. **Fallback Phase**: If no file is found and the setting was `"default"`, the `DEFAULT_SYSTEM_PROMPT` is used.
    5. **Processing Phase**: The raw content is passed to `TemplateInjection` to perform variable/template replacement.
    6. **Output**: Returns the final processed string.
- **Conditional Branching**:
    - **Path Existence**: Checks `os.path.exists` at multiple stages (explicit, template dir, and built-in).
    - **Extension Check**: Appends `.md` if the provided filename lacks it.
    - **Empty Content Check**: Logs a warning if `system_prompt_content` remains empty after all resolution attempts.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `pathlib`, `typing`
- **Internal Modules**: 
    - [functions](/docs/functions.md)
    - [ProgramConfig](/docs/services/config_helper.md)
    - [ProgramSetting](/docs/services/config_helper.md)
    - [TemplateInjection](/docs/core/template_injection.md)
- **External Packages**: None identified.