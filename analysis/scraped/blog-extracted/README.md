# blog-extracted (mirror)

Read-only mirror of the github-awesome blog scrape that lives canonically
in **understory**. Hosted here so scandroid notebooks (Colab / Codespaces)
can use the curation index offline without cloning the larger understory
tree.

- **Canonical source:** [`understory:analysis/scraped/blog-extracted/`](https://github.com/Zheke32174/understory/tree/master/analysis/scraped/blog-extracted)
- **Generator:** [`understory:scripts/scrape-blog.py`](https://github.com/Zheke32174/understory/blob/master/scripts/scrape-blog.py)
- **Categorizer:** [`understory:scripts/categorize-blog-extracted.py`](https://github.com/Zheke32174/understory/blob/master/scripts/categorize-blog-extracted.py)
- **Source attribution:** [`understory:credits/sources/github-awesome-blog.yml`](https://github.com/Zheke32174/understory/blob/master/credits/sources/github-awesome-blog.yml) — *as we use them, if we use them* policy.
- **Source blog:** [githubawesome.com](https://githubawesome.com/) (companion to the github-trending-today YouTube channel).
- **Count:** 1,835 distinct repos across 37 alphabetical shards + 39 by-category shards.
- **Freshness:** see [`freshness-report.md`](freshness-report.md) (~94% alive at last sweep).
- **Session handoff:** [`understory:home-agents/2026-05-07-session-handoff.md`](https://github.com/Zheke32174/understory/blob/master/home-agents/2026-05-07-session-handoff.md) — entry point for the next session.
- **Last refresh:** 2026-05-07.

To update this mirror, re-run the generator in understory (it produces all
shards + `blog-extracted.json` deterministically), then copy the resulting
directory back into this repo at the same path. Don't try to regenerate
in-place here — the script reads `credits/sources/...` and lives at
`scripts/scrape-blog.py`, paths that only exist in understory.

## Why mirrored here

scandroid is the Colab / lightweight-bridge surface. A notebook running in
Colab without local disk can pull these shards directly from the GitHub
raw URLs, query a single letter of repos at a time, and never has to
mount the bigger understory tree or re-fetch the blog. The JSON is
included so notebooks that want structured data don't have to parse the
markdown shards.

The mirror is a snapshot, not a live feed. If the canonical understory
copy moves ahead of this one, the count line above will be stale until
someone re-mirrors.

## Shards

| Shard | Repos | Size |
| ----- | ----: | ---: |
| [0.md](0.md) | 21 | 7 KB |
| [a-01.md](a-01.md) | 55 | 19 KB |
| [a-02.md](a-02.md) | 55 | 18 KB |
| [a-03.md](a-03.md) | 55 | 19 KB |
| [b.md](b.md) | 77 | 27 KB |
| [c-01.md](c-01.md) | 46 | 17 KB |
| [c-02.md](c-02.md) | 45 | 16 KB |
| [d-01.md](d-01.md) | 48 | 17 KB |
| [d-02.md](d-02.md) | 47 | 14 KB |
| [e.md](e.md) | 47 | 17 KB |
| [f.md](f.md) | 50 | 16 KB |
| [g.md](g.md) | 71 | 24 KB |
| [h.md](h.md) | 66 | 21 KB |
| [i.md](i.md) | 47 | 16 KB |
| [j.md](j.md) | 61 | 21 KB |
| [k.md](k.md) | 67 | 24 KB |
| [l-01.md](l-01.md) | 46 | 16 KB |
| [l-02.md](l-02.md) | 46 | 16 KB |
| [m-01.md](m-01.md) | 72 | 24 KB |
| [m-02.md](m-02.md) | 71 | 25 KB |
| [n.md](n.md) | 67 | 23 KB |
| [o.md](o.md) | 53 | 18 KB |
| [p.md](p.md) | 74 | 26 KB |
| [q.md](q.md) | 11 | 3 KB |
| [r-01.md](r-01.md) | 46 | 16 KB |
| [r-02.md](r-02.md) | 45 | 16 KB |
| [s-01.md](s-01.md) | 57 | 20 KB |
| [s-02.md](s-02.md) | 57 | 21 KB |
| [s-03.md](s-03.md) | 57 | 18 KB |
| [t-01.md](t-01.md) | 52 | 18 KB |
| [t-02.md](t-02.md) | 51 | 18 KB |
| [u.md](u.md) | 11 | 4 KB |
| [v.md](v.md) | 57 | 21 KB |
| [w.md](w.md) | 26 | 9 KB |
| [x.md](x.md) | 16 | 5 KB |
| [y.md](y.md) | 32 | 11 KB |
| [z.md](z.md) | 30 | 11 KB |

Totals: **1835 repos**, 651 KB across 37 files.
