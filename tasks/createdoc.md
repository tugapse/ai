**User Goal:** Generate a comprehensive GitHub-style documentation file for our internal tools.

**Task Breakdown:**
1. **MAPPING:** Find the location and Read `agent_tools.py` in its entirety. Identify every function and its corresponding docstring.
2. **ARCHITECTING:** Plan a Markdown structure that includes a Table of Contents, Function Name, Parameters, and Description (sourced from docstrings).
3. **WRITING:** Create `docs/agent_tools.md`. 

**Constraints:** * **Zero Omissions:** Every single (NOT PRIVATE) function in the file must be documented.
* **No Placeholders:** Do not use "..." or "refer to code." 
* **Formatting:** Use GitHub-flavored Markdown (tables or clear headers).

**Verification:** Once written, verify the number of documented functions against the source file count to ensure 100% coverage.