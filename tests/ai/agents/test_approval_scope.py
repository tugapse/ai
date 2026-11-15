import os
import threading
from unittest.mock import MagicMock

from ai.agents import approval_scope as scope
from ai.agents.agent_io import PERMISSION_ALWAYS


def test_command_prefix():
    assert scope.command_prefix("git status -s") == "git status"
    assert scope.command_prefix("ls -la") == "ls"
    assert scope.command_prefix("pytest tests/x.py") == "pytest"
    assert scope.command_prefix("ls && rm -rf /") is None
    assert scope.command_prefix("cat a | sh") is None
    assert scope.command_prefix("echo $(id)") is None
    assert scope.command_prefix("echo hi > f") is None
    assert scope.command_prefix("") is None


def test_shell_rule_covers_same_program_only():
    rule = scope.rule_for("execute_command", {"command": "git status"})
    assert rule == "execute_command|cmd:git status"
    assert scope.is_allowed("execute_command", {"command": "git status --short"}, {rule})
    assert not scope.is_allowed("execute_command", {"command": "git push --force"}, {rule})
    assert not scope.is_allowed("execute_command", {"command": "git status; rm -rf ~"}, {rule})


def test_file_rule_covers_folder_and_below(tmp_path):
    rule = scope.rule_for("write_file", {"path": str(tmp_path / "src" / "a.py")})
    assert scope.is_allowed("write_file", {"path": str(tmp_path / "src" / "b.py")}, {rule})
    assert scope.is_allowed("write_file", {"path": str(tmp_path / "src" / "sub" / "c.py")}, {rule})
    assert not scope.is_allowed("write_file", {"path": str(tmp_path / "other.py")}, {rule})
    assert not scope.is_allowed("write_file", {"path": str(tmp_path / "src2" / "x.py")}, {rule})
    assert not scope.is_allowed("delete_file", {"path": str(tmp_path / "src" / "b.py")}, {rule})


def test_root_marker_is_relative_to_cwd():
    rule = scope.rule_for("patch_file", {"path": "@ROOT/pkg/mod.py"})
    assert rule == f"patch_file|dir:{os.path.join(os.getcwd(), 'pkg')}"


def test_never_remembered_and_whole_tool():
    assert scope.rule_for("enable_mcp_server", {"name": "x"}, never_remember=("enable_mcp_server",)) is None
    assert scope.rule_for("github", {"q": 1}) == "github"
    assert scope.is_allowed("github", {}, {"github"})
    # rules saved by older sessions (plain tool names) still approve the whole tool
    assert scope.is_allowed("execute_command", {"command": "anything"}, {"execute_command"})


def _orchestrator(answer):
    from ai.agents.agent_orchestrator import AgentOrchestrator
    orch = AgentOrchestrator.__new__(AgentOrchestrator)
    orch.cancel_event = threading.Event()
    orch.auto_authorized_tools = set()
    orch.mcp_bridge = None
    orch.io = MagicMock()
    orch.io.request_permission.return_value = answer
    orch.emit = MagicMock()
    return orch


def test_gatekeeper_always_remembers_only_that_command(monkeypatch):
    import ai.agents.agent_orchestrator as ao
    monkeypatch.setattr(ao, "get_hil_tools", lambda: ["execute_command"])
    orch = _orchestrator(PERMISSION_ALWAYS)

    assert orch._gatekeeper("execute_command", {"command": "ls -la"}, "MASTER")
    assert orch._gatekeeper("execute_command", {"command": "ls src"}, "MASTER")
    assert orch.io.request_permission.call_count == 1
    assert orch._gatekeeper("execute_command", {"command": "rm -rf build"}, "MASTER")
    assert orch.io.request_permission.call_count == 2


def test_gatekeeper_always_gated_tool_keeps_asking(monkeypatch):
    import ai.agents.agent_orchestrator as ao
    monkeypatch.setattr(ao, "get_hil_tools", lambda: [])
    orch = _orchestrator(PERMISSION_ALWAYS)
    orch._gatekeeper("enable_mcp_server", {"name": "github"}, "MASTER")
    orch._gatekeeper("enable_mcp_server", {"name": "github"}, "MASTER")
    assert orch.io.request_permission.call_count == 2
    assert orch.auto_authorized_tools == set()


def test_program_rule_covers_every_call_to_it():
    rule = scope.rule_for("execute_command", {"command": "ls -la"})
    assert rule == "execute_command|cmd:ls"
    assert scope.is_allowed("execute_command", {"command": "ls src"}, {rule})
