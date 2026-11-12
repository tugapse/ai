"""Remote LLM resilience: timeouts and transient API errors must not look like broken model output."""

import sys
import threading
import time
import types as pytypes
from unittest.mock import MagicMock

import httpx
import pytest

import ai.program  # noqa: F401  (startup import order, avoids a circular import)
from ai.core.llms import api_retry as R
from ai.core.llms.api_retry import LLMAPIError, RetryPolicy, call_with_retry, is_transient, stream_with_retry
from google.genai import errors as genai_errors

FAST = RetryPolicy(max_retries=3, base_delay=0.01, max_delay=0.05)


def genai_error(code, status="", message="boom"):
    cls = genai_errors.ServerError if code >= 500 else genai_errors.ClientError
    return cls(code, {"error": {"code": code, "message": message, "status": status}})


class StatusError(Exception):
    def __init__(self, status_code, message="", headers=None):
        super().__init__(message or f"HTTP {status_code}")
        self.status_code = status_code
        self.response = MagicMock(status_code=status_code, headers=headers or {})


class APITimeoutError(Exception):
    """Mimics openai.APITimeoutError (classified by name)."""


# ---------------------------------------------------------------- classification

class TestClassification:
    @pytest.mark.parametrize("exc", [
        TimeoutError("t"),
        ConnectionResetError("reset"),
        httpx.ReadTimeout("read timed out"),
        httpx.ConnectTimeout("connect timed out"),
        httpx.ConnectError("refused"),
        httpx.RemoteProtocolError("server disconnected"),
        APITimeoutError("Request timed out."),
        genai_error(503, "UNAVAILABLE", "The model is overloaded."),
        genai_error(504, "DEADLINE_EXCEEDED"),
        genai_error(500, "INTERNAL"),
        genai_error(429, "RESOURCE_EXHAUSTED", "Quota exceeded for metric generate_requests_per_minute"),
        StatusError(429, "Rate limit reached"),
        StatusError(502),
        StatusError(408),
    ])
    def test_transient(self, exc):
        assert is_transient(exc)

    @pytest.mark.parametrize("exc", [
        genai_error(402, "RESOURCE_EXHAUSTED", "Your prepayment credits are depleted."),
        genai_error(400, "INVALID_ARGUMENT"),
        genai_error(403, "PERMISSION_DENIED"),
        StatusError(401, "Incorrect API key"),
        StatusError(404, "model not found"),
        StatusError(429, "You exceeded your current quota: insufficient_quota"),
        ValueError("bug in our code"),
        KeyError("x"),
    ])
    def test_permanent(self, exc):
        assert not is_transient(exc)

    def test_status_of(self):
        assert R.status_of(genai_error(503)) == 503
        assert R.status_of(StatusError(429)) == 429
        assert R.status_of(ValueError()) is None


class TestPolicy:
    def test_from_config(self):
        p = RetryPolicy.from_config({"timeout": "90", "max_retries": 2}, {"connect_timeout": 5, "retry_max_wait": 7})
        assert (p.timeout, p.max_retries, p.connect_timeout, p.max_delay) == (90.0, 2, 5.0, 7.0)

    def test_defaults_and_bad_values(self):
        p = RetryPolicy.from_config({"timeout": "soon"}, None)
        assert p.timeout == 300.0 and p.max_retries == 4

    def test_backoff_grows_and_is_capped(self):
        p = RetryPolicy(base_delay=1, max_delay=5)
        delays = [p.delay(n) for n in range(1, 6)]
        assert delays[0] < delays[2] and all(d <= 6 for d in delays)

    def test_retry_after_header(self):
        p = RetryPolicy(max_delay=30)
        assert p.delay(1, StatusError(429, headers={"retry-after": "12"})) == 12
        assert p.delay(1, StatusError(429, headers={"retry-after": "999"})) == 30


# ---------------------------------------------------------------- call / stream retry

class TestCallWithRetry:
    def test_recovers_after_transient_failures(self):
        calls = []

        def fn():
            calls.append(1)
            if len(calls) < 3:
                raise httpx.ReadTimeout("slow")
            return "ok"

        assert call_with_retry(fn, FAST, "Test") == "ok"
        assert len(calls) == 3

    def test_permanent_error_fails_fast(self):
        calls = []

        def fn():
            calls.append(1)
            raise genai_error(402, "RESOURCE_EXHAUSTED", "credits are depleted")

        with pytest.raises(LLMAPIError) as info:
            call_with_retry(fn, FAST, "Gemini")
        assert len(calls) == 1
        assert info.value.transient is False and info.value.status == 402
        assert "credits" in info.value.user_message()

    def test_gives_up_after_max_retries(self):
        def fn():
            raise httpx.ConnectTimeout("down")

        with pytest.raises(LLMAPIError) as info:
            call_with_retry(fn, FAST, "Test")
        assert info.value.transient is True and info.value.attempts == FAST.max_retries + 1
        assert "timed out" in str(info.value)

    def test_interrupt_during_backoff(self):
        stop = threading.Event()
        policy = RetryPolicy(max_retries=5, base_delay=10, max_delay=10)
        threading.Timer(0.1, stop.set).start()
        start = time.monotonic()
        with pytest.raises(LLMAPIError):
            call_with_retry(lambda: (_ for _ in ()).throw(httpx.ReadTimeout("x")), policy, "Test", stop)
        assert time.monotonic() - start < 2


