"""Google OAuth — Device Flow for headless agents.

Mirror of `scandroid.oauth` (GitHub) but for Google's OAuth 2.0
device authorization grant. Same shape: agent runs `begin()`,
prints URL + user_code, operator approves on phone, agent runs
`poll()` to receive the access token (and a refresh_token, since
Google always returns one for device flow).

Reference:
    https://developers.google.com/identity/protocols/oauth2/limited-input-device

OAuth Client setup (one-time, on the operator's phone):
    1. Open https://console.cloud.google.com/apis/credentials.
    2. Create or select a project.
    3. "Create Credentials" → "OAuth Client ID".
    4. Application type: "TVs and Limited Input devices".
    5. Name it (e.g. "scandroid agent VM"). Copy the Client ID and
       Client Secret.
    6. Set on the agent VM:
           export SCANDROID_GOOGLE_CLIENT_ID="<id>"
           export SCANDROID_GOOGLE_CLIENT_SECRET="<secret>"

Note that Google's "client secret" for limited-input devices is
not actually secret in the traditional sense — Google docs
explicitly say so. It still needs to be present on every token-
endpoint call. We treat it the same way: env var + on-disk
storage, not committed.

Token storage:
    ~/.config/scandroid/google_oauth.json with mode 0600. Schema:
        {
            "access_token":  "<token>",
            "refresh_token": "<token>",
            "scope":         "...",
            "token_type":    "Bearer",
            "expires_at_ms": 1700000000000,  # absolute, not relative
            "stored_at_ms":  1700000000000,
            "client_id":     "<the OAuth client_id>"
        }
    `expires_at_ms` is computed at store time from the response's
    relative `expires_in` so callers can check freshness without
    knowing when the token was stored.

Refresh:
    Google access tokens expire (typically 1h). When expired, use
    refresh_token to get a new access_token via the same token
    endpoint. `load_fresh()` does this transparently — call it
    instead of `load()` if you want the caller to never see an
    expired token.

Default scopes:
    https://www.googleapis.com/auth/drive.file (per-file Drive
    access; doesn't require app verification) +
    https://www.googleapis.com/auth/userinfo.email (basic identity).

    Override via $SCANDROID_GOOGLE_SCOPES or the `scope=` param.
    Sensitive scopes (full Drive, Gmail content, etc.) require
    Google's app-verification process for production use.
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
    "load_fresh",
    "clear",
    "refresh",
    "DEFAULT_SCOPES",
]

DEFAULT_SCOPES = (
    "https://www.googleapis.com/auth/drive.file "
    "https://www.googleapis.com/auth/userinfo.email"
)

DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"
TOKEN_URL = "https://oauth2.googleapis.com/token"

# Per-flow temp file template — keyed by user_code so concurrent
# device flows can't clobber each other (lesson from the GitHub flow
# where a second begin() overwrote the first's device_code on disk).
_DEVICE_FLOW_TMP_TEMPLATE = "/tmp/scandroid_devflow_google_{user_code}.json"


def _config_dir() -> str:
    """Same XDG-aware resolution as scandroid.oauth — single config dir
    holds tokens for both providers as separate files."""
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    d = os.path.join(base, "scandroid")
    os.makedirs(d, mode=0o700, exist_ok=True)
    return d


def _token_path() -> str:
    return os.path.join(_config_dir(), "google_oauth.json")


def _requests():
    try:
        import requests  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            "scandroid.google_oauth requires 'requests'. pip install requests."
        ) from e
    return __import__("requests")


def _resolve_client_id(client_id: Optional[str]) -> str:
    cid = client_id or os.environ.get("SCANDROID_GOOGLE_CLIENT_ID")
    if not cid:
        raise ValueError(
            "No Google OAuth client_id available. Either:\n"
            "  - Pass client_id= explicitly.\n"
            "  - Set SCANDROID_GOOGLE_CLIENT_ID in env.\n"
            "Register one at https://console.cloud.google.com/apis/credentials\n"
            "as 'OAuth Client ID' type 'TVs and Limited Input devices'."
        )
    return cid


def _resolve_client_secret(client_secret: Optional[str]) -> str:
    cs = client_secret or os.environ.get("SCANDROID_GOOGLE_CLIENT_SECRET")
    if not cs:
        raise ValueError(
            "No Google OAuth client_secret available. Either:\n"
            "  - Pass client_secret= explicitly.\n"
            "  - Set SCANDROID_GOOGLE_CLIENT_SECRET in env.\n"
            "Get it from the same OAuth Client at console.cloud.google.com.\n"
            "(Google's 'secret' for limited-input devices is technically\n"
            "non-secret per Google docs; still required by the API.)"
        )
    return cs


def begin(
    client_id: Optional[str] = None,
    scope: Optional[str] = None,
    timeout: int = 15,
) -> Dict[str, Any]:
    """Step 1 of Google's device flow.

    Posts to Google's device-code endpoint. Returns ``{device_code,
    user_code, verification_url, expires_in, interval}``.

    Note Google uses ``verification_url`` (not ``_uri`` like GitHub).
    We normalize to ``verification_uri`` in the returned dict so
    callers can use a consistent key across providers.

    Also persists the device_code to a per-user-code temp file so a
    follow-up :func:`poll` can find it without holding state in
    memory across processes.
    """
    cid = _resolve_client_id(client_id)
    sc = scope or os.environ.get("SCANDROID_GOOGLE_SCOPES") or DEFAULT_SCOPES
    rq = _requests()
    r = rq.post(
        DEVICE_CODE_URL,
        data={"client_id": cid, "scope": sc},
        timeout=timeout,
    )
    r.raise_for_status()
    body = r.json()
    out = {
        "device_code": body["device_code"],
        "user_code": body["user_code"],
        "verification_uri": body.get("verification_url") or body.get("verification_uri"),
        "expires_in": int(body.get("expires_in", 1800)),
        "interval": int(body.get("interval", 5)),
        "client_id": cid,
        "scope": sc,
    }
    # Persist for the matching poll() call. Per-user_code keying so
    # concurrent flows can't overwrite each other.
    path = _DEVICE_FLOW_TMP_TEMPLATE.format(user_code=out["user_code"])
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        os.fchmod(f.fileno(), stat.S_IRUSR | stat.S_IWUSR)
        json.dump(out, f)
    os.replace(tmp, path)
    return out


def poll(
    device_code: str,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    interval: int = 5,
    deadline: Optional[float] = None,
    timeout: int = 15,
) -> Dict[str, Any]:
    """Step 2 of Google's device flow. Blocks until the user
    authorizes, declines, or the device-code expires.

    Returns the full Google token response (including ``refresh_token``,
    which Google always issues for device flow).

    Raises :class:`RuntimeError` on ``access_denied`` /
    ``expired_token`` / unknown failures with the Google-returned
    description.
    """
    cid = _resolve_client_id(client_id)
    cs = _resolve_client_secret(client_secret)
    rq = _requests()
    deadline_v = deadline if deadline is not None else (time.monotonic() + 1800)
    sleep = max(1, interval)
    while time.monotonic() < deadline_v:
        r = rq.post(
            TOKEN_URL,
            data={
                "client_id": cid,
                "client_secret": cs,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
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
            sleep += 5
            time.sleep(sleep)
            continue
        if err in (
            "expired_token", "access_denied", "invalid_grant",
            "unsupported_grant_type", "invalid_client",
        ):
            raise RuntimeError(
                f"Google device flow failed: {err} "
                f"({body.get('error_description', '')})"
            )
        if err:
            raise RuntimeError(
                f"Google device flow failed: {err} "
                f"({body.get('error_description', '')})"
            )
        time.sleep(sleep)
    raise RuntimeError("Google device flow polling timed out before user authorized.")


def authorize(
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    scope: Optional[str] = None,
    on_user_code: Optional[Any] = None,
) -> Dict[str, Any]:
    """One-shot convenience: begin + poll + store.

    Mirror of `scandroid.oauth.authorize()` for Google. Same UX:
    prints (or hands to ``on_user_code``) the URL + 6-digit code,
    then polls until the user authorizes. On success stores the
    token via :func:`store` and returns the response dict.
    """
    init = begin(client_id=client_id, scope=scope)
    user_code = init["user_code"]
    uri = init["verification_uri"]
    expires_in = int(init.get("expires_in", 1800))
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
        client_secret=client_secret,
        interval=int(init.get("interval", 5)),
    )
    store(result, client_id=init.get("client_id"), scope=init.get("scope"))
    # Best-effort cleanup of the per-flow temp file.
    try:
        os.remove(_DEVICE_FLOW_TMP_TEMPLATE.format(user_code=user_code))
    except OSError:
        pass
    return result


def store(
    token_response: Dict[str, Any],
    client_id: Optional[str] = None,
    scope: Optional[str] = None,
) -> str:
    """Persist a poll/authorize result with mode 0600. Computes
    ``expires_at_ms`` from the response's relative ``expires_in``
    so :func:`load_fresh` can check expiry without re-reading the
    storage time."""
    now_ms = int(time.time() * 1000)
    expires_in_s = int(token_response.get("expires_in", 3600))
    payload = {
        "access_token": token_response["access_token"],
        "refresh_token": token_response.get("refresh_token"),
        "scope": token_response.get("scope") or scope,
        "token_type": token_response.get("token_type", "Bearer"),
        "expires_at_ms": now_ms + expires_in_s * 1000,
        "stored_at_ms": now_ms,
        "client_id": client_id or token_response.get("client_id"),
    }
    path = _token_path()
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        os.fchmod(f.fileno(), stat.S_IRUSR | stat.S_IWUSR)
        json.dump(payload, f, indent=2)
    os.replace(tmp, path)
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    return path


def load() -> Optional[Dict[str, Any]]:
    """Read the stored token without checking freshness. Caller is
    responsible for handling expiry — use :func:`load_fresh` for
    auto-refresh."""
    path = _token_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def refresh(
    refresh_token: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    timeout: int = 15,
) -> Dict[str, Any]:
    """Exchange a refresh_token for a fresh access_token. Updates
    storage in-place. Returns the new (access_token, expires_in,
    ...) dict.

    If ``refresh_token`` isn't provided, reads it from the stored
    token. Useful for "make sure the token I'm about to use is
    fresh" check-and-refresh patterns.
    """
    cid = _resolve_client_id(client_id)
    cs = _resolve_client_secret(client_secret)
    rt = refresh_token
    if not rt:
        existing = load()
        if not existing or not existing.get("refresh_token"):
            raise ValueError(
                "No refresh_token available. Re-authorize via "
                "scandroid.google_oauth.authorize()."
            )
        rt = existing["refresh_token"]
    rq = _requests()
    r = rq.post(
        TOKEN_URL,
        data={
            "client_id": cid,
            "client_secret": cs,
            "refresh_token": rt,
            "grant_type": "refresh_token",
        },
        timeout=timeout,
    )
    r.raise_for_status()
    body = r.json()
    # Google's refresh response usually doesn't include refresh_token
    # again — preserve the existing one when storing.
    existing = load() or {}
    if not body.get("refresh_token") and existing.get("refresh_token"):
        body["refresh_token"] = existing["refresh_token"]
    if not body.get("scope") and existing.get("scope"):
        body["scope"] = existing["scope"]
    store(body, client_id=cid)
    return body


def load_fresh(
    grace_seconds: int = 60,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Load the stored token; refresh first if it expires within
    ``grace_seconds``. Returns None if no token is stored.

    Use this in API-call paths that want a "good for at least the
    next minute" token without thinking about refresh themselves.
    """
    existing = load()
    if not existing:
        return None
    expires_at_ms = existing.get("expires_at_ms", 0)
    if expires_at_ms - int(time.time() * 1000) > grace_seconds * 1000:
        return existing
    if not existing.get("refresh_token"):
        # Token is expired (or expiring) and we have no way to refresh.
        # Return as-is; caller can decide whether to use or re-auth.
        return existing
    return refresh(
        refresh_token=existing["refresh_token"],
        client_id=client_id,
        client_secret=client_secret,
    )


def clear() -> bool:
    """Delete the stored Google token. Returns True if a token was deleted."""
    path = _token_path()
    if os.path.exists(path):
        os.remove(path)
        return True
    return False
