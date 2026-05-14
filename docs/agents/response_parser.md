## 1. Architectural Role

**Functional Mission**
The **ResponseParser** class is a specialized parsing engine designed to decode the JARVIS Plain Text Protocol, which utilizes `____@` tokens to demarcate different data segments. Its primary mission is to provide a robust extraction layer that can handle the specific formatting inconsistencies and "drift" often produced by smaller-scale (8B) language models, ensuring that structured data like thoughts, tool calls, and manifests are correctly recovered from raw text.

**System Context & Integration**
This component acts as a critical translation layer between the raw LLM output and the system's execution logic. It sits within the agentic workflow, transforming unstructured string responses into a structured dictionary that downstream modulessuch as the orchestratorcan use to trigger tool executions or update internal states. By sanitizing YAML and normalizing indentation, it prevents malformed model outputs from causing cascading failures in the tool execution pipeline.

## 2. Environment & Configuration

**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `token_pattern` (Default: `re.compile(r"(____@[A-Za-z_:]+)")`)  Regex pattern used to identify protocol delimiters.
- `____@thought`  Token key for extracting internal reasoning.
- `____@notes`  Token key for extracting metadata/notes.
- `____@response`  Token key for extracting the user-facing message.
- `____@TARGET` (Default: `"STOP"`)  Token key for determining the next agent target.
- `____@manifest`  Token key for extracting phase/priority metadata.
- `____@tool:`  Prefix used to identify tool execution blocks.

## 3. Interface & API Surface

| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ResponseParser` | Class | Orchestrates the parsing of the JARVIS Plain Text Protocol. |
| `_parse_key_value_block` | Func | Parses simple `KEY: VALUE` strings for manifest data. |
| `_sanitize_yaml` | Func | Corrects 8B model errors including unquoted variables and indentation drift. |
| `_parse_tool_block` | Func | Extracts tool names, intents, and YAML-formatted arguments from a tool segment. |
| `parse` | Func | The primary public entry point that transforms a raw string into a structured dictionary. |

## 4. Execution Logic & Flow

- **Initialization**: The class initializes by compiling a regex pattern (`token_pattern`) to identify protocol tokens.
- **Data Path**: 
    1. **Segmentation**: The input `raw_string` is split into segments using the `token_pattern`.
    2. **Mapping**: Segments are mapped into a `data_map` dictionary where tokens serve as keys and subsequent text serves as values.
    3. **Extraction**: Standard fields (`thought`, `notes`, `response_to_user`, `agent_target`) are pulled from the map.
    4. **Manifest Parsing**: The `____@manifest` block is processed via `_parse_key_value_block`.
    5. **Tool Parsing**: If a `____@tool:` token is found, `_parse_tool_block` is invoked to extract the tool name, intent, and sanitized YAML arguments.
    6. **Output**: A structured dictionary containing `status`, `thought`, `notes`, `manifest`, `action`, and `response_to_user` is returned.
- **Conditional Branching**:
    - **YAML Sanitization**: If a multi-line block (`|`) is detected, the parser forces a 2-space indentation to correct model drift.
    - **Error Handling**: If YAML parsing fails within a tool block, the error is logged via `func.log` and the error message is embedded in the `tool_parameters`.
    - **Global Exception**: Any catastrophic failure during the `parse` method returns a dictionary with `status: "FAILED"`.

## 5. Resource Dependencies

- **Standard Libraries**: `re`, `yaml`, `typing`
- **Internal Modules**: 
    - [functions](/docs/functions.md)
- **External Packages**: `PyYAML`