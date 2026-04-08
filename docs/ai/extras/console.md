## 1. Architectural Role
Handles the reading and formatting of chat messages from a JSON file for console output.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ConsoleChatReader` | Class | Reads chat messages from a JSON file and formats them for console output. |
| `load` | Method | Loads chat messages from the specified file and prints them. |
| `_print_chat` | Method | Prints a single chat message, formatting it based on the message role. |
| `color_text` | Method | Colors the text of a chat message based on the message role. |
| `ConsoleTokenFormatter` | Class | Formats tokens within chat messages, particularly handling code blocks. |
| `process_token` | Method | Processes a single token, coloring it if it's part of a code block. |

## 3. Execution Logic & Flow
- **Initialization**: 
  - The `ConsoleChatReader` class is initialized with a filename.
  - The `path_file` attribute is set to the provided filename.
  - The `content` attribute is initialized to `None`.
  - The `token_processor` attribute is set to an instance of `ConsoleTokenFormatter`.
- **Data Path**:
  - The `load` method checks if the file exists. If not, it raises a `FileNotFoundError`.
  - It reads the file content as JSON and iterates over each chat message.
  - Each chat message is passed to the `_print_chat` method.
- **Conditional Branching**:
  - In `_print_chat`, the method checks if the chat message role is `SYSTEM` and returns early if true.
  - It sets the text color based on the message role (`USER` or `ASSISTANT`).
  - It formats the message content using the `color_text` method.
  - In `color_text`, it processes each token using the `process_token` method of `ConsoleTokenFormatter`.

## 4. Resource Dependencies
- **Standard Libraries**: `json`, `pathlib`
- **Internal Modules**: `color`, `core`
- **External Packages**: `None`

## 5. Configuration & Environment
- **Hardcoded Constants**: `None`
- **Environment Lookups**: `None`