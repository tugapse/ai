# 6. Models

JARVIS talks to models through one common interface, so the same chat, tasks and agents work with
a local GGUF file, Ollama, Hugging Face Transformers, a cloud API, or another JARVIS.

- [Providers](#providers)
- [Model configs](#model-configs)
- [Choosing a model](#choosing-a-model)
- [Which model for what](#which-model-for-what)
- [Provider details](#provider-details)
- [When the model doesn't fit in the GPU](#when-the-model-doesnt-fit-in-the-gpu)
- [Adding a provider](#adding-a-provider)
- [Code map](#code-map)

---

## Providers

| `model_type` | Runs | Engine to install (`ai install`) | Needs |
|--------------|------|---------------------------------|-------|
| `gguf` | Locally, with llama.cpp | Llama-CPP GGUF | A GGUF file (downloaded from Hugging Face automatically). GPU optional. |
| `ollama` | On an Ollama server | Ollama (Local API) | Ollama running (local or on your network). |
| `causal_lm` | Locally, with Hugging Face Transformers | Transformers (HF) | PyTorch; a GPU for anything but small models. |
| `openai` | OpenAI or any OpenAI-compatible API (incl. Azure) | OpenAI (Cloud API) | An API key. |
| `gemini` | Google Gemini (API key or Vertex AI) | Gemini (API Key & Vertex AI) | An API key, or Google Cloud credentials. |
| `jarvis` | On a JARVIS Brain Server | Neural Link (Tiny PC Client) | A Brain Server reachable over HTTP. |

If a config uses an engine that isn't installed, JARVIS stops with a message telling you to run
`ai install`. What's installed is recorded in `installed_engines.json` next to the app.

## Model configs

A model config is a JSON file that says which model to load and how:

```json
{
  "model_name": "gemma4",
  "model_type": "gguf",
  "model_properties": {
    "model_repo_id": "unsloth/gemma-4-E4B-it-GGUF",
    "gguf_filename": "gemma-4-E4B-it-Q4_K_M.gguf",
    "n_gpu_layers": -1,
    "n_ctx": 35000,
    "max_new_tokens": 12096,
    "temperature": 0.8,
    "top_p": 0.8,
    "top_k": 50,
    "presence_penalty": 1.98,
    "frequency_penalty": 1.7
  }
}
```

- `model_name`: the model's name for the provider (a GGUF label, an Ollama tag, a Hugging Face id,
  an API model name…).
- `model_type`: one of the [providers](#providers).
- `model_properties`: generation settings plus provider-specific keys.

**Common properties:**

| Property | Default | Description |
|----------|---------|-------------|
| `temperature` | `0.5` | Randomness. Agents usually do better low (0.1–0.3). |
| `top_p`, `top_k` | `0.95`, `50` | Sampling limits. |
| `max_new_tokens` | `2048` | Longest answer. Also the output reserve the Context Sentinel keeps free. |
| `presence_penalty`, `frequency_penalty` | `1.0` | Discourage repetition. |
| `n_ctx` | provider default | Context window. Used by the Context Sentinel to know when to compress. |
| `enable_thinking` | `true` | Let reasoning models think (when the provider supports it). |
| `use_system_prompt` | `true` | Send a system prompt (turn off for models that don't support one). |
| `format` | — | Output format hint (e.g. JSON), when the provider supports it. |

**Where configs live:** `user/models/` (yours) and `system/models/` (shipped). A user config wins
over a system one with the same name. Subfolders are fine.

```bash
./run.sh models list                    # what's available
./run.sh --model agents/lite -m "hi"      # use one for this run (.json optional)
./run.sh models generate my-model --type gguf   # write a starting config
```

The default model is `MODEL_CONFIG_NAME` in `config.json` (initially `default.json`).

`ai models generate` writes the new file to `user/models/`; it refuses to replace an existing one
unless you add `--force`.

**Shipped configs** (in `system/models/`):

| Folder | Configs |
|--------|---------|
| (root) | `default` (Gemma 4 E4B GGUF), `jarvis-remote` |
| `agents/` | `default`, `flash`, `lite`, `gemma4-gguf`, `gemma4-26b-gguf`, `gemma4-100k`, `qwen36-35b-gguf` |
| `chat/` | `default` |
| `other/` | DeepSeek R1, Gemini (2.5, 2.5 Pro, flash), Gemma (GGUF and HF), Llama 3.1, Qwen 3 (GGUF CPU/GPU, HF), `jarvis-remote` |

## Choosing a model

Some practical rules:
- **Context window matters for agents.** Tool results, knowledge and history fill it fast. Aim for
  30k+ tokens (`n_ctx`) for agent work; the Context Sentinel compresses when it gets close.
- **Small models (≤ 8B)** handle chat and tasks fine. For agents, use the `small` pipeline (each
  agent has fewer tools) and keep `AGENT_TOOL_CATEGORIES` on.
- **Agents want low temperature** (0.1–0.3): they must follow the XML format and copy text exactly
  for `patch_file`.
- **Vision**: images (`-i`) need a vision-capable model; for GGUF, also its `mmproj_filename`.
- **One GPU, several uses**: if a Brain Server already has the model loaded, use it through a
  `jarvis` config instead of loading a second copy.

## Which model for what

Notes from real use. Each model is better at some things; this table grows over time.

| Model | Config | Good at | Weak at | Context / VRAM notes |
|-------|--------|---------|---------|----------------------|
| Gemma 4 E4B (GGUF Q4_K_M) | `default`, `agents/gemma4-gguf` | *to fill in* | | |
| Gemma 4 26B (GGUF) | `agents/gemma4-26b-gguf` | | | |
| Qwen 3.6 35B (GGUF) | `agents/qwen36-35b-gguf` | | | |
| Gemini flash | `agents/flash` | | | |
| DeepSeek R1 (GGUF) | `other/deepseek/...` | | | |

## Provider details

### gguf (llama.cpp)

| Property | Description |
|----------|-------------|
| `model_repo_id` | Hugging Face repository with the GGUF file. |
| `gguf_filename` | The file in that repo (required). Downloaded on first use and cached by Hugging Face. |
| `mmproj_filename` | Optional vision projector in the same repo; enables images. |
| `n_gpu_layers` | Layers on the GPU. `-1` = all, `0` = CPU only. |
| `n_ctx` | Context window (default 2048 if not set; set it). |
| `verbose` | llama.cpp logging. |

GPU support depends on how `llama-cpp-python` was built (CUDA, Vulkan…). `ai install` offers a CUDA
build and detects the CUDA version from `nvidia-smi`; see [Installation](09-installation.md#gpu-builds) for other GPUs.

### ollama

`model_name` is the Ollama tag (e.g. `llama3.1:8b`); it's pulled if missing. The server is
`127.0.0.1` unless you set `"host"` in `model_properties` (e.g. `"host": "http://192.168.1.10:11434"`).

### causal_lm (Hugging Face Transformers)

`model_name` is the Hugging Face id (e.g. `google/gemma-4-E4B-it`). `quantization_bits` (`4` or
`8`, via bitsandbytes) reduces memory use; `0` = full precision.

### openai

| Setting | Property | Environment variable |
|---------|----------|----------------------|
| API key | — | `AI_API_KEY` |
| Base URL (for compatible servers: LM Studio, vLLM, OpenRouter…) | `base_url` | — |
| Azure | `azure_endpoint`, `api_version` | `AI_AZURE_ENDPOINT`, `AI_API_VERSION` |

### gemini

- API key: `GEMINI_API_KEY`.
- Vertex AI: `"vertex_ai": true` in `model_properties`, with Google Cloud credentials
  (`GOOGLE_APPLICATION_CREDENTIALS` or `gcloud auth application-default login`) and
  `GOOGLE_CLOUD_PROJECT`.

### jarvis (Brain Server)

Sends the request to a JARVIS Brain Server, which runs the model there.

```json
{
  "model_name": "default",
  "model_type": "jarvis",
  "model_properties": {
    "base_url": "http://gpu-box:9999",
    "server_model": "agents/gemma4-gguf",
    "n_ctx": 30000,
    "max_new_tokens": 12096,
    "temperature": 0.1
  }
}
```

- `base_url`: the server (or `AI_API_BASE_URL`; default `http://127.0.0.1:9999`).
- `server_model`: the **server's** model config to use (or `AI_SERVER_MODEL`).
- `n_ctx`: the remote model's window, so the local Context Sentinel can do its job.

See [Server](07-server.md) for the server side and for relay mode, which does the same for a whole server.

### seq2seq_lm

Encoder-decoder models from Hugging Face (T5, FLAN-T5, BART), loaded by `T5Model`
(`core/llms/t5_model.py`). Uses the `transformers` engine, like `causal_lm`.

```json
{ "model_name": "google/flan-t5-base", "model_type": "seq2seq_lm",
  "model_properties": { "max_new_tokens": 256, "do_sample": false } }
```

The whole conversation is sent as one text ("System: … / User: … / Jarvis Ai: …") and the answer
comes back in one piece (no streaming). These models are good at short tasks such as translating
or summarising; they don't follow the agent format, so don't use them for agents.

## When the model doesn't fit in the GPU

If loading a local model fails for lack of GPU memory, JARVIS doesn't just crash. It shows who's
using the GPU (other JARVIS instances from its process registry, other programs from `nvidia-smi`)
and offers choices, for example:

- use the JARVIS server that's already running (it may already have this model);
- ask that server to switch to this model when it's free, or right away (cancelling its work);
- load the model here, partly on the GPU (slower).

It never stops another program by itself.

## Adding a provider

1. Subclass `BaseModel` (`src/ai/core/llms/base_llm.py`) and implement `chat` (streaming and
   non-streaming), plus loading and cleanup.
2. Use `api_retry.py` (`RetryPolicy`, `call_with_retry`, `stream_with_retry`) for network calls and
   raise `LLMAPIError` on failures, so agents report them as API errors and the session can be
   retried.
3. Add a `ModelType` (`src/ai/entities/model_enums.py`) and a `_create_*` branch in
   `EngineManager.load_model_instance` (`src/ai/services/engine_manager.py`).
4. Add the engine and its dependencies to `scripts/install_engines.py`, and to the engine check in
   `EngineManager.is_engine_installed`.

---

## Code map

| File | Role |
|------|------|
| `core/llms/base_llm.py` | `BaseModel` and `ModelParams` (common properties). |
| `core/llms/gguf_model.py` | llama.cpp (text and vision). |
| `core/llms/ollama_model.py` | Ollama. |
| `core/llms/huggingface_model.py`, `core/llms/hf/` | Transformers. |
| `core/llms/open_ai.py` | OpenAI and compatible APIs. |
| `core/llms/gemini.py` | Gemini (API key and Vertex). |
| `core/llms/jarvis.py` | Client for a JARVIS Brain Server. |
| `core/llms/api_retry.py` | Retries and `LLMAPIError`. |
| `core/llms/load_errors.py` | `GpuMemoryError` and friends. |
| `services/engine_manager.py` | Engine check and model instantiation. |
| `services/model_orchestrator.py` | Finds configs (`user/` → `system/`) and loads the model. |
| `services/gpu_advisor.py` | Choices when a model doesn't fit. |
| `model_config_manager.py` | `ai models generate`. |
