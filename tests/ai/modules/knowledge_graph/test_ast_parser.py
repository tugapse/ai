import pytest
import ast

from ai.modules.knowledge_graph.ast_parser import PythonASTParser, get_parser

@pytest.fixture
def parser():
    return PythonASTParser()

class TestPythonASTParser:

    def test_parse_valid_code(self, parser):
        """Tests that valid Python code is parsed into an AST object."""
        code = "x = 1"
        tree = parser.parse(code)
        assert isinstance(tree, ast.AST)

    def test_parse_invalid_code(self, parser):
        """Tests that parsing invalid Python code raises a SyntaxError."""
        code = "x = ="
        with pytest.raises(SyntaxError):
            parser.parse(code)

    def test_to_dict_simple_node(self, parser):
        """Tests the dictionary conversion of a simple AST."""
        code = "x = 1"
        tree = parser.parse(code)
        node_dict = parser.to_dict(tree)

        assert node_dict['node_type'] == 'Module'
        assert isinstance(node_dict['body'], list)
        
        assign_node = node_dict['body'][0]
        assert assign_node['node_type'] == 'Assign'
        assert assign_node['lineno'] == 1
        assert assign_node['col_offset'] == 0

        target_node = assign_node['targets'][0]
        assert target_node['node_type'] == 'Name'
        assert target_node['id'] == 'x'

        value_node = assign_node['value']
        assert value_node['node_type'] == 'Constant'
        assert value_node['value'] == 1

    def test_to_dict_recursive_and_attributes(self, parser):
        """Tests recursive conversion and inclusion of attributes like lineno."""
        code = "def my_func():\n    return 'hello'"
        tree = parser.parse(code)
        node_dict = parser.to_dict(tree)

        # Check root
        assert node_dict['node_type'] == 'Module'
        
        # Check FunctionDef
        func_def_node = node_dict['body'][0]
        assert func_def_node['node_type'] == 'FunctionDef'
        assert func_def_node['name'] == 'my_func'
        assert func_def_node['lineno'] == 1
        assert func_def_node['end_lineno'] == 2

        # Check Return statement
        return_node = func_def_node['body'][0]
        assert return_node['node_type'] == 'Return'
        assert return_node['lineno'] == 2

        # Check Constant inside Return
        constant_node = return_node['value']
        assert constant_node['node_type'] == 'Constant'
        assert constant_node['value'] == 'hello'

    def test_to_dict_non_ast_input(self, parser):
        """Tests that non-AST inputs are handled gracefully."""
        assert parser.to_dict("a string") == "a string"
        assert parser.to_dict(123) == 123
        assert parser.to_dict(None) is None
        
        # Test list of non-AST
        test_list = [1, "two", None]
        assert parser.to_dict(test_list) == test_list


class TestGetParser:

    def test_get_parser_success(self):
        """Tests successful retrieval of a known parser."""
        parser = get_parser("python")
        assert isinstance(parser, PythonASTParser)

    def test_get_parser_case_insensitive(self):
        """Tests that the language name is case-insensitive."""
        parser = get_parser("PYTHON")
        assert isinstance(parser, PythonASTParser)
        parser_lower = get_parser("python")
        assert isinstance(parser_lower, PythonASTParser)

    def test_get_parser_not_found_raises_error(self):
        """Tests that a ValueError is raised for an unknown language."""
        with pytest.raises(ValueError, match="No parser available for language: javascript"):
            get_parser("javascript")