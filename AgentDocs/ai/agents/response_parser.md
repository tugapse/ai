## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **ResponseParser** | [src/ai/agents/response_parser.py](/src/ai/agents/response_parser.py) |

The `ResponseParser` is a specialized parsing engine designed to interpret the JARVIS Plain Text Protocol. It is specifically engineered to handle the output of smaller-parameter LLMs (such as 8B models) that may exhibit formatting inconsistencies, including indentation drift and unquoted special characters in YAML blocks.

This component acts as a critical bridge between raw model output and the structured orchestration layer. It extracts internal reasoning (thought), metadata (notes/manifest), and actionable tool calls from unstructured text by identifying proprietary tokens (e.g., `, `____@`). It ensures that the `agent_orchestrator` or other system controllers receive a standardized, sanitized dictionary rather than raw string data.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ResponseParser()` | Class | Initializes the parser and compiles the regex pattern for identifying JARVIS protocol tokens. |
| `parse(raw_string: str)` | Method | The primary entry point. Takes a raw string from an LLM and returns a dictionary containing `status`, `thought`, `notes`, `manifest`, `action` (including tool name and parameters), and `response_to_user`. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **Token Splitting:** Uses a regex-based approach to split the input string into segments based on the `____@` prefix.
    - **YAML Sanitization:** Implements a custom `_sanitize_yaml` method that uses regex to wrap unquoted `@` variables in quotes and manually corrects indentation drift for multi-line code blocks (e.g., `content: |`).
    - **Block Extraction:** Separates tool headers from their content, extracts `INTENT` and `ARGS` blocks, and uses `yaml.safe_load` to convert the sanitized arguments into Python dictionaries.
    - **Manifest Parsing:** Processes key-value pairs for the `____@manifest` token to manage phase and priority metadata.
- **Side Effects:** 
    - Performs logging via [ai.functions](/AgentDocs/ai/functions.md) if YAML parsing fails within a tool block.
- **Error Handling:** 
    - If a YAML block is malformed, it catches the exception and returns a dictionary containing an `error` key within the `tool_parameters` instead of crashing the parser.
    - If the entire parsing process fails, the `parse` method returns a dictionary with `status: "FAILED"` and an error message.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `re`, `yaml`, `typing`.
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)