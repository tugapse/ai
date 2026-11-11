"""
Pure rendering helpers for the agent chat UI.

Everything here returns ANSI strings so it can be printed through
prompt_toolkit's ``patch_stdout(raw=True)`` from any thread, and unit-tested
without a terminal.
"""

import json
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
            main = _truncate(params[key], MAX_ARG_LEN)
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
        return True, status

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

def render_user_message(text: str) -> str:
    lines = text.rstrip().splitlines() or [""]
    first = f"{GREY}>{RESET} {BOLD}{lines[0]}{RESET}"
    rest = [f"  {BOLD}{line}{RESET}" for line in lines[1:]]
    return "\n" + "\n".join([first] + rest)


def render_event(event: AgentEvent) -> Optional[str]:
    """Converts an orchestrator event into committed output, or None if it is live-only."""
    t = event.type
    if t == AgentEventType.MESSAGE:
        body = event.text.strip()
        lines = body.splitlines() or [""]
        head = f"\n{TerminalUI.TEXT}{BULLET}{RESET} {lines[0]}"
        return head + ("\n" + _indent("\n".join(lines[1:])) if len(lines) > 1 else "")
    if t == AgentEventType.THOUGHT:
        return f"\n{GREY}{ITALIC}✻ {_indent(event.text.strip()).lstrip()}{RESET}"
    if t == AgentEventType.QUESTION:
        return f"\n{CYAN}? {event.text.strip()}{RESET}"
    if t == AgentEventType.TOOL_CALL:
        tool = event.data.get("tool", "?")
        args = summarize_params(tool, event.data.get("params", {}))
        return f"\n{GREEN}{BULLET}{RESET} {BOLD}{tool}{RESET}({args})"
    if t == AgentEventType.TOOL_RESULT:
        tool = event.data.get("tool", "?")
        ok, summary = summarize_result(event.data.get("result"))
        status = (event.data.get("result") or {}).get("status", "") if isinstance(event.data.get("result"), dict) else ""
        color = GREY if ok else RED
        # Refused calls never produced a TOOL_CALL line, so name the tool.
        prefix = f"{RED}{BULLET}{RESET} {BOLD}{tool}{RESET}\n" if status in ("DENIED", "UNAUTHORIZED") else ""
        return f"{prefix}  {GREY}{ELBOW}{RESET}  {color}{summary}{RESET}"
    if t == AgentEventType.SPECIALIST:
        return f"\n{CYAN}{BULLET}{RESET} specialist {BOLD}{event.data.get('tool')}{RESET} generating…"
    if t == AgentEventType.INFO:
        if event.text == "Pipeline execution finished.":
            return None  # the turn summary covers this
        return f"{GREY}· {event.text}{RESET}"
    if t == AgentEventType.ERROR:
        return f"{RED}✗ {event.text}{RESET}"
    if t == AgentEventType.HEADER:
        if event.data.get("resumed") is not None:
            return None  # session start/resume headers are noise in chat mode
        subtitle = event.data.get("subtitle", "")
        return f"{RED}── {event.text}{(' · ' + subtitle) if subtitle else ''}{RESET}"
    return None  # STATUS / LLM_REQUEST are live-only


def render_status_line(agent: str, status: str, phase: str = "") -> str:
    """Committed line for the agent's reported status (manifest.current_priority)."""
    phase_txt = f"{DIM}[{phase}]{RESET}{GREY} " if phase else ""
    return f"\n{TerminalUI.PRIMARY}✻{RESET} {GREY}{phase_txt}{status.strip()}{RESET}"


def render_turn_summary(reason: str, state: LiveState) -> str:
    stats = f"{format_duration(state.elapsed())} · {state.turn_steps} step{'s' if state.turn_steps != 1 else ''} · {format_tokens(state.turn_tokens)} tokens"
    if reason == "cancelled":
        return f"  {GREY}{ELBOW}{RESET}  {RED}Interrupted{RESET} {GREY}· {stats}{RESET}"
    if reason == "awaiting_user":
        return f"{GREY}  (waiting for your reply · {stats}){RESET}"
    if reason == "error":
        return f"{RED}✗ Turn ended with an error{RESET} {GREY}· {stats}{RESET}"
    if reason == "max_iterations":
        return f"{RED}✗ Iteration budget exhausted{RESET} {GREY}· {stats}{RESET}"
    return f"{GREY}✻ Done in {stats}{RESET}"


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
    task = f"\n  {GREY}{ELBOW}  {_truncate(state.task, 90)}{RESET}" if state.task and not state.cancelling else ""
    queued = f"\n  {GREY}queued: {_truncate(state.queued[0], 80)}{' (+' + str(len(state.queued) - 1) + ')' if len(state.queued) > 1 else ''}{RESET}" if state.queued else ""
    return f"{TerminalUI.PRIMARY}{spinner} {label}{RESET} {GREY}({' · '.join(details)}){RESET}{task}{queued}"


def render_status_bar(model: str, session_id: str, pipeline: str, state: LiveState, hint: str = "") -> str:
    parts = [model or "no model", f"session {session_id[:8]}", pipeline]
    if state.context_pressure is not None:
        parts.append(f"ctx {min(state.context_pressure, 9.99):.0%}")
    left = " · ".join(parts)
    right = hint or "/help · ctrl+j newline · ctrl+c exit"
    return f"{GREY} {left}   {DIM}{right}{RESET}"


def render_transcript(entries, session_id: str, request: str = "") -> str:
    """Recent conversation shown when a chat opens on an existing session."""
    lines = [f"{GREY}── resumed session {session_id[:8]}{(' · ' + _truncate(request, 60)) if request else ''} ──{RESET}"]
    if not entries:
        lines.append(f"{GREY}  (no messages to show){RESET}")
    for entry in entries:
        if entry.get("role") == "user":
            lines.append(render_user_message(entry.get("text", "")).lstrip("\n"))
        else:
            text = str(entry.get("text", "")).strip()
            body = text.splitlines() or [""]
            lines.append(f"{TerminalUI.TEXT}{BULLET}{RESET} {body[0]}" + ("\n" + _indent("\n".join(body[1:])) if len(body) > 1 else ""))
    lines.append(f"{GREY}──{RESET}")
    return "\n".join(lines)


def render_permission(tool: str, params: Dict[str, Any]) -> str:
    from ai.agents.tool_preview import describe_tool_request

    lines = [f"{TerminalUI.WARN}{BOLD}Permission required{RESET}"]
    lines += describe_tool_request(tool, params)
    lines.append(f"  {GREEN}[y]{RESET} allow   {GREEN}[a]{RESET} allow all '{tool}' this session   {RED}[n]{RESET} deny {GREY}(esc){RESET}")
    return "\n".join(lines)
