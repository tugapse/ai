"""Edits from small models: indentation kept, JSON-style escapes repaired, broken files reported."""

import json
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

sys.modules.setdefault("ai.core.terminal_ui", MagicMock())
sys.modules.setdefault("ai.program", MagicMock())

from ai.agents.xml_response_parser import ResponseParser
from ai.agents.payload_limits import cap_tool_result
from ai.agents.context_sentinel import ContextSentinel
import ai.tools.base as base
from ai.modules.tools_filesystem.tools import patch_file, write_file, read_file, _looks_escaped

PATCH_RESPONSE = """<response>
  <thought><![CDATA[patch the method]]></thought>
  <action>
    <tool_name>patch_file</tool_name>
    <tool_parameters>
      <path>
        @ROOT/a.py
      </path>
      <search><![CDATA[
        return self.x
]]></search>
      <replace><![CDATA[
        value = self.x
        return value * 2
    ]]></replace>
    </tool_parameters>
    <agent_target>SELF</agent_target>
  </action>
  <response_to_user><![CDATA[patching]]></response_to_user>
</response>"""


class TestParserKeepsIndentation:
    def test_strict_xml(self):
        params = ResponseParser().parse(PATCH_RESPONSE)["action"]["tool_parameters"]
        assert params["path"] == "@ROOT/a.py"
        assert params["search"] == "        return self.x"
        assert params["replace"] == "        value = self.x\n        return value * 2"

    def test_recovery_path(self):
        broken = PATCH_RESPONSE.replace("</response>", "")   # no closing wrapper: field extraction
        params = ResponseParser().parse(broken)["action"]["tool_parameters"]
        assert params["search"] == "        return self.x"
        assert params["replace"].startswith("        value = self.x\n")


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "PROJECT_ROOT", str(tmp_path))
    return tmp_path


OPS = 'def add(a, b):\n    return a + b\n\n\ndef subtract(a: float, b: float) -> float:\n    """Returns a minus b."""\n    return a - b\n'


