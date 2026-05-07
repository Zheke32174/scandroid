# Inheritance line

The cluster's inheritance is **3 internal stations + 3 external
lineages**. This file is the **spine** — a one-page navigation
surface. [BLUEPRINT.md](https://github.com/Zheke32174/undergrowth/blob/main/BLUEPRINT.md)
is the load-bearing reference; [CLUSTER.md](CLUSTER.md) is the
topology map.

Read top to bottom. Each station teaches. Each station owes upstream.

## The line

### Internal triad — the automaton

The cluster's three internal stations together **are an automaton**.
The pattern has two named edges, both surfaced from the cluster's
own awesome-opencode scrape at
[`understory:skillstack/tools/awesome-opencode-recon.md`](https://github.com/Zheke32174/understory/blob/master/skillstack/tools/awesome-opencode-recon.md)
and
[`understory:analysis/scraped/`](https://github.com/Zheke32174/understory/tree/master/analysis/scraped):

- **The attractor edge** — structural commitment to autonomous
  operation, in the spirit of
  [strongdm/attractor](https://github.com/strongdm/attractor) (a
  three-person team shipping production code no human reads). The
  cluster's OAuth-only posture, MCP-first tool discovery, and
  `agentic_loop` provider rotation are concrete instances.
- **The homunculus edge** — self-accretion of capability, in the
  spirit of
  [humanplane/homunculus](https://github.com/humanplane/homunculus)
  (watch the agent work; when it repeats, propose a new shortcut,
  skill, or helper). The skillstack on understory and the
  `agents.yaml` registry on undergrowth are where this lives.

These describe what the inner already is, not something to absorb
from outside. The three stations of the automaton:

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
   The running stack. Where the genome expresses: provider rotation
   (`agentic_loop`), objective queue, MCP skill stack, OAuth token
   management, the arch container hosting it. Where things happen.

3. **[system-soul-backup](https://github.com/Zheke32174/system-soul-backup) — Memory.**
   Encrypted snapshots of the organism's runtime state. Cron-driven,
   append-only. Restore = git clone + decrypt + replay. The truth
   when blueprint and reality disagree.

### External triad — the seed lineages absorbed

All three absorbed ✅ at v0.1.0 (codified in BLUEPRINT.md and the
`inherit.baseline` constants).

4. **AIOS — Substrate kernel.**
   Six-module kernel pattern: scheduler / context / memory /
   storage / tool / access. See
   [BLUEPRINT §2](https://github.com/Zheke32174/undergrowth/blob/main/BLUEPRINT.md#2-kernel-topology-aios-pattern)
   and `KERNEL_MAPPING`. Mirrored in the cluster at
   `system-soul-frameworks-aios:integrated-frameworks/AIOS/`.

5. **Cerebrum — Substrate SDK.**
   Four-layer SDK pattern: LLM / Memory / Storage / Tool. See
   [BLUEPRINT §3](https://github.com/Zheke32174/undergrowth/blob/main/BLUEPRINT.md#3-sdk-layering-cerebrum-pattern)
   and `SDK_LAYERS`. Pairs with AIOS — kernel + SDK — to give the
   cluster a vocabulary for runtime responsibilities.

6. **Archon — Orchestrator.**
   Project-shaped agentic work as a phase-driven DAG: plan →
   implement → validate → review → ship. See
   [BLUEPRINT §4](https://github.com/Zheke32174/undergrowth/blob/main/BLUEPRINT.md#4-workflow-shape-archon-pattern)
   and `WORKFLOW_PHASES`. Mirrored at
   `system-soul-projects:integrated-frameworks/Archon/`;
   deployment notes at
   `system-soul-core:README_ARCHON_DEPLOYMENT.md`.

## Where am I

| Repo | Position on the line | Edits OK |
|---|---|---|
| undergrowth | Station 1 — Genome (the automaton's blueprint) | yes (baseline-bumping) |
| understory | Station 2 — Organism (the automaton's body) | yes |
| system-soul-backup | Station 3 — Memory (the automaton's continuity) | snapshot writes only |
| scandroid | Sapling (a produced artifact, off the spine) | yes |
| zub | Connection house (adjacent; author's hub) | **no — human-only** |

External stations (4–6) are read-only references. Edits to AIOS,
Cerebrum, or Archon belong upstream in their own repositories, not
in this cluster.

## Bootstrap

On spawn, source the line:

    source <(curl -fsSL https://raw.githubusercontent.com/Zheke32174/undergrowth/main/bootstrap.sh)

or, when the local cache exists:

    source $HOME/.undergrowth/bootstrap.sh

After sourcing: `$UNDERGROWTH_DIR`, `$UNDERGROWTH_VERSION`, and
`PYTHONPATH` resolved (so `from inherit.baseline import …` works).
Read `$UNDERGROWTH_DIR/BLUEPRINT.md` before acting on shared state.
Re-source on each objective cycle — ff-only, never clobbers local
work.

## What you owe upstream

Inheritance flows down; integrity flows up.

- A constant on this line drifting from the genome → edit
  `inherit/baseline.py`, bump `.baseline-version`, PR against
  undergrowth (Station 1). Never patch a constant in your own
  agent's scope.
- A long-lived agent spawning anywhere in the cluster → register
  in `agents.yaml`. Ephemerals don't.
- A runtime pattern that survives a restart cleanly → record it
  as a snapshot recipe in system-soul-backup (Station 3).
- A self-accretion (a skill, shortcut, or agent that emerged) →
  promote it back into the skillstack on understory (Station 2)
  and into the `agents.yaml` registry if long-lived. The
  homunculus edge is supposed to grow.
- A new external lineage worth absorbing into the genome →
  posture-change PR against BLUEPRINT.md, bump baseline version.

Drift between blueprint and reality is a real signal. Do not
silently work around it. PR or issue — re-align the cluster, or
update the baseline.

Do not edit zub.
