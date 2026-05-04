#!/usr/bin/env python3
"""
Dry-run bootstrap for KnowledgeGraph integration surface with the Module Registry.

This script exercises the new KnowledgeGraph.register_with_orchestrator(bus) surface
without starting the full orchestration pipeline.

It attempts to import the wrapper KnowledgeGraph from the modules package and
invoke the register_with_orchestrator with a None bus to validate surface presence.

This file is intended for quick, isolated validation during development.
"""

import sys

# Try both import paths to accommodate packaging layouts
KnowledgeGraph = None
try:
    try:
        from modules.knowledge_graph import KnowledgeGraph
    except Exception:
        from knowledge_graph import KnowledgeGraph  # fallback
except Exception as e:
    print(f"[KG-Bootstrap] Import failed: {e}", file=sys.stderr)
    KnowledgeGraph = None

def main() -> int:
    if KnowledgeGraph is None:
        print("[KG-Bootstrap] KnowledgeGraph wrapper not available. Aborting bootstrap.", file=sys.stderr)
        return 1

    try:
        kg = KnowledgeGraph()
        # If wrapper provides a get_instance hook, prefer it for testing surface parity
        target = kg
        if hasattr(kg, "get_instance"):
            target = kg.get_instance()

        if hasattr(target, "register_with_orchestrator"):
            result = target.register_with_orchestrator(None)
            print("[KG-Bootstrap] register_with_orchestrator(None) ->", type(result).__name__)
        else:
            print("[KG-Bootstrap] register_with_orchestrator surface not found on target.", file=sys.stderr)
            return 2
    except Exception as exc:
        print(f"[KG-Bootstrap] Execution failed: {exc}", file=sys.stderr)
        return 3

    return 0

if __name__ == "__main__":
    sys.exit(main())