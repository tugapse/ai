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
        assert evs[-1] == {"type": "done", "reason": "done", "message": "all good", "seq": len(evs)}
        assert [e["seq"] for e in evs] == list(range(1, len(evs) + 1))
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
    """The next event of ``kind`` from a run's log, after the ones already read (earlier ones are skipped)."""
    import time
    deadline = time.time() + timeout
    while time.time() < deadline:
        after = getattr(run_, "_read", 0)
        events, closed = run_.events_after(after, 0.2)
        for ev in events:
            run_._read = ev["seq"]
            if ev["type"] == kind:
                return ev
        if closed and not events:
            raise AssertionError(f"run ended before a {kind!r} event")
    raise AssertionError(f"no {kind!r} event within {timeout}s")


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
        answered = next_event(run_, "permission_answered")
        assert answered["request_id"] == ev["request_id"] and answered["data"] == {"decision": "yes"}
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
        assert client.get("/api/v1/agent/runs/current").json() == {"active": False, "last": None}

    def test_running_run_with_pending_permission(self, client, orchestrators):
        orchestrators.options = {"gated": True}
        run_ = client.app.state.agent_service.start("list files", model="small", session_id="s9")
        ev = next_event(run_, "permission")
        info = client.get("/api/v1/agent/runs/current").json()
        assert info["active"] and info["run_id"] == run_.run_id and info["session_id"] == "s9"
        assert info["pipeline"] == "default" and info["started"] > 0
        assert info["cwd"] == os.path.realpath(client.app.state.agent_service.workspace_root()) and info["model"] == "small" and info["prompt"] == "list files"
        assert info["last_seq"] == ev["seq"]
        assert info["pending_permissions"] == [{"request_id": ev["request_id"], "tool": "execute_command",
                                                "params": {"command": "ls"}, "needs_totp": False}]
        client.post(f"/api/v1/agent/runs/{run_.run_id}/cancel")
        run_.finished.wait(5)
        info = client.get("/api/v1/agent/runs/current").json()
        assert info["active"] is False and info["last"]["run_id"] == run_.run_id
        assert info["last"]["session_id"] == "s9" and info["last"]["reason"] == "cancelled"
        assert info["last"]["finished"] >= info["last"]["started"] and info["last"]["last_seq"] == run_.last_seq

    def test_heartbeat_is_sent_while_a_step_is_slow(self, client, orchestrators, monkeypatch):
        import ai.modules.server.routers.agent as router_mod
        monkeypatch.setattr(router_mod, "HEARTBEAT_SECONDS", 0.5)
        block = threading.Event()
        orchestrators.options = {"block": block}
        threading.Timer(1.6, block.set).start()
        assert ": ping" in run(client).text


class TestWorkspace:
    def test_root(self, client, workdir):
        data = client.get("/api/v1/agent/workspace").json()
        assert data["default"] == data["root"] == os.path.realpath(workdir) and data["default_cwd"] == ""
        assert data["home"] == os.path.expanduser("~") and data["recent"] == []
        assert data["sep"] == os.sep and data["roots"] == ([os.sep] if os.name != "nt" else data["roots"])

    def test_list_folders_first_and_hides_dotfiles_and_links(self, client, workdir, tmp_path):
        workdir.mkdir(exist_ok=True)
        (workdir / "b.txt").write_text("12345")
        (workdir / "a-dir").mkdir()
        (workdir / ".hidden").write_text("x")
        os.symlink(tmp_path, workdir / "link")
        data = client.get("/api/v1/agent/workspace/list").json()
        assert data["path"] == ""
        assert [(e["name"], e["type"]) for e in data["entries"]] == [("a-dir", "dir"), ("b.txt", "file")]
        assert data["entries"][1]["size"] == 5 and "size" not in data["entries"][0]

    def test_list_subfolder_and_errors(self, client, workdir):
        (workdir / "p" / "q").mkdir(parents=True)
        assert client.get("/api/v1/agent/workspace/list", params={"path": "p"}).json()["path"] == "p"
        assert client.get("/api/v1/agent/workspace/list", params={"path": "nope"}).status_code == 404
        for bad in ("../", "/etc", "p/../../x"):
            assert client.get("/api/v1/agent/workspace/list", params={"path": bad}).status_code == 400

    def test_mkdir(self, client, workdir, auth):
        r = client.post("/api/v1/agent/workspace/mkdir", json={"path": "proj/new"})
        assert r.status_code == 201 and r.json() == {"path": "proj/new"}
        assert (workdir / "proj" / "new").is_dir()
        assert client.post("/api/v1/agent/workspace/mkdir", json={"path": "proj/new"}).status_code == 409
        assert client.post("/api/v1/agent/workspace/mkdir", json={"path": "../x"}).status_code == 400
        assert client.post("/api/v1/agent/workspace/mkdir", json={"path": " "}).status_code == 400
        assert "workspace_mkdir" in open(auth.audit_path).read()

    def test_needs_pairing(self, client):
        assert client.get("/api/v1/agent/workspace", headers={"Authorization": ""}).status_code == 401


