# AI Assistant CLI Documentation (v2.2.0)

This document covers the installation-free interaction with the AI Assistant. It is designed for both quick queries and complex automated pipelines.

---

## 1. Core Interaction Modes

The assistant's behavior changes based on which flags you provide:

* **Interactive Chat:** Triggered by running the script with no "task" arguments. It maintains a history and allows for back-and-forth conversation.
* **Direct Execution:** Triggered by `--msg`, `--task`, or `--task-file`. The AI answers the specific prompt and then exits immediately.
* **Agentic Workflow:** Triggered by `--agents`. This allows the AI to use "tools" (like searching files or running code) to complete a complex objective.
* **Piped Input:** If you pipe text into the command (e.g., `cat log.txt | ...`), the assistant automatically treats that text as the primary message.

---

## 2. Comprehensive Argument Reference

### Input & Triggers
| Argument | Shorthand | Logic & Usage |
| :--- | :--- | :--- |
| `--msg "text"` | `-m` | The primary way to send a one-off question. If used with `--file`, the message acts as the instruction for that file. |
| `--task "name"` | `-t` | Loads a template from `prompt_templates/task/`. You don't need the `.md` extension. *Example: `-t summarize`* |
| `--task-file "path"`| `-tf` | Similar to `--task`, but lets you point to any Markdown file on your system to use as the prompt. |
| `--agents` | | **Agent Mode.** If followed by a path (e.g., `--agents my_pipe.json`), it uses that config. If used as a flag alone, it uses the default pipeline. |

### Data Context (Adding Files)
| Argument | Shorthand | Logic & Usage |
| :--- | :--- | :--- |
| `--file "path"` | `-f` | Loads file content. Use commas for multiples: `-f "main.py,utils.py"`. |
| `--image "path"` | `-i` | Attaches images to the prompt. Requires a vision-capable model (like Llama 3.2-Vision or GPT-4o). |
| `--load-folder` | `-D` | Loads all files in a directory. **Note:** Pair this with `--ext` to avoid loading junk files. |
| `--ext "py"` | `-e` | Filters the `--load-folder` search. *Example: `-D ./src -e py` only loads Python files.* |

### Model & Environment Configuration
| Argument | Shorthand | Logic & Usage |
| :--- | :--- | :--- |
| `--model "name"` | `-md` | Points to a JSON file in your `models/` directory. *Example: `-md gemma-2.json`* |
| `--system "name"` | `-s` | Applies a persona/role from `prompt_templates/system/`. |
| `--system-file` | `-sf` | Loads a custom system/persona prompt from any file path. |
| `--list-models` | `-l` | Executes `ollama list` to show you what models are currently served on your machine. |

### Output & Debugging
| Argument | Shorthand | Logic & Usage |
| :--- | :--- | :--- |
| `--output-file` | `-o` | Instead of printing the answer to the screen, it saves it to this file. |
| `--no-out` | `-q` | Quiet mode. Suppresses the AI's response in the terminal (useful for automation scripts). |
| `--debug-console`| `-dc` | Prevents the terminal from clearing. Use this if you are getting errors and the screen wipes before you can read them. |
| `--print-log` | `-pl` | Shows background "INFO" messages (e.g., "Starting direct ask"). |
| `--print-chat` | `-p` | Replays a previous conversation log from the `logs/chat/` folder. |

---

## 3. Power-User Combinations

### The "Auditor" Pattern
Load a whole folder of code, apply a specific system persona, and save the result to a report:
```bash
python -m ai -D "./src" -e "js" -s "security_expert" -t "vulnerability_scan" -o "report.md"