## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| LLMConnector | ai/agents/llm_connector |

This component serves as the primary interface for abstracting and managing all communication channels with various Language Model (LLM) backends. Its core responsibility is to encapsulate the complexity of sending structured requests (like XML generation) or raw prompts, handling necessary pre-processing (such as injecting system prompts, tool descriptions, and agent output rules), and reliably parsing the resulting LLM output.

Architecturally, `LLMConnector` acts as a critical Service Layer component within the AI Agent framework. It sits between the high-level agent logic and the specific LLM implementations (`BaseModel`). It leverages `DirectoryManager` for path resolution, uses `ResponseParser` to interpret structured results, and relies on `ai.functions` and `ai.core.llms.api_retry` for execution and error management.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| LLMConnector | Class | Manages the connection and communication interface with a Language Model (LLM). |
| get_context_limit | Method | Retrieves the maximum context window size supported by the LLM. |
| get_max_tokens | Method | Retrieves the maximum number of tokens the LLM can generate in a single response. |
| send_request | Method | Sends a structured request to the LLM, typically expecting an XML response, after loading and augmenting the system prompt. |
| send_raw_request | Method | Bypasses structured parsing for raw code/text generation, sending a direct instruction and context to the LLM. |
| _execute_llm_call | Method | Executes the LLM call using the underlying `ask` function, capturing the output to a temporary file for reliable retrieval. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `send_request` method first loads the base system prompt, then dynamically injects tool descriptions (via `load_tools_descriptions`) and agent output rules (via `load_system_prompt_agent_output_rules`). It then executes the LLM call, retrying transient stream interruptions up to `PARTIAL_STREAM_RETRIES`. Upon success, the raw response is passed to `ResponseParser` for structured extraction. `send_raw_request` bypasses this parsing, executing a direct call to retrieve raw text.

- **Side Effects:** Reads/writes to the filesystem (reading system prompts, reading agent output rules, writing/reading temporary LLM output files). Interacts with the network via the underlying `ask` function to communicate with the LLM API.

- **Error Handling:** Catches `LLMAPIError` during execution, implementing a retry mechanism for transient/partial stream failures. In `send_request`, it checks the parsed status; if the parser fails, it logs the error but attempts to output the raw content if available.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `typing`, `Callable`, `Dict`, `Any`, `List`, `Optional`.
- **Internal:** [ai.functions](/ai/functions.md), [ai.agents.xml_response_parser](/ai/agents/xml_response_parser.md), [ai.core.llms.base_llm](/ai/core/llms/base_llm.md), [ai.chat.chat](/ai/chat/chat.md), [ai.direct.ask](/ai/direct.md), [ai.services.directory_manager](/ai/services/directory_manager.md), [ai.core.llms.api_retry](/ai/core/llms/api_retry.md).