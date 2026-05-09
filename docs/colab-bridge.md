# Colab GPU offload

A Colab notebook + a small Python module that lets agent VMs offload
inference to a free Colab T4 GPU without a host laptop in the loop.

## The shape

```
+-------------+     publishes     +-------------+
|  Colab      | ----------------> |  Private    |
|  notebook   |                   |  GitHub     |
|  (Ollama +  |                   |  Gist       |
|   tunnel)   |                   +-------------+
+-------------+                          ^
                                         | reads endpoint
                                         |
                                  +-------------+
                                  |  Agent VM   |
                                  |  (any —     |
                                  |   Codespace,|
                                  |   Claude VM,|
                                  |   local)    |
                                  +-------------+
```

**You** run the notebook. The agent never drives Colab itself —
it reads a gist you've authorized it to read, then connects to a
tunnel published by the running notebook. ToS-clean by construction.

## Notebook setup

Open [`scandroid.ipynb`](https://github.com/Zheke32174/scandroid/blob/main/scandroid.ipynb)
in Colab on a T4 GPU runtime. First-run options (all in left
sidebar → 🔑 Secrets, all optional):

- `NGROK_TOKEN` — from ngrok.com. More reliable than the
  cloudflare-quick fallback.
- `GIST_ID` — leave blank on first run; the cell auto-creates one
  and prints the ID. Paste back into Secrets for subsequent runs.
- `GITHUB_TOKEN` — *only* if you want to skip the OAuth device-flow
  prompt below. Needs `gist` scope.

Run all cells. The publish cell will print a URL + 6-digit code;
you open the URL on your phone, type the code, hit Approve. (Same
flow as `gh auth login`.) Token lives in the notebook session
memory only — not on Colab disk, not in Secrets.

The publish cell auto-installs scandroid from this repo if needed,
so the OAuth flow works even if you start from a stock Colab
runtime.

## Agent-side use

```python
import scandroid as sd

# Pre-flight: gist + tunnel + model presence in one call.
h = sd.healthcheck(gist_id="<your-gist-id>")
if h["ok"]:
    print(sd.generate("summarize log.txt", gist_id=h["endpoint"]["url"]))
else:
    print(f"Colab not available: {h['error']}")
    # fall through to local Ollama / Gemini / OpenAI
```

`healthcheck()` returns a state dict so an objective-runner can
make the rotate-to-Colab vs fall-back decision without try/except
spam. See [Healthcheck pre-flight](healthcheck.md).

## Tunnel selection

The notebook tries ngrok first (when `NGROK_TOKEN` is set), then
falls back to a cloudflare quick-tunnel. Both produce HTTPS URLs
the agent connects to over the public internet.

Cloudflare quick-tunnels expire after ~24 hours. ngrok sessions
last as long as the notebook runtime. The notebook's keep-alive
cell re-publishes the gist whenever the tunnel URL changes, so
agents reading the same gist transparently pick up new endpoints.

## What's published in the gist

```json
{
  "url":    "https://abc-def-ghi.ngrok-free.app",
  "model":  "qwen2.5:14b",
  "ts":     "2026-05-09T12:34:56Z",
  "tunnel": "ngrok"
}
```

Agents read this via `scandroid.bridge.discover()`. `model` is the
currently loaded Ollama model — the notebook auto-picks based on
available VRAM but accepts an override.

## API surface

```python
from scandroid import discover, generate, healthcheck

# Read the published endpoint.
endpoint = discover(gist_id="<id>")  # -> {url, model, ts, tunnel}

# Send a prompt; uses Ollama's /api/generate compatible API.
text = generate(
    "your prompt here",
    gist_id="<id>",
    model="qwen2.5:14b",   # optional override
    stream=False,
    timeout=600,
)

# One-call pre-flight.
h = healthcheck(gist_id="<id>")  # -> {ok, gist_ok, tunnel_ok, model_ok, ...}
```

## See also

- [Healthcheck pre-flight](healthcheck.md) — granular state for
  rotation decisions.
- [Codespaces Session ctxmgr](codespaces.md) — the heavier offload
  path for full-container workloads.
