## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | ConsoleChatReader |
| Source file | console.py |

The **ConsoleChatReader** component is a specialized utility designed to ingest and visualize chat history within a terminal environment. It serves as a bridge between serialized JSON chat logs and the user's console, providing a human-readable representation of past interactions by applying semantic color coding and token-level formatting.

**Functional Mission**
The primary responsibility of **ConsoleChatReader** is to parse JSON-formatted chat histories and output them to the standard output with enhanced visual clarity. It solves the problem of raw JSON data being unreadable for humans by transforming structured message objects into formatted, colorized text blocks that distinguish between different participants (User vs. Assistant) and highlight specific syntax elements like code blocks.

**System Context & Integration**
This component acts as a post-processing visualization tool. It consumes data structures defined by [ChatRoles](/docs/ai/chat/chat.md) and utilizes [Color](/docs/ai/color.md) constants to apply terminal styling. During the execution flow, it relies on [func.out](/docs/ai/functions.md) to handle the actual printing to the console. It is strategically positioned as an "extra" utility, likely used during debugging, session recovery, or CLI-based history inspection.

- **INTERNAL REFERENCES**: [ChatRoles](/docs/ai/chat/chat.md), [Color](/docs/ai/color.md), [func.out](/docs/ai/functions.md).

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `Color.BLUE` (via `_print_chat`)  Applied to User messages.
- `Color.YELLOW` (via `_print_chat`)  Applied to Assistant messages.
- `Color.RESET` (via `_print_chat`)  Used to clear color formatting.
- `'printing_block'` (via `ConsoleTokenFormatter.__init__`)  State key for tracking code block toggling.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ConsoleChatReader` | Class | Orchestrates the loading of JSON files and the high-level printing of chat messages. |
| `ConsoleChatReader.load` | Method | Reads the file from disk, parses JSON, and iterates through messages for printing. |
| `ConsoleChatReader._print_chat` | Method | Determines role-based colors and triggers the token-level colorization process. |
| `ConsoleChatReader.color_text` | Method | Splits text into tokens and passes them to the formatter. |
| `ConsoleTokenFormatter` | Class | Maintains stateful formatting logic for specific text patterns (e.g., code blocks). |
| `ConsoleTokenFormatter.process_token` | Method | Applies color toggles based on the presence of backticks (`` ` ``). |
| `ConsoleTokenFormatter.clear_process_token` | Method | Resets the internal `printing_block` state. |

## 4. Execution Logic & Flow
- **Initialization**: 
    - `ConsoleChatReader` is instantiated with a `filename`, initializing a `Path` object and a `ConsoleTokenFormatter` instance.
    - `ConsoleTokenFormatter` initializes its `token_states` dictionary with `printing_block` set to `False`.
- **Data Path**: 
    - **Input**: A JSON file containing a list of chat message objects.
    - **Processing**: 
        1. `load()` reads the file and iterates through the list.
        2. `_print_chat()` filters out `ChatRoles.SYSTEM` messages.
        3. `color_text()` splits the content by spaces.
        4. `process_token()` checks for `` ` `` to toggle `Color.YELLOW` or `Color.RESET`.
    - **Output**: Formatted, colorized strings printed via `func.out`.
- **Conditional Branching**:
    - **Role Check**: If `role == ChatRoles.SYSTEM`, the message is skipped.
    - **Role Coloration**: If `role == ChatRoles.USER`, color is `BLUE`; otherwise, it is `YELLOW`.
    - **Token State Toggle**: In `process_token`, if `` ` `` is detected, the code checks `printing_block`. If `False`, it enables yellow coloring and sets state to `True`. If `True`, it resets color and sets state to `False`.

## 5. Resource Dependencies
- **Standard Libraries**: `json`, `pathlib.Path`
- **Internal Modules**: 
    - [ChatRoles](/docs/ai/chat/chat.md)
    - [Color](/docs/ai/color.md)
    - [func.out](/docs/ai/functions.md)
- **External Packages**: None identified.