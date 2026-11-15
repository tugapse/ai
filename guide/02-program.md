# 2. Program

What happens between typing `./run.sh ...` and the first answer, and the building blocks the rest of
JARVIS is made of: config, modules, events and the process registry. Mostly for developers.

- [Startup](#startup)
- [Modes](#modes)
- [Modules](#modules)
- [Events](#events)
- [Process registry](#process-registry)
- [Services](#services)
- [Code map](#code-map)

---

## Startup

```
run.sh  (activates .venv, sets PYTHONPATH=src)
  └─ main.run()
       1. parse arguments                          main.load_args() → ai.cli.parse_args()
       2. check dependencies, silence warnings
       3. load config                              ProgramConfig.load()  → AI folder, config.json
       4. Program()  +  prog.load_config(args)     CLI flags override config
       5. register in the process registry         ProcessManager.start()
       6. maintenance command?  ──yes──► CliArgs.parse_args() → run it → exit
          (install, server, models, tools, sessions list, knowledge list/forget, ...)
          each command group lives in src/ai/cli/<group>.py
       7. prog.init_config(), prog.init_program()  modules, model, tools
       8. CliArgs.parse_args()                     agent → agent chat / one-shot agent
                                                   -m / -f / -t → one-shot answer
       9. prog.run()                               otherwise: interactive chat
     finally: prog.shutdown(), leave the registry
```

`SIGINT` / `SIGTERM` trigger a graceful shutdown (model unloaded, MCP servers stopped).

`ai` (the installed entry point) runs the same `main.run()`.

## Modes

Each instance has a mode, shown in the process registry:

| Mode | When |
|------|------|
| `server` | `ai server` / `ai server --relay` |
| `maintenance` | `ai install`, `ai config reset`, `ai models generate`, `ai models list`, `--print-chat`, `ai tools create`, `ai server totp-setup`, `ai server frontend`, `ai knowledge list`, `ai knowledge forget`, `ai sessions list` |
| `agent` | `ai agent` (also the old `--agent`, `--resume`, `--pipeline`) |
| `chat` | everything else (chat and one-shot) |

## Modules

Optional parts of JARVIS are **modules**, loaded by `ModuleRegistry` at startup:

| Module | Loads | Enabled |
|--------|-------|---------|
| `tools_filesystem`, `tools_search`, `tools_shell`, `tools_web`, `tools_notify` | Built-in tool categories | by default |
| `knowledge` | Project knowledge store and tools | by default |
| `vector_memory` | Long-term memory | when its engine is installed |
| `voice` | VibeVoice text-to-speech | `VOICE_ENABLED: true` |

Each module is switched by `<NAME>_ENABLED` in `config.json` (e.g. `TOOLS_WEB_ENABLED: false`,
`VOICE_ENABLED: true`). Modules that need an engine check `installed_engines.json` first and log
"Run --install" (`ai install`) if it's missing.

A module subclasses `BaseModule` (`src/ai/modules/base_module.py`) and follows its lifecycle
(initialize, get the instance, shut down). Tool modules are `ToolModule`s: a module that is also a
`ToolCategory`, so its tools reach the agents (see [Tools](04-tools.md)).

Adding a module today means adding it to the manifest in `ModuleRegistry.__init__`; there's no
plugin discovery.

## Events

Many classes extend `Events` (`src/ai/core/events.py`): a tiny publish/subscribe helper with
`add_event(name, callback)` and `trigger(name, data)`. It connects the chat prompt to the program
(message sent, agent run requested), the orchestrator to the UIs (before/after model calls), and the
model streams to the output and voice.

The agent loop has its own typed event channel, `AgentIO` (`src/ai/agents/agent_io.py`): status,
messages, tool calls and results, questions and permission requests. The terminal chat, the
one-shot renderer and the web server each implement it, so the same orchestrator drives all three.

## Process registry

Every running JARVIS writes a small status file and holds a lock on it while alive:

```
pid:      3868145
mode:     agent
install:  /home/user/Code/ai
started:  2026-11-13 21:02:11
model:    gemma4
activity: [3/20] coder: Implement the config parser
endpoint: http://127.0.0.1:9999        (server mode only)
```

Files live in `$XDG_RUNTIME_DIR/jarvis/pids/` (or `<temp>/jarvis-<uid>/pids/`). Other instances
read them to know what's running: the [GPU advisor](06-models.md#when-the-model-doesnt-fit-in-the-gpu)
uses them to offer a running server instead of loading a second copy of a model, and the server
avoids swapping a model out from under running work. A file whose lock can be taken belongs to a
dead process and is cleaned up.

## Services

`src/ai/services/` holds the program's moving parts:

| Service | Role |
|---------|------|
| `model_orchestrator.py` | Finds model configs (`user/` → `system/`) and loads the model. |
| `engine_manager.py` | Checks installed engines and instantiates the right provider. |
| `gpu_advisor.py` | Choices when a model doesn't fit in the GPU. |
| `module_registry.py` | Loads modules. |
| `stream_orchestrator.py` | Streams model output to the screen, the voice and tool-call detection. |
| `ui_orchestrator.py` | Console output and thinking animation. |
| `history_manager.py`, `session_manager.py` | Chat history and chat logs. |
| `prompt_loader.py`, `config_helper.py` | System prompt loading; CLI overrides of the config. |
| `directory_manager.py` | Paths inside the AI folder. |
| `process_manager.py` | The process registry. |
| `event_binder.py` | Wires chat events to the program. |

---

## Code map

| File | Role |
|------|------|
| `src/ai/main.py` | Entry point, arguments, startup and shutdown. |
| `src/ai/cli/` | The command line: one module per command group, with their handlers (see [Development](10-development.md#adding-a-cli-command)). |
| `src/ai/cli_args.py` | Mode dispatch: runs the group handlers, then server mode, agent runs or one-shot answers. |
| `src/ai/program.py` | `Program`: config, modules, model, tools, chat loop. |
| `src/ai/config.py` | `ProgramConfig`, `ProgramSetting`, template copying. |
| `src/ai/functions.py` | Logging/output helpers and small utilities. |
| `src/ai/core/` | Events, template injection, context files, LLM providers (`llms/`). |
| `src/ai/services/` | See [Services](#services). |
| `src/ai/modules/` | Modules: tools, knowledge, memory, voice, server. |
| `src/ai/extras/` | Console output, thinking parser and log. |
| `src/ai/entities/` | Enums (`ModelType`, `EngineType`). |
