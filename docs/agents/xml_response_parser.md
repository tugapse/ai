## 1. Architectural Role
Provides a robust mechanism for extracting structured data from LLM-generated XML strings, featuring a multi-stage salvage operation to repair malformed XML containing unescaped characters in specific text blocks.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ResponseParser` | Class | Orchestrates the parsing, sanitization, and extraction of structured response data. |
| `__init__` | Method | Initializes the parser with a specific `parameter_mode` (defaulting to "xml"). |
| `_extract_params` | Method | Converts `tool_parameters` XML elements into dictionaries via JSON decoding or tag-based mapping. |
| `_sanitize_block` | Method | Uses regex to locate specific tags and replaces `<` and `>` with XML entities to allow parsing of "dirty" content. |
| `parse` | Method | The primary entry point that executes the boundary detection, strict parsing, salvage logic, and final dictionary construction. |

## 3. Execution Logic & Flow
- **Initialization**: An instance of `ResponseParser` is created, setting `self.parameter_mode` to either `"xml"` or `"json"`.
- **Data Path**: 
    1. **Boundary Detection**: `parse` locates `<response>` and `</response>` tags within the `raw_string`.
    2. **Strict Parse Attempt**: `ET.fromstring` attempts to parse the extracted `xml_block`.
    3. **Salvage Operation (on failure)**: If parsing fails, `_sanitize_block` is called sequentially for `thought`, `notes`, and `response_to_user` tags to escape rogue brackets.
    4. **Second Parse Attempt**: `ET.fromstring` attempts to parse the sanitized `xml_block`.
    5. **Extraction**: The logic traverses the `root` to populate a dictionary containing `thought`, `notes`, `manifest`, `action` (sub-fields: `tool_name`, `tool_parameters`, `agent_target`), and `response_to_user`.
    6. **Output**: Returns a dictionary with `status` ("SUCCESS" or "FAILED") and the extracted payload or error message.
- **Conditional Branching**:
    - **Boundary Check**: If `<response>` or `</response>` are missing, returns `FAILED`.
    - **Parse Error Handling**: If the first `ET.fromstring` fails, it triggers the salvage logic; if the second fails, it returns `FAILED`.
    - **Parameter Mode**: `_extract_params` branches between `json.loads` (if `parameter_mode == "json"`) and child-tag iteration.

## 4. Resource Dependencies
- **Standard Libraries**: `xml.etree.ElementTree`, `json`, `re`, `typing`
- **Internal Modules**: `functions` (aliased as `func`)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `parameter_mode` default: `"xml"`
    - XML boundary tags: `<response>`, `</response>`
    - Salvage target tags: `"thought"`, `"notes"`, `"response_to_user"`
    - XML Entity replacements: `&lt;`, `&gt;`
- **Environment Lookups**: None.