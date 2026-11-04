## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Knowledge Graph Models** | [src/ai/modules/knowledge_graph/models.py](/src/ai/modules/knowledge_graph/models.py) |

This component defines the fundamental data structures and schema for the Knowledge Graph (KG) system. It provides a standardized way to represent entities (nodes), their relationships (edges), and the semantic triples that form the basis of the graph-based intelligence layer.

The models are designed to facilitate the extraction of code intelligence from source files, allowing the system to transform raw code into a structured, queryable graph. It serves as the data contract between the extraction logic (such as the AST parser) and the graph management logic, ensuring consistency in how code entities like classes, functions, and variables are stored and related.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `NodeTypes` | Enum | Defines valid categories for graph nodes (e.g., `FILE`, `CLASS`, `FUNCTION`, `IMPORT`). |
| `RelationshipTypes` | Enum | Defines valid connection types between nodes (e.g., `CONTAINS`, `CALLS`, `DEFINES`). |
| `KGNode` | Class | A Pydantic model representing a single entity in the graph with a unique UUID, type, name, and metadata. |
| `KGEdge` | Class | A Pydantic model representing a directed relationship between two `KGNode` entities. |
| `KGTriple` | Class | A lightweight representation of a Subject-Predicate-Object statement used for processing and confidence scoring. |
| `AmbiguityFlag` | Class | A container for triples that require human or LLM re-evaluation due to uncertainty. |
| `AnalysisReport` | Class | The structured output of a file analysis process, containing extracted nodes, triples, and any flagged ambiguities. |
| `RefinementReport` | Class | The structured output of a refinement process, detailing resolved and unresolved ambiguities. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The module utilizes `pydantic` for strict data validation and schema enforcement. It uses `uuid4` to ensure that every node and edge generated during the extraction process has a globally unique identifier. The data models are optimized for a "triple-store" approach where complex relationships are decomposed into simple `KGTriple` objects for easier LLM processing and refinement.
- **Side Effects:** None. This is a pure data modeling module.
- **Error Handling:** Validation errors are handled by `pydantic` during instantiation if the provided data does not conform to the defined types (e.g., invalid `NodeTypes` or missing required fields).

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `enum`, `uuid`, `typing`, `pydantic`.
- **Internal:** None.