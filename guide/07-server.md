# 7. Server (Brain Server)

The Brain Server lets one machine — usually the one with the GPU — run the models, the agents and
the web UI for every other device: another computer's terminal, a phone, a tablet.

- [Why a server](#why-a-server)
- [Starting it](#starting-it)
- [Three ways to use it](#three-ways-to-use-it)
- [Relay mode](#relay-mode)
- [Security](#security)
- [The web UI](#the-web-ui)
- [Agents from the web](#agents-from-the-web)
- [Sharing one model](#sharing-one-model)
- [Keeping it running](#keeping-it-running)
- [API overview](#api-overview)
- [Settings](#settings)
- [Code map](#code-map)

---

## Why a server

Big models need a big GPU, and loading one takes time and memory. The server loads the model
**once** and keeps it, and everything else connects to it:

```
   phone / tablet ──(web UI)──┐
                              │
   laptop ──(jarvis model)────┼──►  Brain Server (GPU box)
                              │       model · agents · tools · web UI
   laptop ──(relay mode)──────┘
```

## Starting it

```bash
./run.sh install            # once: pick "Neural Hub (Main PC Server)" (FastAPI, uvicorn)
./run.sh server             # listens on SERVER_HOST:SERVER_PORT (default 0.0.0.0:9999)
```

The model it loads first is the usual default (`MODEL_CONFIG_NAME` / `--model`); requests can ask
for another model config and the server swaps safely (see [Sharing one model](#sharing-one-model)).

Open `http://<server-ip>:9999` in a browser for the web UI.

## Three ways to use it

| From | How | What runs where |
|------|-----|-----------------|
| **Browser** (phone, tablet, PC) | Open the server's address; pair the device once. | Everything on the server. |
| **Another machine's CLI** | A model config with `"model_type": "jarvis"` (e.g. `models/jarvis-remote.json`), then `./run.sh --model jarvis-remote ...` | Chat/agents/tools run locally; only model calls go to the server. See [Models › jarvis](06-models.md#jarvis-brain-server). |
| **Another server** | `./run.sh server --relay http://gpu-box:9999` | A second server (web UI, agents, tools) on this machine; only inference goes to the Brain Server. |

## Relay mode

```bash
./run.sh server --relay http://gpu-box:9999      # or set SERVER_RELAY_URL and run: ai server
```

The machine running the relay serves its own web UI, runs agents **with its own files and tools**,
and sends only the model calls to the Brain Server. The web UI lists the Brain Server's models.

Use it when the GPU is on one machine but the files you want agents to work on are on another.
A relay pointing at itself is detected and refused.

## Security

The server is meant for your home network (and Tailscale), not the open internet.

**Trusted networks.** The server only answers requests from `SERVER_TRUSTED_NETWORKS`
(default: localhost, private LAN ranges `10/8`, `172.16/12`, `192.168/16`, and `100.64.0.0/10` for
Tailscale).

**Listen address.** `SERVER_HOST` defaults to `0.0.0.0`: the server listens on every network
interface, so phones and tablets on the LAN can reach it. The trusted-network check above is what
keeps other networks out. If you only use it from the same machine, set `"SERVER_HOST":
"127.0.0.1"`; to listen on one interface only, set it to that interface's address (for example
your Tailscale IP).

**Device pairing.** A device pairs once:
1. the device asks to pair;
2. the server prints a **6-digit code in its own terminal** (valid 2 minutes, 5 attempts);
3. you type the code on the device.

The device then gets a random token (the server keeps only its hash) as an HttpOnly cookie, or as a
Bearer token for non-browser clients. Tokens last 30 days, renewed while used. Paired devices are
stored in `user/server/devices.json` (readable only by the server's user); you can list and revoke
them from the API/web UI.

Other protections: browser requests that change state must carry an `X-Jarvis-Client` header (a
cross-site form can't send it), failed attempts are rate limited per IP, and security events are
logged.

**Authenticator codes (TOTP).** For the most dangerous agent tools started from the web, approval
can require a 6-digit code from an authenticator app:

```bash
./run.sh server totp-setup      # run on the server's terminal; shows the secret to add to your app
```

Then set `"SERVER_TOTP_ENABLED": true`. The tools that need a code are `SERVER_TOTP_TOOLS` (default
`execute_command`, `delete_file`). The secret can only be created from the server's terminal, so a
web client can never read or replace it.

**What's protected and what isn't:**

Every route — API and web UI — only answers requests from `SERVER_TRUSTED_NETWORKS`. On top of
that:

| Needs a paired device | Open to any device on a trusted network |
|-----------------------|-----------------------------------------|
| Agent runs, pipelines, workspace and file browsing (`/api/v1/agent/*`) | Chat completions (`/api/v1/chat`, `/api/v1/chat/completions`), used by `jarvis` clients and relays |
| Knowledge API (`/api/v1/knowledge/*`) | Reading prompts (`GET /api/v1/prompts`) |
| Seeing **all** saved chat sessions | Seeing the chat sessions **this browser** created (see below) |
| Changing/deleting sessions and prompts | Model configs, health and stats |
| Unload model, shutdown | |

**Chat sessions per browser.** Every browser gets a random `jarvis_client` cookie (not a login,
just an id). Chat sessions it creates are tagged with a hash of that id. Until the browser is
paired it only lists, reads and continues **its own** sessions; once paired it sees all of them.
Clients without the cookie (the `jarvis` CLI provider, relays) chat as before but list nothing.

Don't expose the port to the internet.

## The web UI

The web UI (jarvis-web) is a separate project; the server ships a build of it as
`frontend.tar.gz` and serves it at `/`.

Which build is served, first match wins:
1. `SERVER_FRONTEND_DIR` — a folder with a build (for frontend development);
2. `SERVER_FRONTEND_VERSION` — a version already in the cache (`<root>/system/frontend/<version>`);
3. the bundled `frontend.tar.gz`, extracted into the cache;
4. none — the server runs the API only.

```bash
./run.sh server frontend list               # cached versions
./run.sh server frontend use 0.1.0          # pin a version (roll back)
./run.sh server frontend use bundled        # back to the bundled one
```

## Agents from the web

The web UI runs the same pipelines, tasks and tools as `ai agent`:

- **One run at a time**, since it shares the server's model.
- Runs are **detached**: closing the browser doesn't stop a run; reconnecting replays its events.
  Only a cancel (or a forced model swap) stops it.
- Runs work in a folder you pick; the default is `SERVER_AGENT_WORKDIR` (or
  `<root>/system/workspace`). File tools stay inside it.
- Approvals for `HIL_TOOLS` are asked in the browser. If nobody answers within **10 minutes**, the
  tool is denied, so nothing gated runs unattended.
- Pipelines can be listed, created and edited from the UI (validated before saving).
- Chat sessions from the web are stored in `<root>/sessions/server/`.

## Sharing one model

The server tracks who's using the loaded model. When a request needs a different model config:

| Policy | What happens |
|--------|--------------|
| `wait` | The swap waits until the current work finishes. |
| `fail` | The swap is refused (busy). |
| `force` | The current work is cancelled, then the model is swapped — only on an explicit request. |

Running work is never swapped out from under itself by default. `POST /api/v1/model/unload` frees
the GPU. JARVIS instances also share a process registry, so a CLI that can't fit its model can
offer to use the running server instead (see [Models](06-models.md#when-the-model-doesnt-fit-in-the-gpu)).

## Keeping it running

`scripts/server/jarvis.sh` is a small watchdog: it runs `$AI_ENGINE server` and restarts it
after a crash (exit code ≠ 0) or a clean stop; `Ctrl+C` ends it.

```bash
export AI_ENGINE="$HOME/Code/ai/run.sh"
scripts/server/jarvis.sh
```

For a permanent setup, a systemd user service that runs `run.sh server` with
`Restart=on-failure` does the same job.

## API overview

All under `http://<server>:9999`. "🔒" = needs a paired device.

| Area | Endpoints |
|------|-----------|
| Health | `GET /api/health`, `GET /api/v1/stats` |
| Chat | `POST /api/v1/chat/completions` (OpenAI-style), `POST /api/v1/chat` — with images and per-request sampling |
| Model | 🔒 `POST /api/v1/model/unload`, 🔒 `POST /api/v1/shutdown`, `GET /api/v1/model-configs` |
| Auth | `POST /api/v1/auth/pair/start`, `POST /api/v1/auth/pair/finish`, 🔒 `GET /me`, 🔒 `POST /logout`, 🔒 `GET /devices`, 🔒 `DELETE /devices/{id}` |
| Sessions | `GET /api/v1/sessions`, `GET /api/v1/sessions/{path}`, 🔒 `PUT .../title`, 🔒 `PUT`, 🔒 `DELETE` |
| Prompts | `GET /api/v1/prompts`, `GET /api/v1/prompts/{path}`, 🔒 `POST`, 🔒 `PUT`, 🔒 `DELETE` |
| Agent 🔒 | `/api/v1/agent/`: `pipelines` (CRUD), `tools`, `tasks`, `sessions`, `workspace`, `fs/list`, `fs/mkdir`, `runs` (start), `runs/{id}/events` (SSE), `runs/current`, `runs/{id}/permission`, `runs/{id}/cancel` |
| Knowledge 🔒 | `/api/v1/knowledge/`: `sources`, `search`, `component`, `status`, `build`, `build/{id}`, `build/{id}/cancel` |

FastAPI also serves interactive docs at `/docs` (OpenAPI).

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `SERVER_HOST` | `0.0.0.0` | Listen address. |
| `SERVER_PORT` | `9999` | Port. |
| `SERVER_TRUSTED_NETWORKS` | localhost, LAN, Tailscale | CIDRs allowed to use the server at all. |
| `SERVER_ALLOWED_ORIGINS` | `http://localhost:4200` | CORS origins (the frontend dev server). |
| `SERVER_RELAY_URL` | — | Relay mode target. |
| `SERVER_AGENT_WORKDIR` | `<root>/system/workspace` | Default folder for web agent runs. |
| `SERVER_FRONTEND_DIR` / `SERVER_FRONTEND_VERSION` | — / bundled | Which web UI build to serve. |
| `SERVER_TOTP_ENABLED` | `false` | Require authenticator codes. |
| `SERVER_TOTP_TOOLS` | `execute_command`, `delete_file` | Tools that need a code. |

---

## Code map

| File (`src/ai/modules/server/`) | Role |
|---------------------------------|------|
| `server_module.py` | Starts uvicorn with the app. |
| `app.py` | FastAPI app: chat, health, stats, unload, shutdown, routers, frontend. |
| `brain_hub.py` | The loaded model: leases, safe swaps, relay mode. |
| `relay.py` | Relay URL helpers. |
| `routers/` | `agent`, `auth`, `knowledge`, `prompts`, `sessions`. |
| `services/auth.py` | Pairing, devices, trusted networks, rate limits. |
| `services/totp.py` | Authenticator codes. |
| `services/agent_runs.py` | Web agent runs (detached, SSE, approvals). |
| `services/chat.py` | Chat completions. |
| `services/frontend.py` | Which web UI build to serve, version cache. |
| `services/pipelines.py` | Pipeline validation for the editor. |
| `services/knowledge_builds.py` | Background knowledge builds. |
| `services/session_manager.py`, `prompt_manager.py` | Chat sessions and prompt files. |
| `scripts/server/jarvis.sh` (repo) | Watchdog. |
