## 1. Architectural Role
This file defines a `ChatCommandInterceptor` class responsible for intercepting and handling commands in a chat session, including saving, loading, and listing chat sessions.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ChatCommandInterceptor` | Class | Intercepts and handles commands in a chat session. |
| `__init__` | Method | Initializes the interceptor with a chat object and a root folder. |
| `run` | Method | Handles a command by splitting it into parts and determining what action to take. |
| `save_session` | Method | Saves the current chat session to a file. |
| `load_session` | Method | Loads a chat session from a file. |
| `list_sessions` | Method | Lists all chat sessions stored in the root folder. |

## 3. Execution Logic & Flow
- **Initialization**: The `ChatCommandInterceptor` is initialized with a `Chat` object and a `root_folder`. It attaches itself to the chat's `EVENT_COMMAND_STARTED` event to intercept commands.
- **Data Path**: 
  - Input: A command text string.
  - Processing: The command text is split into parts, and the first part is identified as the command.
  - Output: Depending on the command, the appropriate action (save, load, list, or invalid command) is taken.
- **Conditional Branching**: 
  - The command is checked against predefined commands (`/save`, `/load`, `/list`).
  - If the command is a custom command, it is checked against `extra_commands`.
  - If the command is not recognized, an invalid command message is output.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `json`
- **Internal Modules**: `core.chat`, `color`, `extras.ConsoleChatReader`
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: `root_folder` (path where chat sessions are stored)
- **Environment Lookups**: None