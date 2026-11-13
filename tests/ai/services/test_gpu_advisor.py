"""GpuAdvisor: a model that does not fit in the GPU gets alternatives instead of a dead end."""

import pytest

from ai.core.llms.load_errors import GpuMemoryError
from ai.services.gpu_advisor import GpuAdvisor, GpuHolder, GpuSnapshot, model_key

GGUF = {"model_name": "gemma4", "model_type": "gguf",
        "model_properties": {"gguf_filename": "gemma-4.gguf", "model_repo_id": "unsloth/gemma-4",
                             "n_gpu_layers": -1, "temperature": 0.6}}
SERVER = {"pid": "4242", "mode": "server", "model": "agents/gemma4-gguf", "activity": "idle (agents/gemma4-gguf)",
          "endpoint": "http://127.0.0.1:9999"}
OTHER_CONFIGS = {
    "agents/gemma4-gguf": GGUF,
    "qwen": {"model_name": "qwen", "model_type": "gguf", "model_properties": {"gguf_filename": "qwen.gguf"}},
}


class Loads(list):
    """Every config the advisor loads; GPU loads fail while layers > fit_layers."""
    fit_layers = 99

    def __call__(self, model_config, system_prompt, tool_registry):
        self.append(model_config)
        layers = model_config["model_properties"].get("n_gpu_layers")
        if model_config["model_type"] == "gguf" and layers is not None and (layers < 0 or layers > self.fit_layers):
            raise GpuMemoryError("full")
        return f"llm:{model_config['model_type']}"


@pytest.fixture
def loads():
    return Loads()


def advisor(loads, servers=(), answers=(), interactive=True, holders=(), config_name="default"):
    replies = list(answers)
    out = []
    adv = GpuAdvisor(
        config_name, GGUF, "sys", loader=loads,
        snapshot=lambda: GpuSnapshot(1600, 8192, list(holders)),
        instances=lambda: list(servers), interactive=interactive,
        ask=lambda prompt: replies.pop(0), find_config=OTHER_CONFIGS.get)
    adv._block_count = staticmethod(lambda path: 42)
    return adv, out


def error():
    return GpuMemoryError("full", model_path="", n_gpu_layers=-1)


@pytest.fixture
def printed(monkeypatch):
    lines = []
    monkeypatch.setattr("ai.services.gpu_advisor.func.out", lambda msg="", *a, **k: lines.append(str(msg)))
    return lines


def test_model_key_normalises():
    assert model_key(" Agents/Lite.json ") == "agents/lite" and model_key("") == "default"


def test_server_with_the_same_model_file_is_offered_first(loads, printed):
    adv, _ = advisor(loads, servers=[SERVER], answers=["1"])
    assert adv.resolve(error()) == "llm:jarvis"
    sent = loads[-1]["model_properties"]
    assert sent["base_url"] == "http://127.0.0.1:9999" and sent["server_model"] == "agents/gemma4-gguf"
    assert "on_busy" not in sent and sent["temperature"] == 0.6
    assert any("already has this model" in line for line in printed)


def test_holders_are_described_with_registry_details(loads, printed):
    holders = [GpuHolder(4242, "python3", 6328), GpuHolder(777, "ComfyUI", 900), GpuHolder(1579, "kwin", 7)]
    adv, _ = advisor(loads, servers=[SERVER], answers=["1"], holders=holders)
    adv.resolve(error())
    text = "\n".join(printed)
    assert "JARVIS server (agents/gemma4-gguf)  PID 4242  6.2 GB - idle" in text
    assert "ComfyUI  PID 777  0.9 GB" in text
    assert "kwin" not in text  # tiny users are noise
    assert "1.6 GB free of 8.0 GB" in text


def test_server_with_another_model_offers_use_switch_and_force_when_busy(loads, printed):
    busy = dict(SERVER, model="qwen", activity="busy: 1 chat")
    adv, _ = advisor(loads, servers=[busy], answers=["3"])
    adv.resolve(error())
    labels = [line.strip() for line in printed if line.strip()[:2] in {f"{n})" for n in range(1, 9)}]
    assert labels[0].startswith("1) Use the running server with its model (qwen)")
    assert labels[1].startswith("2) Ask the server to switch to default when its current work ends")
    assert labels[2].startswith("3) Force the server") and "CANCELS" in labels[2]
    assert labels[3].startswith("4) Load it here, partly on the GPU")
    assert labels[4] == "5) Cancel"
    assert loads[-1]["model_properties"]["on_busy"] == "force"
    assert loads[-1]["model_properties"]["server_model"] == "default"


