## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **TemplateInjection** | [src/ai/core/template_injection.py](/AgentDocs/ai/core/template_injection.md) |

The `TemplateInjection` class is responsible for the dynamic construction of system prompts by injecting content from external markdown files into predefined template placeholders. It allows the system to maintain a modular prompt architecture where specific sections of a system instruction can be swapped or updated via configuration without modifying the core logic.

This component functions as a utility within the AI core layer, bridging the gap between static configuration and the final prompt strings sent to Large Language Models. It relies on the global program configuration to determine which templates to load and where they are located on the filesystem.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `TemplateInjection(system_template, task_template=None, program=None)` | Class | Initializes the injector with a base `system_template` string, an optional `task_template`, and an optional `program` instance. |
| `replace_system_template()` | Method | Iterates through configured injections (retrieved via `ProgramConfig`), loads the corresponding `.md` files, and performs string replacement on the `system_template`. Returns the processed string. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The component uses a key-value replacement strategy. It fetches a list of injection definitions from `ProgramConfig.get_current().config["INJECT_TEMPLATES"]`. For each definition, it identifies a `key` (the placeholder in the string) and a `value` (the filename). It ensures all files are treated as `.md` files by normalizing the filename before attempting to load.
- **Side Effects:** 
    - **Filesystem Access:** Performs read operations on the local filesystem to retrieve template content via `func.read_file`.
    - **Configuration Access:** Interacts with the global `ProgramConfig` to retrieve injection lists and directory paths.
- **Error Handling:** If a specified template file does not exist at the constructed path, the method `_load_injection_template` returns an empty string rather than raising an exception, resulting in the placeholder being replaced by nothing.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `INJECT_TEMPLATES`  A list of dictionaries within the program configuration containing `key` (placeholder) and `value` (template filename) pairs.
- `ProgramSetting.PATHS_INJECT_TEMPLATES`  A configuration key used to resolve the directory path where template files are stored.

**Module Dependencies:**
- **Standard/External:** 
    - `os`  Used for path manipulation and checking file existence.
- **Internal:**
    - [ProgramConfig](/AgentDocs/ai/config.md)  Used to access runtime configuration and injection settings.
    - [ProgramSetting](/AgentDocs/ai/config.md)  Used to resolve configuration keys for template paths.
    - [func](/AgentDocs/ai/functions.md)  Used for file I/O operations.