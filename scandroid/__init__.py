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
