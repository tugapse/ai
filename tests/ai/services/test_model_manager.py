import json
import os
import pytest
import sys
from unittest.mock import MagicMock, patch, mock_open, ANY

# Imports adjusted for PYTHONPATH=src
from ai.services.engine_manager import EngineManager
from ai.entities.model_enums import ModelType, EngineType
from ai.core.llms.base_llm import ModelParams

# Mock the 'functions' module
func = MagicMock()

class TestEngineManager:

    def setup_method(self):
        """Reset mocks before each test to ensure isolation."""
        func.reset_mock()

    def test_generate_default_config(self):
        """Test generating a default config for a standard model."""
        model_name = "test-model"
        model_type = ModelType.CAUSAL_LM
        config = EngineManager.generate_default_config(model_name, model_type)

        assert config["model_name"] == model_name
        assert config["model_type"] == model_type.value
        assert "model_properties" in config
        assert config["model_properties"]["max_new_tokens"] == 1024


    @patch('ai.services.engine_manager.func', func)
    def test_save_and_load_config(self, tmpdir):
        """Test saving a config and loading it back."""
        config = {"model_name": "test", "model_type": "causal_lm"}
        filepath = os.path.join(str(tmpdir), "model.json")

        EngineManager.save_config(config, filepath)
        func.log.assert_called_with(f"Saved model config to {filepath}")

        loaded_config = EngineManager.load_config(filepath)
        func.log.assert_called_with(f"Loaded model config from {filepath}")
        
        assert loaded_config == config

    @patch('ai.services.engine_manager.func', func)
    def test_load_config_not_found(self):
        """Test loading a non-existent config file."""
        with pytest.raises(FileNotFoundError):
            EngineManager.load_config("non_existent_file.json")
        func.error.assert_called_with("Model configuration file 'non_existent_file.json' not found.", level="ERROR")

    @patch('ai.services.engine_manager.func', func)
    def test_load_config_invalid_json(self, tmpdir):
        """Test loading a file with invalid JSON."""
        filepath = os.path.join(str(tmpdir), "invalid.json")
        with open(filepath, 'w') as f:
            f.write("{'invalid': 'json',}")

        with pytest.raises(json.JSONDecodeError):
            EngineManager.load_config(filepath)
        func.error.assert_called_with(ANY, level="ERROR")

    @patch('os.path.exists', return_value=True)
    def test_is_engine_installed_true(self, mock_exists):
        """Test when the engine is marked as installed in the config."""
        mock_config = json.dumps({"transformers": {"installed": True}})
        with patch('builtins.open', mock_open(read_data=mock_config)):
            assert EngineManager.is_engine_installed(ModelType.CAUSAL_LM) is True

    @patch('os.path.exists', return_value=False)
    def test_is_engine_installed_no_config_file(self, mock_exists):
        """Test when installed_engines.json does not exist."""
        assert EngineManager.is_engine_installed(ModelType.OLLAMA) is False

    def test_is_engine_installed_frozen_uses_project_status_file(self, tmp_path, monkeypatch):
        """Test frozen builds read engine status beside the executable's project."""
        project_root = tmp_path / "project"
        executable_dir = project_root / "dist"
        bundle_dir = tmp_path / "bundle"
        executable_dir.mkdir(parents=True)
        bundle_dir.mkdir()
        (project_root / "installed_engines.json").write_text(
            '{"gguf": {"installed": true}}',
            encoding="utf-8",
        )
        (bundle_dir / "installed_engines.json").write_text(
            '{"gguf": {"installed": false}}',
            encoding="utf-8",
        )

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)
        monkeypatch.setattr(sys, "executable", str(executable_dir / "ai.exe"))

        assert EngineManager.is_engine_installed(ModelType.GGUF) is True

    def test_is_engine_installed_frozen_uses_bundled_status_fallback(self, tmp_path, monkeypatch):
        """Test frozen builds fall back to their bundled engine status."""
        executable_dir = tmp_path / "dist"
        bundle_dir = tmp_path / "bundle"
        executable_dir.mkdir()
        bundle_dir.mkdir()
        (bundle_dir / "installed_engines.json").write_text(
            '{"gguf": {"installed": true}}',
            encoding="utf-8",
        )

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)
        monkeypatch.setattr(sys, "executable", str(executable_dir / "ai.exe"))

        assert EngineManager.is_engine_installed(ModelType.GGUF) is True

    @patch('os.path.exists', return_value=True)
    def test_is_engine_installed_gemini_vertex(self, mock_exists):
        """Test special logic for Gemini Vertex AI."""
        mock_config = json.dumps({"gemini_vertex": {"installed": True}})
        with patch('builtins.open', mock_open(read_data=mock_config)):
            assert EngineManager.is_engine_installed(ModelType.GEMINI, "model-name-vertex") is True



    def test_load_model_instance_missing_config_keys(self):
        """Test ValueError when model_name or model_type are missing."""
        with pytest.raises(ValueError, match="missing 'model_name' or 'model_type'"):
            EngineManager.load_model_instance({"model_name": "test"}, "prompt", None)
        
        with pytest.raises(ValueError, match="missing 'model_name' or 'model_type'"):
            EngineManager.load_model_instance({"model_type": "ollama"}, "prompt", None)

    @patch.object(EngineManager, "is_engine_installed", return_value=False)
    def test_load_model_instance_engine_not_installed(self, _mock_is_engine_installed):
        """Test the missing-engine path reports the expected error."""
        with pytest.raises(ValueError, match="engine not installed"):
            EngineManager.load_model_instance(
                {"model_name": "test", "model_type": "ollama"},
                "prompt",
                None,
            )
