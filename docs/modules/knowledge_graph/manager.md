## 1. Architectural Role
The `KnowledgeGraphManager` acts as the central orchestrator for the codebase knowledge extraction lifecycle. It manages the transition from raw source code to a structured graph by coordinating initial LLM-based extraction, iterative refinement of ambiguous relationships, and semantic/structural querying. It serves as the bridge between raw file inputs, the [modules/knowledge_graph/ast_parser.md](modules/knowledge_graph/ast_parser.md) (fallback/enrichment), the [modules/knowledge_graph/prompts.md](modules/knowledge_graph/prompts.md) logic, and the persistence layer provided by the `db_client`.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `max_refinement_passes` (Default: `10`)  Safety threshold to prevent infinite loops during the global refinement phase.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `KnowledgeGraphManager` | Class | Primary controller for KG lifecycle (creation, refinement, querying). |
| `update_knowledge_from_files` | Func | Orchestrates the multi-phase pipeline: initial analysis $\rightarrow$ refinement loop $\rightarrow$ validation. |
| `analyze_file` | Func | Performs single-file extraction of nodes and triples using LLM analysis. |
| `refine_knowledge` | Func | Resolves `AmbiguityFlag` entities by querying graph context and re-evaluating with LLM. |
| `query_graph` | Func | Public interface for `semantiic_search` (vector-based) and `structural_query` (graph-based). |
| `_generate_initial_triples_with_llm` | Func | Internal method for LLM-driven code parsing and triple generation. |
| `_create_and_store_embedding` | Func | Generates and persists vector embeddings for `KGNode` instances. |

## 4. Execution Logic & Flow
- **Initialization**: Instantiates with injected `db_client`, `llm_client`, and `vectorizer_client`.
- **Data Path (Knowledge Update)**:
    1. **Input**: List of file paths.
    2. **Phase 1 (Analysis)**: `analyze_file` $\rightarrow$ `_generate_initial_triples_with_llm` $\rightarrow$ `LLM Response` $\rightarrow$ `AnalysisReport`.
    3. **Persistence (Partial)**: Nodes and unvalidated triples are pushed to `db_client`.
    4. **Phase 2 (Refinement)**: `master_ambiguity_queue` $\rightarrow$ `refine_knowledge` $\rightarrow$ `LLM Contextual Re-evaluation` $\rightarrow$ `Resolved Triples` / `Unresolved Flags`.
    5. **Phase 3 (Finalization)**: `db_client.mark_resolved_triples_as_validated()`.
    6. **Output**: Updated Knowledge Graph in database.
- **Conditional Branching**:
    - If `db_client` or `llm_client` is missing: Skips refinement or querying.
    - If `is_resolved` is `false` in refinement: Updates `AmbiguityFlag` reason and re-queues for next pass.
    - If `query_type` is unrecognized: Returns empty list.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `json`, `typing` (Any, List, Dict, Tuple), `uuid` (UUID).
- **Internal Modules**: 
    - [modules/knowledge_graph/ast_parser.md](modules/knowledge_graph/ast_parser.md)
    - [modules/knowledge_graph/prompts.md](modules/knowledge_graph/prompts.md)
    - [modules/knowledge_graph/models.md](modules/knowledge_graph/models.md)
- **External Packages**: None explicitly listed (assumes injected clients follow specific interfaces).