## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| TemplateInjection | ai/core/template_injection.md |

This component is responsible for dynamically modifying a base system prompt by injecting content from external template files. It resolves placeholders defined in the system template by looking up corresponding keys in the application's configuration and loading the associated content from specified template files.

This class functions as a crucial service layer within the application's prompt engineering pipeline. It integrates configuration data retrieved via `ProgramConfig` and relies on filesystem operations managed by `ai.functions` to ensure the system prompt is contextually rich before being passed to the core AI model.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| TemplateInjection | Class | Handles injection of templates into the system prompt. |
| replace_system_template | Method | Replaces placeholders in the system template with injected content by iterating through configured template injections. Returns the modified string. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `replace_system_template` method reads the "INJECT_TEMPLATES" list from the global configuration. It iterates over each injection definition, calls `_load_injection_template` to fetch the content based on the defined file name, and sequentially replaces placeholders (keys) in the base system template with the loaded content. The `_load_injection_template` method constructs a full path by combining the configured template directory with the template name, enforcing a `.md` extension.

- **Side Effects:** Reads from the filesystem (via `os.path.exists` and `func.read_file`) to load template content. It interacts with the global state via `ProgramConfig.get_current()` to retrieve configuration settings.

- **Error Handling:** If the constructed filepath does not exist, `_load_injection_template` gracefully returns an empty string, preventing runtime errors during template loading.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`
- **Internal:** [ai.config](/ai/config.md), [ai.functions](/ai/functions.md)