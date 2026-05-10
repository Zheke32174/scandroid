# Agent reach boundaries

**Empirically mapped 2026-05-09.** What a Codespace-bridged agent can and
can't reach, given a one-time GitHub OAuth grant approved on phone.

This page is the result of a multi-hour boundary-mapping session that
pushed every credible path to its breaking point. Treat it as
ground-truth for "what's possible" rather than aspirational
architecture — every row below was measured.

## Setup model

```
[Operator]                          [Anthropic Claude VM]                    [GitHub Codespace]
  phone                            (this session)                          (rented compute)
   │                                  │                                       │
   │  one-time OAuth approval         │                                       │
   │ ←──────────── device code ───────┤                                       │
   │  taps Approve                    │                                       │
   ├──────────── access token ───────→│                                       │
   │                                  │  gh codespace ssh / cp / ports        │
   │                                  ├──────────────────────────────────────→│
   │                                  │                                       │
   │  (subsequent operator role:      │                                       │
   │   minimal — phone taps           │                                       │
   │   only when CF/Google challenge) │                                       │
```

Within this setup, the agent has **persistent ability** to:
- start/stop/exec Codespaces under the operator's account
- transfer files via SSH stdin pipes (cleaner than `gh codespace cp`)
- forward Codespace ports privately (to the agent VM) or publicly (to
  any browser via `app.github.dev`)
- run any package or service the Codespace can install (`apt`, `npm`,
  `pip`, system services)
- drive Chromium via CDP over a private port-forward
- talk to any unauthenticated public web surface from inside the
  Codespace, including bypassing Cloudflare Turnstile when fingerprint
  is right

