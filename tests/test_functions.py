
import unittest
from unittest.mock import patch, MagicMock
import os
import tempfile
from functions import (
    set_console_title, clear_console, beep_console, 
    get_files, read_file, write_to_file, format_execution_time,
    get_root_directory, ensure_directory_exists, log, debug, out
)
from pathlib import Path
import time

class TestFunctions(unittest.TestCase):
    def setUp(self):
        """Set up temporary directory for file operations"""
        self.test_dir = tempfile.TemporaryDirectory()
        self.temp_path = self.test_dir.name
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_path)
    
    def tearDown(self):
        """Clean up after tests"""
        self.test_dir.cleanup()
        os.chdir(self.original_cwd)

    def test_set_console_title(self):
        """Test console title setting for different OS"""
        with patch('os.name', 'nt'):  # Windows
            set_console_title("TestTitle")
            self.assertIn("title TestTitle", " ".join([line for line in self._get_output()]))
        
        with patch('os.name', 'posix'):  # Linux/macOS
            set_console_title("TestTitle")
            self.assertIn("\x1b]2;TestTitle\x07", self._get_output())

    def test_clear_console(self):
        """Test console clearing for different OS"""
        with patch('sys.platform', 'win32'):
            clear_console()
            self.assertIn("cls", " ".join([line for line in self._get_output()]))
        
        with patch('sys.platform', 'linux'):
            clear_console()
            self.assertIn("clear", " ".join([line for line in self._get_output()]))

    def test_beep_console(self):
        """Test console beep functionality"""
        self.assertIn("\007", self._get_output())

    def test_get_files(self):
        """Test file search with different extensions"""
        # Create test files
        test_files = [
            ("test1.txt", "content1"),
            ("test2.py", "content2"),
            ("test3.txt", "content3")
        ]
        
        for filename, content in test_files:
            with open(filename, "w") as f:
                f.write(content)
        
        # Test with no extension
        result = get_files(self.temp_path, extension=None)
        self.assertEqual(len(result), len(test_files))
        
        # Test with .txt extension
        result = get_files(self.temp_path, extension="txt")
        self.assertEqual(len(result), 2)
        
        # Test non-existing directory
        with self.assertRaises(SystemExit):
            get_files("nonexistent_dir", extension="txt")

    def test_read_file(self):
        """Test file reading with error handling"""
        # Create test file
        with open("test.txt", "w") as f:
            f.write("test content")
        
        # Test successful read
        content = read_file("test.txt")
        self.assertEqual(content, "test content")
        
        # Test non-existing file
        with self.assertRaises(SystemExit):
            read_file("nonexistent.txt")

    def test_write_to_file(self):
        """Test file writing with different modes"""
        # Test write mode
        write_to_file("test.txt", "test content")
        with open("test.txt", "r") as f:
            self.assertEqual(f.read(), "test content")
        
        # Test append mode
        write_to_file("test.txt", " additional", filemode="a")
        with open("test.txt", "r") as f:
            self.assertEqual(f.read(), "test content additional")
        
        # Test error handling
        with patch('builtins.open', side_effect=OSError("Permission denied")):
            with self.assertRaises(SystemExit):
                write_to_file("test.txt", "content")

    def test_format_execution_time(self):
        """Test time formatting function"""
        self.assertEqual(format_execution_time(0, 3661), "01:01:01")
        self.assertEqual(format_execution_time(0, 3600), "01:00:00")
        self.assertEqual(format_execution_time(0, 60), "00:01:00")

    def test_get_root_directory(self):
        """Test root directory retrieval with fallback"""
        # Test with config
        with patch('config.ProgramConfig.current', 
                  MagicMock(get=MagicMock(return_value="/test/root"))):
            self.assertEqual(get_root_directory(), "/test/root")
        
        # Test without config
        with patch('config.ProgramConfig.current', None):
            self.assertTrue(os.path.exists(get_root_directory()))

    def test_ensure_directory_exists(self):
        """Test directory creation with error handling"""
        # Test existing directory
        os.makedirs("test_dir")
        ensure_directory_exists("test_dir")
        
        # Test non-existing directory
        ensure_directory_exists("new_dir")
        self.assertTrue(os.path.exists("new_dir"))
        
        # Test error case
        with patch('os.makedirs', side_effect=OSError("Permission denied")):
            with self.assertRaises(SystemExit):
                ensure_directory_exists("test_dir")

    def test_log_output(self):
        """Test logging functionality"""
        # Test INFO log
        log("Test message")
        self.assertIn("Test message", self._get_output())
        
        # Test ERROR log
        log("Error message", level="ERROR")
        self.assertIn("Error message", self._get_output())
        
        # Test DEBUG log
        debug("Debug message")
        self.assertIn("Debug message", self._get_output())

    def _get_output(self):
        """Capture and return output from stdout"""
        with open(os.devnull, 'w') as devnull:
            original_stdout = sys.stdout
            sys.stdout = devnull
            sys.stdout = MagicMock()
            sys.stdout.write = MagicMock()
            return sys.stdout.write.call_args[0][0]

if __name__ == '__main__':
    unittest.main()


# This test suite covers:

# 1. Console control functions (title, clear, beep)
# 2. File system operations (search, read, write)
# 3. Time formatting
# 4. Configuration handling
# 5. Directory management
# 6. Logging and output functions

# The tests use:
# - `unittest` for test structure
# - `tempfile` for temporary directory management
# - `unittest.mock` for mocking OS functions and config
# - `patch` to mock external dependencies

# Note: This assumes the `color` module is properly implemented with the required color attributes (RED, BLUE, etc.). If the actual implementation differs, the test may need adjustments.