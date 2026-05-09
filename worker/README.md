# scandroid-approval (Cloudflare Worker)

Agent action 2FA gate. Backs `scandroid.approval` (Python helpers in
this repo) with a tiny Worker + KV namespace + ntfy push notification.

## Deploy

```bash
cd worker

# 1. Install wrangler if you haven't.
npm install -g wrangler

# 2. Log in.
wrangler login

# 3. Create the KV namespace and paste the returned id into wrangler.toml.
wrangler kv:namespace create APPROVALS

# 4. Set secrets.
wrangler secret put AGENT_TOKEN          # any high-entropy random string
wrangler secret put USER_TOKEN            # any high-entropy random string
wrangler secret put TOTP_SECRET_BASE32    # base32; same value you'll add to aegis
wrangler secret put NTFY_TOPIC            # your ntfy.sh topic, e.g. scandroid-approvals-<random>
wrangler secret put NTFY_AUTH             # optional; empty for public ntfy topic

# 5. Deploy.
wrangler deploy
```

You'll get a URL like `https://scandroid-approval.<account>.workers.dev`.
Set that as `SCANDROID_APPROVAL_URL` on every Claude VM that should be
able to request approvals.

## Generate a TOTP secret

```bash
# 20 random bytes → base32
python3 -c '
import secrets, base64
b = secrets.token_bytes(20)
print(base64.b32encode(b).decode().rstrip("="))
'
```

Add it to aegis on your phone: tap "Add entry" → Issuer = "scandroid",
Account = "agent-approval", paste the base32 secret. Aegis will start
generating the 6-digit codes.

Set the same secret as `TOTP_SECRET_BASE32` on the Worker.

## Test the round trip

```python
# On a Claude VM with the worker URL + AGENT_TOKEN exported:
from scandroid.approval import request, wait, cancel

req = request(
    action="post_test_gist",
    details={"title": "ping", "size_bytes": 42},
    ttl_seconds=300,
)
print(req)  # {request_id, expires_at, approve_url}

# You'll get a push on your phone. Tap → /ui page → enter user_token
# + the current 6-digit TOTP from aegis → Approve.

result = wait(req["request_id"], timeout=120)
print(result)  # status: "approved" | "denied" | "expired"
```

## Threat model

See `worker/src/index.ts` header for the full breakdown. Summary:

- Three distinct secrets: AGENT_TOKEN (write requests only), USER_TOKEN
  (resolve), TOTP_SECRET_BASE32 (resolve, second factor).
- Compromised agent → can spam requests; cannot self-approve.
- Compromised push channel → can cause spurious notifications;
  cannot approve without USER_TOKEN + TOTP.
- Compromised TOTP alone → 30s window to use, still needs USER_TOKEN.
- Audit trail in KV with TTL; record self-expires past `expires_at`.

Aligned with [`understory/AI-PARTICIPANTS-TOS-RULE.md`](https://github.com/Zheke32174/understory/blob/main/AI-PARTICIPANTS-TOS-RULE.md):
identity-honest credentials, scope-honored, no impersonation.
