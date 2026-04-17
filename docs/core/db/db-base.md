## 1. Architectural Role
Provides a persistent vector database interface for storing and retrieving document embeddings using ChromaDB and HuggingFace transformer models.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ModelNames` | Enum | Defines supported embedding model identifiers (QWEN, INSTRUCTOR, SENTENCE_TRANSFORMERS). |
| `BaseDB` | Class | Manages the lifecycle of the vector store, embedding generation, and record CRUD operations. |
| `BaseDB.__init__` | Method | Initializes `PersistentClient`, creates/gets a collection, and sets the target model. |
| `BaseDB._initialize_embedding_model` | Method | Lazy-loads `AutoTokenizer` and `AutoModel` from the `transformers` library. |
| `BaseDB.generate_embedding` | Method | Tokenizes input text and computes a mean-pooled embedding vector. |
| `BaseDB.add_record` | Method | Generates a UUID, creates a combined text string, processes metadata, and persists the document/embedding. |
| `BaseDB.search_records` | Method | Generates a query embedding and performs a similarity search via ChromaDB. |
| `BaseDB.get_record` | Method | Retrieves a specific record by its unique ID. |
| `BaseDB.parse_search_results` | Method | Transforms raw ChromaDB query output into a list of structured dictionaries. |
| `BaseDB.get_all_records` | Method | Retrieves all entries currently stored in the collection. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. `PersistentClient` is instantiated at the specified `path`.
    2. `get_or_create_collection` ensures the target collection exists.
    3. `model_name` is stored; `tokenizer` and `model` are initialized as `None`.
- **Data Path (Ingestion)**: 
    `title` + `content` $\rightarrow$ `combined_text` $\rightarrow$ `generate_embedding()` $\rightarrow$ `tokenizer` $\rightarrow$ `model` $\rightarrow$ `mean(dim=1)` $\rightarrow$ `collection.add()`.
- **Data Path (Retrieval)**: 
    `query` $\rightarrow$ `generate_embedding()` $\rightarrow$ `collection.query()` $\rightarrow$ `parse_search_results()` $\rightarrow$ List of records.
- **Conditional Branching**:
    - **Lazy Loading**: `_initialize_embedding_model` only executes if `self.model` is `None`.
    - **Metadata Sanitization**: In `add_record`, if a metadata value is a `list`, it is joined into a comma-separated string.
    - **Error Handling**: `try-except` blocks wrap model loading and record retrieval to handle `ImportError` or `ValueError`.

## 4. Resource Dependencies
- **Standard Libraries**: `uuid`, `enum`
- **Internal Modules**: None
- **External Packages**: `chromadb`, `transformers` (via lazy import)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `collection_name` default: `"my_records"`
    - `model` default: `ModelNames.SENTENCE_TRANSFORMERS_ALL_MINILM_L6_V2`
    - `path` default: `"db"`
    - `n_results` default: `5`
- **Environment Lookups**: None