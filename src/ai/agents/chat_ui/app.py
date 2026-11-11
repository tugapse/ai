"""
Interactive agent chat built on prompt_toolkit.

Layout (inline, not full screen; finished output scrolls into the normal
terminal scrollback):

    ...committed output (messages, tool calls) printed above...
    ✻ MASTER thinking… (12s · step 3/300 · 412 tok · esc to interrupt)   <- live area
    ╭──────────────────────────────────────────────╮
    │ > _                                          │                     <- input
    ╰──────────────────────────────────────────────╯
     model · session · pipeline · ctx %          hints                   <- status bar

The orchestrator runs in a daemon worker thread; see ``bridge.ChatIO``.
"""

import asyncio
import os
import re
import threading
import time
import traceback
import uuid
from typing import Any, Dict, Iterable, List, Optional

from prompt_toolkit.application import Application
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.history import FileHistory, History, InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import ConditionalContainer, FloatContainer, Float, HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Frame, TextArea

import ai.functions as func
from ai.agents.agent_io import PERMISSION_ALWAYS, PERMISSION_NO, PERMISSION_YES
from ai.agents.chat_ui.bridge import ChatIO
from ai.agents.chat_ui import renderer as R
from ai.agents.chat_ui.commands import COMMANDS
from ai.chat.chat import PrefixCompleter

MAX_ATTACHMENT_BYTES = 100_000
_MENTION_RE = re.compile(r"(?<!\S)@(\S+)")


class AgentChatCompleter(Completer):
    """Completes /commands at the start of the input and @file mentions anywhere."""

    def __init__(self, commands: Dict[str, Any]):
        self.commands = commands
        self._files = PrefixCompleter([])

    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        text = document.text_before_cursor
        if text.startswith("/") and " " not in text:
            for name, cmd in self.commands.items():
                if name.startswith(text):
                    yield Completion(name, start_position=-len(text), display_meta=cmd.help)
            return
        word = document.get_word_before_cursor(WORD=True)
        if word.startswith("@"):
            yield from self._files._file_completion(word[1:])


def expand_mentions(text: str, max_bytes: int = MAX_ATTACHMENT_BYTES) -> str:
    """Appends the contents of @mentioned files that exist on disk."""
    blocks: List[str] = []
    seen = set()
    for match in _MENTION_RE.finditer(text):
        path = match.group(1).rstrip(".,;:!?)")
        if path in seen or not os.path.isfile(path):
            continue
        seen.add(path)
        try:
            size = os.path.getsize(path)
            if size > max_bytes:
                blocks.append(f"File: {path}\n(too large to attach: {size} bytes; read it with a tool if needed)")
                continue
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                blocks.append(f"File: {path}\nContent:\n{f.read()}")
        except OSError as e:
            blocks.append(f"File: {path}\n(could not read: {e})")
    if not blocks:
        return text
    return text + "\n\n--- Attached Files ---\n" + "\n---\n".join(blocks)


