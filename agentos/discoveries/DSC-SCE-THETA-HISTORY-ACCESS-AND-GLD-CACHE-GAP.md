---
key: SCE-THETA-HISTORY-ACCESS-AND-GLD-CACHE-GAP
claim: >-
  On 2026-09-09, the canonical ThetaData store resolved with SPY and XLE historical
  EOD/OI/Greeks files for 2023-2026, while GLD was absent from that stored universe
  despite a successful bounded GLD historical request through the existing Terminal.
falsifier: >-
  Repeat resolve_thetadata_store and inspect the dated per-root manifest and the
  eod/GLD, oi/GLD and greeks/GLD directories; a contemporaneous content-bearing
  GLD history contradicts the cache observation, while the original bounded
  Terminal response can independently falsify the request-success observation.
so_what: >-
  Continue SCE research through the existing source owner and resolver. Treat the
  GLD cache gap separately from vendor access, and verify exact timestamped quote
  coverage before claiming executable options replication. Do not start a second
  Terminal or silently populate a parallel options store.
kind: data
verified_at: 2026-09-09
verified_by: >-
  Existing-host Python read: engine.thetadata_store.resolve_thetadata_store;
  manifest per_root and directory census; pyarrow ParquetFile metadata/schema;
  bounded existing-Terminal option/at_time/quote and option/history/eod GETs.
scope:
  - WS:ADVANCED-DATA-OPTIONS
  - options-intelligence
  - research/nextsignals/
confidence: verified
---

## Interpretation

This is a dated access observation, not a new lifecycle state or an instruction to
change the data estate. It neither reopens nor closes AD-1T1/AD-1T2. The evidence
and exact research continuation are in
`research/nextsignals/SCE_HISTORY_ACCESS_AND_REPLAY_BOUNDARY_2026-09-09.md`.

The successful requests cover individual examples, not full history. The normalized
EOD schema does not preserve every field needed for executable-time valuation.
Raw licensed data and private host identifiers remain outside this public record.
