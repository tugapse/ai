"""
chat(stream=False) must return the text itself, not an empty generator.

A chat() that has ``yield`` in its streaming branch is a generator function as a
whole, so ``return text`` in the other branch is lost; the server's non-streaming
endpoint then joined an empty generator and answered with "content": "".
"""

import importlib
import sys
import threading
import types
from unittest.mock import MagicMock

import pytest

import ai.program  # noqa: F401  (startup import order, avoids a circular import)


@pytest.fixture
def gguf_module(monkeypatch):
    fake = types.ModuleType("llama_cpp")
    fake.Llama = MagicMock()
    fake.llama_log_set = lambda *a, **k: None
    monkeypatch.setitem(sys.modules, "llama_cpp", fake)
    monkeypatch.delitem(sys.modules, "ai.core.llms.gguf_model", raising=False)
    return importlib.import_module("ai.core.llms.gguf_model")


@pytest.fixture
def ollama_module(monkeypatch):
    fake = types.ModuleType("ollama")
    fake.Client = MagicMock()
    monkeypatch.setitem(sys.modules, "ollama", fake)
    monkeypatch.delitem(sys.modules, "ai.core.llms.ollama_model", raising=False)
    return importlib.import_module("ai.core.llms.ollama_model")


def bare(cls, **attrs):
    """An instance without running __init__ (which would load a real model)."""
    obj = cls.__new__(cls)
    obj.stop_generation_event = threading.Event()
    obj.options = {}
    obj.check_system_prompt = lambda messages: messages
    obj.trigger = lambda *a, **k: None
    for key, value in attrs.items():
        setattr(obj, key, value)
    return obj


MESSAGES = [{"role": "user", "content": "hi"}]


class TestGGUF:
    def make(self, gguf_module, llama):
        model = bare(gguf_module.GGUFImageLLM, llama_model=llama)
        model._update_token_metrics = lambda *a, **k: None
        return model

    def test_non_stream_returns_text(self, gguf_module):
        llama = MagicMock()
        llama.tokenize.return_value = [1, 2]
        llama.create_chat_completion.return_value = {"choices": [{"message": {"content": "olá mundo"}}], "usage": {}}
        result = self.make(gguf_module, llama).chat(MESSAGES, stream=False)
        assert result == "olá mundo"

    def test_stream_returns_a_token_generator(self, gguf_module):
        model = self.make(gguf_module, MagicMock(tokenize=MagicMock(return_value=[1])))

        def fake_thread(messages, options, q):
            for token in ("a", "b"):
                q.put(token)
            q.put(None)

        model._generate_in_thread = fake_thread
        assert list(model.chat(MESSAGES, stream=True)) == ["a", "b"]

    def test_model_not_loaded(self, gguf_module):
        model = self.make(gguf_module, None)
        assert model.chat(MESSAGES, stream=False) == "Model not loaded."
        assert list(model.chat(MESSAGES, stream=True)) == ["Model not loaded."]


class TestOllama:
    def test_non_stream_returns_text(self, ollama_module):
        client = MagicMock()
        client.chat.return_value = {"message": {"content": "olá"}}
        model = bare(ollama_module.OllamaModel, model=client, model_name="m", keep_alive=False)
        assert model.chat(MESSAGES, stream=False) == "olá"

    def test_stream_returns_a_token_generator(self, ollama_module):
        client = MagicMock()
        client.chat.return_value = iter([{"message": {"content": "a"}}, {"message": {"content": "b"}}])
        model = bare(ollama_module.OllamaModel, model=client, model_name="m", keep_alive=False)
        assert list(model.chat(MESSAGES, stream=True)) == ["a", "b"]
