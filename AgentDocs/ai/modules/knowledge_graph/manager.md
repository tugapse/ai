## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **KnowledgeGraphManager** | [src/ai/modules/knowledge_graph/manager.py](/src/ai/modules/knowledge_graph/manager.py) |

The `KnowledgeGraphManager` is responsible for the end-to-end lifecycle of the codebase knowledge graph. It orchestrates the extraction of structured information (nodes and triples) from source files, manages an iterative refinement process to resolve ambiguities identified during extraction, and provides interfaces for both semantic and structural querying of the resulting graph.

This component acts as a high-level controller within the knowledge graph module. It integrates LLM capabilities for reasoning, a vectorizer for semantic search, and a database client for persistence, effectively bridging raw source code with a structured, queryable intelligence layer.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `KnowledgeGraphManager` | Class | The primary orchestrator for KG creation, refinement, and querying. |
| `__init__(db_client, llm_client, vectorizer_client)` | Constructor | Initializes the manager with injected clients for database, LLM, and vectorization operations. |
| `update_knowledge_from_files(file_paths: List[str])` | Method | Performs a multi-stage update: initial extraction, iterative refinement of ambiguities, and final database validation. |
| `analyze_file(file_path: str)` | Method | Analyzes a single file to extract initial nodes and triples, returning an `AnalysisReport`. |
| `refine_knowledge(ambiguities: List[AmbiguityFlag])` | Method | Processes a batch of ambiguities by querying graph context and using an LLM to resolve or update triples. |
| `query_graph(query_type: str, params: Dict[str, Any])` | Method | Provides a public interface for `semantic_search` (vector-based) or `structural_query` (graph-based) operations. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **Extraction:** Uses an LLM with a specialized prompt to parse source code into `KGNode` and `KGTriple` objects. It utilizes an internal cache during a single file's analysis to prevent duplicate node creation.
    - **Refinement Loop:** Implements a "Global Refinement Loop" that runs up to 10 passes. It attempts to resolve `AmbiguityFlag` objects by providing the LLM with the flagged triple and context retrieved from the database via `GET_NODE_DETAILS_BY_ID`.
    - **Semantic Search:** Converts text queries into embeddings using the `vectorizer_client` and performs similarity searches via the `db_client`.
- **Side Effects:** 
    - **Network:** Performs multiple outbound calls to an LLM API (e.g., GPT-4 Turbo) and potentially a vectorization service.
    - **Database:** Writes nodes and triples to the graph database; updates node properties with embeddings; marks triples as validated.
    - **Filesystem:** Reads source code files from the provided paths.
- **Error Handling:** 
    - Catches `FileNotFoundError` during file analysis, returning a report with a specific error status.
    - Uses broad `Exception` catching during LLM processing and database operations to ensure the refinement loop or batch updates can continue even if individual items fail.
    - Validates LLM JSON responses to prevent crashes on malformed data.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables are explicitly required by this module; it relies on the injected clients being pre-configured.

**Module Dependencies:**
- **Standard/External:** `json`, `typing`.
- **Internal:**
    - [ai.modules.knowledge_graph.ast_parser](/AgentDocs/ai/modules/knowledge_graph/ast_parser.md)
    - [ai.modules.knowledge_graph.prompts](/AgentDocs/ai/modules/knowledge_graph/prompts.md)
    - [ai.modules.knowledge_graph.models](/AgentDocs/ai/modules/knowledge_graph/models.md)