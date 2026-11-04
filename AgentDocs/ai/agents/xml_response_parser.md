## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **ResponseParser** | [src/ai/agents/xml_response_parser.py](/src/ai/agents/xml_response_parser.py) |

The `ResponseParser` class is responsible for transforming raw string outputs from AI agents into structured, machine-readable dictionaries. It specifically targets responses that are encapsulated within `<response>` XML tags and contain nested structured data such as thought processes, manifests, and tool execution parameters.

This component acts as a critical data extraction layer within the agent architecture. By providing a robust mechanism to parse both XML and JSON-formatted tool parameters, it ensures that the agent's intent (actions, targets, and parameters) can be reliably interpreted by the rest of the system. It includes a "salvage" mechanism to recover data from malformed XML, making it resilient to common LLM formatting errors.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ResponseParser(parameter_mode: str = "xml")` | Class | Initializes the parser. `parameter_mode` determines if `tool_parameters` are parsed as XML child tags or a JSON string. |
| `parse(raw_string: str) -> Dict[str, Any]` | Method | The primary entry point. Takes a raw string, extracts the `<response>` block, and returns a dictionary containing `status`, `thought`, `notes`, `manifest`, `action`, and `response_to_user`. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - The parser first attempts to locate `<response>` and `</response>` boundaries.
    - It utilizes `xml.etree.ElementTree` for initial parsing.
    - **Salvage Mechanism:** If standard XML parsing fails, the `_sanitize_block` method uses regular expressions to find specific tags (`thought`, `notes`, `response_to_user`) and escapes illegal `<` and `>` characters within their text content to allow the XML tree to be rebuilt successfully.
    - **Parameter Extraction:** Depending on `parameter_mode`, it either iterates through XML child elements to build a dictionary (handling duplicate tags by converting them into lists) or attempts to `json.loads` the text content of the element.
- **Side Effects:** 
    - Calls `func.log` via [ai.functions](/AgentDocs/ai/functions.md) when an initial parsing failure triggers the salvage operation.
- **Error Handling:** 
    - Returns a dictionary with `"status": "FAILED"` and an `error` key if boundaries are missing, if the salvage operation fails, or if a system exception occurs.
    - If `parameter_mode` is set to `"json"` and parsing fails, the `tool_parameters` field will contain an error dictionary instead of the expected parameters.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `xml.etree.ElementTree`, `json`, `re`, `typing`.
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)