# AI Assistant

![Version](https://img.shields.io/badge/version-3.2.0-orange)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A modular conversational AI framework built with Python. It provides a unified interface for **Ollama** and **Hugging Face Transformers**, supporting advanced file ingestion, autonomous agent workflows, and multimodal analysis.

---

##  Features

* **Hybrid LLM Integration:** Toggle between Ollama and Hugging Face (GGUF/PyTorch) or openapi and gemini models.
* **Autonomous Agents:** Enable tool-use for terminal execution, file manipulation, and smart searching.
* **Contextual Data Ingestion:** Load text data from individual files or entire directories for analysis, reporting, or code reviews.
* **Automated Task Pipeline:** Execute predefined logic (summarize, brainstorm, code) using prompt templates.
* **Multimodal Support:** Analyze images using vision-capable models (VLMs).
* **Flexible Interaction:** Persistent interactive chat mode or single-command CLI execution.

---

##  Autonomous Agents

The assistant includes an **Agentic Mode** that allows the LLM to interact with your system via a suite of tools. 

* **Toolbox:** Includes `smart_search`, `patch_file`, `execute_command`, and more.
* **Safety (HITL):** Sensitive operations require manual user authorization (Human-In-The-Loop) unless explicitly whitelisted.
* **Iteration:** Agents can self-correct and iterate through multiple steps to complete complex tasks.


> For a full list of available tools, safety configurations, and agentic workflows, please refer to the [**Agent Documentation**](docs/agents/agent.md).

---

##  Installation & Setup

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/tugapse/ai.git
    cd ai
    ```

2.  **Install Dependencies:**
    The integrated installer automatically detects your hardware and configures the environment.
    ```bash
    ./build.sh
    ```

---

##  Usage

### Interactive Chat Mode
Run without arguments to start a continuous dialogue:
```bash
./run.sh
```

### Agent Mode (Autonomous)
Run the assistant with tool-access enabled:
```bash
./run.sh --agent --msg "Locate all .py files in /src and check them for security vulnerabilities."
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
Running a task from user/tasks folder
```bash
./run.sh --load-folder "./src" --ext "py" --task "code_review"
```

---

##  CLI Reference

### Cognitive Protocols
| Flag | Alias | Description |
| :--- | :--- | :--- |
| `--help` | `-h` | Show the diagnostic help message. |
| `--msg` | `-m` | Direct inquiry to the sentinel. |
| `--model` | `-md` | Specify neural model configuration. |
| `--system` | `-s` | Load named system persona from user/system folder. |
| `--system-file` | `-sf` | Inject system prompt from disk. |
| `--list-models` | `-l` | Audit available neural models. |

### Asset & Context Management
| Flag | Alias | Description |
| :--- | :--- | :--- |
| `--file` | `-f` | Analyze target file. |
| `--image` | `-i` | Process visual input from image path. |
| `--load-folder` | `-D` | Ingest directory into context. |
| `--ext` | `-e` | Filter context ingestion by extension. |

### Autonomous Operations
| Flag | Alias | Description |
| :--- | :--- | :--- |
| `--agent` | | Enable agentic logic injection. |
| `--task` | `-t` | Load named directive from user/tasks folder.|
| `--task-file` | `-tf` | Load directive from file. |
| `--pipeline` | `-ppl` | Define multi-stage instruction pipeline. (defaults to default.json) |
| `--session-id`| | LTM (Long Term Memory) session key. |
| `--output-file` | `-o` | Designate clean output stream (temp-file mode). |

### Distributed Architecture
| Flag | Alias | Description |
| :--- | :--- | :--- |
| `--server` | | Initialize Brain Server module. |
| `--modules` | | Load specific sub-modules. <module_name> |

### System Debug & Maintenance
| Flag | Alias | Description |
| :--- | :--- | :--- |
| `--version` | `-v` | Display the system version and exit. |
| `--show-logo` | | Display the JARVIS startup logo. |
| `--print-chat` | `-p` | Output session history. |
| `--print-log` | `-pl` | Enable system telemetry logs. |
| `--print-debug`| `-pdb` | Enable verbose debug stream. |
| `--no-out` | `-q` | Quiet mode (suppress terminal output). |
| `--no-think-anim`| `-nta` | Disable reasoning animations. |
| `--debug-console`| `-dc` | Lock console (disable clear-screen). |
| `--install` | | Execute dependency sync protocol. |
| `--overwrite-config`| | Force configuration and templates overwriting. |
| `--create-tool` | | Create a new user tool skeleton file. |

---

##  Model Configuration Generation

The AI Assistant provides specialized options for generating model configuration files, defining how models are loaded and behave within the application.

**Generate a new configuration:**
```bash
python main.py --generate-config "new_model" --model-type "gguf"
```

* **--generate-config:** Specify the filename to save the new JSON config (you can ommit .json).
* **--model-type:** Choose the architectural type (`ollama`, `causallm`, `gguf`, `gemini`, `openai`).

For detailed instructions on configuration parameters, refer to the [**Model Configuration Manager README**](docs/model_config_manager.md).

---


##  License
MIT

##  Contact
**Maintainer:** Fabio Almeida 
**Email:** tugapse@gmail.com