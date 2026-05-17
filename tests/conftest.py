# tests/conftest.py

"""
This file is used to configure pytest.

We are adding an import for the 'torch' library here to address a specific
issue related to the 'transformers' library. The 'transformers' library checks
for the availability of 'torch' in a way that can conflict with pytest's test
discovery process, leading to a "ValueError: torch.__spec__ is not set" error.

By importing 'torch' here, we ensure that it is fully loaded and initialized
before pytest begins collecting tests, thus preventing the error.

Additionally, we use the pytest_configure hook to load the ProgramConfig
before any tests are collected. This is necessary because some modules
access the configuration at import time, which occurs before fixtures are run.
Using pytest_configure ensures the configuration is available when modules
are imported, resolving the "RuntimeError: ProgramConfig not initialized."
"""

import torch
from ai.config import ProgramConfig

def pytest_configure(config):
    """
    Loads the program configuration before test collection begins.
    """
    ProgramConfig.load()