class TestEscapesAndWarnings:
    def test_escaped_replace_is_repaired(self, project):
        (project / "ops.py").write_text(OPS)
        res = patch_file(path="@ROOT/ops.py", search='    return a - b',
                         replace='    return a - b\\n\\n\\ndef multiply(a, b):\\n    return a * b')
        assert res["status"] == "SUCCESS" and "line breaks" in res["note"] and "warning" not in res
        assert (project / "ops.py").read_text().endswith("def multiply(a, b):\n    return a * b\n")

    def test_escaped_search_is_found(self, project):
        (project / "ops.py").write_text(OPS)
        res = patch_file(path="@ROOT/ops.py", search='def add(a, b):\\n    return a + b\\n',
                         replace='def add(a, b):\n    return b + a\n')
        assert res["status"] == "SUCCESS" and "return b + a" in (project / "ops.py").read_text()

    def test_the_e2e_call_warns_about_duplicates(self, project):
        (project / "ops.py").write_text(OPS)
        res = patch_file(path="@ROOT/ops.py", search="def subtract(a: float, b: float) -> float:",
                         replace='def subtract(a: float, b: float) -> float:\\n    """Returns a minus b."""\\n    return a - b'
                                 '\\n\\ndef multiply(a: float, b: float) -> float:\\n    """Returns the product of a and b."""\\n    return a * b')
        assert res["status"] == "SUCCESS" and "duplicated" in res["warning"]

    def test_syntax_warning(self, project):
        res = write_file(path="@ROOT/bad.py", content="def x(:\n    pass\n")
        assert res["status"] == "SUCCESS" and "SyntaxError line 1" in res["warning"]
        assert "warning" not in write_file(path="@ROOT/ok.py", content="x = 1\n")
        assert "not valid JSON" in write_file(path="@ROOT/c.json", content="{bad")["warning"]
        assert "warning" not in write_file(path="@ROOT/notes.txt", content="def x(:")

    def test_inline_search_inside_indented_line(self, project):
        (project / "a.py").write_text("class A:\n    def get(self):\n        return self.x\n")
        res = patch_file(path="@ROOT/a.py", search="return self.x",
                         replace="        value = self.x\n        return value * 2")
        assert res["status"] == "SUCCESS" and "warning" not in res
        assert (project / "a.py").read_text() == "class A:\n    def get(self):\n        value = self.x\n        return value * 2\n"

    def test_first_line_indented_like_the_xml(self, project):
        """The E2E case: the model indented the first CDATA line to the XML nesting level."""
        (project / "ops.py").write_text(OPS)
        res = patch_file(path="@ROOT/ops.py",
                         search='        def subtract(a: float, b: float) -> float:\n    """Returns a minus b."""\n    return a - b',
                         replace='        def subtract(a: float, b: float) -> float:\n    """Returns a minus b."""\n    return a - b\n\n\n'
                                 'def multiply(a: float, b: float) -> float:\n    return a * b')
        assert res["status"] == "SUCCESS" and "ignoring indentation" in res["note"] and "warning" not in res
        assert (project / "ops.py").read_text().endswith(
            'def subtract(a: float, b: float) -> float:\n    """Returns a minus b."""\n    return a - b\n\n\n'
            'def multiply(a: float, b: float) -> float:\n    return a * b\n')

    def test_block_with_wrong_relative_indent(self, project):
        (project / "a.py").write_text("class A:\n    def get(self):\n        return self.x\n")
        res = patch_file(path="@ROOT/a.py", search="def get(self):\n    return self.x",
                         replace="def get(self):\n    return self.x * 2")
        assert res["status"] == "SUCCESS"
        assert (project / "a.py").read_text() == "class A:\n    def get(self):\n        return self.x * 2\n"

    def test_ambiguous_tolerant_match_fails(self, project):
        (project / "a.py").write_text("def a():\n    pass\n\ndef b():\n  pass\n")
        assert patch_file(path="@ROOT/a.py", search="  pass", replace="  return 1")["status"] == "FAILED"

    def test_escape_detection_limits(self, project):
        assert _looks_escaped("a\\nb\\nc")
        assert not _looks_escaped('print("a\\nb")')                 # a single \n is code
        assert not _looks_escaped('{"text": "a\\nb\\nc"}')           # minified JSON is legit
        assert not _looks_escaped("line one\nline\\ntwo\\nthree")   # has real line breaks
        write_file(path="@ROOT/data.json", content='{"text": "a\\nb\\nc"}')
        assert (project / "data.json").read_text() == '{"text": "a\\nb\\nc"}'

    def test_read_file_line_range(self, project):
        (project / "big.py").write_text("\n".join(f"line {i}" for i in range(1, 11)))
        res = read_file(path="@ROOT/big.py", start_line=4, end_line=6)
        assert res["files"]["@ROOT/big.py"] == "line 4\nline 5\nline 6"
        assert res["line_ranges"]["@ROOT/big.py"] == [4, 6, 10]
        assert "line_ranges" not in read_file(path="@ROOT/big.py")


class TestPayloadLimits:
    def test_file_results_are_cut_by_lines_with_a_way_to_continue(self):
        content = "\n".join(f"line {i:04d}" for i in range(1, 2001))
        capped = cap_tool_result({"status": "SUCCESS", "files": {"@ROOT/big.py": content}}, 1000)
        text = capped["files"]["@ROOT/big.py"]
        assert capped["truncated"] is True and len(text) < 1300
        assert text.startswith("line 0001") and "Read the rest with read_file start_line=" in text
        # a ranged read continues the numbering
        ranged = cap_tool_result({"status": "SUCCESS", "files": {"p": content}, "line_ranges": {"p": [500, 2499, 3000]}}, 1000)
        assert "showing lines 500-" in ranged["files"]["p"]

    def test_other_results_get_a_preview(self):
        capped = cap_tool_result({"status": "SUCCESS", "output": "x" * 5000}, 1000)
        assert capped["status"] == "SUCCESS" and capped["truncated"] and len(capped["preview"]) == 1000

    def test_small_results_are_untouched(self):
        result = {"status": "SUCCESS", "files": {"a": "short"}}
        assert cap_tool_result(result, 1000) is result
        assert cap_tool_result({"x": "y" * 5000}, 0)["x"]


