"""Google APIs — agent-friendly wrappers.

Mirror of `scandroid.codespaces` but for Google. Resolves credentials
through the same fallback chain shape (explicit token > stored OAuth
token), uses load_fresh() so callers never see an expired token.

Currently exposes a small surface — Drive listing as the equivalent
of `list_codespaces` (proves the OAuth chain works end-to-end). Add
Gmail / Sheets / Calendar wrappers in follow-up commits as use cases
emerge; the auth chain works for any Google API once the relevant
scope is granted.

Re-exports `authorize` / `deauthorize` for symmetry with
`scandroid.codespaces.authorize` — same shape, different provider.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from . import google_oauth as _oauth

API_BASE = "https://www.googleapis.com"

__all__ = [
    "authorize",
    "deauthorize",
    "list_drive_files",
    "userinfo",
    "_resolve_token",
    "_ensure_headers",
]


def _resolve_token(token: Optional[str]) -> Optional[str]:
    """Walk the auth chain: explicit token > stored OAuth (load_fresh
    so we don't return an expired one).

    Doesn't raise on miss — callers shape error messages with their
    own context.
    """
    if token:
        return token
    stored = _oauth.load_fresh()
    if stored and stored.get("access_token"):
        return stored["access_token"]
    return None


def _ensure_headers(token: Optional[str]) -> Dict[str, str]:
    tok = _resolve_token(token)
    if not tok:
        raise ValueError(
            "No Google credentials available. Either:\n"
            "  - Pass token= explicitly.\n"
            "  - Run scandroid.google.authorize() once to grant access\n"
            "    via OAuth device flow (no PAT needed).\n"
            "Requires SCANDROID_GOOGLE_CLIENT_ID + SCANDROID_GOOGLE_CLIENT_SECRET\n"
            "to be set first — register an OAuth client at\n"
            "https://console.cloud.google.com/apis/credentials\n"
            "as type 'TVs and Limited Input devices'."
        )
    return {
        "Authorization": f"Bearer {tok}",
        "Accept": "application/json",
    }


def _requests():
    try:
        import requests  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            "scandroid.google requires 'requests'. pip install requests."
        ) from e
    return __import__("requests")


def authorize(
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    scope: Optional[str] = None,
    on_user_code: Optional[Any] = None,
) -> Dict[str, Any]:
    """Walk the Google OAuth device flow + persist the result.

    Same UX as :func:`scandroid.codespaces.authorize`:
    prints URL + 6-digit code; operator approves on phone; agent
    receives long-lived access_token + refresh_token, stores them
    at ``~/.config/scandroid/google_oauth.json`` (mode 0600).

    Subsequent calls to functions in this module (and to anything
    that calls :func:`scandroid.google_oauth.load_fresh`) auto-pick
    up the stored token and auto-refresh when expired.

    Pre-req: SCANDROID_GOOGLE_CLIENT_ID + SCANDROID_GOOGLE_CLIENT_SECRET
    must be set (no public Google client_id we can borrow). See
    :mod:`scandroid.google_oauth` for the OAuth Client setup steps.
    """
    return _oauth.authorize(
        client_id=client_id,
        client_secret=client_secret,
        scope=scope,
        on_user_code=on_user_code,
    )


def deauthorize() -> bool:
    """Delete the stored Google token. Returns True if one was deleted.

    Google-side revocation is a separate step: visit
    https://myaccount.google.com/permissions and revoke the OAuth
    app's access. This call only removes the local on-disk token.
    """
    return _oauth.clear()


def userinfo(token: Optional[str] = None) -> Dict[str, Any]:
    """Identity proof: returns the authenticated user's basic info.

    Equivalent of "GET /user" on GitHub — minimal call that proves
    the token is valid and reveals which Google account it's for.
    Requires the userinfo.email or userinfo.profile scope (default
    scope set includes both).
    """
    r = _requests().get(
        f"{API_BASE}/oauth2/v2/userinfo",
        headers=_ensure_headers(token),
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def list_drive_files(
    page_size: int = 10,
    query: Optional[str] = None,
    token: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List files visible to the authenticated user via Drive API.

    With the default ``drive.file`` scope (granted by
    :func:`authorize`), this returns only files the *agent* created
    or had explicitly shared with it via the same OAuth client.
    NOT the user's full Drive — that needs the broader ``drive``
    scope which requires Google's app-verification process.

    The default scope's behavior is correct for an agent that wants
    Drive as a private workspace ("create files, list mine, read/
    write mine") without seeing any of the operator's existing
    personal files. Cleanly bounded.

    Use ``query`` to filter — see Drive API docs for syntax. Common:
        - "mimeType='text/plain'"
        - "modifiedTime > '2026-01-01T00:00:00'"
        - "name contains 'snapshot'"
    """
    params: Dict[str, Any] = {
        "pageSize": page_size,
        "fields": "files(id,name,mimeType,modifiedTime,size)",
    }
    if query:
        params["q"] = query
    r = _requests().get(
        f"{API_BASE}/drive/v3/files",
        headers=_ensure_headers(token),
        params=params,
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("files", [])
