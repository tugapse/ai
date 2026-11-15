## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| tool_preview | ai/agents/tool_preview.md |

This component is responsible for generating human-readable, ANSI-colored previews of tool calls that require Human-in-the-Loop (HIL) approval. Its primary function is to translate complex tool parameters (like file paths, commands, or patch operations) into a clear, concise, and visually distinct summary that can be presented to a user in the chat UI or console prompt.

Architecturally, this serves as a presentation layer utility within the agent system. It consumes tool definitions and parameters and outputs structured text representations. It interacts with filesystem knowledge (via `os.path.exists`) to enrich previews for operations like `write_file`, fitting into the broader workflow management service that controls agent execution flow.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| describe_tool_request | Function | Generates a list of strings describing a pending tool call based on the provided tool name and parameters. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The function dispatches based on the `tool` name. For specific tools (`execute_command`, `write_file`, `patch_file`, `delete_file`), it constructs a highly formatted list of lines using predefined ANSI color codes. For generic tools, it iterates over the first six parameters, displaying key/value pairs. Helper functions like `_clip` and `_block` handle text truncation and grouping for readability.
- **Side Effects:** Reads from the filesystem via `os.path.exists` when processing the `write_file` tool to determine if a file already exists.
- **Error Handling:** Handles cases where input parameters might be non-dictionary types by coercing them to an empty dictionary.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `typing`
- **Internal:** None