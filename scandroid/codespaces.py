"""GitHub Codespaces helpers.

Thin wrapper over the Codespaces REST API so an agent VM can list, create,
start, stop, and delete Codespaces without a local ``gh`` install. ``exec``
is provided as an opt-in convenience that shells out to ``gh codespace ssh``
when available; the REST API itself does not expose remote command execution.

Authentication, in order of resolution:

1. Explicit ``token=`` parameter on each call.
2. ``GITHUB_TOKEN`` or ``GH_TOKEN`` env var (PAT-style, codespace scope).
3. Stored OAuth token from a prior ``authorize()`` device-flow run
   (see ``scandroid.oauth``). The user runs ``authorize()`` once on
   their phone / laptop to grant the agent VM long-lived access
   without ever pasting a PAT.

The third path is the headless-agent-friendly default. PAT-based
auth still works for cases where a long-lived service token is more
convenient, but new deployments should prefer device-flow OAuth so
authorization is bound to the user's GitHub account directly.

References:
    https://docs.github.com/en/rest/codespaces/codespaces
"""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional

from . import oauth as _oauth

API = "https://api.github.com"
__all__ = [
    "list_codespaces",
    "get_codespace",
    "create_codespace",
    "start_codespace",
    "stop_codespace",
    "delete_codespace",
    "exec_in_codespace",
    "authorize",
    "deauthorize",
]


def _resolve_token(token: Optional[str]) -> Optional[str]:
    """Walk the auth-source chain and return the first hit.

    Doesn't raise on miss — callers compose error messages with
    context-appropriate hints (PAT vs device-flow). Public so the
    callers can also surface "we'd be using <source>" if they want.
    """
    if token:
        return token
    env = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if env:
        return env
    stored = _oauth.load()
    if stored and stored.get("access_token"):
        return stored["access_token"]
    return None


def _headers(token: Optional[str]) -> Dict[str, str]:
    tok = _resolve_token(token)
    if not tok:
        raise ValueError(
            "No GitHub credentials available. Pick one:\n"
            "  - Pass token= on the call.\n"
            "  - Set GITHUB_TOKEN or GH_TOKEN in env (codespace + repo scope).\n"
            "  - Run scandroid.codespaces.authorize() once to grant access "
            "via OAuth device flow (no PAT needed)."
        )
    return {
        "Authorization": f"Bearer {tok}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def authorize(
    client_id: Optional[str] = None,
    scope: Optional[str] = None,
    on_user_code: Optional[Any] = None,
) -> Dict[str, Any]:
    """Walk the GitHub OAuth device flow + persist the resulting token.

    One-time setup. The agent VM prints a URL + 6-digit code; the user
    opens the URL on their phone / laptop, types the code, hits
    Approve. The agent receives a long-lived access token and stores
    it at ``~/.config/scandroid/github_oauth.json`` (mode 0600).

    Subsequent calls to any function in this module pick up the stored
    token automatically — no env-var dance, no PAT paste.

    Pass ``client_id`` if you've registered your own OAuth App
    (recommended for production agents); default is the GitHub CLI's
    public client_id which lets the user authorize the same way they
    would with ``gh auth login``.

    ``on_user_code(code, uri, expires_in)`` is invoked with the
    user-facing prompt instead of ``print`` if provided. Useful for
    routing the prompt to an ntfy push, the agent 2FA gate, etc.

    Returns the token response dict; raises ``RuntimeError`` if the
    user denies, the device code expires, or the agent is offline.
    """
    return _oauth.authorize(client_id=client_id, scope=scope, on_user_code=on_user_code)


def deauthorize() -> bool:
    """Delete the stored OAuth token. Returns True if one was deleted.

    GitHub-side revocation is a separate step: visit
    https://github.com/settings/applications and revoke the OAuth app
    grant. This call only removes the local on-disk token.
    """
    return _oauth.clear()


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
