## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **KnowledgeGraphManager** | [src/ai/modules/knowledge_graph/manager.py](/AgentDocs/ai/modules/knowledge_graph/manager.md) |

The `KnowledgeGraphManager` is responsible for the end-to-end lifecycle of the codebase knowledge graph. It orchestrates the extraction of structured information from source files, manages an iterative refinement process to resolve ambiguities identified during extraction, and provides interfaces for both semantic and structural querying of the resulting graph.

This component acts as a high-level controller within the knowledge graph module. It integrates LLM capabilities for intelligent parsing and refinement with graph database persistence and vectorization services to build a high-fidelity representation of code relationships and entities.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `KnowledgeGraphManager` | Class | The primary orchestrator for KG creation, refinement, and querying. |
| `update_knowledge_from_files(file_paths: List[str])` | Method | Orchestrates a multi-stage update: initial extraction, iterative refinement of ambiguities, and final persistence to the DB. |
| `analyze_file(file_path: str)` | Method | Performs single-file analysis to extract nodes, initial triples, and identify ambiguities via LLM. Returns an `AnalysisReport`. |
| `refine_knowledge(ambiguities: List[AmbiguityFlag])` | Method | Processes a batch of ambiguities by querying existing graph context and using an LLM to resolve or update triples. Returns a `RefinementReport`. |
| `query_graph(query_type: str, params: Dict[str, Any])` | Method | Public interface for retrieving data. Supports `semantic_search` (vector-based) and `structural_query` (graph-based). |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **Extraction:** Uses an LLM with a specialized prompt (`CODE_EXTRACTION_PROMPT`) to transform raw source code into a JSON-structured set of nodes and triples.
    - **Refinement Loop:** Implements a "Global Refinement Loop" that runs up to 10 passes. It attempts to resolve `AmbiguityFlag` objects by providing the LLM with the specific flagged triple and the context retrieved from the database via `GET_NODE_DETAILS_BY_ID`.
    - **Semantic Search:** Converts text queries into embeddings using an injected `vectorizer_client` and performs similarity searches via the `db_client`.
- **Side Effects:** 
    - **Network/API:** Makes multiple calls to an LLM API (e.g., `gpt-4-turbo`) for extraction and refinement.
    - **Database:** Performs multiple write operations to the graph database, including adding nodes, adding unvalidated triples, and marking triples as validated.
    - **Filesystem:** Reads source code files from the local filesystem.
- **Error Handling:** 
    - Uses `try-except` blocks to catch file access errors, JSON parsing errors from LLM responses, and database/network failures.
    - Failed analyses return an `AnalysisReport` with error statuses rather than raising unhandled exceptions, allowing the batch process to continue.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No direct environment variables are accessed within this file; configuration is expected to be handled by the injected clients.

**Module Dependencies:**
- **Standard/External:** `json`, `typing`.
- **Internal:**
    - [get_parser](/AgentDocs/ai/modules/knowledge_graph/ast_parser.md)
    - [CODE_EXTRACTION_PROMPT](/AgentDocs/ai/modules/knowledge_graph/prompts.md)
    - [AnalysisReport](/AgentDocs/ai/modules/knowledge_graph/models.md)
    - [AmbiguityFlag](/AgentDocs/ai/modules/knowledge_graph/models.md)
    - [RefinementReport](/AgentDocs/ai/modules/knowledge_graph/models.md)
    - [KGNode](/AgentDocs/ai/modules/knowledge_graph/models.md)
    - [KGEdge](/AgentDocs/ai/modules/knowledge_graph/models.md)
    - [KGTriple](/AgentDocs/ai/modules/knowledge_graph/models.md)
    - [NodeTypes](/AgentDocs/ai/modules/knowledge_graph/models.md)
    - [RelationshipTypes](/AgentDocs/ai/modules/knowledge_graph/models.md)