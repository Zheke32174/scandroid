# Codespaces — Session ctxmgr

For agents that want to offload work to a GitHub Codespace without
managing the start/stop lifecycle by hand.

## Quick example

```python
from scandroid.codespaces import Session

with Session(repository="zheke32174/scandroid") as cs:
    r = cs.run("python3 -c 'import torch; print(torch.cuda.is_available())'")
    print(r.stdout)
```

Behind the scenes:

1. Lists user codespaces; reuses the first one matching `repository`
   (and `ref` if specified).
2. If none, creates a fresh codespace.
3. If found-but-stopped, starts it.
4. Polls `state` every 4 seconds, up to 240 seconds total, until
   `Available`.
5. Hands control to your code.
6. On context exit: stops the codespace by default. Storage charges
   still accrue while stopped; pass `on_exit="delete"` to free that
   too, or `on_exit="leave"` to keep it running.

## API

```python
class Session:
    def __init__(
        self,
        repository: str,
        *,
        ref: Optional[str] = None,
        machine: Optional[str] = None,
        devcontainer_path: Optional[str] = None,
        on_exit: str = "stop",  # or "delete" | "leave"
        token: Optional[str] = None,
    ): ...

    def run(
        self, command: str, timeout: Optional[int] = None
    ) -> subprocess.CompletedProcess: ...
```

`token=` follows the [auth resolution chain](oauth.md#auth-resolution-chain).
The default uses the stored OAuth token from `authorize()`.

## Cost-control modes

| `on_exit=` | Compute cost | Storage cost | When to use |
|---|---|---|---|
| `"stop"` (default) | none | accrues | Agent runs that resume across multiple invocations. Frugal default — a crashed script won't leave a Codespace billed overnight. |
| `"delete"` | none | none | One-shot workloads with no state to preserve. |
| `"leave"` | accrues | accrues | Manual inspection — you'll log in via the GitHub UI to look around. |

## `gh` CLI dependency

`Session.run()` shells out to `gh codespace ssh -c <name> -- <command>`.
The GitHub REST API doesn't expose remote command execution; this
is the supported workaround.

The `gh` CLI must be installed on the agent VM:
<https://github.com/cli/cli#installation>.

You do **not** need to run `gh auth login` separately. `Session.run`
sets `GH_TOKEN` in the subprocess environment from the same auth
chain the rest of the module uses, supersedes any pre-existing gh
login, and is contained to the single subprocess — no mutation of
the user's persistent gh config.

For drivers that want to use `gh` directly (e.g., `gh codespace cp`,
`gh codespace logs`), there's a public helper:

```python
from scandroid.codespaces import _ensure_gh_token_env
import subprocess

env = _ensure_gh_token_env()
subprocess.run(["gh", "codespace", "logs", "-c", name], env=env, check=True)
```

## Lower-level functions

If `Session` is too opinionated for your case, the module exposes
the underlying lifecycle calls directly:

- `list_codespaces(token=None)` — returns the user's codespaces.
- `get_codespace(name, token=None)` — single codespace details.
- `create_codespace(repository, ref=None, machine=None, devcontainer_path=None, token=None)`.
- `start_codespace(name, token=None)`.
- `stop_codespace(name, token=None)`.
- `delete_codespace(name, token=None)`.
- `exec_in_codespace(name, command, token=None, timeout=None)`.

All honor the auth resolution chain.

## Failure modes

| Scenario | What you see |
|---|---|
| No credentials at all | `ValueError` from `_headers()` listing the three auth options. |
| Codespace creation hits quota | HTTP error from `requests` raised by `create_codespace`. |
| Codespace state stuck in `Provisioning` past 240s | `TimeoutError` from `Session._acquire`. |
| Codespace enters terminal `Failed` state | `RuntimeError` with the state name. |
| `gh codespace ssh` returns nonzero | Returned in the `CompletedProcess`; `check=False` so you handle it explicitly. |

## See also

- [OAuth device flow](oauth.md) — the recommended way to get
  credentials onto an agent VM.
- [Colab GPU offload](colab-bridge.md) — the lighter-weight
  offload path for inference workloads.
