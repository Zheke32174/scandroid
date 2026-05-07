# Inheritance line

The cluster's inheritance is **3 internal stations + 3 external
lineages**. This file is the **spine** — a one-page navigation
surface. [BLUEPRINT.md](https://github.com/Zheke32174/undergrowth/blob/main/BLUEPRINT.md)
is the load-bearing reference; [CLUSTER.md](CLUSTER.md) is the
topology map.

Read top to bottom. Each station teaches. Each station owes upstream.

## The line

### Internal triad — the cluster's own spine

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

4. **AIOS × Cerebrum — Substrate.** Absorbed ✅ at v0.1.0.
   AIOS supplies the **kernel topology** (scheduler / context /
   memory / storage / tool / access — see
   [BLUEPRINT §2](https://github.com/Zheke32174/undergrowth/blob/main/BLUEPRINT.md#2-kernel-topology-aios-pattern),
   `KERNEL_MAPPING`). Cerebrum supplies the **SDK layering**
   (LLM / Memory / Storage / Tool —
   [BLUEPRINT §3](https://github.com/Zheke32174/undergrowth/blob/main/BLUEPRINT.md#3-sdk-layering-cerebrum-pattern),
   `SDK_LAYERS`). Mirrored in the cluster at
   `system-soul-frameworks-aios:integrated-frameworks/AIOS/`.

5. **Archon OS — Orchestrator.** Absorbed ✅ at v0.1.0.
   Project-shaped agentic work as a phase-driven DAG: plan →
   implement → validate → review → ship
   ([BLUEPRINT §4](https://github.com/Zheke32174/undergrowth/blob/main/BLUEPRINT.md#4-workflow-shape-archon-pattern),
   `WORKFLOW_PHASES`). Mirrored at
   `system-soul-projects:integrated-frameworks/Archon/`; deployment
   notes at `system-soul-core:README_ARCHON_DEPLOYMENT.md`.

6. **Attractor + Homunculus — Pattern.** Absorbed ⏳ pending v0.2.0.
   - [strongdm/attractor](https://github.com/strongdm/attractor) —
     a three-person team shipping production code no human reads.
     The **autonomy edge**: structural commitment to operating
     without human-in-the-loop on code paths.
   - [humanplane/homunculus](https://github.com/humanplane/homunculus) —
     a Claude Code plugin that watches the agent work and proposes
     new shortcuts, skills, helper agents when it spots repetition.
     The **self-accretion edge**: the cluster grows its own
     skillstack from observed behavior.

   Both surfaced from the awesome-opencode scrape that lives in
   the cluster at
   [`understory:skillstack/tools/awesome-opencode-recon.md`](https://github.com/Zheke32174/understory/blob/master/skillstack/tools/awesome-opencode-recon.md)
   and
   [`understory:analysis/scraped/`](https://github.com/Zheke32174/understory/tree/master/analysis/scraped).
   Codifying these into BLUEPRINT.md — a posture-change PR adding
   an autonomy/self-accretion section, likely a new
   `inherit.baseline` constant, and bumping `.baseline-version` to
   `0.2.0` — is the next genome evolution.

## Where am I

| Repo | Position on the line | Edits OK |
|---|---|---|
| undergrowth | Station 1 — Genome | yes (baseline-bumping) |
| understory | Station 2 — Organism | yes |
| system-soul-backup | Station 3 — Memory | snapshot writes only |
| scandroid | Sapling (a produced artifact, off the spine) | yes |
| zub | Connection house (adjacent; author's hub) | **no — human-only** |

External stations (4–6) are read-only references. Edits to AIOS,
Archon, Attractor, or Homunculus belong upstream in their own
repositories, not in this cluster.

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
  promote it back into the skillstack on understory (Station 2).
- A pattern from an external station (4–6) worth absorbing into
  the genome → posture-change PR against BLUEPRINT.md, bump
  baseline version. **Attractor + Homunculus are the next
  absorption candidates** (→ v0.2.0).

Drift between blueprint and reality is a real signal. Do not
silently work around it. PR or issue — re-align the cluster, or
update the baseline.

Do not edit zub.
