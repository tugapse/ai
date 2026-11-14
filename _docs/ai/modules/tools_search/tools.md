## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| tools_search/tools | /ai/modules/tools_search/tools.md |

This component provides a set of utility tools (`smart_search` and `grep_file`) designed to allow the AI agent to interactively search the project's codebase. Its primary responsibility is to locate definitions, usages, or specific content patterns across files either globally (`smart_search`) or within a single, targeted file (`grep_file`). These tools bridge the gap between the AI's reasoning capabilities and the physical structure of the source code repository.

Architecturally, these functions serve as specialized search services within the tooling layer of the application. They operate by executing system commands (`grep`) or utilizing Python's `os` and `re` modules to perform complex pattern matching. They integrate with path resolution utilities like `ai.tools.base.resolve_path` to ensure all operations are performed relative to the project root, fitting into the broader execution workflow that relies on core functionalities from [ai.tools.base](/ai/tools/base.md).

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| smart_search | Function | Searches the entire project or a specified folder for a pattern in filenames or content. Supports pagination. |
| grep_file | Function | Finds lines matching a pattern within a single specified file, including context lines. |

## 3. Implementation Details & Side Effects
- **Core Logic:** `smart_search` first compiles a regex from the pattern and then performs two searches: one using `os.walk` to find matching filenames based on regex or literal text, and a second, more comprehensive search using `subprocess.run` with `grep` across the specified path. `grep_file` reads the target file into memory and uses `re.search` to find all matches, then constructs an output string showing surrounding lines based on the context parameter.
- **Side Effects:** Both functions interact heavily with the filesystem by traversing directories (`os.walk`) and executing external shell commands (`subprocess.run` with `grep`).
- **Error Handling:** Both functions utilize broad `try...except Exception` blocks to catch issues during path resolution, file operations, or regex compilation, returning a standardized `{"status": "FAILED", "error": "..."}` dictionary upon failure.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `re`, `subprocess`, `typing`, `math`.
- **Internal:** [ai.tools.base](/ai/tools/base.md).