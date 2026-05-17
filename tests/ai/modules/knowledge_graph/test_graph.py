import pytest
from ai.modules.knowledge_graph.graph import KnowledgeGraph

@pytest.fixture
def empty_graph():
    """Returns an empty KnowledgeGraph instance."""
    return KnowledgeGraph()

@pytest.fixture
def populated_graph():
    """Returns a KnowledgeGraph instance populated with some data."""
    kg = KnowledgeGraph()
    kg.add_node("A", type="class")
    kg.add_node("B", type="function")
    kg.add_node("C", type="method")
    kg.add_node("D", type="variable")
    kg.add_relation("A", "CONTAINS", "C")
    kg.add_relation("B", "CALLS", "C")
    kg.add_relation("C", "USES", "D")
    return kg

def test_add_node_new(empty_graph: KnowledgeGraph):
    """Test adding a new node."""
    node_id = empty_graph.add_node("test_node", color="blue")
    assert empty_graph.has_node("test_node")
    assert empty_graph.get_node("test_node") == {"color": "blue"}
    assert node_id == "test_node"

def test_add_node_update_existing(empty_graph: KnowledgeGraph):
    """Test updating an existing node's attributes."""
    empty_graph.add_node("test_node", color="blue")
    empty_graph.add_node("test_node", size=10)
    assert empty_graph.get_node("test_node") == {"color": "blue", "size": 10}

def test_get_node(populated_graph: KnowledgeGraph):
    """Test retrieving an existing node."""
    node = populated_graph.get_node("A")
    assert node is not None
    assert node["type"] == "class"

def test_get_node_nonexistent(populated_graph: KnowledgeGraph):
    """Test retrieving a non-existent node."""
    assert populated_graph.get_node("Z") is None

def test_has_node(populated_graph: KnowledgeGraph):
    """Test checking for node existence."""
    assert populated_graph.has_node("A")
    assert not populated_graph.has_node("Z")

def test_add_relation_existing_nodes(populated_graph: KnowledgeGraph):
    """Test adding a relation between existing nodes."""
    src, rel, dst = populated_graph.add_relation("A", "CALLS", "B")
    assert (src, rel, dst) == ("A", "CALLS", "B")
    assert "B" in populated_graph.get_neighbors("A", "CALLS")

def test_add_relation_creates_nodes(empty_graph: KnowledgeGraph):
    """Test that adding a relation creates nodes if they don't exist."""
    assert not empty_graph.has_node("src_node")
    assert not empty_graph.has_node("dst_node")
    empty_graph.add_relation("src_node", "LINKS_TO", "dst_node")
    assert empty_graph.has_node("src_node")
    assert empty_graph.has_node("dst_node")
    assert "dst_node" in empty_graph.get_neighbors("src_node")

def test_get_relations_all(populated_graph: KnowledgeGraph):
    """Test getting all relations from the graph."""
    relations = populated_graph.get_relations()
    assert len(relations) == 3
    assert ("A", "CONTAINS", "C") in relations
    assert ("B", "CALLS", "C") in relations
    assert ("C", "USES", "D") in relations

def test_get_relations_for_source(populated_graph: KnowledgeGraph):
    """Test getting relations for a specific source node."""
    relations = populated_graph.get_relations("A")
    assert relations == [("A", "CONTAINS", "C")]

def test_get_relations_no_relations(populated_graph: KnowledgeGraph):
    """Test getting relations for a node with no outgoing edges."""
    assert populated_graph.get_relations("D") == []

def test_get_neighbors(populated_graph: KnowledgeGraph):
    """Test getting all neighbors for a node."""
    neighbors = populated_graph.get_neighbors("A")
    assert neighbors == ["C"]

def test_get_neighbors_by_relation(populated_graph: KnowledgeGraph):
    """Test getting neighbors filtered by relation type."""
    populated_graph.add_relation("A", "CALLS", "B")
    assert populated_graph.get_neighbors("A", "CONTAINS") == ["C"]
    assert populated_graph.get_neighbors("A", "CALLS") == ["B"]

def test_get_neighbors_nonexistent_node(populated_graph: KnowledgeGraph):
    """Test getting neighbors for a non-existent node."""
    assert populated_graph.get_neighbors("Z") == []

def test_find_path_exists(populated_graph: KnowledgeGraph):
    """Test finding a simple path."""
    path = populated_graph.find_path("B", "D")
    assert path == ["B", "C", "D"]

def test_find_path_same_node(populated_graph: KnowledgeGraph):
    """Test finding a path from a node to itself."""
    path = populated_graph.find_path("A", "A")
    assert path == ["A"]

def test_find_path_no_path(populated_graph: KnowledgeGraph):
    """Test finding a path that does not exist."""
    path = populated_graph.find_path("A", "B")
    assert path is None

def test_find_path_max_depth(empty_graph: KnowledgeGraph):
    """Test that find_path respects the max_depth parameter."""
    empty_graph.add_relation("1", "->", "2")
    empty_graph.add_relation("2", "->", "3")
    empty_graph.add_relation("3", "->", "4")
    assert empty_graph.find_path("1", "4", max_depth=3) == ["1", "2", "3", "4"]
    assert empty_graph.find_path("1", "4", max_depth=2) is None

def test_repr_method(populated_graph: KnowledgeGraph):
    """Test the __repr__ method for correct output."""
    assert repr(populated_graph) == "KnowledgeGraph(nodes=4, edges=3)"

def test_to_dot_representation(populated_graph: KnowledgeGraph):
    """Test the Graphviz DOT representation."""
    dot_str = populated_graph.to_dot()
    assert "digraph KnowledgeGraph {" in dot_str
    assert 'node [shape=ellipse];' in dot_str
    assert '"A" [label="A\\ntype=class"];' in dot_str
    assert '"B" [label="B\\ntype=function"];' in dot_str
    assert '"C" [label="C\\ntype=method"];' in dot_str
    assert '"D" [label="D\\ntype=variable"];' in dot_str
    assert '"A" -> "C" [label="CONTAINS"];' in dot_str
    assert '"B" -> "C" [label="CALLS"];' in dot_str
    assert '"C" -> "D" [label="USES"];' in dot_str
    assert "}" in dot_str