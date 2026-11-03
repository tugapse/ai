## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **agent_tools.py** | [src/ai/tools/agent_tools.py](/src/ai/tools/agent_tools.py) |

This component provides a suite of high-level tools designed to be consumed by autonomous AI agents. It bridges the gap between LLM reasoning and physical system actions, allowing an agent to interact with the filesystem, execute shell commands, perform network operations, and search through codebases.

The module acts as a capability layer within the broader agent architecture. It includes security-conscious path resolution to ensure agents remain confined to the project root and provides structured, paginated responses to prevent context window overflow during large-scale operations like directory listing or codebase searching.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `tool(func)` | Decorator | Marks a function as an agent tool, attaching a `_is_tool` attribute for automatic discovery. |
| `execute_command(**kwargs)` | Function | Executes a shell command via `subprocess`. Supports `@ROOT` token substitution. |
| `read_dir(**kwargs)` | Function | Recursively explores directories and returns a structured mapping of files and folders. |
| `read_file(**kwargs)` | Function | Reads the UTF-8 text content of one or more specified files. |
| `write_file(**kwargs)` | Function | Creates or overwrites files, automatically generating necessary parent directories. |
| `smart_search(**kwargs)` | Function | Performs keyword or regex searches across filenames and file contents with pagination. |
| `patch_file(**kwargs)` | Function | Performs a surgical text replacement of a specific block within a file. |
| `tcp_client_tool(**kwargs)` | Function | Connects to a TCP server, sends data, and returns the received response. |
| `AVAILABLE_TOOLS` | Dictionary | A registry mapping tool names to their respective function implementations. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **Path Resolution:** Uses `_resolve_path` to convert `@ROOT` tokens into absolute paths and enforces a security boundary by checking if the target path starts with the `PROJECT_ROOT`.
    - **Path Sanitization:** Uses `_sanitize_output_path` to convert absolute system paths back into `@ROOT` format for LLM consumption.
    - **Search Algorithm:** `smart_search` combines `os.walk` for filename matching and a `grep`-based subprocess call for content matching, implementing pagination to manage token limits.
    - **Surgical Patching:** `patch_file` uses `difflib` to generate a unified diff of changes and requires exact string matching to prevent accidental corruption.
- **Side Effects:** 
    - **Filesystem:** Reads, writes, creates directories, and executes commands that can modify the local disk.
    - **Network:** `tcp_client_tool` initiates TCP connections to external hosts/ports.
    - **Process Execution:** `execute_command` spawns shell processes.
- **Error Handling:** 
    - Returns structured dictionaries with `"status": "FAILED"` and an `"error"` key instead of raising unhandled exceptions to the agent.
    - Throws `PermissionError` internally if a path resolution attempt escapes the project root.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No specific environment variables are required, though the module relies on the current working directory (`os.getcwd()`) to define `PROJECT_ROOT`.

**Module Dependencies:**
- **Standard/External:** `os`, `subprocess`, `json`, `difflib`, `typing`, `socket`, `re`, `math`.
- **Internal:** No internal module imports are present in this file.