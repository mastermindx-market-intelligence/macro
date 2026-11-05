---
key: SKEW-THETADATA-RECOMPUTE-DIVERGES-FROM-POLYGON-LEDGER
claim: >
  The ThetaData skew recompute (engine/options_skew on the M1 EOD store) and the legacy
  polygon_gex ledger are NOT interchangeable per (date, underlying): on the 3,965 keys both
  can price, |delta skew| is p50 0.0379 / p90 0.167 / max 3.95 and the SIGN agrees on only
  60% (2,392 match vs 1,563 flip), with the tails on illiquid names (MQ, ALT). Of the
  12,375 legacy keys, 8,410 had no ThetaData chain — 2,875 are weekend-dated rows (legacy
  as_of artifacts; the EOD store has no weekend rows) and 5,535 are weekday keys the
  store did not cover.
falsifier: >
  On the M1 store host run `python -m scripts.audit_options_skew_overlap` (defaults) against
  the committed bootstrap ledger data/options_skew/snapshots.parquet (12,375 polygon_gex rows,
  2026-06-21 -> 2026-08-13) with THETADATA_STORE=/Users/chriswong/theta-ops-wt/data/thetadata_eod
  and read research/MARKET_ONTOLOGY_F03_SKEW_OVERLAP_RECEIPT_2026-09-22.md. A re-run whose sign
  agreement exceeds ~90% or whose p90 |delta| falls under 0.05 refutes the divergence; a run
  whose no_chain count on WEEKDAY keys drops to near zero refutes the coverage half.
so_what: >
  The W2-3 cutover (render hosts emit from the R2-hydrated ThetaData ledger) changes the
  number users see per name, not just its provenance — keep the per-row `source` column,
  keep skew at display tier, and do not promote skew (rank/size/gate) until a
  methodology-parity packet reconciles tenor/strike selection between the ThetaData recompute
  and the retired polygon path. Never compare the two sources as if they were one series.
kind: data
verified_at: 2026-09-23
verified_by: >
  Meta-CEO A seat install of W2-2 (#7737 @ac731aec) on m1: seed + dry-run + full run rc=0,
  first R2 publish 2026-09-22T23:59:54Z; audit receipt written by
  scripts/audit_options_skew_overlap.py, JSON summary keys_compared=3965 n_sign_match=2392
  n_sign_flip=1563 abs_delta_skew p50=0.0379 p90=0.167 max=3.9529; ledger shape read with
  pandas from the R2-hydrated snapshots.parquet (12,747 rows = 12,375 polygon_gex + 372
  thetadata on 2026-09-21; 34 legacy dates, 8 weekend dates / 2,875 weekend rows).
scope:
  - macro
  - engine/options_skew.py
  - scripts/build_options_skew.py
  - scripts/audit_options_skew_overlap.py
  - data/options_skew/snapshots.parquet
  - research/MARKET_ONTOLOGY_F03_SKEW_OVERLAP_RECEIPT_2026-09-22.md
confidence: verified
---

# ThetaData skew recompute diverges from the polygon_gex ledger

Measured on the store host the night the W2-2 producer went live (2026-09-22/23), on the
committed legacy ledger before any ThetaData rows were upserted over it.

| measure | value |
| --- | --- |
| legacy (polygon_gex) keys | 12,375 over 34 dates, 2026-06-21 → 2026-08-13 |
| keys both sources price | 3,965 |
| skipped `no_chain` | 8,410 = 2,875 weekend-dated rows + 5,535 weekday keys without a store chain |
| abs(delta skew) p50 / p90 / max | 0.0379 / 0.167 / 3.9529 |
| sign match / flip / zero | 2,392 / 1,563 / 0 (60% agreement) |
| worst keys | MQ (06-22…06-30, delta up to −3.95), ALT (06-23…07-02, delta up to +2.86) |

What this does and does not say:

- It does **not** say either construction is wrong; it says they are different instruments
  (tenor and strike selection, chain snapshot timing, and the legacy path's weekend as_of
  stamping all differ), so the cutover is a series break, disclosed by the per-row `source`
  column the W2-1b ledger carries.
- It does **not** block W2-3: skew is display-tier context (epistemics law: infrastructure
  ships freely; the gauntlet applies at promotion), and the polygon chain is retired by
  program ruling (MO-PAID-013).
- It **does** gate promotion: any rank/size/gate use of skew needs the parity packet first.

Receipt: `research/MARKET_ONTOLOGY_F03_SKEW_OVERLAP_RECEIPT_2026-09-22.md` (worst-10 table +
first 50 skipped keys; the JSON summary is in the seat ledger). Producer: `DEC:SKEW-ACCRUAL-ON-THE-STORE-HOST`.
