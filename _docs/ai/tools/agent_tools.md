## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| agent_tools | /ai/tools/agent_tools.md |

This component serves as a backward-compatibility shim for legacy code within the application. Its primary responsibility is to maintain compatibility for older import patterns that relied on direct access to built-in tools, `AVAILABLE_TOOLS`, and the `PROJECT_ROOT` variable from this module. By wrapping existing tool implementations, it allows older codebases to function correctly even as those tools are migrated to more modern, modular locations within the application structure.

Architecturally, this module acts as a facade or compatibility layer situated near the core utility layer of the application. It centralizes access to a collection of essential, fundamental tools—such as filesystem operations, shell execution, and web searching—by aggregating imports from specific, newer modules like [ai.modules.tools_filesystem.tools](/ai/modules/tools_filesystem/tools.md) and [ai.modules.tools_search.tools](/ai/modules/tools_search/tools.md). It also provides a compatibility class, `_CompatModule`, to manage global state like `PROJECT_ROOT` for legacy consumers.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| AVAILABLE_TOOLS | Dictionary | A mapping of tool function names to their callable references, providing a centralized registry of all available built-in tools. |
| _CompatModule | Class | A custom module type designed to intercept and forward reads/writes of the `PROJECT_ROOT` attribute to the base tools module for backward compatibility. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The module aggregates various tool functions from specialized sub-modules (e.g., filesystem, search, shell) into a single dictionary, `AVAILABLE_TOOLS`. It also implements `_CompatModule` to override the module's `PROJECT_ROOT` property, ensuring that legacy code referencing this attribute correctly interacts with the core tools base module.

- **Side Effects:** Reads/writes to the filesystem are performed indirectly via the imported tools (e.g., `read_file`, `write_file`). Process execution occurs via imported tools like `execute_command`. It mutates the `sys.modules` dictionary by replacing the module's class type.

- **Error Handling:** No specific custom error handling is visible; it relies on the exception handling mechanisms implemented within the underlying imported tools.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `subprocess`, `sys`, `types`
- **Internal:** [ai.tools.base](/ai/tools/base.md), [ai.modules.tools_filesystem.tools](/ai/modules/tools_filesystem/tools.md), [ai.modules.tools_search.tools](/ai/modules/tools_search/tools.md), [ai.modules.tools_shell.tools](/ai/modules/tools_shell/tools.md), [ai.modules.tools_web.tools](/ai/modules/tools_web/tools.md), [ai.modules.tools_notify.tools](/ai/modules/tools_notify/tools.md)