## 1. Architectural Role
Handles the detection and extraction of file content enclosed within `<file>...</file>` tags from an LLM's token stream, and saves the extracted file content to disk.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `FileContentHandler` | Class | Manages the detection and extraction of file content from an LLM's token stream, and saves the extracted file content to disk. |

## 3. Execution Logic & Flow
- **Initialization**: 
  - Initializes the `FileContentHandler` with optional `ThinkingLogManager` and `output_base_dir`.
  - Sets up regular expressions for detecting file start and end tags, and control characters.
  - Maps MIME types to file extensions.
  - Creates the `output_base_dir` if specified.
- **Data Path**:
  - Accumulates token strings in `_token_accumulation_buffer`.
  - Cleans the buffer of control characters.
  - Searches for file start and end tags.
  - If a file start tag is found, sets `_is_active` to `True` and starts accumulating content.
  - If a file end tag is found, processes the accumulated content, determines the file name and extension, saves the file, and resets the state.
  - If no tags are found, returns the token content for display.
- **Conditional Branching**:
  - Checks if the current state is inside a file content block (`_is_active`).
  - Determines if a file start or end tag is present in the buffer.
  - Handles the extraction and saving of file content.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `re`
- **Internal Modules**: `functions` (aliased as `func`)
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: 
  - `end_file_string`: "[FILE_END]"
  - `MIME_TYPE_TO_EXT`: Dictionary mapping MIME types to file extensions.
- **Environment Lookups**: None