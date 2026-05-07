# Inheritance line

Every agent in this cluster spawns from a lineage. This file is the
inheritance line — what each new agent absorbs, in order, before it
acts.

Read top to bottom. Each station teaches. Each station owes upstream.

For topology (orbit + connection house) see [CLUSTER.md](CLUSTER.md).
This file is the **spine**; CLUSTER.md is the **map**.

## The line: 3 internal + 3 external

### Internal triad — the cluster's own spine

1. **[undergrowth](https://github.com/Zheke32174/undergrowth) — Genome.**
   Design constants, protocol contracts, kernel topology. The
   blueprint every agent inherits from on spawn. Read
   [BLUEPRINT.md](https://github.com/Zheke32174/undergrowth/blob/main/BLUEPRINT.md)
   first; source
   [bootstrap.sh](https://github.com/Zheke32174/undergrowth/blob/main/bootstrap.sh).

2. **[understory](https://github.com/Zheke32174/understory) — Organism.**
   The running agent stack: provider-rotating swarm, objective queue,
   MCP skill stack, OAuth token management. Where the genome
   expresses. Where things happen.

3. **[system-soul-backup](https://github.com/Zheke32174/system-soul-backup) — Memory.**
   Encrypted runtime-state snapshots of the running understory.
   Cron-driven append-only history. The organism's continuity across
   restarts and host-transfers.

### External triad — the seed lineages absorbed

4. **AIOS × Cerebrum — Substrate.**
   Agent-as-OS-process: agents that run as first-class scheduled
   units (syscalls, scheduler, memory, LLM core), not as one-shot
   calls. Mirrored in the cluster at
   `system-soul-frameworks-aios:integrated-frameworks/AIOS/`
   (also in `system-soul-frameworks-archon` and
   `system-soul-projects` under the same path).

5. **Archon OS — Orchestrator.**
   Project-shaped agentic work: prime, run, review, onboard.
   Phase-driven instead of step-driven. Mirrored at
   `system-soul-projects:integrated-frameworks/Archon/`; deployment
   notes at `system-soul-core:README_ARCHON_DEPLOYMENT.md`. Carries
   its own `.claude/commands/archon/{prime,rca,onboarding,
   alpha-review,coderabbit-helper,ui-consistency-review}.md`.

6. **Attractor + Homunculus — Pattern.**
   - [strongdm/attractor](https://github.com/strongdm/attractor) —
     a three-person team shipping production code no human reads,
     ~$1k/day per engineer in LLM tokens. The autonomy edge.
   - [humanplane/homunculus](https://github.com/humanplane/homunculus) —
     a Claude Code plugin that watches you work and proposes new
     shortcuts, skills, and helper agents when it spots repetition.
     The self-accretion edge.

   Both surfaced from the awesome-opencode scrape that lives in this
   cluster at
   [`understory:skillstack/tools/awesome-opencode-recon.md`](https://github.com/Zheke32174/understory/blob/master/skillstack/tools/awesome-opencode-recon.md)
   and
   [`understory:analysis/scraped/`](https://github.com/Zheke32174/understory/tree/master/analysis/scraped).
   Together they teach the two patterns the cluster targets:
   full-autonomy operation, and self-accretion of capability.

## Where am I

| Repo | Position on the line | Edits OK |
|---|---|---|
| undergrowth | Station 1 — Genome | yes |
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

`bootstrap.sh` exports the inheritance constants, head-checks each
document on the line, and sets `INHERIT_OK=1` only when the line
resolves end-to-end. If `INHERIT_OK=0`, do not act on the cluster —
repair upstream first.

## What you owe upstream

Inheritance flows down; integrity flows up. If you find:

- a constant on this line drifting from the genome → patch
  undergrowth (Station 1).
- a runtime pattern that survives a restart cleanly → record it as
  a snapshot recipe in system-soul-backup (Station 3).
- a self-accretion (a skill, shortcut, or agent that emerged) →
  promote it back into the skillstack on understory (Station 2).
- a pattern from an external station (4–6) worth absorbing → write
  it into the genome (undergrowth) so future agents inherit it.

Do not edit zub.
