## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | MCPBridge |
| Source file | mcp_bridge.py |

The **MCPBridge** serves as a dynamic integration layer between the Model Context Protocol (MCP) ecosystem and the JARVIS intelligence core. Its primary purpose is to abstract complex, multi-tool MCP server connections into a single, unified "Gateway" tool for each server. This prevents tool-registry bloat by presenting a flattened interface to the LLM while maintaining the ability to execute granular, specific commands via a controlled dispatch mechanism.

**Functional Mission**
The mission of **MCPBridge** is to provide a scalable, asynchronous bridge that translates high-level LLM intent into low-level JSON-RPC tool calls. It solves the problem of "tool explosion" by wrapping an entire suite of remote MCP tools into a single registered function per server, utilizing a specialized docstring to teach the LLM how to interact with the gateway via `list_tools` and `execute` actions.

**System Context & Integration**
This component acts as a middleware between external MCP servers and the [Tool Registry](/docs/ai/tools/tool_registry.md). Upon initialization, it spawns a background event loop to manage asynchronous lifecycles of multiple server connections. When the LLM decides to use an MCP-backed capability, it calls the injected gateway function, which then routes the request through the `MCPBridge` to the appropriate `ClientSession`. Data flows from the LLM (as keyword arguments) $\rightarrow$ `gateway_wrapper` $\rightarrow$ `_execute_mcp_tool` (with type casting) $\rightarrow$ MCP Server $\rightarrow$ back through the bridge to the LLM.

- **INTERNAL REFERENCES**: 
    - [Tool Registry](/docs/ai/tools/tool_registry.md)
    - [Functions](/docs/ai/functions.md)

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `MCPBridge` | Class | Manages the lifecycle, connection, and tool injection for multiple MCP servers. |
| `load_from_config` | Method | Parses a JSON configuration file to initialize connections for enabled MCP servers. |
| `connect_server` | Method | Triggers the asynchronous connection process for a specific server. |
| `_inject_gateway` | Method | Generates a single, flattened tool function with a specialized docstring for the LLM. |
| `_format_tools_list` | Method | Converts MCP tool schemas into human-readable text for LLM context. |
| `_execute_mcp_tool` | Method | Performs type-casting on raw LLM arguments and executes the remote tool call. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. Accepts a `tool_registry` instance.
    2. Initializes an `AsyncExitStack` for resource management.
    3. Spawns a dedicated background `threading.Thread` running a permanent `asyncio` event loop to handle non-blocking I/O.
- **Data Path**:
    1. **Input**: LLM provides `action`, `command`, and arbitrary `**kwargs`.
    2. **Processing**: 
        - If `action == "list_tools"`, returns a formatted string of available tools.
        - If `action == "execute"`, extracts `command`, retrieves the tool's `inputSchema`, and performs **Universal Type Casting** (converting strings to `int`, `float`, `bool`, `list`, or `dict` based on the schema).
    3. **Output**: Returns a dictionary containing `status` ("SUCCESS" or "FAILED") and either the `output` text or an `error` message.
- **Conditional Branching**:
    - **Config Check**: Skips servers marked as `enabled: false` in the config.
    - **Action Routing**: Branches between `list_tools` and `execute` logic.
    - **Validation**: Checks if the requested `command` exists in the `server_schemas` before attempting execution.
    - **Error Handling**: Catches connection failures, type mismatch errors during casting, and JSON-RPC errors returned by the MCP server.

## 5. Resource Dependencies
- **Standard Libraries**: `asyncio`, `threading`, `json`, `os`, `contextlib`
- **Internal Modules**: 
    - [Functions](/docs/ai/functions.md)
- **External Packages**: `mcp` (Model Context Protocol SDK)