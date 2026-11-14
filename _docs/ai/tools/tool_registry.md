## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| ToolRegistry | ai/tools/tool_registry.md |

This component provides a centralized, singleton mechanism for managing and accessing all callable functions (tools) available to the AI agent. Its primary responsibility is to register these functions, allow for their retrieval based on a unique name, and execute them when triggered by the agent's logic. Furthermore, it offers sophisticated utilities to translate Python docstrings into LLM-consumable JSON Schemas.

Architecturally, `ToolRegistry` functions as a core service layer within the application. It acts as the bridge between the agent's decision-making process and the actual backend logic implemented in other modules. It relies on imports from `ai.functions` for logging and debugging, and its schema generation capabilities are critical for interfacing with external language models.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `register_tool` | Method | Registers a callable function with a unique name in the registry. |
| `get_tool_info` | Method | Retrieves a formatted string containing the name and documentation of a registered tool. |
| `execute_tool` | Method | Executes a registered tool function with the provided parameters. |
| `get_all_tools` | Method | Returns the full dictionary of registered tool functions. |
| `parse_docstring_to_schema` | Static Method | Dynamically translates Python docstrings into an LLM-friendly JSON Schema. |
| `format_tools_for_prompt` | Static Method | Constructs the system access manual using a generic protocol format from all registered tools. |
| `parse_manual_tags` | Static Method | Standardized regex parser for catching tool triggers in the streaming text output. |
| `get_tool_usage_rule` | Static Method | Returns the standardized usage rule string for the LLM prompt. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The registry enforces a Singleton pattern via `__new__`. Tool registration stores functions in an internal dictionary. The `parse_docstring_to_schema` method uses regex to parse structured docstrings (looking for `Args:` sections) to build a JSON schema, enforcing an `intent` property. The `parse_manual_tags` method employs complex regex and state tracking to reliably extract function calls from various proprietary streaming formats.
- **Side Effects:** Mutates the internal state (`_tools` dictionary) upon registration. It calls `func.debug` and `func.log` which implies interaction with a logging mechanism, which could involve I/O or network depending on the configuration of `ai.functions`.
- **Error Handling:** `execute_tool` uses a `try...except` block to catch any runtime exceptions during function execution, returning a standardized failure dictionary. `parse_manual_tags` handles parsing failures by returning `None` to allow for stream buffering.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `inspect`, `json`, `re`, `typing`
- **Internal:** [ai.functions](/ai/functions.md)