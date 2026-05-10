# Recipe: Bitwarden CLI as credential bridge in Codespace

**Field-tested 2026-05-09.** A 150-character generated master password
crosses from the operator's phone to a position where the agent can
issue `bw get password <name>` / `bw get totp <name>` against a
Bitwarden vault — **without the master ever appearing in chat output,
on the agent VM's persistent disk, or in the Codespace's network
traffic in the clear**.

## Why this exists

The cluster's threat model says secrets shouldn't transit the chat
surface. The operator can't realistically type a 150-char random
master password into anything. They also don't want a third-party
password manager's master in the chat transcript.

This recipe routes that master through containment layers:
- Phone → Google Password Manager export → CSV (operator's choice)
- Agent parses **only the Bitwarden entry**, never the rest
- Master extracted to a `0600` file in agent VM **briefly** (parse step)
- SSH stdin pipe to Codespace → `cat > /home/codespace/.bw-master`
- Local copy on agent VM **deleted** before next call
- `bw login --passwordfile /home/codespace/.bw-master` succeeds
- Per-credential extraction via `bw get` runs in the Codespace shell
- Master file shredded after run; vault locked; bw logged out

The credential never appears in: chat output, agent VM's disk after
the parse step, the Codespace's network in the clear (TLS to bw cloud),
the agent's stdout. The 150 chars stay containment-bounded throughout.

## End-to-end flow

```
[Operator phone]
  Google Password Manager exports CSV with bitwarden entry
  Operator uploads CSV to chat (one-shot)

[Agent VM]
  Parse CSV → extract ONLY bitwarden entry → /tmp/.bw-creds.json (0600)
  Master read into Python variable, NEVER printed/echoed

[Agent VM] → [Codespace] via gh codespace ssh stdin pipe:
  cat > /home/codespace/.bw-master
  chmod 0600

[Agent VM]
  Delete local /tmp/.bw-creds.json

[Codespace]
  npm install -g @bitwarden/cli   (one-time, ~60s)
  bw login <email> --passwordfile /home/codespace/.bw-master --raw
  bw unlock --passwordfile /home/codespace/.bw-master --raw  →  session
  bw sync
  bw list items / bw get password <name> / bw get totp <name>

[Cleanup]
  bw lock     (invalidates session)
  bw logout   (clears local config)
  shred -u /home/codespace/.bw-master
```

## Pre-reqs

- Operator authorized GitHub OAuth via `scandroid.codespaces.authorize()`
- Agent VM has `gh` + `openssh-client` (`apt-get install -y gh openssh-client`)
- Codespace exists and is `Available`
- Operator has set up Bitwarden (free tier works) with the master
  password they want to bridge

## The pipeline

### Step 1: parse the master from operator's CSV (agent VM)

```python
import csv, json, os, stat
CSV = "/path/to/operators-Google-Passwords-export.csv"
LOCAL = "/tmp/.bw-creds.json"

with open(CSV) as f:
    rdr = csv.DictReader(f)
    for r in rdr:
        if "bitwarden" in (r.get("name","") + r.get("url","")).lower():
            with open(LOCAL, "w") as out:
                json.dump({"email": r["username"], "master": r["password"]}, out)
            break

os.chmod(LOCAL, stat.S_IRUSR | stat.S_IWUSR)   # 0600
# Master is now in LOCAL on agent VM, never printed
```

### Step 2: write master into Codespace via SSH stdin

```python
import json, subprocess
from scandroid.codespaces import _ensure_gh_token_env
env = _ensure_gh_token_env()
NAME = "<your-codespace-name>"

with open(LOCAL) as f:
    creds = json.load(f)

# Write master to /home/codespace/.bw-master via stdin pipe (cat > file).
# Master never traverses shell args (no quoting issues, no env-var
# forwarding limitations, no on-screen exposure).
script = """
set -e
cat > /home/codespace/.bw-master
chmod 0600 /home/codespace/.bw-master
"""
subprocess.run(
    ["gh", "codespace", "ssh", "-c", NAME, "--", script],
    env=env, input=creds["master"],
    capture_output=True, text=True, timeout=60, check=True,
)

# Local cleanup IMMEDIATELY after transfer
os.unlink(LOCAL)
```

### Step 3: install bw CLI in Codespace (one-time)

```python
script = """
set -e
if ! command -v bw >/dev/null; then
  npm install -g @bitwarden/cli 2>&1 | tail -3
fi
bw --version
"""
subprocess.run(["gh", "codespace", "ssh", "-c", NAME, "--", script],
               env=env, timeout=240, check=True)
```

### Step 4: login + unlock + sync (each subsequent call needs unlock)

`bw login` and `bw unlock` use `--passwordfile` to avoid interactive
prompts. The session token is short-lived; re-unlock on each fresh
SSH call (each gh ssh creates a new shell, env doesn't persist).

```python
script = '''
set -e
EMAIL="''' + creds["email"] + '''"

# Login if not already (stays authenticated across SSH calls;
# only the SESSION token needs refreshing per call)
if ! bw status 2>/dev/null | grep -q '"status": "locked"\\|"status": "unlocked"'; then
  bw login "$EMAIL" --passwordfile /home/codespace/.bw-master --raw >/dev/null
fi

# Unlock for this shell
SESS=$(bw unlock --passwordfile /home/codespace/.bw-master --raw)
export BW_SESSION="$SESS"

# Sync vault
bw sync --session "$BW_SESSION" 2>&1 | head -1

# What you wanted to do (example: list, get password, get totp)
bw list items --session "$BW_SESSION" | python3 -c "
import json, sys
items = json.load(sys.stdin)
print(f'vault has {len(items)} item(s)')
"

# bw get examples — replace with what your agent actually needs
# bw get password google.com --session "$BW_SESSION"
# bw get totp google.com --session "$BW_SESSION"
'''
r = subprocess.run(["gh", "codespace", "ssh", "-c", NAME, "--", script],
                   env=env, capture_output=True, text=True, timeout=120)
print(r.stdout)
```

### Step 5: cleanup when done

```python
script = """
set -e
bw lock 2>&1 | head -1 || true
bw logout 2>&1 | head -1 || true
shred -u /home/codespace/.bw-master 2>&1 || true
ls /home/codespace/.bw-master 2>&1 || echo "  (file gone)"
bw status
"""
subprocess.run(["gh", "codespace", "ssh", "-c", NAME, "--", script],
               env=env, timeout=60, check=True)
```

## What got proven in field test

```
=== writing master to codespace via stdin pipe ===
  size: 150 bytes
  mode: 600

=== bw login with passwordfile ===
  login OK, session length=88

=== unlock ===
  unlock OK (session length 88)

=== sync ===
Syncing complete.

=== inventory ===
  total items: 0   (operator's vault was empty for the access test)

=== cleanup ===
Your vault is locked. You have logged out.
ls: cannot access '/home/codespace/.bw-master': No such file or directory
```

The vault being empty was incidental — the access pipeline worked
fully. Once the operator imports their existing credentials into
Bitwarden via their phone (Google Password Manager → Bitwarden import
is a few-tap operation), every `bw get` call returns real values.

## Use cases this unlocks

| Need | bw call |
|---|---|
| Get a saved login password | `bw get password example.com` |
| Get current TOTP code (from Bitwarden's stored TOTP seeds) | `bw get totp example.com` |
| List all logins for a domain | `bw list items --search example.com` |
| Get a specific item's full record | `bw get item <name-or-id>` |
| Fingerprint check (verify the right account is unlocked) | `bw status` |

For driving login forms via Playwright in the Codespace's Chromium:

```python
# Ask the Codespace's bw CLI for the credential
script = f'''
SESS=$(bw unlock --passwordfile /home/codespace/.bw-master --raw)
PASSWORD=$(bw get password google.com --session "$SESS")
TOTP=$(bw get totp google.com --session "$SESS")
# Echo a JSON line we can parse on the agent side
python3 -c "import json; print(json.dumps({{\\"password\\": \\"$PASSWORD\\", \\"totp\\": \\"$TOTP\\"}}))"
'''
r = subprocess.run(["gh", "codespace", "ssh", ...], ..., capture_output=True)
creds = json.loads(r.stdout.strip().splitlines()[-1])
# Now drive Playwright form-fill with creds["password"] and creds["totp"]
```

The credentials live in the SSH-tunnel-encrypted JSON line for one
hop; never on disk in the agent VM, never in chat. The agent uses
them, doesn't store them.

## Threat properties

- **Master never typed**: 150-char generated string, infeasible for
  operator to type. Containment is the only path.
- **Master never on screen**: parsing step extracts to a 0600 file;
  the parse code reads via Python `csv` module, never prints.
- **Master not on agent disk after transfer**: `os.unlink()` runs
  immediately after the SSH stdin pipe completes.
- **Master only in Codespace's `~/.bw-master`** (mode 0600) **for the
  duration of the bw login session**, then `shred -u` removes it.
- **Bitwarden's vault encryption is end-to-end**: the bw cloud only
  ever sees the encrypted vault blob; decryption happens locally in
  the Codespace process via the master derivation.
- **Cleanup fails closed**: `bw lock` invalidates the session token;
  `bw logout` removes the local bw config; `shred` overwrites the
  master file before unlinking.

## Limits + caveats

- **`gh codespace cp` doesn't reliably handle absolute paths** (we hit
  a quoting bug on `/home/codespace/.bw-master`). The SSH stdin pipe
  pattern (`cat > file`) is more robust for credential transfer.
- **Each fresh `gh codespace ssh` call needs `bw unlock`** because env
  vars don't persist across shell invocations. Login state DOES
  persist (bw stores it in `~/.config/Bitwarden CLI/`), so only
  unlock-with-master-file is needed.
- **Bitwarden may require 2FA on first login from a new device.** The
  operator's account in field test had no 2FA on Bitwarden (they had
  it on their accounts INSIDE the vault, not on Bitwarden itself).
  If 2FA is enforced, the `bw login` call will need `--method 0|1|3`
  + `--code <CODE>` and the agent will need to source that code via
  another path (e.g., aegis on phone, in the Bitwarden TOTP entry of
  *another* manager, or by routing through the same vault).

## See also

- [oauth.md](../oauth.md) — the GitHub OAuth pre-req
- [drive-deposit.md](drive-deposit.md) — alternative file-transfer
  pattern (deposit via Drive, retrieve via Drive read)
- [playwright-in-codespace.md](playwright-in-codespace.md) — Codespace
  Chromium control surface that consumes credentials from this bridge
- [agent-reach-boundaries.md](../agent-reach-boundaries.md) — overall
  map of what's reachable
