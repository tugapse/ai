## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **LLMConnector** | [src/ai/agents/llm_connector.py](/src/ai/agents/llm_connector.py) |

The `LLMConnector` class serves as the primary communication interface between the agentic framework and the underlying Large Language Model (LLM). It is responsible for managing the lifecycle of a request, including loading system prompts from the filesystem, injecting dynamic constraints such as tool descriptions and agent targets, and ensuring that the model's output adheres to expected formats.

Within the broader architecture, this component acts as a bridge between high-level agent logic and the low-level LLM implementations defined in [BaseModel](/AgentDocs/ai/core/llms/base_llm.md). It facilitates both structured XML-based communication for complex agentic reasoning and raw text generation for simpler tasks, ensuring that responses are consistently parsed and handled via [ResponseParser](/AgentDocs/ai/agents/xml_response_parser.md).

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `LLMConnector(llm_instance: BaseModel, parameter_mode: str = "xml")` | Class | Initializes the connector with a specific LLM instance and sets the communication mode. |
| `get_context_limit() -> int` | Method | Returns the maximum context window size supported by the configured LLM. |
| `get_max_tokens() -> int` | Method | Returns the maximum number of tokens the LLM can generate in a single response. |
| `send_request(json_input: Dict[str, Any], system_prompt_path: str, agent_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]` | Method | Sends a structured request to the LLM. It loads a system prompt, injects tools/targets if provided, and returns a parsed dictionary containing the LLM's response. |
| `send_raw_request(payload: Dict[str, Any], system_prompt: str = "") -> str` | Method | Bypasses XML parsing to provide a direct instruction/context interface, returning a raw string response. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The component uses a template-based injection system. It searches for placeholders like `{{TOOLS}}` and `{{AGENT_OUTPUT_RULES}}` within system prompts to inject dynamic runtime constraints. For structured requests, it wraps the user input in `<context>` XML tags and utilizes a `ResponseParser` to validate the LLM's output.
- **Side Effects:** 
    - **Filesystem:** Reads system prompt files from disk and reads agent output rules from the directory managed by [DirectoryManager](/AgentDocs/ai/services/directory_manager.md).
    - **Filesystem:** Writes LLM outputs to a temporary file (`llm_output_active.md`) within the system logs directory to ensure reliable data retrieval during streaming or execution.
    - **Logging:** Uses `func.debug`, `func.error`, and `func.out` for operational telemetry.
- **Error Handling:** If a prompt file cannot be read, the `send_request` method catches the exception and returns a dictionary with a `FAILED` status. If XML parsing fails, the component attempts to fallback to the raw content and logs an error.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No direct environment variables are accessed within this module; it relies on the filesystem structure managed by [DirectoryManager](/AgentDocs/ai/services/directory_manager.md).

**Module Dependencies:**
- **Standard/External:** `os`, `typing`.
- **Internal:**
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.agents.xml_response_parser](/AgentDocs/ai/agents/xml_response_parser.md)
    - [ai.core.llms.base_llm](/AgentDocs/ai/core/llms/base_llm.md)
    - [ai.chat.chat](/AgentDocs/ai/chat/chat.md)
    - [ai.direct](/AgentDocs/ai/direct.md)
    - [ai.services.directory_manager](/AgentDocs/ai/services/directory_manager.md)