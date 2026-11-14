"""
The component knowledge contract.

One JSON document per source file, as produced by the ``code/extract-knowledge`` task
(assets/templates/user/task/code/extract-knowledge.md). Validation is permissive: unknown
fields are kept, everything except ``component.source_path`` is optional.
"""

import os
import re
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _Loose(BaseModel):
    model_config = ConfigDict(extra="allow")


class ComponentInfo(_Loose):
    name: str = ""
    source_path: str
    doc_path: str = ""
    type: str = "module"

    @field_validator("source_path")
    @classmethod
    def _not_empty(cls, v: str) -> str:
        if not v or not str(v).strip():
            raise ValueError("component.source_path is required")
        return str(v).strip()


class VectorInfo(_Loose):
    semantic_summary: str = ""


class GraphNode(_Loose):
    id: str = ""
    label: str = ""
    name: str = ""
    signature: str = ""


class GraphEdge(_Loose):
    source: str = ""
    target: str
    relation: str = "depends_on"


class ComponentMeta(_Loose):
    environment_variables: List[str] = Field(default_factory=list)
    external_dependencies: List[str] = Field(default_factory=list)
    has_side_effects: bool = False


class ComponentDoc(_Loose):
    component: ComponentInfo
    vector_memory: VectorInfo = Field(default_factory=VectorInfo)
    graph_nodes: List[GraphNode] = Field(default_factory=list)
    graph_edges: List[GraphEdge] = Field(default_factory=list)
    metadata: ComponentMeta = Field(default_factory=ComponentMeta)


def parse_component(data: Dict[str, Any]) -> ComponentDoc:
    """Validates one knowledge JSON document. Raises pydantic.ValidationError when invalid."""
    return ComponentDoc.model_validate(data)


def looks_like_component(data: Any) -> bool:
    """Cheap check used to tell knowledge JSON apart from other JSON files."""
    return isinstance(data, dict) and isinstance(data.get("component"), dict)


_EXT_RE = re.compile(r"\.[A-Za-z0-9]{1,6}$")


def path_key(path: str) -> str:
    """
    Normalizes a source/doc path to the key shared by code, knowledge JSON and docs.

    '/ai/agents/memory_manager.py', 'ai/agents/memory_manager.md' and
    'ai\\agents\\memory_manager' all become 'ai/agents/memory_manager'.
    """
    if not path:
        return ""
    p = str(path).strip().replace("\\", "/")
    p = p.split("#", 1)[0]
    if p.startswith("@ROOT"):
        p = p[len("@ROOT"):]
    while p.startswith("./"):
        p = p[2:]
    p = re.sub(r"/+", "/", p).strip("/")
    p = _EXT_RE.sub("", p)
    return p


def relative_key(path: str, root: str) -> str:
    """path_key of ``path`` relative to ``root`` (when it lives under it)."""
    try:
        rel = os.path.relpath(os.path.abspath(path), os.path.abspath(root))
        if not rel.startswith(".."):
            return path_key(rel)
    except ValueError:
        pass
    return path_key(path)
