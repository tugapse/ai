## 1. Architectural Role
Acts as a high-level communication bridge that orchestrates structured (XML) or unstructured (raw) interactions between the agentic system and a specific LLM instance.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `LLMConnector` | Class | Manages LLM lifecycle, prompt injection, and response parsing. |
| `get_context_limit` | Method | Returns the maximum token window from the LLM instance. |
| `get_max_tokens` | Method | Returns the maximum output token capacity from the LLM instance. |
| `send_request` | Method | Executes a structured agentic workflow using XML parsing and dynamic constraint injection. |
| `send_raw_request` | Method | Executes a direct text/code generation request bypassing structured parsing. |
| `_execute_llm_call` | Method | Performs the low-level execution via `ask` and manages the physical output file lifecycle. |

## 3. Execution Logic & Flow
- **Initialization**: 
    - Receives a `BaseModel` instance.
    - Sets `parameter_mode` (defaults to "xml").
    - Instantiates `ResponseParser` as `self.parser`.
- **Data Path (Structured: `send_request`)**:
    - **Input**: `json_input` (Dict), `system_prompt_path` (str), `agent_config` (Dict).
    - **Processing**: 
        1. Reads system prompt from disk.
        2. Injects dynamic constraints (Tools, Descriptions, Targets) into the prompt string if `agent_config` is provided.
        3. Constructs a message list containing a `SYSTEM` role and a `USER` role wrapping the input in `<context>` tags.
        4. Passes messages to `_execute_llm_call`.
        5. Captures file-based output and passes it to `self.parser.parse`.
    - **Output**: A dictionary containing parsed XML data or error status.
- **Data Path (Unstructured: `send_raw_request`)**:
    - **Input**: `payload` (Dict), `system_prompt` (str).
    - **Processing**: Constructs messages using `task_context` and `instruction` keys, then calls `_execute_llm_call`.
    - **Output**: A stripped string of the raw LLM response.
- **Data Path (Execution: `_execute_llm_call`)**:
    - **Input**: `messages` (List).
    - **Processing**: 
        1. Defines `output_filename` pointing to `logs/llm_output_active.md`.
        2. Invokes `ask` with streaming and file-writing enabled.
        3. Reads the resulting file from disk.
    - **Output**: The content of the output file as a string.
- **Conditional Branching**:
    - `if agent_config`: Appends dynamic tool and target constraints to the system prompt.
    - `if parsed.get("status") == "FAILED"`: Triggers error logging for XML parsing failures.
    - `if os.path.exists(output_filename)`: Validates file creation before attempting a read.
    - `except Exception`: Handles execution failures and performs cleanup by removing the active log file.

## 4. Resource Dependencies
- **Standard Libraries**: `re`, `xml.etree.ElementTree`, `typing`, `uuid`, `os`
- **Internal Modules**: `color`, `xml_response_parser`, `functions` (as `func`), `core.llms.base_llm`, `chat.chat`, `direct` (specifically `ask`)
- **External Packages**: None explicitly imported (relies on internal/provided modules)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `output_filename` path: `{func.get_root_directory()}/logs/llm_output_active.md`
    - Constraint Delimiter: `"\n\n--- DYNAMIC CONSTRAINTS ---"`
- **Environment Lookups**: 
    - `func.get_root_directory()` is used to resolve the absolute path for log files.