class Conn:
    def __init__(self, window, out):
        self.window, self.out = window, out

    def get_context_limit(self):
        return self.window

    def get_max_tokens(self):
        return self.out


class TestSentinelLimits:
    def test_limits_are_read_on_every_check(self):
        conn = Conn(2048, 12096)                       # gguf before loading: window looks tiny
        sentinel = ContextSentinel(conn, threshold=0.9, max_tokens=2048, buffer=12096)
        assert sentinel.current_limits() == (2048, 1024)   # reserve capped at half the window
        conn.window = 35000
        assert sentinel.current_limits() == (35000, 12096)

    def test_pressure_counts_prompt_overhead(self):
        sentinel = ContextSentinel(Conn(10000, 2000), threshold=0.9)
        memory = MagicMock()
        payload = {"objective": "x" * 3200}               # ~1000 tokens of 8000 available
        _, compressed = sentinel.enforce_limits("A", memory, payload)
        assert not compressed and 0.1 < sentinel.last_pressure < 0.2
        sentinel.enforce_limits("A", memory, payload, overhead_chars=3200 * 5)
        assert 0.7 < sentinel.last_pressure < 0.8

    def test_unmeasurable_window_disables_with_a_warning(self, monkeypatch):
        import ai.agents.context_sentinel as cs
        logs = []
        monkeypatch.setattr(cs.func, "log", lambda msg, **kw: logs.append(msg))
        sentinel = ContextSentinel(Conn(0, 0), threshold=0.9, max_tokens=0, buffer=0)
        assert sentinel.enforce_limits("A", MagicMock(), {"a": 1}) == ({"a": 1}, False)
        sentinel.enforce_limits("A", MagicMock(), {"a": 1})
        assert len([l for l in logs if "cannot measure" in l]) == 1


def test_base_model_keeps_backend_context_window():
    from ai.core.llms.base_llm import BaseModel
    fake = SimpleNamespace(options={"max_new_tokens": 12096},
                           token_info_count=SimpleNamespace(max_context_window=35000, max_output_tokens=0))
    BaseModel._load_llm_params(fake)
    assert fake.token_info_count.max_context_window == 35000 and fake.token_info_count.max_output_tokens == 12096
    empty = SimpleNamespace(options={}, token_info_count=SimpleNamespace(max_context_window=0, max_output_tokens=0))
    BaseModel._load_llm_params(empty)
    assert empty.token_info_count.max_context_window == 2048


def test_payload_caps_results_but_memory_keeps_them(tmp_path, monkeypatch):
    import ai.functions as ai_functions
    from ai.agents.agent_orchestrator import AgentOrchestrator
    monkeypatch.setattr(ai_functions, "get_root_directory", MagicMock(return_value=str(tmp_path)))
    pipeline = {"entry_point": "MASTER", "agents": {"MASTER": {"role": "management", "prompt_file_path": "m.md",
                                                               "allowed_targets": ["USER"], "tools": []}}}
    conn = MagicMock()
    conn.get_context_limit.return_value, conn.get_max_tokens.return_value = 100000, 1000
    orch = AgentOrchestrator(conn, MagicMock(), pipeline, MagicMock())
    big = {"status": "SUCCESS", "files": {"@ROOT/big.py": "\n".join(f"line {i}" for i in range(5000))}}
    orch.memory.record_tool_result("MASTER", "read_file", {"path": "@ROOT/big.py"}, big)
    payload = orch._prepare_payload("q", "MASTER")
    sent = payload["messages_received"][-1]["result"]
    assert sent["truncated"] is True and "read_file start_line=" in sent["files"]["@ROOT/big.py"]
    assert orch.memory.get_agent_memory("MASTER").messages_received[-1]["result"] is big
    assert orch._prompt_overhead({"tool_descriptions": "x" * 100}) >= 100


