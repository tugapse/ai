## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **PromptLoader** | [src/ai/services/prompt_loader.py](/AgentDocs/ai/services/prompt_loader.md) |

The `PromptLoader` component is responsible for the discovery, retrieval, and processing of system prompt files used to define AI assistant behavior. It provides a robust mechanism for locating prompt templates across multiple hierarchy levels, ensuring that the AI interaction pipeline always has access to a valid system instruction.

This component serves as a service within the AI orchestration layer. It bridges the gap between filesystem-based prompt management and the runtime execution environment by resolving configuration settings into usable, template-injected strings. It integrates with the application's configuration system and the template injection engine to ensure prompts are dynamic and context-aware.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `PromptLoader` | Class | A utility class containing static methods for managing system prompt lifecycles. |
| `PromptLoader.load_system_prompt(config: ProgramConfig, system_file_setting: str) -> str` | Static Method | Resolves a prompt file from an explicit path, a configured template directory, or a built-in default. Returns the content after applying `TemplateInjection`. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The method `load_system_prompt` follows a specific resolution hierarchy:
    1. **Explicit Path:** Checks if `system_file_setting` exists directly on the filesystem.
    2. **Template Directory:** If not found, it looks in the directory defined by `ProgramSetting.PATHS_SYSTEM_TEMPLATES` (within `ProgramConfig`). It automatically appends a `.md` extension if missing.
    3. **Built-in Default:** If the setting is the string `"default"`, it attempts to locate a file at `templates/system/default.md` relative to the repository root.
    4. **Hardcoded Fallback:** If all file lookups fail and the setting was `"default"`, it returns `DEFAULT_SYSTEM_PROMPT`.
- **Template Processing:** Once a file is read, the content is passed through `TemplateInjection.replace_system_template()` to resolve any dynamic placeholders.
- **Side Effects:** 
    - Performs filesystem read operations via `func.read_file`.
    - Performs filesystem existence checks via `os.path.exists`.
    - Generates logs at various levels (`INFO`, `DEBUG`, `WARNING`) via `ai.functions`.
- **Error Handling:** The component does not throw exceptions for missing files; instead, it logs a `WARNING` and returns either a fallback string or an empty/partially processed string to prevent pipeline crashes, allowing the system to continue without a system prompt if necessary.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `ProgramConfig`  Used to retrieve `ProgramSetting.PATHS_SYSTEM_TEMPLATES` to locate the system template directory.

**Module Dependencies:**
- **Standard/External:** `os`, `pathlib`, `typing`.
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.services.config_helper](/AgentDocs/ai/services/config_helper.md)
    - [ai.core.template_injection](/AgentDocs/ai/core/template_injection.md)