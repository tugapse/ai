# TASK: ATOMIC CODE COMPONENT ARCHITECTURE (MANIFEST-AWARE)

**OBJECTIVE:**
Deconstruct the provided source code into a high-density technical map. You MUST use the provided **MANIFEST** for all internal cross-linking to ensure repository-absolute resolution.

**STRICT LINKING RULE**: 
Every internal link must use the REPO-ABSOLUTE path provided in the MANIFEST.
- **FORBIDDEN**: [file](subfolder/file.md) (Relative)
- **MANDATORY**: [file](/subfolder/file.md) (Absolute)
- **MANDATORY**:when providing a link for the src file [FILE_NAME_WITHOUT_EXT] (abs_link_to_actual_src_file.original_ext: replace with the correct path, look for the 'Source folder', 'Docs folder' and the file EXT on the manifest to know what parts need to change)

**DOCUMENTATION STRUCTURE:**

## 1. Architectural Role
| Name | Source file |
| :--- | :--- |
| [Component Name] | [path/filename](/abs/path/to/src/file.ext)|
| [Component Name] | One liner introducing the class/module/code|

Provide a detailed overview of the component's purpose and its strategic position within the system across two or three paragraphs.

**Functional Mission**
Define the primary responsibility of this file. What specific problem does it solve, and what is its core "mission" in the codebase? Ensure the component name is bolded on its first mention.

**System Context & Integration**
Describe how this component interacts with the rest of the architecture. Focus on its role in the broader execution flow, its significance to downstream modules, and how it handles the transition of data or state.

- **INTERNAL REFERENCES**: When referencing other components, look up their REPO-ABSOLUTE path in the MANIFEST and use the format: `[Component Name](/path/from/manifest.md)`.

## 2. Environment & Configuration
**Environment Lookups:**
- `VARIABLE_NAME` (via `method/config_key`) — Brief purpose.
*If none identified, write "No environment lookups identified."*

**Hardcoded Constants:**
- `CONSTANT_NAME` (Default: `value`) — Brief purpose.
*If none identified, write "No hardcoded constants identified."*

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `name` | Class/Func | Specific functional contribution. |

## 4. Execution Logic & Flow
Map the internal logic using a step-by-step sequence:
- **Initialization**: Initial state, properties, or setup requirements.
- **Data Path**: Trace transformation (Input → Processing → Output).
- **Conditional Branching**: Key decision points or error handling pivots.

## 5. Resource Dependencies
- **Standard Libraries**: (e.g., `os`, `sys`, `json`)
- **Internal Modules**: 
    - **MATCHING**: Match imports against the provided **MANIFEST**. 
    - **REPO-ABSOLUTE FORMAT**: Use [module_name](/path/to/file.md). The path MUST start with the leading `/`.
- **External Packages**: (e.g., `requests`, `numpy`, `fastapi`)

**STRICT 8B CONSTRAINTS:**
- **NO PROSE**: Start directly with H2 headers. No conversational filler or "Here is the analysis."
- **MANIFEST VERBATIM**: Use the MANIFEST paths exactly as provided. Do not modify or truncate them.
- **IDENTIFIER INTEGRITY**: Names of classes, functions, and variables must match the code exactly.
- **TRUTH-BOUNDED**: For files with no internal logic (e.g., empty files or simple exports), write: "Direct exports or structural definitions only; no internal logic flow."
