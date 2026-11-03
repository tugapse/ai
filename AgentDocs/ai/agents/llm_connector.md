## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **LLMConnector** | [src/ai/agents/llm_connector.py](/AgentDocs/ai/agents/llm_connector.md) |

The `LLMConnector` class serves as the primary communication gateway between the agentic framework and the underlying Large Language Model (LLM). It abstracts the complexities of prompt management, constraint injection, and response parsing, providing a unified interface for both structured (XML-based) and raw text interactions.

This component sits within the agent layer of the architecture, acting as a bridge between high-level agent logic and the low-level LLM implementations defined in [BaseModel](/AgentDocs/ai/core/llms/base_llm.md). It ensures that agents operate within defined boundaries by dynamically injecting tool descriptions and target constraints into system prompts before execution.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `LLMConnector(llm_instance, parameter_mode="xml")` | Class | Initializes the connector with a specific [BaseModel](/AgentDocs/ai/core/llms/base_llm.md) instance and sets the communication mode. |
| `get_context_limit()` | Method | Returns the maximum context window size supported by the configured LLM. |
| `get_max_tokens()` | Method | Returns the maximum number of tokens the LLM can generate in a single response. |
| `send_request(json_input, system_prompt_path, agent_config=None)` | Method | Sends a structured request. Loads a system prompt from a file, injects dynamic constraints from `agent_config`, and returns a parsed dictionary via [ResponseParser](/AgentDocs/ai/agents/xml_response_parser.md). |
| `send_raw_request(payload, system_prompt="")` | Method | Executes a direct LLM call for raw text/code generation, bypassing the XML parsing logic. Returns a raw string. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - For structured requests, the class performs "Dynamic Constraint Injection." It reads a base system prompt from the filesystem and appends tool definitions and allowed targets if an `agent_config` is provided. 
    - It constructs a message list using [ChatRoles](/AgentDocs/ai/chat/chat.md) and delegates the actual execution to the `ask` function.
    - Responses are passed through [ResponseParser](/AgentDocs/ai/agents/xml_response_parser.md) to extract structured data.
- **Side Effects:** 
    - **Filesystem I/O:** Reads system prompt files from the provided path.
    - **Filesystem I/O:** Writes LLM output to a temporary markdown file (`llm_output_active.md`) within the directory managed by [DirectoryManager](/AgentDocs/ai/services/directory_manager.md).
    - **Filesystem I/O:** Deletes the temporary output file if an execution error occurs.
- **Error Handling:** 
    - Catches file reading errors during prompt loading, returning a `FAILED` status dictionary.
    - Catches LLM execution errors via `ask`, logging the error through [func.error](/AgentDocs/ai/functions.md) and cleaning up temporary files.
    - If XML parsing fails but raw content is available, it outputs the raw content to the console via [func.out](/AgentDocs/ai/functions.md).

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No specific environment variables are required by this component directly, though it relies on the underlying LLM configuration.

**Module Dependencies:**
- **Standard/External:** `os`, `typing`
- **Internal:**
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.agents.xml_response_parser](/AgentDocs/ai/agents/xml_response_parser.md)
    - [ai.core.llms.base_llm](/AgentDocs/ai/core/llms/base_llm.md)
    - [ai.chat.chat](/AgentDocs/ai/chat/chat.md)
    - [ai.direct](/AgentDocs/ai/direct.md)
    - [ai.services.directory_manager](/AgentDocs/ai/services/directory_manager.md)