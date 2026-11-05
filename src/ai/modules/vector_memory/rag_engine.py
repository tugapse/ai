import hashlib
from typing import Any, List, Dict

import ai.functions as func
from ai.modules.vector_memory.vector_memory import SentenceTransformerEmbeddingProvider, ChromaDBProvider


class RAGChromaDBProvider(ChromaDBProvider):
    """
    A specialized provider for interacting with ChromaDB specifically for RAG applications.

    This class wraps the ChromaDB client to ensure it is initialized correctly
    for persistent storage and collection management required by the RAG engine.
    """
    def __init__(self, path: str, collection_name: str):
        """
        Initializes the RAG ChromaDB connection.

        Args:
            path (str): The file path where the ChromaDB persistent storage resides.
            collection_name (str): The name of the collection to use or create.

        Raises:
            ImportError: If the 'chromadb' library is not installed.
        """
        try:
            import chromadb
        except ImportError:
            raise ImportError("chromadb is not installed. Please pip install chromadb")
            
        self.client = chromadb.PersistentClient(path=path)
        func.log(f"Initializing RAG ChromaDB: {collection_name}")
        self.collection = self.client.get_or_create_collection(name=collection_name)


class RAGEmbeddingProvider(SentenceTransformerEmbeddingProvider):
    """
    A specialized provider for generating embeddings using Sentence Transformers.

    This class loads the specified SentenceTransformer model to convert text chunks
    into dense vector representations suitable for vector database storage.
    """
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initializes the embedding model.

        Args:
            model_name (str): The name of the SentenceTransformer model to load.
        
        Raises:
            ImportError: If the 'sentence-transformers' library is not installed.
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError("sentence-transformers is not installed. Please pip install sentence-transformers")
        
        func.log(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Internal helper to split text into overlapping chunks based on word count.

    Args:
        text (str): The full text content to be chunked.
        chunk_size (int): The target number of words per chunk.
        overlap (int): The number of words to overlap between consecutive chunks.

    Returns:
        List[str]: A list of text chunks.
    """
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        if i + chunk_size >= len(words):
            break
        if chunk_size <= overlap:
            break
        i += chunk_size - overlap
    
    if not chunks and words:
        chunks.append(" ".join(words))
        
    return chunks


def ingest_text(
    text: str, 
    metadata: Dict[str, Any], 
    collection_name: str, 
    db_path: str = f"{func.get_root_directory()}/knowledge/db",
    chunk_size: int = 500,
    chunk_overlap: int = 50
) -> None:
    """
    Ingest raw text into a RAG collection, chunking it and applying the provided metadata.

    This function processes large documents by splitting them into manageable chunks,
    generating vector embeddings for each chunk, and storing them in the specified
    ChromaDB collection along with associated metadata.

    Args:
        text (str): The raw text to ingest.
        metadata (Dict[str, Any]): Metadata to attach to every chunk (e.g., source file, document ID).
        collection_name (str): The name of the collection to write embeddings to.
        db_path (str): Path to the persistent database storage. Defaults to a path derived from the root directory.
        chunk_size (int): Number of words per chunk.
        chunk_overlap (int): Number of overlapping words between chunks.
    """
    if not text:
        return

    db = RAGChromaDBProvider(path=db_path, collection_name=collection_name)
    embedder = RAGEmbeddingProvider()
    
    chunks = _chunk_text(text, chunk_size, chunk_overlap)
    
    for i, chunk in enumerate(chunks):
        vector = embedder.embed(chunk)
        
        # Generate a unique deterministic ID for the chunk
        unique_string = f"{collection_name}_{metadata}_{i}_{chunk}"
        chunk_id = hashlib.sha256(unique_string.encode()).hexdigest()
        
        chunk_metadata = metadata.copy()
        chunk_metadata["chunk_index"] = i
        chunk_metadata["content"] = chunk
        
        db.upsert(memory_id=chunk_id, vector=vector, metadata=chunk_metadata)
    
    func.log(f"Successfully ingested {len(chunks)} chunks into {collection_name}")


def retrieve_context(
    query: str, 
    collection_name: str, 
    db_path: str = "./rag_db",
    similarity_threshold: float = 0.5,
    max_items: int = 5,
    max_tokens: int = 2000
) -> List[Dict[str, Any]]:
    """
    Retrieve relevant context from the RAG database with simple reranking and filtering.

    This function takes a natural language query, converts it into a vector, and searches
    the ChromaDB collection for the most semantically similar chunks. It then filters
    these results based on a minimum similarity score and a maximum cumulative token limit.

    Args:
        query (str): The search query.
        collection_name (str): The name of the collection to query.
        db_path (str): Path to the persistent database storage.
        similarity_threshold (float): Minimum similarity score (0.0 to 1.0) to include a result.
        max_items (int): Maximum number of items to return.
        max_tokens (int): Maximum rough token count (approximated by word count) for the returned context.
        
    Returns:
        List[Dict[str, Any]]: Filtered and ranked list of results containing metadata and content.
    """
    if not query:
        return []

    db = RAGChromaDBProvider(path=db_path, collection_name=collection_name)
    embedder = RAGEmbeddingProvider()
    
    query_vector = embedder.embed(query)
    
    # Query more than max_items to allow for filtering
    raw_results = db.query(vector=query_vector, top_k=max_items * 3)
    
    # Pre-sort raw results to ensure we process the highest scoring ones first
    raw_results.sort(key=lambda x: x.get('score', 0.0), reverse=True)
    
    filtered_results = []
    current_tokens = 0
    
    for res in raw_results:
        score = res.get('score', 0.0)
        
        # Filter by semantic similarity threshold
        if score < similarity_threshold:
            continue
            
        content = res.get('metadata', {}).get('content', '')
        approx_tokens = len(content.split())
        
        # Limit by maximum token count
        if current_tokens + approx_tokens > max_tokens:
            continue
            
        filtered_results.append(res)
        current_tokens += approx_tokens
        
        # Limit by maximum item count
        if len(filtered_results) >= max_items:
            break
            
    # Re-sort by score descending just to be safe
    filtered_results.sort(key=lambda x: x.get('score', 0.0), reverse=True)
    
    return filtered_results