def test_recent_outcomes_are_short(tmp_path, monkeypatch):
    import ai.functions as ai_functions
    from ai.agents.agent_orchestrator import AgentOrchestrator
    monkeypatch.setattr(ai_functions, "get_root_directory", MagicMock(return_value=str(tmp_path)))
    pipeline = {"entry_point": "MASTER", "agents": {"MASTER": {"role": "management", "prompt_file_path": "m.md",
                                                               "allowed_targets": ["USER"], "tools": []}}}
    orch = AgentOrchestrator(MagicMock(), MagicMock(), pipeline, MagicMock())
    big = {"status": "SUCCESS", "files": {"@ROOT/a.py": "x = 1\n" * 20000}}
    out = orch._format_recent_outcomes([{"tool": "read_files", "result": big}])
    assert out[0]["tool"] == "read_files" and len(out[0]["result"]) < 2500 and "truncated" in out[0]["result"]


def _orch(tmp_path, monkeypatch):
    import ai.functions as ai_functions
    from ai.agents.agent_orchestrator import AgentOrchestrator
    monkeypatch.setattr(ai_functions, "get_root_directory", MagicMock(return_value=str(tmp_path)))
    pipeline = {"entry_point": "MASTER", "agents": {"MASTER": {"role": "management", "prompt_file_path": "m.md",
                                                               "allowed_targets": ["USER"], "tools": []}}}
    conn = MagicMock()
    conn.get_context_limit.return_value, conn.get_max_tokens.return_value = 100000, 1000
    return AgentOrchestrator(conn, MagicMock(), pipeline, MagicMock())


def _big(n):
    return {"status": "SUCCESS", "files": {f"@ROOT/f{n}.py": "\n".join(f"line {i} of file {n}" for i in range(3000))}}


def test_last_two_tool_results_keep_their_size(tmp_path, monkeypatch):
    orch = _orch(tmp_path, monkeypatch)
    mem = orch.memory.get_agent_memory("MASTER")
    for n in range(3):                          # three earlier results, already in history
        mem.history.append({"from": "SYSTEM", "result": _big(n)})
    orch.memory.record_tool_result("MASTER", "read_file", {}, _big(3))     # this turn's result
    payload = orch._prepare_payload("q", "MASTER")
    sizes = [len(str(m["result"])) for m in payload["conversation_history"]]
    assert sizes[0] < 2500 and sizes[1] < 2500     # older: short reminders
    assert sizes[2] > 5000                          # the latest history result keeps the normal limit
    assert len(str(payload["messages_received"][-1]["result"])) > 5000


def test_sentinel_keeps_the_latest_results():
    from ai.agents.memory_manager import MemoryManager
    mm = MemoryManager(["A"])
    mem = mm.get_agent_memory("A")
    mem.history = [{"from": "USER", "message": "go"}, {"from": "SYSTEM", "result": _big(0)},
                   {"from": "SYSTEM", "result": _big(1)}, {"from": "SELF", "thought": "a"},
                   {"from": "SELF", "thought": "b"}, {"from": "SELF", "thought": "c"}]
    mem.messages_received = [{"from": "SYSTEM", "result": _big(2)}]
    conn = MagicMock()
    conn.get_context_limit.return_value, conn.get_max_tokens.return_value = 1000, 100
    conn.send_raw_request.return_value = "summary"
    sentinel = ContextSentinel(conn, threshold=0.1)
    _, compressed = sentinel.enforce_limits("A", mm, {"x": "y" * 10000}, keep_recent_results=2)
    assert compressed
    assert mem.messages_received[0]["result"] == _big(2)          # this turn's result not distilled
    conn.send_raw_request.assert_not_called()
    kept = [m for m in mem.history if "result" in m]
    assert kept == [{"from": "SYSTEM", "result": _big(1)}]        # + the previous one = 2 recent results
    assert [m.get("thought") for m in mem.history[-3:]] == ["a", "b", "c"]
