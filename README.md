# Scandroid

Utilities to bridge work across Google Colab, OpenAI Codex-compatible APIs, and GitHub from a single notebook—without writing secrets or artifacts to local disk. You can keep everything in-memory and avoid mounting Drive if you have **no local space** available.

Part of a 5-repo cluster — see [CLUSTER.md](CLUSTER.md) for the
4-body nucleic orbit + connection house topology. This repo is a
**sapling** — an artifact produced by the understory trunk that
demonstrates Colab ↔ Codex ↔ GitHub bridge coordination.

## Public bridge

scandroid is the only public cluster repo. The other 4 cluster
repos (undergrowth, understory, system-soul-backup, zub) are
private. scandroid is deliberately public so unauthenticated
agents and readers can:

- See the cluster's topology ([CLUSTER.md](CLUSTER.md))
- Discover what the cluster is and how it fits together
- Read scandroid's own bridge code as a self-contained example
- Find pointers to the public framework repos the cluster inherits from

The full operational documentation (full `INHERIT.md`,
`BLUEPRINT.md`, `inherit/baseline.py`, `deploy/`, agent registry,
baseline pin) lives in the private `undergrowth` repo. scandroid's
[`INHERIT.md`](INHERIT.md) here is a redacted public stub pointing
there.

## Contents
- `scandroid.ipynb`: Colab GPU bridge notebook. **You** open it in Colab, it starts Ollama + a tunnel, publishes the endpoint to a private Gist. Public-friendly mirror of the cluster's `gigadeath_gpu_node` pattern.
- `scandroid/`: Pip-installable package.
  - `scandroid.bridge` — agent-side `discover` / `generate` helpers.
  - `scandroid.gist` — Gist publish/fetch using the `colab_endpoint.json` schema the cluster speaks.
  - `scandroid.codespaces` — GitHub Codespaces REST control.
  - Re-exports `integrations.py` helpers (Drive mount, OpenAI completions, runtime context).
- `integrations.py`: Original Colab/Codex/GitHub helpers. Re-exported under `scandroid`.
- `.claude/hooks/session-start.sh`: SessionStart hook that pip-installs the package on every Claude Code session (local + remote).
- `.devcontainer/setup.sh`: Codespaces post-create that does the same install.
- `bridge_setup.md`: Notes on capturing filesystem snapshots (e.g., `groot.html`).

## Why this exists

