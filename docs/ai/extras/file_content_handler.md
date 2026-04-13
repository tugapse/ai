

## 1. Architectural Role  
Handles extraction and saving of file content from LLM token streams within <file> tags to a specified output directory.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `FileContentHandler` | Class | Processes LLM tokens to extract and save file content enclosed in <file> tags. |  
| `process_token` | Method | Parses raw tokens, accumulates file content, and suppresses output during file processing. |  
| `save_file` | Method | Writes extracted file content to disk using configured output directory. |  

## 3. Execution Logic & Flow  
- **Initialization**: Sets `_is_active` to False, initializes buffer and metadata, creates output directory if provided.  
- **Data Path**: Raw tokens  cleaned buffer  tag detection  content accumulation  file save on closing tag.  
- **Conditional Branching**:  
  - Checks for `</file>` tag to finalize file saving.  
  - Detects `<file>` tag to start content accumulation.  
  - Determines file extension via MIME type mapping or attribute defaults.  
  - Handles fragmented tags across tokens via `_token_accumulation_buffer`.  

## 4. Resource Dependencies  
- **Standard Libraries**: `re`, `os`, `functions`.  
- **Internal Modules**: `extras.thinking_log_manager.ThinkingLogManager`.  
- **External Packages**: None.  

## 5. Configuration & Environment  
- **Hardcoded Constants**:  
  - `MIME_TYPE_TO_EXT` mapping for MIME type  extension.  
  - Regex patterns for tag detection and control character cleaning.  
- **Environment Lookups**: None.