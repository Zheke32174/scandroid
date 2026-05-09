# INHERIT.md — public stub (scandroid)

> **This is a redacted public stub.** scandroid is the cluster's
> public bridge; the full `INHERIT.md` lives in the private
> `undergrowth` repo and is byte-identical across the 4 private
> nucleus repos. This stub is intentionally exempt from that
> byte-identity invariant.

scandroid is the only cluster repo with a public git endpoint. It
serves as the surface unauthenticated agents and readers land on.
The full inheritance documentation — inheritance line, framework
substrate detail, propagation contract, "what you owe upstream"
rules — lives in the 4 private nucleus repos (`undergrowth`,
`understory`, `system-soul-backup`).

## What you can still do without operator access

The cluster's framework substrate is third-party and **public**.
You can clone any of these directly from GitHub (no auth required)
and study them — they are the substrate the cluster bolts onto, not
operator-owned code:

- [strongdm/attractor](https://github.com/strongdm/attractor) — autonomous shipping
- [coleam00/archon](https://github.com/coleam00/archon) — orchestrator (phase DAG)
- [Conway-Research/automaton](https://github.com/Conway-Research/automaton) — runtime + economic survival
- [humanplane/homunculus](https://github.com/humanplane/homunculus) — self-accretion
- [agiresearch/AIOS](https://github.com/agiresearch/AIOS) — substrate kernel
- [agiresearch/Cerebrum](https://github.com/agiresearch/Cerebrum) — substrate SDK
- [supabase/supabase](https://github.com/supabase/supabase) — Archon's Postgres + auth backend

scandroid's own code (notebook + `integrations.py` + bridge setup)
demonstrates one slice of the cluster's coordination capability:
Colab ↔ Codex ↔ GitHub from a single notebook. It is a self-
contained example you can run without touching the rest of the
cluster.

## Public surface of the suite import contract

The cluster's Android suite (`passgen`, `aegis`) accepts user-data
imports from a fixed set of external file formats. The contract
lives on the spine in `undergrowth/inherit/baseline.py` as
`SUITE_IMPORT_FORMATS`, and is mirrored here so external readers
see what the apps will accept without operator access. Schemas are
stable; adding a format forces a baseline-version bump in the
private spine.

| App | Schema | Source |
|---|---|---|
| passgen | `google_passwords_csv` | Google Password Manager export |
| passgen | `proton_pass_json` | Proton Pass — JSON, unencrypted |
| passgen | `proton_pass_csv` | Proton Pass — CSV |
| aegis | `otpauth_migration_uris` | Plain text file of `otpauth-migration://` URIs |
| aegis | `proton_authenticator_json` | Proton Authenticator backup |
| aegis | `generic_otp_json` | Third-party flat OTP JSON dumps |

## What requires operator access

The operator-side overlay — which 4 of 16 catalogued LLM providers
are currently active, where each AIOS module slot is filled, the
deploy script for the 12-repo inheritance stack, the agent registry,
the baseline version pin, the operator's identity bindings — lives
in the private repos and is not visible from this stub.

If you have a legitimate need for full inheritance, request access
from the operator. See [CLUSTER.md](CLUSTER.md) for the full
topology and [README.md](README.md) for scandroid's role.
