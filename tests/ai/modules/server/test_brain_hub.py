"""
BrainHub model swapping: the server loads the model a request names and swaps it safely.

The real ModelOrchestrator runs; only the engine (EngineManager.load_model_instance) and the
config folder are faked, so no model is loaded.
"""

import gc
import json
import threading
import time
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from ai.modules.server.brain_hub import BrainHub
from ai.modules.server.exceptions import ModelBusyError, ModelLoadError, ModelNotFoundError
from ai.modules.server.services.chat import ChatService
from ai.services.process_manager import ProcessManager


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

    def test_model_loaded_outside_the_hub_is_swapped(self, hub, loads, fake_llm):
        # Before the fix, a model loaded at startup (--model) left current_model_id None and
        # every request kept using it whatever model it asked for.
        hub.orchestrator.llm = fake_llm("startup", "")
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

    def test_jarvis_client_config_is_refused(self, hub, loads, folders, write_config):
        write_config(folders[1], "client", "jarvis")
        small = hub.get_brain("small", "")
        with pytest.raises(ModelLoadError, match="Jarvis client config"):
            hub.get_brain("client", "")
        assert hub.orchestrator.llm is small and small.unloaded == 0

    def test_unload_without_a_model_is_a_no_op(self, hub, loads):
        hub.unload_brain()
        assert hub.current_model_id is None


class TestNestedConfigs:
    def test_config_in_a_subfolder_loads_by_its_path_key(self, hub, loads, folders, write_config):
        write_config(folders[1], "agents/lite")
        llm = hub.get_brain("agents/lite", "")
        assert llm.model_name == "Display agents/lite" and hub.current_model_id == "agents/lite"

    def test_same_file_name_in_two_folders_are_two_models(self, hub, loads, folders, write_config):
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
    def test_available_lists_nested_loadable_configs_only(self, hub, loads, folders, write_config):
        write_config(folders[1], "agents/lite")
        write_config(folders[1], "default", "jarvis")
        (folders[1] / "broken.json").write_text("{not json")
        assert hub.list_available_models() == ["agents/lite", "big", "small"]

    def test_model_configs_lists_everything_with_loadable_flag(self, hub, loads, folders, write_config):
        write_config(folders[1], "default", "jarvis")
        (folders[1] / "broken.json").write_text("{not json")
        configs = {c["key"]: c for c in hub.list_model_configs()}
        assert configs["small"] == {"key": "small", "model_name": "Display small",
                                    "model_type": "gguf", "loadable": True, "vision": False}
        assert configs["default"]["loadable"] is False and configs["default"]["model_type"] == "jarvis"
        assert configs["broken"]["loadable"] is False and "error" in configs["broken"]

    @pytest.mark.parametrize("folder", ["chat", "Chat/", "/chat"])
    def test_model_configs_filtered_by_folder_keep_full_keys(self, hub, loads, folders, write_config, folder):
        write_config(folders[1], "chat/lite")
        write_config(folders[0], "chat/deep/big")
        write_config(folders[1], "chatty")
        assert [c["key"] for c in hub.list_model_configs(folder)] == ["chat/deep/big", "chat/lite"]

    def test_model_configs_for_a_missing_folder_is_empty(self, hub, loads):
        assert hub.list_model_configs("chat") == []


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


