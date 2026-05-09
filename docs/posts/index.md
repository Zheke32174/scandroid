# Posts

Long-form notes on real engineering shipped through this project.
Not announcements; not roadmap. Just write-ups of work that's
already in the repo, surfaced for anyone digging.

## Engineering

- **[A streaming AES-GCM codec for multi-GiB Android backups](streaming-aes-gcm-codec.md)**
  *— 2026-05-09.* Chunked AES-GCM with per-chunk GCM tags,
  counter-based IVs derived from a per-stream random prefix, and
  reorder + truncation defenses via AAD-bound chunk position +
  final-flag. The codec we shipped to the understory cluster's
  device-snapshot backups.

This page rewrites every time real work ships. If a post would be
useful and isn't here, it's because the work hasn't shipped yet.
