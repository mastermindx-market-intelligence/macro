# Elliott phase source compatibility finding

**Finding date:** 2026-09-11 UTC
**TOI absorption / repair date:** 2026-09-13 UTC
**Status:** `PARTIAL` source-compatibility evidence; no empirical admission, model fit, signal, production integration, or trading authority.
**Canonical owner:** `WS:TECHNICAL-OPPORTUNITY-INTELLIGENCE`, specifically W1 evidence census and W2-0 data/clock/correction/coverage/rights archaeology.
**Historical semantic head:** `macro@4de6404e4fd7c75fde212294828a1c89179444f7`.
**Current Sol review basis:** `Mastermind@9ed16bf0fcc5b47e870350ff2413ff5c8c73b447` (`mastermind.sol_skillpack.v1`, v1.0.1).

## Ruling

The historical Elliott packet established useful source-contract facts, but it did not admit a forecasting study. This record separates those facts from the sole current E0 proposal in `ELLIOTT_E0_ADMISSION_PROPOSAL_2026-09-11.md`.

The former `research/elliott_phase/**` surface is absorbed into Technical Opportunity Intelligence. It is not a standalone workstream, registry, event plane, replay plane, identity plane, outcome ledger, tactical feed, or universal score. The original contract remains only as superseded provenance with an explicit redirect.

## Verified source facts

At the pinned historical source, the existing `engine/cycle_ontology.py::detect_turns` implementation was inspected without importing the production module. The full source bytes matched Git blob `9e726868f6c218a84cd50a9f976c77c3a347ac6c`; the isolated `TurnParams`, `_yf`, and `detect_turns` definition ASTs matched their expected fingerprints.

The compact characterization probe and archived result now live at:

- `research/technical_opportunity/elliott_phase/source_contract_probe.py`
- `research/technical_opportunity/elliott_phase/source_contract_probe_results_2026-09-11.json`

The version-scoped findings are:

1. Completed synthetic turn geometry remained stable as valid observations were appended. Reuse the existing turn owner; do not build another swing engine.
2. Month/kind `turn_id` values are too coarse to serve as unique high-cadence row identity. This is a compatibility finding, not evidence that a live consumer currently loses rows.
3. Pivot and confirmation serialization are date-only, so the payload cannot attest exact intraday availability or a four-hour deadline.
4. The provisional tail carries a last-observed value in `confirmed_at`; consumers must test `provisional` rather than treating field presence as confirmation.
5. Initialization, missing-row dropping, caller-supplied ordering, declared frequency, and declared price basis are material parts of the available-at contract.
6. OHLC bars do not uniquely identify intrabar event order. A favorable target/invalidation order may not be reconstructed from open/high/low/close alone.
7. Reversal scale materially changes detected geometry. A lower threshold can create more turns without proving a different economic cycle.
8. A necessary six-point outline is not a complete Elliott interpretation. Structural endpoints, subdivisions, parent context, method convention, and truthful available-at times remain separate requirements.

## R11 metadata-only input census

The later bounded census was metadata-only and read no market-price columns. In the inspected checkout:

- all 11 named Yahoo sector files were close-only (`close_price`/`close`, `volume`, `Date`) and tipped at 2026-08-19, so they could not supply a high/low-based true-range ruler;
- all 11 named local `massive_stock_day` files had 1,254 rows spanning 2021-07-06 through 2026-07-02;
- all 11 corresponding local `stocks` paths were absent;
- each present file's SHA-256 and Parquet footer were derived from the same immutable captured byte buffer.

This is evidence about one inspected checkout, not proof that the canonical R2 production plane is stale or unavailable. Daily OHLC basis, first receipt, next-open availability, correction lineage, identity, rights, coverage, exchange calendar, and sampled five-minute observations remain unproven.

## Information-clock boundary

A chart observed while its candle is forming does not make the candle's final value available at the observation time. The research must keep three tasks distinct:

1. faithful author-time reconstruction, which may remain partially unavailable;
2. the first lawful completed-bar adaptation, with measured latency rather than backdating;
3. retrospective explanation, which has no prospective forecast authority.

A forming setup may be evaluated from completed inputs, but TOI's anticipation queue does not itself authorize unfinished-bar features.

## Canonical ownership and non-duplication

