

## 1. Architectural Role  
Provides ANSI color code constants and utility functions for applying text formatting and effects to terminal output.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `Color` | Class | Stores ANSI escape codes for text colors, backgrounds, and effects. |  
| `format_text` | Func | Applies a sequence of ANSI codes to text and resets terminal formatting. |  
| `pformat_text` | Func | Prints formatted text with ANSI codes, bypassing manual reset handling. |  

## 3. Execution Logic & Flow  
- **Initialization**: Class and function definitions are loaded, establishing ANSI code constants.  
- **Data Path**: No runtime data transformation; constants are pre-defined.  
- **Conditional Branching**: None; all logic is static.  

## 4. Resource Dependencies  
- **Standard Libraries**: `sys` (implicit via `print`/`f-string`).  
- **Internal Modules**: None.  
- **External Packages**: None.  

## 5. Configuration & Environment  
- **Hardcoded Constants**: ANSI escape sequences for colors, backgrounds, and effects.  
- **Environment Lookups**: None.