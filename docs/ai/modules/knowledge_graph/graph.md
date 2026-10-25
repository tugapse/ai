## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | KnowledgeGraph |
| Source file | graph.py |

The **KnowledgeGraph** component serves as a specialized data structure for managing structured, relational information within the AI's cognitive architecture. It provides a mechanism to store entities (nodes) and their semantic relationships (labeled edges), enabling the system to perform graph-based reasoning and pathfinding.

**Functional Mission**
The primary responsibility of this file is to provide a lightweight, in-memory implementation of a directed, labeled knowledge graph and an associated vector memory provider. It solves the problem of maintaining explicit relational context that is often lost in pure vector-based retrieval, allowing the system to traverse connections between concepts via the **KnowledgeGraph** class.

**System Context & Integration**
This component acts as a structured memory layer. While the `VectorMemory` class provides high-dimensional similarity search, the `KnowledgeGraph` provides topological connectivity. The `Bridge` class facilitates integration with the broader system orchestrator, specifically exposing the `VectorMemory` through a provider pattern. This allows downstream modules, such as those managed by [Agent Orchestrator](/docs/ai/agents/agent_orchestrator.md), to access both semantic and relational data to enhance context retrieval.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `max_depth` (Default: `5`)  Limits the depth of the Breadth-First Search (BFS) during pathfinding to prevent infinite loops or excessive computation.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `KnowledgeGraph` | Class | Manages nodes, labeled edges, and graph traversal logic. |
| `add_node` | Method | Creates or updates a node with arbitrary metadata. |
| `add_relation` | Method | Establishes a directed edge between two nodes with a specific relation label. |
| `get_neighbors` | Method | Retrieves adjacent nodes, optionally filtered by a specific relation type. |
| `find_path` | Method | Executes a BFS to find the shortest path between two nodes within a depth limit. |
| `to_dot` | Method | Serializes the graph into Graphviz DOT format for visualization. |
| `VectorMemory` | Class | A simple key-value store for high-dimensional floating-point vectors. |
| `GetVectorMemoryProvider` | Class | A singleton-pattern provider that ensures a single `VectorMemory` instance is shared. |
| `Bridge` | Class | Acts as the interface between this module and the system orchestrator/bus. |

## 4. Execution Logic & Flow
- **Initialization**: 
    - `KnowledgeGraph` initializes an empty dictionary for `_nodes` and a `defaultdict` of lists for `_edges`.
    - `VectorMemory` initializes an empty dictionary for `_vectors`.
    - `Bridge` initializes a `GetVectorMemoryProvider` instance.
- **Data Path (Graph Insertion)**: 
    - `add_relation(src, relation, dst)` $\rightarrow$ Checks if `src` and `dst` exist $\rightarrow$ Calls `add_node` if missing $\rightarrow$ Appends `(relation, dst)` to the `_edges[src]` list.
- **Data Path (Pathfinding)**: 
    - `find_path(src, dst)` $\rightarrow$ Initializes a `deque` with `(src, [src], 0)` $\rightarrow$ Pops current node $\rightarrow$ Iterates through neighbors $\rightarrow$ If neighbor is `dst`, returns path $\rightarrow$ If neighbor is unvisited and `depth < max_depth`, adds to queue $\rightarrow$ Returns `None` if no path found.
- **Conditional Branching**:
    - `get_relations`: If `src` is `None`, performs a full graph scan; otherwise, performs a targeted lookup for the specific node.
    - `get_neighbors`: If `relation` is provided, filters the adjacency list; otherwise, returns all destination nodes.

## 5. Resource Dependencies
- **Standard Libraries**: `collections` (`defaultdict`, `deque`), `typing` (`Dict`, `List`, `Tuple`, `Optional`, `Any`).
- **Internal Modules**: 
    - No direct imports from other files are present in the source, though it is designed to interface with [Agent Orchestrator](/docs/ai/agents/agent_orchestrator.md) via the `Bridge`.
- **External Packages**: None identified.