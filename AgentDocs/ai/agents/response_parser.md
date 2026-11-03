## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **ResponseParser** | [src/ai/agents/response_parser.py](/AgentDocs/ai/agents/response_parser.md) |

The `ResponseParser` is a specialized utility designed to interpret the JARVIS Plain Text Protocol, which utilizes proprietary tokens (e.g., `, `____@`) to structure unstructured model output. Its primary responsibility is to transform raw string responses from Large Language Models (LLMs) into structured, actionable data dictionaries containing thoughts, notes, manifests, and tool execution commands.

This component serves as a critical bridge in the agent architecture, specifically addressing the formatting inconsistencies and "indentation drift" common in smaller (e.g., 8B parameter) models. By sanitizing YAML blocks and normalizing tokenized segments, it ensures that the downstream orchestration logic receives predictable and valid data structures.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ResponseParser()` | Class | The main parser class used to initialize the regex engine for token detection. |
| `parse(raw_string: str)` | Method | The primary entry point. Takes a raw model response string and returns a dictionary containing `status`, `thought`, `notes`, `manifest`, `action`, and `response_to_user`. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **Tokenization:** Uses a compiled regular expression (`token_pattern`) to split the input string into segments based on the `____@` prefix.
    - **YAML Sanitization:** Implements a specialized `_sanitize_yaml` method to fix common LLM errors, such as unquoted special variables (e.g., `@ROOT`) and inconsistent indentation in multi-line code blocks.
    - **Block Parsing:** Employs hierarchical parsing to extract `INTENT` and `ARGS` from tool blocks, and key-value pairs from manifest blocks.
- **Side Effects:** None. This is a pure data transformation component.
- **Error Handling:** The `parse` method is wrapped in a broad `try-except` block. If parsing fails due to malformed input or logic errors, it returns a dictionary with `"status": "FAILED"` and an error message rather than raising an exception, ensuring the agent pipeline can handle the failure gracefully.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `re` (regex), `yaml` (parsing), `typing` (type hinting).
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md) (Used for error logging via `func.log`).