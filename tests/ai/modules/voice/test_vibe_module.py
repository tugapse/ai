import unittest
from unittest.mock import patch, Mock, MagicMock, call
import os
import sys

# Add the source directory to the Python path for testing
# This is a common pattern when tests are in a separate top-level directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../src')))

# To solve `isinstance(obj, torch.Tensor)` failing in tests, we must ensure
# `torch.Tensor` is a real type. We do this by importing the real one,
# then attaching it to our mock object before placing it in sys.modules.
# This must be done before the module under test is imported.

# First, we import the real Tensor class. This temporarily loads the real torch.
try:
    from torch import Tensor
except ImportError:
    # If torch is not installed, create a dummy class to allow isinstance checks.
    class Tensor:
        pass

# Now, create a fresh mock for the entire torch module.
mock_torch = MagicMock()
mock_torch.cuda.is_available.return_value = False
mock_torch.float16 = "torch.float16"
mock_torch.float32 = "torch.float32"
mock_torch.Tensor = Tensor  # Attach the real/dummy Tensor type to the mock.

# Finally, overwrite sys.modules['torch'] with our configured mock.
# Any subsequent `import torch` will receive this mock.
sys.modules['torch'] = mock_torch

mock_numpy = MagicMock()
sys.modules['numpy'] = mock_numpy

from modules.voice.vibe_module import VibeVoiceModule

