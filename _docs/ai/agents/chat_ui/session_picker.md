## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| SessionPicker | /ai/agents/chat_ui/session_picker.md |

This component provides a user interface for selecting a previously run agent session via a keyboard-driven picker. It handles filtering, navigation, and display of available sessions, allowing the user to resume a specific interaction history. The primary responsibility is to present a manageable list of sessions derived from the input list, filtered by a user query.

This module acts as a specialized UI component within the application's chat interaction layer. It utilizes `prompt_toolkit` to render an interactive selection window, coordinating session data with the rendering logic provided by [renderer](/ai/agents/chat_ui/renderer.md). It sits between the core session management logic and the user input stream.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `format_age` | Function | Calculates a human-readable relative time string from a Unix timestamp. |
| `_one_line` | Function | Truncates or cleans a string to fit within a specified character limit. |
| `filter_sessions` | Function | Filters a list of sessions based on a case-insensitive query matching session ID, request, or last message. |
| `render_session_row` | Function | Generates the formatted string representation for a single session row in the picker UI. |
| `SessionPicker` | Class | Manages the interactive state and rendering of the session selection interface. |
| `pick_session` | Function | Entry point function that initializes and runs the `SessionPicker` to return the selected session ID. |
| `resolve_session_id` | Function | Attempts to find a unique session ID matching a given query, raising an error if the query is ambiguous. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `SessionPicker` manages an internal index against a filtered list of sessions (`self.visible`). The `_text` method dynamically calculates the visible subset of rows based on the current index and window size. Keyboard bindings (Up, Down, Enter, etc.) update the internal state (`self.index` or `self.query`), which triggers a re-render of the UI via `FormattedTextControl`.
- **Side Effects:** The component interacts with the terminal environment via `prompt_toolkit` to display the UI and captures user input. The `run()` method blocks execution until the user selects an option or cancels.
- **Error Handling:** `resolve_session_id` explicitly raises a `ValueError` if the provided query matches more than one session ID, indicating ambiguity. The `SessionPicker` handles UI rendering gracefully when no sessions match the query.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `time`, `typing`, `prompt_toolkit`
- **Internal:** [renderer](/ai/agents/chat_ui/renderer.md)