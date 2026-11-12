"""
Thread bridge between the orchestrator (worker thread) and the chat UI (asyncio loop).

Committed output is printed directly: under ``patch_stdout`` prints from any
thread are routed above the live area. Live state changes only mutate
``LiveState`` and invalidate the application. Permission requests block the
worker thread on a future resolved by the UI.
"""

import asyncio
import concurrent.futures
import sys
import time
from typing import Any, Callable, Dict, Optional

from ai.agents.agent_io import AgentEvent, AgentEventType, AgentIO, PERMISSION_NO
from ai.agents.chat_ui.renderer import LiveState, render_event, render_status_line


class ChatIO(AgentIO):
    """AgentIO implementation used by the interactive chat UI."""

    # A USER-targeted question ends the turn; the next chat message is the reply.
    blocking_user_input = False

    def __init__(
        self,
        state: LiveState,
        write: Callable[[str], None],
        invalidate: Callable[[], None],
        permission_handler: Optional[Callable[[str, Dict[str, Any]], "asyncio.Future"]] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        """
        Args:
            state: Shared live state rendered by the UI.
            write: Prints committed (ANSI) output.
            invalidate: Requests a UI redraw (must be thread-safe).
            permission_handler: Coroutine function ``(tool, params) -> 'y'|'n'|'a'`` run on the UI loop.
            loop: The UI event loop.
        """
        self.state = state
        self.write = write
        self.invalidate = invalidate
        self.permission_handler = permission_handler
        self.loop = loop
        self._pending_permission: Optional[concurrent.futures.Future] = None

    # ---------------------------------------------------------------- events

    def emit(self, event: AgentEvent) -> None:
        state = self.state
        t = event.type

        if t == AgentEventType.STATUS:
            state.agent = event.agent or state.agent
            state.task = event.text
            state.iteration = event.data.get("iteration", state.iteration)
            state.max_iterations = event.data.get("max_iterations", state.max_iterations)
            pressure = event.data.get("context_pressure")
            if pressure is not None:
                state.context_pressure = pressure
        elif t == AgentEventType.LLM_REQUEST:
            state.agent = event.agent or state.agent
            state.tokens = 0
            state.turn_steps += 1
            state.phase = "thinking"
        elif t == AgentEventType.TOOL_CALL:
            state.phase = f"running {event.data.get('tool')}"
        elif t == AgentEventType.SPECIALIST:
            state.phase = f"specialist {event.data.get('tool')}"

        text = render_event(event)
        if t == AgentEventType.STATUS and event.data.get("fresh"):
            text = render_status_line(event.agent or state.agent, event.text, event.data.get("phase", ""))
        if text is not None:
            self.write(text)
        self.invalidate()

    def on_token(self, token: str) -> None:
        """Per-token callback from the LLM connector."""
        self.state.tokens += 1
        self.state.turn_tokens += 1
        self.invalidate()

    # ---------------------------------------------------------------- permission

    def request_permission(self, tool: str, params: Dict[str, Any]) -> str:
        if self.permission_handler is None or self.loop is None or self.state.cancelling:
            return PERMISSION_NO
        self.state.phase = "waiting for permission"
        self._drain_output()
        future = asyncio.run_coroutine_threadsafe(self.permission_handler(tool, params), self.loop)
        self._pending_permission = future
        try:
            return future.result()
        except (concurrent.futures.CancelledError, Exception):
            return PERMISSION_NO
        finally:
            self._pending_permission = None
            self.state.phase = "working"

    @staticmethod
    def _drain_output() -> None:
        """
        Makes sure everything already printed (status, message) is on screen before
        the permission box shows. Under patch_stdout, writes are batched by a
        background thread that flushes every ``sleep_between_writes`` seconds.
        """
        stdout = sys.stdout
        try:
            stdout.flush()
        except Exception:
            return
        delay = getattr(stdout, "sleep_between_writes", None)
        if delay:
            time.sleep(delay + 0.1)

    def cancel_pending(self) -> None:
        """Unblocks a worker waiting on a permission answer (treated as a denial)."""
        future = self._pending_permission
        if future is not None and not future.done():
            future.cancel()

    def request_user_input(self, agent: str, prompt: str) -> str:
        # Never called: blocking_user_input is False.
        return ""
