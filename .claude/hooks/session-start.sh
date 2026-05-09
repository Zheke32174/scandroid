#!/bin/bash
# SessionStart hook for scandroid.
#
# Installs the scandroid package so `from scandroid import …` and
# `from integrations import …` resolve in any python/ipython spawned during
# the session. Runs for both local and remote (Claude Code on the web)
# sessions so any agent — VM or local CLI — gets the same namespace.
#
# Idempotent and non-interactive. Uses --user to avoid touching system or
# venv-managed site-packages.
set -euo pipefail

cd "${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

# Editable user install: pulls in runtime deps (openai, requests) and exposes
# scandroid + integrations on sys.path under ~/.local. Falls back to
# --break-system-packages only if a PEP 668 environment also blocks --user.
if ! python3 -m pip install --quiet --user -e . 2>/tmp/scandroid-pip.err; then
  if grep -q "externally-managed-environment" /tmp/scandroid-pip.err; then
    python3 -m pip install --quiet --user --break-system-packages -e .
  else
    cat /tmp/scandroid-pip.err >&2
    exit 1
  fi
fi
rm -f /tmp/scandroid-pip.err

# Surface namespace readiness in the session log.
python3 - <<'PY'
from scandroid import runtime_context, runtime_ready
print("[scandroid] namespace ready:", runtime_context())
print("[scandroid] tokens present:",
      runtime_ready(require_openai=False, require_github=False))
PY
