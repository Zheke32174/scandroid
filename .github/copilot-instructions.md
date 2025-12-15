<!-- .github/copilot-instructions.md -->
Purpose: concise, repo-specific guidance for AI coding agents working in this repository.

# Quick project summary
- scandroid is a tiny repository that acts as a bridge between a device's filesystem and GitHub. The primary artifact is `groot.html` (a saved local directory listing). See `bridge_setup.md` for the manual update flow.

# What to work on
- The main maintenance task is updating `groot.html` with a fresh device snapshot (see `bridge_setup.md`).
- No build system or tests are present. Treat changes as documentation/content updates unless a new script or automation is added.

# Repository conventions & actionable examples
- Update snapshot workflow (manual):
  1. Open device browser to `file:///` and "Save Page" as `groot.html`.
 2. Replace `groot.html` in the repo, commit with a short message, e.g. `chore: update snapshot groot.html (YYYY-MM-DD)` and push.
- Commit message style: keep imperative, 50 chars or less for title. Use `chore:` for periodic snapshots and `feat:`/`fix:` only if adding features or bug fixes.
- Branching: small topic branches for changes (e.g., `snapshot/2025-12-15` or `dev/add-sync-script`). Open a PR to `main` for review when adding automation or scripts.

# Patterns and important files
- `bridge_setup.md` — explains the manual snapshot process and future automation ideas.
- `groot.html` — the snapshot artifact. Preserve the HTML structure; prefer replacing the entire file when updating.
- `README.md` — minimal project description; if adding automation or tests, update this file with how to run them.

# Integration points / suggestions for automation
- If adding automation, prefer a small script (Python or Node) that can enumerate a filesystem and output `groot.html` in the same format. Add a simple README section and a GitHub Action to run on a schedule.

# Debugging & development notes for agents
- There is no runtime to launch. Work is done by editing files, validating HTML rendering in a browser, and committing.
- If adding a dev workflow, include a minimal `.devcontainer` so Codespaces and other IDE containers open with a predictable environment.

# If you make changes
- Add a clear commit message and push to a branch on `origin`. Open a PR and include a short description of what was changed and why.

Please ask for clarification if a suggested change would touch areas outside these files (for example, adding CI or remote integrations).