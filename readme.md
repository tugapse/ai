# AI Assistant

![Version](https://img.shields.io/badge/version-2.2.0-orange)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A modular conversational AI framework built with Python. It provides a unified interface for **Ollama** and **Hugging Face Transformers**, supporting advanced file ingestion, autonomous agent workflows, and multimodal analysis.

---

## ✨ Features

* **Hybrid LLM Integration:** Toggle between Ollama (local inference) and Hugging Face (GGUF/PyTorch) models.
* **Autonomous Agents:** Enable tool-use for terminal execution, file manipulation, and smart searching.
* **Contextual Data Ingestion:** Load text data from individual files or entire directories for analysis, reporting, or code reviews.
* **Automated Task Pipeline:** Execute predefined logic (summarize, brainstorm, code) using prompt templates.
* **Multimodal Support:** Analyze images using vision-capable models (VLMs).
* **Flexible Interaction:** Persistent interactive chat mode or single-command CLI execution.

---

## 🤖 Autonomous Agents

The assistant includes an **Agentic Mode** that allows the LLM to interact with your system via a suite of tools. 

* **Toolbox:** Includes `smart_search`, `patch_file`, `execute_command`, and more.
* **Safety (HITL):** Sensitive operations require manual user authorization (Human-In-The-Loop) unless explicitly whitelisted.
* **Iteration:** Agents can self-correct and iterate through multiple steps to complete complex tasks.


> For a full list of available tools, safety configurations, and agentic workflows, please refer to the [**Agent Documentation**](docs/agents.md).

---

## ⚙️ Installation & Setup

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/tugapse/ai.git](https://github.com/tugapse/ai.git)
    cd ai
    ```

2.  **Install Dependencies:**
    The included installer automatically detects your hardware and configures the environment (including CUDA support).
    ```bash
    python install_deps.py --auto-accept
    ```

---

## 🚀 Usage

### Interactive Chat Mode
Run without arguments to start a continuous dialogue:
```bash
./run.sh
```

### Agent Mode (Autonomous)
Run the assistant with tool-access enabled:
```bash
./run.sh --agents --msg "Locate all .py files in /src and check them for security vulnerabilities."
```

### Direct Command Execution
**Ask a single question:**
```bash
./run.sh --msg "What is the capital of Portugal?"
```

**Summarize a file and save the output:**
```bash
./run.sh --file "document.txt" --task "summarize" --output-file "summary.md"
```

**Analyze a source folder:**
```bash
./run.sh --load-folder "./src" --ext "py" --task "code_review"
```

---

## 📖 CLI Reference

### Model & Interaction
| Flag | Alias | Description |
| :--- | :--- | :--- |
| `--agents` | | Enable Agentic Mode (allows tool-use and autonomous iterations). |
| `--msg` | `-m` | Direct question or statement. |
| `--model` | `-md` | Model config filename (e.g., `gemma-2b.json`). |
| `--system` | `-s` | Name of a predefined system prompt template. |
| `--system-file` | `-sf` | Path to a specific system prompt `.md` file. |
| `--list-models` | `-l` | List all available model configurations. |

### Data & Files
| Flag | Alias | Description |
| :--- | :--- | :--- |
| `--file` | `-f` | Pass a text file's content as a message. |
| `--image` | `-i` | Pass an image file (requires multimodal model). |
| `--load-folder` | `-D` | Load multiple files from a directory. |
| `--ext` | `-e` | Filter folder search by extension (e.g., `py`, `md`). |

### Automation & Debugging
| Flag | Alias | Description |
| :--- | :--- | :--- |
| `--task` | `-t` | Execute a prompt template from `prompt_templates/`. |
| `--output-file` | `-o` | Redirect AI output to a specific file. |
| `--print-log` | `-pl` | Show informational log messages. |
| `--no-out` | `-q` | Suppress the main AI response in the console. |
| `--debug-console`| `-dc` | Disable console clearing and show full debug logs. |

---

## 🔧 Model Configuration Generation

The AI Assistant provides specialized options for generating model configuration files, defining how models are loaded and behave within the application.

**Generate a new configuration:**
```bash
python main.py --generate-config "new_model" --model-type "gguf"
```

* **--generate-config:** Specify the filename to save the new JSON config (you can ommit .json).
* **--model-type:** Choose the architectural type (`ollama`, `causallm`, or `gguf`).

For detailed instructions on configuration parameters, refer to the [**Model Configuration Manager README**](docs/MODEL_CONFIG.md).

---

## ❤️ Credits & Acknowledgements

* **Ollama:** For providing the foundation for local model serving.
* **Hugging Face:** For the Transformers ecosystem and GGUF support.
* **The Python Community:** For continuous innovation in AI tooling.

---

## 📄 License
MIT

## 📧 Contact
**Maintainer:** Fabio Almeida 
**Email:** tugapse@gmail.com