"""Tests for the agent XML response parser, including recovery of malformed responses."""

import pytest

import ai.program  # noqa: F401  (startup import order, avoids a circular import)
from ai.agents.xml_response_parser import ResponseParser

BODY = """  <thought><![CDATA[
1. I should list the files.
]]></thought>
  <manifest>
    <phase>exploration</phase>
    <current_priority>List project files</current_priority>
  </manifest>
  <notes><![CDATA[Nothing yet.]]></notes>
  <action>
    <tool_name>read_dir</tool_name>
    <tool_parameters>
      <path>@ROOT/src</path>
      <depth>1</depth>
    </tool_parameters>
    <agent_target>MASTER</agent_target>
  </action>
  <response_to_user>Listing the source folder.</response_to_user>
"""

VALID = f"<response>\n{BODY}</response>"


@pytest.fixture
def parser():
    return ResponseParser()


def assert_full(result):
    assert result["status"] == "SUCCESS", result
    assert result["thought"] == "1. I should list the files."
    assert result["notes"] == "Nothing yet."
    assert result["manifest"] == {"phase": "exploration", "current_priority": "List project files"}
    assert result["action"]["tool_name"] == "read_dir"
    assert result["action"]["tool_parameters"] == {"path": "@ROOT/src", "depth": "1"}
    assert result["action"]["agent_target"] == "MASTER"
    assert result["response_to_user"] == "Listing the source folder."


class TestStrict:
    def test_valid_response(self, parser):
        result = parser.parse(VALID)
        assert_full(result)
        assert "recovered" not in result

    def test_message_to_target_is_extracted(self, parser):
        raw = VALID.replace("<agent_target>MASTER</agent_target>",
                            "<agent_target>USER</agent_target><message_to_target>Which folder?</message_to_target>")
        assert parser.parse(raw)["action"]["message_to_target"] == "Which folder?"

    def test_rogue_angle_brackets_salvaged(self, parser):
        raw = VALID.replace("<path>@ROOT/src</path>", "<command>ls 2>/dev/null | head</command>")
        result = parser.parse(raw)
        assert result["status"] == "SUCCESS"
        assert result["action"]["tool_parameters"]["command"] == "ls 2>/dev/null | head"


