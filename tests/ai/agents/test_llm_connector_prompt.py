"""The system prompt the model receives must be fully assembled (no template placeholders)."""

import os
from types import SimpleNamespace

import ai.program  # noqa: F401  (startup import order, avoids a circular import)
from ai.agents.llm_connector import LLMConnector


def test_system_message_and_attribute_carry_the_injected_rules(tmp_path, monkeypatch):
    prompt = tmp_path / "agent.md"
    prompt.write_text("ROLE\n{{TOOLS}}\n{{AGENT_OUTPUT_RULES}}", encoding="utf-8")
    system_dir = tmp_path / "system"
    (system_dir / "inject").mkdir(parents=True)
    (system_dir / "inject" / "agent-out.md").write_text("OUTPUT RULES: emit <response> XML", encoding="utf-8")
    monkeypatch.setattr("ai.agents.llm_connector.DirectoryManager.get_system_dir", lambda self: str(system_dir))

    llm = SimpleNamespace(system_prompt="")
    connector = LLMConnector(llm)
    sent = []
    monkeypatch.setattr(connector, "_execute_llm_call", lambda messages: sent.append(messages) or "<response></response>")

    connector.send_request({"task": "x"}, str(prompt), agent_config={
        "tools": ["read_file"], "tool_descriptions": "- read_file", "allowed_targets": ["SELF", "USER"],
    })

    system_message = sent[0][0]["content"]
    for text in (system_message, llm.system_prompt):
        assert "{{" not in text
        assert "OUTPUT RULES: emit <response> XML" in text
        assert "ALLOWED AGENT TARGETS: SELF, USER" in text
    assert system_message == llm.system_prompt
