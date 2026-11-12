"""Tests for agent session resume: detailed listing, transcript, picker and --resume."""

import json
import os
import time
from types import SimpleNamespace

import pytest

import ai.program  # noqa: F401  (startup import order, avoids a circular import)
from ai.agents.session_manager import AgentSessionManager
from ai.agents.chat_ui import session_picker as sp


@pytest.fixture(autouse=True)
def storage(tmp_path, monkeypatch):
    monkeypatch.setattr(AgentSessionManager, "_get_agents_storage_root", staticmethod(lambda: str(tmp_path / "agents")))
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    return work


def make_session(session_id, request, last=None, turns=1, mtime=None, history=None):
    mgr = AgentSessionManager(session_id)
    for i in range(turns):
        mgr.commit({
            "user_request": request,
            "last_user_message": last or request,
            "current_agent": "MASTER",
            "iteration": i + 1,
            "memory": {"context": {}, "agents": {"MASTER": {"history": history or [], "messages_received": []}}},
        })
    if mtime is not None:
        os.utime(mgr.session_path, (mtime, mtime))
    return mgr


class TestDetailedListing:
    def test_sorted_newest_first_with_metadata(self):
        now = time.time()
        make_session("old-session", "old task", turns=2, mtime=now - 7200)
        make_session("new-session", "new task", last="follow up", turns=3, mtime=now - 60)
        sessions = AgentSessionManager.list_sessions_detailed()
        assert [s["session_id"] for s in sessions] == ["new-session", "old-session"]
        assert sessions[0]["turns"] == 3
        assert sessions[0]["user_request"] == "new task"
        assert sessions[0]["last_user_message"] == "follow up"
        assert sessions[0]["iteration"] == 3

    def test_empty_and_manifest_ignored(self):
        assert AgentSessionManager.list_sessions_detailed() == []
        AgentSessionManager("empty")  # creates storage + manifest but no session lines
        assert AgentSessionManager.list_sessions_detailed() == []

    def test_original_list_sessions_unchanged(self):
        make_session("abc", "task")
        assert AgentSessionManager.list_sessions() == [{"session_id": "abc", "filename": "abc", "user_request": "task"}]


class TestTranscript:
    def test_extracts_user_and_agent_messages(self):
        state = {"memory": {"agents": {"MASTER": {
            "history": [
                {"from": "USER", "message": "hi"},
                {"from": "SELF", "thought": "t", "response": "hello"},
                {"from": "SYSTEM", "result": {"status": "SUCCESS"}},
                {"from": "SELF", "thought": "t", "response": None},
                {"from": "USER", "message": "next"},
            ],
            "messages_received": [],
        }}}}
        entries = AgentSessionManager.extract_transcript(state)
        assert [(e["role"], e["text"]) for e in entries] == [("user", "hi"), ("agent", "hello"), ("user", "next")]

    def test_limit_and_empty(self):
        history = [{"from": "USER", "message": str(i)} for i in range(20)]
        state = {"memory": {"agents": {"MASTER": {"history": history}}}}
        assert [e["text"] for e in AgentSessionManager.extract_transcript(state, limit=3)] == ["17", "18", "19"]
        assert AgentSessionManager.extract_transcript(None) == []
        assert AgentSessionManager.extract_transcript({}) == []


