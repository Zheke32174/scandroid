"""High-level Colab offload bridge.

Flow:
    1. User opens ``scandroid.ipynb`` in Colab on a GPU runtime and runs all
       cells. The notebook starts Ollama, opens a tunnel, and publishes the
       endpoint to a private GitHub Gist.
    2. Agents call :func:`discover` to read the live endpoint from the Gist,
       then issue requests to ``{url}/api/generate`` (Ollama-compatible API)
       directly.
    3. When the tunnel URL changes (e.g. ngrok session renewal), the notebook
       re-publishes the gist; agents pick up the new URL on the next call.

The agent never drives Colab itself — only the human does. The agent reads a
Gist it has been authorized to read, and connects to a tunnel published by a
running notebook. ToS-clean by construction.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from .gist import fetch_endpoint

__all__ = ["discover", "generate"]


def discover(
    gist_id: Optional[str] = None,
    *,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """Return the live colab endpoint metadata for the given Gist.

    If ``gist_id`` is None, falls back to the ``SCANDROID_GIST_ID`` env var.
    """
    gist_id = gist_id or os.environ.get("SCANDROID_GIST_ID")
    if not gist_id:
        raise ValueError(
            "Provide gist_id or set SCANDROID_GIST_ID to the gist holding "
            "colab_endpoint.json"
        )
    return fetch_endpoint(gist_id, token=token)


def generate(
    prompt: str,
    *,
    gist_id: Optional[str] = None,
    model: Optional[str] = None,
    token: Optional[str] = None,
    stream: bool = False,
    timeout: int = 600,
    **kwargs: Any,
) -> str:
    """Send ``prompt`` to the live colab Ollama endpoint and return the text.

    Discovers the endpoint via :func:`discover`. Defaults to the model the
    notebook is currently serving; pass ``model=`` to override.

    For streaming, set ``stream=True`` and parse the line-delimited JSON
    response yourself; this helper returns the raw response body in that case.
    """
    try:
        import requests
    except ImportError as e:
        raise RuntimeError(
            "scandroid.bridge.generate requires 'requests'."
        ) from e

    ep = discover(gist_id, token=token)
    body = {
        "model": model or ep["model"],
        "prompt": prompt,
        "stream": stream,
        **kwargs,
    }
    r = requests.post(
        f"{ep['url'].rstrip('/')}/api/generate",
        json=body,
        timeout=timeout,
    )
    r.raise_for_status()
    if stream:
        return r.text
    return r.json().get("response", "")
