# Agent action 2FA gate

For high-leverage agent actions that need a hard human gate
before they happen — committing money, sending external messages,
deleting shared resources, anything where the cost of a wrong
agent action is high.

## Shape

```
+---------+         +---------+         +-----------+
|  Agent  | ---1--> |  Worker | ---2--> |  User's   |
|  (code) |  POST   |  (CF)   |  push   |  phone    |
+---------+         +---------+         +-----------+
     ^                  ^   ^                |
     |                  |   |                | 3. resolve
     |   5. status      |   +-------4--------+    + TOTP
     +-- approved? -----+                        (aegis)
                                                  |
                                       (back to Worker)
```

1. Agent posts an approval request: `{action, scope, context, ttl}`.
2. Worker stores it in KV and pushes a notification to the user's
   phone.
3. User opens the approval UI on their phone, reads the action +
   scope + context, types a TOTP code from the cluster's local
   TOTP authenticator (aegis).
4. Resolution lands back in the Worker's KV.
5. Agent polls (or waits via long-poll) until the request is
   `approved` or `denied`, then proceeds.

## Identity-honest, scope-honored

Per the cluster's `AI-PARTICIPANTS-TOS-RULE.md`: the agent
identifies itself as an AI in the request, names the exact scope
of what it wants to do (no "approve a category" patterns), and
respects the user's resolution. The Worker enforces TTL — an
unanswered request expires; the agent must re-request, not assume.

## API

```python
from scandroid.approval import request_approval, wait_for_approval

approval_id = request_approval(
    action="git push",
    scope="zheke32174/scandroid:claude/feature-x",
    context="Adds 200 LoC for Wave B-2 wiring; tests pass.",
    ttl_seconds=300,
)
result = wait_for_approval(approval_id, timeout=300)
if result["status"] == "approved":
    # safe to proceed
else:
    # status == "denied" or "expired" — back off
```

## Worker

The Cloudflare Worker source is in [`scandroid/worker/`][worker].
Deploy via `wrangler deploy`; configuration goes in
`wrangler.toml`. KV namespace + push-notification provider
credentials are repo Secrets.

[worker]: https://github.com/Zheke32174/scandroid/tree/main/worker

## TOTP source

The cluster's TOTP codes come from **aegis**, the on-device
authenticator app in the (private) understory suite. aegis
generates RFC 6238 codes locally and never displays them on
screen — the user copies the current code from clipboard with an
auto-clear at the period boundary. This is what makes the gate
"hard": the TOTP secret never leaves the user's device, and the
code is never visible to anything but the user.

## Why not a simple shared secret

A static shared secret authorizes anyone who has it indefinitely.
A TOTP code authorizes one approval at one moment, by someone who
is actively present and aware of what they're approving. The
combined scheme — push notification (proof of intent) + TOTP
(proof of possession) — gates each action individually.

## See also

- [OAuth device flow](oauth.md) — same phone-approval pattern,
  applied to GitHub authentication.
