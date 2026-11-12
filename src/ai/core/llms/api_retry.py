"""
Shared resilience helpers for remote LLM APIs (Gemini, OpenAI-compatible).

Transient failures (timeouts, dropped connections, rate limits, overloaded
servers) are retried with exponential backoff instead of surfacing as broken
model output. Permanent failures (bad key, no credits, bad request) fail fast
with an ``LLMAPIError`` that callers can tell apart from a malformed response.

The classifier inspects exception attributes and class names instead of importing
provider SDKs, so it works whichever SDK (or version) is installed.
"""

import random
import threading
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Iterator, Optional, TypeVar

import ai.functions as func

T = TypeVar("T")

TRANSIENT_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 529}
TRANSIENT_STATUS_NAMES = {"UNAVAILABLE", "DEADLINE_EXCEEDED", "INTERNAL", "ABORTED", "RESOURCE_EXHAUSTED_RATE"}
TRANSIENT_CLASS_HINTS = (
    "Timeout", "TimedOut", "ConnectError", "ConnectionError", "APIConnectionError",
    "RemoteProtocolError", "ReadError", "WriteError", "ProtocolError", "ServerDisconnected",
    "IncompleteRead", "ChunkedEncodingError", "ServiceUnavailable", "RateLimit", "InternalServerError",
)


class LLMAPIError(RuntimeError):
    """
    A remote model call failed for a reason that is NOT the model's output.

    Attributes:
        provider: e.g. "Gemini", "OpenAI".
        transient: True if retrying later may succeed (timeout, 429, 503...).
        status: HTTP status code when known.
        partial: True if the failure happened after some output was already streamed.
        attempts: How many attempts were made.
    """

    def __init__(self, message: str, provider: str = "LLM", transient: bool = False,
                 status: Optional[int] = None, partial: bool = False, attempts: int = 1):
        super().__init__(message)
        self.provider = provider
        self.transient = transient
        self.status = status
        self.partial = partial
        self.attempts = attempts

    def user_message(self) -> str:
        retry_note = f" after {self.attempts} attempts" if self.attempts > 1 else ""
        return f"{self.provider} API error{retry_note}: {self}"


