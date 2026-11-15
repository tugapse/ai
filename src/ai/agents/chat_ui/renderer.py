"""
Pure rendering helpers for the agent chat UI.

Everything here returns ANSI strings so it can be printed through
prompt_toolkit's ``patch_stdout(raw=True)`` from any thread, and unit-tested
without a terminal.
"""

import json
import os
import re
import shutil
import textwrap
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from ai.agents.agent_io import AgentEvent, AgentEventType
from ai.agents.terminal_ui import TerminalUI

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
RED = "\033[38;5;167m"
GREEN = "\033[38;5;108m"
CYAN = "\033[38;5;110m"
GREY = "\033[38;5;245m"
USER_BG = "\033[48;5;236m"

BULLET = "⏺"
ELBOW = "⎿"
SPINNER_FRAMES = ["✻", "✼", "✽", "✾", "✿", "❀", "✿", "✾", "✽", "✼"]

MAX_ARG_LEN = 70
MAX_RESULT_LEN = 100


@dataclass
class LiveState:
    """Mutable state shown in the live (non-committed) part of the UI."""
    busy: bool = False
    cancelling: bool = False
    agent: str = ""
    task: str = ""
    phase: str = ""
    iteration: int = 0
    max_iterations: int = 0
    tool: str = ""               # tool currently running, with its argument summary
    tokens: int = 0              # tokens in the current model call
    turn_tokens: int = 0         # tokens in the whole turn
    turn_steps: int = 0
    turn_started: float = 0.0
    context_pressure: Optional[float] = None
    queued: list = field(default_factory=list)

    def start_turn(self):
        self.busy = True
        self.cancelling = False
        self.tokens = 0
        self.turn_tokens = 0
        self.turn_steps = 0
        self.phase = "starting"
        self.turn_started = time.monotonic()

    def elapsed(self) -> float:
        return time.monotonic() - self.turn_started if self.turn_started else 0.0


# ---------------------------------------------------------------- helpers

