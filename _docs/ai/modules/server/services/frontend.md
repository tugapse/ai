## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| FrontendService | ai/modules/server/services/frontend.md |

This component is responsible for resolving which version of the frontend interface the server should serve. It implements a strict fallback mechanism to ensure the server always has a valid frontend asset available, prioritizing development overrides over cached or bundled versions. The primary responsibility is to determine the correct `Path` to serve and the metadata describing its source.

This service operates as a critical part of the server's request handling pipeline, sitting above the core API logic. It interfaces with the filesystem to check for local development builds, cached versions stored in a system directory, or fallback assets bundled within the package. It utilizes functions from [ai.functions](/ai/functions.md) and interacts with [ai.services.directory_manager](/ai/services/directory_manager.md) to manage paths and configurations.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| FrontendError | Class | Exception raised when a frontend archive or folder cannot be used. |
| cache_root | Function | Returns the absolute path to the system-wide frontend cache directory. |
| read_version | Function | Reads and parses the `version.json` from a specified frontend directory. |
| _safe_members | Function | Validates archive members to prevent path traversal attacks when extracting tarballs. |
| archive_version | Function | Extracts and validates the version information from a frontend archive (`.tar.gz`). |
| extract | Function | Extracts a tarball into the cache, reusing an existing version if present. Returns the target path and version info. |
| cached_versions | Function | Scans the cache root to list all available frontend versions, sorted by modification time (newest first). |
| prune | Function | Deletes older cached frontend versions, keeping only the specified number of recent versions. |
| _setting | Function | Safely retrieves a configuration value for a given `ProgramSetting`. |
| resolve | Function | The main entry point. Determines and returns the serving path and version metadata based on configuration precedence. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `resolve` function implements a five-step precedence check: 1) `SERVER_FRONTEND_DIR` (local development), 2) `SERVER_FRONTEND_VERSION` (pinned cache version), 3) Bundled `frontend.tar.gz`, 4) Legacy `frontend/` folder, and 5) API only. The `extract` function handles atomic extraction using temporary directories to prevent serving partially extracted assets. Version management relies on metadata stored in `version.json`.

- **Side Effects:** Heavy filesystem interaction. It reads and writes to the filesystem for configuration checks, cache creation/deletion (`prune`), extraction (`extract`), and directory traversal.

- **Error Handling:** `FrontendError` is raised for critical failures during archive parsing or extraction (e.g., unsafe paths, missing `index.html`). The `resolve` function includes fallback logic, such as warning messages when pinned versions are invalid or when the bundled version fails to extract, ensuring a non-None return path if possible.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `ProgramSetting.SERVER_FRONTEND_DIR` — Path to a local development frontend folder. Defaults to `None` if not set in configuration.
- `ProgramSetting.SERVER_FRONTEND_VERSION` — Specific version string to pin and serve from the cache. Defaults to `None` if not set in configuration.

**Module Dependencies:**
- **Standard/External:** `json`, `os`, `shutil`, `tarfile`, `tempfile`, `pathlib`
- **Internal:** [ai.functions](/ai/functions.md), [ai.config](/ai/config.md), [ai.services.directory_manager](/ai/services/directory_manager.md)