## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Knowledge Graph Module** | [src/ai/modules/knowledge_graph/graph.py](/src/ai/modules/knowledge_graph/graph.py) |

This component provides a lightweight, in-memory implementation of a labeled knowledge graph and a companion vector memory system. It is designed to store structured relational data (nodes and edges) and unstructured high-dimensional data (vectors), enabling the system to maintain complex relationships between entities and perform similarity-based lookups.

The module serves as a foundational data layer within the AI architecture, specifically supporting semantic reasoning and long-term memory retrieval. It provides the structural backbone for the knowledge graph services, allowing the agent to traverse relationships between concepts and retrieve associated vector embeddings via the `Bridge` pattern for orchestrator integration.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `KnowledgeGraph` | Class | Manages a directed graph of nodes with attributes and labeled edges. |
| `KnowledgeGraph.add_node(node_id, **attributes)` | Method | Adds or updates a node with arbitrary metadata. Returns `node_id`. |
| `KnowledgeGraph.get_node(node_id)` | Method | Retrieves the attribute dictionary for a specific node. |
| `KnowledgeGraph.has_node(node_id)` | Method | Checks for the existence of a node. |
| `KnowledgeGraph.add_relation(src, relation, dst)` | Method | Creates a directed edge between two nodes, creating them if necessary. |
| `KnowledgeGraph.get_relations(src=None)` | Method | Returns a list of all edges or edges originating from a specific source. |
| `KnowledgeGraph.get_neighbors(node_id, relation=None)` | Method | Returns adjacent node IDs, optionally filtered by a specific relation label. |
| `KnowledgeGraph.find_path(src, dst, max_depth=5)` | Method | Performs a Breadth-First Search (BFS) to find a path between two nodes. |
| `KnowledgeGraph.to_dot()` | Method | Generates a Graphviz DOT string representation of the graph. |
| `KnowledgeGraph.register_with_orchestrator(bus=None)` | Method | Returns a `Bridge` instance to connect the graph to the system orchestrator. |
| `VectorMemory` | Class | An in-memory key-value store for mapping strings to lists of floats (vectors). |
| `VectorMemory.add_vector(key, vector)` | Method | Stores or updates a vector associated with a key. |
| `VectorMemory.get_vector(key)` | Method | Retrieves a vector by its key. |
| `VectorMemory.as_dict()` | Method | Returns a copy of the internal vector storage. |
| `GetVectorMemoryProvider` | Class | A singleton provider for accessing the `VectorMemory` instance. |
| `Bridge` | Class | An orchestrator bridge that exposes the module's services (like vector memory) to the system bus. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - The `KnowledgeGraph` uses an adjacency list (`defaultdict(list)`) to store edges, where each edge is a tuple of `(relation_label, destination_id)`. 
    - Pathfinding is implemented using a Breadth-First Search (BFS) algorithm with a configurable `max_depth` to prevent infinite loops or excessive computation in large graphs.
    - `VectorMemory` acts as a simple dictionary-based wrapper for high-dimensional data.
    - The `GetVectorMemoryProvider` implements the Singleton pattern via the `__call__` magic method to ensure all parts of the system share the same memory instance.
- **Side Effects:** This module is entirely in-memory. It does not perform any I/O operations, network calls, or filesystem mutations. All data is lost when the process terminates.
- **Error Handling:** The module uses safe retrieval methods (e.g., `.get()`) to return `None` when nodes or vectors are not found, rather than raising exceptions.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** 
    - `collections.defaultdict`
    - `collections.deque`
    - `typing` (Dict, List, Tuple, Optional, Any)
- **Internal:** 
    - No internal module imports are present in this specific file.