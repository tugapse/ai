# JARVIS AI

![Version](https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Ftugapse%2Fai%2Fmaster%2Fpyproject.toml&query=%24.project.version&label=version&color=orange)
![Python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue)
![License](https://img.shields.io/badge/license-MIT-green)

My own JARVIS-style personal assistant: it runs on my machine, uses my models, and can actually do things for me.

```
      ██╗  █████╗  ██████╗  ██╗   ██╗ ██╗ ███████╗      █████╗  ██╗
      ██║ ██╔══██╗ ██╔══██╗ ██║   ██║ ██║ ██╔════╝     ██╔══██╗ ██║
      ██║ ███████║ ██████╔╝ ██║   ██║ ██║ ███████╗     ███████║ ██║
 ██   ██║ ██╔══██║ ██╔══██╗ ╚██╗ ██╔╝ ██║ ╚════██║     ██╔══██║ ██║
 ╚█████╔╝ ██║  ██║ ██║  ██║  ╚████╔╝  ██║ ███████║     ██║  ██║ ██║
  ╚════╝  ╚═╝  ╚═╝ ╚═╝  ╚═╝   ╚═══╝   ╚═╝ ╚══════╝     ╚═╝  ╚═╝ ╚═╝

  JUST A REASONING VIRTUAL INTELLIGENT SENTINEL AGENTIC INTERFACE
```
<sub>The startup banner. Yes, the acronym was reverse-engineered.</sub>

---

## Why

Like a lot of people, I watched Iron Man and wanted a JARVIS of my own.
Not a chatbot in a browser tab, but an assistant that lives on *my* machine, runs *my* models,
knows my projects, talks back, and can actually do things for me.

JARVIS AI is that project. It started in April 2024 as a small script to ask a local Ollama
model questions from the terminal and run a few prompt "tasks" (the very first one commented PHP
code). Since then it has grown, one evening at a time, into something closer to the original idea:
agents that read and edit code and run commands, a voice, a web interface I use from my phone and
tablet, memory between sessions, and a "brain" server so the big model can run on the machine with
the GPU while I work from another one.

It's a pet project: an idea I like, built for fun and out of passion. It's not a product or a
framework, and it changes a lot. It's open source in case it's useful or fun for someone else.

## What it can do today

- **Chat** with local or remote models: Ollama, GGUF (llama.cpp), Hugging Face Transformers,
  OpenAI-compatible APIs, Gemini, or another JARVIS running as a server.
- **One-off tasks** from the terminal: ask a question, summarize a file, review a folder, look at an
  image, pipe text in and out.
- **Agents** that read and edit files, search code, run shell commands, search the web and send
  desktop notifications. Risky actions ask for your approval first.
- **Remember**: project knowledge generated from your code, plus long-term memory between sessions.
- **Talk**: text-to-speech voice (VibeVoice), including Portuguese.
- **Brain Server**: run the models on one machine and use them from the terminal on another, or from
  the web UI on your phone or tablet.
- **Extend** it with your own Python tools and MCP servers (`ai mcp`).

## Status

- Personal project, one maintainer, developed in bursts. Expect breaking changes.
- Developed on Linux. Windows works (there's a build for it) but gets less testing.
- Not tied to one model: I use as many as I can, because each one is better at different things.
  Results depend a lot on the model you pick: small local models work, but agents do much better
  with bigger ones.

---

## Getting started

### Install (Linux)

```bash
git clone https://github.com/tugapse/ai.git
cd ai
./build.sh            # creates .venv and installs the base dependencies
./run.sh install    # pick the engines you want (GGUF, Ollama, OpenAI, Gemini, server, memory, voice...)
```

`ai install` is interactive. GPU builds and troubleshooting: [Installation](guide/09-installation.md).

### Install (Windows)

```powershell
.\build.ps1           # set up the environment
.\compile.ps1         # optional: build dist\ai.exe
```

`ai.exe` needs the `.venv` folder next to it; run `.\ai.exe install` to add engines.

### Where your settings live

On the first run JARVIS copies its default config and templates into `~/Ai`. To use another folder,
set `AI_ASSISTANT_DIRECTORY`:

```bash
export AI_ASSISTANT_DIRECTORY="/path/to/my/ai-folder"
```

What's in that folder and every setting: [Configuration](guide/08-configuration.md).

### First steps

```bash
./run.sh                                   # interactive chat
./run.sh -m "What is the capital of Portugal?"
./run.sh -f notes.txt -m "Summarize this" -o summary.md
./run.sh -D ./src -e py -m "Review this code for bugs"   # load a folder into the context
./run.sh -f app.py -t create-comment -o app.commented.py   # run a task (prompt template)
./run.sh -i photo.png -m "What's in this picture?"
git diff --staged | ./run.sh -t commit                     # pipe text in
./run.sh agent                                 # chat with the agents
./run.sh agent -m "Find the TODOs in src and list them by file"
```

`./run.sh` runs from the checkout. If you installed the package, the same command is `ai`.

---

## A quick tour

**Agents.** `ai agent` gives the model tools: read and edit files, search code, run commands, search
the web, send notifications. It opens a chat that shows each tool call as it happens; risky ones
(`execute_command`, `write_file`, `patch_file`, `delete_file`) wait for your OK. Sessions are saved
per folder (`ai agent --resume`), and pipelines (`default`, `small`, `multi`) decide which agents
take part. → [Agents](guide/03-agents.md)

**Tools.** Built-in categories (filesystem, search, shell, web, notify, knowledge, memory), MCP
servers (shipped disabled: `ai mcp enable NAME`) and your own Python tools in
`<AI dir>/user/tools/` (`ai tools create NAME` makes a skeleton). → [Tools](guide/04-tools.md)

**Knowledge & memory.** `ai knowledge build` has the model document a project once (a summary,
symbols and dependencies per file), so agents start from that instead of exploring from scratch.
Long-term memory keeps decisions, preferences and a summary of each finished turn.
→ [Knowledge & memory](guide/05-knowledge-memory.md)

**Brain Server.** `ai server` serves the models, agents and a web UI from the machine with the GPU.
Phones, tablets and other PCs on your network pair with it once; another machine's CLI can use it
as a model (`"model_type": "jarvis"`), or run its own agents and send only inference there
(`ai server --relay URL`). → [Server](guide/07-server.md)

**Commands.** `ai --help` lists them, `ai COMMAND --help` explains one:

```
ai agent · ai sessions list · ai knowledge build|list|forget · ai models list|generate
ai tools create · ai mcp list|enable|disable · ai server [totp-setup|frontend]
ai install · ai config reset
```

Every command and option: [Command-line reference](guide/01-interfaces.md#command-line-reference).

---

## How it's organised

```
 Interfaces     CLI · chat · agent chat · web UI · voice
 Program        startup, services, events, modules
 Agents         pipelines, agent loop, context management
 Tools          categories, built-in tools, MCP, your tools   │  Knowledge & memory
 Models         Ollama · GGUF · HF · OpenAI · Gemini · JARVIS
 Server         Brain Server · relay · API · auth · web UI
```

Each layer has a page in the [guide](guide/index.md):
[Interfaces](guide/01-interfaces.md) ·
[Program](guide/02-program.md) ·
[Agents](guide/03-agents.md) ·
[Tools](guide/04-tools.md) ·
[Knowledge & memory](guide/05-knowledge-memory.md) ·
[Models](guide/06-models.md) ·
[Server](guide/07-server.md) ·
[Configuration](guide/08-configuration.md) ·
[Installation](guide/09-installation.md) ·
[Development](guide/10-development.md).

Per-file docs generated by the model live in `_docs/`, and `docs/` holds a viewer for the knowledge.

## What's next

No big promises. The focus for now is:
- making the system more stable;
- quality-of-life improvements (to be defined as I go).

## License

MIT

## Contact

**Maintainer:** Fabio Almeida · tugapse@gmail.com
