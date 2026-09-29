## 1. Architectural Role
| :--- | :--- |
| Name | ToolRegistry |
| Source file | tool_registry.py |

The **ToolRegistry** serves as the central nervous system for tool management and execution within the AI framework. It implements a Singleton pattern to ensure a unified, global registry where all available functional capabilities are stored, indexed, and accessible by the agentic layers.

**Functional Mission**
The primary responsibility of **ToolRegistry** is to bridge the gap between high-level LLM reasoning and low-level Python execution. It solves the problem of dynamic tool discovery and schema generation by translating Python function metadata (docstrings) into structured JSON schemas that LLMs can understand, while simultaneously providing a robust parser to intercept and execute tool calls embedded within model responses.

**System Context & Integration**
This component acts as a critical intermediary in the execution loop. When an LLM generates a response, the registry's parsing logic identifies tool triggers (supporting multiple formats like YAML and specific Gemma artifacts). Once a call is validated, the registry executes the function and returns the result, facilitating the transition from "thought" to "action." It integrates deeply with [ResponseParser](/docs/ai/agents/response_parser.md) for YAML-based calls and relies on [functions](/docs/ai/functions.md) for logging and debugging operations.

- **INTERNAL REFERENCES**: [ResponseParser](/