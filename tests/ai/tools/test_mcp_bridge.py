"""
MCPBridge tests, driven the same way the agent drives it.

The agent:
  1. builds ``MCPBridge(tool_registry)`` and calls ``load_from_config(mcp_config.json)``
  2. sees ONE gateway tool per server (named after the server)
  3. calls it through ``ToolRegistry.execute_tool(name, params)`` with the
     parameters parsed from its XML output, i.e. mostly *strings*:
        {"action": "list_tools"}
        {"action": "execute", "command": "browser_navigate", "url": "https://..."}

A tiny real MCP server (fixtures/mcp_test_server.py) runs over stdio, exactly
like ``npx @playwright/mcp``. An opt-in live Playwright test is at the end
(set JARVIS_MCP_LIVE=1).
"""

import json
import os
import shutil
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import MagicMock

import pytest

import ai.program  # noqa: F401  (startup import order, avoids a circular import)
from ai.tools.mcp_bridge import MCPBridge
from ai.tools.tool_registry import ToolRegistry

FIXTURE_SERVER = os.path.join(os.path.dirname(__file__), "fixtures", "mcp_test_server.py")
SERVER = "jarvis_test_mcp"
TOOLS = {"echo", "add", "scale", "flag", "join", "describe", "fail", "multi", "screenshot", "noisy", "tabs"}


def write_config(path, servers):
    path.write_text(json.dumps({"mcpServers": servers}))
    return str(path)


def server_entry(**overrides):
    entry = {
        "enabled": True,
        "description": "Test MCP server used by the JARVIS test-suite.",
        "command": sys.executable,
        "args": [FIXTURE_SERVER],
    }
    entry.update(overrides)
    return entry


def close_bridge(bridge, registry):
    for name in list(bridge.server_schemas):
        registry.get_all_tools().pop(name, None)
    if hasattr(bridge, "close"):
        bridge.close()


@pytest.fixture(scope="module", autouse=True)
def isolated_mcp_logs(tmp_path_factory):
    """Keep server stderr logs out of the real logs directory."""
    log_dir = str(tmp_path_factory.mktemp("mcp_logs"))
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(MCPBridge, "_get_log_dir", lambda self: self.log_dir or log_dir)
        yield log_dir


@pytest.fixture(scope="module")
def registry():
    return ToolRegistry()


@pytest.fixture(scope="module")
def bridge(registry, tmp_path_factory):
    config = write_config(tmp_path_factory.mktemp("mcp") / "mcp_config.json", {SERVER: server_entry()})
    b = MCPBridge(registry)
    b.load_from_config(config)
    yield b
    close_bridge(b, registry)


def call(registry, **params):
    """Calls the gateway exactly like the orchestrator does."""
    return registry.execute_tool(SERVER, params)


# ---------------------------------------------------------------- connection

class TestConnection:
    def test_server_connected_and_schemas_loaded(self, bridge):
        assert SERVER in bridge.sessions
        assert set(bridge.server_schemas[SERVER]) == TOOLS

    def test_single_gateway_tool_registered(self, bridge, registry):
        assert SERVER in registry.get_all_tools()
        for tool in TOOLS:
            assert tool not in registry.get_all_tools() or tool == SERVER

    def test_gateway_description_teaches_the_agent(self, bridge, registry):
        info = registry.get_tool_info(SERVER)
        assert "Test MCP server used by the JARVIS test-suite." in info
        assert "list_tools" in info and "execute" in info
        assert "First call it with action" in info  # teaches the list-then-execute flow


# ---------------------------------------------------------------- list_tools

class TestListTools:
    def test_list_tools_succeeds(self, bridge, registry):
        result = call(registry, action="list_tools")
        assert result["status"] == "SUCCESS", result

    def test_list_tools_shows_commands_and_arguments(self, bridge, registry):
        output = call(registry, action="list_tools")["output"]
        for tool in TOOLS:
            assert f"Command: {tool}" in output
        assert "- a [integer]" in output and "(Required)" in output
        assert "- factor [number]" in output
        assert "Add two integers." in output

    def test_action_is_case_and_space_insensitive(self, bridge, registry):
        assert call(registry, action="  LIST_TOOLS ")["status"] == "SUCCESS"


# ---------------------------------------------------------------- execute

