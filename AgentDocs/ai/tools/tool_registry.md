## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **ToolRegistry** | [src/ai/tools/tool_registry.py](/src/ai/tools/tool_registry.py) |

The `ToolRegistry` is a centralized management system designed to handle the registration, documentation, and execution of callable functions (tools) available to the AI agent. It implements the Singleton pattern to ensure a unified registry across the entire application lifecycle, preventing conflicting tool definitions and providing a single source of truth for tool availability.

Within the broader architecture, this component acts as the bridge between the LLM's intent and the system's executable capabilities. It is responsible for translating Python function metadata into LLM-readable JSON schemas and parsing complex, multi-format tool call triggers (such as YAML or specialized tags) from streaming text outputs back into executable Python calls.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ToolRegistry()` | Class | Singleton class that manages the lifecycle and execution of registered tools. |
| `register_tool(name, func_ref)` | Method | Registers a callable function with a unique string identifier. |
| `get_tool_info(name)` | Method | Returns a formatted string containing the tool's name and its docstring documentation. |
| `execute_tool(name, params)` | Method | Executes a registered tool with provided keyword arguments; returns a status dictionary. |
| `get_all_tools()` | Method | Returns the internal dictionary of all registered tool names and their callable references. |
| `parse_docstring_to_schema(func_name, func_ref)` | Static Method | Dynamically converts a Python function's docstring into a JSON Schema, including an enforced `intent` property. |
| `format_tools_for_prompt(all_tools)` | Static Method | Generates a standardized "System Access Manual" string containing all tool schemas for LLM system prompts. |
| `parse_manual_tags(text)` | Static Method | A robust regex-based parser that extracts tool names and arguments from various formats (YAML, J.A.R.V.I.S., Gemma) in LLM streams. |
| `get_tool_usage_rule()` | Static Method | Returns the critical instruction set/protocol that must be included in system prompts to guide LLM tool usage. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **Schema Generation:** Uses regex to parse the `Args:` section of Python docstrings, mapping types like `int`, `bool`, and `list` to JSON-compatible types (`integer`, `boolean`, `array`).
    - **Parsing Engine:** `parse_manual_tags` implements a stateful character-by-character parser to handle nested braces and string escaping within streaming text. It supports multiple formats: YAML-based (via `ResponseParser`), J.A.R.V.I.S. tags, and Gemma-specific artifacts.
    - **Singleton Pattern:** Uses `__new__` to ensure only one instance of `_tools` exists.
- **Side Effects:** 
    - Performs logging via `ai.functions` for tool registration, execution attempts, and parsing failures.
    - Interacts with `ai.agents.response_parser.ResponseParser` during YAML parsing.
- **Error Handling:** 
    - `execute_tool` wraps function calls in a `try-except` block, returning a dictionary with `{"status": "FAILED", "error": str(e)}` instead of raising exceptions to the caller.
    - `parse_manual_tags` returns `None` if a tool call is detected but the JSON/YAML structure is incomplete (common in streaming), allowing the buffer to accumulate more text.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `json`, `re`, `typing`, `yaml`.
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.agents.response_parser](/AgentDocs/ai/agents/response_parser.md)