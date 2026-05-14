# TASK: ATOMIC CODE COMPONENT ARCHITECTURE (MANIFEST-AWARE)

**OBJECTIVE:**
Deconstruct the provided source code into a high-density technical map. Use the provided **MANIFEST** for internal cross-linking to ensure project-wide navigability.

**DOCUMENTATION STRUCTURE:**

## 1. Architectural Role
Define the single responsibility of this file within the system in one high-density paragraph. 
- **MANIFEST LINKING**: Use the [filename.md](path/to/filename.md) syntax for any internal references. Do not put the full path inside the square brackets.

## 2. Environment & Configuration
**Environment Lookups:**
- `VARIABLE_NAME` (via `method/config_key`) — Brief purpose.
*If none, write "No environment lookups identified."*

**Hardcoded Constants:**
- `CONSTANT_NAME` (Default: `value`) — Brief purpose.
*If none, write "No hardcoded constants identified."*

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `name` | Class/Func | What does this specific item do? |

## 4. Execution Logic & Flow
Map the internal logic using a step-by-step sequence:
- **Initialization**: Initial state/properties.
- **Data Path**: Trace transformation (Input → Processing → Output).
- **Conditional Branching**: Key decision points.

## 5. Resource Dependencies
- **Standard Libraries**: (e.g., `os`, `json`)
- **Internal Modules**: 
    - **RULE**: Cross-reference imports against the **MANIFEST**. 
    - Format matches as: `[module_name](path/to/file.md)`.
- **External Packages**: (e.g., `torch`, `transformers`)

**STRICT 8B CONSTRAINTS:**
- **NO PROSE**: Start directly with H2 headers.
- **CLEAN LINKS**: Always use `[filename.md](full/path/to/file.md)`. This keeps the text readable and prevents formatting breaks.
- **IDENTIFIER INTEGRITY**: Names must match the code exactly.
- **TRUTH-BOUNDED**: If no logic exists (e.g., `__init__.py`), write "Direct exports only; no internal logic flow."