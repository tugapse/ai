## 1. Architectural Role
This file serves as the fundamental data schema definition layer for the Knowledge Graph subsystem. It establishes the strictly typed structural primitivesnodes, edges, and triplesrequired to represent code semantics and relationships. By utilizing `pydantic` models, it provides the validation framework for data flowing between the [modules/knowledge_graph/ast_parser.md](modules/knowledge_graph/ast_parser.md) and the [modules/knowledge_graph/manager.md](modules/knowledge_graph/manager.md), while also defining the reporting structures for analysis and ambiguity resolution processes.

## 2. Environment & Configuration
**Environment Lookups:**
No environment lookups identified.

**Hardcoded Constants:**
- `NodeTypes` (Enum)  Categorical definitions for semantic entities (FILE, CLASS, etc.).
- `RelationshipTypes` (Enum)  Categorical definitions for directed edges (CONTAINS, CALLS, etc.).

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `NodeTypes` | Enum | Defines the set of valid entity types allowed within the graph. |
| `RelationshipTypes` | Enum | Defines the set of valid semantic connections between nodes. |
| `KGNode` | Class | Data model for a single entity, including metadata and properties. |
| `KGEdge` | Class | Data model for a direct connection between two specific `KGNode` IDs. |
| `KGTriple` | Class | Lightweight Subject-Predicate-Object structure used for processing and scoring. |
| `AmbiguityFlag` | Class | Container for uncertainty metadata when LLM extraction is inconclusive. |
| `AnalysisReport` | Class | Aggregated result schema for a single file's semantic extraction. |
| `RefinementReport` | Class | Aggregated result schema for resolving flagged ambiguities. |

## 4. Execution Logic & Flow
- **Initialization**: Models are initialized via `pydantic.BaseModel` with default factories (e.g., `uuid4` for IDs, empty dicts/lists for collections).
- **Data Path**: 
    - **Extraction Phase**: `ast_parser` $\rightarrow$ `KGNode`/`KGEdge` $\rightarrow$ `KGTriple` $\rightarrow$ `AnalysisReport`.
    - **Uncertainty Phase**: Low confidence `KGTriple` $\rightarrow$ `AmbiguityFlag` $\rightarrow$ `AnalysisReport.ambiguity_queue`.
    - **Refinement Phase**: `AmbiguityFlag` $\rightarrow$ LLM Re-evaluation $\rightarrow$ `RefinementReport`.
- **Conditional Branching**: None; this file is a purely declarative schema definition module.

## 5. Resource Dependencies
- **Standard Libraries**: `enum`, `uuid`, `typing`
- **Internal Modules**: 
    - [modules/knowledge_graph/models.md](modules/knowledge_graph/models.md)
- **External Packages**: `pydantic`