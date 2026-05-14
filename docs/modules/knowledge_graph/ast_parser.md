## 1. Architectural Role
This module provides a standardized abstraction layer and concrete implementation for parsing source code into Abstract Syntax Trees (AST). It serves as the foundational parsing component for the [modules/knowledge_graph/manager.md](modules/knowledge_graph/manager.md) to facilitate code structure analysis and knowledge extraction. By defining a common interface via `ASTParser`, it enables the system to potentially extend support to multiple programming languages while providing a specialized `PythonASTParser` for recursive serialization of Python nodes into dictionary formats.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `_parsers` (Default: `{"python": PythonASTParser}`)  A registry mapping language identifiers to their respective parser implementations.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ASTParser` | Class (ABC) | Defines the mandatory contract (`parse`, `to_dict`) for all language-specific AST parsers. |
| `PythonASTParser` | Class | Implements Python-specific logic for AST generation and recursive dictionary serialization. |
| `get_parser` | Function | A factory method that returns an instantiated parser based on the provided language string. |

## 4. Execution Logic & Flow
- **Initialization**: The module initializes a private `_parsers` dictionary containing the mapping for the `"python"` key to the `PythonASTParser` class.
- **Data Path**:
    1. **Request**: `get_parser(language)` is invoked with a string (e.g., `"python"`).
    2. **Lookup**: The string is lowercased and checked against `_parsers`.
    3. **Instantiation**: If found, the class is instantiated and returned.
    4. **Parsing**: `PythonASTParser.parse(source_code)` calls `ast.parse()` to generate an `ast.AST` object.
    5. **Serialization**: `PythonASTParser.to_dict(node)` processes the tree:
        - If the input is a primitive/list, it recurses or returns the value.
        - If the input is an `ast.AST` node, it builds a dictionary containing `node_type`.
        - It iterates through `ast.iter_fields(node)` to recursively populate fields.
        - It extracts metadata attributes (`lineno`, `col_offset`, etc.) if they exist.
- **Conditional Branching**:
    - `get_parser` raises a `ValueError` if the requested language is not present in `_parsers`.
    - `to_dict` checks `isinstance(node, ast.AST)` to distinguish between AST nodes and leaf values/lists.

## 5. Resource Dependencies
- **Standard Libraries**: `ast`, `abc`, `typing`
- **Internal Modules**: 
    - [modules/knowledge_graph/ast_parser.md](modules/knowledge_graph/ast_parser.md)
- **External Packages**: None