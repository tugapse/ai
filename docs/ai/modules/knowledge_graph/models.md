## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | models.py |
| Source file | models.py |

The **models.py** component serves as the foundational data schema layer for the Knowledge Graph module. It defines the structural integrity of all entities (nodes), relationships (edges), and analytical outputs used to represent code intelligence within the system. By utilizing Pydantic models, it ensures strict type validation and serialization capabilities for complex graph structures.

**Functional Mission**
The primary responsibility of **models.py** is to provide a standardized, type-safe vocabulary for representing semantic information extracted from source code. It solves the problem of data inconsistency by enforcing specific enumerations for node types and relationship types, ensuring that any component interacting with the Knowledge Graph adheres to a predictable schema.

**System Context & Integration**
This component acts as the data contract between the extraction logic (such as [ast_parser](/docs/ai/modules/knowledge_graph/ast_parser.md)) and the graph management layer ([graph](/docs/ai/modules/knowledge_graph/graph.md) and [manager](/docs/ai/modules/knowledge_graph/manager.md)). It facilitates the transition of raw analysis data into structured [AnalysisReport](/docs/ai/modules/knowledge_graph/models.md) objects, which are then processed or refined. The models defined here are essential for the downstream storage and querying of semantic relationships within the broader AI intelligence framework.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `NodeTypes` | Enum | Defines valid categories for graph nodes (e.g., FILE, CLASS, FUNCTION). |
| `RelationshipTypes` | Enum | Defines valid semantic connections between nodes (e.g., CALLS, INHERITS_FROM). |
| `KGNode` | Class | Represents a discrete entity in the graph with unique UUID and metadata. |
| `KGEdge` | Class | Represents a directed relationship between a source and target node. |
| `KGTriple` | Class | A lightweight Subject-Predicate-Object structure used for processing logic. |
| `AmbiguityFlag` | Class | Encapsulates uncertainty data for LLM-driven refinement processes. |
| `AnalysisReport` | Class | Aggregates nodes, triples, and ambiguities resulting from a file analysis. |
| `RefinementReport` | Class | Summarizes the results of resolving flagged ambiguities. |

## 4. Execution Logic & Flow
Direct exports or structural definitions only; no internal logic flow.

## 5. Resource Dependencies
- **Standard Libraries**: `enum`, `uuid`, `typing`
- **Internal Modules**: 
    - No internal module imports identified within this file.
- **External Packages**: `pydantic`