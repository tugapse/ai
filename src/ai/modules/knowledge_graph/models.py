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
    """Represents a node (entity) in the Knowledge Graph."""
    id: UUID = Field(default_factory=uuid4)
    type: NodeTypes
    name: str
    source_text: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)

class KGEdge(BaseModel):
    """Represents an edge (relationship) between two nodes in the Knowledge Graph."""
    id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    target_id: UUID
    type: RelationshipTypes
    properties: Dict[str, Any] = Field(default_factory=dict)

class KGTriple(BaseModel):
    """Represents a single Subject-Predicate-Object statement for processing."""
    source_id: UUID
    relationship_type: RelationshipTypes
    target_id: UUID
    confidence_score: float = 1.0

class AmbiguityFlag(BaseModel):
    """Flags a triple that the LLM was uncertain about for later re-evaluation."""
    reason: str
    flagged_triple: KGTriple
    suggested_action: str

class AnalysisReport(BaseModel):
    """The output of analyzing a single file."""
    file_path: str
    nodes: List[KGNode] = Field(default_factory=list)
    initial_triples: List[KGTriple] = Field(default_factory=list)
    ambiguity_queue: List[AmbiguityFlag] = Field(default_factory=list)
    status: str

class RefinementReport(BaseModel):
    """The output of the knowledge refinement process for a set of ambiguities."""
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