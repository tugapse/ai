## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **ConsoleChatReader** | [src/ai/extras/console.py](/src/ai/extras/console.py) |

The `ConsoleChatReader` component is responsible for reading structured chat history from JSON files and rendering it to the standard output (console). It provides a human-readable interface for reviewing past interactions by applying color-coded formatting to distinguish between different participants in a conversation.

This component acts as a specialized UI utility within the broader application architecture. It bridges the gap between stored data (JSON-based chat logs) and the user's terminal, ensuring that roles like `USER` and `ASSISTANT` are visually distinct and that specific text patterns, such as code blocks, are highlighted for better readability.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ConsoleChatReader(filename)` | Class | Initializes a reader for a specific JSON file. Handles the loading and printing of chat history. |
| `ConsoleChatReader.load()` | Method | Reads the JSON file from disk and iterates through the messages to print them to the console. Raises `FileNotFoundError` if the file is missing. |
| `ConsoleTokenFormatter()` | Class | A stateful utility used to process individual text tokens and apply formatting (e.g., toggling colors for code blocks). |
| `ConsoleTokenFormatter.process_token(token)` | Method | Evaluates a single string token; if it contains double backticks (``), it toggles the internal `printing_block` state and applies color codes. |
| `ConsoleTokenFormatter.clear_process_token()` | Method | Resets the `printing_block` state to `False`. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - The `ConsoleChatReader` iterates through a list of message dictionaries. It filters out `ChatRoles.SYSTEM` messages and applies specific colors (Blue for User, Yellow for Assistant) using [Color](/AgentDocs/ai/color.md).
    - Text content is processed via `ConsoleTokenFormatter`, which splits text by spaces and evaluates each token. The formatter uses a state machine (`token_states`) to track whether the current token is inside a code block (detected by ``), allowing it to wrap subsequent text in color codes until the block is closed.
- **Side Effects:** 
    - **Filesystem:** Reads files from the local filesystem via `pathlib`.
    - **Standard Output:** Writes formatted, colored text directly to the console using `ai.functions.out`.
- **Error Handling:** 
    - Throws `FileNotFoundError` if the provided `filename` does not exist on the filesystem during the `load()` call.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `json`, `pathlib`.
- **Internal:**
    - [ai.chat.chat.ChatRoles](/AgentDocs/ai/chat/chat.md)
    - [ai.color.Color](/AgentDocs/ai/color.md)
    - [ai.functions](/AgentDocs/ai/functions.md)