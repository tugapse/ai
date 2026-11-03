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
        """Initializes the KnowledgeGraph with empty node and edge storage."""
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._edges: Dict[str, List[Tuple[str, str]]] = defaultdict(list)

    def add_node(self, node_id: str, **attributes) -> str:
        """
        Add or update a node with optional attributes.

        Args:
            node_id: The unique identifier for the node.
            **attributes: Arbitrary key-value pairs to store as node attributes.

        Returns:
            The node_id that was added or updated.
        """
        if node_id not in self._nodes:
            self._nodes[node_id] = {}
        if attributes:
            self._nodes[node_id].update(attributes)
        return node_id

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the attributes dictionary for a given node ID.

        Args:
            node_id: The ID of the node to retrieve.

        Returns:
            A dictionary containing the node's attributes, or None if the node does not exist.
        """
        return self._nodes.get(node_id)

    def has_node(self, node_id: str) -> bool:
        """
        Checks if a node with the given ID exists in the graph.

        Args:
            node_id: The ID of the node to check.

        Returns:
            True if the node exists, False otherwise.
        """
        return node_id in self._nodes

    def add_relation(self, src: str, relation: str, dst: str) -> Tuple[str, str, str]:
        """
        Add a directed, labeled edge from src to dst. If nodes do not exist, they are created.

        Args:
            src: The source node ID.
            relation: The label describing the relationship (e.g., "IS_A", "HAS_PART").
            dst: The destination node ID.

        Returns:
            A tuple representing the added edge: (source, relation, destination).
        """
        if src not in self._nodes:
            self.add_node(src)
        if dst not in self._nodes:
            self.add_node(dst)
        self._edges[src].append((relation, dst))
        return (src, relation, dst)

    def get_relations(self, src: Optional[str] = None) -> List[Tuple[str, str, str]]:
        """
        Return a list of edges as (src, relation, dst).

        Args:
            src: If provided, only returns edges originating from this source node.
            
        Returns:
            A list of tuples, where each tuple is (source_id, relation_label, destination_id).
        """
        if src is None:
            out: List[Tuple[str, str, str]] = []
            for s, edges in self._edges.items():
                for rel, dst in edges:
                    out.append((s, rel, dst))
            return out
        else:
            return [(src, rel, dst) for rel, dst in self._edges.get(src, [])]

    def get_neighbors(self, node_id: str, relation: Optional[str] = None) -> List[str]:
        """
        Return neighbor node IDs connected from node_id. Optionally filter by relation.

        Args:
            node_id: The ID of the node whose neighbors are sought.
            relation: If provided, only neighbors connected by this specific relation are returned.

        Returns:
            A list of neighbor node IDs.
        """
        edges = self._edges.get(node_id, [])
        if relation is None:
            return [dst for _, dst in edges]
        else:
            return [dst for rel, dst in edges if rel == relation]

    def find_path(self, src: str, dst: str, max_depth: int = 5) -> Optional[List[str]]:
        """
        Breadth-first search for a path from src to dst up to max_depth steps.

        Args:
            src: The starting node ID.
            dst: The target node ID.
            max_depth: The maximum number of steps allowed in the path. Defaults to 5.

        Returns:
            A list of node IDs representing the path from src to dst, or None if no path is found within max_depth.
        """
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
        """
        Render a Graphviz DOT representation of the graph.

        Returns:
            A string containing the DOT language definition of the graph.
        """
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
        """
        Returns a string representation of the KnowledgeGraph, showing node and edge counts.
        """
        return f"KnowledgeGraph(nodes={len(self._nodes)}, edges={sum(len(v) for v in self._edges.values())})"

    def register_with_orchestrator(self, bus: Any = None) -> "Bridge":
        """
        Register the module with the orchestrator bus by returning a Bridge instance.

        Args:
            bus: The orchestrator bus object (optional).

        Returns:
            An instance of the Bridge class.
        """
        return Bridge(bus)


class VectorMemory:
    """
    A simple in-memory vector store for storing key-value pairs of vectors.
    """
    def __init__(self) -> None:
        """Initializes the VectorMemory with an empty vector storage."""
        self._vectors: Dict[str, List[float]] = {}

    def add_vector(self, key: str, vector: List[float]) -> None:
        """
        Adds or updates a vector associated with a specific key.

        Args:
            key: The unique identifier for the vector.
            vector: The list of floats representing the vector data.
        """
        self._vectors[key] = vector

    def get_vector(self, key: str) -> Optional[List[float]]:
        """
        Retrieves the vector associated with the given key.

        Args:
            key: The unique identifier of the vector to retrieve.

        Returns:
            The vector (List[float]) if found, otherwise None.
        """
        return self._vectors.get(key)

    def as_dict(self) -> Dict:
        """
        Returns a copy of the entire internal vector storage as a dictionary.

        Returns:
            A dictionary mapping keys to their corresponding vectors.
        """
        return self._vectors.copy()


class GetVectorMemoryProvider:
    """
    Callable provider for the vector memory service, ensuring a singleton instance.
    """
    def __init__(self) -> None:
        """Initializes the provider, setting the instance to None."""
        self._instance: Optional[VectorMemory] = None

    def __call__(self) -> VectorMemory:
        """
        Provides the singleton instance of VectorMemory.

        Returns:
            The shared instance of VectorMemory.
        """
        if self._instance is None:
            self._instance = VectorMemory()
        return self._instance


class Bridge:
    """
    Orchestrator bridge for the KnowledgeGraph module, exposing its services.
    """
    def __init__(self, bus: Any = None) -> None:
        """
        Initializes the bridge, linking to the orchestrator bus and setting up memory providers.

        Args:
            bus: The orchestrator bus object to register with.
        """
        self.bus = bus
        self._memory_provider = GetVectorMemoryProvider()

    def expose(self) -> Dict[str, Any]:
        """
        Expose module services to the orchestrator by returning a dictionary of callable services.

        Returns:
            A dictionary containing service access points, such as the vector memory provider.
        """
        return {
            "get_vector_memory": self._memory_provider
        }