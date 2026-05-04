import sys
import os

# Ensure the repository root and the 'src' directory are on sys.path so imports like
# `import ai` and `from src.ai` both resolve during pytest collection and execution.

ROOT = os.path.abspath(os.path.dirname(__file__))
SRC_DIR = os.path.join(ROOT, 'src')

root_abs = os.path.abspath(ROOT)
src_abs = os.path.abspath(SRC_DIR)

# Add ROOT to sys.path if not already present
if root_abs not in [os.path.abspath(p) for p in sys.path]:
    sys.path.insert(0, root_abs)

# Add ROOT/src to sys.path if it exists and is not already present
if os.path.isdir(src_abs):
    if src_abs not in [os.path.abspath(p) for p in sys.path]:
        sys.path.insert(0, src_abs)