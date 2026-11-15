import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai.modules.knowledge.knowledge_module import KnowledgeModule
from ai.modules.server.routers.auth import require_device
from ai.modules.server.routers.knowledge import router

COMPONENT = {
    "component": {"name": "main", "source_path": "/app/main.py", "type": "module"},
    "vector_memory": {"semantic_summary": "Boots the web server and registers routes."},
}


@pytest.fixture
def client(tmp_path):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[require_device] = lambda: {"device_id": "test", "name": "test"}
    module = KnowledgeModule()
    app.state.modules = {"knowledge": module}
    app.state.config = {"SERVER_AGENT_WORKDIR": str(tmp_path)}
    return TestClient(app)


def test_ingest_search_and_remove(client):
    res = client.post("/api/v1/knowledge/sources", json={"id": "fed", "documents": [
        COMPONENT, {"path": "app/main.md", "content": "## Startup\nThe web server listens on port 8080."}]})
    assert res.status_code == 201 and res.json()["components"] == 1 and res.json()["docs"] == 1

    sources = client.get("/api/v1/knowledge/sources").json()["sources"]
    assert sources[0]["id"] == "fed"

    hits = client.get("/api/v1/knowledge/search", params={"q": "web server port"}).json()["results"]
    assert hits[0]["path"] == "app/main.py"
    assert hits[0]["sections"][0]["heading"] == "Startup"

    assert client.get("/api/v1/knowledge/component", params={"path": "src/app/main.py"}).json()["name"] == "main"
    assert client.get("/api/v1/knowledge/component", params={"path": "nope.py"}).status_code == 404

    assert client.delete("/api/v1/knowledge/sources/fed").status_code == 200
    assert client.delete("/api/v1/knowledge/sources/fed").status_code == 404


def test_add_folder_relative_to_workdir(client, tmp_path):
    (tmp_path / "kb").mkdir()
    (tmp_path / "kb" / "guide.md").write_text("## Setup\nInstall the dependencies first.")
    res = client.post("/api/v1/knowledge/sources", json={"path": "kb"})
    assert res.status_code == 201 and res.json()["docs"] == 1
    assert client.post("/api/v1/knowledge/sources", json={"path": "missing"}).status_code == 404
    assert client.post("/api/v1/knowledge/sources", json={"documents": []}).status_code == 400


def test_disabled_module(tmp_path):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[require_device] = lambda: {}
    app.state.modules = {}
    assert TestClient(app).get("/api/v1/knowledge/sources").status_code == 503


class FakeHub:
    def __init__(self):
        import threading
        from types import SimpleNamespace
        self._lock = threading.RLock()
        self.orchestrator = SimpleNamespace(llm=object())
        self.agent_running = False
        self.knowledge_building = False


def test_build_job_runs_in_background(tmp_path, monkeypatch):
    import time
    import ai.modules.knowledge.builder as builder_mod
    from ai.modules.knowledge.registry import KnowledgeRegistry

    project = tmp_path / "proj"
    (project / "src" / "app").mkdir(parents=True)
    (project / "src" / "app" / "main.py").write_text("def main():\n    return 1\n")

    def fake_call(model):
        def call(messages, system):
            context = messages[3]["content"]
            if ".json" in context.split("\n", 1)[0]:
                return '{"component": {"name": "main", "source_path": "/app/main.py"}, "vector_memory": {"semantic_summary": "Entry point."}}'
            return "## Overview\n" + "The main module starts the application and returns one. " * 3
        return call

    monkeypatch.setattr(builder_mod, "default_llm_call", fake_call)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[require_device] = lambda: {}
    module = KnowledgeModule(registry=KnowledgeRegistry(str(tmp_path / "reg.json")),
                             config={"KNOWLEDGE_OUTPUT_DIR": str(tmp_path / "kb")})
    hub = FakeHub()
    agents = type("Agents", (), {"busy": False, "resolve_cwd": staticmethod(lambda cwd: cwd)})()
    app.state.modules = {"knowledge": module}
    app.state.brain_hub = hub
    app.state.agent_service = agents
    client = TestClient(app)

    assert client.get("/api/v1/knowledge/status", params={"cwd": str(project)}).json()["docs"]["missing"] == 1
    job = client.post("/api/v1/knowledge/build", json={"cwd": str(project)}).json()
    for _ in range(100):
        info = client.get(f"/api/v1/knowledge/build/{job['job_id']}").json()
        if info["state"] != "running":
            break
        time.sleep(0.02)
    assert info["state"] == "done" and info["report"]["done"] == ["app/main.py"]
    assert hub.agent_running is False and hub.knowledge_building is False
    assert module.get_instance().get_component("app/main.py")["summary"] == "Entry point."
    assert client.get("/api/v1/knowledge/build/nope").status_code == 404

    agents.busy = True
    assert client.post("/api/v1/knowledge/build", json={"cwd": str(project)}).status_code == 409
