# 3. Agents

Agent mode gives the model tools: it can read and edit files, search, run commands and browse the
web, step by step, until it has an answer for you. This page explains how that loop works and how
to shape it with pipelines.

- [Running agents](#running-agents)
- [The agent loop](#the-agent-loop)
- [The response format](#the-response-format)
- [Pipelines](#pipelines)
- [Writing your own pipeline](#writing-your-own-pipeline)
- [Approvals (human in the loop)](#approvals-human-in-the-loop)
- [What the agent sees each step](#what-the-agent-sees-each-step)
- [Guards: loops, idle turns, broken output](#guards-loops-idle-turns-broken-output)
- [Sessions](#sessions)
- [Code map](#code-map)

---

## Running agents

```bash
./run.sh agent                              # interactive agent chat
./run.sh agent -m "Find the TODOs in src"   # one-shot: run, print, exit
./run.sh agent --pipeline small             # pick a pipeline
./run.sh agent --resume                             # continue a saved session of this folder
git diff | ./run.sh agent -t commit         # a task as the first message
```

The agents work in the **current folder**. `@ROOT` in tool paths means that folder, and file tools
refuse paths outside it (symlinks included). `execute_command` is not limited this way, which is
one reason it needs your approval by default.

Agent chat keys and commands (`/help`, `/clear`, `/resume`, `/session`, `/pipeline`, `/tools`,
`/thoughts`, `/exit`) are listed in [Interfaces › Agent chat](01-interfaces.md#agent-chat).

The web UI runs the same agents through the Brain Server (see [Server](07-server.md#agents-from-the-web)).

## The agent loop

One user message starts a **turn**. A turn is a loop of **steps**; each step is one model call.

```
 your message
      │
      ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ 1. build the payload for the current agent                  │
 │    objective, messages, notes, recent results, knowledge,   │
 │    long-term memory                                         │
 │ 2. check context size (compress old results if too big)    │
 │ 3. call the model: system prompt + tools + payload          │
 │ 4. parse the XML answer (repair it if needed)               │
 │ 5. act on it:                                               │
 │      tool call      → ask approval if needed → run it       │
 │                       → result goes into the agent's memory │
 │      another agent  → hand the task to it                   │
 │      USER           → show the answer / question, end turn  │
 │      STOP           → task finished, end turn               │
 │ 6. save the session                                         │
 └──────────────┬──────────────────────────────────────────────┘
                │ next step (same or another agent)
                ▼
          ... until USER, STOP, an error, Esc,
              or max_iterations steps
```

When the turn ends, JARVIS also:
- saves a short summary of the turn to long-term memory (if enabled);
- regenerates the knowledge of files the agents changed (`KNOWLEDGE_AUTO_UPDATE`).

## The response format

The model must answer in XML. The rules and examples are in `system/inject/agent-out.md`, which is
added to every agent's system prompt in place of `{{AGENT_OUTPUT_RULES}}`.

```xml
<response>
  <thought><![CDATA[reasoning]]></thought>
  <manifest>
    <phase>Discovery</phase>
    <current_priority>Read the config loader</current_priority>
  </manifest>
  <notes><![CDATA[facts to remember next step]]></notes>
  <action>
    <tool_name>read_file</tool_name>             <!-- a tool, open_tools, or null -->
    <tool_parameters><path>@ROOT/src/app/config.py</path></tool_parameters>
    <agent_target>SELF</agent_target>            <!-- SELF, USER, STOP or another agent -->
    <message_to_target><![CDATA[task, when delegating]]></message_to_target>
  </action>
  <response_to_user><![CDATA[what you read on screen]]></response_to_user>
</response>
```

| Field | Used for |
|-------|----------|
| `thought` | The model's reasoning. Shown only when `AGENT_THOUGHT` is on (`/thoughts`). |
| `manifest.current_priority` | The status line you see while it works. |
| `notes` | The agent's scratchpad, sent back to it on the next step. |
| `action.tool_name` + `tool_parameters` | The tool to run. Repeat a tag to pass a list (`<path>a</path><path>b</path>`). |
| `action.agent_target` | Where control goes next (see below). |
| `response_to_user` | What's printed for you. |

**Targets:**

| Target | Meaning |
|--------|---------|
| `SELF` | Take another step. Only valid together with a tool call. |
| `USER` | Show the answer or question and end the turn. Your next message continues the session. |
| `STOP` | The whole task is done; end the turn. |
| `<AGENT>` | Hand the work to another agent of the pipeline, with the task in `message_to_target`. |
| `DONE` | Special: the agent's memory is cleared and control goes back to the pipeline's `entry_point`. |

Small models often get the format slightly wrong, so the parser is tolerant. It tries, in order:
1. strict XML;
2. re-wrapping the known tags when `<response>` is missing or cut off;
3. pulling each field out on its own (code fences, missing `<action>`, a truncated last tag…).

It only fails when it can't find a tool call, a target or a message at all.

## Pipelines

A pipeline is a JSON file that says which agents exist, who starts, which tools each one can use
and who it can hand work to. Three ship with JARVIS (in `system/pipelines/`):

| Pipeline | Agents | When to use |
|----------|--------|-------------|
| `default` | `MASTER` alone, with every tool | The usual choice. One agent that plans and does the work. |
| `small` | `MASTER` (manager) + `ENGINEER` (edits files), `SECRETARY` (reads and searches), `SYSTEM_OPERATOR` (runs commands) | Small models (~8B): each agent has fewer tools and a narrower job. |
| `multi` | `MASTER` + `PLANNER` + `ENGINEER`, `SECRETARY`, `SYSTEM_OPERATOR` | Bigger tasks that benefit from a separate planning step. |

`default.json`, shortened:

```json
{
  "name": "Single Agent workflow",
  "description": "A single-agent loop with planning, scouting and shell execution.",
  "entry_point": "MASTER",
  "max_iterations": 300,
  "agents": {
    "MASTER": {
      "role": "management",
      "prompt_file": "agents/default.md",
      "tools": ["read_dir", "smart_search", "read_file", "write_file", "patch_file",
                "execute_command", "web_search", "query_memory", "search_knowledge", "..."],
      "allowed_targets": ["MASTER", "USER"]
    }
  }
}
```

| Key | Description |
|-----|-------------|
| `name`, `description` | Shown in the UI. |
| `entry_point` | The agent that receives your message (default `MASTER`). |
| `max_iterations` | Max steps per turn (default 300, like the shipped pipelines). |
| `knowledge` | Optional: extra knowledge sources for this pipeline. |
| `oneshot_hil_tools` | Optional: in one-shot runs (`ai agent -m` / `-t`), the only tools that need approval; see [Approvals](#approvals-human-in-the-loop). |
| `oneshot_auto_reply` | Optional: in one-shot runs without a terminal, the reply sent when an agent hands control to you; see [One-shot runs](#one-shot-runs). |
| `agents.<NAME>.role` | `management` gets your message as its objective; `labor` gets the task it was handed. |
| `agents.<NAME>.prompt_file` | System prompt, relative to `system-prompt/`: `user/system-prompt/` is checked first, then `system/system-prompt/` (or an absolute path). |
| `agents.<NAME>.tools` | Tools this agent may call. Anything else is refused. |
| `agents.<NAME>.allowed_targets` | Where it may send control: `USER`, `STOP`, other agent names. |
| `agents.<NAME>.knowledge` | Optional: only these knowledge source ids are visible to this agent. |

Notes:
- **MCP tools are added to every agent** automatically, on top of its `tools` list.
- An agent can always target itself (`SELF`), even if it's not in `allowed_targets`.
- The shipped prompts: `agents/default.md`, `agents/jarvis.md` (the "Sentinel Architect"
  personality), `agents/gemini.md`, `agents/other/plain.md`, and the role prompts in
  `agents/small/` and `agents/multi/`.

## Writing your own pipeline

1. Copy one of the shipped pipelines to `user/pipelines/my-pipeline.json` (user pipelines win over
   system ones with the same name).
2. Change the agents, tools and targets.
3. For a custom prompt, put the Markdown file under `user/system-prompt/` (e.g.
   `user/system-prompt/agents/mine/coder.md`) and point `prompt_file` at `agents/mine/coder.md`.
   A file there also overrides a shipped prompt with the same path. Keep `{{TOOLS}}` and
   `{{AGENT_OUTPUT_RULES}}` in the prompt: that's where the tool list and the output format go.
4. Run it: `./run.sh agent --pipeline my-pipeline`, or `/pipeline my-pipeline` in the chat.

The pipeline is checked when it loads: a missing `prompt_file` stops the run with an error.


## Approvals (human in the loop)

Tools listed in `HIL_TOOLS` (`config.json`) ask before they run. Default:
`execute_command`, `write_file`, `patch_file`, `delete_file`.

When asked, you can answer:
- **yes** — run it this once;
- **no** — the agent is told "Access Denied" and has to try something else;
- **always** — run it, and don't ask again for calls like this one in this session (saved with the
  session, so it survives `ai agent --resume`). The box shows what "always" covers:
  - shell commands: the same program and sub-command — "always" on `git status -s` covers every
    `git status ...` but not `git push`; on `ls -la` (no sub-command) it covers every `ls`.
    Commands with `;`, `&&`, `|`, `>`, `` ` `` or `$(` are never remembered: they ask every time;
  - `write_file`, `patch_file`, `delete_file`: that tool in the same folder and the folders below it;
  - `enable_mcp_server`: never remembered;
  - any other tool (e.g. an MCP server with `auto_allow: false`): the whole tool.

### One-shot runs

A one-shot run (`ai agent -m "..."` or `ai agent -t TASK`) normally uses `HIL_TOOLS` too. With no
terminal to ask (a script, a pipe, cron), those tools are denied.

A pipeline can set its own list for one-shot runs instead:

```json
"oneshot_hil_tools": ["execute_command", "delete_file"]
```

With this key, in a one-shot run:
- tools **in the list** need approval. With a terminal you are asked as usual. Without one, the run
  **stops** before the tool, saves the session and prints
  `approve and continue: ai agent --resume <id>`. Resume it in the chat to approve the call;
- tools **not in the list** run without asking, even if they are in `HIL_TOOLS`;
- `enable_mcp_server` and the tools of MCP servers with `auto_allow: false` still need approval.

The interactive chat and the web UI ignore this key and keep using `HIL_TOOLS`. An empty list
(`[]`) lets a one-shot run use every tool without asking.

When an agent hands control back to you in a one-shot run (it has a question, or it is done):
- **with a terminal**, you are asked for a reply. Type it and the run goes on in the same
  session; press Ctrl+C (or Ctrl+D) to end the run. An empty line is not taken as an answer. The
  time spent waiting is not counted in the run time;
- **without a terminal**, the run ends and prints `continue: ai agent --resume <id> --msg "..."`,
  unless the pipeline sets an automatic reply:

```json
"oneshot_auto_reply": "Proceed with your best judgment; the user is not available to answer."
```

  The agent gets that text as your reply and carries on. Agents also hand control back when they
  are done, so the reply is sent again only if the agent ran a tool since the previous one;
  otherwise the run ends. Off by default.

From the web UI, tools in `SERVER_TOTP_TOOLS` can also require an authenticator code (see the
[Server](07-server.md#security)).

## What the agent sees each step

Each call sends two messages: the **system prompt** and a **payload**.

**System prompt** = the agent's `prompt_file`, with:
- `{{TOOLS}}` → the available tools (or tool categories, see below) and the allowed targets, each
  with a one-line explanation;
- `{{AGENT_OUTPUT_RULES}}` → `system/inject/agent-out.md`.

**Payload** (sent as `<context>{...}</context>`):

| Field | What's in it |
|-------|--------------|
| `objective` | Your message (manager agents) or the task it was handed (labor agents). |
| `agent_notes` | Its own `notes` from the last step. |
| `messages_received` | New messages: your input, tool results, hand-offs, system hints. |
| `conversation_history` | Its last 10 exchanges (older tool results shortened to 1500 chars, the last 2 kept whole). |
| `recent_outcomes` | The last 3 tool results, short. |
| `context.files_in_project` | Files written in this session. |
| `relevant_components`, `related_to_touched_files` | Project knowledge matching the task and the files it touched. |
| `long_term_memory` | Relevant memories from earlier sessions. |

**Tool categories.** With `AGENT_TOOL_CATEGORIES` on (default), an agent first sees only the
category names and descriptions. It calls `open_tools` to unlock the ones it needs; calling a
tool or a category name directly also opens it. Open categories stay open for the session. This
keeps the prompt small for models with short context windows.

**Size limits.**
- Each tool result is capped at `AGENT_TOOL_RESULT_MAX_CHARS` (12000) characters.
- Before each call, the **Context Sentinel** estimates the size (≈3.2 characters per token, system
  prompt included) against the model's real context window minus its output reserve. Above 90%,
  older large tool results (over 2000 characters) are summarized by the model, the summaries are
  saved to long-term memory, and the history is trimmed to the last 3 entries. The 2 most recent
  results are never summarized, since the agent is usually still working with them.

## Guards: loops, idle turns, broken output

Small models can get stuck. The orchestrator watches for it:

| Situation | What happens |
|-----------|--------------|
| Same tool with the same parameters 3 times in the last 5 calls | The agent is told the result won't change and to try something else. |
| … 5 times | The turn stops and control goes back to you. |
| No tool and target `SELF` (does nothing) | First time: the agent is told how to end its turn. Second time: its answer is handed to you. |
| Output can't be parsed | The agent is told to rewrite it. After 3 failures in a row the turn stops. |
| Agent name used as a tool name | Treated as a hand-off to that agent. |
| Tool not in the agent's list | Refused; the agent is told it's unauthorized. |
| Target not in `allowed_targets` | Refused; the agent stays in control and is told. |
| Hand-off with no task | The delegating agent's current task is passed on. |
| Provider/network error | The turn stops; the session is saved, so sending "continue" retries. |
| `max_iterations` reached | The turn stops with an error. |

## Sessions

The state is saved after every step, so a session can be resumed later, even after a crash.

- Sessions belong to the **folder** you ran JARVIS in.
- They're stored in `<root>/sessions/agents/<folder id>/<session id>.json`, one JSON line per
  saved state. Only the first state (the original request) and the last three are kept, since each
  line holds the full state; every line has `turn`, the number of steps so far. `manifest.json` in
  the same folder lists the sessions.
- The saved state includes every agent's memory, the current agent, the step count and what you
  answered "always" for.

```bash
./run.sh sessions list          # sessions of this folder
./run.sh agent --resume                 # pick one
./run.sh agent --resume 3f2a            # by id or unique prefix
./run.sh agent --session-id ID  # start or continue a session with this id
```

In the chat, `/resume` and `/session` do the same; `/clear` starts a new one.

Server/web sessions are kept separately, in `<root>/sessions/server/`.

---

## Code map

| File (`src/ai/agents/`) | Role |
|-------------------------|------|
| `agent.py` | Loads pipelines (`load_pipeline_config`) and builds the orchestrator with its tools (`build_orchestrator`). |
| `agent_orchestrator.py` | The loop: payload, model call, routing, approvals, guards, session commits, end-of-turn hooks. |
| `llm_connector.py` | Builds the system prompt (`{{TOOLS}}`, `{{AGENT_OUTPUT_RULES}}`), calls the model, retries interrupted streams. |
| `xml_response_parser.py` | Tolerant XML parser (strict → re-wrap → field extraction). |
| `memory_manager.py` | Per-agent memory: messages, history, notes, open categories, stagnation check. |
| `context_sentinel.py` | Context size check and compression. |
| `context_enricher.py` | Adds knowledge and long-term memory to the payload. |
| `payload_limits.py` | Caps on tool result size. |
| `tool_catalog.py` | Tool categories and `open_tools`. |
| `session_manager.py` | Session journal, listing, resume. |
| `agent_io.py`, `terminal_ui.py`, `tool_preview.py` | Events, permission prompts and output for the UIs. |
| `chat_ui/` | The interactive agent chat (prompt_toolkit app, renderer, commands, session picker). |