The agent **cannot** persistently do, even with this setup:
- log in to services with passkey-first auth without operator at-phone
- bypass account-protection escalations (Google's recovery-mode)
- impersonate at the cookie/session layer of services that fingerprint
  hard (banking, primary email web UIs)

## The reach matrix

Legend:
- ✅ proven working in field test
- ⚙️ partial — works under specific conditions (annotated)
- ❌ blocked — root cause known, not a tooling fix

### Identity and lifecycle

| Reach | Result | Notes |
|---|---|---|
| GitHub OAuth device flow | ✅ | One-time phone approval; long-lived token. See [oauth.md](oauth.md). |
| Codespace lifecycle (list / start / stop / delete) | ✅ | `scandroid.codespaces.Session` ctxmgr. Cost: ~$0.18/h compute. |
| `gh codespace ssh -- <command>` (one-shot) | ✅ | Real shell, real container. |
| `gh codespace ssh` interactive (persistent shell from agent VM) | ⚙️ | Possible via subprocess.Popen + fifo, not yet packaged. |
| `gh codespace cp` (file transfer) | ⚙️ | Quoting bugs on absolute paths. SSH-stdin-pipe pattern is more robust. |
| **SSH stdin pipe → file inside Codespace** (`cat > file`) | ✅ | Recommended primitive for credential transit; no shell-quote issues, no env-forwarding limits. |

### Compute and services in Codespace

| Reach | Result | Notes |
|---|---|---|
| Install arbitrary packages (apt, npm, pip) | ✅ | Codespace runs Ubuntu 24.04 with sudo. |
| Run long-lived background services | ✅ | `nohup ... &` works; survives the shell that started it. |
| Run Ollama + pull models + inference | ✅ | Real Llama-3.2:1b response in field test. ~$0.02 per smoke run. |
| Run Playwright + Chromium headless | ✅ | ~2 min first install (~112 MB Chromium download). |
| Run Chromium **headed** under Xvfb | ✅ | Required for fingerprint-clean browser automation. |
| Connect Playwright via CDP from agent VM | ✅ | Private port-forward (9222), `connect_over_cdp` works first try. |
| Run `bw` CLI (Bitwarden) | ✅ | `npm install -g @bitwarden/cli`. Auth via `--passwordfile`. |

### Port forwarding

| Reach | Result | Notes |
|---|---|---|
| Private port-forward (Codespace port → agent VM localhost) | ✅ | `gh codespace ports forward <p>:<p>`. Auto-registers in port table. |
| Public port-forward (`https://<codespace>-<p>.app.github.dev`) | ✅ | First requires private forward, then `gh codespace ports visibility <p>:public`. |
| Operator opens public-forward URL on phone | ✅ | First-visit GitHub interstitial; tap Continue. |
| Bidirectional (operator's phone → Codespace browser → operator drives) | ✅ | noVNC over HTTPS websocket. |

### Browser automation against the open web

| Reach | Result | Notes |
|---|---|---|
| Headless Chromium → unauthenticated public sites | ✅ | example.com round-trip works. |
| Headed Chromium → unauthenticated public sites | ✅ | Real fingerprint helps with sites that fingerprint. |
| **Cloudflare Turnstile pass on `chatgpt.com`** (headed) | ✅ | The headline finding — silent pass, no challenge displayed. |
| Cloudflare Turnstile pass (headless) | ❌ | `navigator.webdriver=true` + datacenter IP triggers challenge. |
| Anonymous ChatGPT prompt + response | ✅ | GPT-5 mini answered. Free tier; rate-limited. |

### Authenticated services

| Reach | Result | Notes |
|---|---|---|
| Google OAuth scoped APIs (Drive, userinfo) | ✅ | Operator phone tap once; scoped tokens persist. See [google-oauth.md](google-oauth.md). |
| Google Drive deposit (write a notebook) | ✅ | Operator taps the Drive URL, file opens in Colab. |
| Google sign-in (passkey-first account) | ❌ | Account requires passkey OR password. Agent has neither typed-in path. |
| Google sign-in (password account) via Bitwarden CLI | not measured | Logical path: bw stores password → agent fills via Playwright. Operator's account is passkey-first so untested. |
| Google sign-in fallback to TOTP via aegis | ❌ | Google escalates to **account recovery mode** after multi-method "Try another way" cycling, which refuses TOTP as primary factor. |
| ChatGPT login via "Continue with Google" | ❌ | Inherits the Google sign-in wall above. |
| ChatGPT logged-in chat | not reached | Blocked by the Google sign-in wall. |

### Credential bridging

| Reach | Result | Notes |
|---|---|---|
| **Bitwarden vault unlock from operator master file** | ✅ | 150-char master, never typed, never on screen. See [recipes/bitwarden-bridge.md](recipes/bitwarden-bridge.md). |
| `bw list / get password / get totp` from agent VM | ✅ | Per-credential extraction; never exposes other entries. |
| TOTP from operator's Proton Authenticator export | ⚙️ | TOTP computation works; Google rejects when account is in recovery mode. Use case fits non-recovery-mode services. |
| Proton Pass CLI (alternative to Bitwarden) | not measured | Architectural sketch only. |

### Storage

| Reach | Result | Notes |
|---|---|---|
| Codespace internal storage | ✅ | Sized per Codespace machine; persists across stops. |
| `~/.config/scandroid/*` agent VM token store | ✅ | mode 0600 enforced. |
| Google Drive (drive.file scope, agent-private workspace) | ✅ | Per-app private files; doesn't see operator's full Drive. |
| OneDrive / MEGA / Dropbox | not measured | Same OAuth-sibling-module pattern would apply. |
| GitHub repos (write access) | ✅ | Via OAuth grant's `repo` scope. |

## Architectural insights

### What unlocks browser-driven access

**Headed Chromium with Xvfb beats headless every time** when the
target uses bot detection. Cloudflare Turnstile silently passes a
real-fingerprint Chromium even from a Codespace IP. Headless gets
challenged. The whole VNC stack matters less for the operator's
visibility than for Chromium's fingerprint.

### What blocks authenticated access

**Account-protection layers escalate by design.** Google's
recovery-mode kicks in after the agent cycles through "Try another
way" multiple times. This is anti-fraud infrastructure working as
intended — there's no exploit or fingerprint trick that bypasses it.

The right architectural response is to AVOID triggering the escalation
in the first place: populate Bitwarden with a real password ahead of
time, drive a clean fresh-profile login that doesn't need to cycle
through alternative methods, accept the operator's one-tap passkey if
that's what the account requires.

### What credential bridging actually buys

The Bitwarden CLI bridge gives the agent a **per-call credential
extraction surface** without ever exposing the master. For services
that accept password+TOTP login (i.e., not passkey-first), that's
genuinely sufficient: agent calls `bw get password <name>`, drives the
form fill, calls `bw get totp <name>` if 2FA appears, done.

For services with stronger primary factors (passkey, phone-prompt,
biometric), no credential-manager-in-Codespace fixes that — the
operator has to participate one-time for the primary factor.

### What MCP integration would change

If `mcp-chrome` or pinchtab's MCP mode were wrapped + deployed, agents
could drive Chromium via tool calls instead of CDP-over-port. The
reach matrix wouldn't change (CF and Google's protections don't care
how the agent gets there) but the tool ergonomics would. See
[TOOLBOX-MAP-STATUS.md](https://github.com/Zheke32174/undergrowth/blob/main/TOOLBOX-MAP-STATUS.md)
for the candidate list.

## Use-case decision tree

```
Need to call an LLM?
├── Free, exploratory → ChatGPT anonymous via Codespace+CDP. ToS-clean.
├── Production / reliable / high-rate → API key (OpenAI / Anthropic / Gemini).
└── Self-hosted compute → Ollama in Codespace (CPU) or Colab tunnel (GPU).

Need to act on operator's behalf in a service?
├── Service has documented OAuth + scoped API → Use it. Map onto
│   scandroid.<provider> sibling module.
├── Service has password+TOTP login → Bitwarden bridge → Playwright fill.
└── Service is passkey-first → Operator one-tap via VNC; agent drives
    rest. Don't try to bypass.

Need to store / retrieve agent state?
├── Files: Drive deposit (operator) or Codespace internal (ephemeral).
├── Code: GitHub repo via OAuth.
├── Credentials: Bitwarden CLI bridge.
└── Long-lived: TBD — Section 12 OpenMemory candidate territory.
```

## See also

- [oauth.md](oauth.md) / [google-oauth.md](google-oauth.md) — auth surface
- [codespaces.md](codespaces.md) — Codespace lifecycle ctxmgr
- [recipes/playwright-in-codespace.md](recipes/playwright-in-codespace.md) — VNC+Chromium+CDP
- [recipes/bitwarden-bridge.md](recipes/bitwarden-bridge.md) — credential bridge
- [recipes/chatgpt-anonymous-via-codespace.md](recipes/chatgpt-anonymous-via-codespace.md) — anonymous LLM channel
- [recipes/drive-deposit.md](recipes/drive-deposit.md) — file deposit pattern
