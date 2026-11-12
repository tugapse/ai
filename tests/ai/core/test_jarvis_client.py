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
