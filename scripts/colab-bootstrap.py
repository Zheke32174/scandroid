#!/usr/bin/env python3
"""Colab bootstrap — one-line pass-to-agent.

The operator pastes this single line into ANY new Colab code cell:

    !curl -fsSL https://raw.githubusercontent.com/Zheke32174/scandroid/main/scripts/colab-bootstrap.py | python3 -

Then runs the cell. The script:

    1. Installs Ollama, starts the daemon detached (survives this script).
    2. Pulls a small Llama (configurable via $SCANDROID_MODEL).
    3. Opens a cloudflare quick-tunnel exposing the Ollama API,
       detached so it survives this script.
    4. Installs scandroid (for the OAuth helper).
    5. Runs the GitHub OAuth device flow — prints URL + 6-digit code.
       Operator taps URL on phone, types code, hits Authorize.
    6. Publishes the live endpoint to a private GitHub Gist.
    7. Prints the GIST_ID for the operator to send to the agent.

After the script exits, Ollama + cloudflared keep running in the
Colab runtime (until the runtime itself is torn down or recycled).
The agent uses the GIST_ID to discover the tunnel URL via
``scandroid.discover()`` and send inference requests via
``scandroid.generate()``.

Pre-req: a Colab runtime that's already connected (any tier — free
CPU runtime works for small models; T4 GPU faster for ≥3B params).

Why one-liner instead of a paste-the-whole-cell flow:
    Pasting a 100-line code block into a Colab cell on a phone is
    real friction. A 100-character one-liner is one tap. The
    operator surface should be as small as possible — that's the
    threat-model invariant the cluster keeps coming back to.

Configuration (env vars, all optional):
    SCANDROID_MODEL          : Ollama model tag. Default: llama3.2:1b
    SCANDROID_GIST_ID        : Reuse an existing gist (updates in place
                               instead of creating new). Default: create.
    SCANDROID_GITHUB_CLIENT_ID : Override the OAuth client_id.
                                Default: GitHub CLI's published id.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.request

MODEL = os.environ.get("SCANDROID_MODEL", "llama3.2:1b")
EXISTING_GIST_ID = os.environ.get("SCANDROID_GIST_ID", "")


def _section(n: int, total: int, msg: str) -> None:
    """Single-line phase marker; flushes immediately so phone-side cell
    output reflects progress in real time rather than buffering."""
    print(f"[{n}/{total}] {msg}", flush=True)


def _shell(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)


def _kill_prior() -> None:
    """Re-runnable: stop any prior Ollama / cloudflared from a previous
    bootstrap attempt. ``|| true`` so the call is harmless if there's
    nothing to kill."""
    subprocess.run("pkill -f 'ollama serve' || true", shell=True)
    subprocess.run("pkill -f 'cloudflared tunnel' || true", shell=True)
    time.sleep(2)


def _install_ollama() -> None:
    """Install Ollama on Colab/headless containers.

    Approach: run the official install.sh, ignore its exit code,
    verify the binary landed.

    Why: install.sh does two things — (1) download + place the
    binary at /usr/local/bin/ollama (works everywhere), (2)
    register a systemd service (fails on Colab, sysvinit-style
    containers, anything without systemd). The script's exit code
    reflects step (2)'s failure, but step (1) already succeeded
    by then. Treating the script as "did it leave a working binary?"
    rather than "did it exit 0?" is the right shape.

    Earlier attempts in this file used a hand-built tar.gz download
    from ollama.com — that URL doesn't actually exist; the tarball
    lives on GitHub releases. Using install.sh and checking for
    the binary is more robust than guessing URLs that move.
    """
    if os.path.exists("/usr/local/bin/ollama"):
        return  # idempotent — already installed
    # check=False because install.sh exits non-zero on Colab even
    # when the binary install part succeeds.
    _shell("curl -fsSL https://ollama.com/install.sh | sh", check=False)
    if not os.path.exists("/usr/local/bin/ollama"):
        raise RuntimeError(
            "Ollama install.sh ran but the binary wasn't placed at "
            "/usr/local/bin/ollama. Try a manual download from "
            "https://github.com/ollama/ollama/releases/latest"
        )


def _start_daemon_detached() -> None:
    """Start ``ollama serve`` as a detached process that survives this
    script's exit. The Colab cell's Python process ends after the
    script returns; without nohup-style detachment, Ollama would die
    with it and the published tunnel would 502."""
    subprocess.run(
        "OLLAMA_HOST=0.0.0.0:11434 nohup ollama serve "
        "> /tmp/ollama.log 2>&1 < /dev/null &",
        shell=True,
        check=True,
    )
    # Wait for the daemon to accept connections.
    for _ in range(30):
        try:
            urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2)
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("Ollama daemon didn't come up in 30s. Check /tmp/ollama.log")


def _pull_model() -> None:
    # Model files are cached under ~/.ollama/models — re-running this
    # script with the same MODEL is fast.
    subprocess.run(["ollama", "pull", MODEL], check=True)


def _ensure_cloudflared() -> None:
    if os.path.exists("/usr/local/bin/cloudflared"):
        return
    _shell(
        "wget -q https://github.com/cloudflare/cloudflared/releases/latest/"
        "download/cloudflared-linux-amd64 -O /usr/local/bin/cloudflared && "
        "chmod +x /usr/local/bin/cloudflared"
    )


def _start_tunnel_detached() -> str:
    """Open a cloudflare quick-tunnel; detach so it survives this script.
    Returns the public URL once cloudflared has published one to its log."""
    _shell("rm -f /tmp/cf.log")
    subprocess.run(
        "nohup cloudflared tunnel --url http://localhost:11434 "
        "> /tmp/cf.log 2>&1 < /dev/null &",
        shell=True,
        check=True,
    )
    # cloudflared prints the public URL to its log within a few seconds.
    pattern = re.compile(r"https://[\w-]+\.trycloudflare\.com")
    for _ in range(60):
        try:
            with open("/tmp/cf.log") as f:
                m = pattern.search(f.read())
                if m:
                    return m.group(0)
        except FileNotFoundError:
            pass
        time.sleep(1)
    raise RuntimeError(
        "cloudflared didn't publish a URL in 60s. Check /tmp/cf.log"
    )


def _install_scandroid() -> None:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q",
         "git+https://github.com/Zheke32174/scandroid.git"],
        check=True,
    )


def _oauth_authorize() -> str:
    """Run the GitHub OAuth device flow. Prints URL + code on first call,
    blocks until the operator approves on phone. Returns the access token."""
    from scandroid import oauth as _oauth
    print()
    print("=" * 60)
    print("OAUTH APPROVAL — tap URL on phone, enter the code:")
    print("=" * 60)
    result = _oauth.authorize(scope="gist repo")
    return result["access_token"]


def _publish_gist(token: str, tunnel_url: str) -> str:
    """Create or update the colab_endpoint.json gist. Returns the gist ID.

    If SCANDROID_GIST_ID is set, updates that gist in place — agents
    polling the same gist transparently pick up the new tunnel URL.
    Otherwise creates a new private gist."""
    body = json.dumps({
        "url": tunnel_url,
        "model": MODEL,
        "tunnel": "cloudflare",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }, indent=2)
    payload = {
        "files": {"colab_endpoint.json": {"content": body}},
    }
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    }
    if EXISTING_GIST_ID:
        url = f"https://api.github.com/gists/{EXISTING_GIST_ID}"
        # urllib doesn't support PATCH directly; use the override header
        # GitHub honors. Cleaner than reaching for requests when stdlib works.
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(),
            headers={**headers, "X-HTTP-Method-Override": "PATCH"},
            method="POST",
        )
    else:
        payload["description"] = "scandroid-colab-endpoint"
        payload["public"] = False
        req = urllib.request.Request(
            "https://api.github.com/gists",
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST",
        )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["id"]


def main() -> int:
    _section(1, 6, f"Killing any prior Ollama/cloudflared (re-run safe)…")
    _kill_prior()

    _section(2, 6, "Installing Ollama…")
    _install_ollama()

    _section(3, 6, "Starting Ollama daemon (detached)…")
    _start_daemon_detached()

    _section(4, 6, f"Pulling {MODEL}… (cached on re-run)")
    _pull_model()

    _section(5, 6, "Opening cloudflare quick-tunnel (detached)…")
    _ensure_cloudflared()
    tunnel_url = _start_tunnel_detached()

    _section(6, 6, "Installing scandroid + running OAuth device flow…")
    _install_scandroid()
    token = _oauth_authorize()

    print()
    print("Publishing endpoint to private gist…", flush=True)
    gist_id = _publish_gist(token, tunnel_url)

    print()
    print("=" * 60)
    print(f"  ENDPOINT : {tunnel_url}")
    print(f"  MODEL    : {MODEL}")
    print(f"  GIST_ID  : {gist_id}")
    print("=" * 60)
    print()
    print("SEND THIS GIST_ID TO YOUR AGENT:")
    print(f"    {gist_id}")
    print()
    print("Ollama + cloudflared continue running in this Colab runtime.")
    print("Re-run this same one-liner anytime to refresh the tunnel URL")
    print("(set SCANDROID_GIST_ID=... in the cell first to update in-place).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
