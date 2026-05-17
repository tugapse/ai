import unittest
from unittest.mock import Mock, patch
import sys
import os

# --- VIRTUAL MODULE PATCH ---
# The module being tested has an incorrect import path in the original tests.
# We create a virtual 'modules' package in sys.modules to redirect the import
# to the correct location at runtime for this test file.

# Ensure the source directory is in the path to find the real module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../src')))

try:
    # 1. Import the actual module we want to test.
    from modules.voice.speech_bridge import SpeechBridge

    # 2. Create a mock for the top-level 'modules' package.
    sys.modules['modules'] = Mock()
    sys.modules['modules.voice'] = Mock()

except ImportError as e:
    raise ImportError(f"Could not import the actual SpeechBridge module for patching: {e}")
# --- END VIRTUAL MODULE PATCH ---


class TestSpeechBridge(unittest.TestCase):

    def setUp(self):
        """Set up a fresh environment before each test."""
        self.mock_voice_module = Mock()
        self.bridge = SpeechBridge(voice_module=self.mock_voice_module)

    def test_initial_state(self):
        """Test that the bridge initializes with a clean state."""
        self.assertEqual(self.bridge.buffer, "")
        self.assertFalse(self.bridge.in_code_block)
        self.assertIsNotNone(self.bridge.voice)

    def test_feed_simple_sentence(self):
        """Test feeding a single, complete sentence."""
        text = "This is a test."
        self.bridge.feed(text)
        self.mock_voice_module.process_token.assert_called_once_with("This is a test.")
        self.assertEqual(self.bridge.buffer, "")

    def test_buffering_incomplete_sentence(self):
        """Test that incomplete sentences are buffered and not sent."""
        text = "This is an incomplete sentence"
        self.bridge.feed(text)
        self.mock_voice_module.process_token.assert_not_called()
        self.assertEqual(self.bridge.buffer, "This is an incomplete sentence")

    def test_completing_a_buffered_sentence(self):
        """Test that a buffered sentence is sent once completed."""
        self.bridge.feed("This is an incomplete sentence")
        self.mock_voice_module.process_token.assert_not_called()
        
        self.bridge.feed(" and now it's complete.")
        self.mock_voice_module.process_token.assert_called_once_with("This is an incomplete sentence and now it's complete.")
        self.assertEqual(self.bridge.buffer, "")

    def test_flush_sends_remaining_buffer(self):
        """Test that flush() sends any content left in the buffer."""
        text = "This is a fragment"
        self.bridge.feed(text)
        self.mock_voice_module.process_token.assert_not_called()
        
        self.bridge.flush()
        self.mock_voice_module.process_token.assert_called_once_with("This is a fragment")
        self.assertEqual(self.bridge.buffer, "")

    @patch('random.choice', return_value="Code is on screen.")
    def test_code_block_handling(self, mock_random_choice):
        """Test the logic for entering and exiting code blocks."""
        text = "Here is some text.```python\nprint('hello')\n```This is after the code."
        
        self.bridge.feed(text)
        
        # 1. The text before the code block should be sent
        self.mock_voice_module.process_token.assert_any_call("Here is some text.")
        
        # 2. The special code announcement should be sent
        self.mock_voice_module.process_token.assert_any_call("Code is on screen.")
        
        # 3. The text after the code block should be sent
        self.mock_voice_module.process_token.assert_any_call("This is after the code.")

        # Verify that the code itself was never sent to voice
        calls = self.mock_voice_module.process_token.call_args_list
        for call in calls:
            self.assertNotIn("python", call.args[0])
            self.assertNotIn("print('hello')", call.args[0])
            
        self.assertEqual(self.mock_voice_module.process_token.call_count, 3)
        self.assertFalse(self.bridge.in_code_block)

    def test_text_is_not_processed_while_in_code_block(self):
        """Ensure that feed() does nothing with text when already in a code block."""
        self.bridge.in_code_block = True
        self.bridge.feed("This text should be ignored.")
        self.mock_voice_module.process_token.assert_not_called()
        self.assertEqual(self.bridge.buffer, "")

    def test_markdown_and_path_cleaning(self):
        """Test removal of markdown and transformation of file paths."""
        text = "### Header\n* Bullet\n**Bold text** `/path/to/file.txt` is the location."
        self.bridge.feed(text)
        
        expected_call = "Header\n Bullet\nBold text , path to file.txt is the location."
        self.mock_voice_module.process_token.assert_called_once_with(expected_call)

    def test_abort_clears_state_and_calls_voice_abort(self):
        """Test that abort() resets the bridge and propagates the call."""
        self.bridge.feed("some buffered text")
        self.bridge.in_code_block = True
        
        self.bridge.abort()
        
        self.assertEqual(self.bridge.buffer, "")
        self.assertFalse(self.bridge.in_code_block)
        self.mock_voice_module.abort.assert_called_once()
        
    def test_no_voice_module(self):
        """Test that the bridge handles having no voice module gracefully."""
        no_voice_bridge = SpeechBridge(voice_module=None)
        
        # These calls should not raise an exception
        no_voice_bridge.feed("test")
        no_voice_bridge.flush()
        no_voice_bridge.abort()
        self.assertTrue(True) # If we got here without an error, the test passes.

if __name__ == '__main__':
    unittest.main()