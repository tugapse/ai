

## 1. Architectural Role  
Singleton registry for tool management, enabling dynamic tool registration, metadata retrieval, and execution.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `ToolRegistry` | Class | Centralized singleton registry for tool lifecycle management. |  
| `register_tool` | Method | Associates a tool name with a callable function reference. |  
| `get_tool_info` | Method | Returns formatted metadata (docstring) for a registered tool. |  
| `execute_tool` | Method | Invokes a registered tool with parameters, returning execution results. |  
| `__new__` | Method | Enforces singleton pattern by controlling instance creation. |  
| `__init__` | Method | Placeholder for initialization, bypassed in singleton pattern. |  

## 3. Execution Logic & Flow  
- **Initialization**: On first instantiation, `__new__` creates the singleton instance and initializes `_tools` as an empty dictionary.  
- **Data Path**: Input (tool name/params)  `execute_tool` checks existence  logs call  invokes tool function  returns result/error.  
- **Conditional Branching**:  
  - `if name not in _tools`: Returns tool not found error.  
  - `try/except`: Catches exceptions during tool execution, returning error status.  

## 4. Resource Dependencies  
- **Standard Libraries**: `typing` (for type hints).  
- **Internal Modules**: `functions` (imported as `func`).  
- **External Packages**: None.  

## 5. Configuration & Environment  
- **Hardcoded Constants**: None.  
- **Environment Lookups**: None.