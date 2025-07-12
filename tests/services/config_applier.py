```python
# tests/test_config_applier.py
import os
import unittest
from unittest.mock import Mock, patch
from config import ProgramConfig, ProgramSetting
from services.config_applier import ConfigApplier

class TestConfigApplier(unittest.TestCase):
    def setUp(self):
        self.config = ProgramConfig()
        self.args = Mock()
        self.args.model = "test-model"
        self.args.system = "test-system"
        self.args.system_file = "test-system-file.md"
        self.args.no_log = True
        self.args.no_out = False

    def test_apply_model_config(self):
        ConfigApplier.apply_cli_args_to_config(self.config, self.args)
        self.assertEqual(self.config.get(ProgramSetting.MODEL_CONFIG_NAME), "test-model")
        self.assertIn("CLI override: Model config set to 'test-model'", func.debug.call_args[0][0])

    def test_apply_system_prompt(self):
        self.args.system = "test-system"
        system_templates_dir = "/test/path/system/templates"
        self.config.set(ProgramSetting.PATHS_SYSTEM_TEMPLATES, system_templates_dir)
        os.path.exists = Mock(return_value=True)
        ConfigApplier.apply_cli_args_to_config(self.config, self.args)
        self.assertEqual(self.config.get(ProgramSetting.SYSTEM_PROMPT_FILE), os.path.join(system_templates_dir, "test-system.md"))
        self.assertIn("CLI override: System prompt file set to '/test/path/system/templates/test-system.md'", func.debug.call_args[0][0])

    def test_system_prompt_file_not_found(self):
        self.args.system = "nonexistent-system"
        system_templates_dir = "/test/path/system/templates"
        self.config.set(ProgramSetting.PATHS_SYSTEM_TEMPLATES, system_templates_dir)
        os.path.exists = Mock(return_value=False)
        ConfigApplier.apply_cli_args_to_config(self.config, self.args)
        self.assertEqual(self.config.get(ProgramSetting.SYSTEM_PROMPT_FILE), None)
        self.assertIn("System prompt file '/test/path/system/templates/nonexistent-system.md' for '--system nonexistent-system' not found. Ignoring CLI override.", func.log.call_args[0][0])

    def test_apply_system_file(self):
        self.args.system_file = "test-system-file.md"
        os.path.exists = Mock(return_value=True)
        ConfigApplier.apply_cli_args_to_config(self.config, self.args)
        self.assertEqual(self.config.get(ProgramSetting.SYSTEM_PROMPT_FILE), "test-system-file.md")
        self.assertIn("CLI override: System prompt file set to 'test-system-file.md' (from --system-file)", func.debug.call_args[0][0])

    def test_system_file_not_found(self):
        self.args.system_file = "nonexistent-file.md"
        os.path.exists = Mock(return_value=False)
        ConfigApplier.apply_cli_args_to_config(self.config, self.args)
        self.assertEqual(self.config.get(ProgramSetting.SYSTEM_PROMPT_FILE), None)
        self.assertIn("System prompt file 'nonexistent-file.md' for '--system-file' not found. Ignoring CLI override.", func.log.call_args[0][0])

    def test_apply_no_log(self):
        self.args.no_log = True
        ConfigApplier.apply_cli_args_to_config(self.config, self.args)
        self.assertEqual(self.config.get(ProgramSetting.PRINT_LOG), False)
        self.assertIn("CLI override: PRINT_LOG set to False", func.debug.call_args[0][0])

    def test_apply_no_out(self):
        self.args.no_out = True
        ConfigApplier.apply_cli_args_to_config(self.config, self.args)
        self.assertEqual(self.config.get(ProgramSetting.PRINT_OUTPUT), False)
        self.assertIn("CLI override: PRINT_OUTPUT set to False", func.debug.call_args[0][0])

    def test_no_args(self):
        ConfigApplier.apply_cli_args_to_config(self.config, None)
        self.assertEqual(self.config.get(ProgramSetting.MODEL_CONFIG_NAME), None)
        self.assertEqual(self.config.get(ProgramSetting.SYSTEM_PROMPT_FILE), None)
        self.assertEqual(self.config.get(ProgramSetting.PRINT_LOG), True)
        self.assertEqual(self.config.get(ProgramSetting.PRINT_OUTPUT), True)

    def test_no_log_and_no_out(self):
        self.args.no_log = True
        self.args.no_out = True
        ConfigApplier.apply_cli_args_to_config(self.config, self.args)
        self.assertEqual(self.config.get(ProgramSetting.PRINT_LOG), False)
        self.assertEqual(self.config.get(ProgramSetting.PRINT_OUTPUT), False)

if __name__ == "__main__":
    unittest.main()
```