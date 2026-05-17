from ai.modules.knowledge_graph import KnowledgeGraph

def test_knowledge_graph_bootstrap_bridge():
    kg = KnowledgeGraph()
    bridge = kg.register_with_orchestrator()
    assert bridge is not None
    assert hasattr(bridge, "expose")
    payload = bridge.expose()
    assert isinstance(payload, dict)
    assert "get_vector_memory" in payload
    provider = payload["get_vector_memory"]
    assert callable(provider)
    vm = provider()
    assert hasattr(vm, "as_dict")
    assert isinstance(vm.as_dict(), dict)