## 1. Architectural Role

**Functional Mission**
The **ast_parser.py** component serves as the structural translation layer for source code analysis within the knowledge graph construction pipeline. Its primary mission is to provide a standardized interface for converting raw programming language source code into Abstract Syntax Trees (AST) and subsequently into serializable dictionary formats, enabling the system to perform semantic analysis on code structures.

**System Context & Integration**
This component acts as a foundational utility for the [knowledge_graph](/docs/modules/knowledge_graph/manager.md) module. By abstracting the complexities of language-specific parsing through a factory pattern, it allows downstream graph construction logic to ingest code-based entities without needing to handle the nuances of the `ast` module directly. It facilitates the transition from unstructured text to structured, traversable data models required for building the knowledge graph.

## 2. Environment & Configuration
**Environment Lookups:**
No environment lookups identified.

**Hardcoded Constants:**
- `_parsers` (Default: `{"python": PythonASTParser}`)  A registry mapping language identifiers to their corresponding concrete parser implementations.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ASTParser` | Class (ABC) | Defines the abstract contract for all language-specific AST parsers. |
| `parse` | Method | Abstract method to transform source code string into an `ast.AST` object. |
| `to_dict` | Method | Abstract method to transform an AST node into a nested dictionary. |
| `PythonASTParser` | Class | Concrete implementation of `ASTParser` specifically for the Python language. |
| `get_parser` | Function | Factory function that returns an initialized instance of a parser based on a language string. |

## 4. Execution Logic & Flow
- **Initialization**: The module initializes a private `_parsers` dictionary mapping the string `"python"` to the `PythonASTParser` class.
- **Data Path**: 
    1. **Input**: A string containing source code and a language identifier are passed to `get_parser`.
    2. **Parsing**: `PythonASTParser.parse` invokes `ast.parse()` to generate a tree of `ast.AST` nodes.
    3. **Transformation**: `PythonASTParser.to_dict` recursively traverses the tree. For each node, it extracts field values via `ast.iter_fields` and captures metadata (line numbers, column offsets) via `getattr`.
    4. **Output**: A deeply nested dictionary representing the code's hierarchical structure.
- **Conditional Branching**:
    - **Parser Lookup**: `get_parser` checks the `_parsers` registry; if the language is not found, it raises a `ValueError`.
    - **Type Validation**: In `to_dict`, the logic branches to handle non-AST objects (returning them directly) and lists (recursively mapping elements) to ensure the entire tree is processed.
    - **Attribute Check**: The parser uses `hasattr` to conditionally include source mapping metadata (`lineno`, `col_offset`, etc.) only if they exist on the specific node.

## 5. Resource Dependencies
- **Standard Libraries**: `ast`, `abc`, `typing`
- **Internal Modules**: 
    - None identified.
- **External Packages**: None identified.