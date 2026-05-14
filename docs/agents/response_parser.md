## 1. Architectural Role
Provides a robust parsing engine to transform raw text containing JARVIS Plain Text Protocol tokens (`____@`) into structured dictionaries, specifically handling LLM-induced YAML formatting errors and indentation drift.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ResponseParser` | Class | Orchestrates the segmentation and transformation of raw model strings into structured data. |
| `__init__` | Method | Compiles the `token_pattern` regex for segmenting the input string. |
| `_parse_key_value_block` | Method | Parses simple `KEY: VALUE` string patterns for manifest extraction. |
| `_sanitize_yaml` | Method | Corrects unquoted special variables and normalizes indentation drift in YAML blocks. |
| `_parse_tool_block` | Method | Extracts tool name, intent, and sanitized YAML arguments from a tool-specific token block. |
| `parse` | Method | The primary entry point; executes the full transformation pipeline from raw string to structured dict. |

## 3. Execution Logic & Flow
- **Initialization**: The `ResponseParser` instance compiles a regex pattern `(____@[A-Za-z_:]+)` to identify protocol tokens.
- **Data Path**: 
    1. **Input**: Raw string containing `____@` tokens and text.
    2. **Segmentation**: `parse` splits the string via `token_pattern`, mapping tokens to their subsequent content.
    3. **Extraction**: Key fields (`thought`, `notes`, `response`, `TARGET`, `manifest`) are pulled from the `data_map`.
    4. **Tool Processing**: If a `____@tool:` token is detected, `_parse_tool_block` is invoked.
    5. **YAML Sanitization**: Within tool parsing, `_sanitize_yaml` applies regex to quote `@` variables and iterates through lines to force 2-space indentation on multi-line blocks.
    6. **Output**: A structured dictionary containing `status`, `thought`, `notes`, `manifest`, `action` (tool details), and `response_to_user`.
- **Conditional Branching**:
    - **Tool Detection**: Checks if any key in `data_map` starts with `____@tool:`.
    - **YAML Block Detection**: Inside `_sanitize_yaml`, checks for multi-line indicators (`|`) to toggle indentation enforcement logic.
    - **Error Handling**: `try-except` blocks wrap YAML loading and the main `parse` loop to return a `FAILED` status instead of crashing.

## 4. Resource Dependencies
- **Standard Libraries**: `re`, `yaml`, `typing`
- **Internal Modules**: `functions as func`
- **External Packages**: `PyYAML` (via `import yaml`)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `token_pattern`: `r"(____@[A-Za-z_:]+)"`
    - `agent_target` default: `"STOP"`
    - Indentation increment: `"  "` (two spaces)
- **Environment Lookups**: None.