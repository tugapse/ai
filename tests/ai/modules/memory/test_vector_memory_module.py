import unittest
import tempfile
import shutil
from unittest.mock import patch, Mock, ANY

# Import the module under test at the top level
from modules.memory.vector_memory_module import VectorMemoryModule


class TestVectorMemoryModule(unittest.TestCase):

    def setUp(self):
        """Set up a fresh module instance, mocks, and a temporary directory before each test."""
        # Start patchers
        self.func_patcher = patch('ai.modules.memory.vector_memory_module.func')
        # Patch the class where it is defined for reliability
        self.vm_patcher = patch('ai.modules.memory.vector_memory_module.VectorMemory')
        
        self.mock_functions = self.func_patcher.start()
        self.mock_vector_memory = self.vm_patcher.start()

        # Create a temporary directory for the test database
        self.test_dir = tempfile.mkdtemp()
        self.db_path = self.test_dir

        self.mock_connector = Mock(name="LLMConnector")
        self.session_id = "test-session-123"

        # Instantiate the module wrapper
        self.module_wrapper = VectorMemoryModule(db_path=self.db_path, some_kwarg="value")

    def tearDown(self):
        """Clean up the temporary directory and stop patchers after each test."""
        shutil.rmtree(self.test_dir)
        self.func_patcher.stop()
        self.vm_patcher.stop()

    def test_initial_state(self):
        """Test that the module is not initialized upon creation."""
        self.assertIsNone(self.module_wrapper._instance)
        self.assertFalse(self.module_wrapper._is_initialized)
        self.assertEqual(self.module_wrapper.db_path, self.db_path)
        self.assertEqual(self.module_wrapper.kwargs, {"some_kwarg": "value"})

    def test_get_instance_before_initialization(self):
        """Test that getting the instance before initialization returns None and logs an error."""
        instance = self.module_wrapper.get_instance()
        self.assertIsNone(instance)
        self.mock_functions.log.assert_called_once_with(
            "Attempted to use VectorMemory before it was initialized.", level="ERROR"
        )

    def test_successful_initialization(self):
        """Test that initialize() creates and configures the VectorMemory instance."""
        self.assertIsNone(self.module_wrapper._instance)

        self.module_wrapper.initialize(self.session_id, self.mock_connector)

        # Assert that the underlying VectorMemory was instantiated with the correct arguments
        self.mock_vector_memory.assert_called_once_with(
            session_id=self.session_id,
            connector=self.mock_connector,
            db_path=self.db_path
        )

        self.assertTrue(self.module_wrapper._is_initialized)
        self.assertIsNotNone(self.module_wrapper._instance)
        self.assertEqual(self.module_wrapper.get_instance(), self.mock_vector_memory.return_value)

        self.mock_functions.log.assert_any_call(f"Initializing VectorMemory for session {self.session_id}...")
        self.mock_functions.log.assert_any_call("VectorMemoryModule initialized successfully.")

    def test_idempotent_initialization(self):
        """Test that calling initialize() multiple times does not re-create the instance."""
        self.module_wrapper.initialize(self.session_id, self.mock_connector)
        first_instance = self.module_wrapper.get_instance()
        
        self.assertEqual(self.mock_vector_memory.call_count, 1)

        self.module_wrapper.initialize("other-session-id", Mock())

        self.assertEqual(self.mock_vector_memory.call_count, 1)
        self.assertIs(self.module_wrapper.get_instance(), first_instance)

        self.mock_functions.log.assert_called_with("VectorMemoryModule is already initialized.", level="WARN")

    def test_shutdown(self):
        """Test that shutdown() resets the module's state."""
        self.module_wrapper.initialize(self.session_id, self.mock_connector)
        self.assertIsNotNone(self.module_wrapper.get_instance())

        self.module_wrapper.shutdown()

        self.assertIsNone(self.module_wrapper._instance)
        self.mock_functions.log.assert_called_with("Shutting down VectorMemoryModule.")

if __name__ == '__main__':
    unittest.main()