## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| KnowledgeGraph | ai/modules/knowledge_graph/graph |

This component implements a lightweight, in-memory graph data structure designed to model entities (nodes) and their relationships (labeled edges). Its primary responsibility is to provide CRUD-like operations for nodes and relationships, enabling graph traversal, neighbor discovery, and pathfinding within the stored data.

It functions as a core data model service within the application architecture. It encapsulates the graph logic, allowing other services, such as those interacting with [VectorMemory](/ai/modules/knowledge_graph/graph.md) via the [Bridge](/ai/modules/knowledge_graph/graph.md), to query structured knowledge representations.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `KnowledgeGraph` | Class | Manages nodes and edges. Methods include `add_node`, `get_node`, `add_relation`, `get_neighbors`, and `find_path`. |
| `VectorMemory` | Class | Simple in-memory store for key-value vector pairs. Methods include `add_vector` and `get_vector`. |
| `GetVectorMemoryProvider` | Class | Singleton provider ensuring only one instance of `VectorMemory` is accessible. |
| `Bridge` | Class | Acts as an orchestrator interface, exposing module services like the vector memory provider. |
| `KnowledgeGraph.add_node` | Method | Adds or updates a node given an ID and optional attributes. Returns the node ID. |
| `KnowledgeGraph.get_node` | Method | Retrieves the attributes dictionary for a specified node ID. Returns `None` if not found. |
| `KnowledgeGraph.has_node` | Method | Checks for the existence of a node by its ID. Returns a boolean. |
| `KnowledgeGraph.add_relation` | Method | Adds a directed, labeled edge from a source to a destination. Creates nodes if they don't exist. Returns the added edge tuple. |
| `KnowledgeGraph.get_relations` | Method | Returns all edges, optionally filtered by a source node ID. Returns a list of (src, relation, dst) tuples. |
| `KnowledgeGraph.get_neighbors` | Method | Returns connected neighbor IDs from a given node, optionally filtering by relation type. |
| `KnowledgeGraph.find_path` | Method | Performs a BFS to find the shortest path between two nodes up to a specified depth. Returns a list of node IDs or `None`. |
| `KnowledgeGraph.to_dot` | Method | Generates a string representation of the graph in Graphviz DOT format. |
| `KnowledgeGraph.register_with_orchestrator` | Method | Returns a `Bridge` instance to register the graph service with an orchestrator bus. |
| `VectorMemory.add_vector` | Method | Inserts or updates a vector associated with a unique key. |
| `VectorMemory.get_vector` | Method | Retrieves a vector based on its key. Returns `None` if the key is missing. |
| `VectorMemory.as_dict` | Method | Returns a copy of the entire internal vector storage as a dictionary. |
| `GetVectorMemoryProvider.__call__` | Method | Provides the singleton instance of `VectorMemory`. |
| `Bridge.expose` | Method | Returns a dictionary mapping service names to callable service providers. |

## 3. Implementation Details & Side Effects
- **Core Logic:** `KnowledgeGraph` uses an adjacency list (`_edges`) and a dictionary (`_nodes`) to store graph data. Pathfinding utilizes a standard Breadth-First Search (BFS) algorithm implemented with `collections.deque`. `VectorMemory` uses a simple dictionary lookup for O(1) average time complexity on vector retrieval. The `Bridge` pattern implements the Singleton pattern via `GetVectorMemoryProvider` to ensure service consistency.

- **Side Effects:** The component mutates its internal state (`_nodes` and `_edges` in `KnowledgeGraph`, `_vectors` in `VectorMemory`) when nodes or relations are added. The `to_dot` method generates a string representation, which is a pure transformation. The `Bridge` registration is designed to interact with an external orchestrator bus, though the bus interaction itself is deferred.

- **Error Handling:** `KnowledgeGraph.get_node` and `KnowledgeGraph.get_neighbors` gracefully handle non-existent nodes by returning `None` or empty lists, respectively, preventing runtime errors. `find_path` returns `None` if the target is unreachable within the specified depth.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `collections`, `typing`
- **Internal:** [KnowledgeGraph](/ai/modules/knowledge_graph/graph.md), [VectorMemory](/ai/modules/knowledge_graph/graph.md), [Bridge](/ai/modules/knowledge_graph/graph.md)