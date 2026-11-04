## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **agent_tools.py** | [src/ai/tools/agent_tools.py](/src/ai/tools/agent_tools.py) |

This component provides a suite of high-level tools designed to be consumed by autonomous AI agents. It bridges the gap between LLM reasoning and system-level execution by providing controlled interfaces for filesystem manipulation, shell command execution, pattern searching, and network communication.

The module acts as a capability layer within the broader agent architecture. It implements strict security boundaries via path resolution and sanitization, ensuring that agents can only interact with files within the project root. This component is essential for agents that require "hands-on" access to the environment to perform coding, debugging, or system administration tasks.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `tool(func)` | Decorator | Marks a function as an agent tool, adding a `_is_tool` attribute for automatic discovery. |
| `execute_command(**kwargs)` | Function | Executes a shell command with support for `@ROOT` path substitution and execution timeouts. |
| `read_dir(**kwargs)` | Function | Recursively explores directories and returns a structured map of files and folders. |
| `read_file(**kwargs)` | Function | Retrieves the UTF-8 text content of one or more specified files. |
| `write_file(**kwargs)` | Function | Creates or overwrites files, automatically handling directory creation. |
| `smart_search(**kwargs)` | Function | Performs keyword or regex searches across filenames and file contents with pagination. |
| `patch_file(**kwargs)` | Function | Performs surgical text replacement within a file using a search-and-replace block mechanism. |
| `tcp_client_tool(**kwargs)` | Function | Establishes a TCP connection to a host/port to send data and receive a response. |
| `AVAILABLE_TOOLS` | Dictionary | A registry mapping tool names to their corresponding function implementations. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **Path Security:** Uses `_resolve_path` to enforce a sandbox. It converts `@ROOT` tokens to absolute paths and raises a `PermissionError` if any operation attempts to escape the `PROJECT_ROOT`.
    - **Path Sanitization:** Uses `_sanitize_output_path` to convert absolute system paths back into `@ROOT` format, preventing the leakage of the host's full filesystem structure to the LLM.
    - **Search Algorithm:** `smart_search` combines `os.walk` for filename matching with a subprocess-based `grep` execution for high-performance content searching. It includes built-in pagination to manage LLM context window limits.
    - **Patching:** `patch_file` utilizes `difflib` to generate unified diffs, allowing the agent to verify exactly what changes were made.
- **Side Effects:**
    - **Filesystem:** Reads, writes, creates directories, and deletes (via shell commands) files on the host system.
    - **Network:** Opens TCP sockets to external hosts via `tcp_client_tool`.
    - **Subprocess:** Spawns shell processes for command execution and searching.
- **Error Handling:** 
    - Most tools return a dictionary containing `{"status": "FAILED", "error": "..."}` instead of raising unhandled exceptions, allowing the agent to receive the error as text and attempt recovery.
    - `_resolve_path` raises a `PermissionError` for security violations.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No specific environment variables are required, though the tool's behavior is relative to the current working directory (`os.getcwd()`) at the time of initialization.

**Module Dependencies:**
- **Standard/External:** `os`, `subprocess`, `json`, `difflib`, `typing`, `socket`, `re`, `math`.
- **Internal:** No internal module imports are present in this file.