# Inheritance line

The agent's full inheritance is **5 third-party scaffolding repos
(the baseline framework) + 5 cluster repos**. Every agent in this
cluster inherits both, in parallel, automatically, on spawn.

This file is the **spine** — a one-page navigation surface.
[BLUEPRINT.md](https://github.com/Zheke32174/undergrowth/blob/main/BLUEPRINT.md)
is the load-bearing reference; [CLUSTER.md](CLUSTER.md) is the
topology map.

## The baseline framework — third-party scaffolding (5 repos)

These are the repos agents inherit from going forward, in parallel,
automatically. Not lineages we are deciding to absorb later — the
substrate the cluster is built on.

1. **[strongdm/attractor](https://github.com/strongdm/attractor) —
   Autonomous shipping.** A three-person team shipping production
   code no human reads; ~$1k/day per engineer in LLM tokens. The
   structural commitment to operating without human-in-the-loop on
   code paths.

2. **[Conway-Research/automaton](https://github.com/Conway-Research/automaton) —
   Runtime + economic survival.** A self-sustaining agent runtime
   with continuous reasoning loops, self-modification,
   self-replication, and built-in economic constraints. Core rule:
   *if it cannot pay, it stops existing*. Forces genuine value
   generation as the survival pressure.

3. **[humanplane/homunculus](https://github.com/humanplane/homunculus) —
   Self-accretion.** A Claude Code plugin that watches the agent
   work and proposes new shortcuts, skills, or helper agents when
   it spots repetition. Capability grows from observed behavior.

4. **[agiresearch/AIOS](https://github.com/agiresearch/AIOS) —
   Substrate kernel.** Six-module agent OS pattern: scheduler /
   context / memory / storage / tool / access. The vocabulary the
   cluster's runtime responsibilities map to. See
   [BLUEPRINT §2](https://github.com/Zheke32174/undergrowth/blob/main/BLUEPRINT.md#2-kernel-topology-aios-pattern)
   and `KERNEL_MAPPING` in
   [`inherit/baseline.py`](https://github.com/Zheke32174/undergrowth/blob/main/inherit/baseline.py).

5. **[coleam00/Archon](https://github.com/coleam00/Archon) —
   Orchestrator.** Project-shaped agentic work as a phase-driven
   DAG: plan → implement → validate → review → ship. See
   [BLUEPRINT §4](https://github.com/Zheke32174/undergrowth/blob/main/BLUEPRINT.md#4-workflow-shape-archon-pattern)
   and `WORKFLOW_PHASES`.

Attractor and homunculus surfaced from the cluster's own
awesome-opencode scrape at
[`understory:skillstack/tools/awesome-opencode-recon.md`](https://github.com/Zheke32174/understory/blob/master/skillstack/tools/awesome-opencode-recon.md)
and
[`understory:analysis/scraped/`](https://github.com/Zheke32174/understory/tree/master/analysis/scraped).
AIOS is mirrored at `system-soul-frameworks-aios:integrated-frameworks/AIOS/`;
Archon at `system-soul-projects:integrated-frameworks/Archon/`
(deployment notes at `system-soul-core:README_ARCHON_DEPLOYMENT.md`).
Conway-Research/automaton is external to this org.

## The cluster — internal (5 repos = core 3 + 2)

The cluster's own repos. Core 3 are the spine; +2 round out to five.

### Core 3

1. **[undergrowth](https://github.com/Zheke32174/undergrowth) — Genome.**
   The blueprint every agent inherits from on spawn. Synthesis in
   [BLUEPRINT.md](https://github.com/Zheke32174/undergrowth/blob/main/BLUEPRINT.md);
   programmatic baseline in
   [`inherit/baseline.py`](https://github.com/Zheke32174/undergrowth/blob/main/inherit/baseline.py)
   (`PROVIDERS`, `ROTATION_ORDER`, `KERNEL_MAPPING`, `SDK_LAYERS`,
   `WORKFLOW_PHASES`); long-lived agent registry in
   [`agents.yaml`](https://github.com/Zheke32174/undergrowth/blob/main/agents.yaml);
   version pin in
   [`.baseline-version`](https://github.com/Zheke32174/undergrowth/blob/main/.baseline-version);
   spawn entry in
   [`bootstrap.sh`](https://github.com/Zheke32174/undergrowth/blob/main/bootstrap.sh).

2. **[understory](https://github.com/Zheke32174/understory) — Organism.**
   The running stack. Provider rotation (`agentic_loop`),
   objective queue, MCP skill stack, OAuth token management, the
   arch container hosting it. Where things happen.

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

After sourcing: `$UNDERGROWTH_DIR`, `$UNDERGROWTH_VERSION`, and
`PYTHONPATH` resolved (so `from inherit.baseline import …` works).
Read `$UNDERGROWTH_DIR/BLUEPRINT.md` before acting on shared state.
Re-source on each objective cycle — ff-only, never clobbers local
work.

The five framework repos are read-only references. The cluster
inherits their patterns; we do not edit them. Edits to attractor,
automaton, homunculus, AIOS, or Archon belong upstream in their
own repositories.

## Where am I

| Repo | Role | Edits OK |
|---|---|---|
| undergrowth | Cluster — core 3 — Genome | yes (baseline-bumping) |
| understory | Cluster — core 3 — Organism | yes |
| system-soul-backup | Cluster — core 3 — Memory | snapshot writes only |
| scandroid | Cluster — +2 — Sapling | yes |
| zub | Cluster — +2 — Connection house | **no — human-only** |
| strongdm/attractor | Framework — Autonomous shipping | upstream only |
| Conway-Research/automaton | Framework — Runtime + economic survival | upstream only |
| humanplane/homunculus | Framework — Self-accretion | upstream only |
| agiresearch/AIOS | Framework — Substrate kernel | upstream only |
| coleam00/Archon | Framework — Orchestrator | upstream only |

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
- A new framework repo worth absorbing → posture-change PR
  against BLUEPRINT.md, bump baseline version. Today the
  framework is the five named above.

Do not edit zub.
