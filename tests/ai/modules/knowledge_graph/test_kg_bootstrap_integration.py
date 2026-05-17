from ai.modules.knowledge_graph import KnowledgeGraph

def test_kg_integration_bootstrap_surface():
    """
    Atomic integration test to validate Knowledge Graph bootstrap wiring.
    Ensures the module exposes an orchestrator bridge and a vector-memory surface
    that can be exposed via the bridge and invoked without errors.
    """
    kg_instance = KnowledgeGraph()
    bridge = kg_instance.register_with_orchestrator()
    assert hasattr(bridge, "expose"), "Bridge should expose a surface accessor"
    
    exposed = bridge.expose()
    assert isinstance(exposed, dict), "Expose() should return a dict of surfaces"
    assert "get_vector_memory" in exposed, "Expose should include get_vector_memory"
    
    vec_memory_provider = exposed["get_vector_memory"]
    assert callable(vec_memory_provider), "Provider should be a callable function"
    
    vector_memory = vec_memory_provider()
    # The vector memory should implement as_dict() per the existing surface
    assert hasattr(vector_memory, "as_dict"), "Vector memory must implement as_dict"
    assert isinstance(vector_memory.as_dict(), dict), "as_dict() should return a dict"