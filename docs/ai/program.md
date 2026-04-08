## Module Purpose
This file defines the `Program` class, which serves as the main entry point and orchestrator for an AI assistant application, managing its configuration, chat interactions, LLM streaming, tool execution, and agent workflows. It is designed for stability and clean exit handling.

## Interface & Exports
*   `Program`: The primary class that encapsulates the entire application logic. It is instantiated and run directly when the script is executed.

## Internal Logic
The `Program` class orchestrates the AI assistant's operations through several key phases:
1.  **Initialization**: The `__init__` method sets up core attributes, including configuration, model parameters, chat state, and paths for session logs and workspace.
2.  **Configuration & Session Setup**: `load_config` loads the main program settings. `init_program` applies CLI arguments, initializes session-specific file paths (chat history, thinking logs, workspace), and instantiates utility managers like `ThinkingLogManager`, `OutputPrinter`, and `HandlerManager`.
3.  **Core Component Initialization**: The `init` method loads the system prompt, uses `ModelManager` to load