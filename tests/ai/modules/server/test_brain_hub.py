"""
BrainHub model swapping: the server loads the model a request names and swaps it safely.

The real ModelOrchestrator runs; only the engine (EngineManager.load_model_instance) and the
config folder are faked, so no model is loaded.
"""

import json
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

import ai.program  # noqa: F401  (startup import order, avoids a circular import)
from ai.modules.server.brain_hub import BrainHub
from ai.modules.server.exceptions import ModelLoadError, ModelNotFoundError
from ai.modules.server.services.chat import ChatService
from ai.services.engine_manager import EngineManager
from ai.services.model_orchestrator import ModelOrchestrator


class FakeLLM:
    def __init__(self, name, system_prompt):
        self.model_name, self.system_prompt = name, system_prompt
        self.unloaded = 0

    def unload(self):
        self.unloaded += 1


class Loads(list):
    """Every engine load, in order. Set ``fail`` to make the next loads raise it."""
    fail = None


def write_config(folder, key, model_type="gguf"):
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
        write_config(folders[1], name)

    record = Loads()

    def load_model_instance(model_config, system_prompt, tool_registry):
        if record.fail:
            raise record.fail
        llm = FakeLLM(model_config["model_name"], system_prompt)
        record.append(llm)
        return llm

    monkeypatch.setattr(EngineManager, "load_model_instance", staticmethod(load_model_instance))
    return record


@pytest.fixture
def hub(loads):
    return BrainHub(MagicMock())


class TestSwap:
    def test_first_request_loads_and_remembers_the_model(self, hub, loads):
        llm = hub.get_brain("small", "sys")
        assert llm is loads[0] and hub.current_model_id == "small"

    def test_same_model_is_reused_and_prompt_updated(self, hub, loads):
        hub.get_brain("small", "one")
        llm = hub.get_brain("small", "two")
        assert len(loads) == 1 and llm.system_prompt == "two"

    def test_name_is_normalised(self, hub, loads):
        hub.get_brain("small", "")
        hub.get_brain(" Small.json ", "")
        assert len(loads) == 1

    def test_different_model_unloads_the_old_one_first(self, hub, loads):
        small = hub.get_brain("small", "")
        big = hub.get_brain("big", "")
        assert small.unloaded == 1 and big is loads[1]
        assert hub.current_model_id == "big" and hub.orchestrator.llm is big

    def test_model_loaded_outside_the_hub_is_swapped(self, hub, loads):
        # Before the fix, a model loaded at startup (--model) left current_model_id None and
        # every request kept using it whatever model it asked for.
        hub.orchestrator.llm = FakeLLM("startup", "")
        big = hub.get_brain("big", "")
        assert big is loads[0] and hub.current_model_id == "big"


class TestFailures:
    def test_unknown_model_keeps_the_current_model(self, hub, loads):
        small = hub.get_brain("small", "")
        with pytest.raises(ModelNotFoundError, match="Available: big, small"):
            hub.get_brain("nope", "")
        assert small.unloaded == 0 and hub.orchestrator.llm is small and hub.current_model_id == "small"

    def test_failed_load_leaves_the_hub_empty_and_recoverable(self, hub, loads):
        small = hub.get_brain("small", "")
        loads.fail = RuntimeError("out of VRAM")
        with pytest.raises(ModelLoadError, match="out of VRAM"):
            hub.get_brain("big", "")
        assert small.unloaded == 1
        assert hub.orchestrator.llm is None and hub.current_model_id is None
        loads.fail = None
        assert hub.get_brain("small", "") is loads[-1]

    def test_unload_error_still_clears_the_state(self, hub, loads):
        small = hub.get_brain("small", "")
        small.unload = MagicMock(side_effect=AttributeError("'NoneType' object has no attribute 'is_alive'"))
        hub.unload_brain()
        assert hub.orchestrator.llm is None and hub.current_model_id is None
        assert hub.get_brain("big", "") is loads[-1]

    def test_jarvis_client_config_is_refused(self, hub, loads, folders):
        write_config(folders[1], "client", "jarvis")
        small = hub.get_brain("small", "")
        with pytest.raises(ModelLoadError, match="Jarvis client config"):
            hub.get_brain("client", "")
        assert hub.orchestrator.llm is small and small.unloaded == 0

    def test_unload_without_a_model_is_a_no_op(self, hub, loads):
        hub.unload_brain()
        assert hub.current_model_id is None


class TestNestedConfigs:
    def test_config_in_a_subfolder_loads_by_its_path_key(self, hub, loads, folders):
        write_config(folders[1], "agents/lite")
        llm = hub.get_brain("agents/lite", "")
        assert llm.model_name == "Display agents/lite" and hub.current_model_id == "agents/lite"

    def test_same_file_name_in_two_folders_are_two_models(self, hub, loads, folders):
        write_config(folders[1], "agents/flash")
        write_config(folders[1], "other/gemini/flash")
        assert hub.get_brain("other/gemini/flash", "").model_name == "Display other/gemini/flash"
        assert hub.get_brain("agents/flash", "").model_name == "Display agents/flash"

    def test_user_config_hides_the_system_one(self, hub, loads, folders):
        (folders[0] / "small.json").write_text(json.dumps({"model_name": "Mine", "model_type": "gguf"}))
        assert hub.get_brain("small", "").model_name == "Mine"
        assert hub.list_available_models().count("small") == 1

    @pytest.mark.parametrize("name", ["../system/small", "agents/../../system/small", "/etc/passwd"])
    def test_names_outside_the_models_folders_are_not_found(self, hub, loads, name):
        with pytest.raises(ModelNotFoundError):
            hub.get_brain(name, "")


class TestListing:
    def test_available_lists_nested_loadable_configs_only(self, hub, loads, folders):
        write_config(folders[1], "agents/lite")
        write_config(folders[1], "default", "jarvis")
        (folders[1] / "broken.json").write_text("{not json")
        assert hub.list_available_models() == ["agents/lite", "big", "small"]

    def test_model_configs_lists_everything_with_loadable_flag(self, hub, loads, folders):
        write_config(folders[1], "default", "jarvis")
        (folders[1] / "broken.json").write_text("{not json")
        configs = {c["key"]: c for c in hub.list_model_configs()}
        assert configs["small"] == {"key": "small", "model_name": "Display small",
                                    "model_type": "gguf", "loadable": True}
        assert configs["default"]["loadable"] is False and configs["default"]["model_type"] == "jarvis"
        assert configs["broken"]["loadable"] is False and "error" in configs["broken"]


class TestChatServiceErrors:
    def request(self, model):
        return MagicMock(model=model, system_prompt_content="", model_config_data=None)

    def test_unknown_model_is_404(self, hub, loads):
        service = ChatService(hub, "/tmp", {})
        with pytest.raises(HTTPException) as info:
            service._resolve_brain(self.request("nope"))
        assert info.value.status_code == 404

    def test_load_failure_is_500(self, hub, loads):
        loads.fail = RuntimeError("boom")
        service = ChatService(hub, "/tmp", {})
        with pytest.raises(HTTPException) as info:
            service._resolve_brain(self.request("small"))
        assert info.value.status_code == 500 and "boom" in info.value.detail
