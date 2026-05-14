## 1. Architectural Role
This module serves as the centralized exception hierarchy for the server subsystem, providing specialized error types to categorize failures related to session lifecycle and filesystem integrity. It establishes a domain-specific error taxonomy used by [modules/server/services/session_manager.md](modules/server/services/session_manager.md) to signal state violations, path traversal attempts, or IO failures, ensuring that the [modules/server/server_module.md](modules/server/server_module.md) can implement granular error handling and meaningful feedback to the client.

## 2. Environment & Configuration
**Environment Lookups:**
No environment lookups identified.

**Hardcoded Constants:**
No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `SessionError` | Class | Base exception class for all session-related error handling. |
| `SessionNotFoundError` | Class | Signifies the absence of a requested session resource on disk. |
| `InvalidPathError` | Class | Signals a security violation where a path attempts to escape the designated root directory. |
| `SessionAccessError` | Class | Represents generic Input/Output (IO) failures during session operations. |

## 4. Execution Logic & Flow
- **Initialization**: Direct inheritance from the Python built-in `Exception` class; no custom `__init__` logic implemented.
- **Data Path**: Direct exports only; no internal logic flow.
- **Conditional Branching**: Direct exports only; no internal logic flow.

## 5. Resource Dependencies
- **Standard Libraries**: `builtins.Exception`
- **Internal Modules**: 
    - None
- **External Packages**: None