"""Agent action approval gate client for the scandroid Worker.

The agent may create, inspect, wait for, or cancel a bounded request. It never
receives the user token or TOTP secret used to resolve the request.
"""
from __future__ import annotations

import os
import time
import uuid
from collections.abc import Mapping
from typing import Any, Dict, Optional
from urllib.parse import urlparse

__all__ = ["request", "wait", "cancel", "status"]

_MIN_TTL_SECONDS = 30
_MAX_TTL_SECONDS = 3600
_MAX_ACTION_LENGTH = 128
_DEFAULT_HTTP_TIMEOUT = 15
_TERMINAL_STATUSES = {"approved", "denied", "expired", "cancelled"}


def _config(token: Optional[str], url: Optional[str]) -> tuple[str, str]:
    raw_url = (url or os.environ.get("SCANDROID_APPROVAL_URL") or "").strip()
    raw_token = (token or os.environ.get("SCANDROID_AGENT_TOKEN") or "").strip()
    if not raw_url:
        raise ValueError("Set SCANDROID_APPROVAL_URL to the approval Worker URL.")
    if not raw_token:
        raise ValueError("Set SCANDROID_AGENT_TOKEN to the Worker agent token.")

    parsed = urlparse(raw_url)
    local_host = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise ValueError("SCANDROID_APPROVAL_URL must be an absolute HTTP(S) URL.")
    if parsed.scheme != "https" and not local_host:
        raise ValueError("SCANDROID_APPROVAL_URL must use HTTPS outside local development.")
    if parsed.query or parsed.fragment:
        raise ValueError("SCANDROID_APPROVAL_URL must not include a query or fragment.")
    return raw_url.rstrip("/"), raw_token


def _requests():
    try:
        import requests
    except ImportError as error:
        raise RuntimeError(
            "scandroid.approval requires requests; install the scandroid package dependencies"
        ) from error
    return requests


def _positive_timeout(value: int | float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{name} must be a positive number")
    return float(value)


def _request_id(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("request_id must be a UUID string")
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError) as error:
        raise ValueError("request_id must be a valid UUID") from error


def _response_dict(response: Any) -> Dict[str, Any]:
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, Mapping):
        raise RuntimeError("approval Worker returned a non-object JSON response")
    return dict(payload)


def _headers(token: str, *, json_body: bool = False) -> Dict[str, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "scandroid-approval/0.1",
    }
    if json_body:
        headers["Content-Type"] = "application/json"
    return headers


def request(
    action: str,
    details: Optional[Dict[str, Any]] = None,
    *,
    ttl_seconds: int = 600,
    token: Optional[str] = None,
    url: Optional[str] = None,
    timeout: int = _DEFAULT_HTTP_TIMEOUT,
) -> Dict[str, Any]:
    """Create a bounded approval request and return its Worker record locator."""
    if not isinstance(action, str) or not action.strip():
        raise ValueError("action must be a non-empty string")
    action = action.strip()
    if len(action) > _MAX_ACTION_LENGTH:
        raise ValueError(f"action must be at most {_MAX_ACTION_LENGTH} characters")
    if details is not None and not isinstance(details, dict):
        raise TypeError("details must be a dictionary when provided")
    if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int):
        raise TypeError("ttl_seconds must be an integer")
    if not _MIN_TTL_SECONDS <= ttl_seconds <= _MAX_TTL_SECONDS:
        raise ValueError(
            f"ttl_seconds must be between {_MIN_TTL_SECONDS} and {_MAX_TTL_SECONDS}"
        )

    request_timeout = _positive_timeout(timeout, "timeout")
    worker_url, agent_token = _config(token, url)
    response = _requests().post(
        f"{worker_url}/request",
        headers=_headers(agent_token, json_body=True),
        json={"action": action, "details": details or {}, "ttl_seconds": ttl_seconds},
        timeout=request_timeout,
    )
    payload = _response_dict(response)
    payload["request_id"] = _request_id(payload.get("request_id", ""))
    if not isinstance(payload.get("expires_at"), int):
        raise RuntimeError("approval Worker response omitted integer expires_at")
    if not isinstance(payload.get("approve_url"), str):
        raise RuntimeError("approval Worker response omitted approve_url")
    return payload


def status(
    request_id: str,
    *,
    token: Optional[str] = None,
    url: Optional[str] = None,
    timeout: int = _DEFAULT_HTTP_TIMEOUT,
) -> Dict[str, Any]:
    """Read one approval request without blocking."""
    normalized_id = _request_id(request_id)
    request_timeout = _positive_timeout(timeout, "timeout")
    worker_url, agent_token = _config(token, url)
    response = _requests().get(
        f"{worker_url}/status",
        headers=_headers(agent_token),
        params={"id": normalized_id},
        timeout=request_timeout,
    )
    payload = _response_dict(response)
    if payload.get("request_id") != normalized_id:
        raise RuntimeError("approval Worker returned a mismatched request_id")
    state = payload.get("status")
    if state not in {"pending", *_TERMINAL_STATUSES}:
        raise RuntimeError(f"approval Worker returned unknown status: {state!r}")
    return payload


def wait(
    request_id: str,
    *,
    timeout: int = 600,
    poll_interval: float = 2.0,
    token: Optional[str] = None,
    url: Optional[str] = None,
) -> Dict[str, Any]:
    """Poll until a terminal state or the local polling deadline is reached."""
    normalized_id = _request_id(request_id)
    local_timeout = _positive_timeout(timeout, "timeout")
    interval = _positive_timeout(poll_interval, "poll_interval")
    deadline = time.monotonic() + local_timeout
    last: Dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = status(normalized_id, token=token, url=url)
        if last.get("status") in _TERMINAL_STATUSES:
            return last
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(interval, remaining))
    return last


def cancel(
    request_id: str,
    *,
    token: Optional[str] = None,
    url: Optional[str] = None,
    timeout: int = _DEFAULT_HTTP_TIMEOUT,
) -> Dict[str, Any]:
    """Ask the Worker to cancel a still-pending request."""
    normalized_id = _request_id(request_id)
    request_timeout = _positive_timeout(timeout, "timeout")
    worker_url, agent_token = _config(token, url)
    response = _requests().post(
        f"{worker_url}/cancel",
        headers=_headers(agent_token, json_body=True),
        json={"request_id": normalized_id},
        timeout=request_timeout,
    )
    payload = _response_dict(response)
    if payload.get("request_id") not in {None, normalized_id}:
        raise RuntimeError("approval Worker returned a mismatched request_id")
    return payload
