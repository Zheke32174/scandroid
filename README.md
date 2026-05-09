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
- `scandroid/`: Python package — re-exports the helpers from `integrations.py` and adds `scandroid.codespaces` for GitHub Codespaces REST control. Pip-installable.
- `scandroid.ipynb`: Blank-slate notebook scaffold (parameters cell + namespace check). Runnable headlessly via papermill.
- `integrations.py`: Original helpers for mounting Google Drive in Colab, calling OpenAI models, and retrieving GitHub user data. Re-exported under `scandroid`.
- `.claude/hooks/session-start.sh`: SessionStart hook that pip-installs the package on every Claude Code session (local + remote).
- `.devcontainer/setup.sh`: Codespaces post-create that does the same install.
- `bridge_setup.md`: Notes on capturing filesystem snapshots (e.g., `groot.html`).

## Quick start
1. Install the package (editable). Pulls `openai` + `requests` and exposes the
   `scandroid` namespace anywhere on `sys.path`:
   ```bash
   pip install --user -e .
   # optional extras:
   pip install --user -e .[papermill]   # headless notebook execution
   ```
2. Open the notebook directly in Colab using the badge at the top of `scandroid.ipynb` or via [this link](https://colab.research.google.com/github/Zheke32174/scandroid/blob/main/scandroid.ipynb).

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

## Headless notebook runs (optional)
```bash
papermill scandroid.ipynb out.ipynb -p label demo
```
The notebook has a `parameters`-tagged cell (`label = "default"`) that
papermill overwrites at runtime. The default scaffold prints
`runtime_context()` so a successful execution doubles as a smoke test.

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
that requires the `gh` CLI on the calling VM (the REST API has no direct
remote-exec endpoint).
3. Add your secrets as environment variables inside Colab or your local shell. In ephemeral environments (e.g., Colab), prefer in-memory variables so nothing touches local storage:
   ```bash
   export OPENAI_API_KEY="sk-..."
   export GITHUB_TOKEN="ghp_..."  # or GH_TOKEN
   ```
   Or inside a notebook:
   ```python
   import getpass
   from integrations import set_runtime_secrets

   set_runtime_secrets(
       openai_api_key=getpass.getpass("OPENAI_API_KEY: "),
       github_token=getpass.getpass("GITHUB_TOKEN: "),
   )
   ```

## Using the helpers
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
