from __future__ import annotations
from enum import Enum
from uuid import UUID, uuid4
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class NodeTypes(str, Enum):
    """Enumeration for the different types of nodes in the Knowledge Graph."""
    FILE = "FILE"
    CLASS = "CLASS"
    FUNCTION = "FUNCTION"
    METHOD = "METHOD"
    VARIABLE = "VARIABLE"
    PARAMETER = "PARAMETER"
    IMPORT = "IMPORT"
    TYPE = "TYPE"

class RelationshipTypes(str, Enum):
    """Enumeration for the different types of relationships (edges) in the Knowledge Graph."""
    CONTAINS = "CONTAINS"
    DEFINES = "DEFINES"
    CALLS = "CALLS"
    INSTANTIATES = "INSTANTIATES"
    INHERITS_FROM = "INHERITS_FROM"
    HAS_PARAMETER = "HAS_PARAMETER"
    RETURNS = "RETURNS"
    HAS_TYPE = "HAS_TYPE"
    IMPORTS = "IMPORTS"

class KGNode(BaseModel):
    """
    Represents a node (entity) in the Knowledge Graph.

    Attributes:
        id (UUID): A unique identifier for the node.
        type (NodeTypes): The type of the entity (e.g., FILE, CLASS).
        name (str): The name of the entity.
        source_text (Optional[str]): The original text snippet where the entity was found.
        properties (Dict[str, Any]): Additional metadata or properties associated with the node.
    """
    id: UUID = Field(default_factory=uuid4)
    type: NodeTypes
    name: str
    source_text: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)

class KGEdge(BaseModel):
    """
    Represents an edge (relationship) between two nodes in the Knowledge Graph.

    Attributes:
        id (UUID): A unique identifier for the edge.
        source_id (UUID): The ID of the starting node.
        target_id (UUID): The ID of the ending node.
        type (RelationshipTypes): The type of relationship connecting the two nodes.
        properties (Dict[str, Any]): Additional metadata or properties associated with the edge.
    """
    id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    target_id: UUID
    type: RelationshipTypes
    properties: Dict[str, Any] = Field(default_factory=dict)

class KGTriple(BaseModel):
    """
    Represents a single Subject-Predicate-Object statement for processing.

    Attributes:
        source_id (UUID): The ID of the subject node.
        relationship_type (RelationshipTypes): The type of relationship (predicate).
        target_id (UUID): The ID of the object node.
        confidence_score (float): The confidence level assigned to this triple (default is 1.0).
    """
    source_id: UUID
    relationship_type: RelationshipTypes
    target_id: UUID
    confidence_score: float = 1.0

class AmbiguityFlag(BaseModel):
    """
    Flags a triple that the LLM was uncertain about for later re-evaluation.

    Attributes:
        reason (str): The reason why the LLM flagged the triple as ambiguous.
        flagged_triple (KGTriple): The specific triple that requires review.
        suggested_action (str): A suggested course of action for resolving the ambiguity.
    """
    reason: str
    flagged_triple: KGTriple
    suggested_action: str

class AnalysisReport(BaseModel):
    """
    The output of analyzing a single file, containing extracted graph components.

    Attributes:
        file_path (str): The path to the file that was analyzed.
        nodes (List[KGNode]): A list of all nodes extracted from the file.
        initial_triples (List[KGTriple]): The set of triples initially derived from the file.
        ambiguity_queue (List[AmbiguityFlag]): A list of triples flagged for further review.
        status (str): The overall processing status of the file analysis.
    """
    file_path: str
    nodes: List[KGNode] = Field(default_factory=list)
    initial_triples: List[KGTriple] = Field(default_factory=list)
    ambiguity_queue: List[AmbiguityFlag] = Field(default_factory=list)
    status: str

class RefinementReport(BaseModel):
    """
    The output of the knowledge refinement process for a set of ambiguities.

    Attributes:
        resolved_triples (List[KGTriple]): Triples that were successfully resolved during refinement.
        unresolved_flags (List[AmbiguityFlag]): Triples that remain ambiguous after refinement attempts.
        summary (str): A summary of the refinement process outcomes.
    """
    resolved_triples: List[KGTriple] = Field(default_factory=list)
    unresolved_flags: List[AmbiguityFlag] = Field(default_factory=list)
    summary: str

__all__ = [
    "NodeTypes",
    "RelationshipTypes",
    "KGNode",
    "KGEdge",
    "KGTriple",
    "AmbiguityFlag",
    "AnalysisReport",
    "RefinementReport",
]