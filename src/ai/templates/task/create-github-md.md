# TASK: INDIVIDUAL FILE DOCUMENTATION

**OBJECTIVE:**
Analyze the provided source code file and generate a precise technical documentation block. Treat this file as a standalone component. Do not infer details about files not provided in this turn.

**DOCUMENTATION STRUCTURE (Use Markdown H2 Headers):**

1. **Module Purpose**: A 1-2 sentence definition of what this specific file responsible for. 
2. **Interface & Exports**: List all primary classes, functions, or variables exported or intended for use by other modules.
3. **Internal Logic**: Briefly describe the core algorithm or data processing steps contained within this file.
4. **Dependencies**: List all external libraries or internal modules imported by this file.
5. **Constants & Environment**: List any hardcoded settings, global constants, or environment variable lookups found in the code.

**STRICT 8B CONSTRAINTS:**

* **ZERO SPECULATION**: If the file contains no exports or no configuration, state "None identified in source."
* **TRUTH-BOUNDED**: Only describe what is explicitly written in the code. Do not suggest "best practices" or "improvements."
* **TECHNICAL IDENTIFIERS**: Use the exact names of functions, classes, and variables as they appear in the source.
* **MARKDOWN FORMATTING**: Wrap all code identifiers, file names, and paths in backticks (`example_function`).

**FINAL RULE:**
Output ONLY the Markdown content for the documentation. Do not include a preamble, conversational filler, or summary of your actions. Only use INFORMATION from the provided file.