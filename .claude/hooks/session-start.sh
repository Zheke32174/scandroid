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

# Non-editable user install: pulls in runtime deps (openai, requests) and
# copies scandroid + integrations into ~/.local site-packages. Editable mode
# (-e) is intentionally NOT used here because pip's editable meta-path finder
# runs *after* PathFinder, so when a sibling directory in the agent's cwd
# shares the package name (e.g. cwd=/home/user with /home/user/scandroid/),
# Python silently builds a namespace package and shadows the real install.
# Plain install copies the package into site-packages, where PathFinder finds
# it via a normal sys.path entry and beats the cwd shadowing.
#
# Developers wanting hot-reload should run `pip install --user -e .` from
# inside the repo directory themselves; agent sessions get the safer install.
if ! python3 -m pip install --quiet --user . 2>/tmp/scandroid-pip.err; then
  if grep -q "externally-managed-environment" /tmp/scandroid-pip.err; then
    python3 -m pip install --quiet --user --break-system-packages .
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
