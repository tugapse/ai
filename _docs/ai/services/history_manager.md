## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| HistoryManager | /ai/services/history_manager.md |

This component is responsible for the entire lifecycle management of chat history, ensuring that conversations are persisted, loaded correctly across sessions, and maintained without duplication. Its primary function is to act as the intermediary between the live `Chat` session in memory and the persistent storage on disk.

The `HistoryManager` operates as a core service layer within the application architecture. It manages state transitions, allowing for both loading history upon session initialization (via `initialize_session`) and dynamically switching memory contexts (`switch_active_session`). It relies on the `Chat` object to hold the active message sequence and interacts with file system operations to manage persistence via methods like `save`.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `HistoryManager` | Class | Manages chat history and persistence. |
| `initialize_session` | Method | Sets session context and triggers history loading on boot using provided paths. |
| `switch_active_session` | Method | Hot-swaps the active memory file, clearing the current context and loading a new history. |
| `load_history` | Method | Loads conversation from disk, skipping messages already present in the current session to prevent duplication. |
| `add_message` | Method | Wraps content and adds it to the active session, preventing empty messages or immediate duplicates. |
| `save` | Method | Persists the current state of the chat memory to the configured disk path. |
| `get_log_path` | Method | Retrieves the configured or default path for the thinking log. |

## 3. Implementation Details & Side Effects
- **Core Logic:** History loading prioritizes integrity by comparing content hashes (via dictionary lookup of message content) between the saved file and the current in-memory messages before appending. Message addition enforces idempotency by checking for empty content and matching the immediately preceding message content. State is managed by setting and updating internal file path pointers.

- **Side Effects:** Reads from and writes to the filesystem (`os.path.exists`, `open`, `json.load`, `json.dump`) when loading or saving history. It mutates the internal state of the injected `Chat` object (`self.chat.messages.clear()`, `self.chat.messages.append()`).

- **Error Handling:** Catches generic `Exception` during history loading (`load_history`) and logging the failure as a `WARN`. It catches generic `Exception` during saving (`save`) and logs the failure as an `ERROR`.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `json`, `typing`
- **Internal:** [Chat](/ai/chat/chat.md), [BaseModel](/ai/core/llms/base_llm.md), [ai.functions](/ai/functions.md)