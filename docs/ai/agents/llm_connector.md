## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | LLMConnector |
| Source file | llm_connector.py |

The **LLMConnector** serves as the primary communication bridge between the high-level agentic logic and the underlying Large Language Model (LLM) implementations. It acts as a sophisticated wrapper that manages the lifecycle of a request, transforming structured JSON inputs into formatted prompts and ensuring that the resulting raw text is parsed back into actionable data structures.

**Functional Mission**
The primary responsibility of **LLMConnector** is to facilitate "Structured Agentic XML communication." It solves the problem of non-deterministic LLM outputs by enforcing strict prompt injection (including dynamic tool constraints) and utilizing a specialized parser to validate and extract structured responses. Its core mission is to provide a reliable, stateful interface for agents to interact with various LLM backends while maintaining strict adherence to defined communication protocols.

**System Context & Integration**
This component sits between the agentic orchestration layer and the low-level model drivers. It consumes `BaseModel` instances from [BaseModel](/docs/ai/core/llms/base_llm.md) to execute calls and utilizes [ResponseParser](/docs/ai/agents/xml_response_parser.md) to sanitize outputs. It integrates with [ask](/docs/ai/direct.md) to perform the actual execution and uses [ChatRoles](/docs/ai/chat/chat.md) to structure the conversation history. Downstream, the parsed output is returned to the calling agent to drive decision-making or tool execution.

- **INTERNAL REFERENCES**: [BaseModel](/docs/ai/core/llms/base_llm.md), [ResponseParser](/docs/ai/agents/xml_response_parser.md), [ChatRoles](/docs/ai/chat/chat.md), [ask](/docs/ai/direct.md).

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `parameter_mode` (Default: `"xml"`)  Determines the expected communication format.
- `output_filename` (Default: `f"{func.get_root_directory()}/logs/llm_output_active.md"`)  The path used to capture the LLM's raw output for reliability.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `LLMConnector` | Class | Orchestrates structured and raw communication with LLM instances. |
| `get_context_limit` | Method | Returns the maximum token window supported by the current LLM. |
| `get_max_tokens` | Method | Returns the maximum output token limit of the current LLM. |
| `send_request` | Method | Executes a structured XML-based request with dynamic tool/target constraints. |
| `send_raw_request` | Method | Executes a direct text/code generation request bypassing XML parsing. |
| `_execute_llm_call` | Method | Internal handler that manages the file-based capture of LLM responses via `ask`. |

## 4. Execution Logic & Flow
- **Initialization**: The class is instantiated with a `BaseModel` instance and an optional `parameter_mode`. It initializes a `ResponseParser` to handle incoming LLM text.
- **Data Path (Structured Request)**:
    1. **Prompt Loading**: Reads a system prompt from a file path.
    2. **Constraint Injection**: If `agent_config` is provided, it appends `AVAILABLE TOOLS` and `ALLOWED AGENT TARGETS` to the system prompt.
    3. **Message Construction**: Wraps the system prompt and the JSON input (inside `<context>` tags) into a list of chat messages.
    4. **Execution**: Calls `_execute_llm_call`, which triggers `ask` and writes the result to a temporary markdown file.
    5. **Parsing**: The file content is read and passed to `self.parser.parse()`.
    6. **Error Handling/Output**: If parsing fails, it attempts to extract `response_to_user` for fallback; otherwise, it returns the parsed dictionary.
- **Conditional Branching**:
    - **Prompt Read Failure**: If the system prompt file cannot be read, the method returns a `FAILED` status immediately.
    - **Parsing Failure**: If `parsed.get("status") == "FAILED"`, the logic checks for `raw_Content` to provide a graceful fallback to the user via `func.out`.
    - **File IO Failure**: In `_execute_llm_call`, if the output file is not created after execution, an error is logged and an empty string is returned.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `typing`
- **Internal Modules**: 
    - [ai.functions](/docs/ai/functions.md)
    - [ai.agents.xml_response_parser](/docs/ai/agents/xml_response_parser.md)
    - [ai.core.llms.base_llm](/docs/ai/core/llms/base_llm.md)
    - [ai.chat.chat](/docs/ai/chat/chat.md)
    - [ai.direct](/docs/ai/direct.md)
- **External Packages**: None identified.