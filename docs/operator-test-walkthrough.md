# Operator test walkthrough

How to actually verify the bridge works end-to-end. Some of this can
run from any agent VM with `pip install scandroid`; the rest needs
your phone or your GitHub account.

The agent-side smoke test ([`scripts/smoke-test.py`][smoke]) covers
everything that doesn't need operator interaction. Run it first; it
tells you if the install + import + GitHub-reachability are healthy.

[smoke]: https://github.com/Zheke32174/scandroid/blob/main/scripts/smoke-test.py

```bash
pip install git+https://github.com/Zheke32174/scandroid.git
python3 -m scandroid.scripts.smoke_test  # if you've installed
# or, from a clone:
python3 scripts/smoke-test.py
```

Expected output ends with `12/12 passed` + "Agent-side surface
healthy." If anything in there fails, the operator-side tests below
will likely fail too — fix the install first.

The walkthroughs below cover the operator-required parts.

!!! note "If you can't run a shell locally"

    Some operators run under a threat model where they don't execute
    shells on any machine they control — the whole point is to keep
    no local execution surface that a remote actor could tamper with
    or swipe from. Under that constraint:

    - Treat every `python3 ...` command in this doc as "your remote
      agent VM runs this." That agent (Claude Code, OpenHands, a
      Codespace you've sshed into, etc.) is the shell.
    - Your role reduces to: tap Approve on the OAuth prompt your
      phone receives, optionally watch the result on phone, optionally
      flip the Pages source toggle once.
    - Tokens land in the agent VM's filesystem, not yours. They die
      when the agent VM dies. That's the point.

    Same end-to-end behavior; the operator surface is just smaller.

## 1. OAuth device flow end-to-end

What you're testing: `authorize()` correctly walks the operator
through the device flow, stores a working token, and that token
authenticates real GitHub API calls.

**What you need:** a phone with a browser, your GitHub credentials.

**Steps:**

```bash
python3 -c "from scandroid.codespaces import authorize; authorize()"
```

The agent prints something like:

```
  Open: https://github.com/login/device
  Code: ABCD-1234
  TTL : 900s

  Waiting for authorization…
```

On your phone:
1. Open `https://github.com/login/device`.
2. Type the 6-digit code.
3. Hit Continue. GitHub shows what's being authorized — should be
   "GitHub CLI" (the default) with `codespace, repo` scopes.
4. Hit Authorize.

Back in the agent terminal: the prompt resolves and the function
returns. Check that the token landed:

```bash
ls -la ~/.config/scandroid/github_oauth.json
# -rw------- 1 you you 234 May  9 12:34 ...
# permissions MUST be 0600
```

Verify it actually authenticates:

```bash
python3 -c "
from scandroid.codespaces import list_codespaces
print(list_codespaces())
"
```

Should return a list (possibly empty `[]` if you have no
Codespaces). If it raises `ValueError`, the token wasn't loaded —
re-run `authorize()`. If it raises an HTTP 401, the token didn't
authenticate — likely a scope problem; re-authorize.

**Pass criteria:**
- [ ] `~/.config/scandroid/github_oauth.json` exists with mode 0600.
- [ ] `list_codespaces()` returns a Python list without raising.
- [ ] No PAT was created or pasted at any point.

## 2. Codespace lifecycle (Session ctxmgr)

What you're testing: `Session(...)` finds-or-creates a Codespace,
starts it, runs a command, and stops it on exit.

**What you need:** GitHub account with Codespaces enabled, ~$0.18/h
of Codespaces compute budget (the smallest 2-core instance), the
`gh` CLI installed on the agent VM (`gh --version` should print).

If `gh` is missing:
```bash
# Debian/Ubuntu — see https://github.com/cli/cli for other OSes.
type -p curl >/dev/null || sudo apt install curl -y
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list
sudo apt update
sudo apt install gh -y
```

You do NOT need to run `gh auth login` — `Session.run()` injects
`GH_TOKEN` from your stored OAuth token into the subprocess env.

**Steps:**

Pick a small repo to back the Codespace (smaller = faster
provision):

