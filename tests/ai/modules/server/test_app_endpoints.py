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
def app(hub, auth, tmp_path, monkeypatch):
    monkeypatch.setattr("ai.functions.get_root_directory", lambda: str(tmp_path))
    return create_app(hub, {}, auth=auth)


@pytest.fixture
def client(app, paired):
    """A paired client on localhost: protected routes get its Bearer token."""
    return TestClient(app, client=("127.0.0.1", 50000), headers=paired)


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


def png_data_url(color="red"):
    import base64
    import io
    from PIL import Image
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), color).save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


class TestImages:
    @pytest.fixture
    def vision(self, folders):
        import json
        (folders[1] / "eyes.json").write_text(json.dumps({
            "model_name": "Eyes", "model_type": "gguf",
            "model_properties": {"gguf_filename": "x.gguf", "mmproj_filename": "mmproj.gguf"}}))

    def message(self, images):
        return [{"role": "user", "content": "what colour?", "images": images}]

    def test_images_reach_a_vision_model_as_pil_images(self, client, loads, vision):
        r = chat(client, model="eyes", messages=self.message([png_data_url()]))
        assert r.status_code == 200
        (image,) = loads[0].images
        assert image.size == (4, 4) and image.getpixel((0, 0)) == (255, 0, 0)

    def test_model_without_vision_is_400(self, client, loads):
        r = chat(client, messages=self.message([png_data_url()]))
        assert r.status_code == 400 and "cannot read images" in r.json()["detail"]

    @pytest.mark.parametrize("images", [["http://x/a.png"], ["data:image/png;base64,@@"], [png_data_url()] * 5])
    def test_bad_images_are_422(self, client, vision, images):
        assert chat(client, model="eyes", messages=self.message(images)).status_code == 422

    def test_undecodable_image_is_400(self, client, vision):
        r = chat(client, model="eyes", messages=self.message(["data:image/png;base64,aGVsbG8="]))
        assert r.status_code == 400 and "Invalid image" in r.json()["detail"]

    def test_session_keeps_the_images(self, client, vision):
        url = png_data_url()
        chat(client, model="eyes", session_id="img", messages=self.message([url]))
        saved = client.get("/api/v1/sessions/img.json").json()
        assert saved["messages"][0]["images"] == [url] and "images" not in saved["messages"][1]

    def test_model_configs_report_vision(self, client, vision):
        configs = {c["key"]: c for c in client.get("/api/v1/model-configs").json()}
        assert configs["eyes"]["vision"] is True and configs["small"]["vision"] is False


class TestChatFolders:
    def test_model_configs_folder_query(self, client, loads, folders):
        import json
        (folders[1] / "chat").mkdir()
        (folders[1] / "chat" / "lite.json").write_text(json.dumps({"model_name": "Lite", "model_type": "gguf"}))
        keys = [c["key"] for c in client.get("/api/v1/model-configs", params={"folder": "chat"}).json()]
        assert keys == ["chat/lite"]

    def test_chat_with_a_folder_model_key(self, client, loads, folders):
        import json
        (folders[1] / "chat").mkdir()
        (folders[1] / "chat" / "lite.json").write_text(json.dumps({"model_name": "Lite", "model_type": "gguf"}))
        assert chat(client, model="chat/lite").status_code == 200


class TestModelInUse:
    def test_finished_chats_leave_the_model_free(self, client, hub, loads):
        assert chat(client).status_code == 200
        assert "data: [DONE]" in chat(client, stream=True).text
        assert not hub.busy

    def test_swap_with_fail_while_in_use_is_409(self, client, hub, loads):
        with hub.acquire("small", ""):
            response = chat(client, model="big", on_busy="fail")
        assert response.status_code == 409 and "in use" in response.json()["detail"]
        assert hub.current_model_id == "small" and loads[0].unloaded == 0

    def test_unknown_on_busy_is_422(self, client):
        assert chat(client, on_busy="maybe").status_code == 422

    def test_unload_while_a_chat_generates_is_409(self, client, hub, loads):
        with hub.acquire("small", ""):
            assert client.post("/api/v1/model/unload").status_code == 409
        assert loads[0].unloaded == 0


