## 1. Architectural Role
Acts as an event-driven middleware that intercepts chat input to execute system-level commands (save, load, list) or delegate to custom command handlers before standard chat processing.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ChatCommandInterceptor` | Class | Manages the lifecycle of command interception and session persistence. |
| `__init__` | Method | Registers the `run` method to the `Chat.EVENT_COMMAND_STARTED` event and initializes state. |
| `run` | Method | Parses raw command strings and routes them to specific command handlers or error states. |
| `save_session` | Method | Serializes `chat.messages` to a JSON file within the `root_folder`. |
| `load_session` | Method | Deserializes a JSON file into `chat.messages` and triggers a visual replay via `ConsoleChatReader`. |
| `list_sessions` | Method | Iterates through `root_folder` to display available session files. |
| `handled_extra_command` | Method | (Implicit/External) Evaluates if a command belongs to the `extra_commands` registry. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Instance receives `chat` object and `root_folder` string.
    2. `self.chat.add_event` binds `self.run` to `Chat.EVENT_COMMAND_STARTED`.
    3. `self.extra_commands` is initialized as an empty list.
- **Data Path**: 
    - **Command Input**: `command_text` (str) $\rightarrow$ `parts` (list of substrings).
    - **Persistence (Save)**: `self.chat.messages` (list/dict) $\rightarrow$ `json.dump` $\rightarrow$ File System.
    - **Persistence (Load)**: File System $\rightarrow$ `json.load` $\rightarrow$ `self.chat.messages` $\rightarrow$ `ConsoleChatReader._print_chat` (UI output).
- **Conditional Branching**:
    - **Command Routing**: Checks if `parts[0]` matches built-in commands (`/save`, `/load`, `/list`).
    - **Sub-command Logic**: Within built-ins, checks `startswith` to determine specific action.
    - **Custom Command Logic**: If not a built-in, checks if `command` exists in `self.extra_commands`.
    - **Error Handling**: If no match is found, executes `func.out("Invalid Command")`.
    - **Termination**: If a command is successfully identified/handled, calls `self.chat.terminate_command()` to prevent standard message processing.

## 4. Resource Dependencies
- **Standard Libraries**: `json`, `os`
- **Internal Modules**: `chat.chat.Chat`, `color.Color`, `extras.ConsoleChatReader`, `functions` (as `func`)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - Command triggers: `'/save'`, `'/load'`, `'/list'`
    - Error message: `"Invalid Command"`
    - Log levels: `"INFO"`, `"WARNING"`
- **Environment Lookups**: None.