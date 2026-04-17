## 1. Architectural Role
Acts as the package initializer for the `core` module, exposing a curated public API by promoting key classes and types from internal submodules to the package level.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `Chat` | Class | Core chat session management. |
| `ChatRoles` | Class/Enum | Definition of participant roles within a chat. |
| `ChatCommandInterceptor` | Class | Logic for intercepting and processing chat-based commands. |
| `Events` | Class | System-wide event definitions or dispatcher. |
| `AsyncExecutor` | Class | Asynchronous implementation of command execution. |
| `CommandExecutor` | Class | Base or synchronous implementation of command execution. |
| `ExecutorResult` | Class/Type | Standardized output format for executed commands. |
| `ContextFile` | Class | Management of files providing context to the system. |

## 3. Execution Logic & Flow
Direct exports only; no internal logic flow.

## 4. Resource Dependencies
- **Standard Libraries**: None.
- **Internal Modules**: 
    - `core.chat`
    - `core.chat_command_interceptor`
    - `core.events`
    - `core.command_executor`
    - `core.context_file`
- **External Packages**: None.

## 5. Configuration & Environment
- **Hardcoded Constants**: None.
- **Environment Lookups**: None.