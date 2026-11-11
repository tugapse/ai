"""
Inline session picker used by ``ai --resume``.

    Resume an agent session  (↑/↓ move · type to filter · enter open · esc cancel)
    filter: api_
    ❯ 2m ago    3f2a91c0  12 turns  Build a new API endpoint
      yesterday 9be01d22   4 turns  Fix the failing tests
"""

import time
from typing import Any, Dict, List, Optional

from prompt_toolkit.application import Application
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl

from ai.agents.chat_ui import renderer as R

VISIBLE_ROWS = 12


def format_age(timestamp: float, now: Optional[float] = None) -> str:
    """Human-friendly relative time ('just now', '5m ago', '3h ago', 'yesterday', '4d ago')."""
    delta = max(0, int((now or time.time()) - timestamp))
    if delta < 60:
        return "just now"
    if delta < 3600:
        return f"{delta // 60}m ago"
    if delta < 86400:
        return f"{delta // 3600}h ago"
    if delta < 172800:
        return "yesterday"
    return f"{delta // 86400}d ago"


def _one_line(text: Any, limit: int) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def filter_sessions(sessions: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """Case-insensitive match on id, original request and last message."""
    query = query.strip().lower()
    if not query:
        return list(sessions)
    return [
        s for s in sessions
        if query in str(s.get("session_id", "")).lower()
        or query in str(s.get("user_request") or "").lower()
        or query in str(s.get("last_user_message") or "").lower()
    ]


def render_session_row(session: Dict[str, Any], selected: bool, width: int = 100, now: Optional[float] = None) -> str:
    age = format_age(session.get("updated_at", 0), now)
    turns = session.get("turns", 0)
    request = session.get("user_request") or "(no request)"
    last = session.get("last_user_message")
    meta = f"{age:<10} {str(session.get('session_id', ''))[:8]}  {turns:>3} turn{'s' if turns != 1 else ' '}  "
    room = max(20, width - len(meta) - 4)
    summary = _one_line(request, room)
    if last and last != request and len(summary) < room - 10:
        summary += f"{R.GREY} → {_one_line(last, room - len(summary) - 3)}"
    pointer = f"{R.TerminalUI.PRIMARY}❯{R.RESET} " if selected else "  "
    body = f"{R.BOLD}{summary}{R.RESET}" if selected else summary
    return f"{pointer}{R.GREY}{meta}{R.RESET}{body}{R.RESET}"


class SessionPicker:
    """Keyboard-driven list of sessions. ``run()`` returns the chosen session id or None."""

    def __init__(self, sessions: List[Dict[str, Any]]):
        self.sessions = sessions
        self.query = ""
        self.index = 0
        self.app = self._build()

    @property
    def visible(self) -> List[Dict[str, Any]]:
        return filter_sessions(self.sessions, self.query)

    def _text(self):
        rows = self.visible
        try:
            width = self.app.output.get_size().columns
        except Exception:
            width = 100
        lines = [f"{R.BOLD}Resume an agent session{R.RESET}  {R.GREY}(↑/↓ move · type to filter · enter open · esc cancel){R.RESET}"]
        if self.query:
            lines.append(f"{R.GREY}filter:{R.RESET} {self.query}")
        if not rows:
            lines.append(f"  {R.GREY}no sessions match{R.RESET}")
            return ANSI("\n".join(lines))

        self.index = max(0, min(self.index, len(rows) - 1))
        start = max(0, min(self.index - VISIBLE_ROWS // 2, len(rows) - VISIBLE_ROWS))
        end = min(len(rows), start + VISIBLE_ROWS)
        if start > 0:
            lines.append(f"  {R.GREY}↑ {start} more{R.RESET}")
        now = time.time()
        for i in range(start, end):
            lines.append(render_session_row(rows[i], i == self.index, width, now))
        if end < len(rows):
            lines.append(f"  {R.GREY}↓ {len(rows) - end} more{R.RESET}")
        return ANSI("\n".join(lines))

    def _build(self) -> Application:
        kb = KeyBindings()

        @kb.add("up")
        @kb.add("c-p")
        def _up(event):
            self.index = max(0, self.index - 1)

        @kb.add("down")
        @kb.add("c-n")
        def _down(event):
            self.index = min(max(0, len(self.visible) - 1), self.index + 1)

        @kb.add("pageup")
        def _pgup(event):
            self.index = max(0, self.index - VISIBLE_ROWS)

        @kb.add("pagedown")
        def _pgdn(event):
            self.index = min(max(0, len(self.visible) - 1), self.index + VISIBLE_ROWS)

        @kb.add("enter")
        def _enter(event):
            rows = self.visible
            event.app.exit(result=rows[self.index]["session_id"] if rows else None)

        @kb.add("escape", eager=True)
        @kb.add("c-c")
        @kb.add("c-d")
        def _cancel(event):
            event.app.exit(result=None)

        @kb.add("backspace")
        def _backspace(event):
            self.query = self.query[:-1]
            self.index = 0

        @kb.add("<any>")
        def _type(event):
            char = event.data
            if char and char.isprintable() and len(char) == 1:
                self.query += char
                self.index = 0

        return Application(
            layout=Layout(HSplit([Window(FormattedTextControl(self._text), dont_extend_height=True, wrap_lines=False)])),
            key_bindings=kb,
            full_screen=False,
            erase_when_done=True,
            mouse_support=False,
        )

    def run(self) -> Optional[str]:
        return self.app.run()


def pick_session(sessions: List[Dict[str, Any]]) -> Optional[str]:
    """Shows the picker and returns the selected session id (None if cancelled or empty)."""
    if not sessions:
        return None
    return SessionPicker(sessions).run()


def resolve_session_id(sessions: List[Dict[str, Any]], query: str) -> Optional[str]:
    """Resolves an exact id or a unique id prefix. Raises ValueError when ambiguous."""
    ids = [str(s.get("session_id", "")) for s in sessions]
    if query in ids:
        return query
    matches = [i for i in ids if i.startswith(query)]
    if len(matches) > 1:
        raise ValueError(f"Session prefix '{query}' is ambiguous ({len(matches)} matches).")
    return matches[0] if matches else None
