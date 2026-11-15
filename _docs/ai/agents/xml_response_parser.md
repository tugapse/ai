## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| ResponseParser | /ai/agents/xml_response_parser.md |

This component, embodied by the `ResponseParser` class, is responsible for reliably extracting structured data from raw strings provided by an AI model. It anticipates that the response will contain structured data, either in XML or JSON format, typically wrapped within `<response>` tags. Its primary function is to parse this potentially messy, LLM-generated content into a predictable, usable Python dictionary structure containing fields like `thought`, `action`, `manifest`, and `response_to_user`.

This parser acts as a critical service layer component within the agent framework. It sits downstream of the LLM interaction layer, taking raw output and transforming it into a canonical data model that other parts of the system, such as the execution engine or state manager, can consume. It interacts heavily with utilities like [ai.functions](/ai/functions.md) for logging and debugging.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `ResponseParser` | Class | Manages the parsing logic, initialized with a `parameter_mode` ("xml" or "json"). |
| `ResponseParser.__init__` | Method | Initializes the parser, setting the expected parameter format. |
| `ResponseParser.parse` | Method | The main entry point; attempts strict parsing, falls back to recovery methods, and returns a final result dictionary. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The parser employs a multi-stage approach. It first attempts strict parsing by locating and processing a full `<response>...</response>` block using `xml.etree.ElementTree`. If this fails, it enters a recovery mode, using regular expressions (`_extract_fields` and `_candidate_block`) to surgically pull out known tags regardless of surrounding structural integrity. It utilizes extensive sanitization routines (`_preprocess_xml`, `_sanitize_tool_params`) to counteract common LLM formatting errors before parsing.
- **Side Effects:** None, beyond internal logging via `ai.functions`.
- **Error Handling:** It implements robust fallback mechanisms. If strict XML parsing fails, it attempts recursive sanitization. If all parsing fails, it defaults to regex-based field extraction. The final `parse` method returns a dictionary indicating "FAILED" status if no discernible instruction (tool call, target, or user response) can be found.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `xml.etree.ElementTree`, `html`, `json`, `re`, `typing`.
- **Internal:** [ai.functions](/ai/functions.md).