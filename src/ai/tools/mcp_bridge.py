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
    """
    
    def __init__(self, tool_registry):
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
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run_async_task(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def load_from_config(self, filepath: str):
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
        func.log(f"[MCP] Connecting to {server_name}...", level="INFO")
        try:
            self._run_async_task(self._async_connect(server_name, command, args, description))
        except Exception as e:
            func.log(f"[MCP] Failed to connect to {server_name}: {e}", level="ERROR")

    async def _async_connect(self, server_name: str, command: str, args: List[str], description: str):
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
        """Creates the single gateway function that JARVIS sees (Flattened Signature)."""
        
        # The docstring explicitly teaches JARVIS to pass arguments flatly
        docstring = f"{description}\n\nArgs:\n"
        docstring += "    action (str): Use 'list_tools' to see available commands, or 'execute' to run one. Required.\n"
        docstring += "    command (str): The specific tool name to run. Required if action is 'execute'.\n"
        docstring += "    [other_params] (Any): Pass any required command arguments directly as top-level parameters.\n"

        def gateway_wrapper(**kwargs) -> Dict[str, Any]:
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
        """Formats the stored schemas into a readable text block for JARVIS's short-term memory."""
        tools = self.server_schemas.get(server_name, {})
        output = f"Available commands for {server_name}:\n\n"
        
        for name, tool in tools.items():
            desc = tool.description or "No description."
            output += f"Command: {name}\n  Desc: {desc}\n"
            
            props = tool.inputSchema.get("properties", {})
            reqs = tool.inputSchema.get("required", [])
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
        """Type-casts the arguments and sends the JSON-RPC execution."""
        schema = self.server_schemas[server_name][command].inputSchema.get("properties", {})
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