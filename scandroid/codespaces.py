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
    "Session",
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


def exec_in_codespace(
    name: str,
    command: str,
    token: Optional[str] = None,
    timeout: Optional[int] = None,
) -> subprocess.CompletedProcess:
    """Run ``command`` inside a running Codespace via ``gh codespace ssh``.

    Requires the ``gh`` CLI installed on the calling VM. ``gh`` is
    authenticated automatically from the same auth chain the rest of
    this module uses (explicit token > env var > stored OAuth token);
    callers don't need to run ``gh auth login`` separately.

    The REST API does not expose remote exec; ``gh codespace ssh`` is
    the supported workaround. ``gh`` invokes ssh against the Codespace's
    container, so the container must be running (use :func:`Session` to
    auto-start, or call :func:`start_codespace` first).
    """
    if not shutil.which("gh"):
        raise RuntimeError(
            "gh CLI not found. Install GitHub CLI: "
            "https://github.com/cli/cli#installation"
        )
    env = os.environ.copy()
    # gh reads GH_TOKEN first, then GITHUB_TOKEN. Setting GH_TOKEN here
    # supersedes any pre-existing gh login, so the agent's OAuth token
    # path always wins. We don't `gh auth login --with-token` because
    # that would mutate the user's persistent gh config — env-var path
    # is contained to this subprocess only.
    resolved = _resolve_token(token)
    if resolved:
        env["GH_TOKEN"] = resolved
    return subprocess.run(
        ["gh", "codespace", "ssh", "-c", name, "--", command],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        timeout=timeout,
    )


def _ensure_gh_token_env(token: Optional[str] = None) -> Dict[str, str]:
    """Return an env dict with GH_TOKEN populated from the auth chain.

    Public helper for callers that want to drive ``gh`` directly with
    the same credentials this module uses (e.g. ``gh codespace cp`` or
    ``gh codespace logs``). Prefers explicit ``token=`` then env vars
    then stored OAuth token. Raises if nothing is found.
    """
    env = os.environ.copy()
    resolved = _resolve_token(token)
    if not resolved:
        raise ValueError(
            "No GitHub credentials available; run "
            "scandroid.codespaces.authorize() first."
        )
    env["GH_TOKEN"] = resolved
    return env


class Session:
    """Codespace lifecycle context manager — agent-friendly compute handle.

    Use case: an agent VM wants to offload a workload to a Codespace
    without managing the start/stop/teardown lifecycle by hand. Wraps
    the lower-level functions so the typical pattern becomes::

        from scandroid.codespaces import Session

        with Session(repository="zheke32174/scandroid") as cs:
            r = cs.run("python3 my_script.py")
            print(r.stdout)

    Behavior:
      - On enter: lists user codespaces; reuses the first one matching
        ``repository`` (and ``ref`` if specified). If none, creates one.
        If found-but-stopped, starts it. Polls the codespace state
        until it reports ``Available``.
      - ``run(cmd)`` shells out to ``exec_in_codespace`` with the
        session's GH_TOKEN env wired up.
      - On exit: by default STOPS the codespace (prepaid hours don't
        accrue while stopped, but storage does). Pass
        ``on_exit="delete"`` to delete instead, or ``on_exit="leave"``
        to leave running.

    The "stop on exit" default matches the agent-frugal posture: an
    objective-runner shouldn't accidentally leave a Codespace billed
    overnight because a script crashed.
    """

    POLL_INTERVAL_S = 4
    READY_TIMEOUT_S = 240

    def __init__(
        self,
        repository: str,
        *,
        ref: Optional[str] = None,
        machine: Optional[str] = None,
        devcontainer_path: Optional[str] = None,
        on_exit: str = "stop",
        token: Optional[str] = None,
    ) -> None:
        if on_exit not in ("stop", "delete", "leave"):
            raise ValueError(f"on_exit must be stop|delete|leave, got {on_exit!r}")
        self.repository = repository
        self.ref = ref
        self.machine = machine
        self.devcontainer_path = devcontainer_path
        self.on_exit = on_exit
        self.token = token
        self.name: Optional[str] = None
        self.created: bool = False

    def __enter__(self) -> "Session":
        self._acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.name is None:
            return
        if self.on_exit == "stop":
            try:
                stop_codespace(self.name, token=self.token)
            except Exception:
                pass
        elif self.on_exit == "delete":
            try:
                delete_codespace(self.name, token=self.token)
            except Exception:
                pass
        # "leave" — no-op.

    def run(
        self, command: str, timeout: Optional[int] = None
    ) -> subprocess.CompletedProcess:
        """Execute ``command`` inside the Codespace. See :func:`exec_in_codespace`."""
        if self.name is None:
            raise RuntimeError("Session not entered (use 'with Session(...) as cs:').")
        return exec_in_codespace(
            self.name, command, token=self.token, timeout=timeout
        )

    def _acquire(self) -> None:
        """Find or create a Codespace for ``repository``, ensure it's running."""
        import time as _time

        existing = list_codespaces(token=self.token)
        match = None
        for cs in existing:
            if cs.get("repository", {}).get("full_name") == self.repository:
                if self.ref is None or cs.get("git_status", {}).get("ref") == self.ref:
                    match = cs
                    break
        if match is None:
            created = create_codespace(
                self.repository,
                ref=self.ref,
                machine=self.machine,
                devcontainer_path=self.devcontainer_path,
                token=self.token,
            )
            self.name = created["name"]
            self.created = True
        else:
            self.name = match["name"]
            if match.get("state") not in ("Available", "Starting"):
                start_codespace(self.name, token=self.token)

        # Poll until available. 'state' transitions through Provisioning ->
        # Building -> Starting -> Available; Failed / ShuttingDown / Stopped
        # are terminal-ish and require us to bail.
        deadline = _time.monotonic() + self.READY_TIMEOUT_S
        while _time.monotonic() < deadline:
            cs = get_codespace(self.name, token=self.token)
            state = cs.get("state")
            if state == "Available":
                return
            if state in ("Failed", "Unknown"):
                raise RuntimeError(
                    f"Codespace {self.name} entered terminal state {state!r}"
                )
            _time.sleep(self.POLL_INTERVAL_S)
        raise TimeoutError(
            f"Codespace {self.name} not Available after {self.READY_TIMEOUT_S}s"
        )
