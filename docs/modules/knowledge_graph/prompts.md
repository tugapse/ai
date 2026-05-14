## 1. Architectural Role

**Functional Mission**
The **CODE_EXTRACTION_PROMPT** serves as a specialized instruction set designed to transform raw source code into a structured, machine-readable knowledge graph. Its primary mission is to guide a Large Language Model (LLM) through the complex process of semantic parsing, ensuring that code entities (classes, functions, variables) and their relational dependencies (calls, inheritance, imports) are extracted with high fidelity and consistent schema adherence.

**System Context & Integration**
This component acts as the cognitive blueprint for the [ast_parser](/docs/modules/knowledge_graph/ast_parser.md) within the knowledge graph module. It facilitates the transition from unstructured text to a formal graph structure, which is subsequently utilized by the [manager](/docs/modules/knowledge_graph/manager.md) to build a comprehensive understanding of the codebase. By enforcing a strict JSON output format, it ensures that the downstream [graph](/docs/modules/knowledge_graph/graph.md) construction processes can ingest the extracted triples without parsing errors.

## 2. Environment & Configuration
**Environment Lookups:**
No environment lookups identified.

**Hardcoded Constants:**
- `CODE_EXTRACTION_PROMPT` (String): The comprehensive system prompt containing instructions, node/edge definitions, and examples for code-to-graph extraction.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `CODE_EXTRACTION_PROMPT` | Constant | Provides the instructional template for LLM-based code analysis and knowledge graph triple extraction. |

## 4. Execution Logic & Flow
- **Initialization**: The prompt is defined as a static multi-line string constant, ready for injection into LLM context windows.
- **Data Path**: Source Code (Input) $\rightarrow$ LLM (Processing via `CODE_EXTRACTION_PROMPT`) $\rightarrow$ JSON Triplets (Output).
- **Conditional Branching**: The prompt contains logic instructions for the LLM to handle different code structures (e.g., distinguishing between `Class` and `Function` nodes, or handling `Type` hints vs. standard parameters).

## 5. Resource Dependencies
- **Standard Libraries**: None
- **Internal Modules**: 
    - [prompt_manager](/docs/modules/server/services/prompt_manager.md) (Contextual usage)
- **External Packages**: None