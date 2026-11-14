"""
Engines inside a server: a failed generation or load raises (LLMAPIError / RuntimeError), never
sys.exit, which killed the whole server; and every engine takes the server's chat() call
``chat(messages, images=..., stream=..., options=...)`` with this request's options.
"""

import importlib
import sys
import threading
import types
from unittest.mock import MagicMock

import pytest

import ai.program  # noqa: F401  (startup import order, avoids a circular import)
from ai.core.llms.api_retry import LLMAPIError

MESSAGES = [{"role": "user", "content": "hi"}]


def bare(cls, **attrs):
    """An instance without running __init__ (which would load a real model)."""
    obj = cls.__new__(cls)
    obj.stop_generation_event = threading.Event()
    obj.check_system_prompt = lambda messages: messages
    obj.trigger = lambda *a, **k: None
    for key, value in attrs.items():
        setattr(obj, key, value)
    return obj


@pytest.fixture
def ollama_module(monkeypatch):
    fake = types.ModuleType("ollama")
    fake.Client = MagicMock()
    monkeypatch.setitem(sys.modules, "ollama", fake)
    monkeypatch.delitem(sys.modules, "ai.core.llms.ollama_model", raising=False)
    return importlib.import_module("ai.core.llms.ollama_model")


class TestOllama:
    def make(self, ollama_module, client):
        return bare(ollama_module.OllamaModel, model=client, model_name="m", keep_alive=False,
                    options={"temperature": 0.7})

    def test_non_stream_failure_raises_instead_of_exiting(self, ollama_module):
        client = MagicMock()
        client.chat.side_effect = ConnectionError("ollama is down")
        with pytest.raises(LLMAPIError, match="ollama is down"):
            self.make(ollama_module, client).chat(MESSAGES, stream=False)

    def test_stream_failure_raises_instead_of_exiting(self, ollama_module):
        def broken():
            yield {"message": {"content": "par"}}
            raise ConnectionError("dropped")
        client = MagicMock()
        client.chat.return_value = broken()
        with pytest.raises(LLMAPIError, match="dropped") as info:
            list(self.make(ollama_module, client).chat(MESSAGES, stream=True))
        assert info.value.partial

    @pytest.mark.parametrize("stream", [False, True])
    def test_request_options_reach_ollama(self, ollama_module, stream):
        client = MagicMock()
        client.chat.return_value = iter([]) if stream else {"message": {"content": "ok"}}
        result = self.make(ollama_module, client).chat(MESSAGES, stream=stream, options={"temperature": 0.1})
        if stream:
            list(result)
        assert client.chat.call_args.kwargs["options"]["temperature"] == 0.1


@pytest.fixture
def openai_model(monkeypatch):
    from ai.core.llms.open_ai import OpenAIAPIModel as OpenAiModel
    client = MagicMock()
    response = MagicMock(usage=None)
    response.choices = [MagicMock(message=MagicMock(content="olá"))]
    client.chat.completions.create.return_value = response
    from ai.core.llms.api_retry import RetryPolicy
    model = bare(OpenAiModel, client=client, model_name="gpt-x", system_prompt="",
                 retry_policy=RetryPolicy.from_config({}, {}, {}),
                 options={"max_tokens": 2048, "temperature": 0.5, "top_p": 0.95})
    model._convert_messages = lambda messages: messages
    return model, client


class TestOpenAI:
    def test_server_call_signature(self, openai_model):
        # Was: TypeError "unexpected keyword argument 'images'" on every server chat.
        model, client = openai_model
        assert model.chat(MESSAGES, images=None, stream=False, options={}) == "olá"

    def test_request_options_override_the_config(self, openai_model):
        model, client = openai_model
        model.chat(MESSAGES, images=None, stream=False,
                   options={"temperature": 0.1, "top_k": 5, "max_tokens": 64, "max_new_tokens": 64})
        sent = client.chat.completions.create.call_args.kwargs
        assert sent["temperature"] == 0.1 and sent["max_tokens"] == 64 and sent["top_p"] == 0.95
        assert "top_k" not in sent and "max_new_tokens" not in sent

    def test_reasoning_models_keep_their_limit_key(self, openai_model):
        model, client = openai_model
        model.options = {"max_completion_tokens": 2048}
        model.chat(MESSAGES, stream=False, options={"temperature": 0.1, "max_tokens": 64})
        sent = client.chat.completions.create.call_args.kwargs
        assert sent["max_completion_tokens"] == 64 and "temperature" not in sent and "max_tokens" not in sent


