

## 1. Architectural Role  
Reads and displays chat messages from a JSON file, applying role-based coloring and token-level formatting for code blocks.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `ConsoleChatReader` | Class | Loads and prints chat messages from a JSON file with role-based color formatting. |  
| `ConsoleChatReader.__init__` | Method | Initializes file path, content, and token formatter. |  
| `ConsoleChatReader.load` | Method | Loads JSON content and processes each chat message. |  
| `ConsoleChatReader._print_chat` | Method | Renders chat message with role-specific text and colored content. |  
| `ConsoleChatReader.color_text` | Method | Formats tokens in content with color codes for code blocks. |  
| `ConsoleTokenFormatter` | Class | Manages token formatting state for code block highlighting. |  
| `ConsoleTokenFormatter.process_token` | Method | Applies color formatting to tokens containing backticks. |  
| `ConsoleTokenFormatter.clear_process_token` | Method | Resets the code block formatting state. |  

## 3. Execution Logic & Flow  
- **Initialization**: Sets `filename`, `path_file`, `content`, and initializes `token_processor` with `ConsoleTokenFormatter`.  
- **Data Path**:  
  1. `load()` reads JSON file  parses into `j_obj` list.  
  2. Iterates over `j_obj`, calling `_print_chat()` for each message.  
  3. `_print_chat()` filters out system messages, assigns color, and calls `color_text()`.  
  4. `color_text()` splits content into tokens, applies `process_token()` to each.  
- **Conditional Branching**:  
  - Skips system messages via `if chat_message['role'] == ChatRoles.SYSTEM`.  
  - Toggles code block formatting state on ```` tokens via `process_token()`.  

## 4. Resource Dependencies  
- **Standard Libraries**: `json`, `pathlib`.  
- **Internal Modules**: `color`, `core.ChatRoles`, `functions`.  
- **External Packages**: None.  

## 5. Configuration & Environment  
- **Hardcoded Constants**: `ChatRoles.SYSTEM`, `Color.RESET`, `Color.BLUE`, `Color.YELLOW`.  
- **Environment Lookups**: None.