class TestStreamWithRetry:
    def test_retries_before_first_chunk(self):
        attempts = []

        def open_stream():
            attempts.append(1)
            if len(attempts) < 3:
                raise genai_error(503, "UNAVAILABLE")
            return iter(["a", "b"])

        assert list(stream_with_retry(open_stream, FAST, "Gemini")) == ["a", "b"]
        assert len(attempts) == 3

    def test_lazy_failure_on_first_next_is_retried(self):
        attempts = []

        def open_stream():
            attempts.append(1)

            def gen():
                if len(attempts) < 2:
                    raise httpx.ReadTimeout("first byte never came")
                yield "ok"
            return gen()

        assert list(stream_with_retry(open_stream, FAST, "Test")) == ["ok"]

    def test_failure_after_output_is_partial(self):
        def open_stream():
            def gen():
                yield "<response><thought>"
                raise httpx.RemoteProtocolError("peer closed connection")
            return gen()

        out = []
        with pytest.raises(LLMAPIError) as info:
            for chunk in stream_with_retry(open_stream, FAST, "Test"):
                out.append(chunk)
        assert out == ["<response><thought>"]
        assert info.value.partial is True and info.value.transient is True

    def test_consumer_stopping_early_does_not_retry(self):
        attempts = []

        def open_stream():
            attempts.append(1)
            return iter(["a", "b", "c"])

        gen = stream_with_retry(open_stream, FAST, "Test")
        assert next(gen) == "a"
        gen.close()
        assert attempts == [1]


# ---------------------------------------------------------------- Gemini model

class FakeChunk:
    def __init__(self, text, finish=None):
        self.text = text
        self.candidates = [MagicMock(finish_reason=finish)]
        self.prompt_feedback = None


@pytest.fixture
def gemini(monkeypatch):
    from ai.core.llms.gemini import GeminiAPIModel
    model = GeminiAPIModel(model_name="gemini-test", api_key="test-key",
                           model_params={"timeout": 45, "max_retries": 2, "retry_base_delay": 0.01})
    model.client = MagicMock()
    return model


class TestGemini:
    def test_policy_and_client_timeout(self, gemini):
        assert gemini.retry_policy.timeout == 45 and gemini.retry_policy.max_retries == 2

    def test_client_receives_timeout_in_ms(self, monkeypatch):
        from ai.core.llms import gemini as gm
        captured = {}
        monkeypatch.setattr(gm.genai, "Client", lambda **kw: captured.update(kw) or MagicMock())
        gm.GeminiAPIModel(model_name="g", api_key="k", model_params={"timeout": 60})
        assert captured["http_options"].timeout == 60000

    def test_transient_errors_are_retried_transparently(self, gemini):
        attempts = []

        def stream(**kw):
            attempts.append(1)
            if len(attempts) < 3:
                raise genai_error(503, "UNAVAILABLE", "overloaded")
            return iter([FakeChunk("<response>"), FakeChunk("</response>", finish="STOP")])

        gemini.client.models.generate_content_stream.side_effect = stream
        out = "".join(gemini.chat([{"role": "user", "content": "hi"}], stream=True))
        assert out == "<response></response>"
        assert len(attempts) == 3

    def test_permanent_error_raises_instead_of_fake_text(self, gemini):
        gemini.client.models.generate_content_stream.side_effect = genai_error(402, "RESOURCE_EXHAUSTED", "credits are depleted")
        with pytest.raises(LLMAPIError) as info:
            list(gemini.chat([{"role": "user", "content": "hi"}], stream=True))
        assert info.value.transient is False and "credits" in str(info.value)

    def test_timeout_exhausted_raises_transient(self, gemini):
        gemini.client.models.generate_content_stream.side_effect = httpx.ReadTimeout("timed out")
        with pytest.raises(LLMAPIError) as info:
            list(gemini.chat([{"role": "user", "content": "hi"}], stream=True))
        assert info.value.transient is True and info.value.attempts == 3

    def test_sync_generation_retries(self, gemini):
        resp = MagicMock(text="hello")
        gemini.client.models.generate_content.side_effect = [httpx.ConnectError("x"), resp]
        assert gemini.chat([{"role": "user", "content": "hi"}], stream=False) == "hello"


# ---------------------------------------------------------------- OpenAI-compatible model

@pytest.fixture
def openai_model(monkeypatch):
    created = {}

    class FakeClient:
        def __init__(self, **kwargs):
            created.update(kwargs)
            self.chat = MagicMock()

    fake = pytypes.ModuleType("openai")
    fake.OpenAI = FakeClient
    fake.AzureOpenAI = FakeClient
    monkeypatch.setitem(sys.modules, "openai", fake)
    from ai.core.llms.open_ai import OpenAIAPIModel
    model = OpenAIAPIModel(model_name="gpt-test", api_key="k", timeout=30, max_retries=2, retry_base_delay=0.01)
    return model, created


