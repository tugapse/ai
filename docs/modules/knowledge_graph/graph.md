## 1. Architectural Role
Provides a lightweight, in-memory graph data structure for relational knowledge storage and a corresponding vector memory provider for orchestrator integration.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `KnowledgeGraph` | Class | Manages a directed graph of nodes (with attributes) and labeled edges using adjacency lists. |
| `KnowledgeGraph.add_node` | Method | Creates or updates a node entry in the `_nodes` dictionary with provided attributes. |
| `KnowledgeGraph.get_node` | Method | Retrieves attributes for a specific `node_id`. |
| `KnowledgeGraph.has_node` | Method | Validates existence of a `node_id`. |
| `KnowledgeGraph.add_relation` | Method | Creates a directed edge between two nodes, auto-initializing nodes if absent. |
| `KnowledgeGraph.get_relations` | Method | Returns all edges or filters edges originating from a specific `src`. |
| `KnowledgeGraph.get_neighbors` | Method | Returns adjacent node IDs, optionally filtered by a specific `relation` label. |
| `KnowledgeGraph.find_path` | Method | Executes a Breadth-First Search (BFS) to find a node path within a `max_depth`. |
| `KnowledgeGraph.to_dot` | Method | Generates a Graphviz DOT string representation of the graph structure and attributes. |
| `KnowledgeGraph.register_with_orchestrator` | Method | Returns a `Bridge` instance to facilitate module registration. |
| `VectorMemory` | Class | Stores and retrieves high-dimensional vectors indexed by string keys. |
| `GetVectorMemoryProvider` | Class | Implements a singleton-pattern provider via `__call__` to supply `VectorMemory` instances. |
| `Bridge` | Class | Acts as an interface between the module and the orchestrator, exposing the vector memory provider. |

## 3. Execution Logic & Flow
- **Initialization**: 
    - `KnowledgeGraph`: Instantiates empty `_nodes` (Dict) and `_edges` (defaultdict of lists).
    - `VectorMemory`: Instantiates an empty `_vectors` (Dict).
    - `GetVectorMemoryProvider`: Initializes `_instance` as `None`.
    - `Bridge`: Initializes `bus` and an instance of `GetVectorMemoryProvider`.
- **Data Path**:
    - **Graph Insertion**: `node_id` + `attributes` $\rightarrow$ `_nodes` update $\rightarrow$ `add_relation(src, rel, dst)` $\rightarrow$ `_edges[src]` append $\rightarrow$ Graph state updated.
    - **Pathfinding**: `src` $\rightarrow$ `deque` queueing $\rightarrow$ BFS traversal $\rightarrow$ neighbor check $\rightarrow$ `visited` set update $\rightarrow$ `path` accumulation $\rightarrow$ `dst` found or `max_depth` reached.
    - **Vector Storage**: `key` + `vector` $\rightarrow$ `_vectors` assignment.
    - **Orchestrator Exposure**: `Bridge.expose()` $\rightarrow$ returns dictionary containing the `GetVectorMemoryProvider` callable.
- **Conditional Branching**:
    - `KnowledgeGraph.get_relations`: Checks if `src` is `None` to decide between returning all edges or filtered edges.
    - `KnowledgeGraph.get_neighbors`: Checks if `relation` is `None` to decide between returning all neighbors or relation-specific neighbors.
    - `KnowledgeGraph.find_path`: Checks if `src == dst` (immediate return) and monitors `depth >= max_depth` to prune search.
    - `GetVectorMemoryProvider.__call__`: Checks if `_instance` is `None` to decide whether to instantiate a new `VectorMemory` or return the existing singleton.

## 4. Resource Dependencies
- **Standard Libraries**: `collections.defaultdict`, `collections.deque`, `typing.Dict`, `typing.List`, `typing.Tuple`, `typing.Optional`, `typing.Any`.

## 5. Configuration & Environment
- **Hardcoded Constants**: `max_depth=5` (default parameter in `find_path`).