## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | ResponseParser |
| Source file | xml_response_parser.py |

The **ResponseParser** serves as a critical data extraction and sanitization layer designed to transform unstructured or semi-structured LLM outputs into structured, actionable Python dictionaries. It specifically targets XML-wrapped responses, which are used to encapsulate complex agentic intents such as internal reasoning (thoughts), metadata (manifests), and tool execution commands (actions).

By providing a robust parsing mechanism, the component ensures that the agent's decision-making process is decoupled from the raw string output of the language model. It acts as a defensive barrier, implementing "salvage operations" to recover data from malformed XML, thereby increasing the system's resilience against LLM hallucinations or formatting errors.

**Functional Mission**
The primary responsibility of **ResponseParser** is to parse and validate XML-formatted strings to extract structured components including `thought`, `notes`, `manifest`, `action` (tool name, parameters, and target), and `response_to_user`. Its core mission is to convert raw text into a reliable schema that downstream execution modules can consume without fear of parsing exceptions.

**System Context & Integration**
This component is a specialized implementation within the agentic workflow, likely utilized by [agent.md](/docs/ai/agents/agent.md) or [response_parser.md](/docs/ai/agents/response_parser.md) to interpret model outputs. It sits between the raw LLM output and the tool execution logic. Once a successful parse occurs, the resulting `action` dictionary is passed to the system to trigger specific functions, while the `thought` and `response_to_user` fields are routed to the user interface or logging systems.

- **INTERNAL REFERENCES**: [ai.functions](/docs/ai/functions.md)

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `parameter_mode` (Default: `"xml"`)  Determines whether tool parameters are extracted via XML child nodes or parsed as a JSON string.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ResponseParser` | Class | Orchestrates the parsing logic and maintains configuration state. |
| `__init__` | Method | Initializes the parser with a specific `parameter_mode`. |
| `_extract_params` | Method | Internal helper to traverse XML elements or decode JSON to extract tool arguments. |
| `_sanitize_block` | Method | Internal helper that uses regex to escape `<` and `>` characters within specific tags to prevent XML parsing failures. |
| `parse` | Method | The primary public entry point; accepts a raw string and returns a structured dictionary containing status and extracted data. |

## 4. Execution Logic & Flow
- **Initialization**: The class is instantiated with a `parameter_mode` (either `"xml"` or `"json"`), defining how the `tool_parameters` block will be processed.
- **Data Path**: 
    1. **Input**: A raw string containing potential XML tags.
    2. **Boundary Detection**: Locates `<response>` and `</response>` tags.
    3. **XML Parsing**: Attempts to load the block via `ET.fromstring`.
    4. **Salvage (If needed)**: If parsing fails, the `_sanitize_block` method is called on `thought`, `notes`, and `response_to_user` tags to escape rogue angle brackets.
    5. **Extraction**: Traverses the XML tree to populate the `manifest`, `action`, and text-based fields.
    6. **Output**: A dictionary with `status` ("SUCCESS" or "FAILED") and the extracted payload.
- **Conditional Branching**:
    - **XML Parse Failure**: Triggers the salvage logic to attempt character escaping.
    - **Parameter Mode**: If `parameter_mode == "json"`, the parser skips XML child traversal for parameters and attempts `json.loads` on the element text.
    - **Missing Boundaries**: If `<response>` tags are absent, returns a `FAILED` status immediately.

## 5. Resource Dependencies
- **Standard Libraries**: `xml.etree.ElementTree`, `json`, `re`, `typing`
- **Internal Modules**: 
    - [ai.functions](/docs/ai/functions.md)
- **External Packages**: None identified.