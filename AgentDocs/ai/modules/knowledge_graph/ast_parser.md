## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **AST Parser** | [src/ai/modules/knowledge_graph/ast_parser.py](/AgentDocs/ai/modules/knowledge_graph/ast_parser.py) |

The `ast_parser.py` module provides a structured mechanism for converting source code into an Abstract Syntax Tree (AST) and subsequently into a serializable dictionary format. It defines a standardized interface for language-specific parsers, ensuring that different programming languages can be processed through a uniform API.

This component is a critical utility within the [knowledge_graph](/AgentDocs/ai/modules/knowledge_graph/graph.md) subsystem. By transforming raw source code into structured data, it enables the knowledge graph to ingest, analyze, and represent code logic and relationships as nodes and edges within the broader graph architecture.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ASTParser` | Abstract Base Class | Defines the required interface (`parse` and `to_dict`) for all AST parser implementations. |
| `PythonASTParser` | Class | A concrete implementation of `ASTParser` specifically designed for Python source code using the built-in `ast` module. |
| `get_parser(language: str)` | Function | A factory function that returns an initialized instance of an `ASTParser` corresponding to the provided language string (e.g., `"python"`). |

## 3. Implementation Details & Side Effects
- **Core Logic:** The module employs a factory pattern via `get_parser`. The `PythonASTParser` implementation utilizes Python's native `ast` module to generate a tree. The `to_dict` method performs a recursive traversal of the AST nodes. It captures the node type, all fields defined in the AST node via `ast.iter_fields`, and specific metadata attributes such as line numbers (`lineno`) and column offsets (`col_offset`).
- **Side Effects:** None. The module performs purely computational transformations of string input to dictionary output.
- **Error Handling:** The `get_parser` function raises a `ValueError` if a requested language is not registered in the internal `_parsers` mapping.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** 
    - `ast`: Used for parsing Python source code into AST nodes.
    - `abc`: Used for defining abstract base classes.
    - `typing`: Used for type hinting.
- **Internal:**
    - No internal module dependencies detected.