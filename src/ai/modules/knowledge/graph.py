from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple


class KnowledgeGraph:
    """
    Lightweight in-memory knowledge graph with labeled, directed edges.

    Nodes carry free-form attributes. Edges are kept in two adjacency lists (outgoing and
    incoming) so both "what does X use" and "who uses X" are O(degree).
    """
    def __init__(self) -> None:
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._out: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        self._in: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        self._edge_set: Set[Tuple[str, str, str]] = set()

    # --- nodes ---
    def add_node(self, node_id: str, **attributes) -> str:
        """Adds or updates a node; attributes are merged."""
        node = self._nodes.setdefault(node_id, {})
        if attributes:
            node.update(attributes)
        return node_id

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        return self._nodes.get(node_id)

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def nodes(self) -> Dict[str, Dict[str, Any]]:
        return self._nodes

    # --- edges ---
    def add_relation(self, src: str, relation: str, dst: str) -> Tuple[str, str, str]:
        """Adds a directed, labeled edge (created nodes when missing). Duplicates are ignored."""
        edge = (src, relation, dst)
        if edge in self._edge_set:
            return edge
        self.add_node(src)
        self.add_node(dst)
        self._out[src].append((relation, dst))
        self._in[dst].append((relation, src))
        self._edge_set.add(edge)
        return edge

    def get_relations(self, src: Optional[str] = None) -> List[Tuple[str, str, str]]:
        """Edges as (src, relation, dst); all edges, or only those leaving ``src``."""
        if src is None:
            return [(s, rel, d) for s, edges in self._out.items() for rel, d in edges]
        return [(src, rel, d) for rel, d in self._out.get(src, [])]

    def get_neighbors(self, node_id: str, relation: Optional[str] = None) -> List[str]:
        """Targets of edges leaving node_id (optionally only one relation)."""
        return [d for rel, d in self._out.get(node_id, []) if relation is None or rel == relation]

    def get_incoming(self, node_id: str, relation: Optional[str] = None) -> List[str]:
        """Sources of edges arriving at node_id (optionally only one relation)."""
        return [s for rel, s in self._in.get(node_id, []) if relation is None or rel == relation]

    def edges_out(self, node_id: str) -> List[Tuple[str, str]]:
        return list(self._out.get(node_id, []))

    def edges_in(self, node_id: str) -> List[Tuple[str, str]]:
        return list(self._in.get(node_id, []))

    def find_path(self, src: str, dst: str, max_depth: int = 5) -> Optional[List[str]]:
        """Breadth-first search for a path from src to dst up to max_depth steps."""
        if src == dst:
            return [src]
        visited = {src}
        queue = deque([(src, [src], 0)])
        while queue:
            current, path, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for _, neighbor in self._out.get(current, []):
                if neighbor == dst:
                    return path + [dst]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor], depth + 1))
        return None

    def to_dot(self) -> str:
        """Graphviz DOT representation of the graph."""
        lines = ["digraph KnowledgeGraph {", '  node [shape=ellipse];']
        for node_id in self._nodes:
            lines.append(f'  "{node_id}";')
        for src, rel, dst in self.get_relations():
            lines.append(f'  "{src}" -> "{dst}" [label="{rel}"];')
        lines.append("}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"KnowledgeGraph(nodes={len(self._nodes)}, edges={len(self._edge_set)})"