try:
    import torch  # noqa: F401
    import transformers  # noqa: F401
    HAS_TORCH = True
except Exception:
    HAS_TORCH = False


@pytest.mark.skipif(not HAS_TORCH, reason="torch/transformers not installed")
class TestHuggingFace:
    def make(self):
        from ai.core.llms.huggingface_model import HuggingFaceModel
        model = bare(HuggingFaceModel, model=MagicMock(spec=[]), tokenizer=MagicMock(), model_name="m",
                     device_map="cpu", turboquant_available=False)
        model.error_queue = __import__("queue").Queue()
        model.is_gpu_available = lambda: False
        model._prepare_input = lambda messages: {"input_ids": MagicMock(shape=(1, 2))}
        model._extract_generation_params = lambda options: (16, False, 0, 1.0, 1.0, 0)
        return model

    def test_non_stream_failure_raises_instead_of_exiting(self):
        model = self.make()
        model._generate_response = MagicMock(side_effect=RuntimeError("CUDA error: device-side assert"))
        with pytest.raises(LLMAPIError, match="CUDA error"):
            list(model.chat(MESSAGES, stream=False))

    def test_unexpected_failure_raises_instead_of_exiting(self):
        model = self.make()
        model._generate_response = MagicMock(side_effect=ValueError("bad input"))
        with pytest.raises(LLMAPIError, match="bad input"):
            list(model.chat(MESSAGES, stream=False))

    def test_load_failure_raises_instead_of_exiting(self, monkeypatch):
        from huggingface_hub.errors import RepositoryNotFoundError
        from ai.core.llms.huggingface_model import HuggingFaceModel
        monkeypatch.setattr(HuggingFaceModel, "_load_llm_params",
                            lambda self: (_ for _ in ()).throw(RepositoryNotFoundError("nope", response=MagicMock())))
        with pytest.raises(RuntimeError, match="not found on Hugging Face Hub"):
            HuggingFaceModel(model_name="missing/model")


@pytest.mark.skipif(not HAS_TORCH, reason="torch/transformers not installed")
def test_huggingface_stream_failure_raises_instead_of_truncating(monkeypatch):
    """The generation thread failing mid-stream: was only logged, the reply silently cut short."""
    import queue
    import transformers
    from ai.core.llms.huggingface_model import HuggingFaceModel

    class Streamer:
        def __init__(self, *a, **k):
            self.q = queue.Queue()

        def put_text(self, text):
            self.q.put(text)

        def end(self):
            self.q.put(None)

        def __iter__(self):
            while (item := self.q.get(timeout=5)) is not None:
                yield item

    monkeypatch.setattr("ai.core.llms.huggingface_model.TextIteratorStreamer", Streamer)
    model = bare(HuggingFaceModel, model=MagicMock(spec=[]), tokenizer=MagicMock(), model_name="m",
                 device_map="cpu", turboquant_available=False, _generation_thread=None)
    model.error_queue = queue.Queue()
    model.is_gpu_available = lambda: False
    model._prepare_input = lambda messages: {"input_ids": MagicMock(shape=(1, 2))}
    model._extract_generation_params = lambda options: (16, False, 0, 1.0, 1.0, 0)
    model.handle_sentinel = lambda content, intercepting, buffer: (content, "", False, False)

    def failing_generation(model, tokenizer, generation_kwargs, error_queue, streamer, stop_event):
        streamer.put_text("par")
        error_queue.put("ERROR: Model generation failed due to a CUDA/Runtime error. \nDetails: out of memory"
                        "\nTraceback:\n  File ...")
        streamer.end()

    model._generate_in_thread = failing_generation
    received = []
    with pytest.raises(LLMAPIError, match="out of memory") as info:
        for token in model.chat(MESSAGES, stream=True):
            received.append(token)
    assert received == ["par"] and info.value.partial and "Traceback" not in str(info.value)
