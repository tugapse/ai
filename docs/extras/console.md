## 1. Architectural Role
Provides a console-based reader and formatter to load JSON chat histories and render them to the terminal with role-based coloring and inline code block highlighting.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ConsoleChatReader` | Class | Manages the loading of chat JSON files and coordinates the printing of messages to the console. |
| `ConsoleTokenFormatter` | Class | Tracks and applies ANSI color codes to tokens to highlight text enclosed in double backticks (``). |
| `ConsoleChatReader.load` | Method | Reads a JSON file, parses the list of messages, and triggers the print sequence. |
| `ConsoleChatReader._print_chat` | Method | Filters system messages and applies role-specific colors and labels to the output. |
| `ConsoleChatReader.color_text` | Method | Splits message content into tokens and passes them through the `ConsoleTokenFormatter`. |
| `ConsoleTokenFormatter.process_token` | Method | Toggles the `printing_block` state and appends `Color.YELLOW` or `Color.RESET` when encountering ``. |
| `ConsoleTokenFormatter.clear_process_token` | Method | Resets the `printing_block` state to `False`. |

## 3. Execution Logic & Flow
- **Initialization**: 
    - `ConsoleChatReader` initializes with a `filename`, creates a `Path` object, and instantiates a `ConsoleTokenFormatter`.
    - `ConsoleTokenFormatter` initializes a `token_states` dictionary with `printing_block` set to `False`.
- **Data Path**: 
    - `load()` $\rightarrow$ `Path.read_text()` $\rightarrow$ `json.loads()` $\rightarrow$ Loop through messages $\rightarrow$ `_print_chat()`.
    - `_print_chat()` $\rightarrow$ `color_text()` $\rightarrow$ `process_token()` $\rightarrow$ `func.out()`.
- **Conditional Branching**:
    - **Role Filter**: In `_print_chat`, if `chat_message['role'] == ChatRoles.SYSTEM`, the message is skipped.
    - **Role Styling**: If `role == ChatRoles.USER`, color is `Color.BLUE` and label is "User :"; otherwise, color is `Color.YELLOW` and label is "Assistant".
    - **Token Highlighting**: In `process_token`, if ` `` ` is detected:
        - If `printing_block` is `False`: Append `Color.YELLOW` and set `printing_block` to `True`.
        - If `printing_block` is `True`: Append `Color.RESET` and set `printing_block` to `False`.

## 4. Resource Dependencies
- **Standard Libraries**: `json`, `pathlib.Path`
- **Internal Modules**: `color.Color`, `core.ChatRoles`, `functions` (aliased as `func`)
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `Color.BLUE`: Assigned to `ChatRoles.USER`.
    - `Color.YELLOW`: Assigned to Assistant role and inline code blocks.
    - `Color.RESET`: Used to clear formatting.
- **Environment Lookups**: None