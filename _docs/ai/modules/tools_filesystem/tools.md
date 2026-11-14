## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| tools_filesystem | /ai/modules/tools_filesystem/tools.md |

This component provides a suite of high-level filesystem interaction tools designed to allow an AI agent to reliably read, write, modify, and explore the project structure. It abstracts low-level OS operations into user-friendly, declarative functions like `read_dir`, `read_file`, and `patch_file`, enabling robust interaction with project assets.

Architecturally, this module serves as a critical service layer within the agent framework. It sits between the high-level reasoning engine and the actual operating system, providing necessary I/O capabilities. It heavily relies on path resolution utilities from [ai.tools.base](/ai/tools/base.md) to ensure all operations are performed relative to the project root, maintaining consistency across the application.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| read_dir | Function | Lists files and folders within specified directories, optionally limiting the recursion depth. Returns a structured dictionary of contents. |
| read_file | Function | Reads the entire content of one or more specified files. Returns a dictionary mapping file paths to their contents. |
| write_file | Function | Creates a new file or overwrites an existing one entirely. Automatically creates necessary parent directories. |
| patch_file | Function | Replaces a specific, exact block of text within an existing file while preserving all other content. Returns a summary of the change via unified diff. |
| read_files | Function | Convenience wrapper that calls `read_file` to read multiple files in a single invocation. |
| delete_file | Function | Deletes a single specified file or an empty directory. Includes checks to prevent deletion of the project root. |

## 3. Implementation Details & Side Effects
- **Core Logic:** Functions primarily use `os.listdir` and `os.path` utilities for directory traversal and file system manipulation. `read_dir` employs a recursive helper function (`get_structure`) to manage depth limits. `patch_file` uses `difflib.unified_diff` to generate a summary of the text replacement.
- **Side Effects:** This component has extensive filesystem side effects, including reading from, writing to, creating directories, and deleting files/directories.
- **Error Handling:** All primary tools wrap their logic in `try...except` blocks to catch operational errors (e.g., `FileNotFoundError`, permission issues). They return standardized status dictionaries (`{"status": "SUCCESS", ...}` or `{"status": "FAILED", "error": ...}`) to communicate failure modes back to the caller.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `difflib`, `typing`
- **Internal:** [ai.tools.base](/ai/tools/base.md)