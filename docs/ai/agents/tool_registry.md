## Module Purpose
This file defines the `ToolRegistry` class, which provides functionality to register, describe, and execute various callable tools. It acts as a central repository for managing tool interactions within an agent system.

## Interface & Exports
*   Class: `ToolRegistry`
    *   Method: `register_tool(self, name: str, func_ref: Callable)`
    *   Method: `get_tool_info(self, name: str) -> str`
    *   Method: `execute_tool(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]`

## Internal Logic
The `ToolRegistry` class maintains an internal dictionary, `_tools`, mapping tool names (strings) to their callable references. The `register_tool` method adds new callable functions to this dictionary. The `get_tool_info` method retrieves the docstring of a registered tool, formats it with indentation, and returns a descriptive string. The `execute_tool` method dynamically calls a registered tool with provided parameters, logs the call using `func.log`, and encapsulates the result or any execution error within a status dictionary.

## Dependencies
*   `typing` (specifically `Dict`, `Any`, `Callable`)
*   `functions` (imported as `func`)

## Constants & Environment
None identified in source.