## 1. Architectural Role
The `LLMConnector` acts as a structured communication bridge that manages the lifecycle of LLM requests, transforming raw model outputs into parsed XML-based agentic instructions.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `LLMConnector` | Class | Orchestrates the sending, execution, and parsing of LLM requests. |
| `send_request` | Method | Handles structured agentic communication using system prompts and XML constraints. |
| `send_raw_request` | Method | Bypasses XML parsing to return raw text/code generation. |
| `_execute_llm_call` | Method | Manages the physical LLM call via `ask` and handles temporary file I/O for output capture. |
| `_parse_xml_response` | Method | Extracts data from XML, featuring an auto-repair mechanism for truncated tags. |

## 3. Execution Logic & Flow
- **Initialization**: The class is instantiated with a `llm_instance` (inheriting from `BaseModel`), which is stored as `self.llm`.
- **Data Path (Structured)**: 
    1. `send_request` reads a system prompt from `system_prompt_path`.
    2. If `agent_config` is provided, it appends dynamic constraints (tools, targets, XML requirements) to the prompt.
    3. Constructs a message list containing the `SYSTEM` prompt and the `USER` input wrapped in `<context>` tags.
    4. Passes messages to `_execute_llm_call`.
    5. `_execute_llm_call` invokes `ask()`, writes the stream to `llm_output_active.tmp`, and reads the file back into a string.
    6. `_parse_xml_response` uses regex to isolate the `<response>` block, repairs missing closing tags if necessary, and converts XML elements into a Python dictionary.
- **Data Path (Raw)**:
    1. `send_raw_request` constructs a simple `SYSTEM` and `USER` message pair.
    2. Calls `_execute_llm_call` and returns the stripped string directly.
- **Conditional Branching**:
    - **Prompt Loading**: If the prompt file cannot be read, it returns a `FAILED` status immediately.
    - **XML Parsing**: If a complete `<response>` block is not found, the parser attempts to find the start tag and manually append missing closing tags based on a stack of open tags.
    - **Manifest Handling**: The `manifest` tag is processed as a dictionary; if it's a string, the code attempts to parse it as JSON.

## 4. Resource Dependencies
- **Standard Libraries**: `re`, `xml.etree.ElementTree`, `typing`, `uuid`, `os`, `json`
- **Internal Modules**: `functions` (as `func`), `core.llms.base_llm.BaseModel`, `core.chat.ChatRoles`, `direct.ask`

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `llm_output_active.tmp`: Temporary filename used for capturing LLM output.
    - `STOP`: Default value for `allowed_targets` if not specified in `agent_config`.
- **Environment Lookups**: None.