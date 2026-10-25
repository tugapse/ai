## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | PromptLoader |
| Source file | prompt_loader.py |

The **PromptLoader** serves as the specialized retrieval and preprocessing engine for system-level instructions within the AI framework. Its primary purpose is to resolve, load, and prepare the foundational "system prompt" that defines the persona and behavioral constraints of the AI agent.

**Functional Mission**
The **PromptLoader** is responsible for the multi-stage resolution of system prompt files. It solves the problem of prompt volatility and configuration complexity by providing a hierarchical lookup mechanism: it first attempts to use an explicit file path, then searches a configured templates directory, and finally falls back to built-in repository defaults or a hardcoded constant.

**System Context & Integration**
This component acts as a critical upstream provider for the LLM execution pipeline. By transforming raw file content into a processed string via [TemplateInjection](/docs/ai/core/template_injection.md), it ensures that all system instructions are properly formatted and injected with necessary variables before being passed to the model orchestrators. It relies heavily on [ProgramConfig](/docs/ai/services/config_helper.md) to locate template directories and [func](/docs/ai/functions.md) for filesystem operations and logging.

- **INTERNAL REFERENCES**: 
    - [TemplateInjection](/docs/ai/core/template_injection.md)
    - [ProgramConfig](/docs/ai/services/config_helper.md)
    - [ProgramSetting](/docs/ai/services/config_helper.md)
    - [func](/docs/ai/functions.md)

## 2. Environment & Configuration
**Environment Lookups:**
- `ProgramSetting.PATHS_SYSTEM_TEMPLATES` (via `config.get`)  Retrieves the directory path where system prompt templates are stored.

**Hardcoded Constants:**
- `DEFAULT_SYSTEM_PROMPT` (Default: `"You are a helpful AI assistant."`)  The ultimate fallback string used if no files are found and the user requests the "default" setting.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `PromptLoader` | Class | Container for static prompt loading utilities. |
| `load_system_prompt` | Static Method | Orchestrates the resolution, file reading, and template injection of the system prompt. |

## 4. Execution Logic & Flow
- **Initialization**: The method accepts a `ProgramConfig` instance and a `system_file_setting` string (which can be a path, a filename, or the keyword "default").
- **Data Path**: 
    1. **Input**: `system_file_setting` (string).
    2. **Resolution Phase**:
        - **Path A (Explicit)**: If `system_file_setting` is a valid existing path, use it.
        - **Path B (Template Dir)**: If not explicit, check `PATHS_SYSTEM_TEMPLATES`. Append `.md` if missing. Check if file exists in that directory.
        - **Path C (Built-in Default)**: If setting is `"default"`, attempt to locate `templates/system/default.md` relative to the repository root.
        - **Path D (Hardcoded Fallback)**: If setting is `"default"` but no file is found, use `DEFAULT_SYSTEM_PROMPT`.
    3. **Processing Phase**: Read the resolved file content using `func.read_file`.
    4. **Injection Phase**: Pass content to `TemplateInjection` to perform variable replacement.
    5. **Output**: A processed string ready for LLM consumption.
- **Conditional Branching**:
    - **File Existence**: Checks `os.path.exists` at every resolution step.
    - **Extension Handling**: Automatically appends `.md` if the template filename lacks it.
    - **Empty Content Check**: If no content is loaded, logs a warning and proceeds with an empty string to prevent total system failure.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `pathlib`, `typing`
- **Internal Modules**: 
    - [func](/docs/ai/functions.md)
    - [ProgramConfig](/docs/ai/services/config_helper.md)
    - [ProgramSetting](/docs/ai/services/config_helper.md)
    - [TemplateInjection](/docs/ai/core/template_injection.md)
- **External Packages**: None identified.