"""Jarvis client against a local HTTP server: network/server failures raise LLMAPIError."""

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

import ai.program  # noqa: F401  (startup import order, avoids a circular import)
from ai.core.llms.api_retry import LLMAPIError
from ai.core.llms.jarvis import JarvisAiModel

MESSAGES = [{"role": "user", "content": "hi"}]


def sse(*events):
    return "".join(f"data: {json.dumps(e) if isinstance(e, dict) else e}\n\n" for e in events).encode()


class Server:
    """Answers every POST with the configured (status, body)."""

    def __init__(self):
        self.status, self.body, self.requests = 200, b"", []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                outer.requests.append(json.loads(self.rfile.read(length)))
                self.send_response(outer.status)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(outer.body)))
                self.end_headers()
                self.wfile.write(outer.body)

            def log_message(self, *args):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"


@pytest.fixture
def server():
    srv = Server()
    yield srv
    srv.httpd.shutdown()


def client(url, **kwargs):
    return JarvisAiModel(model_name="default", base_url=url, max_retries=0, **kwargs)


class TestStreaming:
    def test_yields_content_with_accents(self, server):
        server.body = sse({"choices": [{"delta": {"content": "O ficheiro "}}]},
                          {"choices": [{"delta": {"content": "contém olá"}}]}, "[DONE]")
        assert "".join(client(server.url).chat(MESSAGES, stream=True)) == "O ficheiro contém olá"
        assert server.requests[0]["model"] == "default"

    def test_http_error_raises_api_error(self, server):
        server.status, server.body = 500, b"Internal Server Error"
        with pytest.raises(LLMAPIError) as info:
            list(client(server.url).chat(MESSAGES, stream=True))
        assert info.value.status == 500 and info.value.transient

    def test_in_band_server_error_raises_api_error(self, server):
        server.body = sse({"choices": [{"delta": {"content": "par"}}]}, {"error": "CUDA out of memory"})
        with pytest.raises(LLMAPIError, match="CUDA out of memory") as info:
            list(client(server.url).chat(MESSAGES, stream=True))
        assert info.value.partial

    def test_unreachable_server_raises_transient_api_error(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]  # closed again when the block ends: nothing listens
        with pytest.raises(LLMAPIError) as info:
            list(client(f"http://127.0.0.1:{port}").chat(MESSAGES, stream=True))
        assert info.value.transient and not info.value.partial

    def test_transient_error_is_retried(self, server):
        calls = []
        original = JarvisAiModel._open_stream

        def flaky(self, payload):
            calls.append(1)
            if len(calls) == 1:
                raise ConnectionError("dropped")
            yield from original(self, payload)

        server.body = sse({"choices": [{"delta": {"content": "ok"}}]}, "[DONE]")
        model = JarvisAiModel(model_name="default", base_url=server.url, max_retries=1, retry_base_delay=0)
        model._open_stream = flaky.__get__(model)
        assert "".join(model.chat(MESSAGES, stream=True)) == "ok"
        assert len(calls) == 2


class TestNonStreaming:
    def test_returns_text(self, server):
        server.body = json.dumps({"choices": [{"message": {"content": "café"}}]}).encode()
        assert client(server.url).chat(MESSAGES, stream=False) == "café"

    def test_http_error_raises_api_error(self, server):
        server.status, server.body = 500, b"boom"
        with pytest.raises(LLMAPIError):
            client(server.url).chat(MESSAGES, stream=False)


class TestServerModel:
    """The request's "model" is the server's config file name, not the display name."""

    def test_server_model_is_sent(self, server):
        server.body = sse("[DONE]")
        model = JarvisAiModel(model_name="Gemma 4 - E2B", base_url=server.url, max_retries=0, server_model="small")
        list(model.chat(MESSAGES, stream=True))
        assert server.requests[0]["model"] == "small"

    def test_falls_back_to_model_name(self, server, monkeypatch):
        monkeypatch.delenv("AI_SERVER_MODEL", raising=False)
        server.body = sse("[DONE]")
        list(client(server.url).chat(MESSAGES, stream=True))
        assert server.requests[0]["model"] == "default"

    def test_env_var(self, server, monkeypatch):
        monkeypatch.setenv("AI_SERVER_MODEL", "big")
        server.body = sse("[DONE]")
        list(client(server.url).chat(MESSAGES, stream=True))
        assert server.requests[0]["model"] == "big"


