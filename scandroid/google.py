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
    "create_drive_file",
    "update_drive_file",
    "read_drive_file",
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


def create_drive_file(
    name: str,
    content: bytes,
    mime_type: str = "application/octet-stream",
    parents: Optional[List[str]] = None,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a file in the operator's Drive via multipart upload.

    Returns the Drive resource for the new file ({id, name, mimeType,
    webViewLink, ...}). Use this to deposit notebooks, data, reports,
    or any other artifact the operator should be able to open in
    their Drive UI.

    With the default `drive.file` scope, this is the *only* way the
    agent can put files into the operator's Drive — and the operator
    only sees them as files-from-this-app, kept neatly bounded.

    Notebooks: pass mime_type="application/vnd.google.colaboratory"
    so Colab recognizes them natively. Drive renders the
    "Open with Colab" affordance automatically and a direct
    https://colab.research.google.com/drive/<id> URL works.

    parents: optional list of Drive folder IDs. Default is operator's
    Drive root. Within drive.file scope, parents must themselves
    be folders the agent has access to (created via this same
    OAuth client).
    """
    metadata: Dict[str, Any] = {"name": name, "mimeType": mime_type}
    if parents:
        metadata["parents"] = parents

    boundary = f"scandroid-multipart-{__import__('os').urandom(8).hex()}"
    body = _multipart_body(boundary, metadata, mime_type, content)
    r = _requests().post(
        f"{API_BASE}/upload/drive/v3/files"
        "?uploadType=multipart&fields=id,name,mimeType,webViewLink,modifiedTime",
        headers={
            **_ensure_headers(token),
            "Content-Type": f"multipart/related; boundary={boundary}",
        },
        data=body,
        timeout=120,
    )
    r.raise_for_status()
    return r.json()


def update_drive_file(
    file_id: str,
    content: Optional[bytes] = None,
    name: Optional[str] = None,
    mime_type: Optional[str] = None,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """Update an existing Drive file's content, name, and/or mimeType.

    Either ``content`` or ``name``/``mime_type`` (or both) must be
    provided. Multipart PATCH lets us update content + metadata in one
    call without losing the Colab-friendly mimeType (a media-only
    PATCH would force the Content-Type to be the new content type and
    Drive would silently change the file's mimeType — caught this in
    practice during the in-field test, hence the multipart default).
    """
    if content is None and name is None and mime_type is None:
        raise ValueError("must update at least one of content/name/mime_type")

    metadata: Dict[str, Any] = {}
    if name is not None:
        metadata["name"] = name
    if mime_type is not None:
        metadata["mimeType"] = mime_type

    headers = _ensure_headers(token)
    if content is not None:
        # Multipart PATCH so we can preserve mimeType when caller cares.
        boundary = f"scandroid-update-{__import__('os').urandom(8).hex()}"
        body = _multipart_body(
            boundary, metadata,
            mime_type or "application/octet-stream", content,
        )
        r = _requests().patch(
            f"{API_BASE}/upload/drive/v3/files/{file_id}"
            "?uploadType=multipart&fields=id,name,mimeType,webViewLink,modifiedTime",
            headers={
                **headers,
                "Content-Type": f"multipart/related; boundary={boundary}",
            },
            data=body,
            timeout=120,
        )
    else:
        # Metadata-only patch — no content body.
        r = _requests().patch(
            f"{API_BASE}/drive/v3/files/{file_id}"
            "?fields=id,name,mimeType,webViewLink,modifiedTime",
            headers={**headers, "Content-Type": "application/json"},
            json=metadata,
            timeout=30,
        )
    r.raise_for_status()
    return r.json()


def read_drive_file(file_id: str, token: Optional[str] = None) -> bytes:
    """Read the raw bytes of a Drive file the agent has access to.

    Symmetric counterpart of :func:`create_drive_file`. Useful for
    poll-the-Drive-for-an-output patterns where the operator's Colab
    cell writes a status file and the agent waits to see it.
    """
    r = _requests().get(
        f"{API_BASE}/drive/v3/files/{file_id}",
        headers=_ensure_headers(token),
        params={"alt": "media"},
        timeout=60,
    )
    r.raise_for_status()
    return r.content


def _multipart_body(
    boundary: str, metadata: Dict[str, Any],
    content_mime: str, content: bytes,
) -> bytes:
    """Build a Drive API multipart/related body: metadata part +
    media part. Drive accepts this format on both POST (create) and
    PATCH (update). Centralizes the encoding so create + update can't
    drift apart in subtle ways."""
    import json as _json
    parts = (
        f"--{boundary}\r\n"
        "Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{_json.dumps(metadata)}\r\n"
        f"--{boundary}\r\n"
        f"Content-Type: {content_mime}\r\n\r\n"
    ).encode("utf-8")
    return parts + content + f"\r\n--{boundary}--".encode("utf-8")


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
