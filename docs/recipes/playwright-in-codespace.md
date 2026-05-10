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

For sites that need login (Google, ChatGPT, Sheets, GitHub UI, etc.),
the agent can't fill the password field — operator has to. **Field-tested
2026-05-09**: this whole stack works.

### Architecture (proven)

1. Install Xvfb + x11vnc + websockify + noVNC in the Codespace:
   ```bash
   sudo apt-get install -y xvfb x11vnc websockify novnc
   ```
2. Launch Xvfb (virtual display :99):
   ```bash
   nohup Xvfb :99 -screen 0 1280x800x24 -ac > /tmp/xvfb.log 2>&1 < /dev/null &
   ```
3. Launch Chromium **headed** with `--remote-debugging-port=9222` on
   the virtual display:
   ```bash
   DISPLAY=:99 nohup ~/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome \
     --no-sandbox --disable-dev-shm-usage --disable-gpu \
     --user-data-dir=$HOME/.scandroid-chrome-vnc-profile \
     --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0 \
     --window-size=1280,800 \
     about:blank > /tmp/chrome.log 2>&1 < /dev/null &
   ```
4. Start x11vnc against display :99 (localhost-only, the public bridge
   is the noVNC layer):
   ```bash
   nohup x11vnc -display :99 -nopw -listen localhost -forever -shared \
     > /tmp/x11vnc.log 2>&1 < /dev/null &
   ```
5. Start noVNC + websockify on port 6080:
   ```bash
   nohup websockify --web /usr/share/novnc 6080 localhost:5900 \
     > /tmp/novnc.log 2>&1 < /dev/null &
   ```
6. From agent VM, forward 6080 publicly + 9222 privately:
   ```python
   subprocess.Popen(["gh", "codespace", "ports", "forward", "6080:6080", "-c", NAME], ...)
   subprocess.run(["gh", "codespace", "ports", "visibility", "6080:public", "-c", NAME], ...)
   subprocess.Popen(["gh", "codespace", "ports", "forward", "9222:9222", "-c", NAME], ...)
   ```
7. Send operator the public URL:
   `https://<codespace-name>-6080.app.github.dev/vnc.html`
8. Operator opens, taps Connect, sees Chromium UI, signs in to whatever
   site, walks away.
9. From agent VM: connect Playwright to the running Chromium via CDP
   over the private port-forward:
   ```python
   browser = p.chromium.connect_over_cdp("http://localhost:9222")
   ctx = browser.contexts[0]
   page = ctx.pages[0]  # whatever tab the operator left open
   # Drive normally — Chromium's profile retains the auth cookies from
   # the operator's login.
   ```

### What works through this stack (measured)

- **Cloudflare Turnstile passes silently** for headed Chromium on
  Codespace IP — verified against `chatgpt.com` (anonymous tier).
  Headless Chromium gets challenged; headed does not.
- **Anonymous ChatGPT** — full prompt + response cycle without operator
  interaction. See [chatgpt-anonymous-via-codespace.md](chatgpt-anonymous-via-codespace.md).
- **Operator one-time login flows via VNC** — phone tap on noVNC URL,
  log in to Google/Microsoft/whatever in the embedded Chromium.

### What doesn't work through this stack (measured)

- **Surrogate Google login** — Google's modern auth is passkey-first
  for accounts with passkeys enabled. Even with operator passing
  passkey via VNC, Google's risk-scoring escalates to "account
  recovery" mode after multi-method cycling, which then refuses TOTP
  as a primary factor. This is by design at the account level, not
  fixable at the agent level.
- **High-rate access to authenticated services** — Cloudflare
  re-challenges sessions that exhibit non-human patterns. Bursty
  usage is OK; sustained automation gets flagged.

ToS posture: see BLUEPRINT §9f. Browser automation against
authenticated services is gray-zone; we crossed it explicitly for the
boundary-mapping experiment, with the operator handling the actual
auth steps. Production uses should prefer documented APIs.

See [agent-reach-boundaries.md](../agent-reach-boundaries.md) for the
full reach matrix.
