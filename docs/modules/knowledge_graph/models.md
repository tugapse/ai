## 1. Architectural Role
Defines the core data schemas and type enumerations for representing entities, relationships, and analysis reports within the Knowledge Graph.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `NodeTypes` | Enum | Categorizes nodes into specific semantic types (e.g., `FILE`, `CLASS`, `FUNCTION`). |
| `RelationshipTypes` | Enum | Defines the semantic nature of edges connecting nodes (e.g., `CONTAINS`, `CALLS`). |
| `KGNode` | Class | Represents a discrete entity with a unique `UUID`, type, name, and metadata. |
| `KGEdge` | Class | Represents a directed connection between two `UUID` identifiers with a specific type. |
| `KGTriple` | Class | A lightweight Subject-Predicate-Object structure used for processing relationship statements. |
| `AmbiguityFlag` | Class | Captures uncertainty metadata and suggested actions for unresolved triples. |
| `AnalysisReport` | Class | Aggregates nodes, initial triples, and ambiguity flags resulting from a single file analysis. |
| `RefinementReport` | Class | Summarizes the outcome of a refinement process, including resolved and unresolved items. |

## 3. Execution Logic & Flow
- **Initialization**: 
    - Enums (`NodeTypes`, `RelationshipTypes`) are loaded into memory to provide strict type validation.
    - `BaseModel` inheritance prepares the schema for automated validation and serialization.
- **Data Path**: 
    - **Input**: Raw data or dictionaries passed to class constructors.
    - **Processing**: `pydantic` (via `pydantic` import) validates input against defined types, enforces `UUID` generation via `default_factory`, and populates `properties` dictionaries.
    - **Output**: Validated, type-safe object instances or serialized JSON-compatible structures.
- **Conditional Branching**: 
    - Logic is implicitly handled by the `BaseModel` validation layer; if input data does not match the specified `NodeTypes` or `RelationshipTypes`, a validation error is raised.

## 4. Resource Dependencies
- **Standard Libraries**: `enum`, `uuid`, `typing`
- **Internal Modules**: None
- **External Packages**: `pydantic` (imported as `pydantic` via `from pydantic import BaseModel, Field`)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `__all__` export list defining the public API.
    - Default `confidence_score` of `1.0` in `KGTriple`.
- **Environment Lookups**: None