class TestSessions:
    @pytest.fixture
    def storage(self, tmp_path, monkeypatch):
        from ai.agents.session_manager import AgentSessionManager
        root = tmp_path / "agent-logs"
        monkeypatch.setattr(AgentSessionManager, "_get_agents_storage_root", staticmethod(lambda: str(root)))
        return root

    def save(self, workdir, session_id, cwd=""):
        from ai.agents.session_manager import AgentSessionManager
        folder = workdir / cwd if cwd else workdir
        folder.mkdir(parents=True, exist_ok=True)
        state = {"user_request": "list files", "iteration": 1, "memory": {"agents": {"MASTER": {
            "history": [{"from": "USER", "message": "list files"}, {"from": "SELF", "response": "a.txt"}]}}}}
        AgentSessionManager(session_id, working_directory=os.path.realpath(folder)).commit(state)

    def test_lists_the_sessions_of_a_cwd(self, client, storage, workdir):
        self.save(workdir, "s1")
        self.save(workdir, "s2", cwd="proj")
        assert [s["session_id"] for s in client.get("/api/v1/agent/sessions").json()] == ["s1"]
        (only,) = client.get("/api/v1/agent/sessions", params={"cwd": "proj"}).json()
        assert only["session_id"] == "s2" and only["user_request"] == "list files"

    def test_empty_cwd_has_no_sessions(self, client, storage):
        assert client.get("/api/v1/agent/sessions", params={"cwd": "nothing"}).json() == []

    def test_reads_a_session_transcript(self, client, storage, workdir):
        self.save(workdir, "s1", cwd="proj")
        r = client.get("/api/v1/agent/sessions/s1", params={"cwd": "proj"})
        assert r.json() == {"session_id": "s1", "transcript": [
            {"role": "user", "agent": "MASTER", "text": "list files"},
            {"role": "agent", "agent": "MASTER", "text": "a.txt"}]}

    def test_unknown_session_is_404_and_creates_nothing(self, client, storage):
        assert client.get("/api/v1/agent/sessions/nope").status_code == 404
        assert not storage.exists()

    @pytest.mark.parametrize("cwd", ["../", "/etc"])
    def test_cwd_outside_the_workdir_is_400(self, client, storage, cwd):
        assert client.get("/api/v1/agent/sessions", params={"cwd": cwd}).status_code == 400

    def test_bad_session_id_is_400(self, client, storage):
        assert client.get("/api/v1/agent/sessions/.hidden").status_code == 400


