## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| Knowledge Graph Models | ai/modules/knowledge_graph/models.md |

This component defines the core data structures necessary for representing a Knowledge Graph (KG) within the system. It provides standardized schemas for nodes, relationships (edges), and the resulting triples that form the graph structure. By enforcing these models using Pydantic, it ensures data integrity and consistency across the entire graph processing pipeline.

This module serves as the foundational data model layer for the knowledge extraction subsystem. It dictates the structure for inputs from file analysis ([AnalysisReport](/ai/modules/knowledge_graph/models.md)), the resulting graph elements ([KGNode](/ai/modules/knowledge_graph/models.md), [KGEdge](/ai/modules/knowledge_graph/models.md)), and the iterative refinement process ([RefinementReport](/ai/modules/knowledge_graph/models.md)).

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| NodeTypes | Enum | Enumeration for the different types of nodes in the Knowledge Graph. |
| RelationshipTypes | Enum | Enumeration for the different types of relationships (edges) in the Knowledge Graph. |
| KGNode | Class | Represents a node (entity) in the Knowledge Graph. |
| KGEdge | Class | Represents an edge (relationship) between two nodes in the Knowledge Graph. |
| KGTriple | Class | Represents a single Subject-Predicate-Object statement for processing. |
| AmbiguityFlag | Class | Flags a triple that the LLM was uncertain about for later re-evaluation. |
| AnalysisReport | Class | The output of analyzing a single file, containing extracted graph components. |
| RefinementReport | Class | The output of the knowledge refinement process for a set of ambiguities. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The classes primarily serve as data containers defined by Pydantic models. `UUID` generation is handled via `default_factory=uuid4` for automatic, unique identification upon instantiation. The structures are designed to hold graph elements (nodes, edges, triples) and the state of the extraction/refinement process.

- **Side Effects:** None. The models are purely declarative data structures.

- **Error Handling:** None. Pydantic handles validation errors upon instantiation.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `enum`, `uuid`, `typing`, `pydantic`.
- **Internal:** None.