```bash
python3 << 'PY'
from scandroid.codespaces import Session
with Session(repository="zheke32174/scandroid", on_exit="delete") as cs:
    print("Codespace name:", cs.name)
    print("Created fresh:", cs.created)
    r = cs.run("uname -a && python3 --version && which gh")
    print(r.stdout)
    print("exit code:", r.returncode)
PY
```

Watch for:
1. The first call takes 30-180 seconds (provision + start +
   poll-until-Available). Subsequent calls reuse the same Codespace.
2. The print should show the Codespace's container info.
3. On context exit (`on_exit="delete"`), the Codespace gets
   deleted — verify with:

   ```bash
   python3 -c "from scandroid.codespaces import list_codespaces; print(list_codespaces())"
   ```

   The newly-created codespace shouldn't be in the list.

**Pass criteria:**
- [ ] Codespace got provisioned without manual GitHub UI clicks.
- [ ] `cs.run(...)` printed real container output.
- [ ] `on_exit="delete"` actually removed the codespace.
- [ ] No PAT, no `gh auth login` step.

**Cost note:** the smallest Codespace machine is `basicLinux32gb`
(2-core), billed in 6-second increments. A test like this should
cost a few cents. If you forget `on_exit="delete"` or `"stop"`,
you'll keep paying for compute until you stop it manually via
`stop_codespace(name)` or the GitHub UI.

## 3. Colab notebook + agent-side `discover/generate/healthcheck`

What you're testing: the notebook publishes a usable endpoint via
OAuth; the agent reads + uses it.

**What you need:** a Google account for Colab (free tier works), a
phone for the OAuth approval, the Gist ID to share with the agent.

**Operator side — open the notebook:**

1. Open
   <https://colab.research.google.com/github/Zheke32174/scandroid/blob/main/scandroid.ipynb>
   in any browser (mobile works, just clunky).
2. Runtime → Change runtime type → T4 GPU. Save.
3. Runtime → Run all.
4. Watch the output. Cells 3-5 install Ollama + start the daemon +
   open a tunnel. Cell 6 (publish) prints the OAuth prompt:

   ```
   No GITHUB_TOKEN secret. Falling back to OAuth device flow…

     Open: https://github.com/login/device
     Code: WXYZ-5678
     TTL : 900s

     Waiting for authorization…
   ```

5. On your phone, open the URL, type the code, hit Approve.
6. Cell completes:

   ```
   OAuth token obtained — publishing gist…
   Endpoint published to Gist: <GIST_ID>

   *** Save this GIST_ID for next runs (Colab Secrets) ... ***
       <GIST_ID>

   Agent usage:
       export SCANDROID_GIST_ID=<GIST_ID>
   ```

7. Copy the GIST_ID. Optionally paste into Colab Secrets so
   subsequent runs reuse it.

**Agent side — use the published endpoint:**

```bash
export SCANDROID_GIST_ID=<paste-gist-id-here>
# Optional: also a token if you want to read a private gist;
# without one, the gist must be public.
python3 << 'PY'
import os
from scandroid import healthcheck, generate
GID = os.environ["SCANDROID_GIST_ID"]
h = healthcheck(gist_id=GID)
print("healthcheck:", {k: h[k] for k in ("ok","gist_ok","tunnel_ok","model_ok","model")})
if h["ok"]:
    print(generate("In one sentence: what is a streaming codec?", gist_id=GID))
else:
    print("error:", h["error"])
PY
```

**Pass criteria:**
- [ ] Notebook publish cell completed without GITHUB_TOKEN in
      Colab Secrets.
- [ ] `healthcheck()["ok"]` is True.
- [ ] `generate()` returned a sentence (any sentence — model output
      varies).
- [ ] No PAT, no host laptop kept open after the notebook tab was
      backgrounded.

**Failure modes:**
- `gist_ok=False`: gist couldn't be read. Check the GIST_ID; check
  that the gist is either public or you've passed `token=` with
  `gist` scope.
