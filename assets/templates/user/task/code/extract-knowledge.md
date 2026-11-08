# TASK: CODE COMPONENT KNOWLEDGE EXTRACTION (GRAPH & VECTOR INGESTION)

**OBJECTIVE:**
Analyze the provided source code component to extract structured entities, relationships, and semantic embeddings metadata. The output will be ingested directly into a Knowledge Graph (nodes and edges) and a Vector Memory database for semantic search.

**INPUT VARIABLES (SUPPLIED IN RUNTIME CONTEXT):**
- **CURRENT SOURCE:** The relative path of the file being analyzed.
- **CURRENT TARGET:** The relative output path of the generated JSON component.
- **MANIFEST:** The canonical list of repository mappings in the form `[source_path -> target_path]`.

**STRICT RESOLUTION RULES:**
- **MANIFEST MAPPING:** All internal file targets in `component` and `graph_edges` must match the paths from `MANIFEST`. Always prefix mapped file paths with a leading `/` (e.g., `/${CURRENT_SOURCE}`).
- **TARGET SYNC:** `component.source_path` must equal `/${CURRENT_SOURCE}`. `component.doc_path` must equal `/${CURRENT_TARGET}`.
- **UNMAPPED/EXTERNAL IMPORTS:** If an imported entity (e.g., `google.genai`, `PIL`, `os`, etc.) cannot be resolved in `MANIFEST`, **DO NOT** include it in `graph_edges`. `graph_edges` is STRICTLY for internal repository navigation. Add unmapped/external libraries ONLY to `metadata.external_dependencies`.
- **DETERMINISTIC IDENTIFIERS:** 
  - Node IDs must strictly follow: `/${CURRENT_SOURCE}#${entity_name}`.
  - Class, function, method, variable, and configuration names must match source code casing and identifiers identically.
- **EDGE DIRECTIONALITY:** `source` in `graph_edges` must always be `/${CURRENT_SOURCE}`.

---

## OUTPUT SCHEMA (RAW JSON ONLY)

Output a single, valid, nicely formatted (multi-line indented) JSON object matching this exact schema:

{
  "component": {
    "name": "Primary entity name (class, module, or base filename)",
    "source_path": "/relative/path/to/source_file.ext",
    "doc_path": "/relative/path/to/target_file.md",
    "type": "module | class | utility | controller | model | service | interface | script"
  },
  "vector_memory": {
    "semantic_summary": "A dense, highly descriptive 2-5 sentence paragraph detailing the exact logic, architectural role, and domain responsibilities of this component. Optimized for vector similarity search."
  },
  "graph_nodes": [
    {
      "id": "/relative/path/to/source_file.ext#EntityName",
      "label": "Class | Function | Method | Variable | Interface | Type",
      "name": "EntityName",
      "signature": "def function_name(arg: type) -> return_type"
    }
  ],
  "graph_edges": [
    {
      "source": "/relative/path/to/source_file.ext",
      "target": "/mapped/target/path.ext",
      "relation": "imports | depends_on"
    }
  ],
  "metadata": {
    "environment_variables": ["VAR_NAME"],
    "external_dependencies": ["third_party_package"],
    "has_side_effects": false
  }
}

---

**STRICT GENERATION CONSTRAINTS:**
- Output raw, formatted JSON only. 
- Do NOT wrap output in markdown fences (` ```json ` or ` ``` `).
- Do NOT provide conversational preamble, explanations, disclaimers, or trailing text.
- Ensure all quotes, backslashes, and control characters inside code signatures or summaries are properly escaped.