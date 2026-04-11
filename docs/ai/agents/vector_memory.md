

## 1. Architectural Role
Manages an agent's long-term memory using a vector database, enabling memory ingestion, retrieval, and synthesis through embedding, importance rating, and reflection.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `VectorMemory` | Class | Manages an agent's long-term memory using a vector database. |
| `add_memory` | Method | Adds a new memory to the database, enriched with metadata. |
| `retrieve_memories` | Method | Retrieves the most relevant memories based on a combination of recency, importance, and relevance. |
| `trigger_reflection` | Method | Periodically runs a reflection process to synthesize new, high-level memories. |
| `SentenceTransformerEmbeddingProvider` | Class | Provides embeddings using the sentence-transformers library. |
| `LLMProvider` | Class | Provides language model capabilities for importance rating and reflection. |
| `ChromaDBProvider` | Class | Provides vector database operations using ChromaDB. |
| `EmbeddingProvider` | Abstract Class | Defines an abstract interface for embedding providers. |
| `LanguageModelProvider` | Abstract Class | Defines an abstract interface for language model providers. |
| `VectorDBProvider` | Abstract Class | Defines an abstract interface for vector database providers. |

## 3. Execution Logic & Flow
- **Initialization**: 
  - Loads the `ChromaDBProvider` with a session-specific collection.
  - Initializes the `SentenceTransformerEmbeddingProvider` for text embedding.
  - Initializes the `LLMProvider` if a connector is provided for importance rating and reflection.
- **Data Path**:
  - Input: `content` and `source` for `add_memory`.
  - Processing: Embeds the content, assigns metadata, and upserts into the database.
  - Output: Confirms memory addition.
  - Input: `query` for `retrieve_memories`.
  - Processing: Embeds the query, fetches relevant memories, re-ranks them using recency, importance, and relevance scores.
  - Output: Returns the top `top_k` relevant memories.
  - Input: No direct input for `trigger_reflection`.
  - Processing: Retrieves recent memories, summarizes and reflects using the LLM, and adds new insights as memories.
  - Output: Adds new insights as memories.
- **Conditional Branching**:
  - If no LLM is available, uses a default importance rating of 5.
  - If no results are found during a query, returns an empty list.
  - If no recent memories are found, skips the reflection process.

## 4. Resource Dependencies
- **Standard Libraries**: `time`, `re`, `hashlib`, `os`, `sys`, `json`, `typing`, `abc`, `math`
- **Internal Modules**: `functions`
- **External Packages**: `sentence-transformers`, `chromadb`

## 5. Configuration & Environment
- **Hardcoded Constants**: 
  - `model_name` in `SentenceTransformerEmbeddingProvider` is set to `'all-MiniLM-L6-v2'`.
  - `top_k` in `retrieve_memories` is set to `5`.
- **Environment Lookups**: None specified.