class TestServerErrorDetail:
    """HTTP errors show the server's reason (FastAPI "detail"), not only the status line."""

    NOT_FOUND = json.dumps({"detail": "Model 'gemma4' not found. Available: agents/gemma4-gguf, small"}).encode()

    def test_streaming_404_shows_detail_and_hint(self, server):
        server.status, server.body = 404, self.NOT_FOUND
        with pytest.raises(LLMAPIError) as info:
            list(client(server.url).chat(MESSAGES, stream=True))
        message = str(info.value)
        assert "404" in message and "Available: agents/gemma4-gguf, small" in message
        assert "server_model" in message
        assert info.value.status == 404 and not info.value.transient

    def test_non_streaming_409_shows_detail(self, server):
        server.status = 409
        server.body = json.dumps({"detail": "Model 'small' is in use by 1 chat; not swapping to 'big'."}).encode()
        with pytest.raises(LLMAPIError, match="in use by 1 chat") as info:
            client(server.url).chat(MESSAGES, stream=False)
        assert info.value.status == 409 and "server_model" not in str(info.value)

    def test_validation_errors_are_joined(self, server):
        server.status = 422
        server.body = json.dumps({"detail": [{"msg": "Input should be 'wait', 'fail' or 'force'"}]}).encode()
        with pytest.raises(LLMAPIError, match="Input should be 'wait', 'fail' or 'force'"):
            list(client(server.url).chat(MESSAGES, stream=True))

    def test_non_json_body_keeps_the_status_line(self, server):
        server.status, server.body = 500, b"Internal Server Error"
        with pytest.raises(LLMAPIError, match="server answered 500 Internal Server Error") as info:
            list(client(server.url).chat(MESSAGES, stream=True))
        assert info.value.transient  # 5xx is still retried


class TestImages:
    PNG = "data:image/png;base64,iVBORw0KGgo="

    def test_images_go_on_the_last_user_message_as_data_urls(self, server, tmp_path):
        from PIL import Image
        server.body = json.dumps({"choices": [{"message": {"content": "red"}}]}).encode()
        path = tmp_path / "pic.bmp"  # not a server format: re-encoded as PNG
        Image.new("RGB", (2, 2), (255, 0, 0)).save(path)
        messages = [{"role": "user", "content": "old"}, {"role": "assistant", "content": "ok"},
                    {"role": "user", "content": "colour?"}]
        assert client(server.url).chat(messages, images=[self.PNG, Image.new("RGB", (2, 2)), str(path)],
                                       stream=False) == "red"
        sent = server.requests[0]["messages"]
        images = sent[-1]["images"]
        assert images[0] == self.PNG and all(i.startswith("data:image/png;base64,") for i in images[1:])
        assert "images" not in sent[1] and "images" not in messages[-1]  # caller's list untouched

    def test_no_images_sends_no_field(self, server):
        server.body = json.dumps({"choices": [{"message": {"content": "hi"}}]}).encode()
        client(server.url).chat(list(MESSAGES), stream=False)
        assert "images" not in server.requests[0]["messages"][-1]

    def test_too_many_images_fail_before_the_request(self, server):
        with pytest.raises(ValueError, match="at most 4"):
            client(server.url).chat(list(MESSAGES), images=[self.PNG] * 5, stream=False)
        assert server.requests == []

    def test_vision_flag(self, server):
        assert client(server.url).supports_vision is True
        assert client(server.url, vision=False).supports_vision is False


class TestSamplingOptions:
    """Per-request settings (web sliders, relay) reach the server; the CLI's full config does not."""

    def send(self, server, options):
        server.body = json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode()
        client(server.url).chat(list(MESSAGES), stream=False, options=options)
        return server.requests[-1]

    def test_request_settings_are_sent(self, server):
        sent = self.send(server, {"temperature": 0.1, "top_p": 0.5, "top_k": 7,
                                  "max_tokens": 64, "max_new_tokens": 64})
        assert (sent["temperature"], sent["top_p"], sent["top_k"], sent["max_tokens"]) == (0.1, 0.5, 7, 64)
        assert "max_new_tokens" not in sent

    def test_max_new_tokens_alone_becomes_max_tokens(self, server):
        assert self.send(server, {"max_new_tokens": 32})["max_tokens"] == 32

    def test_no_options_sends_no_fields(self, server):
        sent = self.send(server, {})
        assert not {"temperature", "top_p", "top_k", "max_tokens"} & set(sent)

    def test_full_model_config_is_not_an_override(self, server):
        from ai.core.llms.base_llm import ModelParams
        sent = self.send(server, ModelParams().to_dict())  # what the CLI chat passes
        assert not {"temperature", "top_p", "top_k", "max_tokens"} & set(sent)
