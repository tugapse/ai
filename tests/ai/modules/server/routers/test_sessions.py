import unittest
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai.modules.server.routers.sessions import router
from ai.modules.server.services.session_manager import (
    SessionNotFoundError,
    InvalidPathError as SessionInvalidPathError,
)


class TestSessionsRouter(unittest.TestCase):
    def setUp(self):
        """Set up a test FastAPI app with the sessions router and mock dependencies."""
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)

        # Mock the session manager
        self.mock_session_manager = MagicMock()
        self.app.state.session_manager = self.mock_session_manager

    def test_get_sessions_success(self):
        """Test fetching a list of sessions successfully."""
        mock_sessions = [{"id": "session1"}, {"id": "session2"}]
        self.mock_session_manager.list_sessions.return_value = mock_sessions

        response = self.client.get("/api/v1/sessions")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"sessions": mock_sessions})
        self.mock_session_manager.list_sessions.assert_called_once_with(None)

    def test_get_session_content_success(self):
        """Test fetching a specific session's content."""
        mock_content = {"messages": []}
        self.mock_session_manager.load_session.return_value = mock_content

        response = self.client.get("/api/v1/sessions/test/path")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), mock_content)
        self.mock_session_manager.load_session.assert_called_once_with("test/path")

    def test_get_session_content_not_found(self):
        """Test fetching a non-existent session."""
        self.mock_session_manager.load_session.side_effect = SessionNotFoundError("Not found")

        response = self.client.get("/api/v1/sessions/test/path")
        
        self.assertEqual(response.status_code, 404)

    def test_delete_session_success(self):
        """Test deleting a session."""
        response = self.client.delete("/api/v1/sessions/test/path")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "success", "message": "Session test/path deleted."})
        self.mock_session_manager.delete_session.assert_called_once_with("test/path")

if __name__ == '__main__':
    unittest.main()