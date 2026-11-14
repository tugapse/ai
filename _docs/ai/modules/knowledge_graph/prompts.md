## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **prompts** | [ai/modules/knowledge_graph/prompts](/ai/modules/knowledge_graph/prompts.md) |

This module serves as a centralized repository for complex, structured prompts used by the knowledge graph generation pipeline. Its primary responsibility is to define the exact instructions, schemas, and constraints necessary for an LLM to accurately parse source code and output a machine-readable knowledge graph representation.

Architecturally, this component acts as a configuration layer for the knowledge graph service. It dictates the input/output contract between the core parsing logic and the language model interface, ensuring consistency in how code relationships (like `CALLS`, `INHERITS_FROM`, etc.) are formalized and extracted.

## 2. Public API & Interfaces
This file contains no public exports.

## 3. Implementation Details & Side Effects
Structural definitions only; no complex logic or side effects.

## 4. Dependencies & Configuration
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** None.

- **Internal:** None.