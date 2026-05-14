## 1. Architectural Role
The `ResponseParser` acts as a specialized deserialization engine designed to interpret the JARVIS Plain Text Protocol, specifically engineered to handle the structural inconsistencies and formatting "drift" common in 8B-parameter LLMs. It transforms raw, tokenized string outputs (delimited by `____@`) into structured Python dictionaries, sanitizing YAML blocks and extracting tool execution metadata to facilitate downstream orchestration. This component serves as the high-fidelity successor or alternative to [agents/xml_response_parser.md](agents/xml_response_parser.md).

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `____@` (Regex/Token Pattern)  The primary delimiter used to segment the raw model response into logical blocks.
- `____@TARGET` (Default: `"STOP"`)  The fallback termination state if no target is explicitly provided in the token stream.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ResponseParser` | Class | Orchestrates the parsing lifecycle of raw model strings. |
| `__init__` | Method | Initializes the regex engine for `____@` token detection. |
| `_parse_key_value_block` | Method | Parses flat `KEY: VALUE` pairs, typically used for the `____@manifest` block. |
| `_sanitize_yaml` | Method | Corrects 8B-specific YAML errors, including unquoted variables and indentation drift. |
| `_parse_tool_block` | Method | Decodes tool execution instructions including name, intent, and sanitized arguments. |
| `parse` | Method | The primary public entry point that executes the full transformation pipeline. |

## 4. Execution Logic & Flow
- **Initialization**: The class compiles a regular expression pattern to identify protocol tokens.
- **Data Path**: 
    1. **Input**: A raw string containing the model's unparsed response.
    2. **Segmentation**: The string is split via `token_pattern` into a dictionary mapping tokens to their subsequent text content.
    3. **Extraction**: Standard fields (`thought`, `notes`, `response`, `TARGET`) are extracted from the map.
    4. **Manifest Processing**: The `____@manifest` block is parsed into a key-value dictionary.
    5. **Tool Parsing**: If a `____@tool:` token is detected, the parser extracts the tool name, looks for an `INTENT:` field, and passes the `ARGS:` block through a YAML sanitizer.
    6. **Output**: Returns a structured `Dict[str, Any]` containing `status`, `thought`, `notes`, `manifest`, `action`, and `response_to_user`.
- **Conditional Branching**:
    - **YAML Sanitization**: If a multi-line block (`|`) is detected, it forces 2-space indentation; otherwise, it strips leading whitespace for uniformity.
    - **Tool Detection**: Only attempts tool block parsing if a token matching the `____@tool:` pattern exists.
    - **Error Handling**: If any stage of the process fails, the entire `parse` method catches the exception and returns a `status: "FAILED"` dictionary.

## 5. Resource Dependencies
- **Standard Libraries**: `re`, `yaml`, `typing`
- **Internal Modules**: 
    - [functions](functions.md)
- **External Packages**: `PyYAML` (imported as `yaml`)