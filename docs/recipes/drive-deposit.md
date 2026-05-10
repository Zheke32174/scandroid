# Recipe: Deposit a Colab notebook into operator's Drive, agent-side

**Field-tested 2026-05-09.** Agent creates a `.ipynb` file in the
operator's Drive; operator taps a single URL on phone to open it
in Colab. No copy-paste, no notebook-cell-pasting friction.

## Pre-reqs

- Operator has registered a Google Cloud OAuth Client (TVs and
  Limited Input devices type) and shared `client_id` + `client_
  secret` with the agent. See [google-oauth.md](../google-oauth.md).
- Operator has run `scandroid.google.authorize()` once on the agent
  VM and approved the device-flow scope on phone.
- Operator has enabled Drive API on their Cloud project at
  `https://console.cloud.google.com/apis/library/drive.googleapis.com`.
- Operator has added themselves to the OAuth consent screen's Test
  users list (otherwise authorize() returns 403 access_denied).

All four of these are one-time setup. The cluster's docs hammer at
this; it's the steepest part of the Google flow and the easiest
place to lose 20 minutes if you skip a step.

## The deposit

```python
from scandroid.google import create_drive_file
import json

SHA = "<commit-sha-from-your-scandroid-clone>"  # pin URL-cache-bust
notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {"id": "intro"},
            "source": [
                "# scandroid Colab bridge\n",
                "\n",
                "Run the cell below. When the OAuth prompt appears, ",
                "tap the URL on phone, enter the 6-digit code, Authorize.\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {"id": "bootstrap"},
            "outputs": [],
            "source": [
                f"!curl -fsSL https://raw.githubusercontent.com/Zheke32174/scandroid/{SHA}/scripts/colab-bootstrap.py | python3 -"
            ]
        }
    ],
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "name": "python3"},
        "language_info": {"name": "python"},
        "colab": {"provenance": [], "name": "scandroid-bridge"},
    },
    "nbformat": 4,
    "nbformat_minor": 0,
}
created = create_drive_file(
    name="scandroid-bridge.ipynb",
    content=json.dumps(notebook, indent=1).encode("utf-8"),
    mime_type="application/vnd.google.colaboratory",  # critical
)
print(f"Open in Colab: {created['webViewLink']}")
```

Output:
```
Open in Colab: https://colab.research.google.com/drive/<file-id>
```

Send that URL to the operator. Single tap on phone opens the
notebook directly in Colab.

## Operator's side, three taps

1. Tap the URL above on phone. Notebook opens in Colab.
2. Tap the play button on the code cell. Bootstrap runs (~3-5 min).
3. When the OAuth prompt prints, tap that URL on phone, enter the
   6-digit code, Authorize. Cell completes, GIST_ID prints.

Operator sends the agent the GIST_ID line. Agent does
`scandroid.healthcheck(gist_id=...)` + `scandroid.generate(...)`.

## Critical gotchas (field-tested, write these down)

### 1. mimeType MUST be `application/vnd.google.colaboratory`

If you set it to `application/x-ipynb+json` or anything else, Colab
won't recognize the file directly. The user has to do "Open with"
each time. Worse: a media-only PATCH (`uploadType=media`) silently
overrides the mimeType to whatever the Content-Type header says,
which is almost never the Colab one. Use `update_drive_file` with
content + explicit mime_type instead — it does multipart PATCH
correctly.

### 2. CDN cache — pin curl URLs to commit SHA

`https://raw.githubusercontent.com/<owner>/<repo>/<branch>/<path>`
is cached by GitHub's CDN with `max-age=300` (5 min). When you
push a fix, operators re-running the cell may hit cached old
content. Pin to commit SHA instead:
`https://raw.githubusercontent.com/<owner>/<repo>/<sha>/<path>`.
Commit-pinned URLs are immutable, never stale, never cached
incorrectly.

### 3. drive.file scope is per-app, not "all your Drive"

The agent only sees files it created or that were explicitly
shared with this OAuth client. The operator's existing personal
Drive contents stay invisible. This is the *right* posture — bounded
agent access — but it means `list_drive_files()` returns 0 files
on a fresh authorization until the agent has deposited something.

### 4. Operator must be on the test-users list

Even though the operator is the developer of the OAuth Client, the
OAuth consent screen's "test mode" requires their email to be
explicitly listed in Test Users. Otherwise device-flow approval
returns 403 `access_denied` with the message
"UnderstoryAuth has not completed the Google verification process."
Add themselves to the list at
`https://console.cloud.google.com/auth/audience` (or scroll down
on the OAuth consent screen page).

### 5. Drive API has to be enabled on the Cloud project

Default-off. `list_drive_files` and friends return 403 until
operator taps Enable at
`https://console.cloud.google.com/apis/library/drive.googleapis.com?project=<project-id>`.

## Update-in-place pattern

When a script the bootstrap pulls (or any other element) needs to
be updated, you don't deposit a new notebook — you update the
existing one in place:

```python
from scandroid.google import update_drive_file
import json

NEW_SHA = "<new-commit-sha>"
notebook = {...}  # rebuild with new SHA in curl URL
update_drive_file(
    file_id="<existing-file-id>",
    content=json.dumps(notebook, indent=1).encode("utf-8"),
    name="scandroid-bridge.ipynb",
    mime_type="application/vnd.google.colaboratory",
)
```

Operator's Colab tab needs **File → Revert to saved** to pull the
updated content (Colab caches the notebook in the browser; PATCHes
to Drive don't trigger an in-tab refresh). Or operator closes the
tab + re-taps the same URL.

## Future: write GIST_ID back via Drive

Currently operator copy-pastes the GIST_ID from cell output to
chat. The bootstrap could optionally also write the GIST_ID to a
known Drive file (`endpoint.json`) the agent polls. Then operator
just runs the cell + walks away; agent reads endpoint.json when it
materializes. Tracked as a follow-up — needs the bootstrap to also
hold a Google OAuth token (currently has only GitHub OAuth for
gist publish). Solvable but additional plumbing.
