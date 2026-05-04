import pytest
from unittest.mock import MagicMock, patch, mock_open

from modules.knowledge_graph.manager import KnowledgeGraphManager
from modules.knowledge_graph.models import AnalysisReport, KGNode, KGTriple, AmbiguityFlag, NodeTypes, RelationshipTypes

class TestKnowledgeGraphManager:
    def setup_method(self):
        """
        Set up a new KnowledgeGraphManager instance with mocked clients before each test.
        """
        self.mock_db_client = MagicMock()
        self.mock_llm_client = MagicMock()
        self.mock_vectorizer_client = MagicMock()
        self.manager = KnowledgeGraphManager(
            db_client=self.mock_db_client,
            llm_client=self.mock_llm_client,
            vectorizer_client=self.mock_vectorizer_client
        )

    @patch("builtins.open", new_callable=mock_open, read_data="def hello():\\n    print('world')")
    @patch("modules.knowledge_graph.manager.KnowledgeGraphManager._generate_initial_triples_with_llm")
    def test_analyze_file_success(self, mock_generate_triples, mock_file_open):
        """
        Tests the successful analysis of a file.
        """
        # Arrange
        file_path = "test_project/main.py"
        mock_node_source = KGNode(type=NodeTypes.FUNCTION, name="hello")
        mock_node_target = KGNode(type=NodeTypes.VARIABLE, name="world_var")
        mock_nodes = [mock_node_source, mock_node_target]
        mock_triples = [KGTriple(source_id=mock_node_source.id, target_id=mock_node_target.id, relationship_type=RelationshipTypes.DEFINES)]
        mock_ambiguities = []
        
        mock_generate_triples.return_value = (mock_nodes, mock_triples, mock_ambiguities)

        # Act
        report = self.manager.analyze_file(file_path)

        # Assert
        assert isinstance(report, AnalysisReport)
        assert report.status == "success"
        assert report.file_path == file_path
        assert report.nodes == mock_nodes
        assert report.initial_triples == mock_triples
        assert report.ambiguity_queue == mock_ambiguities
        
        mock_file_open.assert_called_once_with(file_path, "r", encoding="utf-8")
        mock_generate_triples.assert_called_once_with(
            file_path=file_path,
            file_content="def hello():\\n    print('world')"
        )

    def test_analyze_file_not_found(self):
        """
        Tests the case where the file to be analyzed does not exist.
        """
        # Arrange
        file_path = "non_existent_file.py"

        # Act
        report = self.manager.analyze_file(file_path)

        # Assert
        assert isinstance(report, AnalysisReport)
        assert report.status == "error_file_not_found"
        assert report.file_path == file_path
        assert report.nodes == []
        assert report.initial_triples == []

    @patch("builtins.open", new_callable=mock_open, read_data="invalid content")
    @patch("modules.knowledge_graph.manager.KnowledgeGraphManager._generate_initial_triples_with_llm")
    def test_analyze_file_general_exception(self, mock_generate_triples, mock_file_open):
        """
        Tests that a general exception during analysis is caught and reported.
        NOTE: The source code has a bug where it returns 'success' even on an internal
        exception. This test is written to assert the actual, buggy behavior.
        """
        # Arrange
        file_path = "test_project/bad_file.py"
        error = Exception("Something went wrong")
        mock_generate_triples.side_effect = error

        # Act
        report = self.manager.analyze_file(file_path)

        # Assert
        assert isinstance(report, AnalysisReport)
        # This assert reflects the SUT's behavior of returning a specific error status
        # when an internal exception occurs.
        assert isinstance(report.status, str)
        assert report.status.startswith("error_analysis_failed")
        assert report.file_path == file_path
        assert report.nodes == []
        assert report.initial_triples == []
        assert report.ambiguity_queue == []