- `engine/tech_catalog.py` remains the deterministic technical primitive owner.
- Setup Species remains the scientific identity and lifecycle owner.
- Existing Trial/Evaluation owners remain the evidence, multiplicity, grading, and promotion owners.
- Market Memory owns lawful forward contracts and retained forecast evidence.
- Live Entry Radar retains tactical five-minute event ownership.
- Terminal renders owner-approved semantics and does not mint conflicting truth.
- CPI turn/phase/hazard evidence, including TR-1 and the existing CPI null/failure record, must be treated as prior house evidence rather than rediscovered under an Elliott label.
- Compression Release remains TOI's first proving vertical; Elliott E0 does not bypass W1, W2-0, W3, or the later W8 reversal boundary.

## Current sibling-carrier state at application-time reconciliation

The authority gates are no longer merely undispatched, but neither predecessor is accepted and merged as an E0 admission gate:

- Draft PR #7107 is the active TOI W1 carrier. It now has a `PARTIAL` 32-passport universe (12 P0, 10 P1, 8 P2, 2 archive), 10 residual-family dispositions, 27 exact local implementations, and five explicit gaps. It encodes `toi.ordered_path_elliott` as `P2 / toi_later_context / missing`, with controlling requirements for causal confirmed pivots (`extreme_time` separate from `known_at`), a small preregistered ordered-leg grammar, multiple candidate parses or abstain under ambiguity, and comparison against generic causal swing geometry with the same feature budget. W1 has closed the `toi.inside_bar` source-quality issue by moving the branded scenario to `P2 / toi_later_context`; it still owes the independent frozen 20-passport reproduction review, adjudication of findings, the exact validation battery, and Sol acceptance. Its live head remains an independent reconciliation input because the sibling carrier can advance without changing this record.
- Draft PR #7094 is the W2-0 carrier. Its scientific/semantic verdict remains `PARTIAL / HOLD`: current Massive daily depth and rights are evidenced, but Terminal 4H parity failed all five measured early-close cases, whole-universe names without stored five-minute history can fall back to provider-built one-hour bars beginning at 10:00 ET, a same-basis Daily+4H known-at/correction family is unproven, and the broad historical eligible-universe denominator remains partial. The semantic head has a reusable acceptance ruling; its bounded release-maintenance successor changes only the records-only CI waiver and remains draft pending exact-head trusted packs and final release readback.
- PR #7094 has not been release-accepted or merged. Only after exact-head packs, final release readback, and merge may its accepted semantic `PARTIAL / HOLD` result authorize one bounded W2 existing-owner repair/qualification wave: actual exchange close becomes load-bearing first, followed by same-basis source and denominator qualification.

These sibling carriers create no E0 admission. W1's newer method ruling also supersedes any claim that the prior single six-point/30-36-36 diagnostic is already the frozen full ordered-path challenger. Their live partial evidence strengthens the hold and replaces the stale assumption that W1/W2-0 were simply undispatched.

## Reproduction

From an authorized checkout containing the pinned historical object:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python research/technical_opportunity/elliott_phase/source_contract_probe.py
```

The probe characterizes source behavior on synthetic arrays. A passing result is not a market backtest, empirical admission, current-main integration proof, or production proof.

## Capability ledger

| Capability | State | Evidence / boundary |
|---|---|---|
| Historical turn-source characterization | `PARTIAL` | Verified for one pinned historical source fixture; not current-production proof |
| Current source/data compatibility for E0 | `PARTIAL` | W2-0 draft carrier found real depth/rights and preserved clock/parity failures; E0 pairing is not admitted |
| Ordered-path/Elliott method | `SPEC_ONLY` | W1 records a P2/missing method contract; causal grammar, parse/abstention semantics, implementation, and trial are not built |
| Complete Elliott grammar | `NOT_BUILT` | A necessary outline or small grammar does not establish a universal Elliott count |
| E0 empirical trial | `SPEC_ONLY` | `NOT_ADMITTED`; separate proposal and owner gates remain open |
| Forecasting skill | `NOT_BUILT` | No outcomes read, no model fit |
| Product or trading authority | `REJECTED_BY_DESIGN` for this record | No signal/rank/gate/size/entry/execution authority |

## Exact continuation

Complete W1's independent frozen 20-passport reproduction review, adjudication of findings, exact validation battery, and Sol acceptance on its one active carrier. Settle W2-0's exact-head trusted packs and final release readback; only after release acceptance and merge may its bounded existing-owner W2 repair/qualification wave start. Then reconcile E0 to W1's causal grammar/multiple-parse/equal-budget ruling before Trial/Evaluation admission. Until those gates close, the proposal remains `NOT_ADMITTED / HOLD_FOR_TOI_W1_AND_W2_0`, and no source refresh or market-outcome run is authorized by this record.
