# SERVER_AGENT

Tasks for an agent (Claude Code) running on the server machine (`server-x`, the one that runs `ai --server`
with a local GGUF model). One task per line; the indented text says what is needed and how to verify it.
Mark a task `[x]` when done and add a short result line under it. Do not commit secrets or model files.

- [ ] 2026-11-12 — Validate the non-streaming and Jarvis fixes on the GGUF server (branch `develop`)
  - **Context:** `chat(stream=False)` in `src/ai/core/llms/gguf_model.py` (and `ollama_model.py`) was a
    generator function, so the non-streaming result was lost and `POST /api/v1/chat/completions` with
    `"stream": false` answered `{"content": ""}`. Streaming was never affected. The fix moves streaming into
    `_stream_chat()` so `chat()` returns the text directly. The Jarvis client (`jarvis.py`) now raises
    `LLMAPIError` (with retries) on network/server errors instead of returning empty output.
  - **1. Update:** `git checkout develop && git pull`. No new dependencies are needed.
  - **2. Unit tests:** `.venv/bin/python -m pytest tests -q` → expect all passed (4 skipped = live MCP tests).
    Here llama_cpp is really installed, so also run
    `.venv/bin/python -m pytest tests/ai/core/test_chat_return_types.py -q` and confirm it still passes.
  - **3. Restart the server with the new code:** stop the running `ai --server` and start it again
    (`ai --server`, listening on `0.0.0.0:9999`). If you cannot restart it yourself, say so and stop here.
  - **4. Non-streaming now returns text** (this was the bug):
    ```bash
    curl -sS -X POST http://localhost:9999/api/v1/chat/completions -H 'Content-Type: application/json' \
      -d '{"model":"default","system_prompt_content":"Reply with exactly one word: BANANA.","stream":false,"messages":[{"role":"user","content":"hi"}]}'
    ```
    → expect `"content":"BANANA"` (any non-empty text is a pass; `""` is a fail).
  - **5. Streaming keeps accents:** same request with `"stream":true` and the user message
    `"Repeat exactly: O ficheiro contém olá, ação e café."` → the joined `delta.content` must contain
    `contém`, `ação` and `café` (non-ASCII must not be dropped).
  - **6. End-to-end agent run against this server:** in an empty temp dir, `echo hello > a.txt`, then
    `AI_API_BASE_URL=http://localhost:9999 ai --agent --msg "Lê o ficheiro a.txt e diz-me o que tem."`
    → expect chat-style output (`⏺ read_file(...)`, `⎿ SUCCESS`), a final message containing `hello`
    with accents intact (e.g. `contém`), `✻ Done in …`, and a `continue: ai --agent --resume <id>` line.
    The client's model config must have `"model_type": "jarvis"` and a `model_name` that is a model
    config file name on this server (e.g. `default`).
  - **7. Report:** for each step write PASS/FAIL with the relevant output (trim long logs). On a failure,
    include the server log lines around it (the `ai --server` terminal) and the traceback if any.
