## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| RAGEngine | ai/modules/vector_memory/rag_engine |

This component is responsible for implementing the core logic of a Retrieval-Augmented Generation (RAG) system using ChromaDB as the vector store. It provides specialized providers for handling database persistence (`RAGChromaDBProvider`) and text embedding generation (`RAGEmbeddingProvider`). Its primary responsibility is to manage the entire lifecycle of knowledge integration: ingesting raw text, chunking it, generating embeddings, and storing it, as well as retrieving context based on similarity search.

Architecturally, this module functions as a service layer within the AI engine, bridging raw unstructured data (text) with semantic search capabilities. It depends on vector storage mechanisms provided by [ChromaDBProvider](/ai/modules/vector_memory/vector_memory.md) and relies on the embedding capabilities defined in [SentenceTransformerEmbeddingProvider](/ai/modules/vector_memory/vector_memory.md) to perform vectorization before interacting with the database via the public functions like `ingest_text` and `retrieve_context`.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| RAGChromaDBProvider | Class | Specialized provider for interacting with ChromaDB for RAG, managing persistent storage and collection creation. |
| RAGEmbeddingProvider | Class | Specialized provider for generating embeddings using Sentence Transformers. |
| _chunk_text | Function | Internal helper to split text into overlapping chunks based on word count. |
| ingest_text | Function | Ingests raw text into a RAG collection, chunking it, embedding it, and storing it in ChromaDB. |
| retrieve_context | Function | Retrieves relevant context from the RAG database by querying for semantic similarity, applying threshold and token limits. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `ingest_text` function first chunks the input text using word-based splitting with controlled overlap. Each resulting chunk is passed to the `RAGEmbeddingProvider` to generate a dense vector. A deterministic SHA256 ID is generated for each chunk, and the chunk, its vector, and enriched metadata are upserted into the specified ChromaDB collection. The `retrieve_context` function performs a similarity search on the query vector and then filters the results based on a minimum score threshold and a running approximation of the total token count.

- **Side Effects:** The code reads and writes to the filesystem when initializing `RAGChromaDBProvider` by creating or accessing the persistent database path (`db_path`). It also loads external models into memory (`SentenceTransformer`) during initialization.

- **Error Handling:** `RAGChromaDBProvider` explicitly catches `ImportError` if `chromadb` is missing. `RAGEmbeddingProvider` catches `ImportError` if `sentence-transformers` is missing, raising a specific error message to guide installation.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `hashlib`, `typing`, `ai.functions` (assumed to handle logging/root directory).
- **Internal:** [ChromaDBProvider](/ai/modules/vector_memory/vector_memory.md), [SentenceTransformerEmbeddingProvider](/ai/modules/vector_memory/vector_memory.md).