"""
One-shot agent run (``ai agent --msg ...``) printed with the chat UI's renderer.

Runs a single request to completion and exits, like the classic ``ConsoleIO`` mode,
but the output (status lines, tool calls, results, messages, turn summary) looks the
same as in the interactive chat. Works without a terminal too: colors are stripped
when stdout is not a TTY, and permission requests are denied when stdin is not one.

When the agent hands control back to USER (it finished, or it has a question):
- with a terminal, the user replies and the run goes on; Ctrl+C (or Ctrl+D) ends it;
- without one, the pipeline's ``oneshot_auto_reply`` (if set) is sent as the reply, as long as
  the agent ran a tool since the previous automatic reply; otherwise the run ends.
When the run ends, the printed ``--resume`` hint continues the same session with a new message.
"""

import re
import signal
import sys
import threading
import time
from typing import Any, Callable, Dict, Optional, TextIO

from ai.agents.agent_io import AgentEventType, PERMISSION_ALWAYS, PERMISSION_NO, PERMISSION_YES
from ai.agents.chat_ui import renderer as R
from ai.agents.chat_ui.bridge import ChatIO

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")
MAX_PROMPT_LINES = 6


class OneShotIO(ChatIO):
    """ChatIO that prints straight to stdout and asks for permission with blocking ``input()``."""

    def __init__(self, out: Optional[TextIO] = None, read: Callable[[str], str] = input,
                 interactive: Optional[bool] = None):
        """
        Args:
            out: Where output goes (default: sys.stdout).
            read: Reads one line of user input (default: input()).
            interactive: Whether the user can answer prompts (default: stdin is a TTY).
        """
        self.out = out or sys.stdout
        self.read = read
        self.interactive = sys.stdin.isatty() if interactive is None else interactive
        self.color = bool(getattr(self.out, "isatty", lambda: False)())
        self.one_shot = True
        self.can_ask_permission = self.interactive
        self.auto_reply: Optional[str] = None
        self._tools_since_reply = 0
        self._auto_replied = False
        super().__init__(R.LiveState(), self.write, lambda: None)

    @property
    def blocking_user_input(self) -> bool:
        """Questions are answered inline when someone (or the auto reply) can answer them."""
        return self.interactive or bool(self.auto_reply)

    def emit(self, event) -> None:
        if event.type == AgentEventType.TOOL_RESULT:
            self._tools_since_reply += 1
        super().emit(event)

    def request_user_input(self, agent: str, prompt: str) -> str:
        """Reads the reply to a USER hand-off. Ctrl+C / Ctrl+D ends the run (returns "")."""
        self.flush()
        if not self.interactive:
            # Agents also target USER when they are done: reply again only after progress.
            if self._auto_replied and self._tools_since_reply == 0:
                return ""
            self._auto_replied, self._tools_since_reply = True, 0
            self.write(f"{R.GREY}  › {self.auto_reply}  (oneshot_auto_reply){R.RESET}")
            return self.auto_reply or ""
        self.write(f"{R.GREY}  reply to continue, Ctrl+C to finish{R.RESET}")
        started = time.monotonic()
        reply = ""
        # The app's SIGINT handler shuts the program down; here Ctrl+C only ends the run.
        previous = None
        if threading.current_thread() is threading.main_thread():
            previous = signal.signal(signal.SIGINT, signal.default_int_handler)
        try:
            # An empty line is not an answer (easy to hit by mistake): ask again.
            while not reply:
                reply = self.read("  › ").strip()
        except (EOFError, KeyboardInterrupt, OSError):
            reply = ""
            self.write("")
        finally:
            if previous is not None:
                signal.signal(signal.SIGINT, previous)
            # Time spent waiting for the user is not part of the run.
            if self.state.turn_started:
                self.state.turn_started += time.monotonic() - started
        self._tools_since_reply = 0
        return reply

    def write(self, text: str) -> None:
        if not self.color:
            text = "\n".join(line.rstrip() for line in ANSI_ESCAPE.sub("", text).split("\n"))
        self.out.write(text + "\n")
        self.out.flush()

    def request_permission(self, tool: str, params: Dict[str, Any]) -> str:
        self.write("\n" + R.render_permission(tool, params))
        if not self.interactive:
            self.write(f"  {R.RED}denied: no terminal to ask for permission{R.RESET}")
            return PERMISSION_NO
        try:
            choice = self.read("  allow? [y/a/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return PERMISSION_NO
        if choice in ("a", "all"):
            return PERMISSION_ALWAYS
        if choice in ("y", "yes"):
            return PERMISSION_YES
        return PERMISSION_NO


def _prompt_preview(prompt: str) -> str:
    """The request as echoed at the top of the run; long task templates are shortened."""
    lines = prompt.strip().splitlines() or [""]
    if len(lines) <= MAX_PROMPT_LINES:
        return "\n".join(lines)
    return "\n".join(lines[:MAX_PROMPT_LINES] + [f"… (+{len(lines) - MAX_PROMPT_LINES} lines)"])


def run_one_shot(prog, prompt: str, pipeline: str = "default.json", session_id: Optional[str] = None,
                 directory_manager=None, io: Optional[OneShotIO] = None):
    """
    Runs one agent request to completion with chat-style output.

    Returns:
        The orchestrator's RunResult.

    Raises:
        ValueError: If the pipeline cannot be loaded or the LLM is not available.
    """
    import uuid
    from ai.agents.agent import build_orchestrator

    io = io or OneShotIO()
    orchestrator = build_orchestrator(prog, pipeline, io=io, directory_manager=directory_manager)
    orchestrator.llm_connector.on_token = io.on_token
    io.auto_reply = (getattr(orchestrator, "pipeline_config", None) or {}).get("oneshot_auto_reply") or None
    try:
        io.write(R.render_user_message(_prompt_preview(prompt)))
        io.state.start_turn()
        session_id = session_id or str(uuid.uuid4())
        result = orchestrator.run_loop(user_prompt=prompt, session_id=session_id)
        reason = getattr(result, "reason", "error")
        io.flush()
        io.write(R.render_turn_summary("done" if reason == "awaiting_user" else reason, io.state))
        if getattr(orchestrator, "_approval_stop", None):
            # Stopped before a tool listed in oneshot_hil_tools: approve it in the interactive chat.
            io.write(f"{R.GREY}  approve and continue: ai agent --resume {session_id}{R.RESET}")
        elif reason in ("awaiting_user", "api_error"):
            # The session is saved: the same conversation continues with --resume.
            io.write(f"{R.GREY}  continue: ai agent --resume {session_id} --msg \"...\"{R.RESET}")
        return result
    finally:
        io.state.busy = False
        orchestrator.close()
