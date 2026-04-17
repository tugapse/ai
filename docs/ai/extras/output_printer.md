

## 1. Architectural Role  
Manages LLM output token printing modes with buffering logic for line-based and token-thresholded streaming, ensuring consistent console output formatting.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `OutputPrinter` | Class | Orchestrates token printing based on configured mode (token, line, every_x_tokens, line_or_x_tokens). |  
| `__init__` | Method | Initializes print mode and token-per-print threshold, resets buffers. |  
| `process_and_print` | Method | Processes and prints a single token, handling buffering and mode-specific logic. |  
| `flush_buffers` | Method | Clears remaining buffered content for non-line modes at stream end. |  
| `process_token` | Method | Core logic for token processing, determining when to output buffered content. |  
| `flush` | Method | Returns any remaining buffered content for post-stream capture. |  

## 3. Execution Logic & Flow  
- **Initialization**: Sets `print_mode`, `tokens_per_print`, and initializes buffers (`line_buffer`, `token_buffer`, `buffered_token_count`).  
- **Data Path**: Input token  `process_token` (buffers or outputs based on mode)  `process_and_print` (sends to `func.out`)  `flush` (captures residual buffer).  
- **Conditional Branching**:  
  - `print_mode` == "token": Direct output.  
  - `print_mode` == "line": Buffers until newline, splits and outputs line-by-line.  
  - `print_mode` == "every_x_tokens": Buffers until token threshold, then outputs.  
  - `print_mode` == "line_or_x_tokens": Prioritizes newline over token threshold.  

## 4. Resource Dependencies  
- **Internal Modules**: `functions` (via `func`).  
- **Standard Libraries**: None.  
- **External Packages**: None.  

## 5. Configuration & Environment  
- **Hardcoded Constants**: `"token"`, `"line"`, `"every_x_tokens"`, `"line_or_x_tokens"`, `tokens_per_print` (default 5).  
- **Environment Lookups**: None.