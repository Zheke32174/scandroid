# scandroid

Bridge utilities for Colab + GitHub + AI workflows from a single
notebook — no secrets to local disk, OAuth-only auth, lightweight
Python module.

## Install

```bash
pip install git+https://github.com/Zheke32174/scandroid.git
```

Requires Python 3.9+. Uses stdlib + `requests`. The `gh` CLI is
needed for the Codespaces shell-out (`gh codespace ssh`); install
from <https://github.com/cli/cli>.

## What's in here

- **`scandroid/oauth.py`** — GitHub OAuth device flow
- **`scandroid/google_oauth.py`** — Google OAuth device flow
- **`scandroid/google.py`** — Drive / userinfo wrappers
- **`scandroid/codespaces.py`** — Codespaces lifecycle + `Session` ctxmgr
- **`scandroid/bridge.py`** — Colab endpoint discovery + inference helpers
- **`scandroid/gist.py`** — Gist-as-shared-state primitives
- **`scandroid/approval.py`** — Phone-tap approval gate client
- **`scandroid.ipynb`** — Colab notebook for the GPU offload pattern
- **`scripts/colab-bootstrap.py`** — One-liner Colab cell target
- **`scripts/smoke-test.py`** — Agent-side surface verification
- **`worker/`** — Cloudflare Worker source for the approval gate

## Quick example

```python
from scandroid.codespaces import authorize, Session
import scandroid as sd

authorize()                     # one-time phone tap to grant OAuth
print(sd.healthcheck(gist_id="...")["ok"])

with Session(repository="zheke32174/scandroid") as cs:
    print(cs.run("uname -a").stdout)
```

## License

See [LICENSE](LICENSE).
