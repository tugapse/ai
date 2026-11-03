## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **exceptions** | [src/ai/modules/server/exceptions.py](/AgentDocs/ai/modules/server/exceptions.md) |

This component defines a specialized hierarchy of exception classes used for managing session-related errors within the server module. It provides a structured way to differentiate between missing session files, security violations regarding path traversal, and general I/O failures.

By centralizing these error types, the component ensures consistent error reporting across the server's service layer, specifically aiding components like [session_manager](/AgentDocs/ai/modules/server/services/session_manager.md) and [sessions router](/AgentDocs/ai/modules/server/routers/sessions.md) in communicating failure states to the API consumers.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `SessionError` | Class | The base exception class for all session-related errors in the server module. |
| `SessionNotFoundError` | Class | Raised when a requested session file cannot be located on the filesystem. |
| `InvalidPathError` | Class | Raised when a provided file path attempts to escape the designated root session directory (path traversal protection). |
| `SessionAccessError` | Class | Raised when generic Input/Output (IO) errors occur during session manipulation. |

## 3. Implementation Details & Side Effects
Structural definitions only; no complex logic or side effects.