**Ai Assistant Documentation**
=============================

Introduction
-------------

The Ai Assistant is a powerful tool that enables users to interact with AI models and perform various tasks. This documentation provides an overview of the Ai Assistant, its features, and how to use it.

Getting Started
----------------

To get started with the Ai Assistant, follow these steps:

1. **Install the Ai Assistant**: You can install the Ai Assistant by cloning this repository or downloading the zip file from GitHub.
2. **Load the Configuration File**: The Ai Assistant requires a configuration file (config.json) to function properly. This file contains settings such as the AI model name, system prompt file, and output file.
3. **Run the Ai Assistant**: Once you have loaded the configuration file, you can run the Ai Assistant by executing the `main.py` script.

Using the Ai Assistant
----------------------

The Ai Assistant provides several features that enable users to interact with AI models. Here are some of the key features:

* **Chat Mode**: The Ai Assistant allows users to engage in a conversation with an AI model. Users can type messages, and the AI model will respond accordingly.
* **File Input**: Users can input files (text or JSON) as prompts for the AI model.
* **Model Selection**: The Ai Assistant supports multiple AI models. Users can select the desired model using the `--model` option.
* **System Prompt**: The Ai Assistant uses a system prompt file to generate responses from the AI model.

Commands and Options
--------------------

The Ai Assistant provides several commands and options that enable users to customize its behavior. Here are some of the key commands:

* **-m, --msg**: Direct question for the AI model.
* **-model, --m**: Select a specific AI model.
* **-system, --s**: Pass a prompt name or file path.
* **-system-file, --sf**: Pass a system prompt file path.
* **-list-models, -lm**: List all available AI models.
* **-file, -f**: Load a file and pass it as a message.
* **-load-folder, -lf**: Load multiple files from a folder and pass them as messages with file location and content.
* **-extension, -e**: Provide the file extension for folder files search.
* **-task, -t**: Name of the template inside prompt_templates/task (do not insert .md).
* **-task-file, -tf**: Name of the template inside prompt_templates/task (do not insert .md).
* **-output-file, -of**: File name where the output of automatic actions will be saved.

Example Usage
--------------

Here is an example of how to use the Ai Assistant:

```
python main.py --msg "Hello, AI model!" --model "my_model" --system "prompt.md"
```

This command tells the Ai Assistant to load the `config.json` file, select the `my_model` AI model, and use the `prompt.md` system prompt file. The user can then engage in a conversation with the AI model by typing messages.

Troubleshooting
----------------

If you encounter any issues while using the Ai Assistant, refer to the troubleshooting section below:

* **Error: Unable to load configuration file**: Make sure that the `config.json` file is present in the same directory as the `main.py` script.
* **Error: Invalid AI model selection**: Check that the selected AI model exists and is correctly configured.

Conclusion
----------

The Ai Assistant is a powerful tool that enables users to interact with AI models. With its various features and options, it provides a flexible way to perform tasks and engage in conversations with AI models. By following this documentation, you should be able to get started with the Ai Assistant and start using it effectively.