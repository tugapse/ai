# 1. Interfaces

The ways to talk to JARVIS, and when to use each.

| Interface | Start it with | Best for |
|-----------|---------------|----------|
| [One-shot CLI](#one-shot-cli) | `./run.sh -m "..."`, `-f`, `-t`, pipes | Quick questions, scripts, tasks on files |
| [Chat](#chat) | `./run.sh` | A conversation with the model, no tools |
| [Agent chat](#agent-chat) | `./run.sh agent` | Work on a project: read, edit, run, search |
| [One-shot agent](#one-shot-agent) | `./run.sh agent -m "..."` | A single agent task from a script or another terminal |
| [Web UI](#web-ui) | `./run.sh server`, then a browser | Phone, tablet, or another PC |
| [Voice](#voice) | `"VOICE_ENABLED": true` | Hearing the answers |

All commands and options: [Command-line reference](#command-line-reference).

---

## One-shot CLI

Send one message, print the answer, exit.

```bash
./run.sh -m "What is the capital of Portugal?"
./run.sh -f notes.txt -m "Summarize this" -o summary.md
./run.sh -D ./src -e py -m "Review this code for bugs"
./run.sh -i photo.png -m "What's in this picture?"
./run.sh -f app.py -t create-comment -o app.commented.py
git diff --staged | ./run.sh -t commit
```

How the message is put together: the task (`-t` / `-tf`), then anything piped in, then `-m`.
Files (`-f`, `-D`) and images (`-i`) are added as context.

**Pipes.** JARVIS reads stdin only when something is actually piped in, and doesn't hang if a
parent process leaves stdin open without writing to it: with no other prompt it waits for the pipe;
with `-m` or `-t` it waits at most `AI_STDIN_WAIT` seconds (default 3) for the first byte.

**Output.** `-o FILE` writes the answer to a file; `-q` prints nothing; `-nta` turns off the
thinking animation (useful in scripts and logs).

## Chat

```bash
./run.sh
./run.sh --model chat/default --system-file my-persona.md
```

A conversation with the model, with streaming answers.

| Input | Action |
|-------|--------|
| `Enter` | Send |
| `Alt+Enter` | Toggle multi-line mode (then `Enter` adds lines; `Alt+Enter` again to finish) |
| `@path` | Stage a file; it's attached to your next message (Tab completes paths) |
| `/clear` | Clear the conversation |
| `/save NAME` | Save the conversation to `<AI folder>/sessions/chat/NAME.json` |
| `/load NAME` | Load a saved conversation (it's printed again) |
| `/list` | List the saved conversations |
| `/agent` | The next message is run as an agent task |
| `Ctrl+C` / `Ctrl+D` | Exit |

Chat mode is a plain conversation: the model isn't given the tool list. For tool use, use the
agent chat. If long-term memory is enabled, chat messages are stored as memories (`chat_turn`).

## Agent chat

```bash
./run.sh agent
./run.sh agent --resume
```

A multi-turn chat with the agent pipeline. While it works you see its status line, tool calls,
results and approval requests inline. You can keep typing: messages sent while it's busy are
queued.

Keys and commands:

| Key / command | Action |
|---------------|--------|
| `Enter` | Send (queued if busy) |
| `Ctrl+J` / `Alt+Enter` | New line |
| `Esc` | Interrupt the running turn |
| `Ctrl+C` | Interrupt; exit when idle |
| `Ctrl+D` | Exit on an empty line |
| `@path` | Attach a file (Tab completes) |
| `/help` | Commands and keys |
| `/clear` | Start a fresh session |
| `/resume` | List or resume saved sessions |
| `/session` | Show the current session |
| `/pipeline [name]` | Show or switch the pipeline |
| `/tools` | Tools available to each agent |
| `/thoughts` | Toggle showing the agents' reasoning |
| `/exit`, `/quit` | Quit |

How agents work is in [Agents](03-agents.md).

## One-shot agent

```bash
./run.sh agent -m "Find the TODOs in src and list them by file"
./run.sh agent -t release/start
```

Runs one turn with the same renderer as the agent chat, then exits. If the agent asks you
something, the session is saved; continue it with `./run.sh agent --resume`. Approvals are still asked on
the terminal.

## Web UI

Start the Brain Server on the machine with the model, then open `http://<server-ip>:9999` on any
device on your network (pair it once with the code the server prints). It has chat, agent runs with
approvals, saved sessions, a pipeline editor and knowledge search. See [Server](07-server.md).

## Voice

JARVIS can speak its answers with VibeVoice (Microsoft's realtime text-to-speech).

1. Install the engine: `./run.sh install` → *Voice Module (Realtime TTS)*. It needs PyTorch,
   `pyaudio` (on Linux usually `portaudio` from your package manager first), and works best with
   CUDA.
2. In `config.json`:
   ```json
   { "VOICE_ENABLED": true, "VOICE_FILE": "pt-Spk1_man" }
   ```
3. Chat as usual; answers are spoken as they stream. `Ctrl+C` stops the voice too.

**Voices** are `.pt` files in `assets/voices/` (in the repo), taken from Microsoft's VibeVoice demo
voices. Shipped: `pt-Spk1_man` (the default), `pt-Spk0_woman`, `en-Carter_man`, `en-Davis_man`,
`en-Frank_man`, `en-Mike_man`. More (German, French, Italian, Japanese, Korean, Dutch, Polish,
Spanish…) are in [microsoft/VibeVoice `demo/voices/streaming_model`](https://github.com/microsoft/VibeVoice/tree/main/demo/voices/streaming_model):
put the `.pt` file in `assets/voices/` and set `VOICE_FILE` to its name. If the chosen voice isn't
found, the first available one is used.

It's text-to-speech only: JARVIS doesn't listen yet.

---

## Command-line reference

Every command also has its own help: `ai COMMAND --help` (e.g. `ai knowledge build --help`).

```
ai [OPTIONS]                 chat, or one-shot with -m / -t / -f ...
ai COMMAND [OPTIONS]         agent, sessions, knowledge, models, tools, server, install, config
ai COMMAND --help            help for one command
```

### Commands

| Command | What it does |
| :--- | :--- |
| `ai agent` | Agent chat; with `-m`/`-t`, one turn then exit. Options: `--resume [ID]` (`-r`), `--pipeline NAME` (`-ppl`), `--session-id ID`, `--knowledge PATH` (`-kb`, repeatable). Takes the options below too. |
| `ai sessions list` | Saved agent sessions of this folder. |
| `ai knowledge build [SRC]` | Generate knowledge for this folder. Options: `--mode missing\|changed\|all\|diff[:branch]`, `--only docs\|knowledge`, `--ext`, `--files`, `--max`, `--force`, `-md MODEL`. |
| `ai knowledge list` | Knowledge registered for this folder, and coverage. |
| `ai knowledge forget ID` | Stop loading a knowledge source for this folder. |
| `ai models list` | Available model configs (user and system). |
| `ai models generate NAME --type TYPE` | New model config in `user/models/`. Types: `ollama`, `causal_lm`, `seq2seq_lm`, `gguf`, `gemini`, `openai`, `jarvis`. |
| `ai tools create NAME` | Skeleton for your own tool in `user/tools/`. |
| `ai mcp list` / `enable NAME` / `disable NAME` | MCP servers (browser, GitHub…): shipped disabled, turn on what you use. |
| `ai server` | Start the Brain Server. `--relay URL`: run here, inference on the Brain Server at URL. `--modules ...`: server sub-modules. |
| `ai server frontend list` / `use VERSION\|bundled` | Web UI versions. |
| `ai server totp-setup` | Authenticator secret for approving risky web agent tools. |
| `ai install` | Install or remove optional engines. |
| `ai config reset` | Reset `config.json` to the defaults and copy missing templates. |

### Options (chat, one-shot and `ai agent`)

| Option | Alias | Description |
| :--- | :--- | :--- |
| `--msg` | `-m` | Send one message and print the answer. |
| `--model` | `-md` | Model config to use. |
| `--system` | `-s` | System prompt by name (inside `system/system-prompt/`). |
| `--system-file` | `-sf` | System prompt from a file. |
| `--task` | `-t` | Run a task (prompt template from `user/task/`). |
| `--task-file` | `-tf` | Run a task from a file. |
| `--output-file` | `-o` | Write the answer to a file. |
| `--file` | `-f` | Add a file to the context. |
| `--load-folder` | `-D` | Add a folder to the context. |
| `--ext` | `-e` | Only load files with these extensions. |
| `--image` | `-i` | Add an image (needs a vision model). |
| `--print-chat` | `-p` | Print a saved chat history. |
| `--print-log` | `-pl` | Show logs. |
| `--print-debug` | `-pdb` | Show debug logs. |
| `--no-out` | `-q` | Don't print to the terminal. |
| `--no-think-anim` | `-nta` | Disable the thinking animation. |
| `--debug-console` | `-dc` | Don't clear the screen. |
| `--version` | `-v` | Show the version. |
| `--show-logo` | | Show the banner. |

The old flags (`--agent`, `--server`, `--build-knowledge`, `--list-models`, `--install`…) still
work and print the new form to use.

---

## Code map

| File | Role |
|------|------|
| `src/ai/main.py` | Startup. |
| `src/ai/cli/` | The command line: sub-commands (`agent`, `server`, `knowledge`...), one file per group. |
| `src/ai/cli_args.py` | Dispatches the run: group handlers, server, agent, one-shot. |
| `src/ai/direct.py` | One-shot `ask()`. |
| `src/ai/stdin_reader.py` | Safe stdin reading. |
| `src/ai/chat/chat.py` | Chat prompt (prompt_toolkit), multi-line, `@file`, `/clear`, `/agent`. |
| `src/ai/agents/chat_ui/` | Agent chat: app, renderer, commands, session picker, one-shot runner. |
| `src/ai/modules/voice/` | VibeVoice module and the speech bridge. |
| `src/ai/services/stream_orchestrator.py` | Streams answers to the screen (and to the voice). |
