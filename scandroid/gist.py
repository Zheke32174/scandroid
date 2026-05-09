"""GitHub Gist helpers for the scandroid Colab bridge protocol.

Schema:
    Gist file ``colab_endpoint.json``:
    {
        "url":   "https://...trycloudflare.com",
        "model": "qwen2.5:14b",
        "ts":    "2026-05-09T15:30:00Z",
        "tunnel": "ngrok"
    }

The Colab notebook publishes/updates this gist whenever the tunnel URL changes;
agents poll it (via ``scandroid.bridge.discover``) to find the live endpoint.
This is the same schema understory's ``colab-watcher`` daemon consumes, so the
two implementations interoperate.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

DEFAULT_FILENAME = "colab_endpoint.json"
DEFAULT_DESCRIPTION = "scandroid-colab-endpoint"
__all__ = ["publish_endpoint", "fetch_endpoint", "DEFAULT_FILENAME"]


def _token(token: Optional[str]) -> str:
    t = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not t:
        raise ValueError(
            "Provide a GitHub token (gist scope) or set GITHUB_TOKEN/GH_TOKEN."
        )
    return t


def _requests():
    try:
        import requests  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            "scandroid.gist requires 'requests'. Install with: pip install requests"
        ) from e
    return __import__("requests")


def publish_endpoint(
    *,
    url: str,
    model: str,
    tunnel: str = "?",
    gist_id: Optional[str] = None,
    description: str = DEFAULT_DESCRIPTION,
    public: bool = False,
    token: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    """Publish or update the colab endpoint gist. Returns the gist id.

    Pass ``gist_id`` to update in place; omit it to create a new gist (the
    returned id should be saved for subsequent updates and for agents to
    discover).
    """
    requests = _requests()
    body: Dict[str, Any] = {
        "url": url,
        "model": model,
        "tunnel": tunnel,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if extra:
        body.update(extra)

    payload: Dict[str, Any] = {
        "files": {DEFAULT_FILENAME: {"content": json.dumps(body, indent=2)}},
    }
    headers = {
        "Authorization": f"token {_token(token)}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if gist_id:
        r = requests.patch(
            f"https://api.github.com/gists/{gist_id}",
            headers=headers,
            json=payload,
            timeout=15,
        )
    else:
        payload["description"] = description
        payload["public"] = public
        r = requests.post(
            "https://api.github.com/gists",
            headers=headers,
            json=payload,
            timeout=15,
        )
    r.raise_for_status()
    return r.json()["id"]


def fetch_endpoint(gist_id: str, token: Optional[str] = None) -> Dict[str, Any]:
    """Fetch and parse ``colab_endpoint.json`` from the given gist."""
    requests = _requests()
    r = requests.get(
        f"https://api.github.com/gists/{gist_id}",
        headers={
            "Authorization": f"token {_token(token)}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=15,
    )
    r.raise_for_status()
    files = r.json().get("files", {})
    if DEFAULT_FILENAME not in files:
        raise KeyError(f"{DEFAULT_FILENAME} missing from gist {gist_id}")
    return json.loads(files[DEFAULT_FILENAME]["content"])
