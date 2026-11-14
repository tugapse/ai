"""The GGUF engine tells a full GPU apart from a broken model file, from llama.cpp's log."""

import pytest

pytest.importorskip("llama_cpp")
from ai.core.llms import gguf_model  # noqa: E402

# Real lines from a load that failed because another process held the GPU.
CUDA_OOM = (
    "ggml_backend_cuda_buffer_type_alloc_buffer: allocating 2883.51 MiB on device 0: cudaMalloc failed: out of memory\n"
    "alloc_tensor_range: failed to allocate CUDA0 buffer of size 3023580416\n"
    "llama_model_load: error loading model: unable to allocate CUDA0 buffer\n"
)


def test_cuda_allocation_failure_is_gpu_oom():
    assert gguf_model._gpu_oom_in(CUDA_OOM)


def test_unknown_architecture_is_not_gpu_oom():
    assert not gguf_model._gpu_oom_in("llama_model_load: error loading model: unknown model architecture: 'x'\n")


def test_log_lines_are_kept_in_memory_not_printed(capfd):
    gguf_model._engine_log.clear()
    gguf_model._null_log_callback(2, b"cudaMalloc failed: out of memory\n", None)
    gguf_model._null_log_callback(2, None, None)
    assert "".join(gguf_model._engine_log) == "cudaMalloc failed: out of memory\n"
    assert capfd.readouterr().out == ""



def load_with_fake_llama(monkeypatch, free_mb=None, **props):
    """Loads a GGUFImageLLM on a fake Llama; ``free_mb`` is what nvidia-smi reports after the load."""
    from ai.services import gpu_advisor
    seen = {"freed": False}

    class FakeLlama:
        def __init__(self, **kwargs):
            seen["kwargs"] = kwargs

        def __del__(self):
            seen["freed"] = True

    monkeypatch.setattr(gguf_model, "Llama", FakeLlama)
    monkeypatch.setattr(gguf_model, "hf_hub_download", lambda **kw: "/models/x.gguf")
    snapshot = None if free_mb is None else gpu_advisor.GpuSnapshot(free_mb, 8192)
    monkeypatch.setattr(gpu_advisor, "nvidia_snapshot", lambda: snapshot)
    llm = gguf_model.GGUFImageLLM("m", "x.gguf", model_repo_id="r", **props)
    return llm, seen


def test_flash_attention_is_on_by_default(monkeypatch):
    _, seen = load_with_fake_llama(monkeypatch)
    assert seen["kwargs"]["flash_attn"] is True
    assert "gpu_headroom_mb" not in seen["kwargs"]


def test_a_model_can_turn_flash_attention_off(monkeypatch):
    _, seen = load_with_fake_llama(monkeypatch, flash_attn=False)
    assert seen["kwargs"]["flash_attn"] is False


def test_load_that_leaves_enough_room_is_kept(monkeypatch):
    llm, _ = load_with_fake_llama(monkeypatch, free_mb=2000)
    assert llm.llama_model is not None


def test_load_without_room_to_generate_is_unloaded_and_raises(monkeypatch):
    with pytest.raises(gguf_model.GpuMemoryError, match="leaves only 100 MB") as info:
        load_with_fake_llama(monkeypatch, free_mb=100, n_gpu_layers=25)
    assert info.value.model_path == "/models/x.gguf" and info.value.n_gpu_layers == 25


def test_headroom_is_configurable_and_skipped_on_cpu(monkeypatch):
    llm, _ = load_with_fake_llama(monkeypatch, free_mb=100, gpu_headroom_mb=64)
    assert llm.llama_model is not None
    llm, _ = load_with_fake_llama(monkeypatch, free_mb=10, n_gpu_layers=0)
    assert llm.llama_model is not None


def test_no_nvidia_smi_skips_the_check(monkeypatch):
    llm, _ = load_with_fake_llama(monkeypatch, free_mb=None)
    assert llm.llama_model is not None
