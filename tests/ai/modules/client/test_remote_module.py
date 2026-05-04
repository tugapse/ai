import pytest
from unittest.mock import patch, MagicMock
import sys


try:
    from ai.modules.base_module import BaseModule
    from ai.modules.client.remote_connector import RemoteBrainConnector
except ImportError as e:
    pytest.fail(f"Could not import the actual modules needed for patching: {e}")

sys.modules['core'] = MagicMock()
sys.modules['core.modules'] = MagicMock()
sys.modules['core.llms'] = MagicMock()

sys.modules['core.modules.base_module'] = sys.modules['ai.modules.base_module']
sys.modules['core.llms.remote_connector'] = sys.modules['ai.modules.client.remote_connector']


from ai.modules.client.remote_module import RemoteConnectorModule

@patch('ai.modules.client.remote_module.func')
@patch('ai.modules.client.remote_module.RemoteBrainConnector')
def test_remote_connector_module_lifecycle(mock_remote_connector_class, mock_func_log):
    """
    Tests the full lifecycle of the RemoteConnectorModule:
    1. Initialization
    2. Connection logic setup
    3. Shutdown signaling
    """
    # Arrange
    test_url = "http://localhost:8000"
    test_model_id = "test-model"
    test_system_prompt = "You are a test."

    # Mock the instance returned by the RemoteBrainConnector class
    mock_connector_instance = MagicMock()
    mock_remote_connector_class.return_value = mock_connector_instance

    # Instantiate the module
    module = RemoteConnectorModule(url=test_url, model_id=test_model_id)

    # Act: Initialize the module
    module.initialize(system_prompt=test_system_prompt)

    # Assert: Initialization
    # Check if the log function was called with the expected message
    mock_func_log.log.assert_called_with(f"Linking to Remote Brain at {test_url} (Model: {test_model_id})")

    # Check if RemoteBrainConnector was instantiated with the correct arguments
    mock_remote_connector_class.assert_called_once_with(
        url=test_url,
        model_id=test_model_id,
        system_prompt=test_system_prompt
    )
    assert module._instance is mock_connector_instance

    # Act: Shutdown the module
    module.shutdown()

    # Assert: Shutdown
    # Check if the log function was called during shutdown
    mock_func_log.log.assert_called_with("RemoteLink: Closing connection...")
    # Check if the shutdown method on the connector instance was called
    mock_connector_instance.request_shutdown.assert_called_once()