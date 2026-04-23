## 1. Architectural Role
The `FileContentHandler` is responsible for detecting, extracting, and persisting file content embedded within `<file>` tags from an LLM's token stream while suppressing that content from the standard console output.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `FileContentHandler` | Class | Manages the state and logic for parsing file tags and writing content to disk. |
| `__init__` | Method | Initializes state buffers, regex patterns, and ensures the `output_base_dir` exists. |
| `process_token` | Method | Analyzes incoming token strings to toggle file accumulation mode and trigger file saving. |
| `save_file` | Method | Validates file metadata and writes the accumulated buffer to the filesystem. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Sets `printed_create_file` to `False`.
    2. Initializes `_is_active` (boolean), `_buffer` (content), and `_token_accumulation_buffer` (fragment handler).
    3. If `output_base_dir` is provided, it creates the directory via `os.makedirs`.
- **Data Path**: `raw_token_string` $\rightarrow$ `_token_accumulation_buffer` $\rightarrow$ `CONTROL_CHARS_PATTERN` cleaning $\rightarrow$ Tag Detection $\rightarrow$ `_buffer` (if active) $\rightarrow$ `save_file` $\rightarrow$ Disk.
- **Conditional Branching**:
    1. **Closing Tag Check**: If `FILE_END_PATTERN` is found and `_is_active` is `True`, it resolves the final filename (via `MIME_TYPE_TO_EXT` or extension attributes), calls `save_file`, and resets state.
    2. **Opening Tag Check**: If `FILE_START_PATTERN` is found and `_is_active` is `False`, it extracts metadata (`name`, `type`, `ext`), sets `_is_active` to `True`, and suppresses subsequent tokens.
    3. **Active State**: If `_is_active` is `True` and no tags are matched, tokens are appended to `_buffer` and a "Creating file" notification is printed once.
    4. **Inactive State**: If `_is_active` is `False`, tokens are passed through as `token_content_for_display`.

## 4. Resource Dependencies
- **Standard Libraries**: `re`, `os`
- **Internal Modules**: `functions` (as `func`), `extras.thinking_log_manager.ThinkingLogManager`

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `FILE_START_PATTERN`: Regex for `<file name="..." ...>`.
    - `FILE_END_PATTERN`: Regex for `</file>`.
    - `CONTROL_CHARS_PATTERN`: Regex for non-printable characters.
    - `MIME_TYPE_TO_EXT`: Dictionary mapping MIME types (e.g., `text/html`) to extensions (e.g., `.html`).
    - `end_file_string`: `"[FILE_END]"` (defined but not utilized in logic).