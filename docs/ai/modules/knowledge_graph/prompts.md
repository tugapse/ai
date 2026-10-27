## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | prompts.py |
| Source file | [prompts.py](src/ai/modules/knowledge_graph/prompts.py) |

The **prompts.py** component serves as the specialized prompt engineering repository for the knowledge graph extraction subsystem. It contains the high-level instructional templates required to transform raw source code into structured, semantic knowledge graph triples.

**Functional Mission**
The primary responsibility of **prompts.py** is to provide the `CODE_EXTRACTION_PROMPT`, a complex, multi-layered instruction set designed to guide Large Language Models (LLMs) through the process of code analysis. It defines the ontological constraints (Node Types and Edge Types) and the procedural logic (Analysis Instructions) necessary to ensure that code-to-graph transformations are consistent, precise, and follow a strict JSON schema.

**System Context & Integration**
This component acts as a critical configuration layer for the knowledge graph module. It is consumed by services responsible for code analysis, likely interacting with [prompt_loader.md](/docs/ai/services/prompt_loader.md) or similar orchestration logic to feed instructions into the LLM pipeline. By centralizing these instructions, the system ensures that the structural integrity of the generated knowledge graph remains uniform across different files and execution contexts.

- **INTERNAL REFERENCES**: The instructions within this file guide the creation of data structures that are ultimately managed by [manager.md](/docs/ai/modules/knowledge_graph/manager.md) and stored according to the schemas defined in [models.md](/docs/ai/modules/knowledge_graph/models.md).

## 2. Environment & Configuration
**Environment Lookups:**
No environment lookups identified.

**Hardcoded Constants:**
- `CODE_EXTRACTION_PROMPT` (String): The master prompt template used for extracting code components into knowledge graph triples.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `CODE_EXTRACTION_PROMPT` | Constant (String) | Provides the comprehensive system prompt for LLM-based code-to-graph extraction. |

## 4. Execution Logic & Flow
Direct exports or structural definitions only; no internal logic flow.