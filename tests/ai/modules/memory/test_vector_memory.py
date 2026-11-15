import pytest
import time
import hashlib
from unittest.mock import MagicMock, patch

from ai.modules.vector_memory.vector_memory import VectorMemory



@pytest.fixture
def mock_providers(mocker):
    """Mocks all provider classes used by VectorMemory."""
    mock_db_provider = MagicMock()
    mock_embedder_provider = MagicMock()
    mock_llm_provider = MagicMock()

    mocker.patch('ai.modules.vector_memory.vector_memory.ChromaDBProvider', return_value=mock_db_provider)
    mocker.patch('ai.modules.vector_memory.vector_memory.SentenceTransformerEmbeddingProvider', return_value=mock_embedder_provider)
    mocker.patch('ai.modules.vector_memory.vector_memory.LLMProvider', return_value=mock_llm_provider)
    
    return mock_db_provider, mock_embedder_provider, mock_llm_provider

@pytest.fixture
def vector_memory_instance(mock_providers):
    """Provides a VectorMemory instance with mocked dependencies."""
    connector = MagicMock()
    memory = VectorMemory(session_id="test_session", llm=connector)
    return memory

class TestScope:
    def test_project_scope_uses_workspace(self, tmp_path):
        from ai.modules.vector_memory.vector_memory import resolve_ltm_scope
        assert resolve_ltm_scope("project", "s1", str(tmp_path)) == f"project:{tmp_path}"
        assert resolve_ltm_scope(None, "s1", str(tmp_path)) == f"project:{tmp_path}"
        assert resolve_ltm_scope("session", "s1", str(tmp_path)) == "session:s1"
        assert resolve_ltm_scope("global", "s1", str(tmp_path)) == "global"

    def test_collection_comes_from_scope(self, mock_providers, mocker):
        import ai.modules.vector_memory.vector_memory as vm
        provider = mocker.patch.object(vm, 'ChromaDBProvider')
        vm.VectorMemory(session_id="s1", scope_key="project:/repo")
        provider.assert_called_once_with(path="./agent_ltm_db", session_id="project:/repo")


class TestVectorMemory:

    def test_initialization(self, vector_memory_instance, mock_providers):
        """Test that VectorMemory initializes its providers correctly."""
        db, embedder, llm = mock_providers
        
        assert vector_memory_instance.db is db
        assert vector_memory_instance.embedder is embedder
        assert vector_memory_instance.llm is llm
        assert vector_memory_instance.tools is not None

    def test_add_memory(self, vector_memory_instance, mock_providers):
        """add_memory embeds and stores the content; importance comes from the memory type (no LLM call)."""
        db, embedder, llm = mock_providers
        content = "This is a test memory."
        embedder.embed.return_value = [0.1] * 10

        memory_id = vector_memory_instance.add_memory(content, "test_source", memory_type="decision")

        llm.rate_importance.assert_not_called()
        embedder.embed.assert_called_once_with(content)
        expected_id = hashlib.sha256(content.encode()).hexdigest()
        assert memory_id == expected_id
        kwargs = db.upsert.call_args.kwargs
        assert kwargs['memory_id'] == expected_id
        assert kwargs['vector'] == [0.1] * 10
        metadata = kwargs['metadata']
        assert metadata['content'] == content
        assert metadata['source'] == "test_source"
        assert metadata['type'] == "decision"
        assert metadata['importance'] == 8
        assert metadata['session_id'] == "test_session"
        assert vector_memory_instance.new_memories == 1

    def test_add_memory_llm_importance(self, vector_memory_instance, mock_providers):
        """With llm_importance on, the LLM rates the memory."""
        db, embedder, llm = mock_providers
        vector_memory_instance.llm_importance = True
        llm.rate_importance.return_value = 9
        vector_memory_instance.add_memory("rate me", "src")
        llm.rate_importance.assert_called_once_with("rate me")
        assert db.upsert.call_args.kwargs['metadata']['importance'] == 9

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
        db.query.assert_called_once_with(vector=[0.2] * 10, top_k=6, where=None)  # top_k * 3

        # Score 1: 0.99 + 1.0 + 0.9 = 2.89 ; score 2: ~0.78 + 0.2 + 0.7 ; score 3: ~0.98 + 0.5 + 0.8
        assert retrieved == ['memory 1', 'memory 3']

        # The returned memories get their access time refreshed
        ids, metas = db.update_metadata.call_args.args
        assert ids == ['id1', 'id3']
        assert all(m['last_accessed_at'] == current_time for m in metas)

    def test_search_filters_type_and_relevance(self, vector_memory_instance, mock_providers):
        db, embedder, llm = mock_providers
        embedder.embed.return_value = [0.2] * 10
        now = time.time()
        db.query.return_value = [
            {'id': 'a', 'score': 0.8, 'metadata': {'content': 'keep', 'type': 'decision', 'last_accessed_at': now, 'importance': 8}},
            {'id': 'b', 'score': 0.1, 'metadata': {'content': 'drop', 'type': 'decision', 'last_accessed_at': now, 'importance': 8}},
        ]
        hits = vector_memory_instance.search("q", top_k=3, types=["decision"], min_relevance=0.3)
        assert db.query.call_args.kwargs['where'] == {"type": "decision"}
        assert [h['content'] for h in hits] == ['keep']
        assert hits[0]['type'] == 'decision'

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
        mock_memories = [f"memory {i+1}" for i in range(5)]
        vector_memory_instance.retrieve_memories = MagicMock(return_value=mock_memories)
        vector_memory_instance.add_memory = MagicMock()
        
        llm.summarize_and_reflect.return_value = ["insight 1", "insight 2"]
        
        vector_memory_instance.trigger_reflection()
        
        vector_memory_instance.retrieve_memories.assert_called_once_with("current context and recent interactions", top_k=30)
        llm.summarize_and_reflect.assert_called_once_with(mock_memories)
        
        assert vector_memory_instance.add_memory.call_count == 2
        vector_memory_instance.add_memory.assert_any_call("insight 1", source="SELF_REFLECTION", memory_type="reflection")
        vector_memory_instance.add_memory.assert_any_call("insight 2", source="SELF_REFLECTION", memory_type="reflection")

    def test_trigger_reflection_no_llm(self, mock_providers):
        """Test that reflection does not run if LLM is not available."""
        # Create a specific instance without a connector/LLM
        memory = VectorMemory(session_id="test_session_no_llm", llm=None)
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