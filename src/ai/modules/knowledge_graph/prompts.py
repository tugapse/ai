# src/knowledge_graph_module/prompts.py

CODE_EXTRACTION_PROMPT = """
You are an expert programmer and system architect. Your task is to analyze a given source code file and extract its core components and their relationships as a knowledge graph.

Represent the extracted information as a list of knowledge graph "triples". A triple consists of a source node, an edge, and a target node: [Source Node, Edge, Target Node].

**OUTPUT FORMAT:**
Return a single JSON object with one key: "triples".
The value of "triples" should be a list of lists, where each inner list is a triple.

**NODE AND EDGE DEFINITIONS:**

**1. Node Types:**
   - "File": Represents the source code file itself.
   - "Class": Represents a class definition.
   - "Function": Represents a standalone function.
   - "Method": Represents a method within a class.
   - "Variable": Represents a global or class-level variable.
   - "Parameter": Represents a function or method parameter.
   - "Import": Represents an imported module or component.
   - "Type": Represents a data type (e.g., 'str', 'int', 'List', or a custom class name).

**2. Edge Types:**
   - "CONTAINS": A file contains a class, function, or global variable.
   - "DEFINES": A class defines a method or a variable. A function defines a parameter.
   - "CALLS": A function or method calls another function or method.
   - "INSTANTIATES": A function or method creates an instance of a class.
   - "INHERITS_FROM": A class inherits from another class.
   - "HAS_PARAMETER": A function or method has a specific parameter. (Note: Use "DEFINES" from function to parameter for more detail).
   - "RETURNS": A function or method returns a value of a specific type.
   - "HAS_TYPE": A variable or parameter is of a certain type.
   - "IMPORTS": A file imports a module or component.

**ANALYSIS INSTRUCTIONS:**

1.  **File Node:** Start by creating a "File" node for the file being analyzed. The file name should be the node's identifier.
2.  **Top-Level Components:** Identify all top-level classes, functions, and global variables within the file. Create "CONTAINS" edges from the "File" node to each of these component nodes.
3.  **Class Components:** For each "Class" node, identify its methods and class variables. Create "DEFINES" edges from the "Class" node to its "Method" and "Variable" nodes.
4.  **Inheritance:** If a class inherits from another, create an "INHERITS_FROM" edge from the child class to the parent class.
5.  **Function/Method Internals:**
    - **Parameters:** For each "Function" or "Method", identify its parameters. Create "DEFINES" edges from the function/method to its "Parameter" nodes. If type hints are present, create "HAS_TYPE" edges from the "Parameter" node to a "Type" node.
    - **Return Types:** If a return type is specified, create a "RETURNS" edge from the function/method to a "Type" node.
    - **Function Calls:** Identify all calls to other functions or methods. Create "CALLS" edges from the calling function/method to the called function/method.
    - **Instantiations:** Identify all class instantiations. Create "INSTANTIATES" edges from the calling function/method to the "Class" node being instantiated.
6.  **Imports:** Identify all imports. Create "IMPORTS" edges from the "File" node to "Import" nodes representing the imported modules/libraries.

**EXAMPLE:**

**Source Code (`utils.py`):**
```python
import os

class Helper:
    def __init__(self, name: str):
        self.name = name

    def greet(self):
        return f"Hello, {self.name}"

def process_data(data: list, helper: Helper):
    print(helper.greet())
    return len(data)
```

**Expected JSON Output:**
```json
{
  "triples": [
    [{"type": "File", "name": "utils.py", "source_text": null}, "IMPORTS", {"type": "Import", "name": "os", "source_text": null}],
    [{"type": "File", "name": "utils.py", "source_text": null}, "CONTAINS", {"type": "Class", "name": "Helper", "source_text": "class Helper:\\n    ..."}],
    [{"type": "File", "name": "utils.py", "source_text": null}, "CONTAINS", {"type": "Function", "name": "process_data", "source_text": "def process_data(data: list, helper: Helper):\\n    ..."}],
    [{"type": "Class", "name": "Helper", "source_text": null}, "DEFINES", {"type": "Method", "name": "__init__", "source_text": "def __init__(self, name: str):\\n        ..."}],
    [{"type": "Class", "name": "Helper", "source_text": null}, "DEFINES", {"type": "Method", "name": "greet", "source_text": "def greet(self):\\n        ..."}],
    [{"type": "Method", "name": "__init__", "source_text": null}, "DEFINES", {"type": "Parameter", "name": "name", "source_text": "name: str"}],
    [{"type": "Parameter", "name": "name", "source_text": null}, "HAS_TYPE", {"type": "Type", "name": "str", "source_text": null}],
    [{"type": "Function", "name": "process_data", "source_text": null}, "DEFINES", {"type": "Parameter", "name": "data", "source_text": "data: list"}],
    [{"type": "Parameter", "name": "data", "source_text": null}, "HAS_TYPE", {"type": "Type", "name": "list", "source_text": null}],
    [{"type": "Function", "name": "process_data", "source_text": null}, "DEFINES", {"type": "Parameter", "name": "helper", "source_text": "helper: Helper"}],
    [{"type": "Parameter", "name": "helper", "source_text": null}, "HAS_TYPE", {"type": "Type", "name": "Helper", "source_text": null}],
    [{"type": "Function", "name": "process_data", "source_text": null}, "CALLS", {"type": "Method", "name": "greet", "source_text": null}],
    [{"type": "Function", "name": "process_data", "source_text": null}, "RETURNS", {"type": "Type", "name": "int", "source_text": null}]
  ]
}
```

**IMPORTANT:**
- The `source_text` field for nodes can be `null` if it's not a primary definition (like a Type or an Import). For primary definitions (Class, Function, Method), include the full source block.
- Be precise. A method call `helper.greet()` is a call to `greet`, not `helper`. The relationship to `helper` is established through its type.
- Focus on the relationships *defined* in this file. Do not infer relationships from imported libraries beyond the import statement itself.

Now, analyze the following code and provide the JSON output.
"""