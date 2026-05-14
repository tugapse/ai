## 1. Architectural Role

**Functional Mission**
The **ChatCommandInterceptor** class serves as a specialized command listener and dispatcher within the chat interface. Its primary mission is to intercept user input strings that follow a command pattern (e.g., starting with `/`), preventing them from being processed as standard conversational text and instead routing them to specific system operations such as session persistence, session retrieval, or custom command execution.

**System Context & Integration**
This component acts as a middleware layer between the raw user input and the core chat logic. It integrates directly with [Chat](/docs/chat/chat.md) by subscribing to the `EVENT_COMMAND_STARTED` event. When a command is detected, the interceptor manages the state transition of the chat sessioneither by performing I/O operations via the file system or by delegating to `extra_commands`. If a command is successfully handled, it invokes `terminate_command()` on the [Chat](/docs/chat/chat.md) instance to halt the standard message processing pipeline.

## 2. Environment & Configuration
**Environment Lookups:**
- `root_folder` (via `__init__`)  Defines the directory path where chat session JSON files are stored and retrieved.

**Hardcoded Constants:**
- `['/save', '/load', '/list']`  The set of reserved system command keywords.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ChatCommandInterceptor` | Class | Orchestrates command interception, session I/O, and command routing. |
| `__init__` | Method | Registers the interceptor to the chat's event system and sets the storage root. |
| `run` | Method | The primary entry point triggered by `EVENT_COMMAND_STARTED`; parses and routes commands. |
| `save_session` | Method | Serializes the current `chat.messages` list to a JSON file in the `root_folder`. |
| `load_session` | Method | Deserializes a JSON file into `chat.messages` and triggers a console replay. |
| `list_sessions` | Method | Scans the `root_folder` and prints all available session files. |
| `handled_extra_command` | Method | (Internal/Implicit) Logic to delegate execution to user-defined custom commands. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. Receives a `Chat` instance and a `root_folder` string.
    2. Attaches the `run` method to the `Chat.EVENT_COMMAND_STARTED` event listener.
    3. Initializes an empty `extra_commands` list for extensibility.
- **Data Path**: 
    1. **Input**: `command_text` (string) received from the event trigger.
    2. **Processing**: 
        - Split string into `parts`.
        - Identify `command` (first element).
        - Match `command` against reserved list or `extra_commands`.
        - If `/save` or `/load`: Perform File I/O using `json` and `os`.
        - If `/list`: Perform directory listing via `os.listdir`.
    3. **Output**: Side effects including file creation/reading, console output via `func.out`, or calling `chat.terminate_command()`.
- **Conditional Branching**:
    - **Command Match**: If the command is recognized, execute specific logic; otherwise, call `func.out("Invalid Command")`.
    - **File Existence**: In `load_session`, if the target file does not exist in `root_folder`, trigger a `WARNING` and abort.
    - **Extra Commands**: If the command is in `extra_commands`, attempt `handled_extra_command`; if it returns `True`, the flow is halted.

## 5. Resource Dependencies
- **Standard Libraries**: `json`, `os`
- **Internal Modules**: 
    - [Chat](/docs/chat/chat.md)
    - [Color](/docs/color.md)
    - [ConsoleChatReader](/docs/extras/__init__.md) (via `extras` package)
    - [functions](/docs/functions.md)
- **External Packages**: None identified.