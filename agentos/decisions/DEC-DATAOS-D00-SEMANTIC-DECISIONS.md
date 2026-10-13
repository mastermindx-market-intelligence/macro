---
key: DATAOS-D00-SEMANTIC-DECISIONS
question: >
  Which semantic decisions must be frozen before any Data OS completion implementation
  result is seen, so that the identity, time, price, registry, rights and consumer waves
  are adjudicated against a fixed meaning rather than against whatever the first
  implementation happened to do?
answer: >
  Six decisions, frozen in research/data_os_completion/2026-10-13/D00_SEMANTIC_DECISIONS.md
  (PR #9133). D1: three read modes — CURRENT, RECONSTRUCT(cutoff, clock), REPLAY(output_id) —
  each with its own evidence obligation; no single as_of switch promises all three.
  D2: identity continuity from five separately defined names (security_id, listing_id,
  issuer_id, vendor symbol, storage key) with one owner each; a reused ticker is a new
  security; mergers and spin-offs are successor relations that are refused, never coerced.
  D3: economic units RAW / SADJ / TRADJ per lib/dataos/price.py plus a declared-policy
  house TOTAL_RETURN view; supported action families are named and everything else is a
  typed UNSUPPORTED_ACTION refusal. D4: fallback is context, computation refuses.
  D5: immutable generations, one pointer, receipts. D6: the frozen consumer x dataset x
  market acceptance matrix. Every request carries a view contract (purpose, identity,
  field_units, adjustment_reference, evidence_mode, coverage, refusal_reasons) before
  results exist.
rationale: >
  The masterplan's own failure analysis is that prior Data OS work produced library
  surface without a consumer and without a fixed meaning for "as of", "adjusted" and
  "same security". Freezing the meaning first makes every later wave falsifiable: a view
  that cannot state its mode, units and adjustment reference is refused rather than
  served, and cross-consumer agreement is judged against the declared view, never against
  a raw == adjusted coincidence.
alternatives:
  - option: Let the first consumer implementation (Terminal OHLC) define the semantics by example.
    why_not: >
      Repeats the measured failure: three consumers would each inherit a different implicit
      meaning and the acceptance matrix could never state agreement.
  - option: Adopt a single as_of switch that promises reconstruction and replay together.
    why_not: >
      lib/dataos/temporal.py known_at/as_of_filter supplies row eligibility under one clock
      only; replay needs a retained output and reconstruction needs the cutoff applied to
      rows, the revision set and the dependency generation. One switch conflates them.
  - option: Re-price historical books onto a single adjusted basis.
    why_not: >
      Forbidden by the programme (no repricing of historical books) and by
      DNR:KILL-CN-ADJUSTED-TAPE-LEGAL-LIMIT for CN limit arithmetic.
evidence:
  - "PR #9133 merged 2026-10-13 as 52af4108676b; research/data_os_completion/2026-10-13/D00_SEMANTIC_DECISIONS.md and research/MASTERMIND_DATA_OS_ARCHITECTURE.md (new §16 pointer) are blob-identical between head 11386de562f0 and origin/main (git rev-parse <rev>:<path> compare)."
  - "Every symbol the decision names was verified present on origin/main before freezing: KNOWN_AT_CLOCKS and PointInTimeError (lib/dataos/temporal.py); AdjustmentBasis and is_ambiguous (lib/dataos/price.py); normalize_hk_symbol, normalize_cn_symbol, security_id, listing_id, IssuerMaster, VendorAliasTable (lib/dataos/identity.py); config/identity_seams.yml; scripts/build_security_master.py; engine/basket_membership_pit.py; registry row equity.bars.daily.stocks (config/dataset_registry.yml:44); Terminal build_ohlc_json and bar_quality synthetic_open_deepstore (charting-app ingest/build_universe.py at 4005275cc816)."
  - "Chairman masterplan 2026-10-13 (Mastermind_Data_OS_Integrity_Fable_Masterplan; plan text PR #9121): 01_MASTERPLAN.md §9-§16 and 03_WORK_PACKAGES.md package D00."
affects:
  - "WS:DATA-OS-COMPLETION"
  - terminal-market-data
  - "lib/dataos/*"
  - "engine/price_ladder.py"
  - "engine/basket_membership_pit.py"
  - "config/dataset_registry.yml"
  - "terminal:ingest/*"
  - "terminal:terminal/lib/dataCache.ts"
  - "terminal:terminal/components/ChartFrameBar.tsx"
confidence: high
reversibility: costly
decided_by: coo-fable (Fable Meta-CEO seat, Data OS completion programme, Chairman delegation 2026-10-13)
decided_at: 2026-10-13
---

## Decision scope

This records the frozen meaning the implementation waves are adjudicated against. It is
not an implementation freeze, an installed production read, a rights grant or an
acceptance result. No existing program, workstream, source writer or carrier is
reassigned by it, and it grants no execution authority of its own.

## What is true now

D00 is merged and landed on `origin/main` (squash `52af4108676b`). The identity+time and
math+registry waves are in flight under `WS:DATA-OS-COMPLETION`; nothing in `lib/dataos/`
has yet been changed by the programme. The architecture document's own D1-D11 numbering
is unchanged and distinct from D00.D1-D6.

## What would reopen it

A contradicting primary source (a vendor contract that defines SADJ differently from
`lib/dataos/price.py`, a corporate-action family the three consumers need that D3 refuses),
a changed consumer contract, or an explicit Chairman or Sol reversal. A fresh session,
a lost transcript or an absent memory is not an invalidator.
