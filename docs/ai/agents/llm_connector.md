## 1. Architectural Role
Handles the communication and processing of requests to a language model (LLM) using structured XML format.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `LLMConnector` | Class | Manages interactions with an LLM, sending requests and parsing responses. |
| `send_request` | Method | Sends a structured request to the LLM and returns a parsed response. |
| `send_raw_request` | Method | Sends a raw request to the LLM and returns the raw response. |
| `_execute_llm_call` | Method | Executes the LLM call and captures the output. |
| `_parse_xml_response` | Method | Parses the XML response from the LLM. |

## 3. Execution Logic & Flow
- **Initialization**: The `LLMConnector` class is initialized with an `llm_instance` of type `BaseModel`.
- **Data Path**:
  1. `send_request` reads the system prompt from a file and constructs a message with the system and user roles.
  2. The constructed messages are passed to `_execute_llm_call`, which captures the output.
  3. The captured output is then passed to `_parse_xml_response`, which extracts and parses the XML content.
- **Conditional Branching**:
  - In `send_request`, there is a conditional check for `agent_config` to inject dynamic constraints.
  - In `_parse_xml_response`, there is a conditional check to handle incomplete or malformed XML by attempting auto-repair.

## 4. Resource Dependencies
- **Standard Libraries**: `re`, `xml.etree.ElementTree`, `typing`, `uuid`, `os`
- **Internal Modules**: `functions`, `core.llms.base_llm`, `core.chat`, `direct`
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: None
- **Environment Lookups**: None