## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| renderer | /ai/agents/chat_ui/renderer.md |

This component is responsible for translating internal application events and state data into formatted, ANSI-encoded strings suitable for display in a chat user interface. Its primary function is to decouple the rendering logic from the UI framework, ensuring that output can be reliably printed from any thread via `prompt_toolkit`'s raw patching mechanism.

It serves as a critical presentation layer utility within the application architecture. It consumes structured data from the agent execution pipeline—such as `AgentEvent`s, `LiveState`, and results—and transforms them into user-facing visual elements like status lines, transcript entries, and tool call indicators, providing a cohesive experience for the end-user.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| LiveState | Class | Mutable state tracking the real-time progress of an agent turn (e.g., busy status, token count, phase). |
| _truncate | Function | Truncates a string or object to a specified length, ensuring it remains readable. |
| _indent | Function | Formats a string by prefixing every line with a specified indentation string. |
| format_tokens | Function | Converts a raw token count integer into a human-readable string (e.g., "1.2k"). |
| format_duration | Function | Converts a duration in seconds (float) into a concise time string (e.g., "2m 15s"). |
| summarize_params | Function | Creates a one-line, truncated summary string for a tool's input parameters. |
| summarize_result | Function | Analyzes a tool execution result to determine success and generate a short, descriptive summary. |
| render_user_message | Function | Renders a single user message into a formatted transcript entry, highlighting the first line. |
| render_event | Function | Converts a specific `AgentEvent` into its corresponding committed output string, returning `None` if the event is intended only for live display. |
| render_status_line | Function | Generates a formatted, committed status line reflecting the agent's current phase and status. |
| render_turn_summary | Function | Generates the final summary message after a turn concludes, based on the ending reason and `LiveState`. |
| render_live_line | Function | Renders the dynamic, continuously updating line shown while the agent is actively processing. |
| render_status_bar | Function | Generates the persistent status bar at the bottom of the UI, showing model, session ID, and pipeline status. |
| render_transcript | Function | Renders a history of past conversation entries for resuming a session. |
| render_permission | Function | Generates a UI prompt asking the user for explicit permission regarding a tool call. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The component relies on specialized rendering functions to handle different UI contexts: `render_live_line` manages the dynamic spinner state, while `render_event` acts as a dispatcher, routing various `AgentEventType`s to specific formatting routines (e.g., using `summarize_params` for `TOOL_CALL`). State management is handled via the mutable `LiveState` dataclass, which tracks temporal data like elapsed time and token usage.
- **Side Effects:** None. The code is purely functional in its output generation; it does not interact with I/O, network, or global state outside of the data passed into its rendering functions.
- **Error Handling:** The code implements fallback mechanisms in `summarize_result` by checking for common result keys (`result`, `content`, `output`, etc.) to ensure a summary is always returned, even if the structure is unexpected. `render_event` explicitly returns `None` for events that are not meant for committed output (e.g., `STATUS` or `LLM_REQUEST`).

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `json`, `time`, `dataclasses`, `typing`
- **Internal:** [ai/agents/agent_io/AgentEvent](/ai/agents/agent_io/agent_event.md), [ai/agents/terminal_ui/TerminalUI](/ai/agents/terminal_ui/terminal_ui.md)