import os
import argparse
from unittest.mock import MagicMock, patch

# Imports adjusted for PYTHONPATH=src
from services.config_helper import CliConfig
from config import ProgramSetting

# Mock ProgramConfig to avoid dependency issues during testing
class MockProgramConfig:
    def __init__(self):
        # Start with a baseline default config
        self.config = {
            ProgramSetting.SYSTEM_PROMPT_FILE: "/default/path/prompt.md",
            ProgramSetting.PRINT_LOG: True,
            ProgramSetting.PRINT_DEBUG: False,
            ProgramSetting.PRINT_OUTPUT: True,
        }

    def get(self, setting, default=None):
        return self.config.get(setting, default)

    def set(self, setting, value):
        self.config[setting] = value

@patch('ai.services.config_helper.func')
class TestCliConfig:

    def setup_method(self):
        """
        Set up a fresh MockProgramConfig and mock args for each test.
        """
        self.config = MockProgramConfig()
        self.args = argparse.Namespace()

    def test_apply_cli_args_no_args(self, mock_func):
        """Test that nothing happens when args is None."""
        original_config = self.config.config.copy()
        CliConfig.apply_cli_args_to_config(self.config, None)
        # Assert that no config settings were changed
        assert self.config.config == original_config
        mock_func.debug.assert_not_called()

    
    @patch('os.path.exists', return_value=False)
    def test_apply_system_prompt_override_not_found(self, mock_exists, mock_func):
        """Test overriding the system prompt with a non-existent file from --system."""
        self.args.model = None
        self.args.system = "non_existent_prompt"
        self.args.system_file = None
        self.args.print_log = None
        self.args.print_debug = None
        self.args.no_out = None

        original_prompt_file = self.config.get(ProgramSetting.SYSTEM_PROMPT_FILE)

        with patch('ai.services.config_helper.func.get_root_directory', return_value='/fake/root'):
            self.config.set(ProgramSetting.PATHS_SYSTEM_TEMPLATES, '/fake/root/system')
            expected_path = '/fake/root/system/non_existent_prompt.md'

            CliConfig.apply_cli_args_to_config(self.config, self.args)

            # Config should not be changed
            assert self.config.get(ProgramSetting.SYSTEM_PROMPT_FILE) == original_prompt_file
            mock_exists.assert_called_with(expected_path)
            mock_func.log.assert_called_with(f"System prompt file '{expected_path}' for '--system non_existent_prompt' not found. Ignoring CLI override.", level="WARNING")


    @patch('os.path.exists', return_value=False)
    def test_apply_system_file_override_not_found(self, mock_exists, mock_func):
        """Test overriding with a non-existent file from --system-file."""
        self.args.model = None
        self.args.system = None
        self.args.system_file = "/non/existent/path.md"
        self.args.print_log = None
        self.args.print_debug = None
        self.args.no_out = None

        original_prompt_file = self.config.get(ProgramSetting.SYSTEM_PROMPT_FILE)

        CliConfig.apply_cli_args_to_config(self.config, self.args)

        assert self.config.get(ProgramSetting.SYSTEM_PROMPT_FILE) == original_prompt_file
        mock_exists.assert_called_with(self.args.system_file)
        mock_func.log.assert_called_with(f"System prompt file '{self.args.system_file}' for '--system-file' not found. Ignoring CLI override.", level="WARNING")

   