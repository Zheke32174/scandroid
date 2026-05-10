"""GitHub OAuth — Device Flow for headless agents.

Usable from any Claude VM / Codespace / agent remote that doesn't have a
browser. The user runs an authorization step ONCE on their phone / laptop
(open a URL, type a 6-digit code, click Approve), and the agent receives
a long-lived access token it can use for the GitHub API thereafter — no
PAT (personal access token) creation, no token paste, no token-on-disk
copy-paste.

Why device flow specifically:
    GitHub OAuth has three flavors. The web flow needs a redirect URL
    + browser; bad for headless agents. The PKCE flow is the same.
    The device flow is exactly the shape we want: the agent generates
    a code, prints a URL, and polls until the user authorizes from
    any device with a browser. No callback URL needed; no agent-side
    HTTP server.

Reference: https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#device-flow

Token storage:
    ~/.config/scandroid/github_oauth.json with mode 0600. Schema:
        {
            "access_token": "<token>",
            "scope": "codespace,repo,...",
            "stored_at_ms": 1700000000000,
            "client_id": "<the OAuth app's client_id>"
        }
    Loaded automatically by scandroid.codespaces._headers when no
    explicit token + no GITHUB_TOKEN env var.

Client ID:
    Defaults to the GitHub CLI's published client_id
    ("178c6fc778ccc68e1d6a"). The CLI's id is intentionally public —
    using it lets users authorize the same way they would with `gh
    auth login`, with the GitHub UI showing "GitHub CLI" as the
    requesting app. To use your own OAuth App: register one at
    https://github.com/settings/developers (Device Flow checked) and
    set $SCANDROID_GITHUB_CLIENT_ID or pass client_id= explicitly.
"""
from __future__ import annotations

import json
import os
import stat
import time
from typing import Any, Dict, Optional

__all__ = [
    "begin",
    "poll",
    "authorize",
    "store",
    "load",
    "clear",
    "DEFAULT_CLIENT_ID",
    "DEFAULT_SCOPES",
]

# GitHub CLI's publicly-known OAuth app client id. Same one `gh auth login`
# walks users through, so the GitHub authorization page shows "GitHub CLI"
# as the requesting app — recognizable + already-trusted by most users.
DEFAULT_CLIENT_ID = "178c6fc778ccc68e1d6a"

# Default scopes for codespaces work. `codespace` is required for the
# Codespaces REST API; `repo` is needed to list/clone private repos
# the user might want a Codespace built against.
DEFAULT_SCOPES = "codespace repo"

DEVICE_CODE_URL = "https://github.com/login/device/code"
TOKEN_URL = "https://github.com/login/oauth/access_token"


def _config_dir() -> str:
    """Resolve the storage directory. Honors $XDG_CONFIG_HOME; defaults to
    ``~/.config``. Created with mode 0700 if missing."""
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    d = os.path.join(base, "scandroid")
    os.makedirs(d, mode=0o700, exist_ok=True)
    return d


def _token_path() -> str:
    return os.path.join(_config_dir(), "github_oauth.json")


def _requests():
    try:
        import requests  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            "scandroid.oauth requires 'requests'. pip install requests."
        ) from e
    return __import__("requests")


def begin(
    client_id: Optional[str] = None,
    scope: Optional[str] = None,
    timeout: int = 15,
) -> Dict[str, Any]:
    """Step 1 of device flow.

    Posts to GitHub's device-code endpoint. Returns ``{device_code,
    user_code, verification_uri, expires_in, interval}``. The agent
    must print ``user_code`` + ``verification_uri`` for the user, then
    call :func:`poll` with ``device_code``.
    """
    cid = client_id or os.environ.get("SCANDROID_GITHUB_CLIENT_ID") or DEFAULT_CLIENT_ID
    sc = scope or os.environ.get("SCANDROID_GITHUB_SCOPES") or DEFAULT_SCOPES
    rq = _requests()
    r = rq.post(
        DEVICE_CODE_URL,
        data={"client_id": cid, "scope": sc},
        headers={"Accept": "application/json"},
        timeout=timeout,
    )
    r.raise_for_status()
    body = r.json()
    body.setdefault("client_id", cid)
    body.setdefault("scope", sc)
    return body


