# Inheritance line

The agent's full inheritance is **6 third-party framework repos +
their dependency git repos + the awesome-opencode scrape + the
5-repo cluster (the core / minds base)**. Every agent in this
cluster inherits all of it, in parallel, automatically, on spawn.

This file is the **spine** — a one-page navigation surface.
[BLUEPRINT.md](https://github.com/Zheke32174/undergrowth/blob/main/BLUEPRINT.md)
is the load-bearing reference; [CLUSTER.md](CLUSTER.md) is the
topology map; [deploy/README.md](https://github.com/Zheke32174/undergrowth/blob/main/deploy/README.md)
is the universal deploy contract.

## The baseline framework — third-party scaffolding (6 repos)

The substrate the cluster is built on. Cloned shallow with
`--recurse-submodules` so dependency git repos and onward come
along on first clone, refreshed with `submodule update --init
--recursive` on each subsequent bootstrap cycle.

1. **[strongdm/attractor](https://github.com/strongdm/attractor) —
   Autonomous shipping.** A three-person team shipping production
   code no human reads; ~$1k/day per engineer in LLM tokens. The
   structural commitment to operating without human-in-the-loop
   on code paths.

2. **[coleam00/archon](https://github.com/coleam00/archon) —
   Orchestrator.** Project-shaped agentic work as a phase-driven
   DAG: plan → implement → validate → review → ship. See
   [BLUEPRINT §4](https://github.com/Zheke32174/undergrowth/blob/main/BLUEPRINT.md#4-workflow-shape-archon-pattern)
   and `WORKFLOW_PHASES`. Mirrored in this org at
   `system-soul-projects:integrated-frameworks/Archon/`.

3. **[Conway-Research/automaton](https://github.com/Conway-Research/automaton) —
   Runtime + economic survival.** A self-sustaining agent runtime
   with continuous reasoning loops, self-modification,
   self-replication, and built-in economic constraints. Core rule:
   *if it cannot pay, it stops existing*. Forces genuine value
   generation as the survival pressure.

4. **[humanplane/homunculus](https://github.com/humanplane/homunculus) —
   Self-accretion.** A Claude Code plugin that watches the agent
   work and proposes new shortcuts, skills, or helper agents when
   it spots repetition. Capability grows from observed behavior.

5. **[agiresearch/AIOS](https://github.com/agiresearch/AIOS) —
   Substrate kernel.** Six-module agent OS pattern: scheduler /
   context / memory / storage / tool / access. The vocabulary the
   cluster's runtime responsibilities map to. See
   [BLUEPRINT §2](https://github.com/Zheke32174/undergrowth/blob/main/BLUEPRINT.md#2-kernel-topology-aios-pattern)
   and `KERNEL_MAPPING`. Mirrored at
   `system-soul-frameworks-aios:integrated-frameworks/AIOS/`.

6. **[agiresearch/Cerebrum](https://github.com/agiresearch/Cerebrum) —
   Substrate SDK.** Four-layer SDK pattern: LLM / Memory / Storage
   / Tool. Pairs with AIOS — kernel + SDK — to give the cluster a
   vocabulary for runtime responsibilities. See
   [BLUEPRINT §3](https://github.com/Zheke32174/undergrowth/blob/main/BLUEPRINT.md#3-sdk-layering-cerebrum-pattern)
   and `SDK_LAYERS`.

Plus the **dependency git repos and onward** — the transitive
submodule graph reachable from each of the six. Pulled
automatically by the deploy script's `--recurse-submodules`
behavior. Per-framework setup runs once per machine via
`deploy/setup-frameworks.sh` (idempotent, marker-file gated).

Attractor and homunculus surfaced from the cluster's own
awesome-opencode scrape (next section). AIOS, Cerebrum, and
Archon are mirrored in adjacent system-soul repositories with
deployment notes at
`system-soul-core:README_ARCHON_DEPLOYMENT.md`.
Conway-Research/automaton is external to this org.

## The awesome scrape — the cluster's own pattern source

The cluster's awesome-opencode reconnaissance lives at
[`understory:skillstack/tools/awesome-opencode-recon.md`](https://github.com/Zheke32174/understory/blob/master/skillstack/tools/awesome-opencode-recon.md)
and
[`understory:analysis/scraped/`](https://github.com/Zheke32174/understory/tree/master/analysis/scraped).
It is the meta-source: it surfaced attractor and homunculus into
this framework, and it's where the cluster looks when considering
future absorptions. Agents inherit it automatically when they
clone understory (Station 2 of the cluster).

## The cluster — 5 repos = the core / minds base

The cluster's own repos. Core 3 are the spine; +2 round out to
five. **Core 3, 2 more, then our five.**

### Core 3

1. **[undergrowth](https://github.com/Zheke32174/undergrowth) — Genome.**
   The blueprint every agent inherits from on spawn. Synthesis in
   [BLUEPRINT.md](https://github.com/Zheke32174/undergrowth/blob/main/BLUEPRINT.md);
   programmatic baseline in
   [`inherit/baseline.py`](https://github.com/Zheke32174/undergrowth/blob/main/inherit/baseline.py)
   (`FRAMEWORKS`, `PROVIDERS`, `ROTATION_ORDER`, `KERNEL_MAPPING`,
   `SDK_LAYERS`, `WORKFLOW_PHASES`); long-lived agent registry in
   [`agents.yaml`](https://github.com/Zheke32174/undergrowth/blob/main/agents.yaml);
   version pin in
   [`.baseline-version`](https://github.com/Zheke32174/undergrowth/blob/main/.baseline-version);
   spawn entry in
   [`bootstrap.sh`](https://github.com/Zheke32174/undergrowth/blob/main/bootstrap.sh);
   universal deploy at
   [`deploy/`](https://github.com/Zheke32174/undergrowth/blob/main/deploy/README.md);
   branching convention in
   [`BRANCHES.md`](https://github.com/Zheke32174/undergrowth/blob/main/BRANCHES.md).

2. **[understory](https://github.com/Zheke32174/understory) — Organism.**
   The running stack. Provider rotation (`agentic_loop`),
   objective queue, MCP skill stack, OAuth token management, the
   arch container hosting it. Carries the awesome-opencode scrape.
   Where things happen.

3. **[system-soul-backup](https://github.com/Zheke32174/system-soul-backup) — Memory.**
   Encrypted snapshots of the organism's runtime state.
   Cron-driven, append-only. Restore = git clone + decrypt + replay.

### + 2 more

4. **[scandroid](https://github.com/Zheke32174/scandroid) — Sapling.**
   A produced artifact off the spine. Colab/Codex/GitHub bridge.

5. **[zub](https://github.com/Zheke32174/zub) — Connection house.**
   Adjacent to the cluster, not part of it. Author's hub.
   **No autonomous edits.**

## Inheritance — automatic, parallel, going forward

On spawn, every agent sources:

    source <(curl -fsSL https://raw.githubusercontent.com/Zheke32174/undergrowth/main/bootstrap.sh)

or, when the local cache exists:

    source $HOME/.undergrowth/bootstrap.sh

`bootstrap.sh` clones undergrowth itself, exports baseline env
vars, then sources `deploy/deploy.sh` which clones the **other
11 top-level repos** in parallel with `--recurse-submodules`:

- **6 public framework repos** (the substrate the cluster
  bolsters onto): attractor, archon, automaton, homunculus, AIOS,
  Cerebrum.
- **1 framework dep** (Archon's Postgres+auth backend): Supabase.
- **4 other cluster repos** (operator-side, private):
  understory, system-soul-backup, scandroid, zub.

It exports per-repo `*_DIR` env vars (ATTRACTOR_DIR, ARCHON_DIR,
AUTOMATON_DIR, HOMUNCULUS_DIR, AIOS_DIR, CEREBRUM_DIR,
SUPABASE_DIR, UNDERSTORY_DIR, SYSTEM_SOUL_BACKUP_DIR,
SCANDROID_DIR, ZUB_DIR), and sets `DEPLOY_OK=1` only when all 12
resolve (the 11 above + undergrowth itself).

Re-source on each objective cycle — ff-only, never clobbers local
work; submodules refresh recursively; per-shell guard makes
repeat-source a no-op.

The six framework repos are read-only references. The cluster
inherits their patterns; we do not edit them. Edits to attractor,
archon, automaton, homunculus, AIOS, or Cerebrum belong upstream
in their own repositories.

## Where am I

| Repo | Role | Edits OK |
|---|---|---|
| undergrowth | Cluster — core 3 — Genome | yes (baseline-bumping) |
| understory | Cluster — core 3 — Organism (carries the awesome scrape) | yes |
| system-soul-backup | Cluster — core 3 — Memory | snapshot writes only |
| scandroid | Cluster — +2 — Sapling | yes |
| zub | Cluster — +2 — Connection house | **no — human-only** |
| strongdm/attractor | Framework — Autonomous shipping | upstream only |
| coleam00/archon | Framework — Orchestrator | upstream only |
| Conway-Research/automaton | Framework — Runtime + economic survival | upstream only |
| humanplane/homunculus | Framework — Self-accretion | upstream only |
| agiresearch/AIOS | Framework — Substrate kernel | upstream only |
| agiresearch/Cerebrum | Framework — Substrate SDK | upstream only |
| supabase/supabase | Framework dep — Archon's Postgres+auth backend | upstream only |
| (transitive submodules) | Framework deps — inherited automatically | upstream only |

## What you owe upstream

Inheritance flows down; integrity flows up.

- A constant on the cluster spine drifting from the genome → edit
  `inherit/baseline.py`, bump `.baseline-version`, PR against
  undergrowth (Genome). Never patch a constant in your own agent's
  scope.
- A long-lived agent spawning anywhere in the cluster → register
  in `agents.yaml`. Ephemerals don't.
- A runtime pattern that survives a restart cleanly → record it
  as a snapshot recipe in system-soul-backup (Memory).
- A self-accretion (a skill, shortcut, or agent that emerged) →
  promote it back into the skillstack on understory (Organism)
  and into `agents.yaml` if long-lived. Homunculus is supposed
  to grow.
- A new framework repo worth absorbing → add an entry to
  `inherit/baseline.py` `FRAMEWORKS` (the source of truth for the
  framework list), mirror its URL in `deploy/deploy-framework.sh`,
  add the `*_DIR` to `deploy/verify.sh`, posture-change PR against
  BLUEPRINT.md, bump baseline version. Today the framework is the
  six named above plus their transitive submodule graph.

Do not edit zub.
