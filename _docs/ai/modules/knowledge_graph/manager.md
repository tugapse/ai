## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| KnowledgeGraphManager | /ai/modules/knowledge_graph/manager.md |

This component, `KnowledgeGraphManager`, is the central orchestration layer for managing the entire lifecycle of the codebase knowledge graph. Its primary responsibility is to take raw source code files, systematically extract structured knowledge (nodes and triples), iteratively refine uncertain extractions, and persist the final, validated graph into a database.

It acts as a high-level service coordinating multiple specialized sub-systems. It relies heavily on external clients for data persistence ([db\_client]), large language model interaction ([llm\_client]), and vector embedding generation ([vectorizer\_client]), fitting into the application architecture as the primary Knowledge Graph Service.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `KnowledgeGraphManager.__init__` | Constructor | Initializes the manager with dependency-injected clients for database, LLM, and vectorization services. |
| `KnowledgeGraphManager.update_knowledge_from_files` | Method | Orchestrates the end-to-end KG update process, covering initial extraction, iterative refinement, and final persistence from a list of file paths. |
| `KnowledgeGraphManager.analyze_file` | Method | Analyzes a single file, extracting initial triples and identifying any ambiguities using the LLM. |
| `KnowledgeGraphManager.refine_knowledge` | Method | Processes a batch of ambiguity flags by querying the graph context and re-evaluating the uncertainty using the LLM. |
| `KnowledgeGraphManager.query_graph` | Method | Provides a public interface to retrieve data from the KG, supporting both vector-based semantic search and structural database queries. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The system operates in a multi-phase pipeline. Phase 1 involves iterating over files to perform initial extraction via LLM calls, populating an ambiguity queue. Phase 2 is a refinement loop where the queue is iteratively processed, using the DB context to inform the LLM about uncertain triples until the queue is empty or a safety limit is hit. Finally, Phase 3 persists the validated data. Semantic querying involves encoding the query text into a vector and performing a similarity search against stored node embeddings.

- **Side Effects:** The code interacts heavily with external systems: it reads from the filesystem (`open(file_path)`), makes network calls to the LLM API (`self.llm_client.chat.completions.create`), and performs read/write operations to the graph database (`self.db_client.*`).

- **Error Handling:** File I/O errors are caught in `analyze_file` and result in an `AnalysisReport` with an "error\_file\_not\_found" status. LLM processing errors (JSON decoding, API failures) are caught in `_generate_initial_triples_with_llm` and result in the associated ambiguity flag being added to the unresolved list. Structural query errors are caught in `query_graph`.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `json`, `typing`
- **Internal:** [ai/modules/knowledge_graph/ast_parser](/ai/modules/knowledge_graph/ast_parser.md), [ai/modules/knowledge_graph/prompts](/ai/modules/knowledge_graph/prompts.md), [ai/modules/knowledge_graph/models](/ai/modules/knowledge_graph/models.md)