## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Knowledge Graph Prompts** | [src/ai/modules/knowledge_graph/prompts.py](/src/ai/modules/knowledge_graph/prompts.py) |

This component provides the specialized LLM instructions required to transform raw source code into structured knowledge graph data. It defines the semantic frameworkincluding specific node types (e.g., Class, Function, Variable) and edge types (e.g., CONTAINS, CALLS, INHERITS_FROM)that the AI must use to ensure consistency in the extracted data.

The module serves as a critical part of the knowledge graph construction pipeline, acting as the "instruction set" for the extraction phase. It ensures that when the system analyzes code, the resulting JSON output adheres to a strict schema of triples, allowing the [knowledge graph module](/AgentDocs/ai/modules/knowledge_graph/manager.md) to ingest and process the relationships accurately.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `CODE_EXTRACTION_PROMPT` | Constant (String) | A comprehensive system prompt containing instructions, node/edge definitions, and an example for extracting code components into a JSON-formatted list of triples. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The module contains no executable logic; it is a declarative configuration file containing a large multi-line string. The string defines a domain-specific language (DSL) for the LLM, instructing it to perform entity recognition and relationship extraction on source code.
- **Side Effects:** None.
- **Error Handling:** None.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** None.
- **Internal:** None.