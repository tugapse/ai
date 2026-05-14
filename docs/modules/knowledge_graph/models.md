## 1. Architectural Role

**Functional Mission**
The **models.py** component serves as the foundational data schema definition layer for the Knowledge Graph module. Its primary mission is to provide a strictly typed, validated structure for representing entities (nodes), relationships (edges), and the analytical lifecycle of graph construction, including ambiguity handling and refinement reporting.

**System Context & Integration**
This component acts as the "source of truth" for data structures used throughout the knowledge extraction pipeline. It provides the schemas that the [ast_parser](/docs/modules/knowledge_graph/ast_parser.md) populates and that the [manager](/docs/modules/knowledge_graph/manager.md) orchestrates. By defining standardized `KGTriple` and `AmbiguityFlag` objects, it enables a feedback loop where uncertain extractions can be passed to LLMs for refinement, eventually resulting in a structured [graph](/docs/modules/knowledge_graph/graph.md).

## 2. Environment & Configuration
**Environment Lookups:**
No environment lookups identified.

**Hardcoded Constants:**
No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `NodeTypes` | Enum | Defines valid categories for graph nodes (e.g., FILE, CLASS, FUNCTION). |
| `RelationshipTypes` | Enum | Defines valid types of connections between nodes (e.g., CALLS, CONTAINS). |
| `KGNode` | Class | Represents a discrete entity within the graph with unique UUID and properties. |
| `KGEdge` | Class | Represents a directed relationship between a source and target node. |
| `KGTriple` | Class | A lightweight Subject-Predicate-Object structure used for processing and scoring. |
| `AmbiguityFlag` | Class | Encapsulates uncertainty data for triples requiring LLM re-evaluation. |
| `AnalysisReport` | Class | Aggregates nodes, triples, and ambiguities resulting from a single file analysis. |
| `RefinementReport` | Class | Summarizes the outcome of resolving previously flagged ambiguities. |

## 4. Execution Logic & Flow
Direct exports or structural definitions only; no internal logic flow.

## 5. Resource Dependencies
- **Standard Libraries**: `enum`, `uuid`, `typing`
- **Internal Modules**: 
    - [models](/docs/modules/knowledge_graph/models.md) (Self-reference via module context)
- **External Packages**: `pydantic` (imported as `pydantic`)