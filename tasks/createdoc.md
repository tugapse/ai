/no_think
MISSION: Document all Python modules in "@ROOT/src".

OBJECTIVES:
1. Map the directory structure to logical Python import paths (ignoring the 'src/' prefix).
2. Create a .md file for each module in "@ROOT/docs/reference/".
3. Each .md file must contain the '::: module.path' identifier for mkdocstrings.
4. Update "@ROOT/mkdocs.yml" navigation once all files are created.

INITIALIZATION: 
- Start by asking the SECRETARY to list all .py files in "src/". 
- Initialize your JSON 'manifest' with 'phase': 'MAPPING'.
- Do not perform any write actions until the mapping is complete.