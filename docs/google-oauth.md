# Google OAuth setup

For agent-side access to Google APIs (Drive, Gmail, Calendar,
Sheets, etc.) via the same device-flow pattern used for GitHub.

## Why this exists

Unlike GitHub (where we borrow the published GitHub CLI client_id),
Google has no equivalent public limited-input-device client we can
use. Each project needs its own OAuth Client registered in Google
Cloud Console. ~5-10 min one-time setup; nothing required for
subsequent uses.

## One-time setup (operator on phone)

### 1. Create a Cloud project

Tap: <https://console.cloud.google.com/projectcreate>

- Project name: anything (e.g. `scandroid-bridge`).
- Tap **Create**. Wait ~20s for provisioning.

Reuse an existing project if you have one — no need to create one
per app.

### 2. Configure the OAuth consent screen

Tap: <https://console.cloud.google.com/apis/credentials/consent>

- User Type: **External** → Create
- Fill: app name + user support email + developer contact email
- Skip Scopes section (Save and Continue)
- **Test users** section: tap **+ Add Users** → enter your own
  Google email → Save and Continue
- Back to Dashboard

**Critical**: the developer email is NOT auto-added to Test Users.
You have to explicitly add yourself. Otherwise device-flow approval
fails with `Error 403: access_denied` and the message "App has not
completed the Google verification process."

### 3. Enable Drive API on the project

Tap: <https://console.cloud.google.com/apis/library/drive.googleapis.com>
(or replace with whichever API you need: gmail / sheets / calendar / etc.)

- Tap **Enable**. Wait ~10s for the green checkmark.

Drive API is default-off on fresh projects. Without enabling, the
OAuth flow succeeds but actual Drive API calls return 403 with
"Drive API has not been used in project... or it is disabled."

### 4. Create the OAuth Client

Tap: <https://console.cloud.google.com/apis/credentials>

- **+ Create Credentials** → **OAuth Client ID**
- Application type: **TVs and Limited Input devices**
  (NOT "Desktop app", NOT "Web application" — those use redirect-
  based flows incompatible with our headless agent.)
- Name: `scandroid-agent` (or anything recognizable)
- **Create**

A modal appears with **Client ID** and **Client Secret**. Both are
copy-friendly. Per Google's own docs, the Client Secret for limited-
input-device clients is *technically not secret* — share it via
chat with your agent.

## Setting on the agent

```bash
export SCANDROID_GOOGLE_CLIENT_ID="<client-id>.apps.googleusercontent.com"
export SCANDROID_GOOGLE_CLIENT_SECRET="GOCSPX-<secret>"
```

Or pass directly:

```python
from scandroid.google import authorize
authorize(client_id="...", client_secret="...")
```

## Running the device flow

```python
import scandroid.google as g
g.authorize()
```

The agent prints:

```
  Open: https://www.google.com/device
  Code: ABCD-EFGH
  TTL : 1800s
  Waiting for authorization…
```

Operator opens URL on phone, types code, taps **Continue** →
**Authorize**. May see "App not verified" warning — tap **Advanced
→ Go to scandroid (unsafe)** → **Allow**. (Test-user mode; harmless.)

Token + refresh_token land at
`~/.config/scandroid/google_oauth.json` mode 0600.

## Verifying it works

```python
from scandroid.google import userinfo
me = userinfo()
print(me)
# {'id': '...', 'email': '<your-email>', 'verified_email': True, ...}
```

## What you can do once authed

| Function | What it does |
|---|---|
| `userinfo()` | Identity proof — returns email + name |
| `list_drive_files(query=...)` | List files agent has access to (drive.file scope = files agent created or were shared with it) |
| `create_drive_file(name, content, mime_type)` | Deposit a file into operator's Drive |
| `update_drive_file(file_id, content=..., name=..., mime_type=...)` | Update existing file in place |
| `read_drive_file(file_id)` | Read raw bytes from Drive |

For Colab-specific patterns (deposit + open + run), see
[recipes/drive-deposit.md](recipes/drive-deposit.md).

## Token lifecycle

- Access token expires in ~1 hour.
- `load_fresh()` auto-refreshes within 60s of expiry using the
  refresh_token (Google issues one for device-flow clients).
- All API wrapper functions (`userinfo`, `list_drive_files`, etc.)
  call `load_fresh()` internally; you never see an expired token
  unless you reach into the file directly.
- Refresh token doesn't expire on its own. It does get revoked if
  operator removes the app from
  <https://myaccount.google.com/permissions>.

## Revoking access

Local-only:
```python
from scandroid.google import deauthorize
deauthorize()
```

Google-side (full revoke): visit
<https://myaccount.google.com/permissions> → find your OAuth
client → tap Remove access.

Both are independent. For full revocation, do both.

## Scopes

Default scopes (what `authorize()` requests):

- `https://www.googleapis.com/auth/drive.file` — per-file Drive
  access. Agent sees only files it created or that were shared
  with the agent's OAuth client.
- `https://www.googleapis.com/auth/userinfo.email` — basic identity.

Override via:
```python
authorize(scope="<space-separated-scopes>")
```

Or: `export SCANDROID_GOOGLE_SCOPES="..."`

Common additional scopes (each requires Google's app-verification
process for production use; fine in test mode):
- `https://www.googleapis.com/auth/spreadsheets` — Sheets read/write
- `https://www.googleapis.com/auth/gmail.send` — Gmail send-only
- `https://www.googleapis.com/auth/calendar` — Calendar read/write
- `https://www.googleapis.com/auth/drive` — Full Drive access (NOT
  recommended; `drive.file` is bounded + safer)

## See also

- [recipes/drive-deposit.md](recipes/drive-deposit.md) — agent-
  deposits-notebook-into-Drive pattern.
- [oauth.md](oauth.md) — the GitHub-flavor sibling of this doc.
