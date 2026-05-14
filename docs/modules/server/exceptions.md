## 1. Architectural Role
Provides a specialized exception hierarchy for categorizing and propagating errors related to session lifecycle and filesystem integrity within the server module.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `SessionError` | Class | Acts as the base exception class for all session-related error handling. |
| `SessionNotFoundError` | Class | Signals the absence of a requested session file during lookup operations. |
| `InvalidPathError` | Class | Signals a security or logic violation where a path attempts to escape the designated session root. |
| `SessionAccessError` | Class | Signals low-level I/O failures encountered during session file manipulation. |

## 3. Execution Logic & Flow
- **Initialization**: No internal state is initialized; classes are defined as static exception types inheriting from `Exception`.
- **Data Path**: Direct exports only; no internal logic flow.
- **Conditional Branching**: Direct exports only; no internal logic flow.

## 4. Resource Dependencies
- **Standard Libraries**: `Exception` (built-in)

## 5. Configuration & Environment
- **Hardcoded Constants**: None
- **Environment Lookups**: None