class TestPickerHelpers:
    SESSIONS = [
        {"session_id": "3f2a91c0-aaaa", "user_request": "Build API endpoint", "last_user_message": "add tests", "updated_at": 0, "turns": 5},
        {"session_id": "9be01d22-bbbb", "user_request": "Fix failing tests", "last_user_message": "Fix failing tests", "updated_at": 0, "turns": 1},
        {"session_id": "9bf00000-cccc", "user_request": "Refactor", "updated_at": 0, "turns": 2},
    ]

    def test_format_age(self):
        now = 1_000_000
        assert sp.format_age(now - 5, now) == "just now"
        assert sp.format_age(now - 300, now) == "5m ago"
        assert sp.format_age(now - 7200, now) == "2h ago"
        assert sp.format_age(now - 90000, now) == "yesterday"
        assert sp.format_age(now - 86400 * 4, now) == "4d ago"

    def test_filter(self):
        assert len(sp.filter_sessions(self.SESSIONS, "")) == 3
        assert [s["session_id"] for s in sp.filter_sessions(self.SESSIONS, "TESTS")] == ["3f2a91c0-aaaa", "9be01d22-bbbb"]
        assert [s["session_id"] for s in sp.filter_sessions(self.SESSIONS, "9bf")] == ["9bf00000-cccc"]

    def test_resolve(self):
        assert sp.resolve_session_id(self.SESSIONS, "3f2a") == "3f2a91c0-aaaa"
        assert sp.resolve_session_id(self.SESSIONS, "9be01d22-bbbb") == "9be01d22-bbbb"
        assert sp.resolve_session_id(self.SESSIONS, "zzz") is None
        with pytest.raises(ValueError):
            sp.resolve_session_id(self.SESSIONS, "9b")

    def test_row(self):
        row = sp.render_session_row(self.SESSIONS[0], selected=True, width=120)
        assert "3f2a91c0" in row and "5 turns" in row and "Build API endpoint" in row and "add tests" in row


class TestPickerHeadless:
    def _pick(self, sessions, keys):
        from prompt_toolkit.application import create_app_session
        from prompt_toolkit.input import create_pipe_input
        from prompt_toolkit.output import DummyOutput

        with create_pipe_input() as pipe:
            with create_app_session(input=pipe, output=DummyOutput()):
                pipe.send_text(keys)
                return sp.SessionPicker(sessions).run()

    def test_enter_picks_first(self):
        assert self._pick(TestPickerHelpers.SESSIONS, "\r") == "3f2a91c0-aaaa"

    def test_down_then_enter(self):
        assert self._pick(TestPickerHelpers.SESSIONS, "\x1b[B\x1b[B\r") == "9bf00000-cccc"

    def test_filter_then_enter(self):
        assert self._pick(TestPickerHelpers.SESSIONS, "refac\r") == "9bf00000-cccc"

    def test_cancel(self):
        assert self._pick(TestPickerHelpers.SESSIONS, "\x03") is None

    def test_no_match_enter_returns_none(self):
        assert self._pick(TestPickerHelpers.SESSIONS, "nothing-here\r") is None


class TestCliResume:
    def _cli(self):
        from ai.cli_args import CliArgs
        return CliArgs()

    def test_explicit_prefix(self):
        make_session("abc12345-x", "task")
        assert self._cli()._resolve_resume_session(SimpleNamespace(resume="abc1")) == "abc12345-x"

    def test_unknown_id_exits(self):
        make_session("abc12345-x", "task")
        with pytest.raises(SystemExit) as exc:
            self._cli()._resolve_resume_session(SimpleNamespace(resume="nope"))
        assert exc.value.code == 1

    def test_no_sessions_returns_none(self):
        assert self._cli()._resolve_resume_session(SimpleNamespace(resume="")) is None

    def test_picker_requires_tty(self, monkeypatch):
        make_session("abc12345-x", "task")
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        with pytest.raises(SystemExit) as exc:
            self._cli()._resolve_resume_session(SimpleNamespace(resume=""))
        assert exc.value.code == 1

    def test_picker_used_on_tty(self, monkeypatch):
        make_session("abc12345-x", "task")
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        monkeypatch.setattr("sys.stdout.isatty", lambda: True)
        monkeypatch.setattr(sp, "pick_session", lambda sessions: sessions[0]["session_id"])
        assert self._cli()._resolve_resume_session(SimpleNamespace(resume="")) == "abc12345-x"


def test_transcript_render():
    from ai.agents.chat_ui import renderer as R
    out = R.render_transcript([{"role": "user", "text": "hi"}, {"role": "agent", "text": "hello\nworld"}], "abcdef123", "Build it")
    assert "resumed session abcdef12" in out and "hi" in out and "hello" in out and "  world" in out
