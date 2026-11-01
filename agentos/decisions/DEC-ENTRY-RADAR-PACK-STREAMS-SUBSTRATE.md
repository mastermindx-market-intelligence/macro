---
key: ENTRY-RADAR-PACK-STREAMS-SUBSTRATE
question: >
  Should the live Entry Radar pack's substrate stream to a parquet spool in production,
  and on which pack producers?
answer: >
  Yes — on BOTH producers (the VPS systemd pack unit and the GitHub Actions
  entry-radar-live lane) via ``--stream-substrate``. Fingerprint v2 is the pack
  identity for streamed builds; the frozen v1 digest rule remains for legacy packs
  already on disk.
rationale: >
  The in-memory substrate hits a memory ceiling as the probe set scales; streaming
  through ``ParquetSpoolSink`` keeps one pack layout in production instead of a
  VPS-only fast path beside an Actions memory path. Spool orphans are reaped by
  ``reap_spool_orphans`` so abandoned temp files do not accumulate under the state
  dir.
alternatives:
  - option: VPS-only streaming (Actions keeps building substrate in memory)
    why_not: >
      Two production pack layouts — spool-backed on the box, frame materialization in
      CI — diverge on fingerprint semantics, save/load paths, and failure envelopes;
      one layout is the ruling.
  - option: Recompute v1 pack digests for streamed packs
    why_not: >
      Frozen by PR #8387 round-2 review: v1 identity is legacy; streaming adopts
      fingerprint v2 without rewriting historical pack hashes.
evidence:
  - "PR #8387 merge df5d4acb87 — ``--stream-substrate``, ``ParquetSpoolSink``, ``reap_spool_orphans``, fingerprint v2"
  - "tests/test_entry_radar_pack_spool.py — spool round-trip, save/load without ``_substrate_frame``"
  - "tests/test_entry_radar_live_pack_script.py — ``substrate_sink`` and CLI flag wiring"
  - "tests/test_entry_radar_w4_pack.py::test_save_pack_stale_hash_refusal_creates_no_directory — stale hash refusal before ``pack/`` mkdir"
  - "app/deploy/macro-entry-radar-pack.service:48 — ExecStart carries ``--stream-substrate``"
  - ".github/workflows/entry-radar-live.yml:214-216 — dry-run and production invocations both stream"
affects:
  - app/deploy/macro-entry-radar-pack.service
  - .github/workflows/entry-radar-live.yml
  - scripts/entry_radar_live_pack.py
  - engine/entry_radar/live_pack.py
confidence: high
reversibility: easy
decided_by: session:idr-pscale3
decided_at: 2026-10-04
---

## Grounds

PR #8387 landed the spool substrate builder but no production caller passed
``--stream-substrate``; this decision wires both pack producers and refuses stale
``pack_hash`` saves before creating the destination tree.

## What would reopen this

Measured proof that streaming cannot meet the VPS MemoryMax envelope on the armed
probe set, or an explicit operator instruction to split producers again.
