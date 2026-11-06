---
key: SCE-THETA-HISTORY-ACCESS-AND-GLD-CACHE-GAP
claim: >-
  On 2026-09-09, the canonical ThetaData store resolved with SPY and XLE historical
  EOD/OI/Greeks files for 2023-2026, while GLD was absent from that stored universe
  despite a successful bounded GLD historical request through the existing Terminal.
falsifier: |-
  From the authorized source checkout, run the following read-only census command.
  python -c "import json; from engine.thetadata_store import resolve_thetadata_store; s=resolve_thetadata_store(required=True,purpose='sce-history-falsifier'); m=json.loads((s/'_manifest.json').read_text()); print({'gld_manifest':m.get('per_root',{}).get('GLD'),'gld_tiers':{k:(s/k/'GLD').is_dir() for k in ('eod','oi','greeks')}})"
  Compare that result with the dated manifest and original request receipts retained
  for #7009. A contemporaneous content-bearing GLD history contradicts the historical
  cache claim; an unsuccessful original vendor response contradicts request success.
  A later census establishes later liveness only and does not erase the earlier
  observation. An unresolved store must fail rather than select another path.
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

## Record-shape repair, 2026-09-10

CI run 34425846264 correctly rejected the original prose-only falsifier on head
83f9eb1511e5466b984b1f40295b41d1094e3ded: it contained no runnable or openable token.
This correction supplies the actual read-only resolver/manifest census and the
original-record comparison. It changes no validator, data source or historical
claim. The source-read command was syntax-checked, not executed as a new liveness
probe. Full source validation remains the exact-head CI obligation.
