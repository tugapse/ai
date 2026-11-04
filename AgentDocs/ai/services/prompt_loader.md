## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **PromptLoader** | [src/ai/services/prompt_loader.py](/src/ai/services/prompt_loader.py) |

The `PromptLoader` class provides a centralized mechanism for locating, reading, and preparing system prompts for AI interactions. It resolves prompt files through a hierarchical search strategy, starting from explicit paths, moving to configured template directories, and finally falling back to built-in repository defaults.

This component acts as a service within the AI interaction pipeline, ensuring that system instructions are correctly loaded and processed before being passed to the LLM. It integrates template injection logic to allow for dynamic content within the loaded prompts.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `PromptLoader.load_system_prompt(config: ProgramConfig, system_file_setting: str) -> str` | Static Method | Resolves a system prompt file based on the provided setting, reads its content, performs template injection via `TemplateInjection`, and returns the resulting string. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The method implements a prioritized resolution algorithm:
    1. **Explicit Path:** If `system_file_setting` exists as a valid filesystem path.
    2. **Template Directory:** If not an explicit path, it searches the directory defined by `ProgramSetting.PATHS_SYSTEM_TEMPLATES` (retrieved from `ProgramConfig`), appending `.md` if the extension is missing.
    3. **Built-in Default:** If the setting is explicitly `"default"`, it looks in the repository's `templates/system/default.md` path.
    4. **Hardcoded Fallback:** If `"default"` is requested but the file is missing, it returns the `DEFAULT_SYSTEM_PROMPT` constant.
- **Template Injection:** Once a file is read, the content is passed to [TemplateInjection](/AgentDocs/ai/core/template_injection.md) to process any dynamic placeholders.
- **Side Effects:** 
    - Performs filesystem read operations via `func.read_file`.
    - Performs filesystem existence checks via `os.path.exists`.
    - Logs operational status and warnings to the system log via `func.log` and `func.debug`.
- **Error Handling:** If no prompt can be resolved and the setting is not `"default"`, it logs a warning and proceeds with an empty string, which is then processed by the injection engine.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `ProgramConfig`  Used to retrieve the system template directory path via `ProgramSetting.PATHS_SYSTEM_TEMPLATES`.

**Module Dependencies:**
- **Standard/External:** `os`, `pathlib`, `typing`.
- **Internal:**
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.services.config_helper](/AgentDocs/ai/services/config_helper.md)
    - [ai.core.template_injection](/AgentDocs/ai/core/template_injection.md)