## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **AST Parser** | [src/ai/modules/knowledge_graph/ast_parser.py](/src/ai/modules/knowledge_graph/ast_parser.py) |

The `ast_parser.py` module provides a structured mechanism for converting source code into a machine-readable format. It defines an abstract interface for parsing code into an Abstract Syntax Tree (AST) and subsequently transforming that tree into a dictionary representation, which is essential for downstream data processing and knowledge extraction.

This component serves as a critical utility within the knowledge graph module, specifically facilitating the ingestion of code-based information. By converting raw source code into structured dictionaries, it allows the system to perform semantic analysis and populate the [knowledge graph](/src/ai/modules/knowledge_graph/graph.md) with high-fidelity structural data.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ASTParser` | Abstract Class | The base interface defining `parse` and `to_dict` methods for all parser implementations. |
| `PythonASTParser` | Class | A concrete implementation of `ASTParser` specifically designed for Python source code using the `ast` module. |
| `get_parser(language: str)` | Function | A factory function that returns an initialized instance of an `ASTParser` for the requested language (e.g., "python"). |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - The module utilizes a factory pattern via `get_parser` to manage different language implementations.
    - `PythonASTParser.parse` leverages Python's native `ast.parse` to generate a tree structure.
    - `PythonASTParser.to_dict` implements a recursive traversal algorithm. It iterates through all fields of an AST node using `ast.iter_fields`, converts nested nodes or lists into dictionaries, and explicitly captures metadata such as line numbers (`lineno`) and column offsets (`col_offset`, `end_lineno`, `end_col_offset`).
- **Side Effects:** None. The module performs pure data transformations in memory.
- **Error Handling:** 
    - `get_parser` raises a `ValueError` if the requested language identifier is not found in the internal `_parsers` registry.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** 
    - `ast`: Used for parsing Python source code into AST nodes.
    - `abc`: Used for defining Abstract Base Classes.
    - `typing`: Used for type hinting.
- **Internal:** 
    - No internal module dependencies detected.