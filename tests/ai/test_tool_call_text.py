"""
An action dict (an engine caught a tool call in the model's output) travels as its tool call
text: the server sends it to clients and the CLI writes it, and the parser reads the same call back.
"""

import ai.program  # noqa: F401  (startup import order, avoids a circular import)
from ai.tools.tool_registry import ToolRegistry


def test_round_trip():
    action = {"type": "function_call", "name": "read_file", "args": {"path": "a b/ç.txt", "lines": [1, 2]}}
    text = ToolRegistry.format_manual_tag(action)
    assert text.startswith("____@read_file {")
    assert ToolRegistry.parse_manual_tags(text) == action


def test_undecodable_arguments_are_kept_as_written():
    action = {"type": "function_call", "name": "run", "args": {"raw": "{cmd: ls -la, ]"}}
    assert ToolRegistry.format_manual_tag(action) == "____@run {cmd: ls -la, ]"


def test_as_text():
    assert ToolRegistry.as_text("olá") == "olá"
    assert ToolRegistry.as_text({"type": "function_call", "name": "x", "args": {}}) == "____@x {}"
    assert ToolRegistry.as_text(42) == "42"


class TestDirectAsk:
    """The CLI's ask(): action dicts used to crash _sanitize_token (unicodedata on a dict)."""

    class FakeLLM:
        model_name = "fake"

        def __init__(self, output):
            self.output = output

        def chat(self, messages, stream=True):
            return self.output

    def ask(self, tmp_path, output, stream=True):
        from ai.direct import ask
        out = tmp_path / "out.md"
        ask(self.FakeLLM(output), [{"role": "user", "content": "hi"}], write_to_file=True,
            output_filename=str(out), print_output=False, hide_think_anim=True, stream=stream)
        return out.read_text(encoding="utf-8")

    def test_action_dict_is_written_as_tool_call_text(self, tmp_path):
        action = {"type": "function_call", "name": "read_file", "args": {"path": "x"}}
        written = self.ask(tmp_path, iter(["Vou ler. ", action]))
        assert "Vou ler." in written and '____@read_file {"path": "x"}' in written

    def test_whole_text_reply_is_not_split_into_characters(self, tmp_path):
        assert "olá mundo" in self.ask(tmp_path, "olá mundo", stream=False)