class TestExecute:
    def test_echo(self, bridge, registry):
        result = call(registry, action="execute", command="echo", text="hello mcp")
        assert result == {"status": "SUCCESS", "output": "hello mcp"}

    @pytest.mark.parametrize("params, expected", [
        ({"command": "add", "a": "2", "b": "3"}, "2+3=5 (int,int)"),
        ({"command": "add", "a": 2, "b": 3}, "2+3=5 (int,int)"),
        ({"command": "scale", "value": "1.5"}, "3.0"),
        ({"command": "scale", "value": "1.5", "factor": "4"}, "6.0"),
        ({"command": "flag", "enabled": "true"}, "enabled=True (bool)"),
        ({"command": "flag", "enabled": "False"}, "enabled=False (bool)"),
        ({"command": "flag", "enabled": "yes"}, "enabled=True (bool)"),
        ({"command": "join", "items": "solo"}, "solo"),
        ({"command": "join", "items": ["a", "b"], "sep": "-"}, "a-b"),
        ({"command": "describe", "config": '{"b": 1, "a": 2}'}, "keys=a,b"),
        ({"command": "describe", "config": {"x": 1}}, "keys=x"),
    ])
    def test_agent_string_params_are_cast_to_schema_types(self, bridge, registry, params, expected):
        result = call(registry, action="execute", **params)
        assert result["status"] == "SUCCESS", result
        assert result["output"] == expected

    def test_unknown_params_are_dropped(self, bridge, registry):
        result = call(registry, action="execute", command="echo", text="hi", hallucinated="x")
        assert result == {"status": "SUCCESS", "output": "hi"}

    def test_type_mismatch(self, bridge, registry):
        result = call(registry, action="execute", command="add", a="two", b="3")
        assert result["status"] == "FAILED" and "a" in result["error"] and "integer" in result["error"]

    def test_invalid_json_object(self, bridge, registry):
        result = call(registry, action="execute", command="describe", config="{not json")
        assert result["status"] == "FAILED"

    def test_tool_error_is_reported_as_failed(self, bridge, registry):
        result = call(registry, action="execute", command="fail", message="boom from server")
        assert result["status"] == "FAILED"
        assert "boom from server" in result["error"]

    def test_missing_required_argument_is_failed(self, bridge, registry):
        result = call(registry, action="execute", command="add", a="1")
        assert result["status"] == "FAILED"

    def test_multiple_content_parts_are_all_returned(self, bridge, registry):
        result = call(registry, action="execute", command="multi")
        assert result["status"] == "SUCCESS"
        assert "part one" in result["output"] and "part two" in result["output"]

    def test_image_content_is_summarized_not_dumped(self, bridge, registry):
        result = call(registry, action="execute", command="screenshot")
        assert result["status"] == "SUCCESS", result
        output = result["output"]
        assert "image" in output.lower() and "png" in output.lower()
        assert "iVBORw0KGgo" not in output  # no base64 blob in the agent's context
        assert len(output) < 300

    def test_sequential_calls_reuse_the_session(self, bridge, registry):
        for i in range(5):
            assert call(registry, action="execute", command="add", a=str(i), b="1")["output"].startswith(f"{i}+1=")

    def test_calls_from_worker_threads(self, bridge, registry):
        """The chat UI runs the orchestrator in a worker thread."""
        results = []
        threads = [threading.Thread(target=lambda n=n: results.append(call(registry, action="execute", command="echo", text=f"t{n}")))
                   for n in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(10)
        assert sorted(r["output"] for r in results) == ["t0", "t1", "t2", "t3"]


class TestArgumentsObject:
    """Tool parameters named 'action'/'command' clash with the gateway's own parameters."""

    def test_clashing_params_via_json_string(self, bridge, registry):
        # What the agent's XML produces: <arguments>{"action": "list"}</arguments>
        result = call(registry, action="execute", command="tabs", arguments='{"action": "list", "command": "x"}')
        assert result == {"status": "SUCCESS", "output": "tabs action=list command=x"}

    def test_arguments_as_dict_and_mixed_with_top_level(self, bridge, registry):
        result = call(registry, action="execute", command="add", a="1", arguments={"b": 41})
        assert result["output"] == "1+41=42 (int,int)"

    def test_arguments_take_precedence(self, bridge, registry):
        result = call(registry, action="execute", command="echo", text="top", arguments='{"text": "inner"}')
        assert result["output"] == "inner"

    @pytest.mark.parametrize("bad", ["{not json", "[1, 2]", "42"])
    def test_invalid_arguments(self, bridge, registry, bad):
        result = call(registry, action="execute", command="tabs", arguments=bad)
        assert result["status"] == "FAILED" and "JSON object" in result["error"]

    def test_empty_arguments_ignored(self, bridge, registry):
        assert call(registry, action="execute", command="echo", text="hi", arguments="")["output"] == "hi"

    def test_list_tools_and_description_explain_it(self, bridge, registry):
        output = call(registry, action="list_tools")["output"]
        assert 'pass via arguments={"action": ...}' in output
        info = registry.get_tool_info(SERVER)
        assert "arguments (string, optional)" in info and "'action' or 'command'" in info


class TestGatewayErrors:
    def test_missing_command(self, bridge, registry):
        result = call(registry, action="execute")
        assert result["status"] == "FAILED" and "command" in result["error"]

    def test_unknown_command(self, bridge, registry):
        result = call(registry, action="execute", command="browser_teleport")
        assert result["status"] == "FAILED" and "list_tools" in result["error"]

    def test_invalid_action(self, bridge, registry):
        assert call(registry, action="dance")["status"] == "FAILED"

    def test_missing_action(self, bridge, registry):
        assert call(registry)["status"] == "FAILED"


# ---------------------------------------------------------------- config handling

class TestConfig:
    def test_missing_config_file_is_harmless(self, tmp_path):
        reg = MagicMock()
        b = MCPBridge(reg)
        b.load_from_config(str(tmp_path / "nope.json"))
        assert b.server_schemas == {}
        reg.register_tool.assert_not_called()
        close_bridge(b, MagicMock(get_all_tools=dict))

    def test_disabled_and_commandless_servers_are_skipped(self, tmp_path):
        reg = MagicMock()
        config = write_config(tmp_path / "c.json", {
            "off": server_entry(enabled=False),
            "nocmd": {"enabled": True, "args": []},
        })
        b = MCPBridge(reg)
        b.load_from_config(config)
        assert b.server_schemas == {}
        close_bridge(b, MagicMock(get_all_tools=dict))

    def test_broken_server_does_not_block_the_others(self, tmp_path):
        registry = ToolRegistry()
        config = write_config(tmp_path / "c.json", {
            "broken": {"enabled": True, "command": "/nonexistent/mcp-server-binary", "args": []},
            SERVER + "_2": server_entry(),
        })
        b = MCPBridge(registry)
        start = time.monotonic()
        b.load_from_config(config)
        try:
            assert time.monotonic() - start < 30
            assert "broken" not in b.server_schemas
            assert SERVER + "_2" in b.server_schemas
            assert "broken" not in registry.get_all_tools()
        finally:
            close_bridge(b, registry)

    def test_server_stderr_goes_to_log_file_not_terminal(self, tmp_path):
        """Server logs would scribble over the prompt_toolkit chat UI.

        Runs the bridge in a separate process and inspects that process's real stderr
        (in-process fd capture does not model what a terminal sees).
        """
        import subprocess
        name = SERVER + "_noisy"
        config = write_config(tmp_path / "c.json", {name: server_entry()})
        log_dir = tmp_path / "logs"
        script = f"""
import sys
sys.path.insert(0, {os.path.abspath('src')!r})
from ai.config import ProgramConfig
ProgramConfig.load()
import ai.functions as F; F.LOCK_LOG = True; F.LOCK_DEBUG = True
import ai.program
from ai.tools.tool_registry import ToolRegistry
from ai.tools.mcp_bridge import MCPBridge
reg = ToolRegistry()
b = MCPBridge(reg, log_dir={str(log_dir)!r})
b.load_from_config({config!r})
print(reg.execute_tool({name!r}, {{"action": "execute", "command": "noisy"}})["output"])
b.close()
"""
        proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip().endswith("done")
        assert "TEST SERVER STARTED ON STDIO" not in proc.stderr
        assert "NOISY-STDERR-LINE" not in proc.stderr
        server_log = (log_dir / f"{name}.log").read_text()
        assert "TEST SERVER STARTED ON STDIO" in server_log and "NOISY-STDERR-LINE" in server_log


class TestLifecycle:
    def test_close_stops_server_processes_and_unregisters(self, tmp_path):
        registry = ToolRegistry()
        name = SERVER + "_lifecycle"
        existing = _child_server_pids()
        b = MCPBridge(registry, log_dir=str(tmp_path))
        b.load_from_config(write_config(tmp_path / "c.json", {name: server_entry()}))
        assert name in registry.get_all_tools()
        pids_before = _child_server_pids() - existing
        assert pids_before, "test server process not found"

        b.close()
        b.close()  # idempotent

        assert name not in registry.get_all_tools()
        deadline = time.time() + 10
        while time.time() < deadline and (_child_server_pids() & pids_before):
            time.sleep(0.1)
        assert not (_child_server_pids() & pids_before), "server process still running after close()"

    def test_call_after_server_died_fails_cleanly(self, tmp_path):
        registry = ToolRegistry()
        name = SERVER + "_dies"
        b = MCPBridge(registry, log_dir=str(tmp_path))
        existing = _child_server_pids()
        b.load_from_config(write_config(tmp_path / "c.json", {name: server_entry()}))
        try:
            import signal
            for pid in _child_server_pids() - existing:
                os.kill(pid, signal.SIGKILL)
            time.sleep(0.5)
            result = registry.execute_tool(name, {"action": "execute", "command": "echo", "text": "x"})
            assert result["status"] == "FAILED"
        finally:
            b.close()

    def test_connect_timeout(self, tmp_path, monkeypatch):
        """A server that never answers the handshake must not block agent start-up forever."""
        monkeypatch.setattr(MCPBridge, "CONNECT_TIMEOUT", 1.5)
        registry = ToolRegistry()
        b = MCPBridge(registry, log_dir=str(tmp_path))
        start = time.monotonic()
        b.load_from_config(write_config(tmp_path / "c.json", {
            "hung": {"enabled": True, "command": sys.executable, "args": ["-c", "import time; time.sleep(60)"]},
        }))
        try:
            assert time.monotonic() - start < 10
            assert "hung" not in b.server_schemas and "hung" not in registry.get_all_tools()
        finally:
            b.close()


def _child_server_pids():
    """PIDs of fixture server processes started by this test process."""
    pids = set()
    me = str(os.getpid())
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            with open(f"/proc/{entry}/cmdline", "rb") as f:
                cmd = f.read().replace(b"\0", b" ").decode(errors="replace")
            with open(f"/proc/{entry}/stat") as f:
                ppid = f.read().rsplit(")", 1)[1].split()[1]
        except OSError:
            continue
        if "mcp_test_server.py" in cmd and ppid == me:
            pids.add(int(entry))
    return pids


# ---------------------------------------------------------------- the agent path

class TestAgentUsesMcp:
    """Full AgentOrchestrator run: MCP loaded from the user config dir, scripted model."""

    @pytest.fixture
    def orchestrator(self, tmp_path, monkeypatch):
        from ai.agents.agent_io import AgentIO
        from ai.agents.agent_orchestrator import AgentOrchestrator
        from ai.agents.session_manager import AgentSessionManager
        from ai.services.directory_manager import DirectoryManager

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        write_config(config_dir / "mcp_config.json", {SERVER: server_entry()})
        monkeypatch.setattr(DirectoryManager, "get_user_config_directory", lambda self: str(config_dir))
        monkeypatch.setattr(AgentSessionManager, "_get_agents_storage_root", staticmethod(lambda: str(tmp_path / "agents")))
        monkeypatch.chdir(tmp_path)

        class Connector:
            def __init__(self):
                self.requests = []
                self.script = []
                self.llm = MagicMock()

            def send_request(self, payload, prompt_file_path, agent_config):
                self.requests.append({"payload": payload, "config": agent_config})
                return self.script.pop(0) if self.script else {"action": {"agent_target": "STOP"}}

            def get_context_limit(self):
                return 32000

            def get_max_tokens(self):
                return 1024

        class IO(AgentIO):
            def __init__(self):
                self.events = []
                self.permission_requests = []

            def emit(self, event):
                self.events.append(event)

            def request_permission(self, tool, params):
                self.permission_requests.append(tool)
                return "y"

        connector = Connector()
        io = IO()
        registry = ToolRegistry()
        orch = AgentOrchestrator(
            llm_connector=connector,
            tool_registry=registry,
            pipeline_config={
                "entry_point": "MASTER",
                "max_iterations": 10,
                "agents": {"MASTER": {
                    "role": "management",
                    "tools": ["read_file"],
                    "allowed_targets": ["MASTER", "USER", "STOP"],
                    "prompt_file_path": "m.md",
                }},
            },
            module_registry=MagicMock(items=lambda: []),
            io=io,
        )
        yield orch, connector, io
        close_bridge(orch.mcp_bridge, registry)

    def test_agent_lists_then_executes_mcp_tool(self, orchestrator):
        orch, connector, io = orchestrator
        connector.script = [
            {"action": {"tool_name": SERVER, "tool_parameters": {"action": "list_tools"}}},
            {"action": {"tool_name": SERVER, "tool_parameters": {"action": "execute", "command": "add", "a": "20", "b": "22"}}},
            {"response_to_user": "The answer is 42.", "action": {"agent_target": "STOP"}},
        ]
        result = orch.run_loop("add 20 and 22 with the test server", "mcp-session")

        assert result.reason == "done"
        outcomes = orch.memory.context.tool_results
        assert [o["tool"] for o in outcomes] == [SERVER, SERVER]
        assert outcomes[0]["result"]["status"] == "SUCCESS"
        assert "Command: add" in outcomes[0]["result"]["output"]
        assert outcomes[1]["result"] == {"status": "SUCCESS", "output": "20+22=42 (int,int)"}

    def test_mcp_gateway_is_offered_to_the_agent(self, orchestrator):
        orch, connector, _ = orchestrator
        orch.run_loop("anything", "mcp-session-2")
        config = connector.requests[0]["config"]
        assert SERVER in config["tools"]
        assert "Test MCP server used by the JARVIS test-suite." in config["tool_descriptions"]

    def test_mcp_failure_reaches_the_agent_as_a_result(self, orchestrator):
        orch, connector, _ = orchestrator
        connector.script = [
            {"action": {"tool_name": SERVER, "tool_parameters": {"action": "execute", "command": "fail", "message": "nope"}}},
            {"action": {"agent_target": "STOP"}},
        ]
        orch.run_loop("trigger failure", "mcp-session-3")
        result = orch.memory.context.tool_results[0]["result"]
        assert result["status"] == "FAILED" and "nope" in result["error"]
        # and the agent sees it in its next request
        inbox = connector.requests[1]["payload"]["messages_received"]
        assert any(m.get("result", {}).get("status") == "FAILED" for m in inbox)


# ---------------------------------------------------------------- live Playwright (opt-in)

LIVE = os.environ.get("JARVIS_MCP_LIVE") == "1"


@pytest.mark.skipif(not LIVE, reason="set JARVIS_MCP_LIVE=1 to run the live Playwright MCP test")
@pytest.mark.skipif(shutil.which("npx") is None, reason="npx not installed")
class TestLivePlaywright:
    """Uses the real @playwright/mcp server through the bridge against a local page."""

    @pytest.fixture(scope="class")
    def site(self, tmp_path_factory):
        root = tmp_path_factory.mktemp("site")
        (root / "index.html").write_text(
            "<html><head><title>Jarvis MCP Test Page</title></head>"
            "<body><h1>Hello from the test page</h1><button>Press me</button></body></html>"
        )
        handler = lambda *a, **k: SimpleHTTPRequestHandler(*a, directory=str(root), **k)
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        yield f"http://127.0.0.1:{httpd.server_address[1]}/index.html"
        httpd.shutdown()

    @pytest.fixture(scope="class")
    def playwright(self, tmp_path_factory):
        registry = ToolRegistry()
        config = write_config(tmp_path_factory.mktemp("pw") / "mcp_config.json", {
            "playwright": {
                "enabled": True,
                "description": "Browser automation tool.",
                "command": "npx",
                "args": ["-y", "@playwright/mcp@latest", "--headless", "--isolated"],
            }
        })
        b = MCPBridge(registry)
        b.load_from_config(config)
        yield registry, b
        try:
            registry.execute_tool("playwright", {"action": "execute", "command": "browser_close"})
        finally:
            close_bridge(b, registry)

    def test_list_tools(self, playwright):
        registry, bridge = playwright
        assert "playwright" in bridge.server_schemas, "playwright MCP server failed to start"
        result = registry.execute_tool("playwright", {"action": "list_tools"})
        assert result["status"] == "SUCCESS", result
        assert "Command: browser_navigate" in result["output"]

    def test_navigate_and_snapshot(self, playwright, site):
        registry, _ = playwright
        nav = registry.execute_tool("playwright", {"action": "execute", "command": "browser_navigate", "url": site})
        assert nav["status"] == "SUCCESS", nav
        snap = registry.execute_tool("playwright", {"action": "execute", "command": "browser_snapshot"})
        assert snap["status"] == "SUCCESS", snap
        assert "Hello from the test page" in snap["output"]

    def test_browser_tabs_action_param(self, playwright, site):
        """browser_tabs has its own 'action' parameter: only reachable via 'arguments'."""
        registry, _ = playwright
        registry.execute_tool("playwright", {"action": "execute", "command": "browser_navigate", "url": site})
        tabs = registry.execute_tool("playwright", {"action": "execute", "command": "browser_tabs", "arguments": '{"action": "list"}'})
        assert tabs["status"] == "SUCCESS", tabs
        assert "Jarvis MCP Test Page" in tabs["output"]

    def test_screenshot_is_not_a_base64_dump(self, playwright, site):
        registry, _ = playwright
        registry.execute_tool("playwright", {"action": "execute", "command": "browser_navigate", "url": site})
        shot = registry.execute_tool("playwright", {"action": "execute", "command": "browser_take_screenshot"})
        assert shot["status"] == "SUCCESS", shot
        assert len(shot["output"]) < 5000
