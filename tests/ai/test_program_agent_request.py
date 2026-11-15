"""/agent in the plain chat: runs with build_orchestrator and always gives the prompt back."""
import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def program_module(monkeypatch):
    """The real ai.program (some agent tests replace it in sys.modules with a MagicMock)."""
    current = sys.modules.get("ai.program")
    if current is None or isinstance(current, MagicMock):
        monkeypatch.delitem(sys.modules, "ai.program", raising=False)
        current = importlib.import_module("ai.program")
    return current


def _program(module):
    prog = module.Program.__new__(module.Program)  # no model, no modules: only what the handler uses
    prog.agent = None
    prog.chat = MagicMock()
    return prog


def test_agent_request_runs_and_releases_the_prompt(program_module):
    prog = _program(program_module)
    orchestrator = MagicMock()
    with patch.object(program_module, "build_orchestrator", return_value=orchestrator) as build:
        prog._handle_agent_run_requested("list the TODOs")
    build.assert_called_once_with(prog)
    orchestrator.run_loop.assert_called_once()
    assert orchestrator.run_loop.call_args[0][0] == "list the TODOs"
    prog.chat.terminate_command.assert_called_once()


def test_agent_request_releases_the_prompt_on_failure(program_module):
    prog = _program(program_module)
    with patch.object(program_module, "build_orchestrator", side_effect=ValueError("no LLM")):
        prog._handle_agent_run_requested("x")
    prog.chat.terminate_command.assert_called_once()
