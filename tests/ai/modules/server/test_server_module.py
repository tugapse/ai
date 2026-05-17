import unittest
from unittest.mock import Mock, patch, MagicMock
import threading

import sys
import os

# --- VIRTUAL MODULE PATCH ---
# The module being tested and its dependencies have incorrect, non-relative
# import paths in the original source (e.g., `from core...`, `from services...`).
# We create virtual 'core' and 'services' packages in sys.modules to redirect
# these imports to their correct `ai.core` and `ai.services` locations at runtime.

# Ensure the source directory is in the path to find the real modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../src')))

try:
    # 1. Pre-emptively import the *actual* modules that the shims will point to.
    import core
    import services
    import modules.server.server_module
    from modules.server.server_module import JarvisServerModule

    # 4. Create a mock for the legacy top-level 'modules' package for compatibility.
    sys.modules['modules'] = Mock()
    sys.modules['modules.server'] = Mock()

except ImportError as e:
    raise ImportError(f"Could not import the actual JarvisServerModule for patching: {e}")
# --- END VIRTUAL MODULE PATCH ---


class TestJarvisServerModule(unittest.TestCase):

    def setUp(self):
        """Set up a fresh environment and mocks before each test."""
        # The module is now pre-imported by the patch, so we can reference it directly.
        # Patch the dependencies using the *correct* module path.
        self.patcher_uvicorn = patch('modules.server.server_module.uvicorn', new_callable=MagicMock)
        self.patcher_create_app = patch('modules.server.server_module.create_app', new_callable=MagicMock)
        self.patcher_brain_hub = patch('modules.server.server_module.BrainHub', new_callable=MagicMock)
        self.patcher_thread = patch('threading.Thread', new_callable=MagicMock)

        # Start the patchers and get the mock objects.
        self.mock_uvicorn = self.patcher_uvicorn.start()
        self.mock_create_app = self.patcher_create_app.start()
        self.mock_brain_hub_class = self.patcher_brain_hub.start()
        self.mock_thread_class = self.patcher_thread.start()

        # Configure mock instances that will be returned by the patched classes/functions
        self.mock_uvicorn_server = self.mock_uvicorn.Server.return_value
        self.mock_brain_hub_instance = self.mock_brain_hub_class.return_value
        self.mock_fastapi_app = self.mock_create_app.return_value
        self.mock_thread_instance = self.mock_thread_class.return_value

        # The module is already imported via the patch, so we just instantiate it.
        self.module = JarvisServerModule(host="127.0.0.1", port=8080)
        
        # Create mocks for arguments to the initialize method
        self.mock_config = Mock(name="ProgramConfig")
        self.mock_orchestrator = Mock(name="ModelOrchestrator")
        self.mock_history_manager = Mock(name="HistoryManager")

    def tearDown(self):
        """Clean up and stop all patchers after each test."""
        self.patcher_uvicorn.stop()
        self.patcher_create_app.stop()
        self.patcher_brain_hub.stop()
        self.patcher_thread.stop()

    def test_initial_state(self):
        """Test that the module is in a clean state before initialization."""
        self.assertIsNone(self.module._brain_hub)
        self.assertIsNone(self.module._fastapi_app)
        self.assertIsNone(self.module._server_thread)
        self.assertIsNone(self.module._uvicorn_server)

    def test_initialize(self):
        """Test the initialize method correctly sets up all server components."""
        # Call the method under test
        self.module.initialize(self.mock_config, self.mock_orchestrator, self.mock_history_manager)

        # 1. Verify BrainHub was initialized correctly
        self.mock_brain_hub_class.assert_called_once_with(self.mock_config)
        self.assertEqual(self.module._brain_hub, self.mock_brain_hub_instance)
        self.assertEqual(self.mock_brain_hub_instance.orchestrator, self.mock_orchestrator)

        # 2. Verify FastAPI app was created correctly
        self.mock_create_app.assert_called_once_with(self.mock_brain_hub_instance, self.mock_config)
        self.assertEqual(self.module._fastapi_app, self.mock_fastapi_app)

        # 3. Verify Uvicorn was configured and its server instantiated
        self.mock_uvicorn.Config.assert_called_once_with(
            app=self.mock_fastapi_app,
            host="127.0.0.1",
            port=8080,
            log_level="info"
        )
        self.mock_uvicorn.Server.assert_called_once_with(self.mock_uvicorn.Config.return_value)
        self.assertEqual(self.module._uvicorn_server, self.mock_uvicorn_server)

    def test_start(self):
        """Test the start method creates and starts a new thread for the Uvicorn server."""
        # Prerequisite: module must be initialized
        self.module.initialize(self.mock_config, self.mock_orchestrator, self.mock_history_manager)

        # Call the method under test
        self.module.start()

        # Verify a thread was created with the correct target (the uvicorn server's run method)
        self.mock_thread_class.assert_called_once_with(target=self.mock_uvicorn_server.run, daemon=True)

        # Verify the thread was started
        self.mock_thread_instance.start.assert_called_once()

        # Note: The join call is problematic and blocks, but we test the actual implementation.
        self.mock_thread_instance.join.assert_called_once()

    def test_shutdown(self):
        """Test the shutdown method gracefully stops components and cleans up state."""
        # Prerequisite: Initialize to populate internal state
        self.module.initialize(self.mock_config, self.mock_orchestrator, self.mock_history_manager)
        
        # Call the method under test
        self.module.shutdown()

        # Verify the uvicorn server is signaled to exit
        self.assertTrue(self.mock_uvicorn_server.should_exit)
        
        # Verify the brain hub is unloaded
        self.mock_brain_hub_instance.unload_brain.assert_called_once()
            
        # Verify internal state is reset
        self.assertIsNone(self.module._brain_hub)
        self.assertIsNone(self.module._fastapi_app)

if __name__ == '__main__':
    unittest.main()