## 1. Architectural Role

**Functional Mission**
The **KnowledgeGraphManager** serves as the central orchestrator for the lifecycle of the codebase's semantic representation. Its primary mission is to transform raw source code into a structured, validated, and searchable knowledge graph by coordinating LLM-driven extraction, iterative ambiguity refinement, and database persistence.

**System Context & Integration**
This component acts as a high-level controller that bridges raw file data with the persistent graph storage. It consumes file paths to trigger an analysis pipeline that utilizes [ast_parser](/docs/modules/knowledge_graph/ast_parser.md) (conceptually) and [prompts](/docs/modules/knowledge_graph/prompts.md) to generate nodes and triples. It manages the state transition of knowledge from "unvalidated" to "validated" through a refinement loop, interacting heavily with an injected `db_client` for storage and an `llm_client` for reasoning. The resulting graph is made available to the rest of the system via semantic and structural queries, facilitating advanced codebase intelligence.

## 2. Environment & Configuration

**Environment Lookups:**
No environment lookups identified.

**Hardcoded Constants:**
- `max_refinement_passes` (Default: `10`)  Safety threshold to prevent infinite loops during the ambiguity resolution phase.
- `model` (Default: `"gpt-4-turbo"`)  The specific LLM identifier used for extraction and refinement tasks.
- `confidence_score` (Default: `0.9`)  Initial placeholder value assigned to newly extracted triples.
- `temperature` (Default: `0.0`)  Deterministic setting for LLM calls to ensure consistent graph extraction.

## 3. Interface & API Surface

| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `KnowledgeGraphManager` | Class | Main controller for KG creation, refinement, and querying. |
| `update_knowledge_from_files` | Method | Orchestrates the multi-phase pipeline: initial analysis, refinement loop, and final validation. |
| `analyze_file` | Method | Performs single-file extraction of nodes and triples using LLM analysis. |
| `refine_knowledge` | Method | Resolves identified ambiguities by providing graph context to the LLM. |
| `query_graph` | Method | Public interface for semantic (vector-based) and structural (query-based) retrieval. |
| `_generate_initial_triples_with_llm` | Method | Internal logic for converting source code text into structured KG components. |
| `_create_and_store_embedding` | Method | Generates and persists vector embeddings for KG nodes. |

## 4. Execution Logic & Flow

- **Initialization**: The manager is instantiated with three dependency-injected clients: `db_client` (graph storage), `llm_client` (reasoning), and `vectorizer_client` (embeddings).
- **Data Path (Update Pipeline)**:
    1. **Phase 1 (Extraction)**: `update_knowledge_from_files` iterates through `file_paths` $\rightarrow$ `analyze_file` $\rightarrow$ `_generate_initial_triples_with_llm` $\rightarrow$ Returns `AnalysisReport` $\rightarrow$ Nodes/Triples are persisted to `db_client`.
    2. **Phase 2 (Refinement)**: `master_ambiguity_queue` is populated $\rightarrow$ `refine_knowledge` is called $\rightarrow$ LLM evaluates triples using `db_client` context $\rightarrow$ Resolved triples are updated; unresolved flags are re-queued.
    3. **Phase 3 (Finalization)**: `db_client.mark_resolved_triples_as_validated()` is called to finalize the state.
- **Conditional Branching**:
    - **Ambiguity Resolution**: If `reevaluated_data.get("is_resolved")` is `True`, the triple is updated and added to `resolved_triples`; otherwise, it is moved to `unresolved_flags`.
    - **Query Routing**: `query_graph` branches based on `query_type` between `"semantiic_search"` (utilizing `vectorizer_client`) and `"structural_query"` (utilizing `db_client.execute_query`).
    - **Error Handling**: `analyze_file` catches `FileNotFoundError` and general `Exception` to return specific error statuses within an `AnalysisReport`.

## 5. Resource Dependencies

- **Standard Libraries**: `os`, `json`, `typing` (Any, List, Dict, Tuple), `uuid` (UUID)
- **Internal Modules**: 
    - [ast_parser](/docs/modules/knowledge_graph/ast_parser.md)
    - [prompts](/docs/modules/knowledge_graph/prompts.md)
    - [models](/docs/modules/knowledge_graph/models.md)
- **External Packages**: None identified (assumes injected clients follow specific interfaces).