Loading ..
**Ai Assistant Documentation**
============================

Introduction
------------

The Ai Assistant is a Python script that uses various AI models to assist users with their tasks and queries. The script can be used as a command-line tool or integrated into other systems.

**How to Use the Ai Assistant**

### Command-Line Interface

To use the Ai Assistant from the command line, follow these steps:

1. **Install Requirements**: Run `pip install ollama python-dotenv` to install the required packages.
2. **Run the Script**: Run `python init.py --msg "Your message here"` (replace `"Your message here"` with your query or task).
3. **Optional Arguments**:
	* `--model <model_name>`: Specify a specific AI model to use.
	* `--system <prompt_file>`: Use a custom system prompt file instead of the default one.
	* `--system-file <file_path>`: Load a custom system prompt file from the specified path.
	* `--list-models`: List all available AI models.
	* `--task <task_name>`: Load a task template from the `prompt_templates/task` directory.
	* `--task-file <file_path>`: Load a task template file from the specified path.
	* `--file <file_path>`: Load a text file and pass its contents as a message.

### Integrating with Other Systems

To integrate the Ai Assistant with other systems, follow these steps:

1. **Import the Script**: Import the `init.py` script in your Python application or framework.
2. **Create an Instance**: Create an instance of the `Program` class and call its `load_config()` method to configure the AI model and system prompt.
3. **Call the `main()` Method**: Call the `main()` method to start the Ai Assistant's chat loop.

### Configuration File

The Ai Assistant uses a configuration file (`config.json`) that can be customized to suit your needs. The file contains settings such as the default AI model, system prompts, and task templates.

**Customizing the Configuration File**

To customize the configuration file, follow these steps:

1. **Create a New File**: Create a new file named `config.json` in the root directory of your project.
2. **Edit the File**: Edit the file to add or modify settings as needed. For example, you can change the default AI model or add custom system prompts.

**Tips and Tricks**

* Use the `--list-models` argument to list all available AI models.
* Use the `--task` and `--task-file` arguments to load task templates from the `prompt_templates/task` directory.
* Use the `--file` argument to load a text file and pass its contents as a message.

**Troubleshooting**

If you encounter any issues while using the Ai Assistant, refer to the following troubleshooting steps:

1. **Check the Configuration File**: Verify that the configuration file is correctly formatted and contains the necessary settings.
2. **Check the AI Model**: Ensure that the selected AI model is properly installed and configured.
3. **Check the System Prompt**: Verify that the system prompt file is correctly formatted and contains the necessary information.

By following these steps and guidelines, you can effectively use the Ai Assistant to assist with your tasks and queries.
