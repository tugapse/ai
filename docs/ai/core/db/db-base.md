## 1. Architectural Role
This file defines a class `BaseDB` that provides a database interface for storing and querying records with embeddings generated from text using a specified model.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `BaseDB` | Class | Manages a database collection for storing records with embeddings and provides methods for adding records, searching, and retrieving records. |
| `ModelNames` | Enum | Defines a set of predefined model names for embedding generation. |
| `add_record` | Method | Adds a new record to the database with a unique ID, combined text, and optional metadata. |
| `search_records` | Method | Searches the database for records similar to a given query. |
| `get_record` | Method | Retrieves a record by its unique ID. |
| `parse_search_results` | Method | Parses search results into a structured format. |
| `get_all_records` | Method | Retrieves all records from the database. |

## 3. Execution Logic & Flow
- **Initialization**:
  - The `BaseDB` class is initialized with parameters such as `collection_name`, `model`, and `path`.
  - A `chromadb.PersistentClient` is created with the specified `path`.
  - A collection is retrieved or created with the specified `collection_name`.
  - The `model_name` is set, and the `tokenizer` and `model` are initialized lazily on first use.

- **Data Path**:
  - When `add_record` is called, the text is combined with the title and metadata.
  - The embedding is generated using the `generate_embedding` method.
  - The record is added to the collection with the generated embedding, unique ID, and metadata.

- **Conditional Branching**:
  - The `generate_embedding` method checks if the `tokenizer` and `model` are initialized and initializes them if not.
  - The `add_record` method checks if metadata is provided and processes it if necessary.
  - The `search_records` method generates an embedding for the query and searches the collection using this embedding.

## 4. Resource Dependencies
- **Standard Libraries**: `uuid`, `enum`
- **Internal Modules**: None
- **External Packages**: `chromadb`, `transformers`

## 5. Configuration & Environment
- **Hardcoded Constants**: `collection_name`, `model`, `path`
- **Environment Lookups**: None