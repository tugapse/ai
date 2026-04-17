

## 1. Architectural Role  
Manages chat history persistence by loading/saving session data, preventing message duplication, and resuming sessions.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `HistoryManager` | Class | Orchestrates chat history lifecycle via file I/O and duplicate detection |  
| `__init__` | Method | Initializes session context with Chat instance and file paths |  
| `initialize_session` | Method | Maps session paths and triggers history loading |  
| `load_history` | Method | Loads persisted messages while avoiding duplicates |  
| `add_message` | Method | Appends new messages to session, skipping duplicates |  
| `save` | Method | Persists chat messages to disk with directory creation |  
| `get_log_path` | Method | Returns path to thinking log file |  

## 3. Execution Logic & Flow  
- **Initialization**: Sets `chat`, `chat_filepath`, `thinking_log_filepath`, and `workspace_path` via constructor |  
- **Data Path**: Session paths  load history (deserialize JSON  filter duplicates  append to chat)  add messages (validate content  append if unique)  save (serialize JSON to file) |  
- **Conditional Branching**:  
  - If `chat_filepath`  skip history load  
  - If message content exists in chat  skip duplication  
  - If file I/O fails  log error instead of crashing  

## 4. Resource Dependencies  
- **Standard Libraries**: `os`, `json`, `typing`  
- **Internal Modules**: `core.chat`, `core.llms.base_llm`, `functions`  
- **External Packages**: None  

## 5. Configuration & Environment  
- **Hardcoded Constants**: None  
- **Environment Lookups**: None