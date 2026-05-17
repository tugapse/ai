the tool parser used on the chat flow is not working correcly

it didnt catch this output:


 ____@tool: read_file                                                 
INTENT: The user is asking what a specific file, `src/__init__.py`, contains. I need to read the file content to provide an accurate answer.
ARGS:
  paths:
    - "src/__init__.py"
____@tool_end
 
im seeing that we have a space on the start of the line, lets improve the parser