class TestDetachedRuns:
    """A run outlives its stream: viewers attach and replay by seq; only /cancel stops it."""

    def test_closing_the_stream_does_not_cancel(self, client, orchestrators):
        block = threading.Event()
        orchestrators.options = {"block": block}
        with client.stream("POST", "/api/v1/agent/runs", json={"prompt": "x", "model": "small"}) as r:
            first = json.loads(next(l for l in r.iter_lines() if l.startswith("data: "))[6:])
        assert first["type"] == "run" and first["seq"] == 1
        run_ = client.app.state.agent_service.get(first["run_id"])
        block.set()
        assert next_event(run_, "done")["reason"] == "done"
        assert not orchestrators[0].cancelled.is_set()

    def test_events_replay_after_a_seq_and_close_when_finished(self, client, orchestrators):
        evs = events(run(client))
        run_id = evs[0]["run_id"]
        replay = events(client.get(f"/api/v1/agent/runs/{run_id}/events"))
        assert replay == evs
        tail = events(client.get(f"/api/v1/agent/runs/{run_id}/events", params={"after": 2}))
        assert tail == evs[2:]

    def test_viewer_attaches_to_a_live_run(self, client, orchestrators):
        block = threading.Event()
        orchestrators.options = {"block": block}
        run_ = client.app.state.agent_service.start("x", model="small")
        next_event(run_, "status")
        threading.Timer(0.3, block.set).start()
        evs = events(client.get(f"/api/v1/agent/runs/{run_.run_id}/events", params={"after": 1}))
        assert evs[0]["seq"] == 2 and evs[-1]["type"] == "done"

    def test_unknown_or_replaced_run_is_404(self, client, orchestrators):
        old = events(run(client))[0]["run_id"]
        events(run(client))
        assert client.get("/api/v1/agent/runs/nope/events").status_code == 404
        assert client.get(f"/api/v1/agent/runs/{old}/events").status_code == 404


def test_cancel_closes_pending_permissions_for_every_viewer(client, orchestrators):
    orchestrators.options = {"gated": True}
    run_ = client.app.state.agent_service.start("list files", model="small")
    ev = next_event(run_, "permission")
    client.post(f"/api/v1/agent/runs/{run_.run_id}/cancel")
    answered = next_event(run_, "permission_answered")
    assert answered["request_id"] == ev["request_id"] and answered["data"] == {"decision": "no", "cancelled": True}


