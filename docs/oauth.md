# OAuth device flow

Used to authenticate an agent VM to GitHub for Codespaces work
without ever pasting a PAT or running `gh auth login` interactively.

## The flow

```python
from scandroid.codespaces import authorize
authorize()
```

The agent prints:

```
  Open: https://github.com/login/device
  Code: ABCD-1234
  TTL : 900s

  Waiting for authorization…
```

You open the URL on your phone or laptop, type the 6-digit code,
hit Approve. The agent receives a long-lived access token and
stores it at `~/.config/scandroid/github_oauth.json` (mode 0600).
Subsequent calls to any function in `scandroid.codespaces` pick
up the stored token automatically.

## Auth resolution chain

`scandroid.codespaces` resolves credentials in this order:

1. **Explicit `token=` parameter** on each call — useful for tests
   or for callers that already have a token in hand.
2. **`GITHUB_TOKEN` or `GH_TOKEN`** env var — the PAT-style path,
   honored for compatibility with existing scripts.
3. **Stored OAuth token** from a prior `authorize()` run — the
   agent-friendly default.

PAT-style auth still works for cases where a long-lived service
token is more convenient, but new agent deployments should prefer
device-flow OAuth.

## Custom OAuth app

By default, `authorize()` uses the GitHub CLI's published
client_id (`178c6fc778ccc68e1d6a`). The auth page shows "GitHub
CLI" as the requesting app — recognizable to most users since
they've seen it during `gh auth login`.

If you want a distinct app identity (e.g., for production
deployments), register your own OAuth App at
<https://github.com/settings/developers> with **Device Flow**
checked, then either pass `client_id=` to `authorize()` or set:

```bash
export SCANDROID_GITHUB_CLIENT_ID=<your-client-id>
```

## Routing the prompt

By default the URL + code go to stdout. For headless setups, pass
an `on_user_code` callback to route the prompt elsewhere:

```python
from scandroid.codespaces import authorize

def push_to_phone(code, uri, expires_in):
    # ntfy / Slack / agent 2FA gate — your choice.
    requests.post("https://ntfy.sh/my-topic",
                  data=f"Open {uri} and type {code} (expires in {expires_in}s)")

authorize(on_user_code=push_to_phone)
```

## Revoking access

Local-only revoke:

```python
from scandroid.codespaces import deauthorize
deauthorize()  # deletes ~/.config/scandroid/github_oauth.json
```

GitHub-side revoke (so the token stops working anywhere): visit
<https://github.com/settings/applications> and revoke the OAuth
app grant.

Both are independent. For full revocation, do both.

## What's stored on disk

```json
{
  "access_token": "ghu_...",
  "scope": "codespace repo",
  "token_type": "bearer",
  "stored_at_ms": 1700000000000,
  "client_id": "178c6fc778ccc68e1d6a"
}
```

Mode 0600 — the agent's UID is the only entity that legitimately
needs read access. The cluster's posture treats this file the same
as `~/.ssh/id_*` and `~/.config/op/` — agent home is a security
boundary.

## Token refresh

GitHub OAuth Apps support refresh tokens when configured for
"Expire user authorization tokens" in the app settings. The CLI's
public client_id (the default) doesn't have this enabled — its
tokens are long-lived but unrefreshable. To use refresh, register
your own app + set `SCANDROID_GITHUB_CLIENT_ID`. (Refresh-token
storage + auto-refresh isn't yet in `scandroid.oauth`; tracked as
an open follow-up.)

## See also

- [Codespaces Session ctxmgr](codespaces.md) — uses the stored
  OAuth token to drive Codespaces lifecycle.
- [Agent action 2FA](agent-2fa-gate.md) — the same phone-approval
  pattern, applied to in-cluster actions.