class AgentChatApp:
    """Interactive multi-turn chat with the agent orchestrator."""

    def __init__(self, prog, pipeline: str = "default.json", session_id: Optional[str] = None,
                 directory_manager=None, history: Optional[History] = None):
        self.prog = prog
        self.pipeline = pipeline
        self.directory_manager = directory_manager
        self.session_id = session_id or str(uuid.uuid4())

        self.state = R.LiveState()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.worker: Optional[threading.Thread] = None
        self.permission: Optional[tuple] = None
        self._permission_future: Optional[asyncio.Future] = None
        self._last_ctrl_c = 0.0
        self._hint = ""
        self._hint_until = 0.0

        self.io = ChatIO(self.state, self.write, self.invalidate, self._ask_permission)
        self.orchestrator = self._build_orchestrator(pipeline)

        self.input = TextArea(
            multiline=True,
            wrap_lines=True,
            prompt=ANSI(f"{R.GREY}>{R.RESET} "),
            completer=AgentChatCompleter(COMMANDS),
            complete_while_typing=True,
            history=history or self._make_history(),
            height=self._input_height,
            dont_extend_height=True,
            read_only=Condition(lambda: self.permission is not None),
        )
        self.app = self._build_application()

    # ---------------------------------------------------------------- setup

    def _build_orchestrator(self, pipeline: str):
        from ai.agents.agent import build_orchestrator

        orchestrator = build_orchestrator(self.prog, pipeline, io=self.io, directory_manager=self.directory_manager)
        orchestrator.llm_connector.on_token = self.io.on_token
        return orchestrator

    def _make_history(self) -> History:
        try:
            from ai.services.directory_manager import DirectoryManager
            dm = self.directory_manager or DirectoryManager()
            path = os.path.join(dm.get_user_directory(), "agent_chat_history")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            return FileHistory(path)
        except Exception:
            return InMemoryHistory()

    def _input_height(self) -> Dimension:
        # Leave room for the completion menu below the cursor while completing.
        if self.input.buffer.complete_state:
            return Dimension(min=8, max=12)
        return Dimension(min=1, max=10)

    def _build_application(self) -> Application:
        busy = Condition(lambda: self.state.busy)
        in_permission = Condition(lambda: self.permission is not None)

        live = ConditionalContainer(
            Window(FormattedTextControl(self._live_text), dont_extend_height=True, wrap_lines=True),
            filter=busy | in_permission,
        )
        # Stretchable spacer: absorbs the free rows below the cursor so the input box
        # and status bar stay pinned to the bottom of the terminal. Collapses to zero
        # once output fills the screen (or when the terminal can't report its cursor row).
        spacer = Window(height=Dimension(min=0, weight=1), dont_extend_height=False)
        body = HSplit([
            spacer,
            live,
            ConditionalContainer(Frame(self.input), filter=~in_permission),
            Window(FormattedTextControl(self._status_text), height=1),
        ])
        root = FloatContainer(
            content=body,
            floats=[Float(xcursor=True, ycursor=True, content=CompletionsMenu(max_height=8, scroll_offset=1))],
        )

        app = Application(
            layout=Layout(root, focused_element=self.input),
            key_bindings=self._key_bindings(busy, in_permission),
            style=Style.from_dict({
                "frame.border": "#666666",
                "completion-menu": "bg:#303030 #dddddd",
                "completion-menu.completion.current": "bg:#5f87af #ffffff",
                "completion-menu.meta.completion": "bg:#262626 #888888",
            }),
            full_screen=False,
            erase_when_done=True,
            refresh_interval=0.1,
            min_redraw_interval=0.03,
            mouse_support=False,
        )
        # A lone Esc means "interrupt". Terminals send Alt+Enter as "\x1b\r" in a single
        # write, so a short wait for a following key is enough to tell them apart.
        app.timeoutlen = 0.05
        app.ttimeoutlen = 0.1
        return app

    def _key_bindings(self, busy, in_permission) -> KeyBindings:
        kb = KeyBindings()
        typing = ~in_permission

        @kb.add("enter", filter=typing)
        def _submit(event):
            buf = self.input.buffer
            if buf.complete_state and buf.complete_state.current_completion:
                buf.apply_completion(buf.complete_state.current_completion)
                return
            text = buf.text
            if not text.strip():
                return
            buf.append_to_history()
            buf.reset()
            self.submit(text)

        @kb.add("c-j", filter=typing)
        @kb.add("escape", "enter", filter=typing)
        def _newline(event):
            self.input.buffer.insert_text("\n")

        @kb.add("escape", filter=busy & typing)
        def _interrupt(event):
            self.interrupt()

        @kb.add("c-c")
        def _ctrl_c(event):
            if self.permission is not None:
                self._answer_permission(PERMISSION_NO)
                self.interrupt()
            elif self.state.busy:
                self.interrupt()
            elif self.input.buffer.text:
                self.input.buffer.reset()
            elif time.monotonic() - self._last_ctrl_c < 2.0:
                self.exit()
            else:
                self._last_ctrl_c = time.monotonic()
                self.flash("press ctrl+c again to exit")

        @kb.add("c-d", filter=typing)
        def _ctrl_d(event):
            if not self.input.buffer.text:
                self.exit()
            else:
                self.input.buffer.delete()

        # Permission prompt
        @kb.add("y", filter=in_permission)
        def _yes(event):
            self._answer_permission(PERMISSION_YES)

        @kb.add("a", filter=in_permission)
        def _always(event):
            self._answer_permission(PERMISSION_ALWAYS)

        @kb.add("n", filter=in_permission)
        @kb.add("escape", filter=in_permission)
        def _no(event):
            self._answer_permission(PERMISSION_NO)

        return kb

    # ---------------------------------------------------------------- rendering

    def _live_text(self):
        if self.permission is not None:
            tool, params = self.permission
            return ANSI(R.render_permission(tool, params))
        return ANSI(R.render_live_line(self.state, int(time.monotonic() * 10)))

    def _status_text(self):
        hint = self._hint if time.monotonic() < self._hint_until else ""
        if not hint and self.state.busy:
            hint = "esc interrupt · enter queues a message"
        model = getattr(self.orchestrator.llm_connector.llm, "model_name", "") or ""
        return ANSI(R.render_status_bar(str(model), self.session_id, self.pipeline.replace(".json", ""), self.state, hint))

    def write(self, text: str) -> None:
        """Prints committed output above the live area (safe from any thread)."""
        print(text, flush=True)

    def invalidate(self) -> None:
        try:
            self.app.invalidate()
        except Exception:
            pass

    def flash(self, hint: str, seconds: float = 2.0) -> None:
        self._hint = hint
        self._hint_until = time.monotonic() + seconds
        self.invalidate()

    # ---------------------------------------------------------------- actions

    def submit(self, text: str) -> None:
        stripped = text.strip()
        if stripped.startswith("/"):
            name, _, arg = stripped.partition(" ")
            cmd = COMMANDS.get(name)
            if cmd is None:
                self.write(f"{R.RED}Unknown command {name}. Try /help.{R.RESET}")
                return
            if self.state.busy and not cmd.allowed_while_busy:
                self.flash(f"{name} is unavailable while the agent is working (esc to interrupt)")
                return
            self.write(R.render_user_message(stripped))
            cmd.handler(self, arg)
            return

        if self.state.busy:
            self.state.queued.append(stripped)
            self.invalidate()
            return
        self._start_turn(stripped)

    def _start_turn(self, text: str) -> None:
        self.write(R.render_user_message(text))
        prompt = expand_mentions(text)
        self.state.start_turn()
        self.invalidate()
        self.worker = threading.Thread(target=self._run_turn, args=(prompt,), daemon=True, name="agent-turn")
        self.worker.start()

    def _run_turn(self, prompt: str) -> None:
        result = None
        try:
            result = self.orchestrator.run_loop(prompt, self.session_id)
        except Exception as e:
            self.write(f"{R.RED}✗ Orchestrator error: {e}{R.RESET}")
            func.debug(traceback.format_exc())
        finally:
            if self.loop is not None:
                self.loop.call_soon_threadsafe(self._turn_finished, result)

    def _turn_finished(self, result) -> None:
        reason = getattr(result, "reason", "error")
        self.write(R.render_turn_summary(reason, self.state))
        self.state.busy = False
        self.state.cancelling = False
        self.state.phase = ""
        self.state.task = ""
        self.worker = None
        if self.state.queued:
            self._start_turn(self.state.queued.pop(0))
        self.invalidate()

    def interrupt(self) -> None:
        if not self.state.busy or self.state.cancelling:
            return
        self.state.cancelling = True
        self.state.queued.clear()
        self.orchestrator.cancel()
        self.io.cancel_pending()
        self.invalidate()

    def exit(self) -> None:
        if self.state.busy:
            self.orchestrator.cancel()
            self.io.cancel_pending()
        if self.app.is_running:
            self.app.exit()

    # ---------------------------------------------------------------- permission

    async def _ask_permission(self, tool: str, params: Dict[str, Any]) -> str:
        self._permission_future = asyncio.get_running_loop().create_future()
        self.permission = (tool, params)
        self.invalidate()
        try:
            return await self._permission_future
        finally:
            self.permission = None
            self._permission_future = None
            self.invalidate()

    def _answer_permission(self, choice: str) -> None:
        future = self._permission_future
        if future is not None and not future.done():
            future.set_result(choice)

    # ---------------------------------------------------------------- session control

    def new_session(self) -> None:
        self.session_id = str(uuid.uuid4())
        self.orchestrator.reset_state()
        self.state.context_pressure = None

    def switch_session(self, session_id: str) -> None:
        self.session_id = session_id
        self.orchestrator.reset_state()
        self.state.context_pressure = None

    def switch_pipeline(self, pipeline: str) -> None:
        self.orchestrator = self._build_orchestrator(pipeline)
        self.pipeline = pipeline
        self.new_session()

    # ---------------------------------------------------------------- run

    def banner(self) -> str:
        model = getattr(self.orchestrator.llm_connector.llm, "model_name", "") or "?"
        return "\n".join([
            f"{R.TerminalUI.PRIMARY}✻{R.RESET} {R.BOLD}JARVIS agent chat{R.RESET}",
            f"  {R.GREY}model{R.RESET}    {model}",
            f"  {R.GREY}pipeline{R.RESET} {self.pipeline.replace('.json', '')}   {R.GREY}session{R.RESET} {self.session_id[:8]}",
            f"  {R.GREY}cwd{R.RESET}      {os.getcwd()}",
            f"  {R.GREY}/help for commands · esc interrupts · ctrl+d exits{R.RESET}",
        ])

    async def run_async(self, initial_message: Optional[str] = None) -> None:
        self.loop = asyncio.get_running_loop()
        self.io.loop = self.loop
        with patch_stdout(raw=True):
            self.write(self.banner())
            if initial_message:
                self.loop.call_soon(self.submit, initial_message)
            await self.app.run_async()
        print(f"{R.GREY}Session {self.session_id} saved. Resume with: ai --agent --session-id {self.session_id}{R.RESET}")

    def run(self, initial_message: Optional[str] = None) -> None:
        asyncio.run(self.run_async(initial_message))


def run_agent_chat(prog, pipeline: str = "default.json", session_id: Optional[str] = None,
                   directory_manager=None, initial_message: Optional[str] = None) -> None:
    """Entry point used by the CLI (``ai --agent`` on an interactive terminal)."""
    app = AgentChatApp(prog, pipeline=pipeline, session_id=session_id, directory_manager=directory_manager)
    app.run(initial_message)