- `tunnel_ok=False`: notebook's tunnel died. Common causes: Colab
  runtime got recycled (12h limit on free tier), ngrok session
  expired (free ngrok limits), or the cloudflare quick-tunnel
  expired (~24h). Fix: re-run the notebook.
- `model_ok=False`: tunnel up but the model isn't loaded. Usually
  a transient warmup issue; wait 30s and retry. If persistent, the
  notebook's "pull model" cell may have failed — check its output.

## 4. GitHub Pages deploy

What you're testing: the docs site publishes correctly when docs/
or mkdocs.yml change.

**What you need:** repo admin access on `Zheke32174/scandroid`.

**One-time setup:**

1. Go to <https://github.com/Zheke32174/scandroid/settings/pages>.
2. Source: **GitHub Actions** (NOT "Deploy from a branch").
3. Save.

Without this step, the action will run and report success but
the site won't be live.

**Test:**

Push any small change to `docs/` on `main`. E.g., edit a typo in
`docs/index.md`. Watch
<https://github.com/Zheke32174/scandroid/actions/workflows/docs.yml>
for the run. Should take 30-60 seconds.

When green, visit <https://zheke32174.github.io/scandroid/>. The
typo fix should be live.

**Pass criteria:**
- [ ] Action runs on push to main when docs/ or mkdocs.yml change.
- [ ] Site loads at zheke32174.github.io/scandroid/.
- [ ] The change is reflected without a manual rebuild.

**Failure modes:**
- Action fails at `mkdocs build --strict`: dead link or other
  strict-mode violation in the changed file. Build locally first:
  `pip install mkdocs mkdocs-material pymdown-extensions && mkdocs build --strict`.
- Action passes but site doesn't update: Pages source not set to
  "GitHub Actions". See one-time setup above.
- Action passes but page 404s: the upload step isn't running
  (check the workflow log). Or you visited too soon (deploy can
  take a minute after the action completes).

## 5. Device snapshot (sanctuary side)

This is in the (private) understory suite, but the test
walkthrough belongs alongside the others for completeness.

**What you need:** an Android device, the `backups` APK installed
(`dist/backups.apk` from the understory repo), the suite's other
APKs (passgen + aegis + vault-folder optional but recommended),
an external SAF directory (Documents/Backups/ works fine).

**Steps:**

1. Open the backups app, set up a vault with a master passphrase
   (write it down — without it, every snapshot is unrecoverable).
2. Tap "Device-wide snapshot (settings + user dirs)".
3. Toggle on:
   - Android settings
   - Standard user dirs
   - + Include file contents (multi-GiB possible)
4. Pick external dir → choose Documents/Backups (or wherever).
5. Grant media permissions when prompted.
6. Tap "Snapshot now".
7. Watch the foreground notification. It progresses through:
   "Collecting Android settings…" → "Collecting user-dir
   manifest…" → "Encrypting + writing…" → "Streaming user-dir
   content…" → "Snapshot complete".
8. Open Files app, navigate to Documents/Backups/. You should see
   two new files: `device-<ts>.usbe` (small, tens of KB) and
   `device-<ts>.usbs` (larger, depends on user content size).

**Pass criteria:**
- [ ] Both `.usbe` and `.usbs` files exist.
- [ ] `.usbs` size is roughly equal to total user-dir content
      (with a small overhead for chunk framing).
- [ ] App didn't crash on a multi-GB Pictures dir.
- [ ] Foreground notification updated through each phase.

**Decryption testing:** the decode side of `.usbs` isn't shipped
yet (deferred per the device-snapshot service's docstring).
You can verify the file is at least well-formed:

```python
# On any machine with the file copied off the device:
with open("device-20260509-123456.usbs", "rb") as f:
    magic = f.read(8)
    assert magic == b"USTRSTRM", f"bad magic: {magic}"
    print("Magic OK; format header valid")
```

The full restore tooling lands in a follow-up.

## What if something fails

Each section above lists pass criteria + common failure modes.
For anything not covered:

- Check the agent-side smoke test passed first.
- Check the [scandroid issues](https://github.com/Zheke32174/scandroid/issues)
  page for known problems.
- Open an issue with the failing pass criterion + the actual
  output you saw.
