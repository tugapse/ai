import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

@pytest.fixture(scope="session", autouse=True)
def global_mocks():
    """
    This session-scoped fixture provides mocks for the entire test suite.
    It automatically applies the mocks to all tests.
    """
    # Determine the project root dynamically.
    # The conftest.py is in /tests, so the root is one level up.
    project_root = Path(__file__).parent.parent.resolve()

    # We need to patch 'get_root_directory' where it's *looked up*,
    # not where it's defined. The tests import it into their own namespace
    # or use it through other modules. A common pattern is `from ai import functions`.
    # Let's patch the original source to be safe.
    patcher = patch('ai.functions.get_root_directory', return_value=project_root)

    # Start the patch
    mock_get_root = patcher.start()

    # Yield control to the test session
    yield mock_get_root

    # Stop the patch after the test session ends
    patcher.stop()