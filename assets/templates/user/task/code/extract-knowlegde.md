# TASK: CODE COMPONENT KNOWLEDGE EXTRACTION (GRAPH & VECTOR INGESTION)

**OBJECTIVE:**
Analyze the provided source code component and MANIFEST data to extract structured entities, relationships, and semantic embeddings metadata. The output will be ingested directly into a Knowledge Graph (nodes and edges) and a Vector Memory database for semantic search.

**STRICT RESOLUTION RULES:**
- **MANIFEST MAPPING:** All internal dependencies and cross-references must use the exact REPO-ABSOLUTE paths provided in the MANIFEST, prefixed with a leading `/`.
- **UNMAPPED IMPORTS:** If an imported internal module is missing from the MANIFEST, list it by its raw module name without a path link. Never invent paths.
- **DETERMINISTIC NAMING:** Class, function, method, and variable names must match the source code identically.

---

## OUTPUT SCHEMA (JSON ONLY)

You must output a single, valid JSON object matching the exact structure below. Do not include markdown code block wrappers (like ```json) or any conversational text before or after the JSON.

{
  "component": {
    "name": "Name of the primary class, module, or file entity",
    "source_path": "/path/to/source_file.py",
    "doc_path": "/path/to/manifest_documentation.md",
    "type": "module | class | utility | controller | model | service"
  },
  "vector_memory": {
    "semantic_summary": "A dense, highly descriptive 2-3 sentence paragraph capturing the exact business logic, purpose, and technical domain of this component. Optimized for vector embeddings and semantic search queries."
  },
  "graph_nodes": [
    {
      "id": "fully_qualified_name_or_path#entity_name",
      "label": "Class | Function | Variable | Configuration",
      "name": "exact_name",
      "signature": "method signature or type definition if applicable"
    }
  ],
  "graph_edges": [
    {
      "source": "this_component_path",
      "target": "/absolute/path/from/manifest.md or module_name",
      "relation": "imports | calls | inherits | configures | depends_on"
    }
  ],
  "metadata": {
    "environment_variables": ["VAR_NAME_1"],
    "external_dependencies": ["package_name"],
    "has_side_effects": true/false
  }
}

---

**STRICT GENERATION CONSTRAINTS:**
- Output raw JSON string only. No conversational preamble, trailing notes, or Markdown fences.
- Ensure all JSON keys and string values are properly escaped and syntactically valid.