def _truncate(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _indent(text: str, prefix: str = "  ") -> str:
    lines = str(text).rstrip().splitlines() or [""]
    return "\n".join(prefix + line if line else line for line in lines)


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def visible_len(text: str) -> int:
    return len(_ANSI_RE.sub("", text))


def terminal_width(default: int = 100) -> int:
    try:
        return max(40, shutil.get_terminal_size((default, 24)).columns)
    except Exception:
        return default


def _display_path(text: str) -> str:
    """Paths are shown relative to the AI root: '@ROOT/' adds nothing on screen."""
    return str(text).replace("@ROOT/", "")


def format_tokens(count: int) -> str:
    return f"{count / 1000:.1f}k" if count >= 1000 else str(count)


def format_duration(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}m {seconds % 60:02d}s"


def summarize_params(tool: str, params: Dict[str, Any]) -> str:
    """One-line summary of a tool call's arguments."""
    if not isinstance(params, dict) or not params:
        return ""
    if "command" in params:
        return _truncate(params["command"], MAX_ARG_LEN)
    for key in ("path", "file_path", "pattern", "query", "url"):
        if key in params and params[key]:
            extra = len(params) - 1
            main = _truncate(_display_path(params[key]), MAX_ARG_LEN)
            return main if extra <= 0 or key != "path" else f"{main}, +{extra}"
    parts = []
    for key, value in params.items():
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        parts.append(f"{key}={value}")
    return _truncate(", ".join(parts), MAX_ARG_LEN)


def summarize_result(result: Any) -> Tuple[bool, str]:
    """Returns (ok, short description) for a tool result."""
    if not isinstance(result, dict):
        return True, _truncate(result, MAX_RESULT_LEN)

    status = str(result.get("status", "SUCCESS")).upper()
    ok = status in ("SUCCESS", "OK")

    if not ok:
        detail = result.get("error") or result.get("message") or result.get("result") or ""
        return False, f"{status}" + (f" · {_truncate(detail, MAX_RESULT_LEN)}" if detail else "")

    payload = None
    for key in ("result", "content", "output", "stdout", "summary", "message", "data"):
        if result.get(key) not in (None, ""):
            payload = result[key]
            break
    if payload is None:
        return True, ""  # a green bullet already says it worked

    if isinstance(payload, (list, tuple)):
        return True, f"{len(payload)} items"
    if isinstance(payload, dict):
        return True, f"{len(payload)} fields"
    text = str(payload)
    lines = text.count("\n") + 1
    if lines > 1:
        return True, f"{lines} lines"
    return True, _truncate(text, MAX_RESULT_LEN)


# ---------------------------------------------------------------- committed output
#
# Visual language:
#   user message   full-width shaded block           (what you said)
#   step header    ✻ title · phase                   (what the agent set out to do)
#     narration    dim, indented under the step      (what it says while working)
#     ⏺ tool(args) → result, one line, indented      (what it did)
#   answer         ⏺ text, bright, spaced            (what it tells you)
#   turn summary   ✻ Done in … closes the turn

def render_user_message(text: str, width: Optional[int] = None) -> str:
    width = (width or terminal_width()) - 1  # never touch the last column (avoids a double wrap)
    rows = []
    for i, line in enumerate(text.rstrip().splitlines() or [""]):
        wrapped = textwrap.wrap(line, width - 4, replace_whitespace=False, drop_whitespace=False) or [""]
        for j, part in enumerate(wrapped):
            marker = f"{GREY}>{RESET}{USER_BG}" if i == 0 and j == 0 else " "
            pad = " " * max(0, width - 3 - len(part))
            rows.append(f"{USER_BG} {marker} {BOLD}{part}{RESET}{USER_BG}{pad}{RESET}")
    return "\n" + "\n".join(rows)


def render_message(text: str, narration: bool = False, width: Optional[int] = None) -> str:
    """An agent message (Markdown): dim narration under the current step, or a spaced answer."""
    from ai.agents.chat_ui.markdown import render_markdown

    width = (width or terminal_width()) - 1
    if narration:
        lines = render_markdown(text.strip(), width - 2, base=GREY)
        return "\n".join(f"  {line}" if line else "" for line in lines)
    lines = render_markdown(text.strip(), width - 2)
    head = f"\n{TerminalUI.TEXT}{BULLET}{RESET} {lines[0]}"
    return head + "".join(f"\n  {line}" if line else "\n" for line in lines[1:])


def render_tool_line(tool: str, params: Dict[str, Any], result: Any = None, has_result: bool = False) -> str:
    """'⏺ tool(args) → summary' on one line; the bullet is green, or red on failure."""
    args = summarize_params(tool, params or {})
    call = f"{BOLD}{tool}{RESET}{GREY}({args}){RESET}" if args else f"{BOLD}{tool}{RESET}"
    if not has_result:
        return f"  {GREEN}{BULLET}{RESET} {call}"
    ok, summary = summarize_result(result)
    if ok:
        tail = f" {GREY}→ {summary}{RESET}" if summary else ""
        return f"  {GREEN}{BULLET}{RESET} {call}{tail}"
    return f"  {RED}{BULLET}{RESET} {call}\n    {GREY}{ELBOW}{RESET}  {RED}{summary}{RESET}"


def render_event(event: AgentEvent) -> Optional[str]:
    """Converts an orchestrator event into committed output, or None if it is live-only.

    Stateless; ``TranscriptFormatter`` adds the grouping used by the chat.
    """
    t = event.type
    if t == AgentEventType.MESSAGE:
        return render_message(event.text, narration=bool(event.data.get("narration")))
    if t == AgentEventType.THOUGHT:
        return f"{GREY}{ITALIC}{_indent('∴ ' + event.text.strip(), '  ')}{RESET}"
    if t == AgentEventType.QUESTION:
        return f"\n{CYAN}? {event.text.strip()}{RESET}"
    if t == AgentEventType.TOOL_CALL:
        return render_tool_line(event.data.get("tool", "?"), event.data.get("params", {}))
    if t == AgentEventType.TOOL_RESULT:
        tool = event.data.get("tool", "?")
        result = event.data.get("result")
        status = result.get("status", "") if isinstance(result, dict) else ""
        if status in ("DENIED", "UNAUTHORIZED"):
            # Refused calls never produced a TOOL_CALL line, so name the tool.
            return render_tool_line(tool, event.data.get("params", {}), result, has_result=True)
        ok, summary = summarize_result(result)
        if ok and not summary:
            return None
        return f"    {GREY}{ELBOW}{RESET}  {GREY if ok else RED}{summary}{RESET}"
    if t == AgentEventType.INFO:
        if event.text == "Pipeline execution finished.":
            return None  # the turn summary covers this
        return f"{GREY}  · {event.text}{RESET}"
    if t == AgentEventType.ERROR:
        return f"{RED}✗ {event.text}{RESET}"
    if t == AgentEventType.HEADER:
        if event.data.get("resumed") is not None:
            return None  # session start/resume headers are noise in chat mode
        subtitle = event.data.get("subtitle", "")
        return f"\n{RED}── {event.text}{(' · ' + subtitle) if subtitle else ''}{RESET}"
    return None  # STATUS / LLM_REQUEST are live-only


def render_status_line(agent: str, status: str, phase: str = "") -> str:
    """Step header: the agent's reported status (manifest.current_priority)."""
    phase_txt = f"  {GREY}· {phase}{RESET}" if phase else ""
    return f"\n{TerminalUI.PRIMARY}✻{RESET} {TerminalUI.TEXT}{status.strip()}{RESET}{phase_txt}"


class TranscriptFormatter:
    """Groups the event stream into steps for the chat transcript.

    A tool call is held back until its result arrives so both fit on one line; any
    other output (or ``flush``) prints the held call on its own first.
    """

    def __init__(self):
        self._pending: Optional[Tuple[str, Dict[str, Any]]] = None
        self._phase = ""

    def reset(self) -> None:
        self._pending = None
        self._phase = ""

    def flush(self) -> Optional[str]:
        if self._pending is None:
            return None
        tool, params = self._pending
        self._pending = None
        return render_tool_line(tool, params)

    def status(self, agent: str, text: str, phase: str = "") -> str:
        # The phase is shown when it changes, not repeated on every step.
        shown = phase if phase and phase != self._phase else ""
        self._phase = phase or self._phase
        return self._join(self.flush(), render_status_line(agent, text, shown))

    def feed(self, event: AgentEvent) -> Optional[str]:
        t = event.type
        if t == AgentEventType.TOOL_CALL:
            held = self.flush()
            self._pending = (event.data.get("tool", "?"), event.data.get("params", {}) or {})
            return held
        if t == AgentEventType.TOOL_RESULT and self._pending and self._pending[0] == event.data.get("tool", "?"):
            tool, params = self._pending
            self._pending = None
            return render_tool_line(tool, params, event.data.get("result"), has_result=True)
        text = render_event(event)
        if text is None:
            return None
        return self._join(self.flush(), text)

    @staticmethod
    def _join(first: Optional[str], second: Optional[str]) -> Optional[str]:
        parts = [p for p in (first, second) if p]
        return "\n".join(parts) if parts else None


def render_turn_summary(reason: str, state: LiveState, width: Optional[int] = None) -> str:
    """A rule that closes the turn: everything above it is the past."""
    stats = f"{format_duration(state.elapsed())} · {state.turn_steps} step{'s' if state.turn_steps != 1 else ''} · {format_tokens(state.turn_tokens)} tokens"
    labels = {
        "cancelled": (RED, "✗ Interrupted"),
        "awaiting_user": (CYAN, "? Waiting for your reply"),
        "error": (RED, "✗ Turn ended with an error"),
        "api_error": (RED, "✗ Model API unavailable"),
        "max_iterations": (RED, "✗ Iteration budget exhausted"),
    }
    color, label = labels.get(reason, (GREEN, "✓ Done in"))
    sep = " " if label.endswith(" in") else " · "
    text = f" {color}{label}{RESET}{GREY}{sep}{stats} "
    width = min((width or terminal_width()) - 1, 100)
    rule = "─" * max(3, width - 3 - visible_len(text))
    return f"\n{GREY}──{text}{rule}{RESET}"


ROBOT_ART = [
    "    ╷    ",
    " ╭──┴──╮ ",
    " │ ◉ ◉ │ ",
    " │ ╶─╴ │ ",
    " ╰─┬─┬─╯ ",
    "╭──┴─┴──╮",
]
ROBOT_WIDTH = max(len(line) for line in ROBOT_ART)


def _robot_rows():
    eye = f"{CYAN}◉{TerminalUI.PRIMARY}"
    return [f"{TerminalUI.PRIMARY}{line.ljust(ROBOT_WIDTH).replace('◉', eye)}{RESET}" for line in ROBOT_ART]


def render_banner(model: str, pipeline: str, session_id: str, cwd: str, width: Optional[int] = None) -> str:
    """Welcome card shown when the chat opens."""
    home = os.path.expanduser("~")
    if cwd.startswith(home):
        cwd = "~" + cwd[len(home):]
    inner = min((width or terminal_width()) - 2, 76) - 2
    title = f" {TerminalUI.PRIMARY}✻{RESET} {BOLD}JARVIS{RESET} {GREY}agent{RESET} "
    rows = [
        "",
        f"  {GREY}model    {RESET} {model}",
        f"  {GREY}pipeline {RESET} {pipeline}",
        f"  {GREY}session  {RESET} {session_id[:8]}",
        f"  {GREY}cwd      {RESET} {_truncate(cwd, inner - 13 - (ROBOT_WIDTH + 4 if inner >= 52 else 0))}",
        "",
    ]
    # A small robot on the right, when there is room for it.
    if inner >= 52:
        rows = [row + " " * max(0, inner - visible_len(row) - ROBOT_WIDTH - 3) + art + "   "
                for row, art in zip(rows, _robot_rows())]
    border = "\033[38;5;240m"
    top = f"{border}╭─{RESET}{title}{border}{'─' * max(0, inner - 1 - visible_len(title))}╮{RESET}"
    body = [f"{border}│{RESET}{row}{' ' * max(0, inner - visible_len(row))}{border}│{RESET}" for row in rows]
    bottom = f"{border}╰{'─' * inner}╯{RESET}"
    hint = f"  {GREY}/help commands · @file attach · esc interrupt · ctrl+d exit{RESET}"
    return "\n".join([top, *body, bottom, hint])


# ---------------------------------------------------------------- live area

def render_live_line(state: LiveState, frame: int) -> str:
    """The spinner line shown while a turn is running."""
    if not state.busy:
        return ""
    spinner = SPINNER_FRAMES[frame % len(SPINNER_FRAMES)]
    if state.cancelling:
        label = "Interrupting…"
    else:
        agent = state.agent or "agent"
        label = f"{agent} {state.phase or 'working'}…"
    details = [format_duration(state.elapsed())]
    if state.max_iterations:
        details.append(f"step {state.iteration}/{state.max_iterations}")
    if state.tokens:
        details.append(f"{format_tokens(state.tokens)} tok")
    details.append("esc to interrupt")
    sub = []
    if state.task and not state.cancelling:
        sub.append(f"  {GREY}{ELBOW}  {_truncate(state.task, 90)}{RESET}")
    if state.tool and not state.cancelling:
        sub.append(f"  {GREY}   {GREEN}{BULLET}{RESET} {GREY}{_truncate(state.tool, 86)}{RESET}")
    task = "".join("\n" + line for line in sub)
    queued = f"\n  {GREY}queued: {_truncate(state.queued[0], 80)}{' (+' + str(len(state.queued) - 1) + ')' if len(state.queued) > 1 else ''}{RESET}" if state.queued else ""
    return f"\n{TerminalUI.PRIMARY}{spinner} {label}{RESET} {GREY}({' · '.join(details)}){RESET}{task}{queued}"


def render_status_bar(model: str, session_id: str, pipeline: str, state: LiveState, hint: str = "") -> str:
    parts = [model or "no model", f"session {session_id[:8]}", pipeline]
    if state.context_pressure is not None:
        parts.append(f"ctx {min(state.context_pressure, 9.99):.0%}")
    left = " · ".join(parts)
    right = hint or "/help · ctrl+j newline · ctrl+c exit"
    return f"{GREY} {left}   {DIM}{right}{RESET}"


def render_transcript(entries, session_id: str, request: str = "") -> str:
    """Recent conversation shown when a chat opens on an existing session."""
    lines = [f"\n{GREY}── resumed session {session_id[:8]}{(' · ' + _truncate(request, 60)) if request else ''} ──{RESET}"]
    if not entries:
        lines.append(f"{GREY}  (no messages to show){RESET}")
    for entry in entries:
        if entry.get("role") == "user":
            lines.append(render_user_message(entry.get("text", "")))
        else:
            lines.append(render_message(str(entry.get("text", ""))))
    lines.append(f"\n{GREY}── end of history ──{RESET}")
    return "\n".join(lines)


def render_permission(tool: str, params: Dict[str, Any]) -> str:
    from ai.agents.tool_preview import describe_tool_request

    lines = [f"{TerminalUI.WARN}{BOLD}Permission required{RESET}"]
    lines += describe_tool_request(tool, params)
    lines.append(f"  {GREEN}[y]{RESET} allow   {GREEN}[a]{RESET} always (see above)   {RED}[n]{RESET} deny {GREY}(esc){RESET}")
    return "\n".join(lines)
