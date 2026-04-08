## 1. Architectural Role
Manages the pipeline of token processing handlers, focusing specifically on the Thinking/Animation state.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `HandlerManager` | Class | Manages the pipeline of token processing handlers, focusing specifically on the Thinking/Animation state. |
| `process_token_chain` | Method | Processes a token to determine if it's a 'thought' or 'actual output'. Returns a tuple indicating whether to display to the user, the final content, and any file content saved. |

## 3. Execution Logic & Flow
- **Initialization**: The `HandlerManager` class is initialized with a `ThinkingLogManager` instance and various configuration parameters. It creates an instance of `ThinkingAnimationHandler` with these parameters.
- **Data Path**: The `process_token_chain` method takes an `initial_token` as input. It passes this token to the `ThinkingAnimationHandler`'s `process_token_and_thinking_state` method. Depending on whether the token is a thought or actual output, it returns a tuple indicating whether to display to the user, the final content, and `None`.
- **Conditional Branching**: The key decision point is whether the token is a thought or actual output. If it's a thought, the method returns `False`, an empty string, and `None`. If it's actual output, it returns `True`, the content from the handler, and `None`.

## 4. Resource Dependencies
- **Standard Libraries**: None
- **Internal Modules**: `extras.think_parser`, `extras.thinking_log_manager`
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: `thinking_mode`, `enable_thinking_display`, `show_thinking_animation`
- **Environment Lookups**: None