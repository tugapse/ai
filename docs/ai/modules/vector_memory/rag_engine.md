## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | RAG Engine |
| Source file | rag_engine.py |

The **RAGEngine** serves as the retrieval-augmented generation orchestration layer within the vector memory subsystem. It provides the high-level logic required to transform unstructured text into searchable, semantically indexed chunks and to retrieve those chunks based on query relevance. By bridging the gap between raw text and vector databases, it enables the system to possess a long-term, searchable knowledge base.

**Functional Mission**
The primary responsibility of **rag_engine.py** is to implement the Retrieval-Augmented Generation (RAG) workflow. It solves the problem of context window limitations and knowledge decay by providing mechanisms to ingest large volumes of text via chunking and embedding, and subsequently retrieving only the most relevant snippets to augment LLM prompts.

**System Context & Integration**
This component acts as a specialized consumer and provider within the [Vector Memory Module](/docs/ai/modules/vector_memory/vector_memory_module.md). It utilizes specialized providers for database persistence and embedding generation, extending the base capabilities defined in [Vector Memory](/docs/ai/modules/vector_memory/vector_memory.md). The data processed here is intended to be consumed by agents or orchestrators to provide factual grounding during inference. It relies on [Functions](/docs/ai/functions.md) for logging and directory resolution.

- **INTERNAL REFERENCES**: [Vector Memory](/docs/ai/modules/vector_memory/vector_memory.md), [Functions](/docs/ai/functions.md), [Vector Memory Module](/docs/ai/modules/vector_memory/vector_memory_module.md).

## 2. Environment & Configuration
**Environment Lookups:**
- `func.get_root_directory()`  Used to resolve the default `db_path` for knowledge storage.

**Hardcoded Constants:**
- `model_name` (Default: `'all-MiniLM-L6-v2'`)  The default SentenceTransformer model used for generating embeddings.
- `chunk_size` (Default: `500`)  The number of words per text chunk during ingestion.
- `chunk_overlap` (Default: `50`)  The number of words to overlap between consecutive chunks.
- `db_path` (Default: `{func.get_root_directory()}/knowledge/db`)  The default filesystem path for ChromaDB persistence.
- `similarity_threshold` (Default: `0.5`)  The minimum cosine similarity score required for a retrieved chunk to be considered valid.
- `max_items` (Default: `5`)  The maximum number of context chunks to return to the caller.
- `max_tokens` (Default: `2000`)  The approximate word count limit for the total returned context.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `RAGChromaDBProvider` | Class | Extends `ChromaDBProvider` to manage persistent ChromaDB collections for RAG operations. |
| `RAGEmbeddingProvider` | Class | Extends `SentenceTransformerEmbeddingProvider` to wrap `SentenceTransformer` for vector generation. |
| `_chunk_text` | Func | Internal utility to split raw strings into overlapping word-based segments. |
| `ingest_text` | Func | Orchestrates the process of chunking, embedding, and upserting text into the vector database. |
| `retrieve_context` | Func | Performs semantic search, applies similarity filtering, and enforces token/item limits on results. |

## 4. Execution Logic & Flow
- **Initialization**: 
    - `RAGChromaDBProvider` initializes a `chromadb.PersistentClient` at the specified path and retrieves/creates a collection.
    - `RAGEmbeddingProvider` loads a `SentenceTransformer` model into memory.
- **Data Path (Ingestion)**:
    1. **Input**: Raw `text`, `metadata`, and configuration parameters.
    2. **Processing**: 
        - Text is split into chunks via `_chunk_text`.
        - Each chunk is passed to `RAGEmbeddingProvider.embed()`.
        - A deterministic `chunk_id` is generated using `hashlib.sha256` based on collection name, metadata, index, and content.
        - Metadata is augmented with `chunk_index` and the original `content`.
    3. **Output**: Chunks are `upserted` into the ChromaDB collection.
- **Data Path (Retrieval)**:
    1. **Input**: `query` string and retrieval constraints.
    2. **Processing**:
        - Query is converted to a vector via `RAGEmbeddingProvider`.
        - `db.query` fetches `max_items * 3` candidates to allow for filtering.
        - Results are filtered by `similarity_threshold`.
        - Results are filtered by a cumulative `approx_tokens` (word count) check against `max_tokens`.
    3. **Output**: A list of dictionaries containing metadata and content, sorted by similarity score.
- **Conditional Branching**:
    - If `text` is empty in `ingest_text`, the function returns early.
    - If `query` is empty in `retrieve_context`, the function returns an empty list.
    - If `chunk_size <= overlap`, chunking terminates to prevent infinite loops.

## 5. Resource Dependencies
- **Standard Libraries**: `hashlib`, `typing`
- **Internal Modules**: 
    - [Functions](/docs/ai/functions.md)
    - [Vector Memory](/docs/ai/modules/vector_memory/vector_memory.md)
- **External Packages**: `chromadb`, `sentence_transformers`