## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Knowledge Graph Models** | [src/ai/modules/knowledge_graph/models.py](/AgentDocs/ai/modules/knowledge_graph/models.md) |

This component defines the fundamental data structures and schema for the Knowledge Graph (KG) system. It provides the strongly-typed models required to represent entities (nodes), their relationships (edges), and the semantic triples used during the extraction and refinement processes.

The models serve as the primary data contract for the knowledge extraction pipeline. They are utilized by the [ast_parser](/AgentDocs/ai/modules/knowledge_graph/ast_parser.md) to structure code analysis, by the [manager](/AgentDocs/ai/modules/knowledge_graph/manager.md) to orchestrate graph updates, and by the [graph](/AgentDocs/ai/modules/knowledge_graph/graph.md) to maintain the structural integrity of the extracted codebase intelligence.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `NodeTypes` | Enum | Defines valid entity types: `FILE`, `CLASS`, `FUNCTION`, `METHOD`, `VARIABLE`, `PARAMETER`, `IMPORT`, `TYPE`. |
| `RelationshipTypes` | Enum | Defines valid edge types: `CONTAINS`, `DEFINES`, `CALLS`, `INSTANTIATES`, `INHERITS_FROM`, `HAS_PARAMETER`, `RETURNS`, `HAS_TYPE`, `IMPORTS`. |
| `KGNode` | Class | Pydantic model representing a graph node with a unique UUID, type, name, and metadata properties. |
| `KGEdge` | Class | Pydantic model representing a directed relationship between two nodes via their UUIDs. |
| `KGTriple` | Class | A lightweight Subject-Predicate-Object representation used for processing and scoring relationship confidence. |
| `AmbiguityFlag` | Class | A container for triples that failed confidence thresholds, including a reason and suggested resolution action. |
| `AnalysisReport` | Class | The structured output of a file analysis, aggregating extracted nodes, initial triples, and any flagged ambiguities. |
| `RefinementReport` | Class | The structured output of the refinement process, detailing resolved triples and remaining unresolved flags. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The module uses `pydantic.BaseModel` to enforce strict type validation and schema enforcement for all graph components. It utilizes `default_factory` patterns (e.g., `uuid4` for IDs and empty dicts for properties) to ensure that every instantiated model is valid and self-contained upon creation.
- **Side Effects:** Structural definitions only; no complex logic or side effects.
- **Error Handling:** Relies on Pydantic's built-in validation logic. Any attempt to instantiate these models with incorrect types (e.g., an invalid `NodeTypes` string) will trigger a `ValidationError`.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `enum`, `uuid`, `typing`, `pydantic`.
- **Internal:** None.