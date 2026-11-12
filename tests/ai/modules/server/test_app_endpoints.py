"""
Server endpoints for stats, unload, shutdown and per-request sampling settings.

The real app (create_app) and BrainHub run; only the engine is faked (see conftest).
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from ai.modules.server.app import create_app
from ai.modules.server.services.chat import ChatService


@pytest.fixture
def app(hub, tmp_path, monkeypatch):
    monkeypatch.setattr("ai.functions.get_root_directory", lambda: str(tmp_path))
    return create_app(hub, {})


@pytest.fixture
def client(app):
    return TestClient(app)


def chat(client, **fields):
    body = {"model": "small", "stream": False, "messages": [{"role": "user", "content": "hi"}]}
    body.update(fields)
    return client.post("/api/v1/chat/completions", json=body)


class TestStats:
    def test_no_model_is_inactive(self, client):
        assert client.get("/api/v1/stats").json() == {"active": False}

    def test_loaded_model_reports_its_counts(self, client, hub):
        hub.get_brain("small", "")
        stats = client.get("/api/v1/stats").json()
        assert stats["active"] is True and stats["model"] == "small"
        assert stats["window"] == 1000 and stats["prompt_tokens"] == 250 and stats["usage_percent"] == 25.0


class TestUnload:
    def test_unload_frees_the_model_and_health_shows_it(self, client, hub, loads):
        hub.get_brain("small", "")
        assert client.post("/api/v1/model/unload").json() == {"status": "unloaded", "model": "small"}
        assert loads[0].unloaded == 1
        health = client.get("/api/health").json()
        assert health["loaded"] is False and health["model"] == "JARVIS"

    def test_unload_without_a_model(self, client):
        assert client.post("/api/v1/model/unload").json() == {"status": "unloaded", "model": None}

    def test_next_chat_loads_the_model_again(self, client, hub, loads):
        hub.get_brain("small", "")
        client.post("/api/v1/model/unload")
        assert chat(client).status_code == 200 and len(loads) == 2


class TestShutdown:
    def test_calls_the_server_handler_after_replying(self, client, app):
        app.state.shutdown_handler = MagicMock()
        response = client.post("/api/v1/shutdown")
        assert response.json() == {"status": "shutting_down"}
        app.state.shutdown_handler.assert_called_once()

    def test_without_a_server_module_is_501(self, client):
        assert client.post("/api/v1/shutdown").status_code == 501


class TestGenerationSettings:
    def test_fields_reach_the_engine_as_options(self, client, loads):
        assert chat(client, temperature=0.2, top_p=0.9, top_k=20, max_tokens=64).status_code == 200
        assert loads[0].chats[-1][2] == {"temperature": 0.2, "top_p": 0.9, "top_k": 20,
                                         "max_tokens": 64, "max_new_tokens": 64}

    def test_missing_fields_keep_the_config_values(self, client, loads):
        # Before, temperature defaulted to 0.7 in the schema (and was then ignored).
        chat(client)
        assert loads[0].chats[-1][2] == {}

    def test_streaming_passes_them_too(self, client, loads):
        response = chat(client, stream=True, temperature=0.0)
        assert "data: [DONE]" in response.text
        assert loads[0].chats[-1][1:] == (True, {"temperature": 0.0})

    @pytest.mark.parametrize("field,value", [("temperature", 3), ("top_p", 0), ("top_k", -1), ("max_tokens", 0)])
    def test_out_of_range_is_422(self, client, field, value):
        assert chat(client, **{field: value}).status_code == 422

    def test_options_builder_ignores_unset_fields(self):
        request = MagicMock(temperature=None, top_p=None, top_k=None, max_tokens=None)
        assert ChatService.generation_options(request) == {}


class TestSessionMemory:
    def test_chat_stores_model_and_system_prompt_in_the_session(self, client):
        chat(client, session_id="s1", system_prompt_content="Be brief.", session_title="T")
        session = client.get("/api/v1/sessions/s1.json").json()
        assert session["model"] == "small" and session["system_prompt"] == "Be brief."
        assert [m["role"] for m in session["messages"]] == ["user", "assistant"]


class TestSessionContentUpdate:
    @pytest.fixture
    def session(self, client):
        chat(client, session_id="s1", session_title="Title")
        return "/api/v1/sessions/s1.json"

    def test_message_list_replaces_only_the_messages(self, client, session):
        # Before, a bare list became the whole file: the title was lost and listing skipped it.
        r = client.put(session, json={"session_content": [{"role": "user", "content": "x"}]})
        assert r.status_code == 200
        saved = client.get(session).json()
        assert saved["messages"] == [{"role": "user", "content": "x"}]
        assert saved["session_title"] == "Title" and saved["model"] == "small"

    def test_session_object_replaces_the_file(self, client, session):
        whole = client.get(session).json()
        whole["messages"] = whole["messages"][:1]
        assert client.put(session, json={"session_content": whole}).status_code == 200
        assert client.get(session).json() == whole

    @pytest.mark.parametrize("content", [{"no": "messages"}, "text", [{"role": "user"}]])
    def test_bad_content_is_400(self, client, session, content):
        assert client.put(session, json={"session_content": content}).status_code == 400

    def test_title_route_still_works(self, client, session):
        assert client.put(f"{session}/title", json={"session_title": "New"}).status_code == 200
        assert client.get(session).json()["session_title"] == "New"
