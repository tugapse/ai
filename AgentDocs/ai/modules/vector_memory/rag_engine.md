## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **RAG Engine** | [src/ai/modules/vector_memory/rag_engine.py](/AgentDocs/ai/modules/vector_memory/rag_engine.md) |

The RAG (Retrieval-Augmented Generation) Engine provides the logic necessary to ingest raw text into a vector database and retrieve semantically relevant context for LLM queries. It handles the lifecycle of document processing, including text chunking, embedding generation via Sentence Transformers, and persistent storage management using ChromaDB.

This component serves as a specialized layer within the vector memory subsystem. It bridges the gap between raw unstructured data and the retrieval capabilities provided by [vector_memory.py](/AgentDocs/ai/modules/vector_memory/vector_memory.md), enabling the agent to access external knowledge bases during inference.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `RAGChromaDBProvider` | Class | A specialized wrapper for `ChromaDBProvider` that ensures correct initialization for persistent RAG storage. |
| `RAGEmbeddingProvider` | Class | A specialized wrapper for `SentenceTransformerEmbeddingProvider` that loads a SentenceTransformer model for text-to-vector conversion. |
| `ingest_text(...)` | Function | Processes raw text by chunking it, generating embeddings, and upserting the resulting vectors and metadata into a ChromaDB collection. |
| `retrieve_context(...)` | Function | Performs a semantic search against a ChromaDB collection and returns a filtered, ranked list of context chunks based on similarity and token limits. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **Chunking:** Uses a word-count-based sliding window algorithm (`_chunk_text`) to split text into overlapping segments to preserve semantic continuity.
    - **ID Generation:** Generates deterministic `sha256` hashes for each chunk based on the collection name, metadata, index, and content to prevent duplicate entries during ingestion.
    - **Retrieval Pipeline:** Queries the vector database for a larger set of candidates (`max_items * 3`) than requested, then applies a two-stage filter: first by a `similarity_threshold`, and second by a cumulative word count (`max_tokens`) to ensure the context fits within LLM prompt limits.
- **Side Effects:** 
    - **Filesystem:** Writes and reads persistent database files to the specified `db_path`.
    - **Logging:** Utilizes [func.log](/AgentDocs/ai/functions.md) to record initialization and ingestion status.
- **Error Handling:** 
    - Throws `ImportError` if `chromadb` or `sentence-transformers` are not present in the environment.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `hashlib`, `typing`, `chromadb`, `sentence-transformers`.
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.modules.vector_memory.vector_memory](/AgentDocs/ai/modules/vector_memory/vector_memory.md)