import unittest
import tempfile
import shutil
from unittest.mock import patch, Mock, ANY
import sys
from unittest.mock import MagicMock

from ai.modules.vector_memory.vector_memory_module import VectorMemoryModule


class TestVectorMemoryModule(unittest.TestCase):

    def setUp(self):
        """Set up a fresh module instance, mocks, and a temporary directory before each test."""
        # Start patchers
        self.func_patcher = patch('ai.modules.vector_memory.vector_memory_module.func')
        # Patch the class where it is defined for reliability
        self.vm_patcher = patch('ai.modules.vector_memory.vector_memory_module.VectorMemory')

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
        """Getting the instance before initialization returns None."""
        self.assertIsNone(self.module_wrapper.get_instance())

    def _instances_with_scope(self):
        def make(**kwargs):
            inst = Mock(name="VectorMemoryInstance")
            inst.scope_key = kwargs["scope_key"]
            return inst
        self.mock_vector_memory.side_effect = make

    def test_successful_initialization(self):
        """initialize() creates the VectorMemory with the scope and the module kwargs."""
        self.module_wrapper.initialize(self.session_id, self.mock_connector, scope_key="project:/x")

        self.mock_vector_memory.assert_called_once_with(
            session_id=self.session_id,
            llm=self.mock_connector,
            db_path=self.db_path,
            scope_key="project:/x",
            some_kwarg="value",
        )
        self.assertTrue(self.module_wrapper._is_initialized)
        self.assertIs(self.module_wrapper.get_instance(), self.mock_vector_memory.return_value)

    def test_scope_defaults_to_session(self):
        self.module_wrapper.initialize(self.session_id, self.mock_connector)
        self.assertEqual(self.mock_vector_memory.call_args.kwargs["scope_key"], self.session_id)

    def test_same_scope_reuses_instance(self):
        """A new session in the same scope keeps the instance and updates its session id."""
        self._instances_with_scope()
        self.module_wrapper.initialize(self.session_id, self.mock_connector, scope_key="project:/x")
        first = self.module_wrapper.get_instance()

        self.module_wrapper.initialize("other-session-id", Mock(), scope_key="project:/x")

        self.assertEqual(self.mock_vector_memory.call_count, 1)
        self.assertIs(self.module_wrapper.get_instance(), first)
        self.assertEqual(first.session_id, "other-session-id")

    def test_other_scope_opens_new_instance(self):
        self._instances_with_scope()
        self.module_wrapper.initialize(self.session_id, self.mock_connector, scope_key="project:/x")
        first = self.module_wrapper.get_instance()
        self.module_wrapper.initialize(self.session_id, self.mock_connector, scope_key="project:/y")
        self.assertEqual(self.mock_vector_memory.call_count, 2)
        self.assertIsNot(self.module_wrapper.get_instance(), first)

    def test_failed_initialization_leaves_module_inactive(self):
        self.mock_vector_memory.side_effect = ImportError("chromadb is not installed")
        self.module_wrapper.initialize(self.session_id, self.mock_connector)
        self.assertIsNone(self.module_wrapper.get_instance())
        self.assertFalse(self.module_wrapper.is_active)

    def test_shutdown(self):
        """Test that shutdown() resets the module's state."""
        self.module_wrapper.initialize(self.session_id, self.mock_connector)
        self.assertIsNotNone(self.module_wrapper.get_instance())

        self.module_wrapper.shutdown()

        self.assertIsNone(self.module_wrapper._instance)
        self.mock_functions.log.assert_called_with("Shutting down VectorMemoryModule.")

if __name__ == '__main__':
    unittest.main()