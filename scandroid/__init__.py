"""scandroid namespace.

Re-exports the helpers from ``integrations`` under a stable, importable name so
any agent VM can ``from scandroid import …`` regardless of cwd, instead of
relying on the bare ``integrations`` module being on sys.path.

Submodules:
- ``scandroid.codespaces``: GitHub Codespaces REST API helpers (always
  available; needs a ``GITHUB_TOKEN`` with the ``codespace`` scope).
- ``scandroid.drive``: Google Drive API helpers for syncing the notebook to
  and from Drive. Requires the ``[drive]`` extra (``pip install
  scandroid[drive]``) and a service-account JSON.
"""
from integrations import (  # noqa: F401
    mount_colab_drive,
    get_github_user,
    run_codex_completion,
    set_runtime_secrets,
    runtime_ready,
    runtime_context,
)

__all__ = [
    "mount_colab_drive",
    "get_github_user",
    "run_codex_completion",
    "set_runtime_secrets",
    "runtime_ready",
    "runtime_context",
]
