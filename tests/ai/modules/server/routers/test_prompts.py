import unittest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai.modules.server.routers.prompts import router
from ai.modules.server.services.prompt_manager import (
    PromptNotFoundError,
    InvalidPathError as PromptInvalidPathError,
)

class TestPromptsRouter(unittest.TestCase):
    def setUp(self):
        """Set up a test FastAPI app with the prompts router and mock dependencies."""
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)

        # Mock the prompt manager
        self.mock_prompt_manager = MagicMock()
        self.app.state.prompt_manager = self.mock_prompt_manager

    def test_get_prompts_success(self):
        """Test fetching a list of prompts successfully."""
        mock_prompts = [{"name": "prompt1"}, {"name": "prompt2"}]
        self.mock_prompt_manager.list_prompts.return_value = mock_prompts

        response = self.client.get("/api/v1/prompts")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"prompts": mock_prompts})
        self.mock_prompt_manager.list_prompts.assert_called_once_with(None)

    def test_get_prompt_content_success(self):
        """Test fetching a specific prompt's content."""
        mock_content = "This is a prompt."
        self.mock_prompt_manager.read_prompt.return_value = mock_content

        response = self.client.get("/api/v1/prompts/test/prompt")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), mock_content)
        self.mock_prompt_manager.read_prompt.assert_called_once_with("test/prompt")

    def test_create_prompt_success(self):
        """Test creating a new prompt."""
        payload = {"prompt_path": "new/prompt", "content": "New content"}
        self.mock_prompt_manager.create_prompt.return_value = {"status": "success"}

        response = self.client.post("/api/v1/prompts", json=payload)
        
        self.assertEqual(response.status_code, 200)
        self.mock_prompt_manager.create_prompt.assert_called_once_with("new/prompt", "New content")

    def test_delete_prompt_success(self):
        """Test deleting a prompt."""
        response = self.client.delete("/api/v1/prompts/test/prompt")
        
        self.assertEqual(response.status_code, 200)
        self.mock_prompt_manager.delete_prompt.assert_called_once_with("test/prompt")

if __name__ == '__main__':
    unittest.main()