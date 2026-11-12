"""
/api/v1/agent/*: token checks, catalogue, and runs streamed as SSE.

The orchestrator is faked (``build_orchestrator`` is patched); the service, router, threads,
permission waits and working-directory guard are real.
"""

import json
import os
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from ai.agents.agent_io import AgentEvent, AgentEventType, PERMISSION_YES
from ai.config import ProgramSetting
from ai.modules.server.app import create_app

AUTH = {}  # the client fixture already sends a paired device's token


class FakeOrchestrator:
    """Emits a status, asks permission for one tool when ``gated``, then finishes."""

    def __init__(self, io, gated=False, block=None):
        self.io, self.gated, self.block = io, gated, block
        self.llm_connector = SimpleNamespace(on_token=None)
        self.cancelled = threading.Event()
        self.prompt = self.cwd = self.decision = None
        self.closed = False

    def run_loop(self, user_prompt, session_id):
        from ai.modules.tools_filesystem.tools import write_file
        from ai.tools.base import get_project_root
        self.prompt, self.cwd, self.root = user_prompt, os.getcwd(), get_project_root()
        # The real tools, as the agent calls them (the bug: they wrote to the server's folder).
        self.writes = [write_file(path="hello.txt", content="hi"),
                       write_file(path="../escape.txt", content="x"),
                       write_file(path="/tmp/abs-escape.txt", content="x")]
        self.io.emit(AgentEvent(AgentEventType.STATUS, agent="MASTER", text="working"))
        self.llm_connector.on_token("tok")
        if self.gated:
            self.decision = self.io.request_permission("execute_command", {"command": "ls"})
        if self.block is not None:
            self.block.wait(5)
        reason = "cancelled" if self.cancelled.is_set() else "done"
        return SimpleNamespace(reason=reason, message="all good")

    def cancel(self):
        self.cancelled.set()

    def close(self):
        self.closed = True


@pytest.fixture
def workdir(tmp_path):
    return tmp_path / "workspace"


@pytest.fixture
def config(workdir):
    values = {ProgramSetting.SERVER_AGENT_WORKDIR: str(workdir)}
    cfg = MagicMock()
    cfg.get.side_effect = lambda key, default=None: values.get(key, default)
    return cfg


@pytest.fixture
def user_dirs(tmp_path, monkeypatch):
    """Task and pipeline folders in tmp_path."""
    from ai.services.directory_manager import DirectoryManager
    user, pipelines = tmp_path / "user", tmp_path / "pipelines"
    (user / "task" / "release").mkdir(parents=True)
    (user / "task" / "commit.md").write_text("Write a commit message.")
    (user / "task" / "release" / "start.md").write_text("Start a release.")
    pipelines.mkdir()
    (pipelines / "default.json").write_text(json.dumps({
        "name": "Single", "description": "One agent", "entry_point": "MASTER",
        "agents": {"MASTER": {"tools": ["read_file", "execute_command"]}}}))
    monkeypatch.setattr(DirectoryManager, "get_user_directory", lambda self: str(user))
    monkeypatch.setattr(DirectoryManager, "get_user_pipelines_directory", lambda self: str(pipelines))
    monkeypatch.setattr(DirectoryManager, "get_system_pipelines_directory", lambda self: str(tmp_path / "none"))


class Built(list):
    """Fake orchestrators built so far; ``options`` configures the next ones."""
    options: dict = {}


@pytest.fixture
def orchestrators(monkeypatch):
    """Every fake orchestrator built; set ``.options`` to configure the next ones."""
    built = Built()

    def build(prog, pipeline_file, io=None, directory_manager=None):
        orch = FakeOrchestrator(io, **built.options)
        orch.pipeline_file, orch.llm = pipeline_file, prog.llm
        built.append(orch)
        return orch

    monkeypatch.setattr("ai.agents.agent.build_orchestrator", build)
    return built




@pytest.fixture
def client(hub, config, auth, paired, user_dirs, orchestrators, tmp_path, monkeypatch):
    monkeypatch.setattr("ai.functions.get_root_directory", lambda: str(tmp_path))
    return TestClient(create_app(hub, config, auth=auth), client=("127.0.0.1", 50000), headers=paired)


