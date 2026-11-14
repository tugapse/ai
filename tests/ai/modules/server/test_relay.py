"""
Relay mode: a local server (website, agent runs, tools) whose model inference goes to a
remote Brain Server through a generated ``jarvis`` client config.
"""

import pytest

from ai.modules.server.relay import is_self_relay, normalize_relay_url
from ai.modules.server.brain_hub import BrainHub
from ai.modules.server.exceptions import ModelNotFoundError
from ai.services.engine_manager import EngineManager

RELAY = "http://brain:9999"

REMOTE_CONFIGS = [
    {"key": "agents/gemma4-gguf", "model_name": "gemma", "model_type": "gguf", "loadable": True,
     "vision": True, "n_ctx": 30000, "max_new_tokens": 12096},
    {"key": "small", "model_name": "small", "model_type": "gguf", "loadable": True, "vision": False,
     "n_ctx": None, "max_new_tokens": None},
    {"key": "jarvis-remote", "model_name": "default", "model_type": "jarvis", "loadable": False, "vision": False},
]


@pytest.fixture
def remote(monkeypatch):
    """Fakes the Brain Server: ``remote.configs`` is its model list, ``remote.calls`` the paths asked."""
    class Remote:
        configs = list(REMOTE_CONFIGS)
        calls = []
        fail = None

    def relay_get(self, path, params=None):
        Remote.calls.append(path)
        if Remote.fail:
            raise Remote.fail
        if path == "/api/v1/model-configs":
            return Remote.configs
        if path == "/api/health":
            return {"status": "online", "model": "small", "available": ["small"], "api_level": 1}
        raise AssertionError(path)

    Remote.calls = []
    monkeypatch.setattr(BrainHub, "_relay_get", relay_get)
    return Remote


@pytest.fixture
def configs_loaded(loads, monkeypatch):
    """The model configs the engine was asked to load, in order (the engine stays faked)."""
    seen = []
    original = EngineManager.load_model_instance

    def capture(model_config, system_prompt, tool_registry):
        seen.append(model_config)
        return original(model_config, system_prompt, tool_registry)

    monkeypatch.setattr(EngineManager, "load_model_instance", staticmethod(capture))
    return seen


@pytest.fixture
def relay_hub(loads, remote):
    from unittest.mock import MagicMock
    return BrainHub(MagicMock(), relay_url=RELAY + "/")


class TestListing:
    def test_lists_the_brain_server_models_not_the_local_ones(self, relay_hub):
        keys = [c["key"] for c in relay_hub.list_model_configs()]
        assert keys == ["agents/gemma4-gguf", "small", "jarvis-remote"]
        assert relay_hub.list_available_models() == ["agents/gemma4-gguf", "small"]

    def test_vision_and_window_come_from_the_brain_server(self, relay_hub):
        gemma, small = relay_hub.list_model_configs()[:2]
        assert gemma["vision"] is True and gemma["n_ctx"] == 30000
        assert small["vision"] is False

    def test_folder_filter(self, relay_hub):
        assert [c["key"] for c in relay_hub.list_model_configs("agents")] == ["agents/gemma4-gguf"]

    def test_list_is_cached(self, relay_hub, remote):
        relay_hub.list_model_configs()
        relay_hub.list_model_configs()
        assert remote.calls.count("/api/v1/model-configs") == 1

    def test_unreachable_brain_server_gives_an_empty_list(self, relay_hub, remote):
        remote.fail = ConnectionError("refused")
        assert relay_hub.list_model_configs() == []
        assert relay_hub.list_available_models() == []

    def test_local_listing_reports_the_window(self, hub, folders):
        entry = next(c for c in hub.list_model_configs() if c["key"] == "small")
        assert "n_ctx" in entry and "max_new_tokens" in entry


class TestLoading:
    def test_loads_a_jarvis_client_to_the_brain_server(self, relay_hub, configs_loaded):
        relay_hub.get_brain("agents/gemma4-gguf", "sys", on_busy="fail")
        config = configs_loaded[-1]
        assert config["model_type"] == "jarvis"
        assert config["model_properties"] == {
            "base_url": RELAY, "server_model": "agents/gemma4-gguf", "on_busy": "fail",
            "session_folder": "relay", "vision": True, "n_ctx": 30000, "max_new_tokens": 12096}
        assert relay_hub.current_model_id == "agents/gemma4-gguf"

    def test_missing_window_is_left_to_the_client_default(self, relay_hub, configs_loaded):
        relay_hub.get_brain("small", "")
        assert "n_ctx" not in configs_loaded[-1]["model_properties"]

    def test_unknown_model_is_not_found(self, relay_hub, loads):
        with pytest.raises(ModelNotFoundError, match="Available: agents/gemma4-gguf, small"):
            relay_hub.get_brain("nope", "")
        assert loads == []

    def test_remote_jarvis_config_is_not_relayed(self, relay_hub, loads):
        with pytest.raises(ModelNotFoundError):
            relay_hub.get_brain("jarvis-remote", "")

    def test_reuse_updates_the_busy_policy(self, relay_hub, loads):
        llm = relay_hub.get_brain("small", "")
        relay_hub.get_brain("small", "", on_busy="force")
        assert len(loads) == 1 and llm.on_busy == "force"

    def test_model_added_on_the_brain_server_is_found(self, relay_hub, remote, loads):
        relay_hub.list_model_configs()
        remote.configs = REMOTE_CONFIGS + [{"key": "new", "model_type": "gguf", "loadable": True}]
        relay_hub.get_brain("new", "")
        assert relay_hub.current_model_id == "new"

    def test_unreachable_listing_still_relays_and_lets_the_brain_server_decide(self, relay_hub, remote, configs_loaded):
        remote.fail = TimeoutError("timed out")  # e.g. the Brain Server is busy generating
        relay_hub.get_brain("agents/gemma4-gguf", "")
        assert configs_loaded[-1]["model_properties"]["server_model"] == "agents/gemma4-gguf"

    def test_health_comes_from_the_brain_server(self, relay_hub):
        assert relay_hub.relay_health()["status"] == "online"


