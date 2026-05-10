"""Agent action 2FA gate — agent-side client for scandroid-approval Worker.

Pairs with the Cloudflare Worker at ``worker/src/index.ts`` and the
TOTP entry the user adds to aegis (or any RFC 6238 TOTP authenticator).

Typical use::

    from scandroid.approval import request, wait

    req = request(
        action="post_gist",
        details={"description": "snapshot of nightly run"},
        ttl_seconds=300,
    )
    # User gets a push on their phone, opens the URL, types
    # USER_TOKEN + the current TOTP code from aegis, taps Approve.
    result = wait(req["request_id"], timeout=120)
    if result["status"] == "approved":
        # ... do the action ...
        pass
    else:
        # denied / expired — abort and report.
        raise PermissionError(f"approval not granted: {result['status']}")

Configuration via env vars on the agent VM:

- ``SCANDROID_APPROVAL_URL`` — Worker URL (e.g.
  ``https://scandroid-approval.<account>.workers.dev``).
- ``SCANDROID_AGENT_TOKEN`` — bearer token the Worker expects on
  ``/request``, ``/status``, ``/cancel``.

The agent never sees the ``USER_TOKEN`` or the TOTP secret — those are
required only to *resolve* a request, which happens via the Worker's
``/ui`` page on the user's phone.

Aligned with the cluster's ``AI-PARTICIPANTS-TOS-RULE.md``:
identity-honest credentials, scope-honored capabilities, no
impersonation. The agent's token is write-only at the gate; the
user's token + TOTP are resolve-only. Compromise of either alone
cannot approve an action.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

__all__ = ["request", "wait", "cancel", "status"]


def _config(token: Optional[str], url: Optional[str]) -> tuple[str, str]:
    u = url or os.environ.get("SCANDROID_APPROVAL_URL")
    t = token or os.environ.get("SCANDROID_AGENT_TOKEN")
    if not u:
        raise ValueError(
            "Set SCANDROID_APPROVAL_URL to the Worker URL "
            "(e.g. https://scandroid-approval.<account>.workers.dev)."
        )
    if not t:
        raise ValueError(
            "Set SCANDROID_AGENT_TOKEN to the AGENT_TOKEN "
            "configured on the Worker."
        )
    return u.rstrip("/"), t


def _requests():
    try:
        import requests  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            "scandroid.approval requires 'requests'. Install with: pip install requests"
        ) from e
    return __import__("requests")


def request(
    action: str,
    details: Optional[Dict[str, Any]] = None,
    *,
    ttl_seconds: int = 600,
    token: Optional[str] = None,
    url: Optional[str] = None,
    timeout: int = 15,
) -> Dict[str, Any]:
    """Post a new approval request.

    Returns ``{request_id, expires_at, approve_url}``. The user gets a
    push notification with ``approve_url``; the agent should
    immediately call :func:`wait` with the returned id.
    """
    u, t = _config(token, url)
    rq = _requests()
    body = {"action": action, "details": details or {}, "ttl_seconds": ttl_seconds}
    r = rq.post(
        f"{u}/request",
        headers={"Authorization": f"Bearer {t}", "Content-Type": "application/json"},
        json=body,
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()


def status(
    request_id: str,
    *,
    token: Optional[str] = None,
    url: Optional[str] = None,
    timeout: int = 15,
) -> Dict[str, Any]:
    """One-shot status check; doesn't block.

    Returns the full record: ``{request_id, status, action, details,
    created_at, expires_at, resolved_at?}``. ``status`` is one of
    ``pending`` / ``approved`` / ``denied`` / ``expired``.
    """
    u, t = _config(token, url)
    rq = _requests()
    r = rq.get(
        f"{u}/status",
        headers={"Authorization": f"Bearer {t}"},
        params={"id": request_id},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()


def wait(
    request_id: str,
    *,
    timeout: int = 600,
    poll_interval: float = 2.0,
    token: Optional[str] = None,
    url: Optional[str] = None,
) -> Dict[str, Any]:
    """Poll until the request is resolved or [timeout] seconds elapse.

    Returns the same record shape as :func:`status` with a terminal
    status. If the user never resolves and the request TTL passes,
    the Worker self-marks the record ``expired``.

    ``timeout`` here is the agent-side polling cap; the request's
    own TTL is set at creation time (``ttl_seconds`` on
    :func:`request`). If your action TTL is longer than ``timeout``,
    you'll get a record with ``status="pending"`` when this returns —
    treat that as "no decision yet, your call to retry or abort."
    """
    deadline = time.monotonic() + timeout
    last: Dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = status(request_id, token=token, url=url)
        if last.get("status") in {"approved", "denied", "expired"}:
            return last
        time.sleep(poll_interval)
    return last


def cancel(
    request_id: str,
    *,
    token: Optional[str] = None,
    url: Optional[str] = None,
    timeout: int = 15,
) -> Dict[str, Any]:
    """Withdraw a pending request. Useful when an agent's plan
    changes after submitting a request but before the user resolves.
    """
    u, t = _config(token, url)
    rq = _requests()
    r = rq.post(
        f"{u}/cancel",
        headers={"Authorization": f"Bearer {t}", "Content-Type": "application/json"},
        json={"request_id": request_id},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()
