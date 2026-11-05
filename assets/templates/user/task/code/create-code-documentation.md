# TASK: CODE COMPONENT DOCUMENTATION (MANIFEST-AWARE)

**OBJECTIVE:**
Generate pragmatic, developer-focused Markdown documentation for the provided source code. You MUST use the provided **MANIFEST** for all internal documentation cross-linking to ensure repository-absolute resolution.

**STRICT LINKING RULES:**
Every internal link must use the exact REPO-ABSOLUTE path provided in the MANIFEST, prefixed with a leading `/`.
- **FORBIDDEN (Relative):** [file](subfolder/file.md)
- **MANDATORY (Absolute):** [file](/subfolder/file.md)
- **UNMAPPED INTERNAL IMPORTS:** If an internal module is imported in the code but does not exist in the MANIFEST, format it as inline code (e.g., `ai.utils`) without a link. Never guess or invent paths.
- **EXCEPTION FOR SOURCE FILE:** In the "Source File" column of the Overview table, do NOT use the manifest `.md` path. Link directly to the actual source code file by prefixing the `CURRENT_SOURCE` path with a leading `/` (e.g., [src/main.py](/src/main.py)).
- **NO BACKTICKS ON LINKS:** Never wrap markdown links in backticks or code blocks. Always output them as pure Markdown text.

---

## OUTPUT FORMAT & SECTIONS

Follow the exact Markdown structure below:

## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **[Component Name]** | [CURRENT_SOURCE](/CURRENT_SOURCE) |

Write a concise, two-paragraph explanation of what this component does and why it exists:
- Paragraph 1: Explain the specific problem this code solves and its primary responsibility.
- Paragraph 2: Explain where this component fits into the broader application architecture (e.g., data model, utility, UI component, controller, or service). When referencing other internal components, link them using their MANIFEST path, like [Component Name](/path/from/manifest.md).

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `name()` | Function / Class / Method | Brief description of inputs, return values, and behavior. |

*(Instruction: List only public classes, functions, or types exposed by this file. If no public entities exist, omit the table and write only: "This file contains no public exports.")*

## 3. Implementation Details & Side Effects
- **Core Logic:** Brief summary of the internal algorithm, state flow, or data transformation without repeating the code line-by-line.
- **Side Effects:** Explicitly state if the code interacts with the network, reads/writes to the filesystem, spawns processes, or mutates external/global state. (If none, write "None").
- **Error Handling:** Document any specific exceptions raised, caught, or fallback mechanisms used.

*(Instruction: For simple definitions, interfaces, or empty files, omit the bullets above and write only: "Structural definitions only; no complex logic or side effects.")*

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `ENV_VAR_NAME` — Brief purpose and default behavior if unset.

*(Instruction: If no environment variables or external configs are used, omit the bullet above and write only: "No environment variables or external configurations required.")*

**Module Dependencies:**
- **Standard/External:** List key standard library or third-party packages used (e.g., `os`, `json`, `requests`). (If none, write "None").
- **Internal:** Match internal project imports against the MANIFEST using repo-absolute links, like [module_name](/path/to/file.md). Use inline code without a link if absent from the MANIFEST.

---

**STRICT GENERATION CONSTRAINTS:**
- Output raw Markdown only. Do NOT wrap the entire response in a markdown code block (` ```markdown `).
- Start the response directly with `## 1. Overview & Purpose`. No preamble, greetings, or concluding remarks.
- Never output instructional placeholders, guidelines, or parenthetical instruction notes in the final text.
- Class, method, and variable names must match the source code identically.