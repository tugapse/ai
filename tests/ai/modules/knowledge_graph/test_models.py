import pytest
from uuid import UUID, uuid4
from pydantic import ValidationError

from src.ai.modules.knowledge_graph.models import (
    NodeTypes,
    RelationshipTypes,
    KGNode,
    KGEdge,
    KGTriple,
    AmbiguityFlag,
    AnalysisReport,
    RefinementReport
)

def test_node_types_enum():
    """Tests that NodeTypes enum has the correct members."""
    assert NodeTypes.FILE == "FILE"
    assert NodeTypes.CLASS == "CLASS"
    assert NodeTypes.FUNCTION == "FUNCTION"
    assert len(NodeTypes) == 8

def test_relationship_types_enum():
    """Tests that RelationshipTypes enum has the correct members."""
    assert RelationshipTypes.CONTAINS == "CONTAINS"
    assert RelationshipTypes.CALLS == "CALLS"
    assert RelationshipTypes.IMPORTS == "IMPORTS"
    assert len(RelationshipTypes) == 9

def test_kgnode_creation():
    """Tests successful creation of a KGNode."""
    node = KGNode(type=NodeTypes.FUNCTION, name="my_function")
    assert isinstance(node.id, UUID)
    assert node.type == NodeTypes.FUNCTION
    assert node.name == "my_function"
    assert node.source_text is None
    assert node.properties == {}

def test_kgnode_creation_with_optionals():
    """Tests KGNode creation with optional fields."""
    props = {"line": 10, "is_async": True}
    node = KGNode(
        type=NodeTypes.CLASS,
        name="MyClass",
        source_text="class MyClass: pass",
        properties=props
    )
    assert node.name == "MyClass"
    assert node.source_text == "class MyClass: pass"
    assert node.properties == props

def test_kgnode_missing_required_fields():
    """Tests that KGNode raises ValidationError for missing required fields."""
    with pytest.raises(ValidationError):
        KGNode(type=NodeTypes.FILE)  # Missing 'name'
    with pytest.raises(ValidationError):
        KGNode(name="a_file.py")  # Missing 'type'

def test_kgedge_creation():
    """Tests successful creation of a KGEdge."""
    source_id = uuid4()
    target_id = uuid4()
    edge = KGEdge(
        source_id=source_id,
        target_id=target_id,
        type=RelationshipTypes.DEFINES
    )
    assert isinstance(edge.id, UUID)
    assert edge.source_id == source_id
    assert edge.target_id == target_id
    assert edge.type == RelationshipTypes.DEFINES
    assert edge.properties == {}

def test_kgedge_invalid_uuid():
    """Tests that KGEdge raises ValidationError for invalid UUIDs."""
    with pytest.raises(ValidationError):
        KGEdge(source_id="not-a-uuid", target_id=uuid4(), type=RelationshipTypes.CALLS)

def test_kgtriple_creation():
    """Tests successful creation of a KGTriple."""
    source_id = uuid4()
    target_id = uuid4()
    triple = KGTriple(
        source_id=source_id,
        relationship_type=RelationshipTypes.INHERITS_FROM,
        target_id=target_id,
    )
    assert triple.source_id == source_id
    assert triple.target_id == target_id
    assert triple.relationship_type == RelationshipTypes.INHERITS_FROM
    assert triple.confidence_score == 1.0  # Check default value

def test_ambiguity_flag_creation():
    """Tests successful creation of an AmbiguityFlag."""
    triple = KGTriple(
        source_id=uuid4(),
        relationship_type=RelationshipTypes.RETURNS,
        target_id=uuid4(),
    )
    flag = AmbiguityFlag(
        reason="Uncertain about return type",
        flagged_triple=triple,
        suggested_action="Re-analyze with more context"
    )
    assert flag.reason == "Uncertain about return type"
    assert flag.flagged_triple == triple
    assert isinstance(flag.flagged_triple, KGTriple)

def test_analysis_report_creation():
    """Tests successful creation of an AnalysisReport."""
    report = AnalysisReport(file_path="/path/to/file.py", status="SUCCESS")
    assert report.file_path == "/path/to/file.py"
    assert report.status == "SUCCESS"
    assert report.nodes == []
    assert report.initial_triples == []
    assert report.ambiguity_queue == []

def test_refinement_report_creation():
    """Tests successful creation of a RefinementReport."""
    report = RefinementReport(summary="Resolved 2 of 3 ambiguities.")
    assert report.summary == "Resolved 2 of 3 ambiguities."
    assert report.resolved_triples == []
    assert report.unresolved_flags == []