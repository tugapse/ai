## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **TemplateInjection** | [src/ai/core/template_injection.py](/src/ai/core/template_injection.py) |

The `TemplateInjection` class is responsible for dynamically augmenting system prompts by injecting content from external Markdown files into predefined placeholders. It provides a mechanism to keep base system templates clean while allowing modular insertion of task-specific instructions, context, or specialized personas.

This component functions as a utility within the core AI logic, bridging the gap between static configuration and dynamic prompt construction. It relies on the global program configuration to determine which templates to load and where to find them on the filesystem.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `TemplateInjection(system_template, task_template=None, program=None)` | Class | Initializes the injector with a base `system_template` string and optional task/program references. |
| `replace_system_template()` | Method | Iterates through configured injections (from `ProgramConfig`), loads the corresponding `.md` files, and replaces placeholders in the `system_template`. Returns the processed string. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The class uses a key-value replacement strategy. It retrieves a list of injection definitions from the `INJECT_TEMPLATES` key within the current `ProgramConfig`. For each definition, it takes a `key` (the placeholder in the text) and a `value` (the filename), loads the file content via `ai.functions.read_file`, and performs a string replacement on the `system_template`.
- **Side Effects:** 
    - **Filesystem Access:** Performs read operations on the filesystem to load `.md` template files.
    - **Configuration Access:** Interacts with the global `ProgramConfig` state to retrieve injection lists and directory paths.
- **Error Handling:** If a specified template file does not exist at the constructed path, the method returns an empty string for that specific injection rather than raising an exception, ensuring the replacement process can continue.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `INJECT_TEMPLATES`  A list of dictionaries within the program configuration containing `key` (placeholder) and `value` (template filename) pairs.
- `ProgramSetting.PATHS_INJECT_TEMPLATES`  A configuration setting used to resolve the base directory for template files.

**Module Dependencies:**
- **Standard/External:** `os`
- **Internal:**
    - [ai.config.ProgramConfig](/src/ai/config.md)
    - [ai.config.ProgramSetting](/src/ai/config.md)
    - [ai.functions](/src/ai/functions.md)