class TestGenerationDoesNotBlockTheServer:
    """A generation runs in a worker thread: the event loop keeps answering other requests."""

    @pytest.fixture(params=["text", "generator"])
    def slow_model(self, hub, request):
        """
        ``text``: chat(stream=False) returns the text (GGUF, Gemini, OpenAI, Ollama).
        ``generator``: chat() is a generator function whatever ``stream`` is, so all the work runs
        on the first next() (HuggingFace, T5).
        """
        import threading
        llm = hub.get_brain("small", "")
        release, started = threading.Event(), threading.Event()

        def tokens():
            started.set()
            release.wait(10)  # the model "generating"
            yield "done"

        def chat(messages, images=None, stream=True, options=None):
            if stream or request.param == "generator":
                return tokens()
            return "".join(tokens())

        llm.chat = chat
        return started, release

    @pytest.fixture
    def client(self, app, paired):
        # One event loop for every request, like uvicorn (without ``with``, each request gets its own).
        with TestClient(app, client=("127.0.0.1", 50000), headers=paired) as shared:
            yield shared

    @pytest.mark.parametrize("stream", [False, True])
    def test_health_answers_while_a_chat_generates(self, client, slow_model, stream):
        import threading
        started, release = slow_model
        result = {}
        chatting = threading.Thread(target=lambda: result.update(chat=chat(client, stream=stream)))
        chatting.start()
        try:
            assert started.wait(5)
            health = threading.Thread(target=lambda: result.update(health=client.get("/api/health")))
            health.start()
            health.join(5)
            assert not health.is_alive(), "health blocked by the generation"
            assert result["health"].status_code == 200
        finally:
            release.set()
            chatting.join(10)
        assert result["chat"].status_code == 200 and "done" in result["chat"].text

    def test_lease_is_released_after_a_generation(self, client, hub, slow_model):
        slow_model[1].set()
        assert chat(client).status_code == 200
        assert not hub.busy


class TestActionChunks:
    """An engine that caught a tool call returns a dict: clients get its tool call text, not a repr."""

    ACTION = {"type": "function_call", "name": "read_file", "args": {"path": "x"}}

    def test_non_stream_action_is_tool_call_text(self, client, hub):
        hub.get_brain("small", "").chat = lambda *a, **k: self.ACTION
        content = chat(client).json()["choices"][0]["message"]["content"]
        assert content == '____@read_file {"path": "x"}'

    def test_stream_action_is_tool_call_text(self, client, hub):
        hub.get_brain("small", "").chat = lambda *a, **k: iter(["Vou ler. ", self.ACTION])
        body = chat(client, stream=True).text
        assert '____@read_file {\\"path\\": \\"x\\"}' in body and "'type'" not in body


class TestClientGoneStopsTheGeneration:
    """A stream whose client went away stops its generation, unless other work shares the model."""

    def stream_then_drop(self, hub):
        import asyncio
        from ai.modules.server.services.chat import ChatResponseHandler
        llm = hub.orchestrator.llm

        def endless():
            while not llm.stop_generation_event.is_set():
                yield "token "

        llm.chat = lambda *a, **k: endless()
        lease = hub.acquire("small", "")

        async def run():
            response = await ChatResponseHandler(hub).stream_response([], lease=lease)
            body = response.body_iterator
            await body.__anext__()  # the client read one chunk...
            await body.aclose()     # ...then disconnected

        asyncio.run(run())
        return llm, lease

    def test_sole_user_stops(self, hub, fake_llm):
        import threading
        hub.get_brain("small", "")
        hub.orchestrator.llm.stop_generation_event = threading.Event()
        llm, lease = self.stream_then_drop(hub)
        assert llm.stop_generation_event.is_set() and lease.released and not hub.busy

    def test_shared_model_keeps_generating(self, hub):
        import threading
        hub.get_brain("small", "")
        hub.orchestrator.llm.stop_generation_event = threading.Event()
        other = hub.acquire("small", "")  # another chat on the same model
        try:
            llm, _ = self.stream_then_drop(hub)
            assert not llm.stop_generation_event.is_set()
        finally:
            other.release()

    def test_released_lease_does_not_stop(self, hub):
        import threading
        hub.get_brain("small", "")
        hub.orchestrator.llm.stop_generation_event = threading.Event()
        lease = hub.acquire("small", "")
        lease.release()
        assert hub.stop_generation_for(lease) is False
        assert not hub.orchestrator.llm.stop_generation_event.is_set()
