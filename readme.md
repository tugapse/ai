# AI Assistant
================
A conversational AI assistant built with Python and Ollama.

## Features
----------------
### Natural Language Processing (NLP)
The AI assistant uses natural language processing (NLP) to understand and respond to user input. This allows for more accurate and helpful responses, as well as the ability to handle complex queries and conversations.

### Contextual Understanding
The AI assistant is designed to understand context and follow a conversation. This means that it can keep track of what has been discussed previously and use this information to inform its responses.

### Multiple Models and Prompts
The AI assistant supports multiple models and prompts, allowing users to choose the best one for their needs. This includes options such as:

* Large language model: This is a powerful model that can handle complex queries and conversations.
* Small language model: This is a smaller model that is better suited for simple queries and conversations.
* General conversation prompt: This is a general-purpose prompt that can be used to start a conversation on any topic.

### File and Folder Support
The AI assistant supports loading files and folders, allowing users to pass in large amounts of text data. This can be useful for tasks such as:

* Analyzing large datasets
* Generating reports or summaries
* Creating chatbots or virtual assistants

### Output Options
The AI assistant provides several output options, including:

* Text: The default output format is plain text.
* JSON: The AI assistant can also output its responses in JSON format.
* CSV: The AI assistant can also output its responses in CSV format.

## Installation
-----------------
To install this project, simply run the following commands:
```bash
sudo apt install portaudio19-dev
sudo apt install python3-pip
pip install -r requirements.txt
```
## Ollama Integration
---------------------
This program also uses the Ollama application from ollama.com, which provides a powerful and flexible way to generate text based on user input. By integrating Ollama into this program, we can take advantage of its advanced language processing capabilities and provide even more accurate and helpful responses.

## Config File Option (Optional)
If you want to use a different configuration file, you can set an environment variable `AI_ASSISTANT_CONFIG_FILENAME` with the path to your desired config file. For example:

### Unix/Linux/MacOS
To set this environment variable on Linux/macOS systems, run the following command in your terminal:
```bash
export AI_ASSISTANT_CONFIG_FILENAME="/path/to/your/config.json"                                                                                                             
```                                                                                                                                                                         
This will allow you to specify a custom configuration file that overrides the default one used by the AI Assistant.

### Windows

1. Right-click on "Computer" or "This PC" and select "Properties".
2. Click on "Advanced system settings" (on older versions of Windows, click on "System Properties").
3. In the System Properties window, click on the "Environment Variables" button.
4. Under "User variables", click "New". Name the variable `AI_ASSISTANT_CONFIG_FILENAME` and set its value to the path of your desired config file (e.g., `C:\Path\To\Your\Config.json`).


## Usage
--------------
To use this program, simply run the `bin/{so required ext}` file from the command line. You can then interact with the AI assistant by typing commands and prompts.

Example usage:
```bash
$ bash bin/sh
Welcome to the AI Assistant! What would you like to talk about?
```
## CLI Options
----------------
The AI assistant provides several command-line interface (CLI) options that allow you to customize its behavior. These options include:

* `--msg <message>`: Direct question
* `--model <model_name>`: Model to use
* `--system <prompt_name>`: Pass a prompt name
* `--system-file <filename>`: Pass a prompt filename
* `--list-models`: See a list of models available
* `--file <filename>`/`--files <filename>`: Load a file and pass it as a message
* `--load-folder <folder_name>`/`--folder <folder_name>`: Load multiple files from folder and pass them as a message with file location and file content
* `--extension <extension>`/`--ext <extension>`: Provides File extension for folder files search
* `--task <template_name>`/`--task-file <filename>`: Name of the template inside prompt_templates/task, do not insert .md
* `--output-file <filename>`: Filename where the output of automatic actions will be saved

## Contributing
----------------
If you'd like to contribute to this project, please fork it on GitHub and submit a pull request. We welcome any suggestions or patches that can improve the functionality of this project.

## License
-------------
N/A

## Credits
--------------
* Fábio Almeida - Original Author
* Ollama - AI Model Library Used in This Project (https://ollama.com)
* Python - Programming Language Used to Develop this Project (https://www.python.org)


## Contact
--------------

If you have any questions or need further assistance, please don't hesitate to reach out. You can contact me at [your email address] or through the GitHub issues page for this project.

## Acknowledgments
-----------------

I would like to thank the Ollama team for providing their AI model library and for their support in developing this project.

## Changelog
--------------

* [Version 1.0]: Initial release of the AI assistant.
* [Version 1.1]: Added support for multiple models and prompts.
* [Version 1.2]: Improved language processing capabilities through integration with Ollama.

