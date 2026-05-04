import pytest
import os
from unittest.mock import MagicMock, patch, call

# Adjust imports for PYTHONPATH=src
from ai.services.prompt_loader import PromptLoader, DEFAULT_SYSTEM_PROMPT
from ai.services.config_helper import ProgramSetting

# Since ProgramConfig is a dependency, we can create a mock version of it for tests.
class MockProgramConfig:
    def __init__(self, settings=None):
        self._settings = settings or {}

    def get(self, setting, default=None):
        return self._settings.get(setting, default)

    def set(self, setting, value):
        self._settings[setting] = value

class TestPromptLoader:

    def setup_method(self):
        """Set up mocks for each test."""
        self.patcher_os_path = patch('ai.services.prompt_loader.os.path')
        self.patcher_func = patch('ai.services.prompt_loader.func')
        self.patcher_template_injection = patch('ai.services.prompt_loader.TemplateInjection')
        self.patcher_pathlib = patch('ai.services.prompt_loader.Path')

        self.mock_os_path = self.patcher_os_path.start()
        self.mock_func = self.patcher_func.start()
        self.mock_template_injection_class = self.patcher_template_injection.start()
        self.mock_pathlib = self.patcher_pathlib.start()

        # Mock the TemplateInjection class to return a mock instance
        self.mock_template_instance = MagicMock()
        self.mock_template_injection_class.return_value = self.mock_template_instance
        # Default behavior: replace_system_template returns the original content
        self.mock_template_instance.replace_system_template.side_effect = lambda: self.mock_template_instance.content
        
        # Make the constructor store the content
        def store_content(content):
            self.mock_template_instance.content = content
            return self.mock_template_instance
        self.mock_template_injection_class.side_effect = store_content


    def teardown_method(self):
        """Clean up patches after each test."""
        self.patcher_os_path.stop()
        self.patcher_func.stop()
        self.patcher_template_injection.stop()
        self.patcher_pathlib.stop()

    def test_load_from_explicit_path(self):
        """
        Tests loading a system prompt from an explicit, absolute file path.
        """
        # Arrange
        config = MockProgramConfig()
        explicit_path = "/path/to/my/prompt.md"
        prompt_content = "This is the prompt from an explicit path."
        
        self.mock_os_path.exists.return_value = True
        self.mock_func.read_file.return_value = prompt_content

        # Act
        result = PromptLoader.load_system_prompt(config, explicit_path)

        # Assert
        self.mock_os_path.exists.assert_called_once_with(explicit_path)
        self.mock_func.log.assert_any_call(f"Loaded system file from explicit path: {explicit_path}")
        self.mock_func.read_file.assert_called_once_with(explicit_path)
        self.mock_template_injection_class.assert_called_once_with(prompt_content)
        self.mock_template_instance.replace_system_template.assert_called_once()
        assert result == prompt_content

    def test_load_from_configured_template_dir(self):
        """
        Tests loading a prompt from a filename when the templates dir is configured.
        """
        # Arrange
        template_dir = "/path/to/templates"
        template_name = "my_template"
        prompt_content = "This is from the template dir."
        
        config = MockProgramConfig(settings={
            ProgramSetting.PATHS_SYSTEM_TEMPLATES: template_dir
        })
        
        # First exists check is for the explicit path, which fails.
        # Second is for the path constructed from the template dir.
        self.mock_os_path.exists.side_effect = [False, True]
        self.mock_func.read_file.return_value = prompt_content

        # Act
        result = PromptLoader.load_system_prompt(config, template_name)

        # Assert
        expected_path = os.path.join(template_dir, f"{template_name}.md")
        self.mock_os_path.exists.assert_has_calls([
            call(template_name),
            call(expected_path)
        ])
        self.mock_func.log.assert_any_call(f"Loaded system file from templates directory: {expected_path}")
        self.mock_func.read_file.assert_called_once_with(expected_path)
        self.mock_template_injection_class.assert_called_once_with(prompt_content)
        self.mock_template_instance.replace_system_template.assert_called_once()
        assert result == prompt_content

    def test_load_from_default_template_dir(self):
        """
        Tests loading from the default templates dir when none is configured.
        """
        # Arrange
        root_dir = "/app"
        template_name = "my_template"
        prompt_content = "This is from the default template dir."
        
        config = MockProgramConfig() # No template dir configured
        
        self.mock_func.get_root_directory.return_value = root_dir
        # First exists check is for the explicit path, which fails.
        # Second is for the path constructed from the default template dir.
        self.mock_os_path.exists.side_effect = [False, True]
        self.mock_func.read_file.return_value = prompt_content

        # Act
        result = PromptLoader.load_system_prompt(config, template_name)

        # Assert
        expected_path = os.path.join(root_dir, "system", f"{template_name}.md")
        self.mock_os_path.exists.assert_has_calls([
            call(template_name),
            call(expected_path)
        ])
        self.mock_func.debug.assert_any_call(f"PromptLoader: defaulting system templates dir to {os.path.join(root_dir, 'system')}")
        self.mock_func.log.assert_any_call(f"Loaded system file from templates directory: {expected_path}")
        self.mock_func.read_file.assert_called_once_with(expected_path)
        self.mock_template_injection_class.assert_called_once_with(prompt_content)
        self.mock_template_instance.replace_system_template.assert_called_once()
        assert result == prompt_content

    def test_load_with_default_keyword_fallback(self):
        """
        Tests that using the "default" keyword falls back to the built-in prompt
        when no "default.md" file is found.
        """
        # Arrange
        config = MockProgramConfig()
        self.mock_os_path.exists.return_value = False  # Ensure no file is found

        # Act
        result = PromptLoader.load_system_prompt(config, "default")

        # Assert
        self.mock_os_path.exists.assert_called()  # It should try to find files
        self.mock_func.read_file.assert_not_called()
        self.mock_func.log.assert_any_call(
            "Using built-in fallback system prompt for 'default'.",
            level="WARNING"
        )
        self.mock_template_injection_class.assert_called_once_with(DEFAULT_SYSTEM_PROMPT)
        self.mock_template_instance.replace_system_template.assert_called_once()
        assert result == DEFAULT_SYSTEM_PROMPT

    def test_load_file_not_found_returns_empty(self):
        """
        Tests that the loader returns an empty string if a specified file is not found
        and is not the 'default' keyword.
        """
        # Arrange
        template_name = "non_existent_template"
        config = MockProgramConfig()

        # All os.path.exists checks will fail
        self.mock_os_path.exists.return_value = False

        # Act
        result = PromptLoader.load_system_prompt(config, template_name)

        # Assert
        self.mock_os_path.exists.assert_called()  # It should have at least tried
        self.mock_func.read_file.assert_not_called()

        # It should log two warnings: one for the file not found, one for empty content
        expected_calls = [
            call(
                f"System prompt file '{template_name}' not found at any known location (explicit path or in templates dir).",
                level="WARNING",
            ),
            call(
                "No system prompt loaded or found. Continuing without a system prompt.",
                level="WARNING",
            ),
        ]
        self.mock_func.log.assert_has_calls(expected_calls, any_order=False)

        self.mock_template_injection_class.assert_called_once_with("")
        self.mock_template_instance.replace_system_template.assert_called_once()
        assert result == ""

    # More tests to be added here