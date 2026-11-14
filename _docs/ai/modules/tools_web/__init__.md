## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| tools_web | /ai/modules/tools_web/__init__.md |

This component serves as the primary entry point and configuration wrapper for the web-related tools within the AI system. Its core responsibility is to aggregate specific functionalities—namely web searching and web page reading—into a cohesive, manageable set of tools available to the core AI engine. It encapsulates the logic for defining which tools are available and how they are instantiated.

Architecturally, this module acts as a service layer provider for external data retrieval. It exposes a standardized `ToolModule` instance, allowing higher-level components like the main execution pipeline or agent controllers to seamlessly interact with web capabilities without needing to know the underlying implementation details of `web_search` or `web_read`.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| create_module | Function | Constructs and returns a fully configured `ToolModule` instance for web tools, providing the name, list of tools, and a descriptive summary. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The module defines a list named `TOOLS` containing references to the imported web functions (`web_search`, `web_read`). The `create_module` function then wraps these functions into a `ToolModule` object, passing the necessary metadata.
- **Side Effects:** None.
- **Error Handling:** None.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- TOOLS_WEB_ENABLED — Controls whether the web tools are active in the system configuration.

**Module Dependencies:**
- **Standard/External:** None
- **Internal:** [base_module](/ai/modules/base_module.md)