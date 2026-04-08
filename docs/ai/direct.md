## 1. Architectural Role
`direct.py` is responsible for handling user input, streaming responses from a language model, and managing the display and output of the response.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ask` | Function | Asks the language model a question and streams its response. |

## 3. Execution Logic & Flow
1. **Initialization**:
   - The function `ask` is called with parameters including the language model (`llm`), input message, and various options for output formatting and behavior.
   - A `ThinkingLogManager` is initialized to manage logging of the thinking process.
   - Configuration settings are retrieved from `ProgramConfig` for thinking mode, print mode, tokens per print, and whether to show the thinking animation.
   - A `HandlerManager` is created to handle the token processing and display logic.
   - An `OutputPrinter` is initialized to manage the printing of the language model's output.

2. **Data Path**:
   - The input message is converted to a list of message dictionaries if it is a string.
   - The language model is loaded and its model name is logged.
   - The language model's `chat` method is called with the message list, and the response is streamed token by token.
   - Each token is processed by the `HandlerManager`, which may update the thinking log and handle the display of the token.
   - The processed token is then printed by the `OutputPrinter` and written to a file if specified.
   - After all tokens are processed, the `OutputPrinter` flushes any remaining buffers.

3. **Conditional Branching**:
   - The