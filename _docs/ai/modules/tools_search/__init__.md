## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| tools_search | ai/modules/tools_search/__init__.md |

This component aggregates and exposes a collection of search utility tools, specifically `smart_search` and `grep_file`. Its primary responsibility is to provide a centralized interface for users to perform complex content discovery across the entire project directory or within a specific file, managed via the `ToolModule` abstraction.

This module acts as a service provider within the application's architecture. It is responsible for instantiating and managing the available search tools, making them accessible to higher-level components that require content introspection capabilities, such as a command execution or agent logic service.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| create_module | Function | Constructs and returns a configured `ToolModule` instance for the search tools. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The module initializes a list named `TOOLS` containing references to the imported search functions. The `create_module` function wraps these tools into a `ToolModule` object, providing a standardized entry point for tool invocation.

- **Side Effects:** None.

- **Error Handling:** None.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** None.

- **Internal:** [base_module](/ai/modules/base_module.md), [tools](/ai/modules/tools_search/tools.md)