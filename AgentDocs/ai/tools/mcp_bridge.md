## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **MCPBridge** | [src/ai/tools/mcp_bridge.py](/src/ai/tools/mcp_bridge.py) |

The `MCPBridge` class serves as a dynamic integration layer between the JARVIS agent and external Model Context Protocol (MCP) servers. It solves the problem of heterogeneous tool interfaces by abstracting multiple specialized MCP servers into a single, unified "Gateway" tool per server. This allows the agent to interact with diverse backend systems through a standardized, flattened interface without needing to understand the underlying JSON-RPC complexities of each individual server.

In the broader system architecture, this component acts as a tool provider within the `ai.tools` ecosystem. It manages the lifecycle of asynchronous connections to external processes via standard I/O, handles real-time schema discovery, and performs automatic type-casting of agent-provided arguments to ensure compatibility with the target MCP server's requirements.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `MCPBridge(tool_registry)` | Class | Initializes the bridge with a provided registry for tool injection. Starts a background `asyncio` event loop in a dedicated thread. |
| `load_from_config(filepath: str)` | Method | Parses a JSON configuration file to identify, enable, and connect to multiple MCP servers defined in the `mcpServers` key. |
| `connect_server(server_name: str, command: str, args: List[str], description: str)` | Method | Synchronously triggers the asynchronous connection process for a specific MCP server. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **Connection Management:** Uses `AsyncExitStack` to manage the lifecycles of `stdio_client` transports and `ClientSession` objects.
    - **Gateway Abstraction:** For every connected server, it generates a `gateway_wrapper` function. This wrapper uses a "flattened" signature, teaching the LLM to pass arguments via `action` (`list_tools` or `execute`) and `command` parameters.
    - **Type Casting:** During tool execution, the bridge performs "Universal Type Casting" by inspecting the MCP server's `inputSchema`. It converts raw input (often strings from the LLM) into `integer`, `number`, `boolean`, `array`, or `object` types as required by the schema.
    - **Thread Bridging:** Uses `asyncio.run_coroutine_threadsafe` to bridge synchronous calls from the main application thread to the dedicated background `asyncio` loop.
- **Side Effects:** 
    - **Process Spawning:** Executes external commands/processes defined in the configuration.
    - **I/O Streams:** Establishes and maintains bidirectional communication via standard I/O (stdin/stdout) with child processes.
    - **Registry Mutation:** Automatically registers new tools into the provided `tool_registry`.
- **Error Handling:** 
    - Catches configuration loading errors and connection failures, logging them via `ai.functions`.
    - Returns structured error dictionaries (`{"status": "FAILED", "error": "..."}`) to the agent when tool execution fails or type mismatches occur, preventing the bridge from crashing the main loop.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No specific environment variables are required, but the component relies on a JSON configuration file passed to `load_from_config`. The config must follow the structure: `{"mcpServers": {"name": {"command": "...", "args": [...], "enabled": true, "description": "..."}}}`.

**Module Dependencies:**
- **Standard/External:** `asyncio`, `threading`, `json`, `os`, `contextlib`, `typing`, `mcp` (Model Context Protocol SDK).
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)