"""GitHub Codespaces helpers.

Thin wrapper over the Codespaces REST API so an agent VM can list, create,
start, stop, and delete Codespaces without a local ``gh`` install. ``exec``
is provided as an opt-in convenience that shells out to ``gh codespace ssh``
when available; the REST API itself does not expose remote command execution.

Requires a ``GITHUB_TOKEN`` (or ``GH_TOKEN``) with the ``codespace`` scope.
Pass ``token=`` explicitly if you do not want to rely on env vars.

References:
    https://docs.github.com/en/rest/codespaces/codespaces
"""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional

API = "https://api.github.com"
__all__ = [
    "list_codespaces",
    "get_codespace",
    "create_codespace",
    "start_codespace",
    "stop_codespace",
    "delete_codespace",
    "exec_in_codespace",
]


def _headers(token: Optional[str]) -> Dict[str, str]:
    tok = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not tok:
        raise ValueError(
            "Provide a GitHub token (codespace scope) or set GITHUB_TOKEN/GH_TOKEN."
        )
    return {
        "Authorization": f"Bearer {tok}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _requests():
    try:
        import requests  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            "scandroid.codespaces requires 'requests'. Install with: pip install requests"
        ) from e
    return __import__("requests")


def list_codespaces(token: Optional[str] = None) -> List[Dict[str, Any]]:
    r = _requests().get(f"{API}/user/codespaces", headers=_headers(token), timeout=15)
    r.raise_for_status()
    return r.json().get("codespaces", [])


def get_codespace(name: str, token: Optional[str] = None) -> Dict[str, Any]:
    r = _requests().get(
        f"{API}/user/codespaces/{name}", headers=_headers(token), timeout=15
    )
    r.raise_for_status()
    return r.json()


def create_codespace(
    repository: str,
    *,
    ref: Optional[str] = None,
    machine: Optional[str] = None,
    devcontainer_path: Optional[str] = None,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a Codespace for ``owner/repo``.

    Parameters
    ----------
    repository: str
        ``owner/repo`` slug. Resolved to a numeric ``repository_id`` first.
    ref: Optional[str]
        Branch/ref to check out. Defaults to the repo's default branch.
    machine: Optional[str]
        Machine type (e.g. ``basicLinux32gb``). Omit for the API default.
    devcontainer_path: Optional[str]
        Path to a non-default devcontainer config inside the repo.
    """
    requests = _requests()
    repo_resp = requests.get(
        f"{API}/repos/{repository}", headers=_headers(token), timeout=15
    )
    repo_resp.raise_for_status()
    repo_id = repo_resp.json()["id"]
    body: Dict[str, Any] = {"repository_id": repo_id}
    if ref:
        body["ref"] = ref
    if machine:
        body["machine"] = machine
    if devcontainer_path:
        body["devcontainer_path"] = devcontainer_path
    r = requests.post(
        f"{API}/user/codespaces", headers=_headers(token), json=body, timeout=30
    )
    r.raise_for_status()
    return r.json()


def start_codespace(name: str, token: Optional[str] = None) -> Dict[str, Any]:
    r = _requests().post(
        f"{API}/user/codespaces/{name}/start", headers=_headers(token), timeout=30
    )
    r.raise_for_status()
    return r.json()


def stop_codespace(name: str, token: Optional[str] = None) -> Dict[str, Any]:
    r = _requests().post(
        f"{API}/user/codespaces/{name}/stop", headers=_headers(token), timeout=30
    )
    r.raise_for_status()
    return r.json()


def delete_codespace(name: str, token: Optional[str] = None) -> None:
    r = _requests().delete(
        f"{API}/user/codespaces/{name}", headers=_headers(token), timeout=30
    )
    r.raise_for_status()


def exec_in_codespace(name: str, command: str) -> subprocess.CompletedProcess:
    """Run ``command`` inside a running Codespace via ``gh codespace ssh``.

    Requires the ``gh`` CLI installed on the calling VM and an authenticated
    ``gh`` session (``gh auth login`` or ``GH_TOKEN`` env var). The REST API
    does not expose remote exec; this is the supported workaround.
    """
    if not shutil.which("gh"):
        raise RuntimeError(
            "gh CLI not found. Install GitHub CLI to use exec_in_codespace."
        )
    return subprocess.run(
        ["gh", "codespace", "ssh", "-c", name, "--", command],
        capture_output=True,
        text=True,
        check=False,
    )
