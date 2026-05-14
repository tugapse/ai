## 1. Architectural Role
Defines the high-density prompt template used to instruct Large Language Models to perform structural code analysis and transform source code into a JSON-formatted knowledge graph of triples.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `CODE_EXTRACTION_PROMTP` | Constant (String) | Contains the system instructions, node/edge definitions, analysis rules, and an example for the LLM to follow. |

## 3. Execution Logic & Flow
- **Initialization**: The module is loaded as a static provider of prompt strings; no runtime state or class instantiation occurs.
- **Data Path**: 
    1. **Input**: Raw source code provided to an LLM.
    2. **Processing**: The LLM applies the `CODE_EXTRACTION_PROMPT` logic (identifying Files, Classes, Functions, etc., and their relationships).
    3. **Output**: A JSON object containing a `"triples"` list of `[Source, Edge, Target]` arrays.
- **Conditional Branching**: None; the prompt dictates a deterministic structural extraction process based on the presence of specific code constructs (e.g., if a class is present, create `CONTAINS` edges).

## 4. Resource Dependencies
- **Standard Libraries**: None.
- **Internal Modules**: None.
- **External Packages**: None.

## 5. Configuration & Environment
- **Hardcoded Constants**: `CODE_EXTRACTION_PROMTP` (The primary instruction set).
- **Environment Lookups**: None.