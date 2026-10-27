## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | ResponseParser |
| Source file | response_parser.py |

The **ResponseParser** serves as the critical translation layer between the raw, unstructured text output of Large Language Models (specifically optimized for 8B parameter models) and the structured command format required by the system's orchestration logic. It implements the JARVIS Plain Text Protocol, utilizing specific token delimiters (` (`____@`) to segment model thoughts, metadata, and actionable tool calls.

Its primary mission is to provide high-fidelity parsing that is resilient to common LLM failures, such as indentation drift in YAML blocks and the omission of quotes around special characters (e.g., `@ROOT`). By sanitizing these outputs, it ensures that the downstream execution engine receives valid, predictable data structures, preventing system crashes caused by malformed model responses.

**System Context & Integration**
This component acts as a gatekeeper in the agentic loop. Once an LLM generates a response, the `ResponseParser` intercepts the raw string and transforms it into a standardized dictionary. This dictionary is then consumed by the orchestrator to determine the next state of the agent, whether that involves updating the user via `response_to_user`, logging internal reasoning via `thought`, or executing a tool via the `action` object. It effectively bridges the gap between probabilistic text generation and deterministic code execution.

- **INTERNAL REFERENCES**: The parser utilizes logging capabilities provided by [ai.functions](/docs/ai/functions.md).

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `token_pattern` (Regex: `(\s*____@[A-Za-z_:]+)`)  Defines the delimiter pattern for the JARVIS Plain Text Protocol.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ResponseParser` | Class | Orchestrates the parsing of raw model strings into structured data. |
| `_parse_key_value_block` | Method | Parses simple colon-delimited strings for Manifest data. |
| `_sanitize_yaml` | Method | Corrects indentation and quoting errors in model-generated YAML. |
| `_parse_tool_block` | Method | Extracts tool names, intents, and parameters from a specific tool token block. |
| `parse` | Method | The primary public entry point for processing raw text into a structured dictionary. |

## 4. Execution Logic & Flow
- **Initialization**: The class initializes a compiled regular expression (`token_pattern`) to identify protocol tokens.
- **Data Path**: 
    1. **Segmentation**: The raw input string is split into segments using the `____@` regex.
    2. **Mapping**: Segments are paired into a dictionary where tokens are keys and subsequent text is the value.
    3. **Extraction**: Standard fields (`thought`, `notes`, `response`, `TARGET`) are pulled from the map.
    4. **Manifest Parsing**: The `____@manifest` block is processed via `_parse_key_value_block`.
    5. **Tool Processing**: If a `____@tool:` token is detected, `_parse_tool_block` is invoked.
    6. **YAML Sanitization**: Inside tool parsing, `_sanitize_yaml` applies regex fixes for `@` variables and forces indentation on multi-line blocks.
    7. **Output**: A unified dictionary containing `status`, `thought`, `notes`, `manifest`, `action`, and `response_to_user` is returned.
- **Conditional Branching**:
    - **Tool Detection**: If no `____@tool:` token exists, the `action` object is returned with empty parameters.
    - **YAML Error Handling**: If `yaml.safe_load` fails after sanitization, the error is caught, logged via `func.log`, and the error message is embedded into the `tool_parameters`.
    - **Global Exception Handling**: Any catastrophic parsing failure returns a dictionary with `status: "FAILED"`.

## 5. Resource Dependencies
- **Standard Libraries**: `re`, `yaml`, `typing`
- **Internal Modules**: 
    - [ai.functions](/docs/ai/functions.md)
- **External Packages**: `PyYAML` (imported as `yaml`)