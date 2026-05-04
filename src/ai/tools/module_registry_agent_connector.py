#!/usr/bin/env python3

"""
ModuleRegistry-Agent Connector
Minimal integration helper to initialize the in-repo ModuleRegistry and expose
the list of active modules for agent startup orchestration.

This file is intentionally lightweight to avoid side effects during normal agent
startup while providing a deterministic integration point for capability discovery.
"""

from typing import Optional, Dict, Any, List

class _InlineConfig:
    """Fallback config object used when no external config is provided."""
    def get(self, key: str, default=None):
        return default

def initialize_registry(config: Optional[Any] = None):
    """
    Create and initialize a ModuleRegistry instance using the provided config.

    If no config is provided, a minimal inline config is used to exercise
    the default-loading semantics (e.g., knowledge_graph by default).
    """
    try:
        from ai.services.module_registry import ModuleRegistry
    except Exception:
        return None

    cfg = config or _InlineConfig()
    registry = ModuleRegistry(cfg)

    # Attempt to wire KnowledgeGraph into the orchestrator bus if it's available.
    # This preserves startup behavior when a bus is not present.
    try:
        import ai.modules.knowledge_graph as _kg  # noqa: F401
        if hasattr(_kg, "register_with_orchestrator"):
            bus = None
            # Discover a bus from several conventional locations
            for path in [
                "ai.orchestrator.bus",
                "ai.services.orchestrator",
                "ai.services.orchestrator_bus",
                "ai.tools.orchestrator_bus",
            ]:
                try:
                    mod = __import__(path, fromlist=['bus', 'get_bus'])
                    if hasattr(mod, "get_bus") and callable(getattr(mod, "get_bus")):
                        bus = getattr(mod, "get_bus")()
                    elif hasattr(mod, "bus"):
                        bus = getattr(mod, "bus")
                    if bus is not None:
                        break
                except Exception:
                    continue
            try:
                _kg.register_with_orchestrator(bus)
            except Exception:
                # If bus wiring fails, fall back to existing behavior with None
                try:
                    _kg.register_with_orchestrator(None)
                except Exception:
                    pass
    except Exception:
        pass

    # Eagerly import optional capabilities to ensure they're registered
    try:
        import ai.modules.knowledge_graph as _kg
    except Exception:
        pass

    # Best-effort load; failures should not crash agent startup
    try:
        registry.load_all()
    except Exception:
        pass

    return registry

def active_module_names(registry) -> List[str]:
    """Return a list of currently active module names from the registry."""
    if registry is None:
        return []
    return list(getattr(registry, "_active_modules", {}).keys())

def describe_registry(registry) -> Dict[str, str]:
    """Return a human-friendly description of loaded modules and their types."""
    names = active_module_names(registry)
    summary: Dict[str, str] = {}
    for name in names:
        inst = registry._active_modules.get(name)
        summary[name] = type(inst).__name__ if inst is not None else "None"
    return summary

def bootstrap_registry_report(config: Optional[Any] = None) -> Dict[str, Any]:
    """
    Production-ready bootstrap helper for agents.

    Returns a deterministic payload describing the current registry state:
      - active_modules: list[str]
      - module_descriptions: dict[str, str] mapping module name -> type name
    """
    registry = initialize_registry(config)
    # Force import of knowledge_graph to ensure Python side-effects register it if present
    try:
        import ai.modules.knowledge_graph as _kg
    except Exception:
        pass
    # Best-effort load; do not raise on failure
    if registry is not None:
        try:
            registry.load_all()
        except Exception:
            pass
    names = sorted(active_module_names(registry))
    descriptions = describe_registry(registry) if registry is not None else {}
    # Ensure deterministic payload shape
    return {
        "active_modules": names,
        "module_descriptions": descriptions
    }

if __name__ == "__main__":
    reg = initialize_registry()
    names = active_module_names(reg)
    print("ACTIVE_MODULES:", names)
    for name, t in describe_registry(reg).items():
        print(f"Module '{name}': {t}")