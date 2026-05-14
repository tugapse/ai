## 1. Architectural Role

**Functional Mission**
The **LLMConnector** serves as the primary communication gateway between the agentic framework and the underlying Large Language Model (LLM) instances. Its core mission is to abstract the complexities of LLM interaction by providing structured, XML-based communication protocols for agentic workflows while maintaining a fallback for raw text/code generation. It ensures that system prompts are dynamically augmented with tool descriptions and constraints before being dispatched to the model.

**System Context & Integration**
This component acts as a bridge between high-level agent logic and the low-level LLM implementations defined in [BaseModel](/docs/core/llms/base_llm.md). It consumes JSON-formatted context and transforms it into structured XML messages, which are then processed by the [ResponseParser](/docs/agents/xml_response_parser.md) to ensure output adheres to strict schema requirements. The component integrates deeply with the execution layer via [ask](/docs/direct.md) to manage the actual inference call and utilizes a file-based logging mechanism to capture and retrieve model outputs reliably.

## 2. Environment & Configuration
**Environment Lookups:**
- `output_filename` (via `_execute_llm_call`)  Determines the path for the active LLM output log using `func.get_root_directory()`.

**Hardcoded Constants:**
- `parameter_mode` (Default: `"xml"`)  Defines the default communication protocol mode.
- `STOP` (Default: `"STOP"`)  The default allowed agent target when no configuration is provided.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `LLMConnector` | Class | Orchestrates structured and raw communication with LLM instances. |
| `get_context_limit` | Method | Returns the maximum token window supported by the current LLM. |
| `get_max_tokens` | Method | Returns the maximum output token limit for the current LLM. |
| `send_request` | Method | Executes a structured agentic request using XML wrapping and dynamic constraint injection. |
| `send_raw_request` | Method | Executes a direct text/code generation request bypassing XML parsing. |
| `_execute_llm_call` | Method | Internal handler that invokes the [ask](/docs/direct.md) function and manages output file persistence. |

## 4. Execution Logic & Flow
- **Initialization**: The class is instantiated with an instance of [BaseModel](/docs/core/llms/base_llm.md) and initializes a [ResponseParser](/docs/agents/xml_response_parser.md) for output validation.
- **Data Path (Structured)**: 
    1. Receives `json_input` and `system_prompt_path`.
    2. Loads the system prompt from disk.
    3. If `agent_config` is present, injects `AVAILABLE TOOLS` and `ALLOWED AGENT TARGETS` into the system prompt.
    4. Wraps `json_input` in `<context>` XML tags.
    5. Dispatches messages via `_execute_llm_call`.
    6. Captures output from a temporary markdown file.
    7. Passes raw string to `self.parser.parse()` for structured extraction.
- **Data Path (Raw)**: 
    1. Receives `payload` containing `task_context` and `instruction`.
    2. Constructs a plain text message sequence.
    3. Dispatches via `_execute_llm_call` and returns the stripped string.
- **Conditional Branching**:
    - **Prompt Loading Error**: If the system prompt file cannot be read, returns a `FAILED` status dictionary.
    - **Parsing Error**: If the `ResponseParser` returns a `FAILED` status, logs an error via `func.error`.
    - **File IO Error**: If the LLM execution completes but the expected output file is missing, logs an error and returns an empty string.
    - **Execution Exception**: If `ask` fails, the component attempts to clean up the active output file before returning an empty string.

## 5. Resource Dependencies
- **Standard Libraries**: `re`, `xml.etree.ElementTree`, `typing`, `uuid`, `os`
- **Internal Modules**: 
    - [Color](/docs/color.md)
    - [ResponseParser](/docs/agents/xml_response_parser.md)
    - [functions](/docs/functions.md)
    - [BaseModel](/docs/core/llms/base_llm.md)
    - [ChatRoles](/docs/chat/chat.md)
    - [ask](/docs/direct.md)
- **External Packages**: None identified.