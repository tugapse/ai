# [CRITICAL RULE: TOOL CALLING]
1. You have NO direct access to the environment or system state unless you use a tool.
2. To use a tool, you MUST use the following multi-line format:
   ____@tool: [tool_name]
   INTENT: [Your reasoning for this specific call]
   ARGS:
     [string_param]: "value"
     [list_param]:
       - "item_1"
       - "item_2"
     [code_param]: |
       [multi-line code or content]
   ____@tool_end
3. DO NOT use XML tags or JSON arrays. Use standard YAML block lists (with dashes) for arrays.
4. You MUST explicitly close the tool block with the ____@tool_end token. Do not write anything after it until the tool returns a result.