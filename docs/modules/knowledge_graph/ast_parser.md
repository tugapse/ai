## 1. Architectural Role
Provides an abstract interface and concrete implementation for parsing source code into Abstract Syntax Trees (AST) and serializing those trees into dictionary representations for downstream knowledge graph processing.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ASTParser` | Class (ABC) | Defines the mandatory interface for language-specific AST parsing and dictionary serialization. |
| `parse` | Method | Abstract method to transform source code strings into `ast.AST` objects. |
| `to_dict` | Method | Abstract method to recursively convert `ast.AST` nodes into nested dictionaries. |
| `PythonASTParser` | Class | Implements `ASTParser` specifically for the Python language using the `ast` module. |
| `to_dict` (PythonASTParser) | Method | Recursively traverses Python AST nodes, capturing field values and positional metadata (line numbers, offsets). |
| `_parsers` | Variable | Internal registry mapping language identifiers (strings) to `ASTParser` subclasses. |
| `get_parser` | Function | Factory function that returns an instantiated `ASTParser` based on a provided language string. |

## 3. Execution Logic & Flow
- **Initialization**: 
    - The `_parsers` dictionary is initialized at module load time, mapping `"python"` to the `PythonASTParser` class.
- **Data Path**:
    - **Parsing Path**: `get_parser(lang)` $\rightarrow$ `PythonASTParser()` $\rightarrow$ `parse(source_code)` $\rightarrow$ `ast.parse()` $\rightarrow$ `ast.AST` object.
    - **Serialization Path**: `ast.AST` object $\rightarrow$ `to_dict(node)` $\rightarrow$ Recursive traversal of `ast.iter_fields()` $\rightarrow$ Extraction of `linenumber`/`col_offset` attributes $\rightarrow$ Nested `Dict[str, Any]`.
- **Conditional Branching**:
    - **`get_parser`**: Checks if the lowercase input exists in `_parsers`; if not, raises `ValueError`.
    - **`to_dict`**: 
        - Checks if `node` is an instance of `ast.AST`.
        - If not `ast.AST`, checks if it is a `list` to perform list comprehension.
        - If neither, returns the primitive value directly.
        - Iterates through `ast.iter_fields(node)` to recurse into child nodes.
        - Checks for the existence of specific metadata attributes (`lineno`, `col_offset`, etc.) before assignment.

## 4. Resource Dependencies
- **Standard Libraries**: `ast`, `abc`, `typing`
- **Internal Modules**: None
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `_parsers` mapping: `{"python": PythonASTParser}`
    - Metadata attribute keys: `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')`
- **Environment Lookups**: None