class TestRecovery:
    def test_missing_response_wrapper(self, parser):
        result = parser.parse(BODY)
        assert_full(result)
        assert result["recovered"] is True
        assert "Missing response boundaries." in result["warnings"][0]

    def test_truncated_closing_wrapper(self, parser):
        result = parser.parse("<response>\n" + BODY)
        assert_full(result)
        assert result["recovered"] is True

    def test_code_fence_and_prose_around(self, parser):
        raw = f"Sure! Here is my response:\n```xml\n{BODY}```\nLet me know if you need more."
        assert_full(parser.parse(raw))

    def test_code_fenced_valid_response(self, parser):
        result = parser.parse(f"```xml\n{VALID}\n```")
        assert_full(result)

    def test_missing_action_wrapper(self, parser):
        raw = """<thought>Run it.</thought>
<tool_name>execute_command</tool_name>
<tool_parameters><command>pytest -q</command></tool_parameters>
<agent_target>MASTER</agent_target>
<response_to_user>Running the tests.</response_to_user>"""
        result = parser.parse(raw)
        assert result["status"] == "SUCCESS"
        assert result["action"]["tool_name"] == "execute_command"
        assert result["action"]["tool_parameters"] == {"command": "pytest -q"}
        assert result["action"]["agent_target"] == "MASTER"

    def test_truncated_last_tag(self, parser):
        raw = BODY.replace("<response_to_user>Listing the source folder.</response_to_user>",
                           "<response_to_user>Listing the source fol")
        result = parser.parse(raw)
        assert result["status"] == "SUCCESS"
        assert result["action"]["tool_name"] == "read_dir"
        assert result["response_to_user"].startswith("Listing the source fol")

    def test_truncated_inside_thought_with_reply_missing(self, parser):
        raw = "<thought><![CDATA[I was thinking about <action> and then"
        result = parser.parse(raw)
        assert result["status"] == "FAILED"

    def test_tags_quoted_inside_thought_are_ignored(self, parser):
        raw = """<thought><![CDATA[Example of what NOT to do:
<action><tool_name>delete_file</tool_name><agent_target>STOP</agent_target></action>
]]></thought>
<action>
  <tool_name>read_file</tool_name>
  <tool_parameters><path>a.py</path></tool_parameters>
  <agent_target>MASTER</agent_target>
</action>"""
        result = parser.parse(raw)
        assert result["action"]["tool_name"] == "read_file"
        assert result["action"]["agent_target"] == "MASTER"
        assert "delete_file" in result["thought"]

    def test_unescaped_markup_in_free_text_without_wrapper(self, parser):
        raw = """<thought>Compare a < b and use <div> tags</thought>
<action><tool_name>null</tool_name><agent_target>USER</agent_target></action>
<response_to_user>Use `<div class="x">` here & there.</response_to_user>"""
        result = parser.parse(raw)
        assert result["status"] == "SUCCESS"
        assert result["action"]["agent_target"] == "USER"
        assert '<div class="x">' in result["response_to_user"]
        assert "&" in result["response_to_user"]

    def test_params_with_code_and_cdata(self, parser):
        raw = """<action>
<tool_name>write_file</tool_name>
<tool_parameters>
  <path>@ROOT/x.html</path>
  <content><![CDATA[<html><body>Hi & bye</body></html>]]></content>
</tool_parameters>
<agent_target>MASTER</agent_target>
</action>"""
        params = parser.parse(raw)["action"]["tool_parameters"]
        assert params == {"path": "@ROOT/x.html", "content": "<html><body>Hi & bye</body></html>"}

    def test_repeated_params_become_list(self, parser):
        raw = """<action><tool_name>read_files</tool_name>
<tool_parameters><path>a.py</path><path>b.py</path></tool_parameters></action>"""
        assert parser.parse(raw)["action"]["tool_parameters"] == {"path": ["a.py", "b.py"]}

    def test_entities_unescaped(self, parser):
        raw = "<response_to_user>a &lt; b &amp;&amp; c</response_to_user>"
        assert parser.parse(raw)["response_to_user"] == "a < b && c"

    def test_leaked_think_block_ignored(self, parser):
        raw = "<think>maybe <action><tool_name>delete_file</tool_name></action></think>\n" + BODY
        assert_full(parser.parse(raw))

    def test_spaces_inside_tags(self, parser):
        raw = "< action >< tool_name >read_dir</ tool_name ></ action >< response_to_user >ok</ response_to_user >"
        result = parser.parse(raw)
        assert result["action"]["tool_name"] == "read_dir"
        assert result["response_to_user"] == "ok"

    def test_only_reply_is_enough(self, parser):
        result = parser.parse("<response_to_user>Done, all tests pass.</response_to_user>")
        assert result["status"] == "SUCCESS"
        assert result["response_to_user"] == "Done, all tests pass."

    def test_json_parameter_mode(self):
        parser = ResponseParser(parameter_mode="json")
        raw = '<action><tool_name>x</tool_name><tool_parameters>{"a": 1}</tool_parameters></action>'
        assert parser.parse(raw)["action"]["tool_parameters"] == {"a": 1}


class TestStillFails:
    @pytest.mark.parametrize("raw", [
        "",
        "I think the answer is 42, but I forgot the format.",
        "<thought>Just thinking, no decision yet.</thought>",
        "<thought>x</thought><action><tool_name>null</tool_name></action>",
        "<manifest><phase>x</phase></manifest><notes>n</notes>",
    ])
    def test_no_usable_instruction(self, parser, raw):
        result = parser.parse(raw)
        assert result["status"] == "FAILED"
        assert result["response_to_user"] == raw  # raw text still available for display/debug

    def test_none_input(self, parser):
        assert parser.parse(None)["status"] == "FAILED"


class TestConnectorUsesRecovery:
    def test_send_request_recovers_wrapperless_output(self, tmp_path, monkeypatch):
        from unittest.mock import MagicMock
        from ai.agents.llm_connector import LLMConnector

        prompt = tmp_path / "prompt.md"
        prompt.write_text("You are an agent. {{TOOLS}} {{AGENT_OUTPUT_RULES}}")
        llm = MagicMock()
        connector = LLMConnector(llm)
        monkeypatch.setattr(connector, "_execute_llm_call", lambda messages: BODY)
        result = connector.send_request({"objective": "x"}, str(prompt), agent_config={"tools": [], "allowed_targets": ["STOP"]})
        assert_full(result)
        assert result["recovered"] is True
