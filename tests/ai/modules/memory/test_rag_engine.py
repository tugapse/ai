import pytest
import hashlib
from unittest.mock import MagicMock, patch

from ai.modules.memory.rag_engine import _chunk_text, ingest_text, retrieve_context

def test_chunk_text():
    text = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10"
    chunks = _chunk_text(text, chunk_size=4, overlap=2)
    # Expected logic:
    # i=0: w1 w2 w3 w4
    # i=2: w3 w4 w5 w6
    # i=4: w5 w6 w7 w8
    # i=6: w7 w8 w9 w10
    assert len(chunks) == 4
    assert chunks[0] == "word1 word2 word3 word4"
    assert chunks[1] == "word3 word4 word5 word6"
    assert chunks[2] == "word5 word6 word7 word8"
    assert chunks[3] == "word7 word8 word9 word10"

    # Edge cases
    assert _chunk_text("", chunk_size=4, overlap=2) == []
    short_text = "word1 word2"
    assert _chunk_text(short_text, chunk_size=4, overlap=2) == [short_text]

@patch("ai.modules.memory.rag_engine.RAGChromaDBProvider")
@patch("ai.modules.memory.rag_engine.RAGEmbeddingProvider")
def test_ingest_text(mock_embedding, mock_db):
    mock_db_instance = MagicMock()
    mock_db.return_value = mock_db_instance
    
    mock_embedder_instance = MagicMock()
    mock_embedder_instance.embed.return_value = [0.1, 0.2]
    mock_embedding.return_value = mock_embedder_instance

    text = "hello world this is a test"
    metadata = {"source": "test.txt", "author": "me"}
    
    # Chunk size 3, overlap 1
    # i=0: "hello world this"
    # i=2: "this is a"
    # i=4: "a test"
    
    ingest_text(
        text=text,
        metadata=metadata,
        collection_name="test_col",
        db_path="./test_db",
        chunk_size=3,
        chunk_overlap=1
    )
    
    mock_db.assert_called_once_with(path="./test_db", collection_name="test_col")
    mock_embedding.assert_called_once_with()
    
    assert mock_embedder_instance.embed.call_count == 3
    assert mock_db_instance.upsert.call_count == 3
    
    # Check the first upsert
    args, kwargs = mock_db_instance.upsert.call_args_list[0]
    assert kwargs["vector"] == [0.1, 0.2]
    expected_meta = metadata.copy()
    expected_meta["chunk_index"] = 0
    expected_meta["content"] = "hello world this"
    assert kwargs["metadata"] == expected_meta
    
def test_ingest_text_empty():
    assert ingest_text("", {}, "test_col") is None

@patch("ai.modules.memory.rag_engine.RAGChromaDBProvider")
@patch("ai.modules.memory.rag_engine.RAGEmbeddingProvider")
def test_retrieve_context(mock_embedding, mock_db):
    mock_db_instance = MagicMock()
    mock_db.return_value = mock_db_instance
    
    mock_embedder_instance = MagicMock()
    mock_embedder_instance.embed.return_value = [0.1, 0.2]
    mock_embedding.return_value = mock_embedder_instance

    mock_db_instance.query.return_value = [
        {"id": "c1", "score": 0.9, "metadata": {"content": "one two three"}},
        {"id": "c2", "score": 0.8, "metadata": {"content": "four five"}},
        {"id": "c3", "score": 0.4, "metadata": {"content": "six"}}, # Below threshold
        {"id": "c4", "score": 0.7, "metadata": {"content": "seven eight nine ten eleven twelve"}} # Too many tokens
    ]

    results = retrieve_context(
        query="test query",
        collection_name="test_col",
        db_path="./test_db",
        similarity_threshold=0.5,
        max_items=2,
        max_tokens=6 # limits to one two three (3) + four five (2)
    )
    
    mock_db.assert_called_once_with(path="./test_db", collection_name="test_col")
    mock_embedder_instance.embed.assert_called_once_with("test query")
    mock_db_instance.query.assert_called_once()
    
    assert len(results) == 2
    assert results[0]["id"] == "c1"
    assert results[1]["id"] == "c2"

def test_retrieve_context_empty():
    assert retrieve_context("", "test_col") == []

def test_chunk_text_invalid_overlap():
    """Ensure that if overlap >= chunk_size, the loop doesn't infinite loop, and breaks cleanly."""
    text = "word1 word2 word3 word4"
    chunks = _chunk_text(text, chunk_size=2, overlap=2)
    assert len(chunks) == 1
    assert chunks[0] == "word1 word2"

@patch("ai.modules.memory.rag_engine.RAGChromaDBProvider")
@patch("ai.modules.memory.rag_engine.RAGEmbeddingProvider")
def test_ingest_text_deterministic_ids(mock_embedding, mock_db):
    """Ensure identical inputs produce the exact same SHA-256 chunk IDs."""
    mock_db_instance = MagicMock()
    mock_db.return_value = mock_db_instance
    mock_embedder_instance = MagicMock()
    mock_embedder_instance.embed.return_value = [0.1]
    mock_embedding.return_value = mock_embedder_instance

    text = "chunk testing content"
    metadata = {"source": "test"}
    collection = "my_test_col"
    
    ingest_text(text, metadata, collection, chunk_size=10, chunk_overlap=0)
    
    # Manually recreate the expected ID for chunk index 0
    # Formula in engine: f"{collection_name}_{metadata}_{i}_{chunk}"
    expected_string = f"{collection}_{metadata}_0_{text}"
    expected_id = hashlib.sha256(expected_string.encode()).hexdigest()
    
    args, kwargs = mock_db_instance.upsert.call_args_list[0]
    assert kwargs["memory_id"] == expected_id

@patch("ai.modules.memory.rag_engine.RAGChromaDBProvider")
@patch("ai.modules.memory.rag_engine.RAGEmbeddingProvider")
def test_retrieve_context_sorting_and_limits(mock_embedding, mock_db):
    """Ensure results are sorted by score descending, and max_items is strictly enforced."""
    mock_db_instance = MagicMock()
    mock_db.return_value = mock_db_instance
    mock_embedding.return_value = MagicMock()

    # Raw results returned out of order, all valid tokens and scores
    mock_db_instance.query.return_value = [
        {"id": "c1", "score": 0.6, "metadata": {"content": "short"}},
        {"id": "c2", "score": 0.9, "metadata": {"content": "short"}},
        {"id": "c3", "score": 0.7, "metadata": {"content": "short"}},
        {"id": "c4", "score": 0.8, "metadata": {"content": "short"}},
    ]

    results = retrieve_context(
        query="test",
        collection_name="test_col",
        similarity_threshold=0.5,
        max_items=3,  # Out of 4 valid results, we only want 3
        max_tokens=100
    )
    
    # Expected output: Sorted by score descending, max 3 items
    assert len(results) == 3
    assert results[0]["id"] == "c2" # score 0.9
    assert results[1]["id"] == "c4" # score 0.8
    assert results[2]["id"] == "c3" # score 0.7

