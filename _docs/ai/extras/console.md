## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| ConsoleChatReader | ai/extras/console.md |

This component is responsible for reading and rendering structured chat history stored in a JSON file directly to the console interface. Its primary responsibility is to parse message objects, distinguish between different speaker roles (User, Assistant), and apply visual formatting to enhance readability.

It serves as a presentation or utility layer within the application architecture. It consumes raw chat data and interfaces with formatting utilities like [ConsoleTokenFormatter](/ai/extras/console.md) to ensure that specialized content, such as code blocks, is displayed correctly in the terminal output.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| ConsoleChatReader | Class | Handles loading, iterating, and displaying chat history from a JSON file. |
| ConsoleTokenFormatter | Class | Manages the state and processing of individual tokens to apply specific formatting rules. |

## 3. Implementation Details & Side Effects
- **Core Logic:** `ConsoleChatReader` loads JSON data, iterating over messages and calling `_print_chat`. `_print_chat` determines the color and speaker label based on the message role, then passes the content to `color_text`. `color_text` splits the text by spaces and iterates over tokens, using `ConsoleTokenFormatter.process_token` to apply formatting rules, specifically toggling state when encountering '``'.
- **Side Effects:** Reads from the filesystem (reads the JSON file) and writes to standard output (`func.out`).
- **Error Handling:** Raises `FileNotFoundError` if the specified JSON file path does not exist during the `load` operation.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `json`, `pathlib`
- **Internal:** [ai.chat.chat](/ai/chat/chat.md), [ai.color](/ai/color.md), ai.functions