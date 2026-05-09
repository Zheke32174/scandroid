# Healthcheck pre-flight

End-to-end probe an agent can run before deciding to offload to Colab.

## The call

```python
from scandroid import healthcheck

h = healthcheck(gist_id="<your-gist-id>")
if h["ok"]:
    use_colab(h["endpoint"]["url"], h["model"])
else:
    fall_back_to_local()  # h["error"] tells you which check failed
```

## Returned dict

```python
{
    "ok": bool,            # True only when every check passed
    "gist_ok": bool,       # gist read returned a valid endpoint
    "tunnel_ok": bool,     # GET {url}/api/tags returned 200
    "model_ok": bool,      # the published model is in Ollama's list
    "endpoint": {...},     # the gist payload (or None on failure)
    "model": "qwen2.5:14b",
    "tags": ["model:tag", ...],   # what Ollama is actually serving
    "elapsed_ms": int,
    "error": str | None,
}
```

No exceptions on partial failure — the function always returns the
state dict. Agents branch on `ok` (and on the granular flags when
they want a specific recovery path).

## Use case: provider rotation

```python
def select_backend():
    h = sd.healthcheck(gist_id=GID)
    if h["ok"]:
        return ("colab", h["endpoint"]["url"], h["model"])
    if not h["gist_ok"]:
        # Gist offline — Colab notebook isn't running. Skip ahead.
        return local_ollama_or_cloud()
    if not h["tunnel_ok"]:
        # Gist published but tunnel dead. Notebook may be in a
        # restart cycle; back off + retry once.
        ...
    if not h["model_ok"]:
        # Tunnel up but model not loaded. Notebook is still
        # warming. Back off.
        ...
```

The granular flags exist because each failure mode wants a
different recovery: gist-down vs tunnel-down vs model-cold each
imply different backoff strategies.

## Cost

`healthcheck()` makes one gist read + one HTTP GET to the
tunnel's `/api/tags` endpoint. Total round-trip is in the hundreds
of milliseconds; cheap enough to run before every offload if you
want.

## See also

- [Colab GPU offload](colab-bridge.md) — what you do once
  `healthcheck` says ok.