To offload CPU/RAM/GPU-heavy work from a small agent VM to a stronger model
running on Colab's free GPU — without violating Google's ToS. The user opens
the notebook (legitimate), the notebook self-publishes its tunnel URL to a
private Gist, agents read the Gist and connect to the tunnel. No automated
Google login, no UI scraping, no scope abuse. Aligned with this cluster's
[`AI-PARTICIPANTS-TOS-RULE.md`](https://github.com/Zheke32174/understory/blob/main/AI-PARTICIPANTS-TOS-RULE.md).

## Quick start (agent side)
1. Install the package:
   ```bash
   pip install --user -e .
   # optional:
   pip install --user -e .[papermill]   # headless notebook execution
   ```
2. Open `scandroid.ipynb` in Colab on a T4 GPU runtime. Add `GITHUB_TOKEN`
   (gist scope) and optionally `NGROK_TOKEN` to Colab Secrets. Run all cells.
   The notebook prints a `GIST_ID` on first run.
3. From any agent VM, with `GITHUB_TOKEN` in env:
   ```python
   from scandroid import generate
   print(generate("Say hello.", gist_id="<gist-id-from-step-2>"))
   ```
   Or set `SCANDROID_GIST_ID` once and drop the `gist_id=` argument.

## Agent access paths

The `scandroid` namespace is preloaded automatically in three environments so
any agent — local CLI or remote VM — can `from scandroid import …` without
extra setup:

- **Claude Code (local CLI or remote VM on the web)**: the SessionStart hook
  at `.claude/hooks/session-start.sh` runs `pip install --user -e .` on every
  session start. Registered via `.claude/settings.json`.
- **GitHub Codespaces**: `.devcontainer/setup.sh` runs the same install during
  `postCreateCommand`.
- **Anywhere else**: `pip install -e .` from a fresh checkout.

## Bridge protocol

`scandroid.ipynb` and `scandroid.bridge` interoperate with the cluster's
`colab-watcher` daemon. The contract is a private Gist containing one file,
`colab_endpoint.json`:

```json
{
  "url":    "https://abc.trycloudflare.com",
  "model":  "qwen2.5:14b",
  "ts":     "2026-05-09T15:30:00Z",
  "tunnel": "ngrok"
}
```

The notebook updates this file whenever the tunnel URL changes (e.g. ngrok
session renewal). Any consumer — `scandroid.bridge.discover()`,
`colab-watcher`, a hand-rolled curl — picks up the new URL on next read.

## Codespaces from a VM (`scandroid.codespaces`)

Wraps the GitHub Codespaces REST API so an agent can drive a Codespace as
backing compute without a local `gh` install:

```python
from scandroid.codespaces import (
    list_codespaces, create_codespace, start_codespace,
    stop_codespace, delete_codespace, exec_in_codespace,
)
# Requires GITHUB_TOKEN with the `codespace` scope.
```
`exec_in_codespace` shells out to `gh codespace ssh` and is the only function
that requires the `gh` CLI on the calling VM.

## Headless notebook runs

```bash
papermill scandroid.ipynb out.ipynb -p KEEPALIVE False
```
The notebook has a `parameters`-tagged cell so papermill can override `MODEL`,
`KEEPALIVE`, etc. Pass `KEEPALIVE=False` for smoke tests so cell 8 doesn't
block forever.

## Secrets

Set these as environment variables on the agent VM (the SessionStart hook
reads them; the notebook reads them from Colab Secrets):

```bash
export GITHUB_TOKEN="ghp_..."        # gist scope (and `codespace` if using scandroid.codespaces)
export SCANDROID_GIST_ID="..."       # convenient default for scandroid.bridge.discover()
export OPENAI_API_KEY="sk-..."       # only if using run_codex_completion
```

Inside a notebook you can also use the in-memory pattern (nothing touches disk):

```python
import getpass
from scandroid import set_runtime_secrets

set_runtime_secrets(
    openai_api_key=getpass.getpass("OPENAI_API_KEY: "),
    github_token=getpass.getpass("GITHUB_TOKEN: "),
)
```

## Other helpers in `integrations` (re-exported under `scandroid`)
The `integrations.py` module exposes convenience functions:
- `mount_colab_drive(force_remount=False)`: Mounts your Google Drive at `/content/drive` inside Colab.
- `run_codex_completion(prompt, model="gpt-4o-mini", api_key=None, **kwargs)`: Sends a prompt to an OpenAI chat-completions model for code generation or assistance.
- `get_github_user(token=None)`: Fetches the authenticated GitHub user profile using the provided token or `GITHUB_TOKEN`/`GH_TOKEN`.
- `set_runtime_secrets(openai_api_key=None, github_token=None)`: Stores secrets in memory-backed environment variables so nothing is written to disk.
- `runtime_ready(require_openai=True, require_github=True)`: Quickly verify whether the required secrets are present before connecting.
- `runtime_context()`: Inspect whether you are running in Colab, whether Drive is mounted, and whether required tokens are present. Reads OS mount state but does not write to disk or persist anything.

Example usage inside the notebook:
```python
from integrations import mount_colab_drive, run_codex_completion, get_github_user

# Mount Google Drive (prompts for authorization inside Colab)
# mount_colab_drive()

# Query GitHub identity
# me = get_github_user()
# print(me["login"])

# Generate code with Codex-style completion
# code = run_codex_completion("Write a Python function that reverses a string")
# print(code)

# Inspect runtime state (no writes to disk)
# from integrations import runtime_context
# print(runtime_context())
```

## Tips
- When running in GitHub Codespaces, the `.devcontainer` files will bootstrap a consistent environment.
- Keep tokens in environment variables or a local secrets manager; avoid committing credentials to the repository.
- Update `bridge_setup.md` if you change how filesystem snapshots are generated.
