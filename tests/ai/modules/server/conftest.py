"""
Shared server fixtures: a real BrainHub and ModelOrchestrator with only the engine
(EngineManager.load_model_instance) and the model config folders faked, so no model is loaded.
"""

import json
from unittest.mock import MagicMock

import pytest

import ai.program  # noqa: F401  (startup import order, avoids a circular import)
from ai.core.llms.base_llm import TokenCountInfo
from ai.modules.server.brain_hub import BrainHub
from ai.services.engine_manager import EngineManager
from ai.services.model_orchestrator import ModelOrchestrator


class FakeLLM:
    def __init__(self, name, system_prompt):
        self.model_name, self.system_prompt = name, system_prompt
        self.unloaded = 0
        self.chats = []  # (messages, stream, options) per chat call
        self.token_info_count = TokenCountInfo()
        self.token_info_count.max_context_window = 1000
        self.token_info_count.prompt_count = 250

    def chat(self, messages, images=None, stream=True, options=None):
        self.chats.append((messages, stream, options))
        self.images = images
        return iter(["he", "llo"]) if stream else "hello"

    def unload(self):
        self.unloaded += 1


class Loads(list):
    """Every engine load, in order. Set ``fail`` to make the next loads raise it."""
    fail = None


def _write_config(folder, key, model_type="gguf"):
    path = folder / f"{key}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"model_name": f"Display {key}", "model_type": model_type, "model_properties": {}}))
    return path


@pytest.fixture
def folders(tmp_path, monkeypatch):
    """(user, system) model folders; the real lookup and listing run against them."""
    user, system = tmp_path / "user", tmp_path / "system"
    user.mkdir(), system.mkdir()
    monkeypatch.setattr(ModelOrchestrator, "config_folders", staticmethod(lambda: [str(user), str(system)]))
    return user, system


@pytest.fixture
def loads(folders, monkeypatch):
    for name in ("small", "big"):
        _write_config(folders[1], name)

    record = Loads()

    def load_model_instance(model_config, system_prompt, tool_registry):
        if record.fail:
            raise record.fail
        llm = FakeLLM(model_config["model_name"], system_prompt)
        llm.supports_vision = BrainHub.has_vision(model_config)
        record.append(llm)
        return llm

    monkeypatch.setattr(EngineManager, "load_model_instance", staticmethod(load_model_instance))
    return record


@pytest.fixture
def hub(loads):
    return BrainHub(MagicMock())


@pytest.fixture
def write_config():
    """write_config(folder, key, model_type="gguf") -> path of a new config file."""
    return _write_config


@pytest.fixture
def fake_llm():
    """The FakeLLM class, to put a model in the hub without the engine."""
    return FakeLLM


LOCAL = ("127.0.0.1", 50000)


@pytest.fixture
def auth(tmp_path):
    """A real AuthService with its device file and audit log in tmp_path."""
    from ai.modules.server.services.auth import AuthService
    return AuthService(None, devices_path=str(tmp_path / "devices.json"), audit_path=str(tmp_path / "audit.log"))


@pytest.fixture
def paired(auth):
    """Headers of a paired CLI-style device (Bearer token)."""
    pairing = auth.start_pairing("tests", LOCAL[0])
    code = auth.pairings[pairing["pairing_id"]]["code"]
    token, _ = auth.finish_pairing(pairing["pairing_id"], code, LOCAL[0])
    return {"Authorization": f"Bearer {token}"}
