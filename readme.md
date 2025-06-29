# AI Assistant
================

A conversational AI assistant built with Python, supporting various AI models including Ollama and Hugging Face Transformers.

## Features
-------------

### Core AI Capabilities: NLP and Contextual Understanding

The AI Assistant's ability to engage in natural, coherent conversations, understand complex queries, and maintain context throughout a dialogue is powered by its flexible integration with diverse Large Language Models (LLMs). This pluggable architecture supports:

*   Ollama Server Models: For efficient, local inference, allowing you to run powerful models directly on your hardware. This provides robust Natural Language Processing (NLP) and contextual understanding without relying on external API calls.
*   Hugging Face Transformers Models: For access to a vast ecosystem of pre-trained and fine-tunable models. This enables the assistant to leverage state-of-the-art NLP techniques and deep contextual understanding across a wide range of tasks and model architectures (e.g., causal language models, sequence-to-sequence models).

### Versatile Model and Prompt Management

The AI Assistant supports multiple models and prompts, allowing users to choose the best configuration for their specific needs:

*   Multiple Models: Utilize large language models for complex queries or smaller models for simpler conversations.
*   Custom Prompts: Apply general conversation prompts or specialized system prompts to guide the AI's behavior and conversational style.

### Comprehensive File and Folder Support

The AI assistant can load and process large amounts of text data from files and folders, which is incredibly useful for tasks such as:

*   Analyzing large datasets
*   Generating reports or summaries
*   Creating chatbots or virtual assistants

## Usage
---------

The AI Assistant offers two primary modes of operation: an interactive chat mode for continuous conversation, and direct command-line execution for specific tasks or automated workflows.

### Interactive Chat Mode

If you run the program without specific task-oriented command-line arguments (like `--msg`, `--file`, `--task`, or `--generate-config`), it will launch into an interactive chat loop, allowing for continuous dialogue:

```sh
../run.sh
Welcome to the AI Assistant! What would you like to talk about?
> How can I help you?
(AI responds)
```

### Direct Command-Line Execution

For one-off questions, automated tasks, or configuration generation, you can pass arguments directly to the `run.sh` script. The program will execute the specified action and then exit (unless the action naturally leads to prolonged output, like `--print-chat`):

Example: Ask a direct question:

```sh
./run.sh --msg "What is the capital of Portugal?"
```

Example: Summarize a file and save the output:

```sh
./run.sh --file "my_document.txt" --task "summarize" --output-file "summary.md"
```

## CLI Options
--------------

The AI Assistant provides a comprehensive set of command-line interface (CLI) options to customize its behavior, control input/output, and trigger specific functionalities. These options are passed to the `run.sh` script.

### Model and Interaction Control

*   `--msg <message>` / `-m <message>`: Directly pass a single question or statement to the AI. The assistant will process this message and then exit.
*   `--model <model_name>` / `-md <model_name>`: Specify which AI model to use for the current session.
*   `--system <prompt_name>` / `-s <prompt_name>`: Apply a predefined system prompt (template name from `prompt_templates/system/`) to guide the AI’s persona or behavior.
*   `--system-file <filename>` / `-sf <filename>`: Load a system prompt from a specific file.

### Data Input Options

*   `--file <filename>` / `-f <filename>`: Load the content of a single text file and pass it as input to the AI.
*   `--image <image_file>` / `-i <image_file>`: Load an image file and pass it as input to the AI. Requires an AI model capable of multimodal (image understanding) capabilities.
*   `--load-folder <folder_name>` / `-D <folder_name>`: Load the content of multiple text files from a specified folder.
*   `--extension <extension>` / `-e <extension>`: Used with `--load-folder` to filter files by a specific extension (e.g., py, md, txt).

### Automated Tasks and Output

*   `--task <template_name>` / `-t <template_name>`: Execute a predefined task or template (name from `prompt_templates/task/`). This instructs the AI to perform a specific type of action (e.g., summarize, generate code, brainstorm).
*   `--task-file <filename>` / `-tf <filename>`: Load a task definition from a specific file.
*   `--output-file <filename>` / `-o <filename>`: Redirect the AI’s generated output to a specified file instead of printing it to the console.

### Program Control and Debugging

*   `--no-log` / `-q`: Suppress informational "log" messages from being printed to the console.
*   `--no-out`: Suppress the main AI output message from being printed to the console (useful when combined with `--output-file`).
*   `--debug`: Enable debug mode, which prevents the console from being cleared and may provide more detailed error traceback information.

## Model Configuration Generation
-------------------------------

Beyond the general usage, the AI Assistant provides specialized options for generating model configuration files. These files are crucial for defining how different AI models are loaded and behave within the application.

For detailed instructions on generating model configuration files, including available model types and examples, please refer to the dedicated Model Configuration Manager README.

## Contributing
--------------

If you’d like to contribute to this project, please fork the repository on GitHub and submit a pull request. I’m always happy to see suggestions or patches that could improve the Assistant’s functionality.

## License
---------

N/A

## Credits
----------

I’m the one who built this AI Assistant, and it’s been an absolutely fascinating journey! It’s incredibly rewarding to see all these different technologies – Python, sophisticated NLP techniques, and the power of Large Language Models – come together to create something like this.

I owe a *huge* debt of gratitude to the team at Ollama. Their platform and libraries have been instrumental in making the local model inference so smooth and efficient.  And I’m also incredibly impressed by the breadth and depth of the resources available through Hugging Face Transformers – a truly impressive ecosystem for anyone working with NLP.

This project really is a testament to the power of combining these incredible tools, and I'm so excited to share it with the community!  I’ve learned so much throughout this process, and I'm already thinking about ways to expand its capabilities.

## Contact
-------------

If you have any questions or need further assistance, please don't hesitate to reach out. You can contact me at [your email address] or through the GitHub issues page for this project.

## Acknowledgements
------------------

I’m incredibly grateful to the Ollama team for building such a fantastic AI model library, and to the entire Python community for their continuous innovation and support. It's a really inspiring environment to be a part of, and it makes projects like this possible.
