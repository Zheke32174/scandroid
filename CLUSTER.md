# Cluster: 4 + 1

This repo is part of a 5-repo cluster. The structure is **4-body
nucleic orbit + 1 connection house**:

- **4 repos** form the cluster's nucleus — autonomous, mutually
  referential, in orbit around each other. Agent-driven.
- **1 repo** ([zub](https://github.com/Zheke32174/zub)) is the
  author's **connection house** — the human hub adjacent to the
  cluster. Not part of the orbit. Off-limits to autonomous agent
  edits.

## The 4-body nucleus

| Repo | Role | Visibility |
|---|---|---|
| [understory](https://github.com/Zheke32174/understory) | **Trunk.** The running agent stack: provider-rotating swarm, objective queue, MCP skill stack, OAuth token management. Where things happen. | private |
| [undergrowth](https://github.com/Zheke32174/undergrowth) | **Blueprint.** The baseline every agent inherits from on spawn. Design constants, protocol contracts, kernel topology. Read [BLUEPRINT.md](https://github.com/Zheke32174/undergrowth/blob/main/BLUEPRINT.md). | private |
| [system-soul-backup](https://github.com/Zheke32174/system-soul-backup) | **Heartbeat.** Encrypted runtime-state snapshots of the running understory. Cron-driven append-only history of the trunk's state. | private |
| [scandroid](https://github.com/Zheke32174/scandroid) | **Sapling + public bridge.** A produced artifact (Colab/Codex/GitHub bridge experiment) AND the cluster's only public-facing repo. See §scandroid below. | **public** |

## The connection house

| Repo | Role | Visibility |
|---|---|---|
| [zub](https://github.com/Zheke32174/zub) | **The author's connection house.** Personal hub. Adjacent to the cluster, not part of the orbit. Human-only. | private |

## Topology

```
      ┌────────────────────────────────────┐
      │        4-body nucleic orbit            │
      │                                        │
      │            ┌──────────────┐            │
      │            │  undergrowth │            │
      │            │  blueprint   │            │
      │            └───────┬──────┘            │
      │                    │ inherited by      │
      │                    ▼                   │
      │            ┌──────────────┐            │
      │            │  understory  │            │
      │            │    trunk     │            │
      │            └──┬─────────┬─┘            │
      │   snapshots   │         │ produces    │
      │               ▼         ▼             │
      │       ┌────────────┐ ┌────────────┐   │
      │       │system-soul-│ │ scandroid  │   │
      │       │   backup   │ │  sapling   │   │
      │       └────────────┘ └────────────┘   │
      └────────────────┬─────────────────────┘
                       │ accessed by author via
                       ▼
               ┌──────────────┐
               │     zub        │   connection house
               │  (adjacent;    │   (human-only;
               │   not orbiting)│    no autonomous edits)
               └──────────────┘
```

## scandroid as public bridge

scandroid is the only public cluster repo — a deliberate bridge that
lets unauthenticated agents and readers see the cluster's surface
without the operator handing out access. The other 4 cluster repos
are private.

**What's visible publicly via scandroid:**
- This `CLUSTER.md` (full topology; safe to share)
- `README.md` (cluster overview + scandroid's own role)
- scandroid's own code (the Colab/Codex/GitHub bridge artifact)
- A redacted `INHERIT.md` stub pointing at the private full version

**What requires operator access (private):**
- The full `INHERIT.md` (in the 4 private nucleus repos)
- `BLUEPRINT.md` (design synthesis)
- `inherit/baseline.py` (programmatic baseline)
- `deploy/`, `bootstrap.sh`, `agents.yaml`, `OPERATOR.md`,
  `.baseline-version`
- The 4 private cluster repos (`undergrowth`, `understory`,
  `system-soul-backup`, `zub`) themselves

The byte-identity invariant for `CLUSTER.md` is enforced across all
5 cluster repos via spine-sync CI (each repo's workflow clones
scandroid — the canonical — and diffs). The byte-identity invariant
for `INHERIT.md` is enforced across the 4 private nucleus repos via
the pre-push hook (operator-side); scandroid's stub is intentionally
exempt.

Request access from the operator if you need the full inheritance.

## If you are an agent

Your inheritance is layered. **6 public framework repos**
(attractor, archon, automaton, homunculus, AIOS, Cerebrum) are
the substrate — the cluster bolsters onto their patterns rather
than re-implementing them. **undergrowth** is the operator-side
bindings overlay: which 4 of 16 catalogued providers are live,
which paths fill which AIOS module slots, version pin, agent
registry. The **5-repo cluster** (undergrowth + understory +
system-soul-backup + scandroid + zub) holds running state,
snapshots, sapling work, and the author's hub.

Read [undergrowth/BLUEPRINT.md](https://github.com/Zheke32174/undergrowth/blob/main/BLUEPRINT.md)
first for the synthesis. Source the bootstrap on spawn — it
clones the 6 frameworks (+ Supabase as Archon's backend dep) +
their transitive submodule graph + the 4 other cluster repos,
then exports per-repo `*_DIR` env vars and `DEPLOY_OK`:

    source <(curl -fsSL https://raw.githubusercontent.com/Zheke32174/undergrowth/main/bootstrap.sh)

**Do not edit zub.** It is the author's connection house, not a
place for autonomous work. If you need scratch space, work in your
own process state or in a sapling branch under understory or
scandroid.

## If you are the author

zub is yours. The other four orbit on their own; this is your hub.
