"""
One-shot agent run (``ai --agent --msg ...``) printed with the chat UI's renderer.

Runs a single request to completion and exits, like the classic ``ConsoleIO`` mode,
but the output (status lines, tool calls, results, messages, turn summary) looks the
same as in the interactive chat. Works without a terminal too: colors are stripped
when stdout is not a TTY, and permission requests are denied when stdin is not one.

When the agent hands control back to USER (it finished, or it has a question) the run
ends; the printed ``--resume`` hint continues the same session with a new message.
"""

import re
import sys
from typing import Any, Callable, Dict, Optional, TextIO

from ai.agents.agent_io import PERMISSION_ALWAYS, PERMISSION_NO, PERMISSION_YES
from ai.agents.chat_ui import renderer as R
from ai.agents.chat_ui.bridge import ChatIO

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")
MAX_PROMPT_LINES = 6


class OneShotIO(ChatIO):
    """ChatIO that prints straight to stdout and asks for permission with blocking ``input()``."""

    # Handing control to USER ends the run (inherited from ChatIO): agents target USER
    # when they are done, so waiting for a reply would keep a one-shot run alive forever.

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
        super().__init__(R.LiveState(), self.write, lambda: None)

    def write(self, text: str) -> None:
        if not self.color:
            text = ANSI_ESCAPE.sub("", text)
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
    try:
        io.write(R.render_user_message(_prompt_preview(prompt)))
        io.state.start_turn()
        session_id = session_id or str(uuid.uuid4())
        result = orchestrator.run_loop(user_prompt=prompt, session_id=session_id)
        reason = getattr(result, "reason", "error")
        io.write(R.render_turn_summary("done" if reason == "awaiting_user" else reason, io.state))
        if reason in ("awaiting_user", "api_error"):
            # The session is saved: the same conversation continues with --resume.
            io.write(f"{R.GREY}  continue: ai --agent --resume {session_id} --msg \"...\"{R.RESET}")
        return result
    finally:
        io.state.busy = False
        orchestrator.close()
