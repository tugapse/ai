## 1. Architectural Role
`LLMConnector` serves as the primary communication bridge between high-level agentic logic and the underlying LLM abstraction layer. It manages the lifecycle of structured XML-based interactions, handles dynamic system prompt injection (including tool and target constraints), and orchestrates the execution of LLM calls via the [direct](direct.md) module. It is responsible for ensuring that raw model outputs are transformed into validated, structured data using the [xml_response_parser](agents/xml_response_parser.md) to maintain strict agentic state consistency.

## 2. Environment & Configuration
**Environment Lookups:**
- `system_prompt_path` (via `send_request`)  File system path used to load the foundational system instructions.
- `output_filename` (via `_execute_llm_call`)  Resolves via `func.get_root_directory()` to define the temporary log path for capturing streamed LLM output.

**Hardcoded Constants:**
- `parameter_mode` (Default: `"xml"`)  Determines the intended communication protocol.
- `output_filename` (Default: `"{root}/logs/llm_output_active.md"`)  Fixed path for capturing active LLM inference streams.
- `allowed_targets` (Default: `["STOP"]`)  Fallback agent termination signal.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `LLMConnector` | Class | Orchestrates structured and raw LLM communication and response parsing. |
| `get_context_limit` | Method | Returns the maximum token capacity of the underlying LLM instance. |
| `get_max_tokens` | Method | Returns the maximum output token capacity of the underlying LLM instance. |
| `send_request` | Method | Performs structured XML-based interaction, injecting dynamic agent constraints and parsing the response. |
| `send_raw_request` | Method | Executes a direct, unparsed text-to-text request for code or general text generation. |
| `_execute_llm_call` | Method | Internal handler that triggers the [direct](direct.md) `ask` function and manages the output file lifecycle. |

## 4. Execution Logic & Flow
- **Initialization**: Instantiates the `LLMConnector` with a specific [base_llm](core/llms/base_llm.md) instance and initializes the [xml_response_parser](agents/xml_response_parser.md).
- **Data Path (Structured Request)**: 
    1. Load `system_content` from file.
    2. If `agent_config` exists, append `AVAILABLE TOOLS` and `ALLOWED AGENT TARGETS` to the prompt.
    3. Construct `messages` array containing `ChatRoles.SYSTEM` and `ChatRoles.USER` (wrapped in XML tags).
    4. Pass messages to `_execute_llm_call`.
    5. Read the resulting `.md` file produced by the `ask` function.
    6. Pass raw string to `parser.parse()`.
    7. Return structured dictionary.
- **Data Path (Raw Request)**:
    1. Construct `messages` using `task_context` and `instruction`.
    2. Execute via `_execute_llm_call`.
    3. Return stripped string content.
- **Conditional Branching**:
    - **File Read Error**: If prompt loading fails, returns a `FAILED` status dictionary.
    - **Parsing Error**: If the `parser` returns a failure status, logs the error via [functions](functions.md).
    - **File IO Error**: If `ask` completes but the log file is missing, returns an empty string and logs an error.
    - **Exception Handling**: On execution failure, attempts to clean up the active log file before returning an empty string.

## 5. Resource Dependencies
- **Standard Libraries**: `re`, `xml.etree.ElementTree`, `typing`, `uuid`, `os`
- **Internal Modules**: 
    - [color](color.md)
    - [xml_response_parser](agents/xml_response_parser.md)
    - [functions](functions.md)
    - [core/llms/base_llm](core/llms/base_llm.md)
    - [chat/chat](chat/chat.md)
    - [direct](direct.md)
- **External Packages**: None identified.