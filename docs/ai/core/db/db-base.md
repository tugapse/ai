## Module Purpose
This file defines a `BaseDB` class that provides a standardized interface for interacting with a ChromaDB persistent client, integrating transformer-based models for generating text embeddings to support vector database operations.

## Interface & Exports
*   Class: `ModelNames`
*   Class: `BaseDB`
    *   Method: `__init__`
    *   Method: `_initialize_embedding_model`
    *   Method: `generate_embedding`
    *   Method: `add_record`
    *   Method: `search_records`
    *   Method: `get_record`
    *   Method: `parse_search_results`
    *   Method: `get_all_records`

## Internal Logic
The `BaseDB` class initializes a `chromadb.PersistentClient` and a collection, defaulting to a local path and collection name. It uses an internal `_initialize_embedding_model` method to lazy-load a tokenizer and model from the `transformers` library based on a specified `ModelNames` enum value, handling potential `ImportError` if the library is not installed. The `generate_embedding` method processes text through the loaded transformer model to produce a numerical embedding. Records are added using `add_record`, which generates a UUID, creates a combined text string, generates its embedding, and stores it in ChromaDB along with provided metadata (converting list metadata values to comma-separated strings). `search_records` performs a vector similarity search using an embedding generated from a query. `get_record` retrieves a specific record by its ID. `parse_search_results` structures the raw output from ChromaDB queries into a more accessible dictionary format, including `id`, `document`, `distance`, and `metadata`. `get_all_records` retrieves all entries from the collection.

## Dependencies
*   `chromadb`
*   `uuid`
*   `enum`
*   `transformers` (specifically `AutoTokenizer`, `AutoModel` are imported conditionally within `_initialize_embedding_model`)

## Constants & Environment
*   `ModelNames` Enum members:
    *   `QWEN_RE_RANKER_0_6B = "Qwen/Qwen3-Reranker-0.6B"`
    *   `INSTRUCTOR_XL = "hkunlp/instructor-xl"`
    *   `SENTENCE_TRANSFORMERS_ALL_MINILM_L6_V2 = "sentence-transformers/all-MiniLM-L6-v2"`
*   Default `collection_name` for `BaseDB`: `"my_records"`
*   Default `model` for `BaseDB`: `ModelNames.SENTENCE_TRANSFORMERS_ALL_MINILM_L6_V2`
*   Default `path` for `chromadb.PersistentClient`: `"db"`