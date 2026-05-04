import sys
import os
from pathlib import Path

# Ensure the repository root and the 'src' directory are on sys.path so imports like
# `from src.ai` resolve during pytest collection and execution.
# The conftest.py is in /tests, so the root is two levels up.
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
SRC_DIR = PROJECT_ROOT / 'src'

# Add project root to sys.path if not already present
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add src directory to sys.path if it exists and is not already present
if SRC_DIR.is_dir() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture(scope="session", autouse=True)
def global_mocks():
    """
    This session-scoped fixture provides mocks for the entire test suite.
    It automatically applies the mocks to all tests.
    """
    # The project root is already determined above.
    # We need to patch 'get_root_directory' where it's *looked up*,
    # not where it's defined. The tests import it into their own namespace
    # or use it through other modules. A common pattern is `import functions`.
    # Let's patch the original source to be safe.
    patcher = patch('ai.functions.get_root_directory', return_value=PROJECT_ROOT)

    # Start the patch
    mock_get_root = patcher.start()

    # Yield control to the test session
    yield mock_get_root

    # Stop the patch after the test session ends
    patcher.stop()