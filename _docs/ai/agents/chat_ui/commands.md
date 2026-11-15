## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| commands | ai/agents/chat_ui/commands.md |

This component centralizes the definition and implementation of all slash commands available within the agent chat UI. Its primary responsibility is to expose a structured interface to the user, allowing them to execute specific system functions—such as clearing the session, viewing pipeline details, or toggling agent reasoning—via simple command inputs.

Architecturally, this module functions as a command dispatcher and handler registry for the UI layer. It utilizes functions like `_help`, `_clear`, and `_session` to encapsulate the logic that interacts with the core application state managed by `AgentChatApp`, coordinating state changes through methods on that object.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| Command | Class | Defines a single chat command, holding its name, help text, handler function, and whether it can execute while the agent is busy. |
| COMMANDS | Dictionary | A mapping of command names (string) to `Command` instances, serving as the registry for all available commands. |

## 3. Implementation Details & Side Effects
- **Core Logic:** Commands are registered in the `COMMANDS` dictionary. When a command is invoked, its associated handler function is executed, receiving the `AgentChatApp` instance and the command argument. Handlers perform specific actions like querying session managers, modifying program configuration, or triggering UI state changes.
- **Side Effects:** Yes. Commands interact heavily with the filesystem (e.g., `/resume` lists sessions in the current directory), mutate global state (e.g., `/clear` starts a new session, `/thoughts` changes `ProgramConfig`), and print output via `app.write`.
- **Error Handling:** Specific commands implement error handling. For instance, `/resume` uses `try...except` blocks when resolving session IDs, and `/pipeline` catches general exceptions when attempting to switch pipelines.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `uuid`, `dataclasses`, `typing`.
- **Internal:** [ProgramConfig](/ai/config.md), [ProgramSetting](/ai/config.md), [AgentChatApp](/ai/agents/chat_ui/app.md), [AgentSessionManager](/ai/agents/session_manager.md), [render_session_row](/ai/agents/chat_ui/renderer.md), [resolve_session_id](/ai/agents/chat_ui/session_picker.md).