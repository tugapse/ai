import hashlib
import os
import sys
import uuid
from unittest.mock import patch, MagicMock

import pytest

import ai.functions as ai_functions

# --- 1. CIRCULAR IMPORT & UI BYPASS ---
# Use the real ai.functions module and patch the specific behavior we need locally.
# Replacing the module globally causes import leakage across later tests.

# Mock the Terminal UI so tests run silently
mock_ui = MagicMock()
sys.modules["ai.core.terminal_ui"] = mock_ui
sys.modules["terminal_ui"] = mock_ui

# THE FUSE CUTTER: Stop thinking_log_manager from loading program.py
mock_program = MagicMock()
sys.modules["program"] = mock_program
sys.modules["ai.program"] = mock_program

# Now we import the class we want to test
from ai.agents.agent_orchestrator import AgentOrchestrator


class MockConnector:
    """Fakes the 8B Model. Returns predefined JSON responses."""

    def __init__(self, responses):
        self.responses = responses
        self.request_history = []

    def send_request(self, payload, prompt_file_path, agent_config):
        self.request_history.append(payload)
        if self.responses:
            return self.responses.pop(0)
        return {"action": {"agent_target": "STOP"}}

    def send_raw_request(self, payload, system_prompt):
        yield "mocked_raw_text"

    def get_context_limit(self):
        return 8192

    def get_max_tokens(self):
        return 1024


class MockRegistry:
    """Fakes the Tool Execution so we don't actually modify files."""

    def get_tool_info(self, tool_name):
        return f"Mock info for {tool_name}"

    def execute_tool(self, tool_name, params):
        return {"status": "SUCCESS", "mock_data": f"Did {tool_name}"}

    def get_all_tools(self):
        return {}


class TestMessageOrchestrator:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path, monkeypatch):
        self.test_root = str(tmp_path / "workspace")
        self.root_dir_mock = MagicMock(return_value=self.test_root)
        monkeypatch.setattr(ai_functions, "get_root_directory", self.root_dir_mock)
        self.session_id = f"test-session-{uuid.uuid4().hex}"

        digest = hashlib.sha256(os.path.abspath(self.test_root).encode("utf-8")).hexdigest()[:16]
        storage_dir = os.path.join(self.test_root, "logs", "agents", digest)
        if os.path.isdir(storage_dir):
            for filename in os.listdir(storage_dir):
                file_path = os.path.join(storage_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)

        self.pipeline_config = {
            "entry_point": "MANAGER",
            "max_iterations": 10,
            "agents": {
                "MANAGER": {
                    "role": "management",
                    "tools": ["smart_search"],
                    "allowed_targets": ["CODER", "STOP", "USER"],
                    "prompt_file_path": "manager.md"
                },
                "CODER": {
                    "role": "worker",
                    "tools": ["write_file", "patch_file"],
                    "allowed_targets": ["MANAGER", "STOP"],
                    "prompt_file_path": "coder.md"
                }
            }
        }
        self.registry = MockRegistry()
        self.module_registry = MagicMock()

    def log_test(self, title):
        print(f"\n[TEST] {title}")

    def test_routing_one_and_done(self):
        self.log_test("One and Done")
        mock_responses = [
            {
                "action": {"tool_name": "smart_search", "tool_parameters": {"pattern": "main"}},
                "manifest": {"current_priority": "Searching..."}
            },
            {
                "action": {"agent_target": "STOP", "message_to_target": "I am done."}
            }
        ]
        connector = MockConnector(mock_responses)
        orchestrator = AgentOrchestrator(llm_connector=connector, tool_registry=self.registry, pipeline_config=self.pipeline_config, module_registry=self.module_registry)

        with patch("builtins.input", return_value="y"):
            orchestrator.run_loop("Find the main file.", session_id=self.session_id)

        assert len(connector.request_history) == 2
        assert len(orchestrator.memory.context.tool_results) == 1

    def test_routing_clean_handoff(self):
        self.log_test("Clean Handoff (MANAGER -> CODER)")
        mock_responses = [
            {"action": {"agent_target": "CODER", "message_to_target": "Write the code."}},
            {"action": {"agent_target": "STOP"}}
        ]
        connector = MockConnector(mock_responses)
        orchestrator = AgentOrchestrator(llm_connector=connector, tool_registry=self.registry, pipeline_config=self.pipeline_config, module_registry=self.module_registry)

        orchestrator.run_loop("Write a script.", session_id=self.session_id)

        coder_history = orchestrator.memory.get_agent_memory("CODER").history
        assert any("Write the code" in msg.get("message", "") for msg in coder_history)

    def test_routing_hallucinated_target(self):
        self.log_test("Hallucinated Target Bounce")
        mock_responses = [
            {"action": {"agent_target": "BATMAN"}},
            {"action": {"agent_target": "STOP"}}
        ]
        connector = MockConnector(mock_responses)
        orchestrator = AgentOrchestrator(llm_connector=connector, tool_registry=self.registry, pipeline_config=self.pipeline_config, module_registry=self.module_registry)

        orchestrator.run_loop("Call Batman.", session_id=self.session_id)

        manager_history = orchestrator.memory.get_agent_memory("MANAGER").history
        assert any("Invalid transition target" in msg.get("message", "") for msg in manager_history)

    def test_death_loop_strikeout(self):
        self.log_test("Strikeout (3 Fails = Halt)")
        mock_responses = [
            {"status": "FAILED", "error": "Bad JSON 1"},
            {"status": "FAILED", "error": "Bad JSON 2"},
            {"status": "FAILED", "error": "Bad JSON 3"},
            {"action": {"agent_target": "STOP"}}
        ]
        connector = MockConnector(mock_responses)
        orchestrator = AgentOrchestrator(llm_connector=connector, tool_registry=self.registry, pipeline_config=self.pipeline_config, module_registry=self.module_registry)

        orchestrator.run_loop("Break the parser.", session_id=self.session_id)

        assert len(connector.request_history) == 3
        assert orchestrator.format_error_count == 3

    def test_death_loop_recovery(self):
        self.log_test("Recovery (2 Fails -> Success -> Reset)")
        mock_responses = [
            {"status": "FAILED", "error": "Bad JSON 1"},
            {"status": "FAILED", "error": "Bad JSON 2"},
            {"action": {"agent_target": "STOP"}}
        ]
        connector = MockConnector(mock_responses)
        orchestrator = AgentOrchestrator(llm_connector=connector, tool_registry=self.registry, pipeline_config=self.pipeline_config, module_registry=self.module_registry)

        orchestrator.run_loop("Recover from error.", session_id=self.session_id)

        assert len(connector.request_history) == 3
        assert orchestrator.format_error_count == 0
