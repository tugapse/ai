## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| SessionError | ai/modules/server/exceptions |

This component defines a hierarchy of custom exception classes specifically designed for robust session management within the server environment. It encapsulates various failure modes related to session lifecycle, such as the absence of a session file, invalid file paths, or generic I/O errors during session handling.

These exceptions serve as the primary error contract for any module interacting with session persistence. They allow calling services to catch specific, domain-relevant errors—like `SessionNotFoundError`—rather than relying on generic Python exceptions, thus providing cleaner, more predictable control flow across the application architecture.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| SessionError | Class | Base exception for session handling. |
| SessionNotFoundError | Class | Raised when a session file does not exist. |
| InvalidPathError | Class | Raised when a provided path would escape the root session directory. |
| SessionAccessError | Class | Raised on generic IO errors while handling sessions. |
| ModelError | Class | Base exception for model selection on the server. |
| ModelNotFoundError | Class | Raised when a requested model has no config file on the server. |
| ModelLoadError | Class | Raised when a model config exists but the engine failed to load it. |
| ModelBusyError | Class | Raised when a model swap is refused because the loaded model is still in use. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The component defines classes inheriting from Python's base `Exception`. These classes serve purely as named error types, inheriting specific behaviors and relationships to categorize the nature of the failure (e.g., session-related vs. model-related).

- **Side Effects:** None.

- **Error Handling:** Defines the structure for propagating specific, predictable errors related to session and model operations.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** None.

- **Internal:** None.