def delta(text, finish=None):
    choice = MagicMock()
    choice.delta.content = text
    choice.finish_reason = finish
    chunk = MagicMock(usage=None)
    chunk.choices = [choice]
    return chunk


class TestOpenAI:
    def test_client_timeout_and_sdk_retries_disabled(self, openai_model):
        model, created = openai_model
        assert created["max_retries"] == 0
        assert created["timeout"].read == 30 and created["timeout"].connect == 15

    def test_stream_retries_transient_then_succeeds(self, openai_model):
        model, _ = openai_model
        model.client.chat.completions.create.side_effect = [
            APITimeoutError("Request timed out."),
            StatusError(503, "overloaded"),
            iter([delta("<response>"), delta("</response>", finish="stop")]),
        ]
        out = "".join(model.chat([{"role": "user", "content": "hi"}], stream=True))
        assert out == "<response></response>"

    def test_stream_permanent_error_raises(self, openai_model):
        model, _ = openai_model
        model.client.chat.completions.create.side_effect = StatusError(401, "Incorrect API key")
        with pytest.raises(LLMAPIError) as info:
            list(model.chat([{"role": "user", "content": "hi"}], stream=True))
        assert info.value.status == 401 and not info.value.transient

    def test_sync_error_raises_instead_of_empty_string(self, openai_model):
        model, _ = openai_model
        model.client.chat.completions.create.side_effect = StatusError(400, "bad request")
        with pytest.raises(LLMAPIError):
            model.chat([{"role": "user", "content": "hi"}], stream=False)


# ---------------------------------------------------------------- agent layer

BODY = "<response><action><tool_name>null</tool_name><agent_target>STOP</agent_target></action><response_to_user>ok</response_to_user></response>"


class TestConnectorAndOrchestrator:
    def _connector(self, tmp_path, monkeypatch, behaviours):
        from ai.agents.llm_connector import LLMConnector
        prompt = tmp_path / "p.md"
        prompt.write_text("prompt {{TOOLS}} {{AGENT_OUTPUT_RULES}}")
        connector = LLMConnector(MagicMock())
        calls = []

        def fake_call(messages):
            calls.append(1)
            item = behaviours[len(calls) - 1]
            if isinstance(item, Exception):
                raise item
            return item

        monkeypatch.setattr(connector, "_execute_llm_call", fake_call)
        return connector, str(prompt), calls

    def test_partial_stream_failure_reruns_the_call(self, tmp_path, monkeypatch):
        connector, prompt, calls = self._connector(tmp_path, monkeypatch, [
            LLMAPIError("peer closed", transient=True, partial=True), BODY])
        result = connector.send_request({}, prompt, agent_config={"tools": [], "allowed_targets": ["STOP"]})
        assert result["status"] == "SUCCESS" and len(calls) == 2

    def test_api_failure_is_not_a_parse_failure(self, tmp_path, monkeypatch):
        connector, prompt, _ = self._connector(tmp_path, monkeypatch, [
            LLMAPIError("credits are depleted", provider="Gemini", transient=False, status=402)])
        result = connector.send_request({}, prompt, agent_config={"tools": [], "allowed_targets": ["STOP"]})
        assert result["status"] == "FAILED" and result["api_error"] is True
        assert "Gemini API error" in result["error"]

    def test_orchestrator_ends_turn_without_format_strike(self, tmp_path, monkeypatch):
        sys.path.insert(0, str(__import__("pathlib").Path(__file__).parents[1] / "agents"))
        from test_agent_chat import make_orchestrator, RecordingIO
        from ai.agents.agent_orchestrator import MCPBridge
        from ai.agents.session_manager import AgentSessionManager
        from ai.agents.agent_io import AgentEventType
        monkeypatch.setattr(MCPBridge, "load_from_config", lambda self, p: None)
        monkeypatch.setattr(AgentSessionManager, "_get_agents_storage_root", staticmethod(lambda: str(tmp_path / "a")))
        monkeypatch.chdir(tmp_path)

        io = RecordingIO()
        orch, connector, _ = make_orchestrator([
            {"status": "FAILED", "api_error": True, "transient": True, "error": "Gemini API error after 5 attempts: request timed out"},
        ], io=io)
        result = orch.run_loop("hello", "s-api")
        assert result.reason == "api_error"
        assert orch.format_error_count == 0
        assert len(connector.requests) == 1  # no retry loop burning requests
        errors = [e.text for e in io.events if e.type == AgentEventType.ERROR]
        assert any("timed out" in e and "continue" in e for e in errors)
        inbox = orch.memory.get_agent_memory("MASTER").messages_received
        assert not any("PARSING FAILURE" in str(m.get("message", "")) for m in inbox)
