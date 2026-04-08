# TASK: ATOMIC CODE COMPONENT ARCHITECTURE

**OBJECTIVE:**
Deconstruct the provided source code into a high-density technical map. You are documenting a single component. Do not guess its relationship to files not provided.

**DOCUMENTATION STRUCTURE:**

## 1. Architectural Role
Define the single responsibility of this file within the system in one high-density sentence.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `name` | Class/Func | What does this specific item do? |

## 3. Execution Logic & Flow
Map the internal logic of the file using a step-by-step sequence:
- **Initialization**: What state is set when the file/class is first loaded?
- **Data Path**: Trace the primary transformation of data (Input → Processing → Output).
- **Conditional Branching**: What are the key decision points in the code?

## 4. Resource Dependencies
- **Standard Libraries**: (e.g., `os`, `json`)
- **Internal Modules**: (e.g., `core.utils`)
- **External Packages**: (e.g., `colorama`)

## 5. Configuration & Environment
- **Hardcoded Constants**: List key values used for logic.
- **Environment Lookups**: List any `os.getenv` or config-file keys accessed.

**STRICT 8B CONSTRAINTS:**
- **NO PROSE**: Start directly with the H2 headers. No "Here is the documentation."
- **THE "HOW" RULE**: In section 3, focus on the **order of operations**. If it's a class, describe the lifecycle of an instance.
- **IDENTIFIER INTEGRITY**: Every name in the documentation must match the code exactly.
- **TRUTH-BOUNDED**: If no logic exists (e.g., an `__init__.py`), write "Direct exports only; no internal logic flow."