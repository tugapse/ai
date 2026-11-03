## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Prompts Module** | [src/ai/modules/knowledge_graph/prompts.py](/AgentDocs/ai/modules/knowledge_graph/prompts.md) |

This component provides the specialized LLM instruction sets required to transform raw source code into structured knowledge graph data. It defines the semantic schema, node types, and edge relationships that the AI must follow to ensure consistent and machine-readable code analysis.

The module serves as a critical part of the knowledge graph extraction pipeline. It acts as the "instruction layer" that guides the reasoning process of the LLM, ensuring that the resulting JSON output conforms to the specific graph ontology used by the rest of the `knowledge_graph` module.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `CODE_EXTRACTION_PROMPT` | Constant (String) | A comprehensive system prompt that instructs an LLM to act as a system architect and extract code components (classes, functions, variables, etc.) into a JSON-formatted list of triples. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The file contains a single, large multi-line string constant. This string defines a rigorous ontology for code analysis, including specific definitions for "Node Types" (e.g., File, Class, Function, Parameter) and "Edge Types" (e.g., CONTAINS, CALLS, INHERITS_FROM). It provides explicit instructions on how to handle parameters, return types, and imports, and includes a detailed example of a source-to-JSON transformation to guide the LLM's few-shot learning.
- **Side Effects:** Structural definitions only; no complex logic or side effects.
- **Error Handling:** N/A.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** None.
- **Internal:** None.