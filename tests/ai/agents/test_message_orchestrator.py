import sys
import unittest
from unittest.mock import patch, MagicMock

# --- 1. CIRCULAR IMPORT & UI BYPASS ---
mock_func = MagicMock()
sys.modules["functions"] = mock_func
sys.modules["ai.functions"] = mock_func

# Mock the Terminal UI so tests run silently
mock_ui = MagicMock()
sys.modules["ai.core.terminal_ui"] = mock_ui
sys.modules["terminal_ui"] = mock_ui

# THE FUSE CUTTER: Stop thinking_log_manager from loading program.py
mock_program = MagicMock()
sys.modules["program"] = mock_program
sys.modules["ai.program"] = mock_program

# Now we import the class we want to test
from ai.agents.agent import MessageOrchestrator


# =================================================================
#  DUMMY COMPONENTS (The Fake LLM and Fake Tools)
# =================================================================

class MockConnector:
    """Fakes the 8B Model. Returns predefined JSON responses."""
    def __init__(self, responses):
        self.responses = responses
        self.request_history = []  # To verify what was sent to the model

    def send_request(self, payload, prompt_file_path, agent_config):
        self.request_history.append(payload)
        if self.responses:
            return self.responses.pop(0)
        return {"action": {"agent_target": "STOP"}} # Failsafe

    def send_raw_request(self, payload, system_prompt):
        yield "mocked_raw_text"

class MockRegistry:
    """Fakes the Tool Execution so we don't actually modify files."""
    def get_tool_info(self, tool_name):
        return f"Mock info for {tool_name}"

    def execute_tool(self, tool_name, params):
        return {"status": "SUCCESS", "mock_data": f"Did {tool_name}"}

# =================================================================
#  THE TEST SUITE
# =================================================================

class TestMessageOrchestrator(unittest.TestCase):

    def setUp(self):
        """Sets up a fresh pipeline for every test."""
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

    def log_test(self, title):
        print(f"\n[TEST] {title}")

    # --- CATEGORY 1: ROUTING & STATE MACHINE ---

    def test_routing_one_and_done(self):
        self.log_test("One and Done")
        # Model does a tool call, then immediately stops.
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
        orchestrator = MessageOrchestrator(connector, self.registry, self.pipeline_config)
        
        # Patch input just in case, though it shouldn't be called here
        with patch('builtins.input', return_value='y'):
            orchestrator.run_loop("Find the main file.")

        # Verify it stopped without blowing through max_iterations
        self.assertEqual(len(connector.request_history), 2)
        # Verify it saved the tool result
        self.assertEqual(len(orchestrator.context["tool_results"]), 1)

    def test_routing_clean_handoff(self):
        self.log_test("Clean Handoff (MANAGER -> CODER)")
        mock_responses = [
            # MANAGER hands off to CODER
            {"action": {"agent_target": "CODER", "message_to_target": "Write the code."}},
            # CODER stops
            {"action": {"agent_target": "STOP"}}
        ]
        connector = MockConnector(mock_responses)
        orchestrator = MessageOrchestrator(connector, self.registry, self.pipeline_config)
        
        orchestrator.run_loop("Write a script.")
        
        # Verify CODER actually received the message from MANAGER in its history
        coder_history = orchestrator.agent_memory["CODER"]["history"]
        self.assertTrue(any("Write the code" in msg.get("message", "") for msg in coder_history))

    def test_routing_hallucinated_target(self):
        self.log_test("Hallucinated Target Bounce")
        mock_responses = [
            # MANAGER hallucinates BATMAN
            {"action": {"agent_target": "BATMAN"}},
            # System should bounce it back to MANAGER, who then STOPs
            {"action": {"agent_target": "STOP"}}
        ]
        connector = MockConnector(mock_responses)
        orchestrator = MessageOrchestrator(connector, self.registry, self.pipeline_config)
        
        orchestrator.run_loop("Call Batman.")
        
        # Verify the system injected an error message in MANAGER's history
        manager_history = orchestrator.agent_memory["MANAGER"]["history"]
        self.assertTrue(any("Invalid transition target" in msg.get("message", "") for msg in manager_history))

    # --- CATEGORY 5: DEATH LOOP BREAKER ---

    def test_death_loop_strikeout(self):
        self.log_test("Strikeout (3 Fails = Halt)")
        # Model returns invalid JSON 3 times in a row
        mock_responses = [
            {"status": "FAILED", "error": "Bad JSON 1"},
            {"status": "FAILED", "error": "Bad JSON 2"},
            {"status": "FAILED", "error": "Bad JSON 3"},
            {"action": {"agent_target": "STOP"}} # Should never reach this
        ]
        connector = MockConnector(mock_responses)
        orchestrator = MessageOrchestrator(connector, self.registry, self.pipeline_config)
        
        orchestrator.run_loop("Break the parser.")
        
        # Verify it halted exactly after 3 attempts
        self.assertEqual(len(connector.request_history), 3)
        self.assertEqual(orchestrator.format_error_count, 3)

    def test_death_loop_recovery(self):
        self.log_test("Recovery (2 Fails -> Success -> Reset)")
        mock_responses = [
            {"status": "FAILED", "error": "Bad JSON 1"},
            {"status": "FAILED", "error": "Bad JSON 2"},
            {"action": {"agent_target": "STOP"}} # 3rd try is valid JSON
        ]
        connector = MockConnector(mock_responses)
        orchestrator = MessageOrchestrator(connector, self.registry, self.pipeline_config)
        
        orchestrator.run_loop("Recover from error.")
        
        # Verify it processed all 3, and the strike counter reset to 0
        self.assertEqual(len(connector.request_history), 3)
        self.assertEqual(orchestrator.format_error_count, 0)

if __name__ == "__main__":
    unittest.main()