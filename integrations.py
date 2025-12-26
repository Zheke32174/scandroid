"""Helper utilities to connect Colab, Codex (OpenAI), and GitHub services."""
from __future__ import annotations

from typing import Optional, Dict, Any
import os
import requests
from openai import OpenAI

__all__ = [
    "mount_colab_drive",
    "get_github_user",
    "run_codex_completion",
    "set_runtime_secrets",
    "runtime_ready",
]


def mount_colab_drive(force_remount: bool = False) -> str:
    """Mount Google Drive when running inside Google Colab.

    Parameters
    ----------
    force_remount: bool
        Whether to force a remount if the drive is already mounted.

    Returns
    -------
    str
        The mount point used by Colab.
    """
    from google.colab import drive  # type: ignore

    mount_point = "/content/drive"
    drive.mount(mount_point, force_remount=force_remount)
    return mount_point


def get_github_user(token: Optional[str] = None) -> Dict[str, Any]:
    """Return the authenticated GitHub user payload using the provided token.

    Parameters
    ----------
    token: Optional[str]
        A GitHub Personal Access Token. If omitted, the function falls back to
        the ``GITHUB_TOKEN`` or ``GH_TOKEN`` environment variables.

    Raises
    ------
    ValueError
        If no token is provided and no environment variable is available.
    requests.HTTPError
        If the GitHub API rejects the request.
    """
    github_token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not github_token:
        raise ValueError("Provide a GitHub token or set GITHUB_TOKEN/GH_TOKEN.")

    response = requests.get(
        "https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def run_codex_completion(prompt: str, model: str = "gpt-4o-mini", api_key: Optional[str] = None, **kwargs: Any) -> str:
    """Execute a Codex-style completion using the OpenAI Chat Completions API.

    Parameters
    ----------
    prompt: str
        The instruction or code generation prompt to send to the model.
    model: str
        The model identifier to use. Defaults to ``gpt-4o-mini``.
    api_key: Optional[str]
        The OpenAI API key. If omitted, the ``OPENAI_API_KEY`` environment
        variable is used.
    **kwargs: Any
        Additional keyword arguments forwarded to ``client.chat.completions.create``.

    Returns
    -------
    str
        The text content returned by the model.
    """
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("Provide an OpenAI API key or set OPENAI_API_KEY.")

    client = OpenAI(api_key=key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        **kwargs,
    )
    return response.choices[0].message.content or ""


def set_runtime_secrets(
    *,
    openai_api_key: Optional[str] = None,
    github_token: Optional[str] = None,
) -> Dict[str, bool]:
    """Inject secrets into environment variables for ephemeral runtimes (e.g., Colab).

    This helper avoids writing credentials to disk and keeps everything in-memory.

    Parameters
    ----------
    openai_api_key: Optional[str]
        The OpenAI API key to set as ``OPENAI_API_KEY``.
    github_token: Optional[str]
        The GitHub token to set as ``GITHUB_TOKEN``.

    Returns
    -------
    Dict[str, bool]
        Flags indicating which secrets are present after the update.
    """
    if openai_api_key:
        os.environ["OPENAI_API_KEY"] = openai_api_key
    if github_token:
        os.environ["GITHUB_TOKEN"] = github_token

    return {
        "openai_api_key": bool(os.environ.get("OPENAI_API_KEY")),
        "github_token": bool(os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")),
    }


def runtime_ready(require_openai: bool = True, require_github: bool = True) -> bool:
    """Check if required environment variables are available before connecting.

    Parameters
    ----------
    require_openai: bool
        Whether an OpenAI API key is required.
    require_github: bool
        Whether a GitHub token is required.

    Returns
    -------
    bool
        True if the requested secrets are present in the environment.
    """
    openai_ok = bool(os.environ.get("OPENAI_API_KEY")) or not require_openai
    github_ok = bool(os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")) or not require_github
    return openai_ok and github_ok
