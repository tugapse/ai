

## 1. Architectural Role  
Manages text-to-voice conversion, handling code blocks and sentence segmentation for streaming output to a voice module.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `SpeechBridge` | Class | Coordinates text processing and voice output, managing code block state and sentence splitting |  
| `__init__` | Method | Initializes voice module, debug flag, buffer, and code block tracking |  
| `feed` | Method | Processes incoming text, splitting code blocks and sending text chunks to voice |  
| `_process_text_chunk` | Method | Cleans text (removes markdown), appends to buffer, and splits into sentences for voice output |  
| `flush` | Method | Sends remaining buffer content to voice if not in code block |  
| `_send_to_voice` | Method | Cleans text, formats debug output, and forwards to voice module |  
| `abort` | Method | Resets buffer, code block state, and aborts voice module |  
| `code_announcements` | List | Hardcoded phrases for announcing code blocks |  
| `sentence_regex` | Regex | Pattern for splitting text by sentence-ending punctuation |  

## 3. Execution Logic & Flow  
- **Initialization**: Sets `voice`, `debug`, `buffer`, `in_code_block`, and initializes `code_announcements` and `sentence_regex` |  
- **Data Path**: Input text  `feed` splits code blocks  `feed` or `_process_text_chunk` cleans text  appends to buffer  splits sentences via `sentence_regex`  sends chunks to voice via `_send_to_voice`  `flush` handles residual buffer content |  
- **Conditional Branching**:  
  - Code block detection (`"```"` in text) toggles `in_code_block` state and triggers code announcement |  
  - Sentence splitting via `sentence_regex` triggers chunk sending |  
  - Debug mode enables text formatting and logging |  

## 4. Resource Dependencies  
- **Standard Libraries**: `re`, `random`, `typing` |  
- **Internal Modules**: `color`, `functions` |  
- **External Packages**: None |  

## 5. Configuration & Environment  
- **Hardcoded Constants**:  
  - `code_announcements` list of 5 code-block announcement phrases |  
  - `sentence_regex` pattern for sentence splitting |  
- **Environment Lookups**: None |