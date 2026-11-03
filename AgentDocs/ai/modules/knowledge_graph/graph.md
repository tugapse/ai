## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Knowledge Graph Module** | [src/ai/modules/knowledge_graph/graph.py](/AgentDocs/ai/modules/knowledge_graph/graph.md) |

The `graph.py` module provides a lightweight, in-memory implementation of a labeled knowledge graph and a supporting vector memory system. It is designed to store structured relationships between entities (nodes) via directed, labeled edges, allowing for complex relational queries and pathfinding within an AI agent's cognitive architecture.

This component serves as a foundational data layer for the knowledge graph module. It provides the primitive structures required to represent semantic networks and offers a `Bridge` class to facilitate integration with an orchestrator bus, enabling the module's services to be exposed to the broader system.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `KnowledgeGraph` | Class | A graph structure supporting nodes with attributes, labeled directed edges, and BFS-based pathfinding. |
| `KnowledgeGraph.add_node()` | Method | Adds or updates a node with arbitrary attributes. Returns `node_id`. |
| `KnowledgeGraph.get_node()` | Method | Retrieves the attribute dictionary for a specific `node_id`. |
| `KnowledgeGraph.has_node()` | Method | Returns `True` if the node exists. |
| `KnowledgeGraph.add_relation()` | Method | Creates a directed edge between two nodes, creating them if they do not exist. |
| `KnowledgeGraph.get_relations()` | Method | Returns a list of all edges or edges originating from a specific `src` node. |
| `KnowledgeGraph.get_neighbors()` | Method | Returns a list of neighbor IDs, optionally filtered by a specific relation label. |
| `KnowledgeGraph.find_path()` | Method | Performs a Breadth-First Search (BFS) to find a path between two nodes up to a `max_depth`. |
| `KnowledgeGraph.to_dot()` | Method | Generates a Graphviz DOT string representation of the graph. |
| `KnowledgeGraph.register_with_orchestrator()` | Method | Returns a `Bridge` instance to register the module with an orchestrator. |
| `VectorMemory` | Class | An in-memory key-value store for high-dimensional float vectors. |
| `VectorMemory.add_vector()` | Method | Stores or updates a vector associated with a specific key. |
| `VectorMemory.get_vector()` | Method | Retrieves a vector by its key. |
| `GetVectorMemoryProvider` | Class | A singleton provider that returns a shared `VectorMemory` instance via `__call__`. |
| `Bridge` | Class | An orchestrator bridge used to expose module services (like vector memory) to the system bus. |
| `Bridge.expose()` | Method | Returns a dictionary of callable services for orchestrator consumption. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **Graph Storage:** Uses a dictionary (`_nodes`) for node attributes and a `defaultdict` of lists (`_edges`) for the adjacency list.
    - **Pathfinding:** Implements a Breadth-First Search (BFS) algorithm using `collections.deque` to find the shortest path between nodes within a specified depth limit.
    - **Vector Storage:** Uses a simple dictionary mapping string keys to lists of floats.
    - **Singleton Pattern:** `GetVectorMemoryProvider` implements a singleton pattern to ensure all parts of the module interact with the same `VectorMemory` instance.
- **Side Effects:** All storage is strictly in-memory. There are no filesystem or network side effects.
- **Error Handling:** The `find_path` method returns `None` if no path is found within the `max_depth`. Node retrieval via `get_node` returns `None` if the ID is invalid.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** 
    - `collections` (specifically `defaultdict` and `deque`)
    - `typing` (for type hinting)
- **Internal:** 
    - No direct internal module imports are present in this file, though it is designed to be used within the [src/ai/modules/knowledge_graph/](/AgentDocs/ai/modules/knowledge_graph/) ecosystem.