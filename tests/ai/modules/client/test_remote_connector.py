import pytest
import json
from unittest.mock import patch, MagicMock
from requests.exceptions import RequestException

from modules.client.remote_connector import RemoteBrainConnector

class TestRemoteBrainConnector:
    def setup_method(self):
        """
        Setup a new RemoteBrainConnector instance before each test.
        """
        self.url = "http://fake-brain:8000"
        self.model_id = "test-model"
        self.connector = RemoteBrainConnector(url=self.url, model_id=self.model_id)

    def test_initialization(self):
        """
        Tests that the connector is initialized with the correct attributes.
        """
        assert self.connector.url == self.url
        assert self.connector.model_id == self.model_id
        # Test that trailing slashes are stripped
        connector_with_slash = RemoteBrainConnector(url="http://fake-brain:8000/", model_id=self.model_id)
        assert connector_with_slash.url == self.url

    @patch('ai.modules.client.remote_connector.requests.get')
    def test_list_success(self, mock_get):
        """
        Tests the list method on a successful API call.
        """
        # Arrange
        mock_response = MagicMock()
        mock_response.json.return_value = {"model": "gpt-4-test"}
        mock_get.return_value = mock_response

        # Act
        result = self.connector.list()

        # Assert
        mock_get.assert_called_once_with(f"{self.url}/health")
        assert result == ["gpt-4-test"]

    @patch('ai.modules.client.remote_connector.requests.get')
    def test_list_failure(self, mock_get):
        """
        Tests the list method when the API call fails.
        """
        # Arrange
        mock_get.side_effect = RequestException("Connection failed")

        # Act
        result = self.connector.list()

        # Assert
        mock_get.assert_called_once_with(f"{self.url}/health")
        assert result == []

    @patch('ai.modules.client.remote_connector.requests.post')
    def test_chat_non_streaming_success(self, mock_post):
        """
        Tests the chat method for a successful non-streaming call.
        """
        # Arrange
        mock_response = MagicMock()
        expected_content = "This is a test response."
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": expected_content
                }
            }]
        }
        mock_post.return_value = mock_response
        messages = [{"role": "user", "content": "Hello"}]

        # Act
        # The chat method is a generator, so we collect its output into a list
        result = list(self.connector.chat(messages=messages, stream=False))

        # Assert
        mock_post.assert_called_once()
        assert len(result) == 1
        assert result[0] == expected_content

    @patch('ai.modules.client.remote_connector.requests.post')
    def test_chat_streaming_success(self, mock_post):
        """
        Tests the chat method for a successful streaming call.
        """
        # Arrange
        mock_response = MagicMock()
        chunks = ["This ", "is a ", "streaming test."]
        
        # Simulate the server sending data chunks
        def mock_iter_lines():
            for chunk in chunks:
                line = {
                    "choices": [{
                        "delta": {"content": chunk}
                    }]
                }
                # The server sends byte strings prefixed with 'data: '
                yield f"data: {json.dumps(line)}".encode('utf-8')
            # The stream is terminated by a special line
            yield b'data: [DONE]'

        mock_response.iter_lines.return_value = mock_iter_lines()
        mock_post.return_value = mock_response
        messages = [{"role": "user", "content": "Hello stream"}]

        # Act
        result_chunks = list(self.connector.chat(messages=messages, stream=True))
        result = "".join(result_chunks)

        # Assert
        mock_post.assert_called_once()
        assert result == "".join(chunks)