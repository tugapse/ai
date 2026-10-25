## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | ASTParser |
| Source file | ast_parser.py |

The **ASTParser** component serves as a specialized translation layer within the knowledge extraction pipeline. Its primary purpose is to transform raw source code into structured, machine-readable formats by leveraging Abstract Syntax Trees (AST). By converting hierarchical code structures into serialized dictionaries, it enables the system to perform deep semantic analysis of programming logic.

**Functional Mission**
The **ASTParser** is responsible for providing a standardized interface for parsing multiple programming languages into a unified dictionary representation. It solves the problem of language-specific syntax complexity by abstracting the parsing logic behind a common API, allowing downstream components to consume code structure without needing to understand the underlying grammar of the source language.

**System Context & Integration**
This component acts as a foundational utility for the [Knowledge Graph](/docs/ai/modules/knowledge_graph/graph.md) construction process. It is strategically positioned to ingest source code and output structured data that can be ingested by the [Knowledge Graph Manager](/docs/ai/modules/knowledge_graph/manager.md) to build nodes and edges representing code entities. It functions as a provider for the broader knowledge extraction modules, ensuring that code-based intelligence is captured in a consistent schema.

## 2. Environment & Configuration
**Environment Lookups:**
No environment lookups identified.

**Hardcoded Constants:**
No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ASTParser` | Class (ABC) | Defines the abstract contract for all language-specific AST parsers. |
| `PythonASTParser` | Class | Implements the `ASTParser` interface specifically for Python source code. |
| `parse` | Method | Converts a raw string of source code into a native `ast.AST` object. |
| `to_dict` | Method | Recursively traverses an AST and converts nodes and fields into a JSON-serializable dictionary. |
| `get_parser` | Function | A factory method that returns the appropriate `ASTParser` instance based on a language string. |

## 4. Execution Logic & Flow
- **Initialization**: The component utilizes a registry pattern via the `_parsers` dictionary, mapping language identifiers (e.g., "python") to their respective concrete class implementations.
- **Data Path**: 
    1. **Input**: A string containing source code is passed to `parse()`.
    2. **Parsing**: The `ast.parse()` method generates a tree of `ast.AST` nodes.
    3. **Transformation**: The `to_dict()` method is called on the root node.
    4. **Recursion**: `to_dict()` iterates through `ast.iter_fields()`, recursively calling itself for every child node or list of nodes.
    5. **Metadata Enrichment**: During recursion, the parser checks for and attaches positional metadata (`lineno`, `col_offset`, etc.).
    6. **Output**: A deeply nested dictionary representing the full syntax tree is returned.
- **Conditional Branching**:
    - **Type Checking**: In `to_dict`, the logic branches to handle non-AST objects (primitives) and lists of nodes differently to ensure recursive integrity.
    - **Factory Validation**: In `get_parser`, if the requested language is not found in the `_parsers` registry, a `ValueError` is raised to prevent invalid execution flows.

## 5. Resource Dependencies
- **Standard Libraries**: `ast`, `abc`, `typing`
- **Internal Modules**: 
    - No internal modules imported.
- **External Packages**: No external packages identified.