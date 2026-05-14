import os
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
from agents.message_orchestrator import MessageOrchestrator


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

# =================================================================
#  THE TEST SUITE
# =================================================================

class TestMessageOrchestrator(unittest.TestCase):

    def setUp(self):
        """Sets up a fresh pipeline for every test."""
        # --- 1. CONFIGURE THE MOCK ---
        # The SessionVault depends on get_root_directory() to find the project root
        # and build the path to the /logs/agents directory. In the test environment,
        # the `functions` module is mocked. We MUST configure the mock to return a
        # valid path, otherwise SessionVault cannot read, write, or delete sessions.
        # We use os.getcwd() to ensure it points to the project root where `pytest` is run.
        self.test_root = os.getcwd()
        mock_func.get_root_directory.return_value = self.test_root

        # --- 2. CLEAN UP PREVIOUS TEST STATE ---
        # Now that the mock is configured, we can reliably find and delete the
        # session file from the previous test run.
        session_file = os.path.join(self.test_root, "logs", "agents", "test-session.json")
        if os.path.exists(session_file):
            os.remove(session_file)

        # --- 3. SET UP TEST-SPECIFIC CONFIG ---
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
        orchestrator = MessageOrchestrator(connector, self.registry, self.pipeline_config, self.module_registry)
        
        # Patch input just in case, though it shouldn't be called here
        with patch('builtins.input', return_value='y'):
            orchestrator.run_loop("Find the main file.", session_id="test-session")

        # Verify it stopped without blowing through max_iterations
        self.assertEqual(len(connector.request_history), 2)
        # Verify it saved the tool result
        self.assertEqual(len(orchestrator.memory.context.tool_results), 1)

    def test_routing_clean_handoff(self):
        self.log_test("Clean Handoff (MANAGER -> CODER)")
        mock_responses = [
            # MANAGER hands off to CODER
            {"action": {"agent_target": "CODER", "message_to_target": "Write the code."}},
            # CODER stops
            {"action": {"agent_target": "STOP"}}
        ]
        connector = MockConnector(mock_responses)
        orchestrator = MessageOrchestrator(connector, self.registry, self.pipeline_config, self.module_registry)
        
        orchestrator.run_loop("Write a script.", session_id="test-session")
        
        # Verify CODER actually received the message from MANAGER in its history
        coder_history = orchestrator.memory.get_agent_memory("CODER").history
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
        orchestrator = MessageOrchestrator(connector, self.registry, self.pipeline_config, self.module_registry)
        
        orchestrator.run_loop("Call Batman.", session_id="test-session")
        
        # Verify the system injected an error message in MANAGER's history
        manager_history = orchestrator.memory.get_agent_memory("MANAGER").history
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
        orchestrator = MessageOrchestrator(connector, self.registry, self.pipeline_config, self.module_registry)
        
        orchestrator.run_loop("Break the parser.", session_id="test-session")
        
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
        orchestrator = MessageOrchestrator(connector, self.registry, self.pipeline_config, self.module_registry)
        
        orchestrator.run_loop("Recover from error.", session_id="test-session")
        
        # Verify it processed all 3, and the strike counter reset to 0
        self.assertEqual(len(connector.request_history), 3)
        self.assertEqual(orchestrator.format_error_count, 0)

if __name__ == "__main__":
    unittest.main()