class TestAnyFolder:
    """Runs may work in any absolute folder except the root, system folders and the server's data."""

    @pytest.fixture
    def storage(self, tmp_path, monkeypatch):
        from ai.agents.session_manager import AgentSessionManager
        root = tmp_path / "agent-logs"
        monkeypatch.setattr(AgentSessionManager, "_get_agents_storage_root", staticmethod(lambda: str(root)))
        return root

    @pytest.fixture
    def project(self, tmp_path):
        path = tmp_path / "elsewhere" / "proj"
        path.mkdir(parents=True)
        (path / "a.txt").write_text("hi")
        (path / ".env").write_text("x")
        return path

    def test_run_in_an_absolute_folder(self, client, orchestrators, project):
        evs = events(run(client, cwd=str(project)))
        assert evs[-1]["type"] == "done" and orchestrators[0].cwd == os.path.realpath(project)

    def test_relative_cwd_is_still_inside_the_default_workspace(self, client, orchestrators, workdir):
        events(run(client, cwd="sub"))
        assert orchestrators[0].cwd == os.path.realpath(workdir / "sub")

    @pytest.mark.parametrize("cwd", ["/", "/etc", "/usr/lib"])
    def test_root_and_system_folders_are_refused(self, client, cwd):
        r = run(client, cwd=cwd)
        assert r.status_code == 400

    def test_server_data_folder_is_refused(self, client, tmp_path, monkeypatch):
        from ai.services.directory_manager import DirectoryManager
        data = tmp_path / "data"
        data.mkdir()
        monkeypatch.setattr(DirectoryManager, "get_system_dir", lambda self: str(data))
        assert run(client, cwd=str(data)).status_code == 400

    def test_missing_folder_is_400(self, client, tmp_path):
        assert run(client, cwd=str(tmp_path / "nope")).status_code == 400

    def test_current_reports_the_absolute_cwd(self, client, orchestrators, project):
        events(run(client, cwd=str(project)))
        assert client.get("/api/v1/agent/runs/current").json()["last"]["cwd"] == os.path.realpath(project)

    def test_fs_list(self, client, project):
        data = client.get("/api/v1/agent/fs/list", params={"path": str(project)}).json()
        assert data["path"] == os.path.realpath(project) and data["parent"] == os.path.dirname(data["path"])
        assert [e["name"] for e in data["entries"]] == ["a.txt"]
        hidden = client.get("/api/v1/agent/fs/list", params={"path": str(project), "hidden": 1}).json()
        assert [e["name"] for e in hidden["entries"]] == [".env", "a.txt"]

    def test_fs_list_root_has_no_parent(self, client):
        assert client.get("/api/v1/agent/fs/list", params={"path": "/"}).json()["parent"] is None

    @pytest.mark.parametrize("path,status", [("relative", 400), ("/nope/at/all", 404)])
    def test_fs_list_errors(self, client, path, status):
        assert client.get("/api/v1/agent/fs/list", params={"path": path}).status_code == status

    def test_fs_list_a_file_is_400(self, client, project):
        assert client.get("/api/v1/agent/fs/list", params={"path": str(project / "a.txt")}).status_code == 400

    def test_fs_mkdir(self, client, project):
        r = client.post("/api/v1/agent/fs/mkdir", json={"path": str(project / "new" / "deep")})
        assert r.status_code == 201 and (project / "new" / "deep").is_dir()
        assert client.post("/api/v1/agent/fs/mkdir", json={"path": str(project / "new")}).status_code == 409
        assert client.post("/api/v1/agent/fs/mkdir", json={"path": "rel"}).status_code == 400

    def test_sessions_and_recent_by_absolute_folder(self, client, storage, project):
        from ai.agents.session_manager import AgentSessionManager
        AgentSessionManager("s1", working_directory=os.path.realpath(project)).commit({"user_request": "hi"})
        sessions = client.get("/api/v1/agent/sessions", params={"cwd": str(project)}).json()
        assert [s["session_id"] for s in sessions] == ["s1"]
        recent = client.get("/api/v1/agent/workspace").json()["recent"]
        assert [r["path"] for r in recent] == [os.path.realpath(project)]


def test_tilde_means_home(client, orchestrators, tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / "proj").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    listed = client.get("/api/v1/agent/fs/list", params={"path": "~"}).json()
    assert listed["path"] == os.path.realpath(home) and [e["name"] for e in listed["entries"]] == ["proj"]
    events(run(client, cwd="~/proj"))
    assert orchestrators[0].cwd == os.path.realpath(home / "proj")


