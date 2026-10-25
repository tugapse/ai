## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | KnowledgeGraphManager |
| Source file | manager.py |

The **KnowledgeGraphManager** serves as the central orchestrator for the lifecycle of the codebase's semantic knowledge representation. It manages the complex transition from raw source code to a structured, validated, and searchable graph of entities and relationships.

**Functional Mission**
The primary responsibility of the **KnowledgeGraphManager** is to automate the extraction, refinement, and querying of a Knowledge Graph (KG) from source files. It solves the problem of maintaining an accurate, high-fidelity semantic map of a codebase by implementing a multi-phase pipeline: initial LLM-driven extraction, iterative ambiguity resolution through graph-contextualized refinement, and vector-enhanced semantic querying.

**System Context & Integration**
This component acts as the bridge between raw file data and the structured intelligence stored in the graph database. It consumes source code and utilizes an LLM to generate initial nodes and triples, which are then persisted via a `db_client`. It integrates deeply with the refinement loop, where it uses the `db_client` to fetch context for ambiguous data points, feeding that context back into the `llm_client` to achieve higher confidence scores. Downstream, it provides a unified interface for semantic and structural queries, enabling other modules to perform RAG (Retrieval-Augmented Generation) or structural analysis using the enriched graph data.

- **INTERNAL REFERENCES**: 
    - [KnowledgeGraphManager](/docs/ai/modules/knowledge_graph/manager.md)
    - [AnalysisReport](/docs/ai/modules/knowledge_graph/models.md)
    - [AmbiguityFlag](/docs/ai/modules/knowledge_graph/models.md)
    - [RefinementReport](/docs/ai/modules/knowledge_graph/models.md)
    - [KGNode](/docs/ai/modules/knowledge_graph/models.md)
    - [KGEdge](/docs/ai/modules/knowledge_graph/models.md)
    - [KGTriple](/docs/ai/modules/knowledge_graph/models.md)
    - [NodeTypes](/docs/ai/modules/knowledge_graph/models.md)
    - [RelationshipTypes](/docs/ai/modules/knowledge_graph/models.md)
    - [CODE_EXTRACTION_PROMPT](/docs/ai/modules/knowledge_graph/prompts.md)

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `max_refinement_passes` (Default: `10`)  Safety threshold to prevent infinite loops during the ambiguity resolution phase.
- `model` (Default: `"gpt-4-turbo"`)  The specific LLM model used for extraction and refinement tasks.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `KnowledgeGraphManager` | Class | Orchestrates KG creation, refinement, and querying. |
| `update_knowledge_from_files` | Method | Executes the full pipeline: analysis, DB persistence, and iterative refinement. |
| `analyze_file` | Method | Performs single-file extraction of nodes and triples using an LLM. |
| `refine_knowledge` | Method | Resolves ambiguities by providing graph context to the LLM for re-evaluation. |
| `query_graph` | Method | Public API for `semantic_search` (vector-based) and `structural_query` (graph-based). |
| `_generate_initial_triples_with_llm` | Method | Internal LLM logic to parse code into structured JSON triples and nodes. |
| `_create_and_store_embedding` | Method | Generates and persists vector embeddings for `KGNode` entities. |

## 4. Execution Logic & Flow
- **Initialization**: The manager is instantiated with three injected dependencies: `db_client` (graph storage), `llm_client` (intelligence), and `vectorizer_client` (embedding generation).
- **Data Path (Update Pipeline)**:
    1. **Extraction**: `update_knowledge_from_files` iterates through paths $\rightarrow$ `analyze_file` $\rightarrow$ `_generate_initial_triples_with_llm` $\rightarrow$ `AnalysisReport`.
    2. **Initial Persistence**: Nodes and unvalidated triples are sent to `db_client`.
    3. **Refinement Loop**: `master_ambiguity_queue` is processed by `refine_knowledge`.
    4. **Contextual Re-evaluation**: For each ambiguity, `db_client.execute_query` fetches node details $\rightarrow$ Prompt is constructed with context $\rightarrow$ `llm_client` returns resolution $\rightarrow$ `resolved_triples` are updated.
    5. **Finalization**: `db_client.mark_resolved_triples_as_validated()` is called to finalize the state.
- **Conditional Branching**:
    - **Refinement Limit**: The `while` loop terminates if `master_ambiguity_queue` is empty OR `current_pass` reaches `max_refinement_passes`.
    - **LLM Response Validation**: In `_generate_initial_triples_with_llm`, malformed JSON or invalid `RelationshipTypes` are caught and skipped to prevent pipeline crashes.
    - **Query Routing**: `query_graph` branches logic based on `query_type` (`semantic_search` vs `structural_query`).

## 5. Resource Dependencies
- **Standard Libraries**: `json`, `typing`
- **Internal Modules**: 
    - [get_parser](/docs/ai/modules/knowledge_graph/ast_parser.md)
    - [CODE_EXTRACTION_PROMPT](/docs/ai/modules/knowledge_graph/prompts.md)
    - [AnalysisReport](/docs/ai/modules/knowledge_graph/models.md)
    - [AmbiguityFlag](/docs/ai/modules/knowledge_graph/models.md)
    - [RefinementReport](/docs/ai/modules/knowledge_graph/models.md)
    - [KGNode](/docs/ai/modules/knowledge_graph/models.md)
    - [KGEdge](/docs/ai/modules/knowledge_graph/models.md)
    - [KGTriple](/docs/ai/modules/knowledge_graph/models.md)
    - [NodeTypes](/docs/ai/modules/knowledge_graph/models.md)
    - [RelationshipTypes](/docs/ai/modules/knowledge_graph/models.md)
- **External Packages**: None explicitly imported (assumes injected clients follow specific interfaces).