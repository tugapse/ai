#!/usr/bin/env python3
import os
import sys

# Dry-run harness to verify that Knowledge Graph surfaces in ModuleRegistry
# when no explicit ENABLED config is provided. The harness loads the
# registry with a minimal dummy config and reports the actively loaded modules.

# Ensure the project src directory is on sys.path so that `ai` packages can be imported.
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    # Import the ModuleRegistry from the in-repo source
    from ai.services.module_registry import ModuleRegistry
except Exception as import_error:
    print("IMPORT_ERROR:", import_error)
    sys.exit(1)

class DummyConfig:
    """
    Minimal config object that mirrors the interface used by ModuleRegistry.
    Returns default for any key to trigger default-loading behavior.
    """
    def get(self, key, default=None):
        return default

def main():
    config = DummyConfig()
    registry = ModuleRegistry(config)

    # Execute a dry-run load; knowledge_graph should auto-load by default
    registry.load_all()

    loaded_names = list(registry._active_modules.keys())
    print("DRY_RUN_ACTIVE_MODULES:", loaded_names)

    for name, instance in registry._active_modules.items():
        print(f"Module '{name}': {type(instance).__name__}")

if __name__ == "__main__":
    main()