class TestSwapWhileBusy:
    """A swap never interrupts work in progress unless the request explicitly forces it."""

    def test_lease_marks_the_hub_busy_until_released(self, hub, loads):
        lease = hub.acquire("small", "")
        assert hub.busy
        lease.release()
        lease.release()  # idempotent: a double release must not free someone else's lease
        assert not hub.busy

    def test_same_model_while_busy_does_not_wait(self, hub, loads):
        with hub.acquire("small", ""):
            with hub.acquire("small", "", on_busy="fail"):
                assert len(loads) == 1

    def test_fail_refuses_the_swap_and_keeps_the_model(self, hub, loads):
        with hub.acquire("small", ""):
            with pytest.raises(ModelBusyError, match="in use by 1 chat"):
                hub.get_brain("big", "", on_busy="fail")
            assert hub.current_model_id == "small" and loads[0].unloaded == 0

    def test_agent_run_also_blocks_a_swap(self, hub, loads):
        hub.get_brain("small", "")
        hub.agent_running = True
        with pytest.raises(ModelBusyError, match="an agent run"):
            hub.get_brain("big", "", on_busy="fail")

    def test_wait_swaps_once_the_current_work_finishes(self, hub, loads):
        lease = hub.acquire("small", "")
        result = {}
        waiter = threading.Thread(target=lambda: result.setdefault("llm", hub.get_brain("big", "")))
        waiter.start()
        time.sleep(0.1)
        assert waiter.is_alive() and hub.current_model_id == "small"  # still waiting
        assert loads[0].unloaded == 0

        lease.release()
        waiter.join(2)
        assert not waiter.is_alive()
        assert hub.current_model_id == "big" and result["llm"] is loads[1] and loads[0].unloaded == 1

    def test_wait_times_out_with_busy_error(self, hub, loads, monkeypatch):
        monkeypatch.setattr(BrainHub, "SWAP_WAIT_TIMEOUT", 0.1)
        with hub.acquire("small", ""):
            with pytest.raises(ModelBusyError, match="still in use"):
                hub.get_brain("big", "")
            assert hub.current_model_id == "small"

    def test_force_cancels_the_work_then_swaps(self, hub, loads):
        hub.get_brain("small", "")
        hub.agent_running = True
        cancelled = []

        def cancel():  # what AgentRunService.cancel_current does, as the run thread would end
            cancelled.append(True)
            threading.Timer(0.05, lambda: setattr(hub, "agent_running", False)).start()

        hub.add_cancel_hook(cancel)
        llm = hub.get_brain("big", "", on_busy="force")
        assert cancelled and llm is loads[1] and hub.current_model_id == "big"

    def test_unknown_policy_is_rejected(self, hub, loads):
        with hub.acquire("small", ""):
            with pytest.raises(ValueError, match="on_busy"):
                hub.get_brain("big", "", on_busy="maybe")

    def test_dropped_stream_releases_its_lease(self, hub, loads):
        lease = hub.acquire("small", "")

        def gen():
            yield "never started"

        owner = gen()
        BrainHub.release_with(owner, lease)
        del owner
        gc.collect()
        assert not hub.busy

    def test_activity_reflects_the_hub_state(self, hub, loads):
        ProcessManager._state = {}
        hub.get_brain("small", "")
        assert ProcessManager._state["activity"] == "idle (small)"
        with hub.acquire("small", ""):
            assert ProcessManager._state["activity"] == "busy: 1 chat"
        assert ProcessManager._state["activity"] == "idle (small)"


class TestChatServiceBusy:
    def request(self, model, on_busy=None):
        return MagicMock(model=model, system_prompt_content="", model_config_data=None, on_busy=on_busy)

    def test_resolve_returns_a_lease(self, hub, loads):
        lease = ChatService(hub, "/tmp", {})._resolve_brain(self.request("small"))
        assert hub.busy
        lease.release()
        assert not hub.busy

    def test_busy_with_fail_is_409(self, hub, loads):
        service = ChatService(hub, "/tmp", {})
        with service._resolve_brain(self.request("small")):
            with pytest.raises(HTTPException) as info:
                service._resolve_brain(self.request("big", on_busy="fail"))
        assert info.value.status_code == 409 and hub.current_model_id == "small"


class TestGpuFull:
    """A model that does not fit in the free GPU memory is loaded partly on the GPU, not dropped."""

    @pytest.fixture
    def gpu(self, loads, monkeypatch, fake_llm):
        from ai.core.llms.load_errors import GpuMemoryError
        from ai.services.engine_manager import EngineManager
        monkeypatch.setattr("ai.services.gpu_advisor.nvidia_snapshot", lambda: None)
        state = {"fit": 99, "tried": []}

        def load(model_config, system_prompt, tool_registry):
            layers = model_config["model_properties"].get("n_gpu_layers", -1)
            state["tried"].append(layers)
            if layers < 0 or layers > state["fit"]:
                raise GpuMemoryError("full")
            llm = fake_llm(model_config["model_name"], system_prompt)
            loads.append(llm)
            return llm

        monkeypatch.setattr(EngineManager, "load_model_instance", staticmethod(load))
        return state

    def test_swap_falls_back_to_a_partial_load(self, hub, gpu):
        gpu["fit"] = 8
        llm = hub.get_brain("small", "")
        assert llm is hub.orchestrator.llm and hub.current_model_id == "small"
        assert gpu["tried"][0] == -1 and 0 <= gpu["tried"][-1] <= 8

    def test_nothing_fits_is_a_load_error_and_the_hub_stays_empty(self, hub, gpu):
        gpu["fit"] = -1
        with pytest.raises(ModelLoadError, match="Failed to load model .small.: full"):
            hub.get_brain("small", "")
        assert hub.orchestrator.llm is None and hub.current_model_id is None
