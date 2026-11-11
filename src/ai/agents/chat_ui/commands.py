"""
Slash commands for the agent chat UI.

Each command is ``handler(app, arg) -> None``. Handlers run on the UI loop and
print through ``app.write``.
"""

import os
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Dict

from ai.config import ProgramConfig, ProgramSetting
from ai.agents.chat_ui.renderer import BOLD, GREY, RED, RESET, GREEN

if TYPE_CHECKING:
    from ai.agents.chat_ui.app import AgentChatApp


@dataclass
class Command:
    name: str
    help: str
    handler: Callable[["AgentChatApp", str], None]
    allowed_while_busy: bool = False


def _help(app: "AgentChatApp", arg: str) -> None:
    lines = [f"{BOLD}Commands{RESET}"]
    for cmd in COMMANDS.values():
        lines.append(f"  {GREEN}{cmd.name:<11}{RESET} {cmd.help}")
    lines += [
        "",
        f"{BOLD}Keys{RESET}",
        f"  {GREEN}{'enter':<11}{RESET} send (queued if the agent is busy)",
        f"  {GREEN}{'ctrl+j':<11}{RESET} newline (also alt+enter)",
        f"  {GREEN}{'esc':<11}{RESET} interrupt the running turn",
        f"  {GREEN}{'ctrl+c':<11}{RESET} interrupt / clear input / press twice to exit",
        f"  {GREEN}{'ctrl+d':<11}{RESET} exit on an empty line",
        f"  {GREEN}{'@path':<11}{RESET} attach a file (tab completes)",
    ]
    app.write("\n".join(lines))


def _clear(app: "AgentChatApp", arg: str) -> None:
    app.new_session()
    app.write(f"{GREY}Started a new session {app.session_id[:8]}.{RESET}")


def _session(app: "AgentChatApp", arg: str) -> None:
    app.write(f"{GREY}session{RESET} {app.session_id}\n{GREY}pipeline{RESET} {app.pipeline}\n{GREY}cwd{RESET} {os.getcwd()}")


def _resume(app: "AgentChatApp", arg: str) -> None:
    from ai.agents.session_manager import AgentSessionManager
    from ai.agents.chat_ui.session_picker import render_session_row, resolve_session_id

    sessions = AgentSessionManager.list_sessions_detailed(os.getcwd())
    arg = arg.strip()
    if not arg:
        if not sessions:
            app.write(f"{GREY}No saved sessions for this directory.{RESET}")
            return
        lines = [f"{BOLD}Sessions in this directory{RESET} {GREY}(/resume <n|id>){RESET}"]
        for idx, s in enumerate(sessions[:20], 1):
            marker = f"{GREEN}*{RESET}" if s.get("session_id") == app.session_id else " "
            lines.append(f"{GREEN}{idx:>2}{RESET}{marker}{render_session_row(s, False)}")
        if len(sessions) > 20:
            lines.append(f"{GREY}   … {len(sessions) - 20} older sessions{RESET}")
        app.write("\n".join(lines))
        return

    if arg.isdigit() and 1 <= int(arg) <= len(sessions):
        target = sessions[int(arg) - 1]["session_id"]
    else:
        try:
            target = resolve_session_id(sessions, arg) or arg  # full ids work even if unlisted
        except ValueError as e:
            app.write(f"{RED}{e}{RESET}")
            return
    app.switch_session(target)
    if not app.show_history():
        app.write(f"{GREY}Session {target[:8]} has no saved state yet; your next message starts it.{RESET}")


def _pipeline(app: "AgentChatApp", arg: str) -> None:
    arg = arg.strip()
    if not arg:
        app.write(f"{GREY}Current pipeline:{RESET} {app.pipeline}  {GREY}(/pipeline <name> to switch){RESET}")
        return
    try:
        app.switch_pipeline(arg)
        app.write(f"{GREY}Pipeline switched to{RESET} {arg}{GREY}; started a new session {app.session_id[:8]}.{RESET}")
    except Exception as e:
        app.write(f"{RED}✗ Could not load pipeline '{arg}': {e}{RESET}")


def _tools(app: "AgentChatApp", arg: str) -> None:
    orch = app.orchestrator
    lines = []
    for agent in orch.agents.keys():
        tools = orch._allowed_tools(agent)
        lines.append(f"{BOLD}{agent}{RESET} {GREY}({len(tools)}){RESET}")
        lines.append("  " + ", ".join(tools) if tools else f"  {GREY}none{RESET}")
    app.write("\n".join(lines) or f"{GREY}No agents in pipeline.{RESET}")


def _thoughts(app: "AgentChatApp", arg: str) -> None:
    config = ProgramConfig.get_current()
    value = not bool(config.get(ProgramSetting.AGENT_THOUGHT, False))
    config.set(ProgramSetting.AGENT_THOUGHT, value)
    app.write(f"{GREY}Agent thoughts {'shown' if value else 'hidden'}.{RESET}")


def _exit(app: "AgentChatApp", arg: str) -> None:
    app.exit()


COMMANDS: Dict[str, Command] = {c.name: c for c in [
    Command("/help", "show commands and keys", _help, True),
    Command("/clear", "start a fresh session", _clear),
    Command("/resume", "list or resume saved sessions", _resume),
    Command("/session", "show the current session", _session, True),
    Command("/pipeline", "show or switch the agent pipeline", _pipeline),
    Command("/tools", "list tools available to each agent", _tools, True),
    Command("/thoughts", "toggle display of agent reasoning", _thoughts, True),
    Command("/exit", "quit the chat", _exit, True),
    Command("/quit", "quit the chat", _exit, True),
]}
