## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| PromptLoader | [prompt_loader](/ai/services/prompt_loader.md) |

This component is responsible for the entire lifecycle of loading system prompts used by the AI engine. Its primary responsibility is to locate, read, and preprocess the system prompt content from various potential sources, ensuring that a usable prompt string is always available for the AI pipeline.

It functions as a crucial service layer component within the application architecture. It orchestrates the search across explicit configuration paths, configured template directories, and finally falls back to hardcoded defaults, integrating with [TemplateInjection](/ai/core/template_injection.md) to prepare the final, injectable prompt.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| PromptLoader.load_system_prompt | Static Method | Reads and processes the content of a system prompt file. Attempts to load from explicit path, template directory, or built-in default. Returns the processed string. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `load_system_prompt` method executes a tiered search algorithm. It first checks the explicit path provided in the configuration. If not found, it checks a configurable template directory, appending `.md` if necessary. If neither path succeeds, it checks for the special "default" setting, which triggers a search for a hardcoded `default.md` within the repository's template structure. If all searches fail, it falls back to a hardcoded `DEFAULT_SYSTEM_PROMPT`. Finally, the loaded content is passed to [TemplateInjection](/ai/core/template_injection.md) for template replacement.

- **Side Effects:** Reads from the filesystem (via `os.path.exists` and `func.read_file`).

- **Error Handling:** Uses multiple fallback mechanisms: an explicit default string if `system_file_setting` is "default" but the file isn't found, and a warning log if no prompt can be loaded at all.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- None

**Module Dependencies:**
- **Standard/External:** `os`, `pathlib`
- **Internal:** [ai.functions](/ai/functions.md), [ai.services.config_helper](/ai/services/config_helper.md), [ai.core.template_injection](/ai/core/template_injection.md)