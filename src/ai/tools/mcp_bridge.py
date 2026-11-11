import asyncio
import threading
import json
import os
from contextlib import AsyncExitStack
from typing import Dict, Any, List
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import ai.functions as func

class MCPBridge:
    """
    Connects to MCP servers and injects a single Gateway tool per server into JARVIS.

    This class manages the lifecycle of asynchronous connections to external
    MCP servers via standard I/O streams. It fetches the available tools from
    each server and wraps them into a unified 'Gateway' function that JARVIS
    can call, allowing JARVIS to interact with multiple backend systems through
    a single, standardized interface.
    """
    
    def __init__(self, tool_registry):
        """
        Initializes the MCPBridge.

        Args:
            tool_registry: The registry object used to register the gateway tools.
        """
        self.registry = tool_registry
        self.sessions: Dict[str, ClientSession] = {}
        
        # Stores the raw tool schemas for each server: { "powerpoint": { "add_slide": {...} } }
        self.server_schemas: Dict[str, Dict[str, Any]] = {}
        
        # safely manages the lifecycles of async connections in the background
        self.exit_stack = AsyncExitStack()
        
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._start_background_loop, daemon=True)
        self._thread.start()

    def _start_background_loop(self):
        """
        Starts the asyncio event loop in a dedicated background thread.
        """
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run_async_task(self, coro):
        """
        Runs an asynchronous coroutine safely from a synchronous context thread.

        Args:
            coro: The coroutine to execute.

        Returns:
            The result of the coroutine execution.
        """
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def load_from_config(self, filepath: str):
        """
        Loads server connection details from a JSON configuration file and initiates connections.

        Args:
            filepath: The path to the JSON configuration file containing MCP server definitions.
        """
        if not os.path.exists(filepath):
            func.log(f"[MCP] Config file not found: {filepath}", level="WARN")
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                config = json.load(f)
                
            servers = config.get("mcpServers", {})
            for server_name, details in servers.items():
                if not details.get("enabled", True):
                    func.log(f"[MCP] Skipping '{server_name}' (Disabled in config).", level="INFO")
                    continue
                    
                command = details.get("command")
                args = details.get("args", [])
                description = details.get("description", f"Gateway tool for {server_name} MCP server.")
                
                if not command:
                    continue
                    
                self.connect_server(server_name, command, args, description)
                
        except Exception as e:
            func.log(f"[MCP] Error loading config: {str(e)}", level="ERROR")

    def connect_server(self, server_name: str, command: str, args: List[str], description: str):
        """
        Initiates the connection process for a specified MCP server.

        Args:
            server_name: The unique name identifier for the server.
            command: The executable command for the server process.
            args: A list of command-line arguments for the server process.
            description: A human-readable description of the server's functionality.
        """
        func.log(f"[MCP] Connecting to {server_name}...", level="INFO")
        try:
            self._run_async_task(self._async_connect(server_name, command, args, description))
        except Exception as e:
            func.log(f"[MCP] Failed to connect to {server_name}: {e}", level="ERROR")

    async def _async_connect(self, server_name: str, command: str, args: List[str], description: str):
        """
        Asynchronously establishes the connection, fetches schemas, and registers the gateway.

        Args:
            server_name: The name of the server being connected to.
            command: The command to execute the server.
            args: Arguments for the server command.
            description: The description used for the gateway tool.
        """
        server_params = StdioServerParameters(command=command, args=args)
        
        # Safely enter and hold the context managers open using AsyncExitStack
        transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        read_stream, write_stream = transport
        
        session = await self.exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
        
        await session.initialize()
        self.sessions[server_name] = session
        
        # 1. Fetch and store the schemas internally
        tools_response = await session.list_tools()
        self.server_schemas[server_name] = {tool.name: tool for tool in tools_response.tools}
        
        # 2. Inject the single Gateway tool
        self._inject_gateway(server_name, description)
            
        func.log(f"[MCP] {server_name} connected. Gateway active for {len(tools_response.tools)} tools.", level="INFO")

    def _inject_gateway(self, server_name: str, description: str):
        """
        Creates the single gateway function that JARVIS sees (Flattened Signature).

        This wrapper function abstracts the complex MCP interaction (listing tools,
        executing commands) into a simple, flat interface for the AI agent.

        Args:
            server_name: The name of the server this gateway represents.
            description: The high-level description of the server's capabilities.
        """
        
        # The docstring explicitly teaches JARVIS to pass arguments flatly
        docstring = f"{description}\n\nArgs:\n"
        docstring += "    action (str): Use 'list_tools' to see available commands, or 'execute' to run one. Required.\n"
        docstring += "    command (str): The specific tool name to run. Required if action is 'execute'.\n"
        docstring += "    [other_params] (Any): Pass any required command arguments directly as top-level parameters.\n"

        def gateway_wrapper(**kwargs) -> Dict[str, Any]:
            """
            Gateway wrapper function exposed to JARVIS.

            Handles the routing logic based on the 'action' parameter.

            Args:
                **kwargs: Parameters passed by the calling agent, including 'action', 'command', and tool-specific arguments.

            Returns:
                A dictionary containing the status ('SUCCESS' or 'FAILED') and the result/error message.
            """
            # Use .pop() to remove 'action' and 'command' from the kwargs dictionary
            action = kwargs.pop("action", "").strip().lower()
            
            if action == "list_tools":
                return {"status": "SUCCESS", "output": self._format_tools_list(server_name)}
            
            elif action == "execute":
                command = kwargs.pop("command", None)
                
                if not command:
                    return {"status": "FAILED", "error": "Missing 'command' parameter for execution."}
                if command not in self.server_schemas[server_name]:
                    return {"status": "FAILED", "error": f"Unknown command '{command}'. Run 'list_tools' first."}
                    
                return self._run_async_task(self._execute_mcp_tool(server_name, command, kwargs))
                
            else:
                return {"status": "FAILED", "error": "Invalid action. Use 'list_tools' or 'execute'."}
            
        gateway_wrapper.__name__ = server_name
        gateway_wrapper.__doc__ = docstring
        
        self.registry.register_tool(server_name, gateway_wrapper)

    def _format_tools_list(self, server_name: str) -> str:
        """
        Formats the stored schemas into a readable text block for JARVIS's short-term memory.

        Args:
            server_name: The name of the server whose tools are being listed.

        Returns:
            A formatted string detailing all available commands and their arguments.
        """
        tools = self.server_schemas.get(server_name, {})
        output = f"Available commands for {server_name}:\n\n"
        
        for name, tool in tools.items():
            desc = tool.description or "No description."
            output += f"Command: {name}\n  Desc: {desc}\n"
            
            input_schema = getattr(tool, "input_schema", getattr(tool, "inputSchema", {}))
            props = input_schema.get("properties", {}) if isinstance(input_schema, dict) else {}
            reqs = input_schema.get("required", []) if isinstance(input_schema, dict) else []
            if props:
                output += "  Arguments:\n"
                for p_name, p_data in props.items():
                    req_tag = " (Required)" if p_name in reqs else ""
                    p_type = p_data.get('type', 'any')
                    output += f"    - {p_name} [{p_type}]: {p_data.get('description', '')}{req_tag}\n"
            output += "\n"
            func.log(f"[MCP] {server_name} - Command: {name} | Args: {list(props.keys())}", level="DEBUG")
            
        return output.strip()

    async def _execute_mcp_tool(self, server_name: str, command: str, raw_params: dict) -> dict:
        """
        Type-casts the arguments and sends the JSON-RPC execution request to the MCP server.

        Args:
            server_name: The name of the server to execute the tool on.
            command: The name of the tool/command to run.
            raw_params: A dictionary of parameters passed by the agent, which will be type-casted.

        Returns:
            A dictionary indicating the execution status and the resulting output or error.
        """
        tool_def = self.server_schemas[server_name][command]
        input_schema = getattr(tool_def, "input_schema", getattr(tool_def, "inputSchema", {}))
        schema = input_schema.get("properties", {}) if isinstance(input_schema, dict) else {}
        casted_params = {}
        
        # Universal Type Casting
        if isinstance(raw_params, dict):
            for key, value in raw_params.items():
                if key not in schema:
                    continue
                expected_type = schema[key].get("type", "string")
                try:
                    if expected_type == "integer": casted_params[key] = int(value)
                    elif expected_type == "number": casted_params[key] = float(value)
                    elif expected_type == "boolean": casted_params[key] = str(value).lower() in ("true", "1", "yes")
                    elif expected_type == "array": casted_params[key] = value if isinstance(value, list) else [value]
                    elif expected_type == "object": casted_params[key] = value if isinstance(value, dict) else json.loads(value)
                    else: casted_params[key] = str(value)
                except Exception:
                    return {"status": "FAILED", "error": f"Type mismatch: '{key}' must be {expected_type}."}
        
        # Dispatch
        try:
            session = self.sessions[server_name]
            result = await session.call_tool(command, arguments=casted_params)
            
            if result.isError:
                err = result.content[0].text if result.content else "Unknown MCP Error."
                return {"status": "FAILED", "error": err}
                
            out = result.content[0].text if result.content else "Action completed."
            return {"status": "SUCCESS", "output": out}
        except Exception as e:
            func.error(f"[MCP] Execution error for {server_name}.{command}: {str(e)}")
            return {"status": "FAILED", "error": str(e)}