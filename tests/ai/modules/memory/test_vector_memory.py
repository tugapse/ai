import pytest
import time
import hashlib
from unittest.mock import MagicMock, patch

from src.ai.modules.memory.vector_memory import VectorMemory

# Mock external dependencies that are imported in the module
@pytest.fixture(autouse=True)
def mock_external_libs():
    """Mock heavy external libraries for all tests in this file."""
    with patch('src.ai.modules.memory.vector_memory.SentenceTransformer', MagicMock()) as mock_st, \
         patch('src.ai.modules.memory.vector_memory.chromadb', MagicMock()) as mock_cdb:
        yield mock_st, mock_cdb

@pytest.fixture
def mock_providers(mocker):
    """Mocks all provider classes used by VectorMemory."""
    mock_db_provider = MagicMock()
    mock_embedder_provider = MagicMock()
    mock_llm_provider = MagicMock()

    mocker.patch('src.ai.modules.memory.vector_memory.ChromaDBProvider', return_value=mock_db_provider)
    mocker.patch('src.ai.modules.memory.vector_memory.SentenceTransformerEmbeddingProvider', return_value=mock_embedder_provider)
    mocker.patch('src.ai.modules.memory.vector_memory.LLMProvider', return_value=mock_llm_provider)
    
    return mock_db_provider, mock_embedder_provider, mock_llm_provider

@pytest.fixture
def vector_memory_instance(mock_providers):
    """Provides a VectorMemory instance with mocked dependencies."""
    connector = MagicMock()
    memory = VectorMemory(session_id="test_session", connector=connector)
    return memory

class TestVectorMemory:

    def test_initialization(self, vector_memory_instance, mock_providers):
        """Test that VectorMemory initializes its providers correctly."""
        db, embedder, llm = mock_providers
        
        assert vector_memory_instance.db is db
        assert vector_memory_instance.embedder is embedder
        assert vector_memory_instance.llm is llm
        assert vector_memory_instance.tools is not None

    def test_add_memory(self, vector_memory_instance, mock_providers):
        """Test the add_memory method."""
        db, embedder, llm = mock_providers
        
        content = "This is a test memory."
        source = "test_source"
        
        # Mock provider responses
        llm.rate_importance.return_value = 8
        embedder.embed.return_value = [0.1] * 10
        
        vector_memory_instance.add_memory(content, source)
        
        # Assertions
        llm.rate_importance.assert_called_once_with(content)
        embedder.embed.assert_called_once_with(content)
        
        expected_id = hashlib.sha256(content.encode()).hexdigest()
        
        db.upsert.assert_called_once()
        args, kwargs = db.upsert.call_args
        assert kwargs['memory_id'] == expected_id
        assert kwargs['vector'] == [0.1] * 10
        metadata = kwargs['metadata']
        assert metadata['content'] == content
        assert metadata['source'] == source
        assert metadata['importance'] == 8

    def test_add_memory_no_content(self, vector_memory_instance, mock_providers):
        """Test that add_memory does nothing if content is empty."""
        db, embedder, llm = mock_providers
        vector_memory_instance.add_memory("", "test_source")
        db.upsert.assert_not_called()
        embedder.embed.assert_not_called()
        llm.rate_importance.assert_not_called()

    def test_retrieve_memories(self, vector_memory_instance, mock_providers, mocker):
        """Test the retrieve_memories method with composite scoring."""
        db, embedder, llm = mock_providers
        
        query = "find relevant test data"
        
        # Mock time to control recency score
        current_time = time.time()
        mocker.patch('time.time', return_value=current_time)
        
        # Mock provider responses
        embedder.embed.return_value = [0.2] * 10
        
        # Mock DB results
        mock_results = [
            {'id': 'id1', 'score': 0.9, 'metadata': {'content': 'memory 1', 'last_accessed_at': current_time - 3600, 'importance': 10}}, # recent, important
            {'id': 'id2', 'score': 0.7, 'metadata': {'content': 'memory 2', 'last_accessed_at': current_time - (3600 * 24), 'importance': 2}}, # old, unimportant
            {'id': 'id3', 'score': 0.8, 'metadata': {'content': 'memory 3', 'last_accessed_at': current_time - 7200, 'importance': 5}}, # medium
        ]
        db.query.return_value = mock_results
        
        # Set weights for predictable scoring
        vector_memory_instance.recency_weight = 1.0
        vector_memory_instance.importance_weight = 1.0
        vector_memory_instance.relevance_weight = 1.0
        
        retrieved = vector_memory_instance.retrieve_memories(query, top_k=2)
        
        embedder.embed.assert_called_once_with(query)
        db.query.assert_called_once_with(vector=[0.2] * 10, top_k=6) # top_k * 3
        
        # Check that the highest scored memory is first
        # Score for memory 1: (0.99**1)*1 + (10/10)*1 + 0.9*1 = 0.99 + 1.0 + 0.9 = 2.89
        # Score for memory 2: (0.99**24)*1 + (2/10)*1 + 0.7*1 = ~0.78 + 0.2 + 0.7 = ~1.68
        # Score for memory 3: (0.99**2)*1 + (5/10)*1 + 0.8*1 = ~0.98 + 0.5 + 0.8 = ~2.28
        assert len(retrieved) == 2
        assert retrieved[0] == 'memory 1'
        assert retrieved[1] == 'memory 3'

    def test_retrieve_memories_no_query(self, vector_memory_instance, mock_providers):
        """Test retrieve_memories with an empty query string."""
        db, embedder, llm = mock_providers
        result = vector_memory_instance.retrieve_memories("", top_k=5)
        assert result == []
        db.query.assert_not_called()

    def test_trigger_reflection(self, vector_memory_instance, mock_providers):
        """Test the reflection mechanism."""
        db, embedder, llm = mock_providers
        
        # Mock methods that are part of the same class
        vector_memory_instance.retrieve_memories = MagicMock(return_value=["memory 1", "memory 2"])
        vector_memory_instance.add_memory = MagicMock()
        
        llm.summarize_and_reflect.return_value = ["insight 1", "insight 2"]
        
        vector_memory_instance.trigger_reflection()
        
        vector_memory_instance.retrieve_memories.assert_called_once_with("Identify key technical events and patterns.", top_k=25)
        llm.summarize_and_reflect.assert_called_once_with(["memory 1", "memory 2"])
        
        assert vector_memory_instance.add_memory.call_count == 2
        vector_memory_instance.add_memory.assert_any_call("insight 1", source="SELF_REFLECTION", memory_type="reflection")
        vector_memory_instance.add_memory.assert_any_call("insight 2", source="SELF_REFLECTION", memory_type="reflection")

    def test_trigger_reflection_no_llm(self, mock_providers):
        """Test that reflection does not run if LLM is not available."""
        # Create a specific instance without a connector/LLM
        memory = VectorMemory(session_id="test_session_no_llm", connector=None)
        memory.retrieve_memories = MagicMock()
        
        memory.trigger_reflection()
        
        assert memory.llm is None
        memory.retrieve_memories.assert_not_called()

    @pytest.mark.parametrize("hours_ago, decay, expected", [
        (0, 0.99, 1.0),
        (1, 0.99, 0.99),
        (10, 0.9, 0.3486),
        (24, 0.995, 0.8867)
    ])
    def test_calculate_recency_score(self, mocker, hours_ago, decay, expected):
        """Test the static recency score calculation."""
        current_time = time.time()
        mocker.patch('time.time', return_value=current_time)
        
        past_time = current_time - (hours_ago * 3600)
        
        score = VectorMemory._calculate_recency_score(past_time, decay_factor=decay)
        assert abs(score - expected) < 1e-4