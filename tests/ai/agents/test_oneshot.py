"""One-shot ``ai --agent --msg ...`` runs printed with the chat UI renderer."""

import io as _io

import pytest

import ai.program  # noqa: F401  (startup import order, avoids a circular import)
from ai.agents.agent_io import PERMISSION_ALWAYS, PERMISSION_NO, PERMISSION_YES
from ai.agents.chat_ui import oneshot
from ai.agents.chat_ui.oneshot import OneShotIO, run_one_shot

from test_agent_chat import make_orchestrator, isolate  # noqa: F401


class TtyBuffer(_io.StringIO):
    def isatty(self):
        return True


def run(monkeypatch, responses, io):
    orch, conn, reg = make_orchestrator(responses, io=io)
    closed = []
    orch.close = lambda: closed.append(True)
    monkeypatch.setattr("ai.agents.agent.build_orchestrator", lambda prog, pipeline, io=None, directory_manager=None: orch)
    result = run_one_shot(prog=None, prompt="run the tests", io=io)
    return result, reg, closed


class TestRunOneShot:
    def test_prints_chat_style_transcript_and_exits(self, monkeypatch):
        out = _io.StringIO()
        result, reg, closed = run(monkeypatch, [
            {"manifest": {"current_priority": "Running tests"},
             "action": {"tool_name": "read_file", "tool_parameters": {"path": "a.py"}}},
            {"response_to_user": "All tests pass.", "action": {"agent_target": "STOP"}},
        ], OneShotIO(out=out, interactive=False))

        text = out.getvalue()
        assert result.reason == "done"
        assert closed == [True]
        assert reg.executed == [("read_file", {"path": "a.py"})]
        for expected in ("> run the tests", "Running tests", "read_file(a.py)", "All tests pass.", "Done in"):
            assert expected in text
        assert text.index("read_file") < text.index("All tests pass.") < text.index("Done in")

    def test_no_ansi_without_tty_but_colors_on_tty(self, monkeypatch):
        plain = _io.StringIO()
        run(monkeypatch, [{"response_to_user": "hi", "action": {"agent_target": "STOP"}}], OneShotIO(out=plain, interactive=False))
        assert "\x1b[" not in plain.getvalue()

        tty = TtyBuffer()
        run(monkeypatch, [{"response_to_user": "hi", "action": {"agent_target": "STOP"}}], OneShotIO(out=tty, interactive=False))
        assert "\x1b[" in tty.getvalue()

    def test_handing_back_to_user_ends_the_run(self, monkeypatch):
        """Agents target USER when done; a one-shot run must stop there, not loop on an empty reply."""
        def never(_):
            raise AssertionError("one-shot must not wait for a reply")
        out = _io.StringIO()
        io = OneShotIO(out=out, read=never, interactive=True)
        orch, conn, _ = make_orchestrator([
            {"response_to_user": "OK", "action": {"agent_target": "USER"}},
            {"response_to_user": "OK again", "action": {"agent_target": "USER"}},
        ], io=io)
        orch.close = lambda: None
        monkeypatch.setattr("ai.agents.agent.build_orchestrator", lambda *a, **k: orch)

        result = run_one_shot(prog=None, prompt="say ok", session_id="s-user-end", io=io)

        text = out.getvalue()
        assert result.reason == "awaiting_user"
        assert len(conn.requests) == 1
        assert "OK again" not in text
        assert "Done in" in text
        assert "ai --agent --resume s-user-end" in text

    def test_question_is_shown_with_resume_hint(self, monkeypatch):
        out = _io.StringIO()
        io = OneShotIO(out=out, interactive=True)
        orch, _, _ = make_orchestrator([
            {"action": {"agent_target": "USER", "message_to_target": "Which file?"}},
        ], io=io)
        orch.close = lambda: None
        monkeypatch.setattr("ai.agents.agent.build_orchestrator", lambda *a, **k: orch)

        run_one_shot(prog=None, prompt="pick one", session_id="s-q", io=io)

        text = out.getvalue()
        assert text.index("Which file?") < text.index("ai --agent --resume s-q")

    def test_closes_orchestrator_on_error(self, monkeypatch):
        orch, _, _ = make_orchestrator([], io=OneShotIO(out=_io.StringIO(), interactive=False))
        closed = []
        orch.close = lambda: closed.append(True)
        orch.run_loop = lambda **_: (_ for _ in ()).throw(RuntimeError("boom"))
        monkeypatch.setattr("ai.agents.agent.build_orchestrator", lambda *a, **k: orch)
        with pytest.raises(RuntimeError):
            run_one_shot(prog=None, prompt="x", io=orch.io)
        assert closed == [True]


class TestOneShotIO:
    @pytest.mark.parametrize("answer,expected", [
        ("y", PERMISSION_YES), ("yes", PERMISSION_YES), ("a", PERMISSION_ALWAYS),
        ("all", PERMISSION_ALWAYS), ("n", PERMISSION_NO), ("", PERMISSION_NO),
    ])
    def test_permission_mapping(self, answer, expected):
        out = _io.StringIO()
        io = OneShotIO(out=out, read=lambda _: answer, interactive=True)
        assert io.request_permission("execute_command", {"command": "ls"}) == expected
        assert "Permission required" in out.getvalue()

    def test_permission_denied_without_terminal(self):
        def never(_):
            raise AssertionError("must not prompt")
        io = OneShotIO(out=_io.StringIO(), read=never, interactive=False)
        assert io.request_permission("execute_command", {"command": "ls"}) == PERMISSION_NO

    def test_eof_on_prompt_is_a_denial(self):
        def eof(_):
            raise EOFError
        io = OneShotIO(out=_io.StringIO(), read=eof, interactive=True)
        assert io.request_permission("write_file", {"path": "a"}) == PERMISSION_NO

    def test_long_prompt_is_shortened_in_the_echo(self):
        preview = oneshot._prompt_preview("\n".join(f"line {i}" for i in range(20)))
        assert preview.splitlines()[-1] == "… (+14 lines)"
        assert len(preview.splitlines()) == oneshot.MAX_PROMPT_LINES + 1


class TestCliAgentMode:
    def test_msg_runs_one_shot_with_the_new_renderer(self, monkeypatch):
        import argparse
        import sys
        from ai.cli_args import CliArgs

        calls = []
        monkeypatch.setattr(oneshot, "run_one_shot", lambda prog, prompt, **kw: calls.append((prompt, kw)))
        monkeypatch.setattr(sys, "stdin", _io.StringIO(""))
        args = argparse.Namespace(resume=None, task_file=None, task=None, msg="run the tests",
                                  pipeline=None, output_file=None, session_id="s-cli")
        with pytest.raises(SystemExit) as exit_info:
            CliArgs()._handle_agent_mode(prog=None, args=args, directory_manager=None)

        assert exit_info.value.code == 0
        assert calls == [("run the tests", {"pipeline": "default.json", "session_id": "s-cli", "directory_manager": None})]
