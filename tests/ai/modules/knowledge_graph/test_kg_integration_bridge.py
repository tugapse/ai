"""
Knowledge Graph integration bridge integration test.

This test ensures the KnowledgeGraph module wires into the agent orchestrator surface
without altering startup behavior. It exercises the public API surface exposed by
src.ai.modules.knowledge_graph.KnowledgeGraph and its register_with_orchestrator hook.
"""

from src.ai.modules.knowledge_graph import KnowledgeGraph


def test_kg_integration_bridge_bootstrap():
    """
    Validates that the KnowledgeGraph class can be instantiated, registered,
    and that its exposed vector memory can be accessed and used.
    """
    kg = KnowledgeGraph()
    bridge = kg.register_with_orchestrator(None)
    assert hasattr(bridge, "expose"), "Bridge should expose an interface for downstream wiring"

    exposed = bridge.expose()
    assert "get_vector_memory" in exposed, "Bridge should expose vector memory accessor"

    memory_provider = exposed["get_vector_memory"]
    assert callable(memory_provider), "The vector memory accessor should be a callable provider"

    vector_memory = memory_provider()
    assert hasattr(vector_memory, "as_dict"), "Vector memory must implement as_dict"

    # Validate basic vector memory operations
    vector_memory.add_vector("sample_key", [0.1, 0.2, 0.3])
    assert vector_memory.get_vector("sample_key") == [0.1, 0.2, 0.3]
    assert isinstance(vector_memory.as_dict(), dict)