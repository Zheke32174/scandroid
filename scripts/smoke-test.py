#!/usr/bin/env python3
"""Smoke test for scandroid's agent-side surface.

Run from any agent VM after `pip install scandroid`. Exits 0 iff every
check passes; non-zero on any failure with a clear per-check report.

Designed to run without operator interaction — covers exactly the
parts that can be verified without a phone tap or a Codespace
provision. Includes one real network call to GitHub's device-code
endpoint (which costs nothing and doesn't authorize anything).

Use cases:
    - "I just installed scandroid on a fresh agent VM. Did anything
      break?"  Run this first.
    - "Something feels off; is it me or the install?"  Run this.
    - CI smoke against any cluster baseline change.

Doesn't cover (needs operator):
    - Full OAuth approval flow.
    - Codespace provision + run + stop.
    - Notebook-side gist publish.
    - GitHub Pages deploy.

For those, see docs/posts/index.md and the README operator-test
walkthrough.
"""
from __future__ import annotations

import os
import shutil
import sys
import traceback
from typing import Callable, List, Tuple


def main() -> int:
    results: List[Tuple[bool, str, str]] = []

    def check(name: str, fn: Callable[[], object]) -> None:
        try:
            out = fn()
            detail = str(out)[:120] if out is not None else "ok"
            results.append((True, name, detail))
        except Exception as e:
            results.append((False, name, f"{type(e).__name__}: {e}"))

    # --- 1. Imports ---------------------------------------------------
    check("import scandroid", lambda: __import__("scandroid"))
    check(
        "import scandroid.oauth",
        lambda: __import__("scandroid.oauth", fromlist=["DEFAULT_CLIENT_ID"]),
    )
    check(
        "import scandroid.codespaces.Session",
        lambda: __import__("scandroid.codespaces", fromlist=["Session"]).Session,
    )
    check(
        "import scandroid.bridge.healthcheck",
        lambda: __import__("scandroid.bridge", fromlist=["healthcheck"]).healthcheck,
    )

    from scandroid import codespaces, healthcheck, oauth

    # --- 2. OAuth no-state path ---------------------------------------
    # Move any pre-existing token aside so we test the clean state.
    # Restored in the finally block below.
    token_path = oauth._token_path()
    moved = None
    if os.path.exists(token_path):
        moved = token_path + ".smoketest.bak"
        shutil.move(token_path, moved)
    try:
        def no_token_load() -> str:
            r = oauth.load()
            assert r is None, f"expected None, got {r!r}"
            return "= None"
        check("oauth.load() with no token = None", no_token_load)

        def no_token_clear() -> str:
            r = oauth.clear()
            assert r is False, f"expected False, got {r!r}"
            return "= False"
        check("oauth.clear() with no token = False", no_token_clear)

        check("oauth._token_path() resolves", oauth._token_path)

        # --- 3. OAuth device-flow START (real GitHub call) ------------
        # Round-trips a real device_code; doesn't authorize anything
        # because we don't poll for the user_code.
        def begin_check() -> str:
            init = oauth.begin()
            assert init["device_code"], "device_code missing"
            assert init["user_code"], "user_code missing"
            assert "github.com" in init["verification_uri"]
            assert int(init["expires_in"]) > 0
            return f"user_code={init['user_code']} uri={init['verification_uri']}"
        check("oauth.begin() against real GitHub", begin_check)

        # --- 4. Codespaces no-token error path ------------------------
        def no_auth_check() -> str:
            try:
                codespaces.list_codespaces()
                raise AssertionError("expected ValueError")
            except ValueError as e:
                msg = str(e)
                assert "authorize()" in msg
                assert "GITHUB_TOKEN" in msg
                return "raises ValueError naming all three options"
        check("codespaces no-auth raises with helpful message", no_auth_check)

        # --- 5. Session ctxmgr construction (no API calls) ------------
        def session_ctor() -> str:
            s = codespaces.Session(
                repository="zheke32174/scandroid", on_exit="leave"
            )
            assert s.name is None
            assert s.created is False
            assert s.on_exit == "leave"
            return "ok"
        check("Session() construction without entering", session_ctor)

        def session_bad_on_exit() -> str:
            try:
                codespaces.Session(repository="x/y", on_exit="invalid")
                raise AssertionError("expected ValueError")
            except ValueError:
                return "raises ValueError on bad on_exit"
        check("Session() rejects bad on_exit", session_bad_on_exit)

        # --- 6. healthcheck shape on failure --------------------------
        def hc_fail_path() -> str:
            h = healthcheck(
                gist_id="nonexistent_gist_id_xxxxxxxxxxxx", token="fake"
            )
            assert h["ok"] is False
            assert h["gist_ok"] is False
            assert h["error"], "error must be populated on failure"
            assert "elapsed_ms" in h
            return f"ok=False err={h['error'][:60]!r}"
        check(
            "healthcheck() returns state dict on failure (no exception)",
            hc_fail_path,
        )
    finally:
        # Restore any pre-existing token so we don't lose user state.
        if moved:
            shutil.move(moved, token_path)

    # --- Report -------------------------------------------------------
    passed = sum(1 for ok, _, _ in results if ok)
    total = len(results)
    print()
    for ok, name, detail in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print()
    print(f"  {passed}/{total} passed")
    print()
    if passed != total:
        print("  Failures above. Trace details:")
        for ok, name, detail in results:
            if not ok:
                print(f"    {name}")
                print(f"      {detail}")
        return 1
    print("  Agent-side surface healthy.")
    print("  Operator-side checks (OAuth approval, Codespace lifecycle,")
    print("  notebook end-to-end, Pages deploy) require the walkthroughs")
    print("  in docs/operator-test-walkthrough.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