class TestVibeVoiceModule(unittest.TestCase):

    def setUp(self):
        """Set up a fresh module instance and mocks before each test."""
        
        # Patch external dependencies for VibeVoiceModule
        self.patchers = {
            'func': patch('ai.modules.voice.vibe_module.func'),
            'os_path_exists': patch('os.path.exists'),
            'os_listdir': patch('os.listdir'),
            'torch_load': patch('torch.load'),
            'VibeProcessor': patch('vibevoice.VibeVoiceStreamingProcessor', create=True),
            'VibeModel': patch('vibevoice.VibeVoiceStreamingForConditionalGenerationInference', create=True),
        }
        
        # Since vibevoice is imported dynamically, we need to ensure it exists in sys.modules for the patchers to work
        sys.modules['vibevoice'] = MagicMock()
        
        self.mocks = {name: patcher.start() for name, patcher in self.patchers.items()}

        # Default mock behaviors
        self.mocks['os_path_exists'].return_value = True
        self.mocks['torch_load'].return_value = {"embedding": Mock()}

        # Instantiate the module under test
        self.module = VibeVoiceModule(voice_file="test_voice.pt")

    def tearDown(self):
        """Stop all patchers after each test."""
        for patcher in self.patchers.values():
            patcher.stop()
        # Reset global mocks between tests
        mock_torch.reset_mock()
        mock_numpy.reset_mock()

    def test_initial_state(self):
        """Test that the module initializes with correct default values and null runtime state."""
        self.assertEqual(self.module.model_id, "microsoft/VibeVoice-Realtime-0.5B")
        self.assertEqual(self.module.voice_file, "test_voice.pt")
        self.assertIsNone(self.module.model)
        self.assertIsNone(self.module.processor)
        self.assertIsNone(self.module.voice_embeddings)
        self.assertIsNone(self.module.device)
        self.assertIsNone(self.module.model_dtype)

    def test_preload_triggers_initialization(self):
        """Test that preload() calls the internal _initialize_model method."""
        with patch.object(self.module, '_initialize_model') as mock_init:
            self.module.preload()
            mock_init.assert_called_once()
        self.mocks['func'].log.assert_called_with("VibeVoice: Preloading model components...")

    def test_initialize_model_on_cpu(self):
        """Test model initialization path when CUDA is not available."""
        mock_torch.cuda.is_available.return_value = False
        
        self.module._initialize_model()

        self.assertEqual(self.module.device, "cpu")
        self.assertEqual(self.module.model_dtype, "torch.float32")
        self.mocks['func'].log.assert_any_call("VibeVoice: Initializing on CPU (torch.float32)")
        
        # Verify components are loaded
        self.mocks['VibeProcessor'].from_pretrained.assert_called_once_with(self.module.model_id)
        self.mocks['VibeModel'].from_pretrained.assert_called_once()
        self.assertIsNotNone(self.module.model)
        self.assertIsNotNone(self.module.processor)

    def test_initialize_model_on_cuda(self):
        """Test model initialization path when CUDA is available."""
        mock_torch.cuda.is_available.return_value = True

        self.module._initialize_model()

        self.assertEqual(self.module.device, "cuda")
        self.assertEqual(self.module.model_dtype, "torch.float16")
        self.mocks['func'].log.assert_any_call("VibeVoice: Initializing on CUDA (torch.float16)")
        self.mocks['VibeModel'].from_pretrained.assert_called_once()

    def test_voice_file_discovery_and_load(self):
        """Test that it finds and loads a voice file."""
        # This test now relies on the default os.path.exists mock behavior (return_value=True)
        # from setUp(), which is more robust than a brittle side_effect iterator.
        
        self.module._initialize_model()
        
        # Check that it tried to find the voices dir and then the specific file
        self.mocks['os_path_exists'].assert_any_call(unittest.mock.ANY)
        self.mocks['torch_load'].assert_called_once()
        self.assertIsNotNone(self.module.voice_embeddings)
        self.mocks['func'].log.assert_any_call("VibeVoice: Loading voice profile: test_voice.pt")

    def test_voice_file_fallback(self):
        """Test that it falls back to another voice file if the preferred one is not found."""
        # Rig the mock to say the preferred file doesn't exist, but others do.
        # This correctly triggers the fallback logic in the module.
        self.mocks['os_path_exists'].side_effect = lambda p: "test_voice.pt" not in p
        self.mocks['os_listdir'].return_value = ['fallback.pt', 'another.wav']
        
        self.module._initialize_model()
        
        self.mocks['torch_load'].assert_called_once()
        # Check that the path passed to torch.load is the fallback one
        self.assertIn('fallback.pt', self.mocks['torch_load'].call_args[0][0])
        self.mocks['func'].log.assert_any_call("VibeVoice: Loading voice profile: fallback.pt")

    def test_no_voice_directory_found(self):
        """Test that it handles the case where the 'voices' directory cannot be found."""
        self.mocks['os_path_exists'].return_value = False
        
        self.module._initialize_model()
        
        self.mocks['func'].log.assert_any_call("VibeVoice: WARNING - Could not locate 'voices' directory.", level="WARN")
        self.mocks['torch_load'].assert_not_called()
        self.assertIsNone(self.module.voice_embeddings)

    def test_run_inference_no_model(self):
        """Test that inference returns an empty array if the model is not loaded."""
        result = self.module._run_inference("test")
        
        mock_numpy.zeros.assert_called_once_with(1, dtype=mock_numpy.float32)
        self.assertEqual(result, mock_numpy.zeros.return_value)

    def test_run_inference_empty_text(self):
        """Test that inference returns an empty array for blank input text."""
        self.module.model = Mock() # Pretend model is loaded
        
        result = self.module._run_inference("   ")
        
        mock_numpy.zeros.assert_called_once_with(1, dtype=mock_numpy.float32)
        self.assertEqual(result, mock_numpy.zeros.return_value)

    def test_run_inference_success(self):
        """Test a successful inference run."""
        # Setup a fully initialized module state
        self.module._initialize_model()
        # This test case follows the `len > 1` is `False` path, so `audio_tensor`
        # becomes `output.speech_outputs[0]`. We must configure the mock *inside*
        # that list to behave like a tensor.
        mock_audio_tensor = Mock()
        mock_audio_tensor.cpu.return_value.numpy.return_value.squeeze.return_value.astype.return_value = mock_numpy.zeros(100)
        self.module.model.generate.return_value = MagicMock(speech_outputs=[mock_audio_tensor])

        # Prevent RecursionError by giving _recursive_cast a real dict to traverse
        self.module.processor.process_input_with_cached_prompt.return_value = {
            "input_ids": Mock(), "attention_mask": Mock()
        }

        text_input = "Hello world"
        self.module._run_inference(text_input)

        # Verify processor is used
        self.module.processor.process_input_with_cached_prompt.assert_called_once_with(
            text=text_input,
            cached_prompt=unittest.mock.ANY,
            padding=True,
            return_tensors="pt"
        )
        
        # Verify model generate is called
        self.module.model.generate.assert_called_once()
        
        # Verify that torch.cat was NOT called, as we are testing the single-tensor path
        self.assertFalse(mock_torch.cat.called)

        # We can also verify that the mock tensor we created was used as expected.
        # This confirms the audio data processing chain was called on the correct object.
        mock_audio_tensor.cpu.return_value.numpy.return_value.squeeze.return_value.astype.assert_called_once_with(mock_numpy.float32)


if __name__ == '__main__':
    unittest.main()