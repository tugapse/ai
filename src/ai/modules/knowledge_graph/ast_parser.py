import ast
from abc import ABC, abstractmethod
from typing import Dict, Any, Type

class ASTParser(ABC):
    """Abstract base class for AST parsers."""

    @abstractmethod
    def parse(self, source_code: str) -> ast.AST:
        """
        Parses the source code into an AST.

        Args:
            source_code: The source code to parse.

        Returns:
            The root of the AST.
        """
        pass

    @abstractmethod
    def to_dict(self, node: ast.AST) -> Dict[str, Any]:
        """
        Converts an AST node to a dictionary representation.

        Args:
            node: The AST node.

        Returns:
            A dictionary representation of the node.
        """
        pass

class PythonASTParser(ASTParser):
    """Concrete AST parser for Python."""

    def parse(self, source_code: str) -> ast.AST:
        """
        Parses Python source code into an AST.

        Args:
            source_code: The Python source code.

        Returns:
            The root of the AST.
        """
        return ast.parse(source_code)

    def to_dict(self, node: ast.AST) -> Dict[str, Any]:
        """
        Converts a Python AST node to a dictionary representation.
        This is a recursive function.

        Args:
            node: The AST node.

        Returns:
            A dictionary representation of the node.
        """
        if not isinstance(node, ast.AST):
            if isinstance(node, list):
                return [self.to_dict(n) for n in node]
            return node

        node_dict = {
            "node_type": node.__class__.__name__
        }

        for field, value in ast.iter_fields(node):
            node_dict[field] = self.to_dict(value)
        
        for attr in ('lineno', 'col_offset', 'end_lineno', 'end_col_offset'):
            if hasattr(node, attr):
                node_dict[attr] = getattr(node, attr)

        return node_dict

_parsers: Dict[str, Type[ASTParser]] = {
    "python": PythonASTParser,
}

def get_parser(language: str) -> ASTParser:
    """
    Factory function to get a parser for a given language.

    Args:
        language: The programming language (e.g., "python").

    Returns:
        An instance of an ASTParser for the specified language.

    Raises:
        ValueError: If no parser is available for the language.
    """
    parser_class = _parsers.get(language.lower())
    if not parser_class:
        raise ValueError(f"No parser available for language: {language}")
    return parser_class()