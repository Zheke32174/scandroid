"""scandroid namespace.

Re-exports the helpers from ``integrations`` and the Colab offload bridge so
any agent VM can ``from scandroid import …`` regardless of cwd.

Top-level helpers:
- ``runtime_context`` / ``runtime_ready`` / ``set_runtime_secrets`` / etc.:
  thin re-exports of ``integrations.py``.
- ``discover(gist_id)``: read the live colab endpoint from a Gist.
- ``generate(prompt, gist_id=...)``: send a prompt to the Ollama endpoint
  the notebook is serving and return the response.

Submodules:
- ``scandroid.gist``: GitHub Gist publish/fetch for the
  ``colab_endpoint.json`` schema the cluster speaks.
- ``scandroid.bridge``: high-level discover/generate.
- ``scandroid.codespaces``: GitHub Codespaces REST API helpers.
  Auth resolves through explicit token > GITHUB_TOKEN env > stored
  OAuth device-flow token.
- ``scandroid.oauth``: GitHub OAuth device-flow helpers. Run
  ``scandroid.oauth.authorize()`` once on the agent VM; user
  approves on their phone / laptop; the agent gets a long-lived
  access token without a PAT.
- ``scandroid.approval``: agent action 2FA gate. Posts approval
  requests to a Cloudflare Worker; user resolves on phone via push
  + aegis TOTP. See worker/README.md for deploy.
"""
from integrations import (  # noqa: F401
    mount_colab_drive,
    get_github_user,
    run_codex_completion,
    set_runtime_secrets,
    runtime_ready,
    runtime_context,
)

from .bridge import discover, generate  # noqa: F401

__all__ = [
    "mount_colab_drive",
    "get_github_user",
    "run_codex_completion",
    "set_runtime_secrets",
    "runtime_ready",
    "runtime_context",
    "discover",
    "generate",
]
