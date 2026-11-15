# 4. Tools

Tools are what agents can actually do: read and edit files, search, run commands, browse the web,
send notifications, query project knowledge and memory. This page lists them, explains tool
categories, and shows how to add MCP servers and your own tools.

- [How tools reach an agent](#how-tools-reach-an-agent)
- [Tool categories and open_tools](#tool-categories-and-open_tools)
- [Built-in tools](#built-in-tools)
- [Safety](#safety)
- [MCP servers](#mcp-servers)
- [Writing your own tools](#writing-your-own-tools)
- [Code map](#code-map)

---

## How tools reach an agent

```
 built-in modules (tools_filesystem, tools_search, ...)  ─┐
 knowledge module, long-term memory module                │
 MCP servers (one gateway tool per server)                ├─► ToolRegistry ─► agent
 your files in user/tools/*.py                           ─┘        ▲
                                                                   │
                                     filtered by the agent's "tools" list in the pipeline
                                     (MCP tools are added to every agent)
```

An agent can only call the tools listed for it in the [pipeline](03-agents.md#pipelines), plus every
MCP gateway. Calling anything else is refused.

Each tool is a Python function marked with `@tool`. Its **docstring is what the model reads**: what
it does, its `Args:` and what it returns. That's why the built-in docstrings are written for the
model, with short examples.

Every tool returns a dict with a `status` (`SUCCESS`, `FAILED`, …) plus its data or an `error`.

## Tool categories and open_tools

Tools are grouped in **categories**. With `AGENT_TOOL_CATEGORIES` on (the default), an agent starts
by seeing only the category names and one-line descriptions:

```
TOOL CATEGORIES (call open_tools to see their tools):
- filesystem: List folders and read, write, patch or delete project files.
- search: ...
- knowledge: Project knowledge base: what each file does, where symbols are, dependencies and docs.
```

It calls `open_tools` with the categories it needs (several at once), and from then on their full
descriptions are in its prompt under OPEN TOOLS. Calling a tool or a category name directly also
opens it. Open categories stay open for the rest of the session.

Why: a full tool list with descriptions can take thousands of tokens. With small context windows
that space is better spent on the task. Set `"AGENT_TOOL_CATEGORIES": false` to always list every
tool.

| Category | Source | Tools |
|----------|--------|-------|
| `filesystem` | `modules/tools_filesystem` | `read_dir`, `read_file`, `read_files`, `write_file`, `patch_file`, `delete_file` |
| `search` | `modules/tools_search` | `smart_search`, `grep_file` |
| `shell` | `modules/tools_shell` | `execute_command` |
| `web` | `modules/tools_web` | `web_search`, `web_read` |
| `notify` | `modules/tools_notify` | `send_notification` |
| `knowledge` | `modules/knowledge` | `search_knowledge`, `get_component`, `knowledge_neighbors`, `find_symbol`, `read_doc`, `knowledge_status`, `update_knowledge`, `ingest_knowledge` |
| `memory` | `modules/vector_memory` | `query_memory`, `remember`, `trigger_reflection` |
| one per MCP server | `mcp_config.json` (enabled servers) | one gateway tool named after the server |
| `mcp_servers` | `tools/mcp_admin_tools.py` | `list_mcp_servers`, `enable_mcp_server` (always asks) |
| yours | `user/tools/*.py` | whatever you write |

Each built-in module can be turned off in `config.json`: `TOOLS_FILESYSTEM_ENABLED`,
`TOOLS_SEARCH_ENABLED`, `TOOLS_SHELL_ENABLED`, `TOOLS_WEB_ENABLED`, `TOOLS_NOTIFY_ENABLED`
(all `true` by default).

## Built-in tools

Paths use `@ROOT`, the folder JARVIS was started in (e.g. `@ROOT/src/app.py`). To pass a list,
the model repeats the tag: `<path>@ROOT/a.py</path><path>@ROOT/b.py</path>`.

### filesystem

| Tool | What it does | Main parameters |
|------|--------------|-----------------|
| `read_dir` | Lists files and folders. | `path` (repeatable), `depth` (0 = this folder only) |
| `read_file` | Reads a file, or a range of lines. | `path` (repeatable), `start_line`, `end_line` |
| `read_files` | Reads several files in one call. | `paths` (repeatable) |
| `write_file` | Creates a file or replaces its whole content; creates missing folders. | `path`, `content` |
| `patch_file` | Replaces one exact block of text, keeping the rest. | `path`, `search`, `replace` |
| `delete_file` | Deletes one file or an empty folder. | `path` |

`patch_file` and `write_file` try hard to survive small-model mistakes:
- `search` must appear exactly once; if it isn't found, a match **ignoring indentation** is tried,
  and the replacement is re-indented to fit;
- text written with literal `\n` escapes instead of real line breaks is fixed;
- after writing a `.py` or `.json` file, a **warning** is returned if it no longer parses, or if the
  patch seems to have duplicated a block.

### search

| Tool | What it does | Main parameters |
|------|--------------|-----------------|
| `smart_search` | Searches file **names and contents** in the project (case-insensitive regex), 50 results per page. Skips `.git`, `node_modules`, `venv`, `dist`, `build`. | `pattern`, `path`, `exclude_dirs`, `page` |
| `grep_file` | Finds lines in one file, with line numbers and context. Handy before `patch_file`. | `path`, `pattern`, `context`, `ignore_case`, `max_matches` |

`smart_search` uses the system `grep` for contents, or a Python search with the same output when
`grep` isn't installed (Windows).

### shell

| Tool | What it does | Main parameters |
|------|--------------|-----------------|
| `execute_command` | Runs a shell command and returns `returncode`, `stdout` and `stderr`. | `command`, `path` (working folder), `timeout` (default 180 s) |

Commands run **without a terminal**: no keyboard input, so interactive programs (editors, pagers,
password or y/N prompts) can't be used; the docstring tells the model to use non-interactive flags.
On timeout the whole process tree is stopped. `@ROOT` inside the command is replaced by the project
folder.

### web

| Tool | What it does | Main parameters |
|------|--------------|-----------------|
| `web_search` | Searches the web (DuckDuckGo's HTML page) and returns titles, URLs and snippets. No API key. | `query`, `max_results` (1–20), `region` (e.g. `pt-pt`) |
| `web_read` | Downloads a page and returns its readable text (HTML, text, JSON, XML). | `url`, `max_chars` (default 12000) |

Sites that block automated reading (HTTP 403/429), or pages that need JavaScript or a login, need
a browser: the shipped MCP config includes Playwright for that.

### notify

| Tool | What it does | Main parameters |
|------|--------------|-----------------|
| `send_notification` | Desktop notification, for when a long task finishes or the agent needs you. | `message`, `title` (default `JARVIS`), `urgency` (`low`, `normal`, `critical`) |

Uses `notify-send` on Linux and `osascript` on macOS. If neither is there (e.g. Windows), it rings
the terminal bell instead.

### knowledge and memory

These are covered in [Knowledge & memory](05-knowledge-memory.md). In short:

| Tool | What it does |
|------|--------------|
| `search_knowledge` | Search the project knowledge (components and docs). |
| `get_component` | What one file does: summary, symbols, dependencies. |
| `knowledge_neighbors` | Files related to one file (imports, used by). |
| `find_symbol` | Where a class or function is defined. |
| `read_doc` | Read the generated documentation of a file. |
| `knowledge_status` / `update_knowledge` | Check coverage / regenerate knowledge for files. |
| `ingest_knowledge` | Register a folder of knowledge or docs for this project. |
| `query_memory` | Recall facts and decisions from earlier sessions. |
| `remember` | Store a fact, decision or preference. |
| `trigger_reflection` | Ask the model to distil recent memories into higher-level ones. |

## Safety

| Protection | How |
|------------|-----|
| Project boundary | File tools resolve every path inside `@ROOT`, after following symlinks. Anything outside is refused. |
| Approvals | Tools in `HIL_TOOLS` ask you first (default: `execute_command`, `write_file`, `patch_file`, `delete_file`). See [Approvals](03-agents.md#approvals-human-in-the-loop). |
| Per-agent lists | An agent can only call the tools its pipeline gives it. |
| Result size | Each result is capped at `AGENT_TOOL_RESULT_MAX_CHARS` (12000 characters). |
| Web agents | Runs started from the web UI are kept inside their workdir; tools in `SERVER_TOTP_TOOLS` can require an authenticator code. |

Keep in mind:
- `execute_command` is **not** limited to the project folder: a command can touch anything your
  user can. That's why it needs approval by default; think twice before answering "always".
- MCP gateways run without asking by default. Set `"auto_allow": false` on a server in
  `mcp_config.json` (or add its name to `HIL_TOOLS`) to approve each call. Starting a server from
  an agent (`enable_mcp_server`) always asks.

## MCP servers

[MCP](https://modelcontextprotocol.io) servers give the agents extra abilities (a browser, GitHub,
databases…). JARVIS starts each **enabled** server as a local process (stdio) when an agent run
begins. The shipped ones (Playwright, GitHub) start **disabled**.

**Turning them on:**

```bash
ai mcp list                    # configured servers, enabled or not
ai mcp enable playwright       # start it in every agent run
ai mcp disable playwright
```

Agents can do it too, without leaving the run:
- `list_mcp_servers` — what's configured, enabled and running;
- `enable_mcp_server` (`name`, optional `remember`) — starts a server for this run; **always asks
  you first**, since it runs a program on your machine. With `remember: true` it stays enabled for
  later runs.

Both tools are given to every agent (category `mcp_servers`).

**Config files:** `system/config/mcp_config.json` (shipped), then `user/config/mcp_config.json`
(yours, optional). They're merged by server name: your file can add servers, or override keys of a
shipped one without copying the rest. `ai mcp enable/disable` only writes
`{"NAME": {"enabled": true|false}}` to your file. The shipped one:

```json
{
  "mcpServers": {
    "playwright": {
      "enabled": false,
      "auto_allow": true,
      "description": "Browser automation tool. Use this to navigate websites, click elements, extract text, and interact with web applications.",
      "command": "npx",
      "args": ["-y", "@playwright/mcp@latest"]
    },
    "github": {
      "enabled": false,
      "auto_allow": true,
      "description": "Interact with the GitHub API. Use this to read repositories, create issues, review PRs, and manage branches.",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    }
  }
}
```

| Key | Description |
|-----|-------------|
| `enabled` | `false` skips the server (default `true` for your own servers; the shipped ones are `false`). |
| `description` | What the agent reads about the server. Make it say when to use it. |
| `command`, `args` | How to start the server. |
| `env` | Optional environment variables for the process (e.g. an API token — GitHub needs `GITHUB_PERSONAL_ACCESS_TOKEN`). |
| `auto_allow` | `true` (default): the gateway runs without asking. `false`: every call to this server asks for your approval, like the tools in `HIL_TOOLS`. |

Adding your own server, in `user/config/mcp_config.json`:

```json
{ "mcpServers": { "sqlite": { "command": "uvx", "args": ["mcp-server-sqlite", "--db-path", "data.db"],
                               "description": "Query the project's SQLite database." } } }
```

Servers need their runtime (Node.js for `npx`, `uv` for `uvx`…). If one fails to start, the run
continues without it.

**How the agent uses it.** Each running server becomes **one gateway tool** named after it (e.g.
`playwright`), in its own category. The gateway has two actions:
- `list_tools` — the server's commands and their parameters (also shown when the category is open);
- `execute` — run a command, with its arguments as tags or as a JSON `arguments` string.

Each server's error output is logged to `<root>/system/logs/mcp/`.

## Writing your own tools

User tools are Python files in `<root>/user/tools/`. Every `@tool` function must belong to a
`ToolCategory`.

1. Create a skeleton (a tool inside its own category, ready to load), or copy the example:
   ```bash
   ./run.sh tools create git_status          # writes ~/Ai/user/tools/git_status.py
   # or: cp ~/Ai/user/tools/_example_tools.py ~/Ai/user/tools/git_tools.py
   ```
   Files starting with `_` aren't loaded, which is why the example has to be copied to a new name.
2. Write the tool and its category:
   ```python
   import subprocess
   from ai.tools import ToolCategory, tool
   from ai.tools.base import resolve_path

   @tool
   def git_status(path: str = "@ROOT") -> dict:
       """
       Shows the git status of the project (changed, staged and untracked files).

       Args:
           path (string, optional): Repository folder. Defaults to the project root.

       Returns:
           output: the short git status, or an error.
       """
       try:
           cwd = resolve_path({"path": path})        # keeps the path inside @ROOT
           out = subprocess.run(["git", "status", "--short", "--branch"], cwd=cwd,
                                capture_output=True, text=True, timeout=30)
           if out.returncode != 0:
               return {"status": "FAILED", "error": out.stderr.strip()}
           return {"status": "SUCCESS", "output": out.stdout}
       except Exception as e:
           return {"status": "FAILED", "error": str(e)}


   class GitTools(ToolCategory):
       name = "git"
       description = "Inspect the git repository of the project: status of changed files."

       def get_category_tools(self):
           return [git_status]
   ```
3. Add the tool names to an agent's `tools` list in your pipeline (user tools, unlike MCP tools,
   are **not** given to agents automatically):
   ```json
   "tools": ["read_file", "patch_file", "git_status"]
   ```

Rules, checked when the file loads (a broken file stops the run with a clear error):

| Rule | Detail |
|------|--------|
| Category `name` | 2–40 characters: lowercase letters, digits, `_`, starting with a letter. Unique (not `filesystem`, `search`, `shell`, `web`, `notify`, `knowledge`, `memory` or an MCP server name). |
| Category `description` | One line, at most 120 characters. |
| Each tool | Marked with `@tool`, has a docstring, and an `Args:` section if it takes parameters (`name (type): description`). |
| Ownership | A tool belongs to one category only; every `@tool` function in the file must be in a category. |
| Files | Files starting with `_` are skipped. Files in the folder can import each other. |

Tips:
- Write the docstring for the model: say when to use the tool, give an example value, describe the
  result.
- Use `resolve_path` for any path parameter so the project boundary applies.
- Return `{"status": "SUCCESS", ...}` or `{"status": "FAILED", "error": "..."}`.
- Add your tool to `HIL_TOOLS` if it changes things.

---

## Code map

| File | Role |
|------|------|
| `src/ai/tools/base.py` | `@tool`, `@ROOT` and `resolve_path` (project boundary). |
| `src/ai/tools/category.py` | The `ToolCategory` contract and its validation. |
| `src/ai/tools/tool_registry.py` | Registers categories and tools, builds descriptions, executes tools. |
| `src/ai/tools/tool_loader.py` | Loads `user/tools/*.py`. |
| `src/ai/cli/tools.py` | `ai tools create` (skeleton). |
| `src/ai/tools/mcp_bridge.py` | Starts MCP servers and exposes one gateway tool per server. |
| `src/ai/tools/mcp_config.py` | Merges the system and user MCP configs; enable/disable. |
| `src/ai/tools/mcp_admin_tools.py` | `list_mcp_servers`, `enable_mcp_server`. |
| `src/ai/cli/mcp.py` | `ai mcp list / enable / disable`. |
| `src/ai/agents/tool_catalog.py` | Categories as the agent sees them, and `open_tools`. |
| `src/ai/modules/tools_*/` | The built-in tool modules. |
