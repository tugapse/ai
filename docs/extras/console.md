## 1. Architectural Role
Provides a mechanism for reading JSON-formatted chat histories from disk and rendering them to the terminal with role-based color coding and token-level syntax highlighting for code blocks.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ConsoleChatReader` | Class | Orchestrates the loading, parsing, and terminal output of chat history files. |
| `__init__` | Method | Initializes the reader with a target filename and a `ConsoleTokenFormatter` instance. |
| `load` | Method | Validates file existence, parses JSON content, and iterates through messages for printing. |
| `_print_chat` | Method | Determines role-based colors/labels and triggers the colorization and output process. |
| `color_text` | Method | Splits raw text into tokens and applies formatting via the token processor. |
| `ConsoleTokenFormatter` | Class | Maintains stateful formatting logic for detecting and highlighting code blocks. |
| `__init__` | Method | Initializes the `token_states` dictionary with `printing_block` set to `False`. |
| `process_token` | Method | Toggles color states when encountering `` `` `` and returns the formatted string. |
| `clear_process_token` | Method | Resets the `printing_block` state to `False`. |

## 3. Execution Logic & Flow
- **Initialization**: 
    - `ConsoleChatReader` captures the `filename` and converts it to a `Path` object, instantiating a `ConsoleTokenFormatter`.
    - `ConsoleTokenFormatter` initializes its internal `token_states` dictionary.
- **Data Path**: 
    - `Path(filename)` $\rightarrow$ `json.loads()` $\rightarrow$ `list[dict]` $\rightarrow$ `_print_chat()` $\rightarrow$ `color_text()` $\rightarrow$ `process_token()` $\rightarrow$ `func.out()`.
- **Conditional Branching**:
    - **File Check**: `load` checks `path_file.exists()`; raises `FileNotFoundError` if missing.
    - **Role Filtering**: `_print_chat` skips processing if `chat_message['role']` is `ChatRoles.SYSTEM`.
    - **Color Assignment**: `_print_chat` selects `Color.BLUE` for `ChatRoles.USER` and `Color.YELLOW` otherwise.
    - **Syntax Toggling**: `process_token` checks for `` `` `` in a token; if `printing_block` is `False`, it appends `Color.YELLOW` and sets state to `True`; if `True`, it appends `Color.RESET` and sets state to `False`.

## 4. Resource Dependencies
- **Standard Libraries**: `json`, `pathlib.Path`
- **Internal Modules**: `chat.chat.ChatRoles`, `color.Color`, `functions` (as `func`)
- **External Packages**: None specified (relies on internal `color` and `functions` modules)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `ChatRoles.SYSTEM` (Filter criteria)
    - `ChatRoles.USER` (Color/Label criteria)
    - `` `` `` (Code block delimiter)
    - `"User :"` and `"Assistant"` (Label strings)
- **Environment Lookups**: None