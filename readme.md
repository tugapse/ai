
**Ai Assistant Documentation**
=============================

### Introduction

This AI assistant allows users to interact with a language model using natural language commands. It provides various features for loading config files, setting system prompts, executing tasks, reading and executing files, and handling direct questions from users.

### Command-Line Arguments

To use the AI assistant, you can run the script with various command-line arguments. Here are some examples:

#### Basic Usage

* `--list-models`: List available models for use
* `--model <model_name>`: Specify a model to use (e.g., "bloom-64b1a0")
* `--system <prompt_name>`: Pass a system prompt name (e.g., "my_system_prompt")
* `--system-file <filename>`: Pass a system prompt filename (e.g., "path/to/my/system/prompt.md")

#### Task Execution

* `--task <task_name>`: Execute a task with the specified name (e.g., "my_task")
* `--task-file <filename>`: Execute a task by loading a file (e.g., "path/to/my/task/file.md")

#### File Handling

* `--file <filename>`: Load and execute a file
* `--msg`: Pass a direct question to the AI assistant (e.g., "What is the meaning of life?")

### Examples

Here are some examples of how you can use this AI assistant:

```bash
# List available models
$ python ai_assistant.py --list-models

# Use a specific model
$ python ai_assistant.py --model <model_name>

# Set system prompt from file
$ python ai_assistant.py --system-file my_system_prompt.md

# Execute task with specified name
$ python ai_assistant.py --task my_task

# Pass a direct question to the AI assistant
$ python ai_assistant.py --msg "What is the meaning of life?"
```

### Functionality

The AI assistant includes the following functionality:

* Loading config files
* Setting system prompts
* Executing tasks
* Reading and executing files
* Handling direct questions from users
* Creating messages for the language model
