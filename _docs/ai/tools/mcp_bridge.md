## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| MCPBridge | ai/tools/mcp_bridge |

This component is responsible for establishing and managing persistent, bidirectional connections to external Machine Control Protocol (MCP) servers. Its primary role is to abstract the complex, low-level interaction—which involves standard I/O streaming over processes—into a single, unified interface that the main AI agent (JARVIS) can consume. It acts as a sophisticated bridge, allowing JARVIS to interact with disparate backend systems using a consistent, standardized toolset.

Architecturally, `MCPBridge` functions as a critical service layer component. It manages the lifecycle of background asynchronous tasks for each connected server, handles connection timeouts, and registers a single, flattened "Gateway" tool into the global tool registry. This gateway allows the agent to delegate complex multi-step interactions (like listing tools, then executing them) through a single, simplified function call, effectively unifying many backend services under one umbrella.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| MCPBridge | Class | Manages connections, tool registration, and lifecycle for multiple MCP servers. |
| load_from_config | Method | Loads server connection details from a JSON file and initiates connections for all defined servers. |
| connect_server | Method | Initiates the connection process for a single, specified MCP server. |
| close | Method | Gracefully shuts down all active MCP server connections, terminates background tasks, and unregisters all gateway tools. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The bridge operates by spawning a dedicated, persistent background thread running an `asyncio` event loop for each server connection. Connections are established using `stdio_client` to manage input/output streams. Upon successful connection, it fetches all available tools from the server and wraps them into a single `gateway_wrapper`. This wrapper implements a state machine logic: the agent first calls `list_tools` to discover capabilities, and then calls `execute` with a specific `command` and parameters. Type casting occurs during execution to match the server's expected schema.

- **Side Effects:** The code extensively interacts with the filesystem (reading configuration, writing per-server error logs), spawns external processes (via `stdio_client`), and manages asynchronous background tasks (`asyncio.Task`, `threading.Thread`).

- **Error Handling:** It uses `asyncio.wait_for` with defined timeouts (`CONNECT_TIMEOUT`, `CALL_TIMEOUT`) to prevent indefinite blocking. Errors during startup cause the connection attempt to fail and log to a specific file. During execution, it catches timeouts and general exceptions, returning structured failure dictionaries to the agent.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables are explicitly required for core operation, though the `env` parameter allows passing custom environment variables to the spawned server processes.

**Module Dependencies:**
- **Standard/External:** `asyncio`, `threading`, `json`, `os`, `contextlib`, `typing`.
- **Internal:** [ai.functions](/ai/functions.md), [ai.services.directory_manager](/ai/services/directory_manager.md).