def events(response):
    out = []
    for line in response.iter_lines():
        if line.startswith("data: ") and line != "data: [DONE]":
            out.append(json.loads(line[6:]))
    return out


def run(client, **body):
    body.setdefault("prompt", "list the files")
    body.setdefault("model", "small")
    return client.post("/api/v1/agent/runs", json=body, headers=AUTH)


class TestAccess:
    def test_unpaired_client_is_401(self, client):
        assert client.get("/api/v1/agent/pipelines", headers={"Authorization": ""}).status_code == 401

    def test_unknown_token_is_401(self, client):
        assert client.get("/api/v1/agent/pipelines", headers={"Authorization": "Bearer nope"}).status_code == 401

    def test_runs_need_pairing_too(self, client):
        assert client.post("/api/v1/agent/runs", json={"prompt": "x"},
                           headers={"Authorization": ""}).status_code == 401

    def test_runs_and_permissions_are_audited(self, client, auth):
        events(run(client))
        lines = [json.loads(l) for l in open(auth.audit_path)]
        assert [l["event"] for l in lines][-1] == "agent_run" and lines[-1]["device_id"]


class TestCatalogue:
    def test_pipelines(self, client):
        (pipeline,) = client.get("/api/v1/agent/pipelines", headers=AUTH).json()
        assert pipeline["name"] == "default" and pipeline["title"] == "Single"
        assert pipeline["agents"] == [{"name": "MASTER", "tools": ["read_file", "execute_command"]}]

    def test_tasks_include_subfolders(self, client):
        names = [t["name"] for t in client.get("/api/v1/agent/tasks", headers=AUTH).json()]
        assert names == ["commit", "release/start"]

    def test_task_content(self, client):
        r = client.get("/api/v1/agent/tasks/release/start", headers=AUTH)
        assert r.json() == {"name": "release/start", "content": "Start a release."}

    @pytest.mark.parametrize("name", ["nope", "../task/commit", "release/../../x"])
    def test_unknown_or_escaping_task_is_404(self, client, name):
        assert client.get(f"/api/v1/agent/tasks/{name}", headers=AUTH).status_code == 404


class TestRuns:
    def test_run_streams_events_and_finishes(self, client, orchestrators, loads, workdir):
        evs = events(run(client, session_id="sess-1"))
        assert evs[0]["type"] == "run" and evs[0]["session_id"] == "sess-1"
        types = [e["type"] for e in evs]
        assert types[1:] == ["status", "token", "done"]
        assert evs[-1] == {"type": "done", "reason": "done", "message": "all good"}
        orch = orchestrators[0]
        assert orch.llm is loads[0] and orch.pipeline_file == "default.json" and orch.closed
        assert orch.cwd == os.path.realpath(workdir)

    def test_task_text_goes_before_the_prompt(self, client, orchestrators):
        events(run(client, task="commit", prompt="only staged files"))
        assert orchestrators[0].prompt == "Write a commit message.\n\nonly staged files"

    def test_cwd_is_a_subfolder_of_the_workdir(self, client, orchestrators, workdir):
        events(run(client, cwd="proj/a"))
        assert orchestrators[0].cwd == os.path.realpath(workdir / "proj" / "a")

    @pytest.mark.parametrize("cwd", ["../outside", "/etc"])
    def test_cwd_outside_the_workdir_is_400(self, client, cwd):
        assert run(client, cwd=cwd).status_code == 400

    def test_no_model_loaded_and_none_given_is_409(self, client):
        assert run(client, model=None).status_code == 409

    def test_run_without_model_uses_the_loaded_one(self, client, hub, orchestrators, loads):
        hub.get_brain("big", "")
        events(run(client, model=None))
        assert orchestrators[0].llm is loads[0] and hub.current_model_id == "big"

    def test_unknown_pipeline_and_model(self, client):
        assert run(client, pipeline="nope").status_code == 404
        assert run(client, model="nope").status_code == 404

    def test_empty_prompt_is_400(self, client):
        assert run(client, prompt=" ").status_code == 400

    def test_working_directory_is_restored(self, client):
        import ai.tools.base as tool_base
        before, root = os.getcwd(), tool_base.PROJECT_ROOT
        events(run(client))
        assert os.getcwd() == before and tool_base.PROJECT_ROOT == root

    def test_tools_write_inside_the_workdir_only(self, client, orchestrators, workdir, tmp_path):
        # Regression: write_file("hello.txt") landed in the server's own folder (the repo).
        server_dir = os.getcwd()
        events(run(client, cwd="proj"))
        orch = orchestrators[0]
        assert orch.root == os.path.realpath(workdir / "proj")
        ok, up, absolute = orch.writes
        assert ok["status"] == "SUCCESS" and (workdir / "proj" / "hello.txt").read_text() == "hi"
        assert not os.path.exists(os.path.join(server_dir, "hello.txt"))
        assert up["status"] == "FAILED" and absolute["status"] == "FAILED"
        assert not (workdir / "escape.txt").exists() and not os.path.exists("/tmp/abs-escape.txt")


