## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| ASTParser | ai/modules/knowledge_graph/ast_parser.md |

This component defines the abstract interface and concrete implementation for parsing source code into an Abstract Syntax Tree (AST) and subsequently converting that AST into a structured dictionary format. Its primary responsibility is to decouple the parsing logic from the consuming knowledge graph system, providing a standardized way to represent code structure programmatically.

This parser acts as a foundational utility within the system's processing pipeline. It is responsible for the initial syntactic analysis of input code, allowing higher-level services, such as those found in [ai/modules/knowledge_graph/graph_builder.md], to operate on structured code representations rather than raw text.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| ASTParser | Class | Abstract base class defining the contract for parsing and dictionary conversion. |
| PythonASTParser | Class | Concrete implementation of ASTParser using Python's built-in `ast` module. |
| parse(source_code: str) -> ast.AST | Method | Parses the provided source code string into the root AST node. |
| to_dict(node: ast.AST) -> Dict[str, Any] | Method | Recursively traverses an AST node and converts it into a serializable dictionary structure. |
| get_parser(language: str) -> ASTParser | Function | Factory function that retrieves and returns an initialized ASTParser instance based on the specified language identifier. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `PythonASTParser.to_dict` method employs a recursive traversal strategy using `ast.iter_fields` to map AST node attributes and children into a dictionary. It handles nested lists by recursively calling `to_dict` on list elements.
- **Side Effects:** None. The component performs in-memory transformations on input strings and AST objects.
- **Error Handling:** The `get_parser` function explicitly raises a `ValueError` if the requested language is not registered in the internal `_parsers` dictionary.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `ast` (standard library), `abc` (standard library), `typing` (standard library).
- **Internal:** None.