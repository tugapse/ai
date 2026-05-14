from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any

class KnowledgeGraph:
    """
    Lightweight in-memory knowledge graph with labeled edges.
    Nodes are stored with optional attributes.
    Edges are stored as an adjacency list with relation labels.
    """
    def __init__(self) -> None:
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._edges: Dict[str, List[Tuple[str, str]]] = defaultdict(list)

    def add_node(self, node_id: str, **attributes) -> str:
        """Add or update a node with optional attributes."""
        if node_id not in self._nodes:
            self._nodes[node_id] = {}
        if attributes:
            self._nodes[node_id].update(attributes)
        return node_id

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        return self._nodes.get(node_id)

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def add_relation(self, src: str, relation: str, dst: str) -> Tuple[str, str, str]:
        """Add a directed, labeled edge from src to dst."""
        if src not in self._nodes:
            self.add_node(src)
        if dst not in self._nodes:
            self.add_node(dst)
        self._edges[src].append((relation, dst))
        return (src, relation, dst)

    def get_relations(self, src: Optional[str] = None) -> List[Tuple[str, str, str]]:
        """Return a list of edges as (src, relation, dst)."""
        if src is None:
            out: List[Tuple[str, str, str]] = []
            for s, edges in self._edges.items():
                for rel, dst in edges:
                    out.append((s, rel, dst))
            return out
        else:
            return [(src, rel, dst) for rel, dst in self._edges.get(src, [])]

    def get_neighbors(self, node_id: str, relation: Optional[str] = None) -> List[str]:
        """Return neighbor node IDs connected from node_id. Optionally filter by relation."""
        edges = self._edges.get(node_id, [])
        if relation is None:
            return [dst for _, dst in edges]
        else:
            return [dst for rel, dst in edges if rel == relation]

    def find_path(self, src: str, dst: str, max_depth: int = 5) -> Optional[List[str]]:
        """Breadth-first search for a path from src to dst up to max_depth steps."""
        if src == dst:
            return [src]
        from collections import deque
        visited = set([src])
        queue = deque([(src, [src], 0)])
        while queue:
            current, path, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for rel, neighbor in self._edges.get(current, []):
                if neighbor == dst:
                    return path + [dst]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor], depth + 1))
        return None

    def to_dot(self) -> str:
        """Render a Graphviz DOT representation of the graph."""
        lines = ["digraph KnowledgeGraph {"]
        lines.append('  node [shape=ellipse];')
        for node_id, attrs in self._nodes.items():
            label = node_id
            if attrs:
                attr_str = ", ".join(f"{k}={v}" for k, v in attrs.items())
                label = f"{node_id}\\n{attr_str}"
            lines.append(f'  "{node_id}" [label="{label}"];')
        for src, edges in self._edges.items():
            for rel, dst in edges:
                lines.append(f'  "{src}" -> "{dst}" [label="{rel}"];')
        lines.append("}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"KnowledgeGraph(nodes={len(self._nodes)}, edges={sum(len(v) for v in self._edges.values())})"

    def register_with_orchestrator(self, bus: Any = None) -> "Bridge":
        """Register the module with the orchestrator bus."""
        return Bridge(bus)


class VectorMemory:
    """A simple in-memory vector store."""
    def __init__(self):
        self._vectors: Dict[str, List[float]] = {}

    def add_vector(self, key: str, vector: List[float]):
        self._vectors[key] = vector

    def get_vector(self, key: str) -> Optional[List[float]]:
        return self._vectors.get(key)

    def as_dict(self) -> Dict:
        return self._vectors.copy()


class GetVectorMemoryProvider:
    """Callable provider for the vector memory service."""
    def __init__(self):
        self._instance: Optional[VectorMemory] = None

    def __call__(self) -> VectorMemory:
        if self._instance is None:
            self._instance = VectorMemory()
        return self._instance


class Bridge:
    """Orchestrator bridge for the KnowledgeGraph module."""
    def __init__(self, bus: Any = None):
        self.bus = bus
        self._memory_provider = GetVectorMemoryProvider()

    def expose(self) -> Dict[str, Any]:
        """Expose module services to the orchestrator."""
        return {
            "get_vector_memory": self._memory_provider
        }