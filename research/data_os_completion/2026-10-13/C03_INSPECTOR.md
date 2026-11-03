# C03 — cross-source agreement inspector (lane C03-1)

## Purpose

`lib/dataos/quality.py` grew a pure, deterministic inspector for the
`CheckFamily.CROSS_SOURCE` family: it decides whether two declared sources AGREE
about the same observations, and it retains every disagreement with its raw values.
It never resolves anything — no consensus, golden or preferred value is produced,
no vendor is scored, no cause is guessed. A discrepancy between two feeds is
delivered as evidence (`AgreementInspection`, one `Finding`), so the owner of the
canonical view can make the declared call.

## Law

- Masterplan §9 — the canonical view is a DECLARED answer, not a vote among feeds:
  instrument, session, currency, trade eligibility, timestamp convention,
  adjustment/reference and observation revision are compared FIRST; values only
  after, and only on actual overlapping observations in the same window.
- ARCHITECTURE §7 — the agreement vocabulary is exactly
  `AGREE · WITHIN_TOLERANCE · DISCREPANT_MINOR · DISCREPANT_MAJOR · UNRESOLVED`.
  The §7 escalation (quarantine, last-good, incident) is NOT built here.
- Interface contract — declared tolerances, same-unit quantities. D00: never
  average incompatible sources. D00.A1.3: a total-return-adjusted (TRADJ) series
  is never compared against a printed price.

## Vocabulary

- `AgreementState` — the five §7 states, value == name, in §7 order.
- `InspectionOutcome` — what the inspection could DO: `COMPARED`,
  `INCOMPATIBLE` (rows never examined), `INSUFFICIENT_OVERLAP`, `DUPLICATE_KEY`.
- `DiscrepancyCause` — exactly `SEMANTIC_DIFFERENCE` or `UNKNOWN`; there is no
  vendor-error member (C03.04: unknown causes stay unknown).

## Comparison order (frozen in `inspect_agreement`)

1. Declarations — `keys`/`value_col`/`tolerance`/`min_overlap` are keyword-only
   with no defaults; a malformed declaration raises, it is never returned.
2. Semantics — the eight `_SEMANTIC_KEYS` plus (for one source, two generations)
   `generation` are diffed first; any difference returns `INCOMPATIBLE` before the
   rows are iterated.
3. Index — each side is materialised once; a key with a `None` component is
   counted unkeyed and never compared; a repeated key is a `DUPLICATE_KEY`
   finding, not a crash.
4. Exact-key overlap only — never a nearest-date, as-of or forward-fill join.
5. Sufficiency — fewer overlapping observations than the declared `min_overlap`
   is `INSUFFICIENT_OVERLAP`; sampled dates and history depth are not reconciled
   causally (C03.03).
6. Compare — exact `Fraction` arithmetic under the declared absolute `precision`
   and relative `within`/`minor` bands, inclusive boundaries; raw values are
   retained on every `PairObservation`; a one-sided constant-ratio shape is
   reported as a `RatioStep` between two sampled keys, and never sets a cause.

## Tolerances

`AgreementTolerance(precision, within, minor)`: `precision` is absolute in the
value's unit; `within` and `minor` are relative to `max(|a|,|b|)`. Everything is
normalised to `Fraction`, so band boundaries are inclusive and exact.
`float` is refused (a `TypeError`): binary floating point cannot declare an exact
band, and an approximate band cannot judge a boundary exactly. A `float` VALUE is
accepted and read through its shortest round-trip decimal (`repr`), so `114.8`
is exactly 1148/10 and `114.8 / 57.4` is exactly 2.

## Acceptance map

| Acceptance | Proved by |
| --- | --- |
| C03.01 same-generation replays agree within precision; independent sources may retain an explicit UNRESOLVED discrepancy | `test_C03_01_same_generation_replay_agrees_within_precision`, `test_C03_01_same_generation_beyond_precision_is_major`, `test_C03_01_the_same_difference_between_independent_sources_is_within_tolerance`, `test_C03_01_independent_discrepancy_is_retained_unresolved`, `test_C03_01_band_boundaries_are_inclusive_and_exact` |
| C03.02 raw vs adjusted, auction vs consolidated are never averaged or compared into a golden price | `test_C03_02_raw_against_split_adjusted_is_incompatible`, `test_C03_02_total_return_adjusted_is_never_compared_with_a_printed_price`, `test_C03_02_closing_auction_against_consolidated_is_incompatible`, `test_C03_02_any_single_semantic_difference_is_incompatible`, `test_C03_02_two_generations_of_one_source_are_incompatible`, `test_C03_02_incompatible_rows_are_never_examined`, `test_C03_02_the_inspection_carries_no_consensus_value`, `test_C03_02_the_verdict_is_symmetric` |
| C03.03 different sampled dates or history depths never fund a causal adjustment comparison | `test_C03_03_disjoint_sampled_dates_are_insufficient_overlap`, `test_C03_03_min_overlap_is_the_declared_threshold`, `test_C03_03_deeper_history_on_one_side_never_funds_a_step`, `test_C03_03_a_step_boundary_is_the_interval_between_sampled_keys` |
| C03.04 unknown causes stay unknown — no model-written certainty, no vendor score | `test_C03_04_irregular_discrepancies_have_no_step_and_no_named_cause`, `test_C03_04_a_missing_value_is_unresolved_never_zero`, `test_C03_a_one_sided_factor_shows_a_step_but_names_no_cause`, `test_C03_finding_text_names_no_cause_or_winner` |

## What is NOT built

- No consensus, golden, preferred or reconciled value exists anywhere in the
  vocabulary; `AgreementInspection` carries no number a consumer could average.
- No vendor score, ranking or blame; `DiscrepancyCause` has two members and one
  of them is `UNKNOWN`.
- No store, queue, incident or quarantine path — the ARCHITECTURE §7 escalation
  stays with its owners; this lane only reports the agreement state.
- No production caller yet; `agreement_findings` is renderable with
  `annotation_line`/`emit_annotations` but nothing in the pipeline invokes it.
- The new names are not yet re-exported by `lib/dataos/__init__.py` (a seat act,
  not this lane's).

Evidence class: synthetic. All fixtures are declared in-memory rows; no market
data, no store, no network.
