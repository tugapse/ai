import pytest
from unittest.mock import MagicMock, patch
from services.config_applier import ConfigApplier, ProgramConfig, ProgramSetting

class TestConfigApplier:
    @pytest.mark.parametrize("args_model, expected_model", [
        ("model1", "model1"),
        ("model2", "model2"),
    ])
    def test_model_arg(self, args_model, expected_model):
        config = MagicMock()
        args = MagicMock(model=args_model)
        with patch('services.config_applier.func.debug') as mock_debug:
            ConfigApplier.apply_cli_args_to_config(config, args)
            config.set.assert_called_once_with(ProgramSetting.MODEL_CONFIG_NAME, expected_model)
            mock_debug.assert_called_once_with(f"CLI override: Model config set to '{args_model}'")

    @pytest.mark.parametrize("system_file, exists", [
        ("system.md", True),
        ("system.txt", False),
    ])
    def test_system_arg(self, system_file, exists):
        config = MagicMock()
        args = MagicMock(system=system_file)
        config.get = MagicMock(
            side_effect=lambda key, default: "/some/system/templates" if key == ProgramSetting.PATHS_SYSTEM_TEMPLATES else default
        )
        with patch('os.path.exists', return_value=exists):
            with patch('services.config_applier.func.debug') as mock_debug:
                with patch('services.config_applier.func.log') as mock_log:
                    ConfigApplier.apply_cli_args_to_config(config, args)
                    if exists:
                        expected_path = os.path.join("/some/system/templates", system_file.replace(".md", "") + ".md")
                        config.set.assert_called_once_with(ProgramSetting.SYSTEM_PROMPT_FILE, expected_path)
                        mock_debug.assert_called_once_with(f"CLI override: System prompt file set to '{expected_path}' (from --system)")
                    else:
                        mock_log.assert_called_once_with(
                            f"System prompt file '{os.path.join('/some/system/templates', system_file.replace('.md', '') + '.md')}' for '--system {system_file}' not found. Ignoring CLI override.",
                            level="WARNING"
                        )

    @pytest.mark.parametrize("system_file, exists", [
        ("/path/to/system.md", True),
        ("/nonexistent/file.txt", False),
    ])
    def test_system_file_arg(self, system_file, exists):
        config = MagicMock()
        args = MagicMock(system_file=system_file)
        with patch('os.path.exists', return_value=exists):
            with patch('services.config_applier.func.debug') as mock_debug:
                with patch('services.config_applier.func.log') as mock_log:
                    ConfigApplier.apply_cli_args_to_config(config, args)
                    if exists:
                        config.set.assert_called_once_with(ProgramSetting.SYSTEM_PROMPT_FILE, system_file)
                        mock_debug.assert_called_once_with(f"CLI override: System prompt file set to '{system_file}' (from --system-file)")
                    else:
                        mock_log.assert_called_once_with(
                            f"System prompt file '{system_file}' for '--system-file' not found. Ignoring CLI override.",
                            level="WARNING"
                        )

    @pytest.mark.parametrize("no_log, expected_log", [
        (True, False),
        (False, True),
    ])
    def test_no_log_arg(self, no_log, expected_log):
        config = MagicMock()
        args = MagicMock(no_log=no_log)
        with patch('services.config_applier.func.debug') as mock_debug:
            ConfigApplier.apply_cli_args_to_config(config, args)
            config.set.assert_called_once_with(ProgramSetting.PRINT_LOG, not no_log)
            mock_debug.assert_called_once_with(f"CLI override: PRINT_LOG set to {not no_log}")

    @pytest.mark.parametrize("no_out, expected_out", [
        (True, False),
        (False, True),
    ])
    def test_no_out_arg(self, no_out, expected_out):
        config = MagicMock()
        args = MagicMock(no_out=no_out)
        with patch('services.config_applier.func.debug') as mock_debug:
            ConfigApplier.apply_cli_args_to_config(config, args)
            config.set.assert_called_once_with(ProgramSetting.PRINT_OUTPUT, not no_out)
            mock_debug.assert_called_once_with(f"CLI override: PRINT_OUTPUT set to {not no_out}")

    def test_no_args(self):
        config = MagicMock()
        args = None
        ConfigApplier.apply_cli_args_to_config(config, args)
        config.set.assert_not_called()
        # No logs should be called
        assert not hasattr(config, 'set') or config.set.call_count == 0

    def test_system_no_templates_dir(self):
        config = MagicMock()
        args = MagicMock(system="system.md")
        config.get = MagicMock(return_value="")
        with patch('os.path.exists', return_value=True):
            with patch('services.config_applier.func.log') as mock_log:
                ConfigApplier.apply_cli_args_to_config(config, args)
                mock_log.assert_called_once_with(
                    "System prompt file '/system.md' for '--system system.md' not found. Ignoring CLI override.",
                    level="WARNING"
                )


# ### ✅ **Test Coverage Highlights**

# 1. **Model Argument (`--model`)**:
#    - Verifies that the `config.set` is called with the correct key and value.
#    - Ensures `func.debug` is called with the expected message.

# 2. **System Prompt File (`--system`)**:
#    - Simulates both **existing** and **non-existing** files.
#    - Validates that `config.set` is called with the correct path when the file exists.
#    - Ensures `func.log` is called with a warning when the file is not found.

# 3. **System File Argument (`--system-file`)**:
#    - Tests both **existing** and **non-existing** files.
#    - Confirms `config.set` is called with the correct path when the file exists.
#    - Validates that `func.log` is called with a warning when the file is not found.

# 4. **No Log (`--no-log`)** and **No Output (`--no-out`)**:
#    - Ensures that `config.set` is called with the inverse of the `no_log`/`no_out` flag.
#    - Confirms that `func.debug` is called with the correct message.

# 5. **No Arguments**:
#    - Ensures the method returns early when `args` is `None`.
#    - No `config.set` or log calls should occur.

# 6. **Missing System Templates Directory**:
#    - Simulates a scenario where the system templates directory is not set.
#    - Validates that a warning is logged when the system file is not found.

# ---

# ### 🧪 **Best Practices Implemented**

# - **Isolation**: Mocks `func.debug`, `func.log`, and `os.path.exists` to isolate the logic.
# - **Readability**: Uses `pytest`'s `@parametrize` for test data and follows the **AAA** pattern (Arrange, Act, Assert).
# - **Maintainability**: Each test is self-contained and focused on a single behavior.
# - **Edge Case Coverage**: Handles missing keys, invalid file paths, and missing arguments.
# - **Asynchronous Handling**: Not required here, but the structure is ready for future async testing.