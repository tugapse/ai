"""
Tests for the agent I/O abstraction, multi-turn orchestration and the
prompt_toolkit agent chat UI.
"""

import asyncio
import threading
import time
from unittest.mock import MagicMock

import pytest

# Import in the same order as real startup (main -> program) to avoid the
# ai.direct -> config_helper -> ai.program circular import.
import ai.program  # noqa: F401
from ai.agents import agent_orchestrator as orch_mod
from ai.agents.agent_io import AgentEvent, AgentEventType, AgentIO, ConsoleIO, PERMISSION_NO, PERMISSION_YES
from ai.agents.agent_orchestrator import AgentOrchestrator
from ai.agents.session_manager import AgentSessionManager
from ai.agents.chat_ui import renderer as R
from ai.agents.chat_ui.bridge import ChatIO
from ai.config import ProgramConfig, ProgramSetting


# ---------------------------------------------------------------- fakes

class FakeLLM:
    model_name = "fake-model"

    def __init__(self):
        self.stop_generation_event = threading.Event()
        self.request_shutdown = MagicMock()


class FakeConnector:
    """Scripted connector. A response may be a callable(payload) -> dict."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.llm = FakeLLM()
        self.on_token = None

    def send_request(self, payload, prompt_file_path, agent_config):
        self.requests.append({"payload": payload, "config": agent_config})
        if not self.responses:
            return {"action": {"agent_target": "STOP"}}
        resp = self.responses.pop(0)
        return resp(payload) if callable(resp) else resp

    def get_context_limit(self):
        return 8192

    def get_max_tokens(self):
        return 1024


class FakeRegistry:
    def __init__(self):
        self.executed = []

    def get_tool_info(self, name):
        return f"info {name}"

    def execute_tool(self, name, params):
        self.executed.append((name, params))
        return {"status": "SUCCESS", "result": f"did {name}"}

    def get_all_tools(self):
        return {}


class RecordingIO(AgentIO):
    def __init__(self, blocking=False, permission=PERMISSION_YES):
        self.blocking_user_input = blocking
        self.events = []
        self.permission = permission
        self.permission_requests = []

    def emit(self, event):
        self.events.append(event)

    def request_permission(self, tool, params):
        self.permission_requests.append((tool, params))
        return self.permission

    def types(self):
        return [e.type for e in self.events]


PIPELINE = {
    "entry_point": "MASTER",
    "max_iterations": 10,
    "agents": {
        "MASTER": {
            "role": "management",
            "tools": ["read_file", "execute_command"],
            "allowed_targets": ["MASTER", "USER", "STOP"],
            "prompt_file_path": "master.md",
        }
    },
}


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(AgentSessionManager, "_get_agents_storage_root", staticmethod(lambda: str(tmp_path / "agents")))
    monkeypatch.setattr(orch_mod.MCPBridge, "load_from_config", lambda self, path: None)
    monkeypatch.chdir(tmp_path)
    yield


def make_orchestrator(responses, io=None, pipeline=None):
    import copy
    connector = FakeConnector(responses)
    registry = FakeRegistry()
    orchestrator = AgentOrchestrator(
        llm_connector=connector,
        tool_registry=registry,
        pipeline_config=copy.deepcopy(pipeline or PIPELINE),
        module_registry=MagicMock(),
        io=io or RecordingIO(),
    )
    return orchestrator, connector, registry


def inbox_messages(request):
    return [m.get("message") for m in request["payload"]["messages_received"]]


# ---------------------------------------------------------------- orchestrator

class TestMultiTurnOrchestrator:
    def test_done_result_and_last_message(self):
        orch, conn, _ = make_orchestrator([
            {"response_to_user": "Hello!", "action": {"agent_target": "STOP"}},
        ])
        result = orch.run_loop("hi", "s1")
        assert result.reason == "done"
        assert result.message == "Hello!"
        assert result.iterations == 1

    def test_resumed_session_receives_new_message(self):
        orch, conn, _ = make_orchestrator([{"action": {"agent_target": "STOP"}}])
        orch.run_loop("first question", "s-resume")

        # A brand-new orchestrator (e.g. a new CLI process) resuming the session.
        orch2, conn2, _ = make_orchestrator([{"action": {"agent_target": "STOP"}}])
        orch2.run_loop("follow-up question", "s-resume")

        assert "follow-up question" in inbox_messages(conn2.requests[0])
        history = [m.get("message") for m in conn2.requests[0]["payload"]["conversation_history"]]
        assert "first question" in history

    def test_same_orchestrator_multi_turn(self):
        orch, conn, _ = make_orchestrator([
            {"action": {"agent_target": "STOP"}},
            {"action": {"agent_target": "STOP"}},
        ])
        orch.run_loop("turn one", "s-multi")
        orch.run_loop("turn two", "s-multi")
        assert inbox_messages(conn.requests[1]) == ["turn two"]
        assert conn.requests[1]["payload"]["objective"] == "turn two"

    def test_session_keeps_original_request(self):
        orch, _, _ = make_orchestrator([{"action": {"agent_target": "STOP"}}] * 2)
        orch.run_loop("original", "s-orig")
        orch.run_loop("second", "s-orig")
        state = AgentSessionManager("s-orig").get_session()
        assert state["user_request"] == "original"
        assert state["last_user_message"] == "second"

    def test_new_session_resets_memory(self):
        orch, conn, _ = make_orchestrator([{"action": {"agent_target": "STOP"}}] * 2)
        orch.run_loop("secret A", "sA")
        orch.run_loop("question B", "sB")
        history = [m.get("message") for m in conn.requests[1]["payload"]["conversation_history"]]
        assert "secret A" not in history

    def test_user_target_non_blocking_ends_turn(self):
        io = RecordingIO(blocking=False)
        orch, conn, _ = make_orchestrator([
            {"action": {"agent_target": "USER", "message_to_target": "Which file?"}},
            {"action": {"agent_target": "STOP"}},
        ], io=io)

        result = orch.run_loop("fix the bug", "s-q")
        assert result.reason == "awaiting_user"
        assert result.message == "Which file?"
        assert len(conn.requests) == 1
        assert AgentEventType.QUESTION in io.types()

        result2 = orch.run_loop("main.py", "s-q")
        assert result2.reason == "done"
        assert "main.py" in inbox_messages(conn.requests[1])

    def test_user_target_blocking_uses_io(self):
        io = RecordingIO(blocking=True)
        io.request_user_input = MagicMock(return_value="the answer")
        orch, conn, _ = make_orchestrator([
            {"action": {"agent_target": "USER", "message_to_target": "Q?"}},
            {"action": {"agent_target": "STOP"}},
        ], io=io)
        result = orch.run_loop("go", "s-b")
        assert result.reason == "done"
        io.request_user_input.assert_called_once()
        assert "the answer" in inbox_messages(conn.requests[1])

    def test_cancel_during_request(self):
        orch, conn, _ = make_orchestrator([])

        def cancel_during(payload):
            orch.cancel()
            return {"action": {"tool_name": "read_file", "tool_parameters": {"path": "x"}}}
        conn.responses = [cancel_during]
        result = orch.run_loop("go", "s-c")
        assert result.reason == "cancelled"
        assert len(conn.requests) == 1

    def test_cancel_does_not_unload_model(self):
        orch, conn, _ = make_orchestrator([])
        orch.cancel()
        assert conn.llm.stop_generation_event.is_set()
        conn.llm.request_shutdown.assert_not_called()

    def test_tool_events_and_execution(self):
        io = RecordingIO()
        orch, conn, reg = make_orchestrator([
            {"action": {"tool_name": "read_file", "tool_parameters": {"path": "a.py"}}},
            {"action": {"agent_target": "STOP"}},
        ], io=io)
        orch.run_loop("read a.py", "s-t")
        assert reg.executed == [("read_file", {"path": "a.py"})]
        calls = [e for e in io.events if e.type == AgentEventType.TOOL_CALL]
        results = [e for e in io.events if e.type == AgentEventType.TOOL_RESULT]
        assert calls[0].data["tool"] == "read_file"
        assert results[0].data["result"]["status"] == "SUCCESS"

    def test_gated_tool_denied(self):
        io = RecordingIO(permission=PERMISSION_NO)
        orch, conn, reg = make_orchestrator([
            {"action": {"tool_name": "execute_command", "tool_parameters": {"command": "rm -rf /"}}},
            {"action": {"agent_target": "STOP"}},
        ], io=io)
        orch.run_loop("clean up", "s-g")
        assert reg.executed == []
        assert io.permission_requests[0][0] == "execute_command"
        denied = [e for e in io.events if e.type == AgentEventType.TOOL_RESULT]
        assert denied[0].data["result"]["status"] == "DENIED"

    def test_mcp_tools_do_not_mutate_pipeline(self):
        orch, conn, reg = make_orchestrator([
            {"action": {"tool_name": "my_mcp", "tool_parameters": {"command": "x"}}},
            {"action": {"tool_name": "read_file", "tool_parameters": {"path": "y"}}},
            {"action": {"agent_target": "STOP"}},
        ])
        orch.mcp_bridge.server_schemas = {"my_mcp": {}}
        orch.run_loop("go", "s-mcp")

        assert orch.agents["MASTER"]["tools"] == ["read_file", "execute_command"]
        # MCP tool authorized on the very first iteration
        assert reg.executed[0][0] == "my_mcp"
        # and listed once per request
        for req in conn.requests:
            assert req["config"]["tools"].count("my_mcp") == 1

    def test_stop_signal_equality_not_identity(self):
        orch, conn, _ = make_orchestrator([{"action": {"agent_target": "".join(["ST", "OP"])}}])
        assert orch.run_loop("go", "s-eq").reason == "done"

    def test_resume_after_stop_restarts_at_entry_point(self):
        orch, _, _ = make_orchestrator([{"action": {"agent_target": "STOP"}}])
        orch.run_loop("one", "s-stop")
        orch2, conn2, _ = make_orchestrator([{"action": {"agent_target": "STOP"}}])
        result = orch2.run_loop("two", "s-stop")
        assert result.reason == "done"
        assert len(conn2.requests) == 1

    def test_iteration_budget_is_per_call(self):
        pipeline = dict(PIPELINE, max_iterations=2)
        loop_forever = {"action": {"tool_name": "read_file", "tool_parameters": {"path": "z"}}}
        orch, conn, _ = make_orchestrator([loop_forever] * 2, pipeline=pipeline)
        assert orch.run_loop("go", "s-budget").reason == "max_iterations"
        conn.responses = [{"action": {"agent_target": "STOP"}}]
        assert orch.run_loop("again", "s-budget").reason == "done"


class TestConsoleIO:
    def test_permission_mapping(self, monkeypatch):
        io = ConsoleIO()
        monkeypatch.setattr("ai.agents.agent_io.TerminalUI.auth_request", lambda *a, **k: None)
        for answer, expected in [("y", "y"), ("yes", "y"), ("a", "a"), ("all", "a"), ("n", "n"), ("", "n")]:
            monkeypatch.setattr("builtins.input", lambda *_: answer)
            assert io.request_permission("execute_command", {"command": "ls"}) == expected


# ---------------------------------------------------------------- renderer

class TestRenderer:
    def test_summarize_params(self):
        assert R.summarize_params("execute_command", {"command": "ls -la"}) == "ls -la"
        assert R.summarize_params("read_file", {"path": "a.py"}) == "a.py"
        assert R.summarize_params("x", {}) == ""
        assert len(R.summarize_params("x", {"data": "y" * 500})) <= R.MAX_ARG_LEN

    def test_summarize_result(self):
        assert R.summarize_result({"status": "SUCCESS", "result": "a\nb\nc"}) == (True, "3 lines")
        assert R.summarize_result({"status": "SUCCESS", "result": [1, 2]}) == (True, "2 items")
        ok, text = R.summarize_result({"status": "FAILED", "error": "boom"})
        assert not ok and "boom" in text
        assert R.summarize_result({"status": "SUCCESS"}) == (True, "SUCCESS")

    def test_render_event_types(self):
        msg = R.render_event(AgentEvent(AgentEventType.MESSAGE, "MASTER", "line1\nline2"))
        assert "line1" in msg and "  line2" in msg
        assert "read_file" in R.render_event(AgentEvent(AgentEventType.TOOL_CALL, data={"tool": "read_file", "params": {"path": "p"}}))
        denied = R.render_event(AgentEvent(AgentEventType.TOOL_RESULT, data={"tool": "execute_command", "result": {"status": "DENIED", "error": "no"}}))
        assert "execute_command" in denied and "DENIED" in denied
        assert R.render_event(AgentEvent(AgentEventType.STATUS, "MASTER", "x")) is None
        assert R.render_event(AgentEvent(AgentEventType.HEADER, text="Pipeline Execution Start", data={"resumed": False})) is None

    def test_live_line(self):
        state = R.LiveState()
        assert R.render_live_line(state, 0) == ""
        state.start_turn()
        state.agent, state.phase, state.iteration, state.max_iterations, state.tokens = "MASTER", "thinking", 2, 10, 1500
        line = R.render_live_line(state, 3)
        assert "MASTER thinking" in line and "step 2/10" in line and "1.5k tok" in line
        state.cancelling = True
        assert "Interrupting" in R.render_live_line(state, 0)

    def test_turn_summary(self):
        state = R.LiveState()
        state.start_turn()
        assert "Done" in R.render_turn_summary("done", state)
        assert "Interrupted" in R.render_turn_summary("cancelled", state)
        assert "waiting for your reply" in R.render_turn_summary("awaiting_user", state)


# ---------------------------------------------------------------- bridge

class TestChatIO:
    def test_emit_updates_state_and_writes(self):
        state = R.LiveState()
        out = []
        io = ChatIO(state, out.append, lambda: None)
        io.emit(AgentEvent(AgentEventType.STATUS, "MASTER", "planning", {"iteration": 3, "max_iterations": 9, "context_pressure": 0.4}))
        assert (state.agent, state.task, state.iteration, state.context_pressure) == ("MASTER", "planning", 3, 0.4)
        assert out == []
        io.emit(AgentEvent(AgentEventType.LLM_REQUEST, "MASTER"))
        io.on_token("a"); io.on_token("b")
        assert state.tokens == 2 and state.turn_steps == 1
        io.emit(AgentEvent(AgentEventType.MESSAGE, "MASTER", "hi"))
        assert len(out) == 1 and "hi" in out[0]

    def test_permission_round_trip_and_cancel(self):
        state = R.LiveState()
        loop = asyncio.new_event_loop()
        gate = {}

        async def handler(tool, params):
            gate["future"] = loop.create_future()
            return await gate["future"]

        io = ChatIO(state, lambda s: None, lambda: None, handler, loop)
        t = threading.Thread(target=loop.run_forever, daemon=True)
        t.start()
        try:
            answers = []
            worker = threading.Thread(target=lambda: answers.append(io.request_permission("execute_command", {})))
            worker.start()
            for _ in range(100):
                if "future" in gate:
                    break
                time.sleep(0.01)
            loop.call_soon_threadsafe(gate["future"].set_result, PERMISSION_YES)
            worker.join(2)
            assert answers == [PERMISSION_YES]

            gate.clear()
            worker = threading.Thread(target=lambda: answers.append(io.request_permission("execute_command", {})))
            worker.start()
            for _ in range(100):
                if "future" in gate:
                    break
                time.sleep(0.01)
            io.cancel_pending()
            worker.join(2)
            assert answers[-1] == PERMISSION_NO
        finally:
            loop.call_soon_threadsafe(loop.stop)
            t.join(2)
            loop.close()


# ---------------------------------------------------------------- app (headless)

class TestAgentChatAppHeadless:
    def _run(self, monkeypatch, responses, keys, initial=None):
        from prompt_toolkit.application import create_app_session
        from prompt_toolkit.history import InMemoryHistory
        from prompt_toolkit.input import create_pipe_input
        from prompt_toolkit.output import DummyOutput
        import ai.agents.agent as agent_mod
        from ai.agents.chat_ui import app as app_mod

        built = {}

        def fake_build(prog, pipeline, io=None, directory_manager=None):
            orch, conn, reg = make_orchestrator(responses, io=io)
            built.update(orch=orch, conn=conn, reg=reg)
            return orch

        monkeypatch.setattr(agent_mod, "build_orchestrator", fake_build)
        out = []

        async def scenario(chat, pipe):
            run = asyncio.ensure_future(chat.run_async(initial))
            for chunk in keys:
                await asyncio.sleep(0.15)
                # wait for the agent to go idle before the next input
                for _ in range(100):
                    if not chat.state.busy:
                        break
                    await asyncio.sleep(0.02)
                pipe.send_text(chunk)
            await asyncio.wait_for(run, timeout=5)

        with create_pipe_input() as pipe:
            with create_app_session(input=pipe, output=DummyOutput()):
                chat = app_mod.AgentChatApp(MagicMock(), history=InMemoryHistory())
                chat.write = out.append
                chat.io.write = out.append
                asyncio.run(scenario(chat, pipe))
        return chat, built, "\n".join(out)

    def test_send_message_and_exit(self, monkeypatch):
        chat, built, output = self._run(
            monkeypatch,
            [{"response_to_user": "Hi there", "action": {"agent_target": "STOP"}}],
            ["hello agent\r", "\x04"],  # enter, then ctrl+d
        )
        assert "hello agent" in output
        assert "Hi there" in output
        assert "Done" in output
        assert inbox_messages(built["conn"].requests[0]) == ["hello agent"]

    def test_help_command(self, monkeypatch):
        _, built, output = self._run(monkeypatch, [], ["/help\r", "\x04"])
        assert "/resume" in output and "ctrl+j" in output
        assert built["conn"].requests == []

    def test_clear_starts_new_session(self, monkeypatch):
        captured = {}
        from ai.agents.chat_ui import app as app_mod
        original = app_mod.AgentChatApp.new_session

        def spy(self):
            captured["before"] = self.session_id
            original(self)
            captured["after"] = self.session_id

        monkeypatch.setattr(app_mod.AgentChatApp, "new_session", spy)
        _, _, output = self._run(monkeypatch, [], ["/clear\r", "\x04"])
        assert captured["before"] != captured["after"]
        assert "new session" in output

    def test_thoughts_toggle(self, monkeypatch):
        config = ProgramConfig.get_current()
        before = bool(config.get(ProgramSetting.AGENT_THOUGHT, False))
        self._run(monkeypatch, [], ["/thoughts\r", "\x04"])
        assert bool(config.get(ProgramSetting.AGENT_THOUGHT, False)) is (not before)
        config.set(ProgramSetting.AGENT_THOUGHT, before)


def test_expand_mentions(tmp_path):
    from ai.agents.chat_ui.app import expand_mentions
    f = tmp_path / "notes.txt"
    f.write_text("hello file")
    text = f"look at @{f} please and @missing.txt"
    expanded = expand_mentions(text)
    assert "hello file" in expanded and "missing.txt" not in expanded.split("--- Attached Files ---")[1]
    assert expand_mentions("no mentions") == "no mentions"


class TestCtrlC:
    def _app(self, monkeypatch, responses):
        import ai.agents.agent as agent_mod
        from ai.agents.chat_ui import app as app_mod
        from prompt_toolkit.history import InMemoryHistory

        def fake_build(prog, pipeline, io=None, directory_manager=None):
            orch, conn, reg = make_orchestrator(responses, io=io)
            return orch

        monkeypatch.setattr(agent_mod, "build_orchestrator", fake_build)
        history = InMemoryHistory()
        chat = app_mod.AgentChatApp(MagicMock(), history=history)
        out = []
        chat.write = out.append
        chat.io.write = out.append
        return chat, history, out

    def _drive(self, chat, pipe, steps):
        async def scenario():
            run = asyncio.ensure_future(chat.run_async())
            for wait_for, keys in steps:
                for _ in range(200):
                    if wait_for(chat):
                        break
                    await asyncio.sleep(0.02)
                await asyncio.sleep(0.1)
                pipe.send_text(keys)
            await asyncio.wait_for(run, timeout=5)
        asyncio.run(scenario())

    def test_single_ctrl_c_exits_when_idle(self, monkeypatch):
        from prompt_toolkit.application import create_app_session
        from prompt_toolkit.input import create_pipe_input
        from prompt_toolkit.output import DummyOutput
        with create_pipe_input() as pipe, create_app_session(input=pipe, output=DummyOutput()):
            chat, _, _ = self._app(monkeypatch, [])
            self._drive(chat, pipe, [(lambda c: True, "\x03")])
        assert not chat.app.is_running

    def test_ctrl_c_with_draft_exits_and_keeps_draft(self, monkeypatch):
        from prompt_toolkit.application import create_app_session
        from prompt_toolkit.input import create_pipe_input
        from prompt_toolkit.output import DummyOutput
        with create_pipe_input() as pipe, create_app_session(input=pipe, output=DummyOutput()):
            chat, history, _ = self._app(monkeypatch, [])
            self._drive(chat, pipe, [(lambda c: True, "half typed idea"), (lambda c: True, "\x03")])
        assert "half typed idea" in list(history.load_history_strings())

    def test_ctrl_c_while_busy_interrupts_then_exits(self, monkeypatch):
        from prompt_toolkit.application import create_app_session
        from prompt_toolkit.input import create_pipe_input
        from prompt_toolkit.output import DummyOutput

        def slow(payload):
            # Block until the UI cancels the turn.
            for _ in range(300):
                if chat.orchestrator.cancel_event.is_set():
                    break
                time.sleep(0.01)
            return {"action": {"agent_target": "STOP"}}

        with create_pipe_input() as pipe, create_app_session(input=pipe, output=DummyOutput()):
            chat, _, out = self._app(monkeypatch, [slow])
            self._drive(chat, pipe, [
                (lambda c: True, "do something slow\r"),
                (lambda c: c.state.busy, "\x03"),          # interrupt
                (lambda c: not c.state.busy, "\x03"),      # now idle -> exit
            ])
        text = "\n".join(out)
        assert "Interrupted" in text
        assert not chat.app.is_running


class TestStuckModelCall:
    """A model call that ignores cancellation (e.g. remote API before its first token)."""

    def _setup(self, monkeypatch, responses):
        return TestCtrlC()._app(monkeypatch, responses)

    def test_interrupt_is_immediate_and_next_message_waits(self, monkeypatch):
        from prompt_toolkit.application import create_app_session
        from prompt_toolkit.input import create_pipe_input
        from prompt_toolkit.output import DummyOutput

        def stubborn(payload):
            time.sleep(1.0)  # does not look at the cancel flag
            return {"response_to_user": "LATE RESULT", "action": {"agent_target": "STOP"}}

        timings = {}
        with create_pipe_input() as pipe, create_app_session(input=pipe, output=DummyOutput()):
            chat, _, out = self._setup(monkeypatch, [stubborn, {"response_to_user": "second answer", "action": {"agent_target": "STOP"}}])

            async def scenario():
                run = asyncio.ensure_future(chat.run_async())
                await asyncio.sleep(0.2)
                pipe.send_text("slow request\r")
                await asyncio.sleep(0.3)
                assert chat.state.busy
                t = time.monotonic()
                pipe.send_text("\x03")
                while chat.state.busy:
                    await asyncio.sleep(0.01)
                timings["idle_after"] = time.monotonic() - t
                pipe.send_text("next message\r")        # must wait for the stubborn call
                await asyncio.sleep(0.1)
                assert not chat.state.busy and chat._waiting_message == "next message"
                for _ in range(300):
                    if "second answer" in "\n".join(out):
                        break
                    await asyncio.sleep(0.01)
                for _ in range(300):
                    if not chat.state.busy:
                        break
                    await asyncio.sleep(0.01)
                pipe.send_text("\x03")
                await asyncio.wait_for(run, timeout=5)

            asyncio.run(scenario())

        text = "\n".join(out)
        assert timings["idle_after"] < 0.3
        assert "Interrupted" in text
        assert "LATE RESULT" not in text          # discarded
        assert "second answer" in text            # waiting message ran afterwards

    def test_ctrl_c_twice_exits_even_if_call_still_running(self, monkeypatch):
        from prompt_toolkit.application import create_app_session
        from prompt_toolkit.input import create_pipe_input
        from prompt_toolkit.output import DummyOutput

        def hang(payload):
            time.sleep(3)
            return {"action": {"agent_target": "STOP"}}

        with create_pipe_input() as pipe, create_app_session(input=pipe, output=DummyOutput()):
            chat, _, _ = self._setup(monkeypatch, [hang])

            async def scenario():
                run = asyncio.ensure_future(chat.run_async())
                await asyncio.sleep(0.2)
                pipe.send_text("hang\r")
                await asyncio.sleep(0.3)
                start = time.monotonic()
                pipe.send_text("\x03")
                await asyncio.sleep(0.1)
                pipe.send_text("\x03")
                await asyncio.wait_for(run, timeout=2)
                return time.monotonic() - start

            elapsed = asyncio.run(scenario())
        assert elapsed < 1.0
