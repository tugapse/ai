## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **ToolRegistry** | [src/ai/tools/tool_registry.py](/src/ai/tools/tool_registry.py) |

The `ToolRegistry` is a centralized management system designed to handle the registration, documentation, and execution of callable functions (tools) available to the AI agent. It implements the Singleton pattern to ensure a unified registry across the entire application lifecycle, preventing conflicting tool definitions and providing a single source of truth for tool availability.

This component acts as a critical bridge between the LLM's reasoning and the system's execution capabilities. It is responsible for translating Python function metadata into LLM-compatible JSON schemas and parsing raw text streams to detect and extract tool invocation triggers. It fits into the broader architecture as a core utility within the `ai.tools` subsystem, facilitating the "action" phase of the agentic loop.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ToolRegistry()` | Class | A Singleton class that manages the lifecycle of tool registration and execution. |
| `register_tool(name, func_ref)` | Method | Registers a callable function under a unique string identifier. |
| `get_tool_info(name)` | Method | Returns a formatted string containing the tool's name and its docstring documentation. |
| `execute_tool(name, params)` | Method | Executes a registered tool with the provided dictionary of keyword arguments; returns a status dictionary. |
| `get_all_tools()` | Method | Returns the internal dictionary mapping tool names to their callable references. |
| `parse_docstring_to_schema(func_name, func_ref)` | Static Method | Dynamically converts a Python function's docstring into a JSON Schema, including an enforced `intent` property. |
| `format_tools_for_prompt(all_tools)` | Static Method | Generates a standardized "System Access Manual" string containing all tool schemas for LLM system prompts. |
| `parse_manual_tags(text)` | Static Method | A robust regex-based parser that detects tool calls in streaming text, supporting YAML, J.A.R.V.I.S., and Gemma artifact formats. |
| `get_tool_usage_rule()` | Static Method | Returns the mandatory system prompt instructions regarding the `e `____@tool` protocol. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **Schema Generation:** The `parse_docstring_to_schema` method uses regular expressions to parse the `Args:` section of Python docstrings, mapping Python types (int, bool, list) to JSON types (integer, boolean, array).
    - **Parsing Engine:** `parse_manual_tags` employs a stateful character-by-character loop to handle nested braces and complex string escaping (including special handling for Gemma's `<|...|>` artifacts). It supports multiple formats, including a fallback to `ResponseParser` for YAML-based tool endings.
    - **Singleton Pattern:** Uses `__new__` to ensure that only one instance of the registry is ever instantiated.
- **Side Effects:** 
    - **Logging:** Interacts with the `ai.functions` module to log tool registration, execution attempts, and parsing failures.
    - **Dynamic Imports:** Performs local imports of `ai.agents.response_parser` and `yaml` within method scopes to optimize startup time and handle conditional dependencies.
- **Error Handling:** 
    - Tool execution is wrapped in a broad `try-except` block; failures return a dictionary with `{"status": "FAILED", "error": str(e)}` rather than raising exceptions to the caller.
    - If `parse_manual_tags` encounters an incomplete JSON/YAML block (common in streaming), it returns `None` to signal that the buffer should be maintained.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `json`, `re`, `typing`, `yaml` (Third-party).
- **Internal:** 
    - [ai.functions](/src/ai/functions.md)
    - [ai.agents.response_parser](/src/ai/agents/response_parser.md)