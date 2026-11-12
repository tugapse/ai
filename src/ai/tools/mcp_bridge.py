import asyncio
import threading
import json
import os
from contextlib import AsyncExitStack
from typing import Dict, Any, List, Optional
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
    
    # Seconds to wait for a server to start and list its tools (npx may download on first run).
    CONNECT_TIMEOUT = 120.0
    # Seconds to wait for a single tool call.
    CALL_TIMEOUT = 300.0

    def __init__(self, tool_registry, log_dir: Optional[str] = None):
        """
        Initializes the MCPBridge.

        Args:
            tool_registry: The registry object used to register the gateway tools.
            log_dir: Directory for per-server stderr logs. Defaults to <system logs>/mcp.
        """
        self.registry = tool_registry
        self.sessions: Dict[str, ClientSession] = {}
        
        # Stores the raw tool schemas for each server: { "powerpoint": { "add_slide": {...} } }
        self.server_schemas: Dict[str, Dict[str, Any]] = {}

        # Each server lives in its own task (anyio contexts must be exited by the task that
        # entered them); setting its stop event shuts the server down cleanly.
        self._server_tasks: Dict[str, "asyncio.Task"] = {}
        self._stop_events: Dict[str, asyncio.Event] = {}
        self.log_dir = log_dir
        self._closed = False
        
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

    def _get_log_dir(self) -> str:
        if not self.log_dir:
            try:
                from ai.services.directory_manager import DirectoryManager
                self.log_dir = os.path.join(DirectoryManager().get_system_logs_directory(), "mcp")
            except Exception:
                import tempfile
                self.log_dir = os.path.join(tempfile.gettempdir(), "ai-mcp-logs")
        return self.log_dir

    def get_log_path(self, server_name: str) -> str:
        """Path of the file receiving a server's stderr."""
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in server_name)
        return os.path.join(self._get_log_dir(), f"{safe}.log")

    def _open_errlog(self, server_name: str):
        """
        Opens the stderr sink for a server process. Servers often log to stderr
        (e.g. "GitHub MCP Server running on stdio"); inheriting the terminal's stderr
        would write straight over the interactive chat UI.
        """
        try:
            path = self.get_log_path(server_name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            return open(path, "a", encoding="utf-8")
        except OSError:
            return open(os.devnull, "w", encoding="utf-8")

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
                    
                self.connect_server(server_name, command, args, description, env=details.get("env"))
                
        except Exception as e:
            func.log(f"[MCP] Error loading config: {str(e)}", level="ERROR")

    def connect_server(self, server_name: str, command: str, args: List[str], description: str, env: Optional[Dict[str, str]] = None):
        """
        Initiates the connection process for a specified MCP server.

        Args:
            server_name: The unique name identifier for the server.
            command: The executable command for the server process.
            args: A list of command-line arguments for the server process.
            description: A human-readable description of the server's functionality.
            env: Optional extra environment variables for the server process.
        """
        func.log(f"[MCP] Connecting to {server_name}...", level="INFO")
        try:
            self._run_async_task(self._async_connect(server_name, command, args, description, env))
        except Exception as e:
            func.log(f"[MCP] Failed to connect to {server_name}: {e or type(e).__name__} (server log: {self.get_log_path(server_name)})", level="ERROR")

    async def _async_connect(self, server_name: str, command: str, args: List[str], description: str, env: Optional[Dict[str, str]] = None):
        """
        Starts the server task and waits until it is connected, its schemas are fetched
        and its gateway is registered.

        Args:
            server_name: The name of the server being connected to.
            command: The command to execute the server.
            args: Arguments for the server command.
            description: The description used for the gateway tool.
            env: Optional extra environment variables for the server process.

        Raises:
            Exception: Whatever prevented the server from starting (or TimeoutError).
        """
        server_env = None
        if env:
            server_env = dict(os.environ)
            server_env.update({str(k): str(v) for k, v in env.items()})
        server_params = StdioServerParameters(command=command, args=args, env=server_env)

        ready: asyncio.Future = asyncio.get_running_loop().create_future()
        self._stop_events[server_name] = asyncio.Event()
        task = asyncio.create_task(self._serve(server_name, server_params, description, ready))
        self._server_tasks[server_name] = task
        try:
            tool_count = await asyncio.wait_for(asyncio.shield(ready), timeout=self.CONNECT_TIMEOUT)
        except BaseException:
            task.cancel()
            self._server_tasks.pop(server_name, None)
            raise
        func.log(f"[MCP] {server_name} connected. Gateway active for {tool_count} tools.", level="INFO")

    async def _serve(self, server_name: str, server_params: StdioServerParameters, description: str, ready: asyncio.Future):
        """
        Owns one server connection for its whole life: connects, publishes the gateway,
        then holds the connection open until the server's stop event is set.
        """
        try:
            async with AsyncExitStack() as stack:
                errlog = stack.enter_context(self._open_errlog(server_name))
                read_stream, write_stream = await stack.enter_async_context(stdio_client(server_params, errlog=errlog))
                session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
                await session.initialize()

                tools_response = await session.list_tools()
                self.sessions[server_name] = session
                self.server_schemas[server_name] = {tool.name: tool for tool in tools_response.tools}
                self._inject_gateway(server_name, description)

                if not ready.done():
                    ready.set_result(len(tools_response.tools))
                await self._stop_events[server_name].wait()
        except BaseException as e:
            if not ready.done():
                ready.set_exception(e if isinstance(e, Exception) else RuntimeError(f"{server_name} stopped during startup"))
            elif not isinstance(e, asyncio.CancelledError):
                func.log(f"[MCP] {server_name} disconnected: {e}", level="WARN")
        finally:
            self.sessions.pop(server_name, None)

    def close(self, timeout: float = 10.0):
        """
        Shuts down every server (closing sessions and terminating the processes),
        unregisters their gateways and stops the background loop. Safe to call twice.
        """
        if self._closed:
            return
        self._closed = True

        async def _shutdown():
            for event in self._stop_events.values():
                event.set()
            tasks = [t for t in self._server_tasks.values() if not t.done()]
            if tasks:
                done, pending = await asyncio.wait(tasks, timeout=timeout)
                for task in pending:
                    task.cancel()
                if pending:
                    await asyncio.wait(pending, timeout=2)

        if self._loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(_shutdown(), self._loop).result(timeout + 5)
            except Exception as e:
                func.debug(f"[MCP] Shutdown error: {e}")
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=5)

        tools = getattr(self.registry, "get_all_tools", None)
        if callable(tools):
            try:
                registered = tools()
                for name in list(self.server_schemas):
                    if isinstance(registered, dict):
                        registered.pop(name, None)
            except Exception:
                pass
        self.sessions.clear()

    def _inject_gateway(self, server_name: str, description: str):
        """
        Creates the single gateway function that JARVIS sees (Flattened Signature).

        This wrapper function abstracts the complex MCP interaction (listing tools,
        executing commands) into a simple, flat interface for the AI agent.

        Args:
            server_name: The name of the server this gateway represents.
            description: The high-level description of the server's capabilities.
        """
        
        # This docstring is the ONLY thing the agent sees about the server: keep it model-facing.
        docstring = (
            f"{description}\n\n"
            "This tool is a gateway to an MCP server with its own commands. First call it with action\n"
            "'list_tools' to see the commands and their arguments, then call it with action 'execute'.\n"
            "Pass each command argument as its own tag (e.g. <url>https://example.com</url>), or all of\n"
            "them in 'arguments'.\n\n"
            "Args:\n"
            "    action (string): 'list_tools' or 'execute'.\n"
            "    command (string, optional): Command name from list_tools. Required when action is 'execute'.\n"
            "    arguments (string, optional): The command's arguments as a JSON object, e.g. {\"url\": \"https://example.com\"}. "
            "REQUIRED for command arguments named 'action' or 'command'.\n\n"
            "Returns:\n"
            "    output: the command's result text (images are summarized as [image: type, size]), or an error.\n"
        )

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
            action = str(kwargs.pop("action", "") or "").strip().lower()
            
            if action == "list_tools":
                return {"status": "SUCCESS", "output": self._format_tools_list(server_name)}
            
            elif action == "execute":
                command = kwargs.pop("command", None)
                
                if not command:
                    return {"status": "FAILED", "error": "Missing 'command' parameter for execution."}
                if command not in self.server_schemas[server_name]:
                    return {"status": "FAILED", "error": f"Unknown command '{command}'. Run 'list_tools' first."}

                # Explicit arguments object: the only way to pass tool params named
                # 'action'/'command' (e.g. Playwright's browser_tabs(action=...)).
                explicit = kwargs.pop("arguments", None)
                if explicit not in (None, ""):
                    if isinstance(explicit, str):
                        try:
                            explicit = json.loads(explicit)
                        except json.JSONDecodeError:
                            return {"status": "FAILED", "error": "'arguments' must be a JSON object, e.g. {\"action\": \"list\"}."}
                    if not isinstance(explicit, dict):
                        return {"status": "FAILED", "error": "'arguments' must be a JSON object, e.g. {\"action\": \"list\"}."}
                    kwargs.update(explicit)
                    
                if server_name not in self.sessions:
                    return {"status": "FAILED", "error": f"MCP server '{server_name}' is not connected. See {self.get_log_path(server_name)}."}
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
                    if p_name in ("action", "command", "arguments"):
                        req_tag += f" [pass via arguments={{\"{p_name}\": ...}}]"
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
            result = await asyncio.wait_for(session.call_tool(command, arguments=casted_params), timeout=self.CALL_TIMEOUT)
            
            is_error = getattr(result, "is_error", getattr(result, "isError", False))
            
            content_parts = []
            if getattr(result, "content", None):
                for item in result.content:
                    content_parts.append(self._content_to_text(item))
            out = "\n".join(content_parts) if content_parts else ("Action completed." if not is_error else "Unknown MCP Error.")
            
            if is_error:
                return {"status": "FAILED", "error": out}
                
            return {"status": "SUCCESS", "output": out}
        except asyncio.TimeoutError:
            return {"status": "FAILED", "error": f"MCP call {server_name}.{command} timed out after {self.CALL_TIMEOUT:.0f}s."}
        except Exception as e:
            func.error(f"[MCP] Execution error for {server_name}.{command}: {str(e)}")
            return {"status": "FAILED", "error": str(e) or type(e).__name__}

    @staticmethod
    def _content_to_text(item: Any, max_len: int = 2000) -> str:
        """
        Converts one MCP content block into text for the agent. Binary payloads
        (images, audio, blobs) are summarized: a single screenshot is hundreds of KB
        of base64 and would flood the agent's context window.
        """
        kind = getattr(item, "type", None)
        text = getattr(item, "text", None)
        if isinstance(text, str):
            return text
        if kind in ("image", "audio"):
            data = getattr(item, "data", "") or ""
            mime = getattr(item, "mime_type", None) or getattr(item, "mimeType", None) or kind
            size = len(data) * 3 // 4 if isinstance(data, str) else len(data)
            return f"[{kind}: {mime}, {size} bytes]"
        if kind == "resource":
            resource = getattr(item, "resource", None)
            res_text = getattr(resource, "text", None)
            uri = getattr(resource, "uri", "")
            if isinstance(res_text, str):
                return res_text
            mime = getattr(resource, "mime_type", None) or getattr(resource, "mimeType", None) or "binary"
            return f"[resource: {uri} ({mime})]"
        if kind == "resource_link":
            return f"[resource link: {getattr(item, 'uri', '')} {getattr(item, 'name', '') or ''}]".strip()
        rendered = str(item)
        return rendered if len(rendered) <= max_len else rendered[:max_len] + "…"