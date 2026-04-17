## 1. Architectural Role
The `HistoryManager` class provides a persistence layer for chat sessions, managing the synchronization between in-memory message lists and on-disk JSON storage while preventing message duplication.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `HistoryManager` | Class | Orchestrates the loading, appending, and saving of chat history. |
| `initialize_session` | Method | Configures session file paths and triggers the `load_history` process. |
| `load_history` | Method | Reads JSON history from disk and merges unique messages into the `Chat` object. |
| `add_message` | Method | Validates, formats, and appends a new message to the session, preventing immediate duplicates. |
| `save` | Method | Serializes the current `Chat` message list to a JSON file on disk. |
| `get_log_path` | Method | Returns the configured path for the thinking log. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. `__init__` is called with a `Chat` instance.
    2. State is initialized with `chat_filepath`, `thinking_log_filepath`, and `workspace_path` set to `None`.
- **Data Path**:
    - **Load**: `session_paths` (Dict) $\rightarrow$ `initialize_session` $\rightarrow$ `load_history` $\rightarrow$ `json.load` $\rightarrow$ Filter by `existing_contents` $\rightarrow$ `self.chat.messages` (List).
    - **Append**: `role`/`content` (Strings) $\rightarrow$ `add_message` $\rightarrow$ `BaseModel.create_message` $\rightarrow$ Duplicate Check $\rightarrow$ `self.chat.messages` (List).
    - **Save**: `self.chat.messages` (List) $\rightarrow$ `save` $\rightarrow$ `os.makedirs` $\rightarrow$ `json.dump` $\rightarrow$ Disk.
- **Conditional Branching**:
    - **Load Guard**: If `chat_filepath` is missing or file does not exist, loading is aborted.
    - **Deduplication (Load)**: Messages are only appended if their `content` is not already present in the `existing_contents` set.
    - **Deduplication (Add)**: A message is rejected if it is identical to the most recent message in `self.chat.messages`.
    - **Input Validation**: `add_message` returns immediately if `content` is empty or whitespace.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `json`
- **Internal Modules**: `core.chat.Chat`, `core.chat.ChatRoles`, `core.llms.base_llm.BaseModel`, `functions` (aliased as `func`)

## 5. Configuration & Environment
- **Hardcoded Constants**: None.
- **Environment Lookups**: None. (Relies on `session_paths` dictionary passed during `initialize_session`).