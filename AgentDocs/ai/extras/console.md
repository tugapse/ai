## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **ConsoleChatReader & ConsoleTokenFormatter** | [src/ai/extras/console.py](/AgentDocs/ai/extras/console.md) |

The `ConsoleChatReader` component is responsible for reading structured chat history from JSON files and rendering it to the standard output (console). It provides a human-readable view of past interactions by distinguishing between different speaker roles and applying visual formatting to the text content.

This component serves as a utility for debugging or reviewing conversation logs. It fits into the broader application architecture as a presentation utility, transforming serialized chat data into a formatted terminal interface. It utilizes specialized color logic and token-based processing to highlight specific text patterns, such as code blocks.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ConsoleChatReader(filename)` | Class | Initializes a reader for a specific JSON file path. |
| `ConsoleChatReader.load()` | Method | Reads the JSON file and prints the formatted chat history to the console. Raises `FileNotFoundError` if the file is missing. |
| `ConsoleTokenFormatter()` | Class | A stateful formatter used to apply terminal colors to specific text tokens. |
| `ConsoleTokenFormatter.process_token(token)` | Method | Processes a single string token, toggling color states when encountering backtick delimiters (``). |
| `ConsoleTokenFormatter.clear_process_token()` | Method | Resets the internal `printing_block` state to `False`. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - `ConsoleChatReader` iterates through a list of message dictionaries. It filters out messages where the role matches `ChatRoles.SYSTEM`. 
    - For valid messages, it assigns colors (Blue for `USER`, Yellow for `ASSISTANT`) and passes the content through `ConsoleTokenFormatter`.
    - `ConsoleTokenFormatter` maintains a `token_states` dictionary. When a token contains the ` `` ` sequence, it toggles a `printing_block` boolean, which determines whether subsequent text is wrapped in specific color codes or reset.
- **Side Effects:** 
    - **Filesystem:** Reads from the local filesystem via `pathlib.Path`.
    - **Standard Output:** Writes formatted, colored text directly to the console using `ai.functions.out`.
- **Error Handling:** 
    - Explicitly raises `FileNotFoundError` if the provided `filename` does not exist on the filesystem.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `json`, `pathlib`.
- **Internal:**
    - [ai.chat.chat.ChatRoles](/AgentDocs/ai/chat/chat.md)
    - [ai.color.Color](/AgentDocs/ai/color.md)
    - [ai.functions](/AgentDocs/ai/functions.md)