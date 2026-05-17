import json
import os
import pytest
from unittest.mock import MagicMock, patch, mock_open, ANY

# Imports adjusted for PYTHONPATH=src
from services.model_orchestrator import EngineManager
from entities.model_enums import ModelType, EngineType
from core.llms.base_llm import ModelParams

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


    @patch('ai.services.model_manager.func', func)
    def test_save_and_load_config(self, tmpdir):
        """Test saving a config and loading it back."""
        config = {"model_name": "test", "model_type": "causal_lm"}
        filepath = os.path.join(str(tmpdir), "model.json")

        EngineManager.save_config(config, filepath)
        func.log.assert_called_with(f"Saved model config to {filepath}")

        loaded_config = EngineManager.load_config(filepath)
        func.log.assert_called_with(f"Loaded model config from {filepath}")
        
        assert loaded_config == config

    @patch('ai.services.model_manager.func', func)
    def test_load_config_not_found(self):
        """Test loading a non-existent config file."""
        with pytest.raises(FileNotFoundError):
            EngineManager.load_config("non_existent_file.json")
        func.error.assert_called_with("Model configuration file 'non_existent_file.json' not found.", level="ERROR")

    @patch('ai.services.model_manager.func', func)
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

    @patch('os.path.exists', return_value=True)
    def test_is_engine_installed_gemini_vertex(self, mock_exists):
        """Test special logic for Gemini Vertex AI."""
        mock_config = json.dumps({"gemini_vertex": {"installed": True}})
        with patch('builtins.open', mock_open(read_data=mock_config)):
            assert EngineManager.is_engine_installed(ModelType.GEMINI, "model-name-vertex") is True



    def test_load_model_instance_missing_config_keys(self):
        """Test ValueError when model_name or model_type are missing."""
        with pytest.raises(ValueError, match="missing 'model_name' or 'model_type'"):
            EngineManager.load_model_instance({"model_name": "test"}, "prompt",None)
        
        with pytest.raises(ValueError, match="missing 'model_name' or 'model_type'"):
            EngineManager.load_model_instance({"model_type": "ollama"}, "prompt",None)

   
    