def test_engine_passes_the_window_and_vision_to_the_jarvis_client():
    llm = EngineManager.load_model_instance(
        {"model_name": "x", "model_type": "jarvis",
         "model_properties": {"base_url": RELAY, "server_model": "x", "n_ctx": 30000, "vision": False}}, "", None)
    assert llm.token_info_count.max_context_window == 30000
    assert llm.endpoint == f"{RELAY}/api/v1/chat/completions"
    assert llm.supports_vision is False


class TestRelayedImages:
    """Web chat on a relay: images reach the Brain Server, or are refused like on a local model."""

    @pytest.fixture
    def sent(self, monkeypatch):
        """The payloads the jarvis client would POST to the Brain Server (the real engine builds it)."""
        from ai.core.llms.jarvis import JarvisAiModel
        payloads = []
        monkeypatch.setattr(EngineManager, "load_model_instance", staticmethod(
            lambda model_config, system_prompt, tool_registry: JarvisAiModel(
                system_prompt=system_prompt, model_name=model_config["model_name"],
                **model_config["model_properties"])))
        monkeypatch.setattr(JarvisAiModel, "_run_sync_chat", lambda self, payload: payloads.append(payload) or "ok")
        return payloads

    @pytest.fixture
    def client(self, relay_hub, auth, tmp_path, monkeypatch):
        from fastapi.testclient import TestClient
        from ai.modules.server.app import create_app
        monkeypatch.setattr("ai.functions.get_root_directory", lambda: str(tmp_path))
        return TestClient(create_app(relay_hub, {}, auth=auth))

    @staticmethod
    def chat(client, model):
        import base64, io
        from PIL import Image
        buffer = io.BytesIO()
        Image.new("RGB", (4, 4), (255, 0, 0)).save(buffer, format="PNG")
        url = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
        return client.post("/api/v1/chat/completions", json={
            "model": model, "stream": False,
            "messages": [{"role": "user", "content": "what colour?", "images": [url]}]})

    def test_vision_model_gets_the_image(self, client, sent):
        assert self.chat(client, "agents/gemma4-gguf").status_code == 200
        (image,) = sent[0]["messages"][-1]["images"]
        assert image.startswith("data:image/png;base64,")

    def test_model_without_vision_is_refused_locally(self, client, sent):
        r = self.chat(client, "small")
        assert r.status_code == 400 and "cannot read images" in r.json()["detail"] and sent == []


class TestCli:
    @pytest.mark.parametrize("url, expected", [
        (None, None), ("", None), ("brain:9999/", "http://brain:9999"),
        ("https://brain.lan/", "https://brain.lan")])
    def test_normalize(self, url, expected):
        assert normalize_relay_url(url) == expected

    @pytest.mark.parametrize("url", ["http://127.0.0.1:9999", "http://localhost:9999", "http://0.0.0.0:9999"])
    def test_self_relay_is_detected(self, url):
        assert is_self_relay(url, "0.0.0.0", 9999)

    @pytest.mark.parametrize("url", ["http://127.0.0.1:8000", "http://brain.example.invalid:9999"])
    def test_other_servers_are_allowed(self, url):
        assert not is_self_relay(url, "0.0.0.0", 9999)


def test_relayed_chat_forwards_the_request_sampling_settings(relay_hub, auth, tmp_path, monkeypatch):
    """Web sliders on a relay: the Brain Server gets this request's settings."""
    from fastapi.testclient import TestClient
    from ai.core.llms.jarvis import JarvisAiModel
    from ai.modules.server.app import create_app
    sent = []
    monkeypatch.setattr(EngineManager, "load_model_instance", staticmethod(
        lambda model_config, system_prompt, tool_registry: JarvisAiModel(
            system_prompt=system_prompt, model_name=model_config["model_name"], **model_config["model_properties"])))
    monkeypatch.setattr(JarvisAiModel, "_run_sync_chat", lambda self, payload: sent.append(payload) or "ok")
    monkeypatch.setattr("ai.functions.get_root_directory", lambda: str(tmp_path))
    r = TestClient(create_app(relay_hub, {}, auth=auth)).post("/api/v1/chat/completions", json={
        "model": "small", "stream": False, "temperature": 0.2, "max_tokens": 50,
        "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 200
    assert sent[0]["temperature"] == 0.2 and sent[0]["max_tokens"] == 50 and "top_p" not in sent[0]
