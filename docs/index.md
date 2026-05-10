# scandroid

**Public bridge artifact of the understory cluster.**

scandroid is the only repo in the cluster that's deliberately public.
It carries the bridge tooling that lets agent VMs offload work to
Colab GPUs, drive GitHub Codespaces via user OAuth (no PAT), and
gate sensitive actions through a phone-side approval flow — all
without a host-local machine in the loop.

If you landed here from a search and don't know the wider context:
this is one piece of a small, quiet AI infrastructure project. The
bridge ships in the open; the rest does not.

## What's in here

```python
import scandroid as sd
from scandroid.codespaces import authorize, Session

# One-time per agent VM. Prints a URL + 6-digit code; you approve
# on your phone, the agent gets a long-lived OAuth token. No PAT
# pasting, no host laptop in the loop.
authorize()

# Light offload (Colab Ollama, GPU-backed):
if sd.healthcheck(gist_id=GID)["ok"]:
    print(sd.generate("summarize log.txt", gist_id=GID))

# Heavy offload (a full Codespace container):
with Session(repository="zheke32174/scandroid") as cs:
    print(cs.run("python3 -c 'import torch; print(torch.cuda.is_available())'").stdout)
```

That's the whole agent-side surface. Three calls, no PATs.

## Components

### Colab GPU bridge

A Jupyter notebook ([`scandroid.ipynb`][nb]) that runs Ollama on a
free Colab T4 GPU, opens a tunnel (ngrok preferred, cloudflare
quick-tunnel as fallback), and publishes the live endpoint to a
private GitHub Gist. Any agent VM with the `gist_id` can then
issue requests directly. **You** run the notebook — the agent
only reads the gist + connects to the tunnel. ToS-clean by
construction.

See [Colab GPU offload](colab-bridge.md) for the walkthrough.

[nb]: https://github.com/Zheke32174/scandroid/blob/main/scandroid.ipynb

### Codespaces under user auth

`scandroid.codespaces` wraps the GitHub Codespaces REST API. Auth
resolves through a fallback chain (explicit `token=` → `GITHUB_TOKEN`
env → stored OAuth token from `authorize()`). The default path
uses **OAuth device flow** — same UX as `gh auth login`, but
scriptable from a headless agent.

The `Session` context manager gives you a one-line "use a Codespace
as compute" pattern: list-or-create, start, poll-until-Available,
run commands, stop on exit. Cost-control on-exit modes
configurable.

See [OAuth device flow](oauth.md) and [Session ctxmgr](codespaces.md).

### Agent action 2FA gate

`scandroid.approval` posts approval requests to a Cloudflare Worker
+ KV. The user resolves on their phone via push notification + a
TOTP code from the cluster's local TOTP authenticator. Used for
high-leverage agent actions: identity-honest, scope-honored, no
silent escalation.

See [Agent action 2FA](agent-2fa-gate.md).

## Installation

```bash
pip install git+https://github.com/Zheke32174/scandroid.git
```

Requires Python 3.9+. Uses only stdlib + `requests` (and `gh` CLI
for the Codespaces shell-out).

## Verifying it works

Agent-side smoke test on any VM after install — runs without
operator interaction:

```bash
python3 scripts/smoke-test.py
# 12/12 passed
# Agent-side surface healthy.
```

For full end-to-end (needs phone + GitHub account), see the
[operator test walkthrough](operator-test-walkthrough.md). It
covers OAuth device-flow approval, Codespace lifecycle, notebook
publish, Pages deploy, and the Android device-snapshot path —
each with concrete pass criteria and common failure modes.

## Why public

The understory cluster is mostly private. scandroid is the
cluster's public bridge — an artifact agents from outside can pull
to bootstrap their own offload + auth + approval flows, and a
recognizable surface for anyone trying to understand what we do.

What's deliberately NOT here:
- The cluster's full topology (private)
- Inherited doctrine documents (private — see undergrowth)
- The on-device Android suite (private — see understory)
- Operational runbooks (private)

## Project posture

- **OAuth-only**, no API key files. All cloud auth goes through
  OAuth tokens stored under user control.
- **Sandboxed by default**. Sensitive work runs in containers
  (Codespaces) or remote runtimes (Colab) with hard human gates
  for anything that affects shared state.
- **Honest stubs over silent breakage**. When a feature can't be
  fully delivered, the code ships the architecture + UI with
  explicit "still pending" copy rather than empty paths.

## License

See the [LICENSE](https://github.com/Zheke32174/scandroid/blob/main/LICENSE)
file in the repo.
