import sys
import os
import unittest
import shutil
import tempfile
import json
from unittest.mock import patch, MagicMock

# --- 1. CIRCULAR IMPORT BYPASS ---
mock_func = MagicMock()
sys.modules["functions"] = mock_func
sys.modules["ai.functions"] = mock_func

from ai.tools.agent_tools import (
    write_file, read_file, read_dir, 
    patch_file, smart_search, execute_command, 
    _resolve_path, AVAILABLE_TOOLS
)

class TestAgentToolsExtensive(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.sandbox_dir = os.path.abspath(tempfile.mkdtemp())
        import ai.tools.agent_tools as tools_module
        cls.original_root = tools_module.PROJECT_ROOT
        tools_module.PROJECT_ROOT = cls.sandbox_dir

    @classmethod
    def tearDownClass(cls):
        import ai.tools.agent_tools as tools_module
        tools_module.PROJECT_ROOT = cls.original_root
        shutil.rmtree(cls.sandbox_dir)

    def log_scenario(self, title, objective):
        print(f"\n{'='*60}")
        print(f"🎯 TEST: {title}")
        print(f"📖 OBJ:  {objective}")
        print(f"{'-'*60}")

    def log_result(self, tool_name, params, response):
        print(f"🛠️  TOOL:   {tool_name}")
        print(f"📥 INPUT:  {params}")
        print(f"📤 OUTPUT: {json.dumps(response, indent=2)}")

    # =================================================================
    # 🟢 HAPPY PATH TESTS (From Previous Run)
    # =================================================================

    def test_01_path_resolution_variations(self):
        self.log_scenario("Path Resolution", "Verify @ROOT, relative, and messy path normalization.")
        scenarios = [
            {"path": "@ROOT/src/main.py", "desc": "Explicit @ROOT"},
            {"path": "agents/tools.py", "desc": "Implicit Relative"},
            {"path": "ai//core///logic.py", "desc": "Dirty Slashes"},
        ]
        for s in scenarios:
            resolved = _resolve_path(s)
            self.assertTrue(resolved.startswith(self.sandbox_dir))

    def test_02_security_jailbreak_attempts(self):
        self.log_scenario("Security Jailbreak", "Ensure paths outside PROJECT_ROOT are strictly blocked.")
        with self.assertRaises(PermissionError):
            _resolve_path({"path": "../../etc/passwd"})
            _resolve_path({"path": "/home/passwd"})

    def test_03_filesystem_lifecycle(self):
        self.log_scenario("Filesystem Lifecycle", "Test deep directory creation and file I/O.")
        path = "deep/folder/structure/test.txt"
        res_w = write_file(path=path, content="JARVIS Logic v1")
        self.assertEqual(res_w["status"], "SUCCESS")
        
        res_d = read_dir(path="deep/folder")
        self.assertEqual(res_d["status"], "SUCCESS")
        self.assertIn("structure", res_d["results"]["@ROOT/deep/folder"]["folders"])

    def test_04_search_and_truncation(self):
        self.log_scenario("Search & Recon", "Test regex filename matching and content grep.")
        write_file(path="logs/error.log", content="CRITICAL: DB Down")
        res_f = smart_search(pattern=r"error.*log")
        self.assertTrue(len(res_f["matched_filenames"]) > 0)

    def test_05_patching_precision(self):
        self.log_scenario("Surgical Patching", "Test exact string replacement in code files.")
        file_path = "logic.py"
        write_file(path=file_path, content="def old_func():\n    pass")
        res_p = patch_file(path=file_path, search="old_func", replace="new_func")
        self.assertEqual(res_p["status"], "SUCCESS")

    @patch('subprocess.run')
    def test_06_execute_command_logic(self, mock_run):
        self.log_scenario("Command Interpolation", "Ensure @ROOT is swapped for real paths in shell commands.")
        mock_run.return_value = MagicMock(returncode=0, stdout="success", stderr="")
        execute_command(command="ls @ROOT/src")
        args, _ = mock_run.call_args
        self.assertNotIn("@ROOT", args[0])

    def test_07_command_timeout(self):
        self.log_scenario("Execution Safety", "Ensure long-running processes are killed by timeout.")
        res = execute_command(command="sleep 2", timeout=1)
        self.assertEqual(res["status"], "FAILED")

    # =================================================================
    # 🔴 SAD PATH TESTS (Edge Cases & Hallucinations)
    # =================================================================

    def test_08_sad_file_ops(self):
        self.log_scenario("Sad Path: File Ops", "Agent tries to read missing files or bad paths.")
        
        # Read missing file
        res_miss = read_file(path="does_not_exist.txt")
        self.log_result("read_file", "does_not_exist.txt", res_miss)
        self.assertEqual(res_miss["status"], "FAILED")
        
        # Read a directory as a file
        os.makedirs(os.path.join(self.sandbox_dir, "empty_dir"), exist_ok=True)
        res_dir = read_file(path="empty_dir")
        self.log_result("read_file", "empty_dir", res_dir)
        self.assertEqual(res_dir["status"], "FAILED")
        
        # List missing directory
        res_ldir = read_dir(path="ghost_folder")
        self.log_result("read_dir", "ghost_folder", res_ldir)
        self.assertEqual(res_ldir["status"], "FAILED")

    def test_09_sad_patching(self):
        self.log_scenario("Sad Path: Patching", "Agent sends missing or invalid patch parameters.")
        
        # Patch missing file
        res_miss = patch_file(path="missing.py", search="a", replace="b")
        self.log_result("patch_file", "missing.py", res_miss)
        self.assertEqual(res_miss["status"], "FAILED")
        
        # Missing 'replace' parameter
        res_param = patch_file(path="logic.py", search="old_func")
        self.log_result("patch_file", "Missing replace param", res_param)
        self.assertEqual(res_param["status"], "FAILED")

    def test_10_sad_search(self):
        self.log_scenario("Sad Path: Search", "Agent hallucinates bad regex or forgets the pattern.")
        
        # Malformed Regex (Python's re engine should catch this and fallback to literal)
        res_reg = smart_search(pattern="[unclosed_bracket")
        self.log_result("smart_search", "[unclosed_bracket", res_reg)
        # It shouldn't crash. It might return SUCCESS with 0 matches or FAILED gracefully.
        self.assertIn(res_reg["status"], ["SUCCESS", "FAILED"])
        
        # Missing pattern completely
        res_miss = smart_search(path="@ROOT/src")
        self.log_result("smart_search", "No pattern param", res_miss)
        self.assertEqual(res_miss["status"], "FAILED")

    def test_11_sad_execution(self):
        self.log_scenario("Sad Path: Execution", "Agent runs failing commands or empty commands.")
        
        # Intentional failing command to capture stderr
        res_fail = execute_command(command="ls /directory_that_does_not_exist_999")
        self.log_result("execute_command", "ls bad_dir", res_fail)
        self.assertEqual(res_fail["status"], "FAILED")
        self.assertNotEqual(res_fail["stderr"].strip(), "") # Make sure error is captured
        
        # Empty command
        res_empty = execute_command(command="")
        self.log_result("execute_command", "Empty command", res_empty)
        self.assertEqual(res_empty["status"], "FAILED")

if __name__ == "__main__":
    unittest.main()