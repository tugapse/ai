## 1. Architectural Role
| Name | Source file |
| :--- | :--- |
| ResponseParser | [/src/ai/agents/xml_response_parser.py](/src/ai/agents/xml_response_parser.py) |

The **ResponseParser** is a focused XML/JSON response decoding utility that translates the raw textual output from an LLM into a structured, machine-usable dictionary. It supports two parameter modes (xml by default and json) for extracting tool_parameters and builds a consistent payload containing thought, notes, manifest, action (tool_name, tool_parameters, agent_target), and response_to_user. A salvaging pathway is provided: if strict XML parsing fails, the component sanitizes specific blocks (thought, notes, response_to_user) to escape rogue characters and retries parsing, enabling graceful recovery from malformed generations.

Strategically, this component sits at the boundary between the LLMs generated content and the agents orchestration layer. It enforces a consistent data contract for downstream modules to consume (e.g., the action with tool parameters, manifest details, and user-facing responses), while offering resilience against poorly formed outputs. It also encapsulates the logic for parameter extraction, supporting JSON or tag-based kv pairs, thus decoupling the parsing concerns from higher-level orchestration.

- Internal reference: This module relies on the internal logging function to report salvage attempts, interfacing with [AI Functions](/docs/ai/functions.md) for cross-cutting tooling utilities.


## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ResponseParser` | Class | Parses a raw response string to a structured dictionary, supporting XML and JSON parameter modes, with a salvage path for malformed XML and extraction of fields: thought, notes, manifest, action (tool_name, tool_parameters, agent_target), and response_to_user. |

## 4. Code Example
- Usage example:
```python
from ai.agents.xml_response_parser import ResponseParser

parser = ResponseParser(parameter_mode="xml")
raw_string = "<response>...</response>"  # LLM output
result = parser.parse(raw_string)
print(result)
```

## 5. Execution Logic & Flow
- Initialization
  - Instantiate ResponseParser with an optional parameter_mode (default "xml").
- Data Path
  - locate the <response> boundaries in the input.
  - Attempt strict XML parsing of the extracted block.
  - If parsing fails, trigger salvage:
    - sanitize_block called on blocks: thought, notes, response_to_user
    - second attempt: parse the repaired xml_block
  - On success, extract:
    - manifest data (each child tag under <manifest>)
    - action (tool_name, tool_parameters, agent_target)
    - thought, notes, response_to_user
- Conditional Branching
  - If boundaries are missing: return {"status": "FAILED", "error": "Missing response boundaries"}.
  - If salvage parsing fails: return {"status": "FAILED", "error": "Malformed XML (Salvage Failed): ..." }.
  - On success: return {"status": "SUCCESS", ...structured fields...}.

## 6. Resource Dependencies
- **Standard Libraries**:
  - `xml.etree.ElementTree` (ET)  XML parsing
  - `json`  JSON parsing for tool_parameters when in json mode
  - `re`  regular expression-based sanitization in _sanitize_block
  - `typing`  type hints (`Dict`, `Any`, `Optional`)
- **Internal Modules**:
  - [ai.functions](/docs/ai/functions.md)  logging and auxiliary helpers used via `func.log`
- **External Packages**:
  - None