def test_idle_server_switch_waits_and_no_force_is_offered(loads, printed):
    adv, _ = advisor(loads, servers=[dict(SERVER, model="qwen")], answers=["2"])
    adv.resolve(error())
    assert loads[-1]["model_properties"]["on_busy"] == "wait"
    assert not any("Force" in line for line in printed)


def test_partial_load_steps_down_until_it_fits(loads, printed):
    loads.fit_layers = 5
    adv, _ = advisor(loads, answers=["1"])  # no server: only partial and cancel
    assert adv.resolve(error()) == "llm:gguf"
    tried = [c["model_properties"]["n_gpu_layers"] for c in loads]
    assert tried == sorted(tried, reverse=True) and tried[-1] <= 5
    assert GGUF["model_properties"]["n_gpu_layers"] == -1  # the original config is untouched


def test_cpu_only_is_the_last_resort(loads, printed):
    loads.fit_layers = 0
    adv, _ = advisor(loads, answers=["1"])
    assert adv.resolve(error()) == "llm:gguf"
    assert loads[-1]["model_properties"]["n_gpu_layers"] == 0


def test_cancel_returns_none(loads, printed):
    adv, _ = advisor(loads, servers=[SERVER], answers=["3"])  # 1 server, 2 partial, 3 cancel
    assert adv.resolve(error()) is None and loads == []


def test_invalid_answers_are_asked_again(loads, printed):
    adv, _ = advisor(loads, servers=[SERVER], answers=["x", "9", ""])  # empty = default 1
    assert adv.resolve(error()) == "llm:jarvis"


def test_eof_on_the_prompt_cancels(loads, printed):
    adv = GpuAdvisor("default", GGUF, "", loader=loads, snapshot=lambda: None, instances=lambda: [],
                     interactive=True, ask=lambda p: (_ for _ in ()).throw(EOFError()), find_config=OTHER_CONFIGS.get)
    assert adv.resolve(error()) is None


def test_non_interactive_uses_a_server_with_the_same_model(loads, printed):
    adv, _ = advisor(loads, servers=[SERVER], interactive=False)
    assert adv.resolve(error()) == "llm:jarvis"


def test_non_interactive_never_switches_a_server_model(loads, printed):
    adv, _ = advisor(loads, servers=[dict(SERVER, model="qwen")], interactive=False)
    loads.fit_layers = 10
    assert adv.resolve(error()) == "llm:gguf"
    assert all(c["model_type"] == "gguf" for c in loads)


def test_own_instance_and_servers_without_endpoint_are_ignored(loads, printed):
    import os
    me = dict(SERVER, pid=str(os.getpid()))
    no_endpoint = dict(SERVER, pid="5", endpoint="")
    adv, _ = advisor(loads, servers=[me, no_endpoint], interactive=False)
    loads.fit_layers = 10
    assert adv.resolve(error()) == "llm:gguf"


def test_without_nvidia_smi_it_still_offers_choices(loads, printed):
    adv = GpuAdvisor("default", GGUF, "", loader=loads, snapshot=lambda: None, instances=lambda: [SERVER],
                     interactive=True, ask=lambda p: "1", find_config=OTHER_CONFIGS.get)
    assert adv.resolve(error()) == "llm:jarvis"
    assert any("Not enough free GPU memory to load default." in line for line in printed)


def test_own_process_is_not_listed_as_a_holder(loads, printed):
    import os
    adv, _ = advisor(loads, servers=[SERVER], answers=["1"], holders=[GpuHolder(os.getpid(), "python3", 120)])
    adv.resolve(error())
    assert not any(f"PID {os.getpid()}" in line for line in printed)


def test_partial_load_reports_only_the_final_placement(loads, printed):
    loads.fit_layers = 0
    adv, _ = advisor(loads, answers=["1"])
    adv.resolve(error())
    loaded = [line for line in printed if "Loaded default" in line]
    assert len(loaded) == 1 and "on the CPU only" in loaded[0]


def test_cpu_only_keeps_kv_cache_and_compute_off_the_gpu(loads, printed):
    loads.fit_layers = 0
    adv, _ = advisor(loads, answers=["1"])
    adv.resolve(error())
    last = loads[-1]["model_properties"]
    assert last["n_gpu_layers"] == 0 and last["offload_kqv"] is False and last["op_offload"] is False
    assert all("op_offload" not in c["model_properties"] for c in loads[:-1])