def next_event(run_, kind, timeout=5):
    """The next event of ``kind`` from a run's queue (earlier ones are skipped)."""
    while True:
        ev = run_.events.get(timeout=timeout)
        if ev is None:
            raise AssertionError(f"run ended before a {kind!r} event")
        if ev["type"] == kind:
            return ev


class TestPermissions:
    """Driven through the service: the test client cannot answer while it reads a stream."""

    @pytest.fixture
    def service(self, client, orchestrators):
        orchestrators.options = {"gated": True}
        return client.app.state.agent_service

    def test_permission_event_then_answer_reaches_the_tool(self, client, service, orchestrators):
        run_ = service.start("list files", model="small")
        ev = next_event(run_, "permission")
        assert ev["tool"] == "execute_command" and ev["params"] == {"command": "ls"}
        assert any("ls" in line for line in ev["preview"]) and "\x1b" not in "".join(ev["preview"])
        r = client.post(f"/api/v1/agent/runs/{run_.run_id}/permission",
                        json={"request_id": ev["request_id"], "decision": "yes"}, headers=AUTH)
        assert r.status_code == 200
        assert next_event(run_, "done")["reason"] == "done"
        assert orchestrators[0].decision == PERMISSION_YES

    def test_bad_permission_answers(self, client, service, orchestrators):
        run_ = service.start("list files", model="small")
        ev = next_event(run_, "permission")
        url = f"/api/v1/agent/runs/{run_.run_id}/permission"
        assert client.post(url, json={"request_id": "x", "decision": "yes"}, headers=AUTH).status_code == 404
        assert client.post(url, json={"request_id": ev["request_id"], "decision": "maybe"},
                           headers=AUTH).status_code == 400
        client.post(url, json={"request_id": ev["request_id"], "decision": "no"}, headers=AUTH)
        next_event(run_, "done")
        assert orchestrators[0].decision == "n"

    def test_cancel_denies_a_pending_permission(self, client, service, orchestrators):
        run_ = service.start("list files", model="small")
        next_event(run_, "permission")
        assert client.post(f"/api/v1/agent/runs/{run_.run_id}/cancel", headers=AUTH).status_code == 200
        assert next_event(run_, "done")["reason"] == "cancelled"
        assert orchestrators[0].decision == "n"


