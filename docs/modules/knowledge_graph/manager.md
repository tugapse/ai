## 1. Architectural Role
Orchestrates the multi-phase lifecycle of codebase knowledge extraction, iterative refinement of ambiguous relationships, and semantic/structural querying of a graph database.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `KnowledgeGraphManager` | Class | Primary controller for KG lifecycle (analysis, refinement, querying). |
| `__init__` | Method | Injects `db_client`, `llm_client`, and `vectorizer_client` into the instance. |
| `update_knowledge_from_files` | Method | Executes the high-level orchestration loop: initial analysis $\rightarrow$ iterative refinement $\rightarrow$ DB validation. |
| `analyze_file` | Method | Reads source code and invokes LLM-based extraction to produce `AnalysisReport`. |
| `refine_knowledge` | Method | Iteratively resolves `AmbiguityFlag` objects by querying the DB for context and re-evaluating via LLM. |
| `query_graph` | Method | Public entry point for `semantiic_search` (vector-based) and `structural_query` (direct DB execution). |
| `_generate_initial_triples_with_llm` | Method | Internal logic to transform raw source code into `KGNode` and `KGTriple` objects via LLM. |
| `_create_and_store_embedding` | Method | Generates vector embeddings for `KGNode` and persists them to the database. |

## 3. Execution Logic & Flow
- **Initialization**: An instance is created by binding three external clients: a database client, an LLM client, and a vectorizer client.
- **Data Path**: 
    1. **Extraction**: `file_paths` $\rightarrow$ `analyze_file` $\rightarrow$ `_generate_initial_triples_with_llm` $\rightarrow$ `AnalysisReport` (Nodes, Triples, Ambiguities).
    2. **Persistence (Initial)**: `AnalysisReport` $\rightarrow$ `db_client.add_nodes` and `db_client.add_triples`.
    3. **Refinement**: `AmbiguityFlag` $\rightarrow$ `refine_knowledge` $\rightarrow$ `db_client.execute_query` (Context Retrieval) $\rightarrow$ `llm_client.chat.completions.create` $\rightarrow$ `RefinementReport` (Resolved/Unresolved).
    4. **Finalization**: `RefinementReport` $\rightarrow$ `db_client.mark_resolved_triples_as_validated`.
    5. **Querying**: `query_text` $\rightarrow$ `vectorizer_client.encode` $\rightarrow$ `db_client.find_similar_nodes` $\rightarrow$ `KGNode` list.
- **Conditional Branching**:
    - **Refinement Loop**: Continues while `master_ambiguity_queue` is non-empty AND `current_pass` < `max_refinement_passes`.
    - **LLM Response Parsing**: Checks `is_resolved` boolean to decide whether to update a triple or re-queue an ambiguity flag.
    - **Query Routing**: Branches logic based on `query_type` (`semantiic_search` vs `structural_query`).
    - **Error Handling**: Catches `FileNotFoundError` and generic `Exception` during file analysis and LLM processing to prevent total pipeline failure.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `json`, `typing` (`Any`, `List`, `Dict`, `Tuple`), `uuid` (`UUID`).
- **Internal Modules**: `.ast_parser` (`get_parser`), `.prompts` (`CODE_EXTRACTION_PROMPT`), `.models` (`AnalysisReport`, `AmbiguityFlag`, `RefinementReport`, `KGNode`, `KGEdge`, `KGTriple`, `NodeTypes`, `RelationshipTypes`).
- **External Packages**: Implicitly requires an OpenAI-compatible LLM client and a vectorizer client (e.g., `sentence-transformers` style).

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `max_refinement_passes = 10`
    - `model = "gpt-4-turbo"`
    - `confidence_score = 0.9` (initial placeholder)
    - `temperature = 0.0`
- **Environment Lookups**: None explicitly present in this file.