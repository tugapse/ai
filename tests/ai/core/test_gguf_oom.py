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