class TestBusyAndCancel:
    def test_second_run_chat_and_unload_are_409_while_running(self, client, orchestrators):
        block = threading.Event()
        orchestrators.options = {"block": block}
        run_ = client.app.state.agent_service.start("work", model="small")
        assert run(client).status_code == 409
        chat = client.post("/api/v1/chat/completions", json={
            "model": "small", "messages": [{"role": "user", "content": "hi"}]})
        assert chat.status_code == 409 and "Agent run" in chat.json()["detail"]
        assert client.post("/api/v1/model/unload").status_code == 409
        block.set()
        run_.finished.wait(5)
        assert run(client).status_code == 200  # free again

    def test_cancel_endpoint_stops_the_run(self, client, orchestrators):
        block = threading.Event()
        orchestrators.options = {"block": block}
        run_ = client.app.state.agent_service.start("work", model="small")
        assert client.post(f"/api/v1/agent/runs/{run_.run_id}/cancel", headers=AUTH).status_code == 200
        block.set()
        assert next_event(run_, "done")["reason"] == "cancelled"

    def test_shutdown_cancels_the_run(self, client, orchestrators):
        block = threading.Event()
        orchestrators.options = {"block": block}
        client.app.state.shutdown_handler = MagicMock()
        run_ = client.app.state.agent_service.start("work", model="small")
        client.post("/api/v1/shutdown")
        block.set()
        assert next_event(run_, "done")["reason"] == "cancelled"

    def test_unknown_run_is_404(self, client):
        assert client.post("/api/v1/agent/runs/nope/cancel", headers=AUTH).status_code == 404


class TestTotpOverHttp:
    def test_off_by_default_even_with_a_secret(self, client, auth, orchestrators):
        auth.totp.setup()
        orchestrators.options = {"gated": True}
        run_ = client.app.state.agent_service.start("list files", model="small")
        ev = next_event(run_, "permission")
        assert ev["needs_totp"] is False
        client.post(f"/api/v1/agent/runs/{run_.run_id}/permission",
                    json={"request_id": ev["request_id"], "decision": "yes"})
        assert next_event(run_, "done")["reason"] == "done"

    def test_permission_event_flags_totp_and_wrong_code_is_401(self, client, auth, orchestrators, config):
        from ai.modules.server.services.totp import code_at
        secret = auth.totp.setup()
        enabled = config.get.side_effect
        config.get.side_effect = lambda key, default=None: True if key == ProgramSetting.SERVER_TOTP_ENABLED else enabled(key, default)
        orchestrators.options = {"gated": True}
        run_ = client.app.state.agent_service.start("list files", model="small")
        ev = next_event(run_, "permission")
        assert ev["needs_totp"] is True
        url = f"/api/v1/agent/runs/{run_.run_id}/permission"
        r = client.post(url, json={"request_id": ev["request_id"], "decision": "yes", "totp": "000000"})
        assert r.status_code == 401
        good = code_at(secret, int(auth.totp.clock()) // 30)
        r = client.post(url, json={"request_id": ev["request_id"], "decision": "yes", "totp": good})
        assert r.status_code == 200 and next_event(run_, "done")["reason"] == "done"
        assert orchestrators[0].decision == PERMISSION_YES


class TestCurrentRun:
    def test_no_run_is_inactive(self, client):
        assert client.get("/api/v1/agent/runs/current").json() == {"active": False}

    def test_running_run_with_pending_permission(self, client, orchestrators):
        orchestrators.options = {"gated": True}
        run_ = client.app.state.agent_service.start("list files", model="small", session_id="s9")
        ev = next_event(run_, "permission")
        info = client.get("/api/v1/agent/runs/current").json()
        assert info["active"] and info["run_id"] == run_.run_id and info["session_id"] == "s9"
        assert info["pipeline"] == "default" and info["started"] > 0
        assert info["pending_permissions"] == [{"request_id": ev["request_id"], "tool": "execute_command",
                                                "params": {"command": "ls"}, "needs_totp": False}]
        client.post(f"/api/v1/agent/runs/{run_.run_id}/cancel")
        run_.finished.wait(5)
        assert client.get("/api/v1/agent/runs/current").json() == {"active": False}

    def test_heartbeat_is_sent_while_a_step_is_slow(self, client, orchestrators, monkeypatch):
        import ai.modules.server.routers.agent as router_mod
        monkeypatch.setattr(router_mod, "HEARTBEAT_SECONDS", 0.5)
        block = threading.Event()
        orchestrators.options = {"block": block}
        threading.Timer(1.6, block.set).start()
        assert ": ping" in run(client).text
