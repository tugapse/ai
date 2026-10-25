## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | ToolRegistry |
| Source file | tool_registry.py |

The **ToolRegistry** serves as the centralized authority for managing the lifecycle, discovery, and execution of all functional capabilities available to the AI agents. It acts as a bridge between raw Python functions and the LLM's reasoning engine, ensuring that tools are not only registered but also presented to the model in a structured, schema-compliant format.

**Functional Mission**
The primary responsibility of the **ToolRegistry** is to provide a unified interface for registering tool functions, generating LLM-compatible JSON schemas from Python docstrings, and parsing complex, multi-format tool-call triggers from model responses. It solves the problem of "capability discovery" by translating code-level metadata into actionable system protocols.

**System Context & Integration**
This component sits at the intersection of the agent's reasoning loop and the system's execution environment. It is utilized by [Agent](/docs/ai/agents/agent.md) logic to understand available tools via `format_tools_for_prompt` and is critical during the response parsing phase. When an LLM outputs a tool trigger, the registry's parsing logic identifies the intent and arguments, which are then passed to `execute_tool` to perform the actual side effect. It integrates closely with [ResponseParser](/docs/ai/agents/response_parser.md) for YAML-based triggers and provides the necessary schema definitions to maintain strict adherence to the `[PROTOCOL: SYSTEM ACCESS]`.

- **INTERNAL REFERENCES**: [ResponseParser](/docs/ai/agents/response_parser.md), [Agent](/docs/ai/agents/agent.md).

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `get_tool_usage_rule` (Default: Multi-line string)  Defines the mandatory YAML-based syntax and critical constraints for the LLM to follow when invoking tools.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ToolRegistry` | Class | Singleton manager for tool registration, schema generation, and execution. |
| `register_tool` | Method | Adds a callable to the internal `_tools` dictionary. |
| `get_tool_info` | Method | Retrieves a human-readable description of a tool from its docstring. |
| `execute_tool` | Method | Invokes a registered tool with provided parameters and handles execution errors. |
| `get_all_tools` | Method | Returns the raw dictionary of all registered tool functions. |
| `parse_docstring_to_schema` | Static Method | Converts Python docstrings (Args/Returns) into a JSON Schema including a mandatory `intent` field. |
| `format_tools_for_prompt` | Static Method | Aggregates all tools into a single string formatted as a "System Access Manual" for LLM context. |
| `parse_manual_tags` | Static Method | A complex regex-based parser that detects and extracts tool calls from text streams, supporting YAML, J.A.R.V.I.S., and Gemma-specific artifacts. |
| `get_tool_usage_rule` | Static Method | Returns the system prompt instructions for tool usage. |

## 4. Execution Logic & Flow
- **Initialization**: Implements the Singleton pattern via `__new__` to ensure a single, global registry exists across the application. Initializes an empty `_tools` dictionary.
- **Data Path (Schema Generation)**: 
    1. Input: Function reference.
    2. Processing: Parses docstring lines $\rightarrow$ Identifies `Args:` section $\rightarrow$ Regex matches `param (type): desc` $\rightarrow$ Maps Python types to JSON types $\rightarrow$ Injects mandatory `intent` property.
    3. Output: JSON Schema dictionary.
- **Data Path (Tool Parsing)**:
    1. Input: Raw text stream from LLM.
    2. Processing: 
        - Check for `r `____@tool_end` $\rightarrow$ Delegate to `ResponseParser`.
        - If not found, apply regex for `____@` or `<|tool_call|>`.
        - If match found, perform brace-counting to extract the JSON/YAML block.
        - Clean artifacts (Gemma-specific quotes) and fix unquoted keys.
        - Attempt `yaml.safe_load`.
    3. Output: Dictionary containing `type`, `name`, and `args` (with `intent` stripped).
- **Conditional Branching**:
    - `execute_tool`: If tool name is missing $\rightarrow$ Return `FAILED` status. If execution raises `Exception` $\rightarrow$ Catch and return error dictionary.
    - `parse_manual_tags`: If brace count does not reach zero $\rightarrow$ Return `None` (signals incomplete stream).

## 5. Resource Dependencies
- **Standard Libraries**: `json`, `re`, `typing`
- **Internal Modules**: 
    - [Functions](/docs/ai/functions.md)
    - [ResponseParser](/docs/ai/agents/response_parser.md)
- **External Packages**: `yaml` (PyYAML)