def poll(
    device_code: str,
    client_id: Optional[str] = None,
    interval: int = 5,
    deadline: Optional[float] = None,
    timeout: int = 15,
) -> Dict[str, Any]:
    """Step 2 of device flow. Blocks until the user authorizes,
    declines, or the device-code expires.

    Returns ``{access_token, scope, token_type, ...}`` on success.
    Raises :class:`RuntimeError` with the GitHub-returned error string
    on ``access_denied`` / ``expired_token`` / unknown failures.

    ``deadline`` is an absolute monotonic-clock value past which the
    poll should give up (default: 15 minutes from now). The GitHub
    server-side device-code TTL is typically 15 minutes; matching it
    here surfaces the timeout cleanly to the caller.
    """
    cid = client_id or os.environ.get("SCANDROID_GITHUB_CLIENT_ID") or DEFAULT_CLIENT_ID
    rq = _requests()
    deadline_v = deadline if deadline is not None else (time.monotonic() + 900)
    sleep = max(1, interval)
    while time.monotonic() < deadline_v:
        r = rq.post(
            TOKEN_URL,
            data={
                "client_id": cid,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
            headers={"Accept": "application/json"},
            timeout=timeout,
        )
        body = r.json() if r.text else {}
        err = body.get("error")
        if not err and body.get("access_token"):
            return body
        if err == "authorization_pending":
            time.sleep(sleep)
            continue
        if err == "slow_down":
            # GitHub asks us to back off — increment sleep by 5s per docs.
            sleep += 5
            time.sleep(sleep)
            continue
        if err in ("expired_token", "access_denied", "incorrect_device_code", "unsupported_grant_type"):
            raise RuntimeError(f"Device flow failed: {err} ({body.get('error_description', '')})")
        if err:
            # Unknown error — surface verbatim instead of looping.
            raise RuntimeError(f"Device flow failed: {err} ({body.get('error_description', '')})")
        # No error and no token — back off conservatively.
        time.sleep(sleep)
    raise RuntimeError("Device flow polling timed out before user authorized.")


def authorize(
    client_id: Optional[str] = None,
    scope: Optional[str] = None,
    on_user_code: Optional[Any] = None,
) -> Dict[str, Any]:
    """One-shot convenience: begin + poll + store.

    Calls :func:`begin`, prints (or hands to ``on_user_code``) the
    user-facing URL + code, then polls until the user authorizes.
    On success stores the token via :func:`store` and returns the
    same ``{access_token, scope, ...}`` dict.

    ``on_user_code(code, verification_uri, expires_in)`` is invoked
    instead of ``print`` if provided — useful for piping the prompt
    into an agent's structured logging or a Slack/ntfy push.
    """
    init = begin(client_id=client_id, scope=scope)
    user_code = init["user_code"]
    uri = init["verification_uri"]
    expires_in = int(init.get("expires_in", 900))
    if on_user_code is not None:
        on_user_code(user_code, uri, expires_in)
    else:
        print()
        print(f"  Open: {uri}")
        print(f"  Code: {user_code}")
        print(f"  TTL : {expires_in}s")
        print()
        print("  Waiting for authorization…")
    result = poll(
        init["device_code"],
        client_id=init.get("client_id"),
        interval=int(init.get("interval", 5)),
    )
    store(result, client_id=init.get("client_id"), scope=init.get("scope"))
    return result


def store(
    token_response: Dict[str, Any],
    client_id: Optional[str] = None,
    scope: Optional[str] = None,
) -> str:
    """Persist a poll/authorize result to disk with mode 0600.

    Returns the absolute path. Caller can rotate or revoke by calling
    :func:`clear`.
    """
    payload = {
        "access_token": token_response["access_token"],
        "scope": token_response.get("scope") or scope,
        "token_type": token_response.get("token_type", "bearer"),
        "stored_at_ms": int(time.time() * 1000),
        "client_id": client_id or token_response.get("client_id"),
    }
    path = _token_path()
    # Atomic-ish write: tmp + rename, then chmod 0600 on the final
    # file. The tmp file is mode 0600 from the start so there's no
    # window where another process can grab a 0644 dropping.
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        os.fchmod(f.fileno(), stat.S_IRUSR | stat.S_IWUSR)
        json.dump(payload, f, indent=2)
    os.replace(tmp, path)
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    return path


def load() -> Optional[Dict[str, Any]]:
    """Read the stored token, or return None if no token is present."""
    path = _token_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def clear() -> bool:
    """Delete the stored token. Returns True if a token was deleted."""
    path = _token_path()
    if os.path.exists(path):
        os.remove(path)
        return True
    return False
