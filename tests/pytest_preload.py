# tests/pytest_preload.py
"""
This file is loaded as a pytest plugin to force the 'torch' library to be
imported at the very beginning of the test execution process.

This is necessary to work around an issue where the 'transformers' library
checks for 'torch' during pytest's test discovery phase, leading to a
"ValueError: torch.__spec__ is not set" error. By pre-loading 'torch' here,
we ensure it is fully initialized before any test collection begins.
"""
import torch