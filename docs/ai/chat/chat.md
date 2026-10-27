## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | Chat |
| Source file | chat.py |

The **Chat** component serves as the primary interactive interface layer for the AI system, managing the lifecycle of user-to-assistant communication. It orchestrates the terminal-based input/output loop, handles complex user input modes (such as multiline and agent tasking), and manages the staging of file attachments for context injection.

By implementing the `Events` interface, the component acts as a central dispatcher that translates raw user input into high-level system events. It bridges the gap between the low-level terminal interaction (via `prompt_toolkit`) and the high-level logic required for command execution and agentic workflows.

**Functional Mission**
The primary responsibility of **Chat** is to provide a robust, feature-rich Command Line Interface (CLI) that supports advanced interaction patterns like file attachment (`@path`), command execution (`/command`), and agentic tasking (`/agent`). It solves the problem of managing stateful, multi-modal (text + file context) conversations within a synchronous terminal environment.

**System Context & Integration**
The component sits at the edge of the application, receiving input from the user and triggering events that drive the rest of the system. It integrates with [Events](/docs/ai/core/events.md) to signal when messages are sent or commands are initiated. When a user attaches a file, the component stages the content, which is then merged with the subsequent prompt to provide context to the LLM. It relies on [BaseModel](/docs/ai/core/llms/base_llm.md) to structure the message objects that are passed downstream to the orchestration layers.

- **INTERNAL REFERENCES**: [Events](/docs/ai/core/events.md), [BaseModel](/docs/ai/core/llms/base_llm.md), [Color](/docs/ai/color.md), [func](/docs/ai/functions.md).

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `ChatRoles.USER` (Default: `"user"`)  Role identifier for user messages.
- `ChatRoles.ASSISTANT` (Default: `"assistant"`)  Role identifier for AI responses.
- `ChatRoles.SYSTEM` (Default: `"system"`)  Role identifier for system instructions.
- `ChatRoles.CONTROL` (Default: `"control"`)  Role identifier for internal control signals.
- `ChatRoles.TOOL` (Default: `"tool"`)  Role identifier for tool outputs.
- `self.max_chat_log` (Default: `50`)  Maximum number of messages to retain in memory.
- `self.terminate_tokens` (Default: `["quit", "q"]`)  Strings that trigger session termination.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ChatRoles` | Class | Provides constant string identifiers for message roles. |
| `PrefixCompleter` | Class | Custom `prompt_toolkit` completer for `/` commands and `@` file paths. |
| `Chat` | Class | The main controller for the interactive chat session. |
| `update_suggestions` | Method | Dynamically updates available commands and agents. |
| `loop` | Method | The main blocking execution loop for the chat interface. |
| `process_loop_frame` | Method | Handles a single iteration of the prompt/input cycle. |
| `_handle_file_attachment` | Method | Reads file content from disk and stages it in `pending_files`. |
| `send_chat` | Method | Formats user input and triggers the `EVENT_CHAT_SENT` event. |
| `run_command` | Method | Routes input to specific command handlers (e.g., `/clear`, `/agent`). |
| `chat_finished` | Method | Finalizes an assistant response and updates message history. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. Initializes state variables (`terminate`, `running_command`, `waiting_for_response`).
    2. Sets up `PromptSession` with `InMemoryHistory`.
    3. Configures `PrefixCompleter` for command and file path autocompletion.
    4. Defines key bindings for toggling `multiline_mode`.
- **Data Path**: 
    1. **Input**: User types text in the terminal.
    2. **Parsing**: `process_loop_frame` checks for prefixes (`@` for files, `/` for commands).
    3. **Context Merging**: If `pending_files` exist, their content is prepended to the user's text.
    4. **Dispatch**: The processed string is sent via `send_chat` or `trigger` (for agent tasks).
    5. **Output**: The assistant's response is captured and added to `self.messages`.
- **Conditional Branching**:
    - **File Attachment**: If input starts with `@`, the loop breaks to `_handle_file_attachment` and waits for the next input.
    - **Agent Mode**: If `agent_mode_active` is True, the input is treated as a task rather than a standard chat message.
    - **Multiline Mode**: Controlled by `[Alt+Enter]` or `[Enter]` depending on the `multiline_mode` boolean state.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `sys`, `datetime`, `typing`
- **Internal Modules**: 
    - [func](/docs/ai/functions.md)
    - [Events](/docs/ai/core/events.md)
    - [Color](/docs/ai/color.md)
    - [BaseModel](/docs/ai/core/llms/base_llm.md)
- **External Packages**: `prompt_toolkit`