def status_of(exc: BaseException) -> Optional[int]:
    """Best-effort HTTP status code of an SDK exception."""
    for attr in ("status_code", "code", "http_status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int) and 100 <= value < 600:
            return value
    response = getattr(exc, "response", None)
    value = getattr(response, "status_code", None)
    return value if isinstance(value, int) else None


def is_transient(exc: BaseException) -> bool:
    """True for failures worth retrying: timeouts, connection drops, 408/429/5xx."""
    if isinstance(exc, LLMAPIError):
        return exc.transient
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True

    status = status_of(exc)
    if status is not None:
        if status == 429:
            # Out of quota/credits is not going to fix itself by retrying.
            text = str(exc).lower()
            return not any(k in text for k in ("credit", "billing", "insufficient_quota"))
        return status in TRANSIENT_STATUS

    status_name = str(getattr(exc, "status", "") or "").upper()
    if status_name in TRANSIENT_STATUS_NAMES:
        return True

    names = " ".join(cls.__name__ for cls in type(exc).__mro__)
    return any(hint in names for hint in TRANSIENT_CLASS_HINTS)


def retry_after_seconds(exc: BaseException) -> Optional[float]:
    """Honors a Retry-After header (seconds) when the SDK exposes the response."""
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    try:
        value = headers.get("retry-after") or headers.get("Retry-After")
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


@dataclass
class RetryPolicy:
    """
    Attributes:
        max_retries: Retries after the first attempt (0 disables retrying).
        base_delay: First backoff delay in seconds (doubles each retry).
        max_delay: Upper bound for a single wait.
        timeout: Per-request read timeout in seconds (applied by the provider client).
        connect_timeout: Connection timeout in seconds.
    """
    max_retries: int = 4
    base_delay: float = 1.0
    max_delay: float = 30.0
    timeout: float = 300.0
    connect_timeout: float = 15.0

    @classmethod
    def from_config(cls, *sources: dict) -> "RetryPolicy":
        """Reads 'max_retries', 'timeout', 'connect_timeout', 'retry_max_wait' from model config dicts."""
        policy = cls()
        for source in sources:
            if not isinstance(source, dict):
                continue
            for key, attr, cast in (("max_retries", "max_retries", int), ("timeout", "timeout", float),
                                    ("connect_timeout", "connect_timeout", float),
                                    ("retry_max_wait", "max_delay", float), ("retry_base_delay", "base_delay", float)):
                if source.get(key) is not None:
                    try:
                        setattr(policy, attr, max(0, cast(source[key])))
                    except (TypeError, ValueError):
                        pass
        return policy

    def delay(self, attempt: int, exc: Optional[BaseException] = None) -> float:
        """Backoff for retry number ``attempt`` (1-based), with jitter and Retry-After support."""
        hinted = retry_after_seconds(exc) if exc is not None else None
        if hinted is not None:
            return min(max(hinted, 0.0), self.max_delay)
        backoff = self.base_delay * (2 ** (attempt - 1))
        return min(backoff, self.max_delay) * random.uniform(0.8, 1.2)


def wrap_error(exc: BaseException, provider: str, attempts: int, partial: bool = False) -> LLMAPIError:
    if isinstance(exc, LLMAPIError):
        exc.attempts = max(exc.attempts, attempts)
        return exc
    message = str(exc) or type(exc).__name__
    if is_transient(exc) and ("timeout" in type(exc).__name__.lower() or isinstance(exc, TimeoutError)):
        message = f"request timed out ({type(exc).__name__})"
    return LLMAPIError(message, provider=provider, transient=is_transient(exc),
                       status=status_of(exc), partial=partial, attempts=attempts)


def _wait(seconds: float, stop_event: Optional[threading.Event]) -> bool:
    """Sleeps; returns False if interrupted by stop_event."""
    if stop_event is None:
        threading.Event().wait(seconds)
        return True
    return not stop_event.wait(seconds)


def call_with_retry(fn: Callable[[], T], policy: RetryPolicy, provider: str,
                    stop_event: Optional[threading.Event] = None) -> T:
    """Runs a non-streaming request with retries on transient errors."""
    attempt = 0
    while True:
        attempt += 1
        try:
            return fn()
        except Exception as exc:
            if not is_transient(exc) or attempt > policy.max_retries:
                raise wrap_error(exc, provider, attempt) from exc
            delay = policy.delay(attempt, exc)
            func.log(f"[{provider}] Transient error ({type(exc).__name__}: {str(exc)[:120]}). "
                     f"Retry {attempt}/{policy.max_retries} in {delay:.1f}s", level="WARN")
            if not _wait(delay, stop_event):
                raise wrap_error(exc, provider, attempt) from exc


def stream_with_retry(open_stream: Callable[[], Iterable[Any]], policy: RetryPolicy, provider: str,
                      stop_event: Optional[threading.Event] = None) -> Iterator[Any]:
    """
    Iterates a streaming request, transparently retrying transient failures that
    happen before the first chunk. A failure after chunks were delivered cannot be
    replayed, so it raises ``LLMAPIError(partial=True)`` for the caller to handle.
    """
    attempt = 0
    while True:
        attempt += 1
        delivered = False
        try:
            for chunk in open_stream():
                delivered = True
                yield chunk
            return
        except GeneratorExit:
            raise
        except Exception as exc:
            if delivered:
                raise wrap_error(exc, provider, attempt, partial=True) from exc
            if not is_transient(exc) or attempt > policy.max_retries:
                raise wrap_error(exc, provider, attempt) from exc
            if stop_event is not None and stop_event.is_set():
                raise wrap_error(exc, provider, attempt) from exc
            delay = policy.delay(attempt, exc)
            func.log(f"[{provider}] Transient error before first token ({type(exc).__name__}: {str(exc)[:120]}). "
                     f"Retry {attempt}/{policy.max_retries} in {delay:.1f}s", level="WARN")
            if not _wait(delay, stop_event):
                raise wrap_error(exc, provider, attempt) from exc
