## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **MCPBridge** | [src/ai/tools/mcp_bridge.py](/src/ai/tools/mcp_bridge.py) |

The `MCPBridge` component facilitates communication between the JARVIS agent and external Model Context Protocol (MCP) servers. It manages the lifecycle of asynchronous connections to multiple backend systems via standard I/O streams, effectively acting as a translation layer between the agent's tool-calling interface and the MCP protocol.

Instead of exposing every individual tool from an MCP server to the agent, this component implements a "Gateway" pattern. It wraps all tools from a single server into one unified, flattened function. This reduces the cognitive load on the LLM by providing a single interface per server, where the agent specifies an `action` (either `list_tools` or `execute`) to interact with the underlying capabilities.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `MCPBridge(tool_registry)` | Class | Initializes the bridge with a reference to a [tool_registry](/AgentDocs/ai/tools/tool_registry.md) to register the generated gateway tools. |
| `load_from_config(filepath: str)` | Method | Reads a JSON configuration file containing MCP server definitions (command, args, enabled status) and initiates connections. |
| `connect_server(server_name: str, command: str, args: List[str], description: str)` | Method | Synchronously triggers the asynchronous connection process for a specific MCP server. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **Lifecycle Management:** Uses an `AsyncExitStack` within a dedicated background `asyncio` event loop running in a daemon thread to manage long-lived `stdio_client` and `ClientSession` contexts.
    - **Gateway Injection:** For every connected server, it generates a `gateway_wrapper` function. This function uses a custom docstring to instruct the agent on how to use the `action` and `command` parameters.
    - **Type Casting:** When executing a tool, the bridge performs "Universal Type Casting" by inspecting the MCP server's `inputSchema`. It converts incoming string or loosely typed arguments from the agent into the specific types (integer, number, boolean, array, object) required by the MCP server.
    - **Tool Discovery:** Provides a `list_tools` action that parses the MCP server's tool definitions into a human-readable string format optimized for LLM context windows.
- **Side Effects:** 
    - **Process Management:** Spawns and manages external child processes via `stdio_client`.
    - **Network/IO:** Communicates via standard input/output streams with external processes.
    - **Concurrency:** Starts a background thread to run a persistent `asyncio` event loop.
- **Error Handling:** 
    - Captures connection failures and configuration errors, logging them via [func.log](/AgentDocs/ai/functions.md).
    - Returns structured error dictionaries (`{"status": "FAILED", "error": "..."}`) to the agent if tool execution fails or if type mismatches occur during parameter casting.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- Requires a JSON configuration file (path provided to `load_from_config`) containing an `mcpServers` object with `command`, `args`, and optional `enabled` or `description` keys.

**Module Dependencies:**
- **Standard/External:** `asyncio`, `threading`, `json`, `os`, `contextlib`, `typing`, `mcp` (Model Context Protocol SDK).
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md) (Logging and utility functions).