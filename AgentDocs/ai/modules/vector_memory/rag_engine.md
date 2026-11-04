## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **RAG Engine** | [src/ai/modules/vector_memory/rag_engine.py](/src/ai/modules/vector_memory/rag_engine.py) |

The RAG (Retrieval-Augmented Generation) Engine is responsible for managing the lifecycle of unstructured text data within a vector database. It provides the mechanisms to transform raw text into searchable semantic embeddings, manage persistent storage via ChromaDB, and retrieve highly relevant context chunks to augment LLM prompts.

This component serves as a specialized layer within the vector memory subsystem. It bridges the gap between raw text input and the vector database providers defined in [vector_memory.py](/src/ai/modules/vector_memory/vector_memory.md), implementing specific logic for text chunking, deterministic ID generation, and similarity-based context retrieval with token-limit constraints.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `RAGChromaDBProvider` | Class | A specialized wrapper for `ChromaDBProvider` that ensures persistent storage and collection management for RAG workflows. |
| `RAGEmbeddingProvider` | Class | A specialized wrapper for `SentenceTransformerEmbeddingProvider` that loads a `SentenceTransformer` model for text-to-vector conversion. |
| `ingest_text(...)` | Function | Processes raw text by chunking it, generating embeddings, and upserting the results into a ChromaDB collection with associated metadata. |
| `retrieve_context(...)` | Function | Performs a semantic search against a collection and returns a filtered, ranked list of text chunks based on similarity scores and token limits. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **Chunking:** Uses an internal `_chunk_text` helper to split text into overlapping segments based on word count to maintain semantic continuity.
    - **ID Generation:** Generates deterministic `sha256` hashes for each chunk using a combination of the collection name, metadata, index, and content to prevent duplicate entries.
    - **Retrieval Filtering:** Implements a multi-stage filter during retrieval: first by a `similarity_threshold`, then by a cumulative `max_tokens` (approximated by word count), and finally capped by `max_items`.
- **Side Effects:** 
    - **Filesystem:** Writes and reads persistent database files to the specified `db_path`.
    - **Logging:** Utilizes [functions.py](/src/ai/functions.md) to log initialization and ingestion status.
- **Error Handling:** 
    - Throws `ImportError` if `chromadb` or `sentence-transformers` are not installed in the environment.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables are explicitly required, though the `db_path` defaults to a directory derived from the system root via [functions.get_root_directory()](/src/ai/functions.md).

**Module Dependencies:**
- **Standard/External:** `hashlib`, `typing`, `chromadb`, `sentence-transformers`.
- **Internal:** 
    - [ai.functions](/src/ai/functions.md)
    - [ai.modules.vector_memory.vector_memory.SentenceTransformerEmbeddingProvider](/src/ai/modules/vector_memory/vector_memory.md)
    - [ai.modules.vector_memory.vector_memory.ChromaDBProvider](/src/ai/modules/vector_memory/vector_memory.md)