class TestPipelineEditor:
    @pytest.fixture
    def dirs(self, tmp_path, monkeypatch, user_dirs):
        from ai.services.directory_manager import DirectoryManager
        system, prompts = tmp_path / "system-pipelines", tmp_path / "system-prompt"
        system.mkdir()
        (prompts / "agents").mkdir(parents=True)
        (prompts / "agents" / "default.md").write_text("You are the master.")
        (system / "sys.json").write_text(json.dumps(self.pipeline()))
        (system / ".sys.json.kate-swp").write_text("junk")
        monkeypatch.setattr(DirectoryManager, "get_system_pipelines_directory", lambda self: str(system))
        monkeypatch.setattr(DirectoryManager, "get_system_prompts_templates_directory", lambda self: str(prompts))
        return SimpleNamespace(user=tmp_path / "pipelines", system=system)

    @staticmethod
    def pipeline(**changes):
        data = {"name": "Sys", "description": "d", "entry_point": "MASTER", "max_iterations": 10,
                "agents": {"MASTER": {"role": "management", "prompt_file": "agents/default.md",
                                      "tools": ["read_file"], "allowed_targets": ["MASTER", "USER", "STOP"]}}}
        data.update(changes)
        return data

    def test_read(self, client, dirs):
        r = client.get("/api/v1/agent/pipelines/sys").json()
        assert r["source"] == "system" and r["content"]["entry_point"] == "MASTER"
        assert client.get("/api/v1/agent/pipelines/default").json()["source"] == "user"

    @pytest.mark.parametrize("name,status", [("nope", 404), (".sys.json.kate-swp", 400), ("a.b", 400)])
    def test_read_errors(self, client, dirs, name, status):
        assert client.get(f"/api/v1/agent/pipelines/{name}").status_code == status

    def test_save_keeps_extra_keys_in_its_own_folder(self, client, dirs):
        content = self.pipeline(description="new", custom={"x": 1})
        r = client.put("/api/v1/agent/pipelines/sys", json={"content": content})
        assert r.status_code == 200 and r.json()["source"] == "system"
        assert json.loads((dirs.system / "sys.json").read_text()) == content
        assert not (dirs.user / "sys.json").exists()

    def test_unknown_tool_is_a_warning(self, client, dirs):
        content = self.pipeline()
        content["agents"]["MASTER"]["tools"] = ["read_file", "made_up_tool"]
        r = client.put("/api/v1/agent/pipelines/sys", json={"content": content})
        assert r.status_code == 200 and any("made_up_tool" in w for w in r.json()["warnings"])

    @pytest.mark.parametrize("change,message", [
        ({"agents": {}}, "non-empty"),
        ({"entry_point": "NOBODY"}, "entry_point"),
        ({"max_iterations": 0}, "max_iterations"),
        ({"agents": {"MASTER": {"prompt_file": "agents/missing.md", "tools": []}}}, "doesn't exist"),
        ({"agents": {"MASTER": {"prompt_file": "../../etc/passwd", "tools": []}}}, "inside system-prompt"),
        ({"agents": {"MASTER": {"prompt_file": "agents/default.md", "tools": "read_file"}}}, "list of tool names"),
        ({"agents": {"MASTER": {"prompt_file": "agents/default.md", "allowed_targets": ["GHOST"]}}}, "GHOST"),
    ])
    def test_validation(self, client, dirs, change, message):
        r = client.put("/api/v1/agent/pipelines/sys", json={"content": self.pipeline(**change)})
        assert r.status_code == 400 and any(message in m for m in r.json()["detail"])
        assert json.loads((dirs.system / "sys.json").read_text()) == self.pipeline()

    def test_create_in_the_user_folder(self, client, dirs):
        r = client.post("/api/v1/agent/pipelines", json={"name": "mine", "content": self.pipeline()})
        assert r.status_code == 201 and r.json()["source"] == "user" and (dirs.user / "mine.json").is_file()
        assert "mine" in [p["name"] for p in client.get("/api/v1/agent/pipelines").json()]
        assert client.post("/api/v1/agent/pipelines", json={"name": "sys", "content": self.pipeline()}).status_code == 409

    def test_delete(self, client, dirs):
        assert client.delete("/api/v1/agent/pipelines/sys").status_code == 200 and not (dirs.system / "sys.json").exists()
        assert client.delete("/api/v1/agent/pipelines/default").status_code == 409
        assert client.delete("/api/v1/agent/pipelines/sys").status_code == 404

    def test_delete_refused_while_a_run_uses_it(self, client, dirs, orchestrators):
        block = threading.Event()
        orchestrators.options = {"block": block}
        client.app.state.agent_service.start("x", pipeline="sys", model="small")
        try:
            assert client.delete("/api/v1/agent/pipelines/sys").status_code == 409
        finally:
            block.set()

    def test_tools(self, client, monkeypatch):
        def read_file(**kwargs):
            """Reads a file.

            Args:
                path (str): the file
            """
        modules = SimpleNamespace(tool_functions=lambda: {"read_file": read_file, "execute_command": read_file})
        monkeypatch.setattr(client.app.state.agent_service, "modules", modules)
        tools = {t["name"]: t for t in client.get("/api/v1/agent/tools").json()}
        assert tools["read_file"]["needs_permission"] is False and "Reads a file" in tools["read_file"]["description"]
        assert tools["execute_command"]["needs_permission"] is True and tools["execute_command"]["needs_totp"] is False
