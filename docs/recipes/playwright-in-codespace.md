# Recipe: Playwright in a Codespace, driven from a remote agent

**Field-tested 2026-05-09.** Proves an agent on one VM can install +
drive a real browser inside a GitHub Codespace via shell, with no
operator interaction beyond the one-time OAuth grant.

## What this gets you

- A Chromium browser running inside a Codespace you authorized via
  GitHub OAuth.
- Driven from your agent VM via `gh codespace ssh`-piped Python.
- Useful for: scraping public sites, parsing dynamic web pages,
  testing web apps, screenshotting, anything browser-shaped where
  the target *doesn't require authentication*.

## What this does NOT get you (yet)

- Authenticated services driven via the operator's session cookies.
  That requires either operator login via VNC port-forward (next
  recipe) or a service-account / API path. Calling out the limit
  explicitly because the next-step temptation is real.

## Pre-reqs

- Operator has approved a `scandroid.codespaces.authorize()` device-
  flow grant (one phone tap; see [oauth.md](../oauth.md)).
- Agent VM has `gh` CLI + `openssh-client` installed
  (`apt-get install -y gh openssh-client`).
- A Codespace exists and is `Available`. Start one via
  `scandroid.codespaces.Session(...)` or directly with
  `start_codespace(name)` + `get_codespace(name)` until state is
  `Available`.

## The full one-shot

From the agent VM, this is a single shell-out:

```python
from scandroid.codespaces import _ensure_gh_token_env
import subprocess

env = _ensure_gh_token_env()
NAME = "<your-codespace-name>"

script = """
set -e
echo '=== install playwright ==='
pip install -q playwright
echo '=== install chromium ==='
playwright install chromium 2>&1 | tail -5
playwright install-deps chromium 2>&1 | tail -3 || true
echo '=== drive headless chromium ==='
python3 << 'PY'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://example.com", wait_until="domcontentloaded")
    print(f"TITLE: {page.title()}")
    print(f"H1:    {page.locator('h1').first.inner_text()}")
    browser.close()
PY
echo '=== done ==='
"""
r = subprocess.run(
    ["gh", "codespace", "ssh", "-c", NAME, "--", script],
    env=env, capture_output=True, text=True, timeout=600,
)
print(r.stdout)
```

Expected output:

```
=== install playwright ===
=== install chromium ===
Chrome Headless Shell <version> downloaded
=== drive headless chromium ===
TITLE: Example Domain
H1:    Example Domain
=== done ===
```

Total time: ~2 min on first run (Chromium install dominates), ~5 s
on subsequent runs (cached).

## Things to know

- `playwright install chromium` downloads ~112 MB of Chromium runtime
  to `~/.cache/ms-playwright/`. Persists across SSH sessions but
  not across Codespace deletions.
- `playwright install-deps chromium` runs apt to fetch system libs
  (libcups, fontconfig, etc.). May fail on ultra-locked-down images;
  Codespaces' default `mcr.microsoft.com/devcontainers/universal`
  image works fine.
- Headless mode is the default and lightest. For headed mode (next
  recipe) you need a virtual display; Xvfb works.

## Extending: authenticated targets

For sites that need login (Colab, Sheets, GitHub UI, etc.), the
agent can't fill the password field — operator has to. Pattern:

1. Install Xvfb + x11vnc + websockify + noVNC in the Codespace.
2. Launch Chromium **headed** with `--remote-debugging-port=9222`,
   on the virtual display.
3. `gh codespace ports forward 6080:6080 -c <name>` and set
   visibility to public for the noVNC port.
4. Send operator the public URL: `https://<codespace>-6080.app.github.dev/vnc.html`.
5. Operator opens, sees the Chromium UI, signs in to whatever site,
   walks away.
6. From agent VM: connect Playwright to the running Chromium via
   `playwright.chromium.connect_over_cdp("http://<codespace-cdp-url>:9222")`
   and drive normally — Chromium's profile retains the auth cookies
   from the operator's login.

This is documented as a separate recipe rather than inline because it
crosses the "operator does a UI thing" boundary and the failure modes
(VNC latency, Google anti-bot, port visibility) are different.

ToS posture: see BLUEPRINT §9f. Authenticated-target browser
automation is a gray-zone path; do it with eyes open and prefer
documented APIs (Drive deposit, Codespace shell, etc.) where
available. The recipe is here for cases where no documented path
exists.
