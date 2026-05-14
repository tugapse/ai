## 1. Architectural Role
The file [graph.py](/home/fabio/Code/ai/src/ai/modules/knowledge_graph/graph.py) serves as the structural backbone for relational data storage and retrieval within the knowledge graph module. It provides a lightweight, in-memory implementation of a directed graph with labeled edges and node attributes, alongside a basic vector storage mechanism. It also implements the `Bridge` pattern to facilitate service exposure to the orchestrator, enabling the connection between graph-based relational data and vector-based semantic memory.

## 2. Environment & Configuration
**Environment Lookups:**
No environment lookups identified.

**Hardcoded Constants:**
- `max_depth` (Default: `5`)  Constraint for the Breadth-First Search pathfinding algorithm in `find_path`.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `KnowledgeGraph` | Class | Manages an in-memory directed graph consisting of nodes (with attributes) and labeled edges. |
| `add_node` | Method | Creates or updates a node with provided attribute dictionaries. |
| `get_node` | Method | Retrieves attributes for a specific node ID. |
| `add_relation` | Method | Establishes a directed, labeled edge between two nodes, auto-creating nodes if absent. |
| `get_relations` | Method | Returns all edges in the graph or filters edges originating from a specific node. |
| `get_neighbors` | Method | Retrieves adjacent node IDs, optionally filtered by a specific relation label. |
| `find_path` | Method | Executes a Breadth-First Search (BFS) to find the shortest path between two nodes within a depth limit. |
| `to_dot` | Method | Serializes the graph structure into a Graphviz DOT format string for visualization. |
| `register_with_orchestrator` | Method | Returns a `Bridge` instance to link the graph to the system bus. |
| `VectorMemory` | Class | Provides a simple key-value store for high-dimensional vector embeddings. |
| `GetVectorMemoryProvider` | Class | A singleton-pattern provider that returns the shared `VectorMemory` instance. |
| `Bridge` | Class | Acts as the integration layer that exposes `VectorMemory` services to the central orchestrator. |

## 4. Execution Logic & Flow
- **Initialization**: 
    - `KnowledgeGraph`: Initializes `_nodes` as an empty dictionary and `_edges` as a `defaultdict` of lists.
    - `VectorMemory`: Initializes `_vectors` as an empty dictionary.
    - `Bridge`: Initializes with an optional `bus` and an internal `GetVectorMemoryProvider`.
- **Data Path (Graph Construction)**: 
    - `add_relation(src, rel, dst)` $\rightarrow$ Checks existence of `src`/`dst` $\rightarrow$ Calls `add_node` if required $\rightarrow$ Appends `(relation, dst)` to `_edges[src]`.
- **Data Path (Pathfinding)**: 
    - `find_path(src, dst)` $\rightarrow$ Check `src == dst` $\rightarrow$ Initialize `deque` with `(src, [src], 0)` $\rightarrow$ Pop node $\rightarrow$ Check `depth < max_depth` $\rightarrow$ Iterate neighbors $\rightarrow$ If neighbor is `dst`, return path $\rightarrow$ Else, add to `visited` and `queue`.
- **Conditional Branching**:
    - `get_relations`: If `src` is `None`, iterates the entire adjacency list; otherwise, performs a targeted lookup.
    - `get_neighbors`: If `relation` is `None`, returns all neighbors; otherwise, applies a filter on the edge label.

## 5. Resource Dependencies
- **Standard Libraries**: `collections` (`defaultdict`, `deque`), `typing` (`Dict`, `List`, `Tuple`, `Optional`, `Any`).
- **Internal Modules**: 
    - None (Logic is self-contained within this file, though it acts as a provider for [modules/memory/vector_memory_module.md](/home/fabio/Code/ai/src/ai/modules/memory/vector_memory_module.md)).
- **External Packages**: None.