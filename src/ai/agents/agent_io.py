"""
I/O abstraction for the agent orchestrator.

The orchestrator never talks to the terminal directly. It emits ``AgentEvent``
objects and asks for permission / user input through an ``AgentIO`` instance.

* ``ConsoleIO`` reproduces the classic one-shot ``--agent`` terminal output
  (``TerminalUI`` + blocking ``input()``).
* The interactive chat UI provides its own implementation (see
  ``ai.agents.chat_ui.bridge.ChatIO``).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

import ai.functions as func
from ai.color import Color
from ai.agents.terminal_ui import TerminalUI


class AgentEventType(str, Enum):
    """Kinds of events emitted by the orchestrator."""
    HEADER = "header"            # Section header (pipeline start / resume / fatal loop)
    STATUS = "status"            # Agent X is now working on Y (live, not committed)
    LLM_REQUEST = "llm_request"  # A model call is about to start
    THOUGHT = "thought"          # Agent reasoning (only when AGENT_THOUGHT is enabled)
    MESSAGE = "message"          # response_to_user
    QUESTION = "question"        # Agent targets USER and wants an answer
    TOOL_CALL = "tool_call"      # A tool is about to run
    TOOL_RESULT = "tool_result"  # A tool finished (or was refused)
    SPECIALIST = "specialist"    # A specialist sub-model is generating content
    INFO = "info"                # Step / informational log line
    ERROR = "error"              # Something went wrong


@dataclass
class AgentEvent:
    """A single event emitted by the orchestrator."""
    type: AgentEventType
    agent: Optional[str] = None
    text: str = ""
    data: Dict[str, Any] = field(default_factory=dict)


# Permission answers
PERMISSION_YES = "y"
PERMISSION_NO = "n"
PERMISSION_ALWAYS = "a"


class AgentIO:
    """
    Base I/O channel. Subclasses override what they need.

    Attributes:
        blocking_user_input: When True, a USER-targeted question is answered
            inline via ``request_user_input`` and the loop keeps going. When
            False, the loop ends the turn and returns ``awaiting_user`` so the
            caller can collect the answer as the next chat message.
    """
    blocking_user_input: bool = True

    def emit(self, event: AgentEvent) -> None:
        """Receives an orchestrator event."""

    def request_permission(self, tool: str, params: Dict[str, Any]) -> str:
        """Asks whether a gated tool may run. Returns 'y', 'n' or 'a'."""
        return PERMISSION_NO

    def request_user_input(self, agent: str, prompt: str) -> str:
        """Asks the user a question and returns the answer (blocking mode only)."""
        return ""


class ConsoleIO(AgentIO):
    """Classic terminal behaviour used by one-shot ``--agent`` runs."""
    blocking_user_input = True

    def emit(self, event: AgentEvent) -> None:
        t = event.type
        if t == AgentEventType.HEADER:
            TerminalUI.header(event.text, event.data.get("subtitle", ""))
        elif t == AgentEventType.STATUS:
            TerminalUI.status(event.agent or "", event.text)
        elif t == AgentEventType.THOUGHT:
            TerminalUI.message(event.agent or "", event.text, Color.DIM)
        elif t == AgentEventType.MESSAGE:
            TerminalUI.message(event.agent or "", event.text, Color.NORMAL_WHITE)
        elif t == AgentEventType.QUESTION:
            TerminalUI.message(event.agent or "", event.text, Color.NORMAL_CYAN)
        elif t == AgentEventType.TOOL_CALL:
            # Gated tools were already announced by the authorization box.
            if not event.data.get("gated"):
                TerminalUI.agent_step(f"Executing tool: {event.data.get('tool')} with params: {event.data.get('params')}")
        elif t == AgentEventType.SPECIALIST:
            TerminalUI.clear_line()
            func.out(f"{Color.NORMAL_CYAN} Specialist: {event.data.get('tool')}{Color.RESET}")
        elif t == AgentEventType.INFO:
            TerminalUI.log_step(event.text, event.data.get("status", "INFO"))
        elif t == AgentEventType.ERROR:
            func.error(event.text)
        # LLM_REQUEST / TOOL_RESULT: silent in classic mode

    def request_permission(self, tool: str, params: Dict[str, Any]) -> str:
        TerminalUI.auth_request(tool, params.get('path') or "@ROOT", params.get('command', ""))
        choice = input("Allow? ( y / n / (a)ll): ").lower().strip()
        if choice in ("a", "all"):
            return PERMISSION_ALWAYS
        if choice in ("y", "yes"):
            return PERMISSION_YES
        return PERMISSION_NO

    def request_user_input(self, agent: str, prompt: str) -> str:
        return input(f"{Color.BLUE} {Color.RESET}").strip()
