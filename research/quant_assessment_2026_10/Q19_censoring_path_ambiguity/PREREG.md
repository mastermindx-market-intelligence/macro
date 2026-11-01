# Q19 PREREG: first-passage ambiguity and censoring-aware outcome diagnostics

Status: frozen at the sha256 recorded in `FREEZE.log`. Never edited after the freeze;
any change goes only to `PREREG_AMENDMENT.md`.
Author: Opus 5.5, model ID claude-opus-5-5 (ROLE AUTHOR, quant assessment 2026-10).
Reference module: `engine/outcome_first_passage_ambiguity.py` (RESEARCH REFERENCE, NOT WIRED).
Evaluator: `research/quant_assessment_2026_10/Q19_censoring_path_ambiguity/evaluate.py`.

## 1. Question and framing

Brief Q19 asks whether outcome ledgers mislabel paths when **both barriers are crossed
inside one observation window** (the OHLC same-window first-passage problem), and whether
open, delisted, halted or missing cases are being silently dropped or treated as losses.

No cohort owner has admitted a path-dependent directional question for the options
signal-episode cohort. This study therefore makes **no edge claim and uses no signal
direction, disposition, grade or rank**. It is a direction-free *measurement-resolution
diagnostic of the price ruler*. The barriers are symmetric around the entry price, and the
question is purely: how often does a forced same-window ordering convention contradict
what finer, admissible evidence identifies? Any directional use of the diagnostic stays
blocked until an owner admits the question (DNR:KILL-OUTCOME-AUDITION stands; nothing here
auditions outcomes against a signal).

## 2. Non-duplication

EXCLUSIONS incumbents (named by the brief; not rebuilt, not edited, not imported):

* `engine/trial_ledger.py` (trial accounting): untouched. This study records exactly one
  primary trial in its own RUNS.log and does not write the trial ledger.
* `engine/calibration_hub.py` (calibration owner): untouched. No calibration, grade or
  reliability curve is produced.
* The OA-3 / qledger owners (`engine/options_alpha_exact_option_outcome.py` with its
  pending/complete/unavailable/excluded/invalid status ruler, and the qledger publication
  owners): untouched. The OA-3 status separation is the **baseline** (section 9), read only.
* `engine/options_signal_episode.py` (owner of the session ledger used here): read-only
  input. Canonical outcome IDs, statuses, horizons and the ledger bytes are never changed.

Other incumbents found by the collision grep of `_base` (all left as they are):

* `engine/grading.py` `_cushion_stop_scan` / `cushion_incidence`: closes-only scan in which
  a same-step straddle goes to the stop; complete-case `n_gradable` denominator; no censoring
  model. Used here only as the description of baseline competitor B1 (tie goes to stop).
* `engine/entry_radar/tactical_research.py` `first_touch`: labels `same_bar_ambiguous` on
  5-minute frames for one tactical study. Baseline competitor B3 (identified, unrefined).
* `engine/pb_d_evaluation.py` (`UNKNOWN_SAME_BAR_FIRST_CROSSING_ORDER`), `engine/meta_label.py`
  `triple_barrier_labels`, `engine/track_record.py` same-bar shadow fields,
  `scripts/exit_policy_study.py`, `scripts/validate_options_entry.py`,
  `engine/personality_relief_hazard.py`, `engine/tape_disagreement.py`,
  `scripts/s11_buyback_floor_phase0.py`: domain-specific uses. None is a general,
  pure, censoring-class-aware first-passage bounds + assumption-gated competing-risk
  reference, and none is modified.

Collision grep result: no `engine/*first_passage*`, `*ambiguity*` or `*censor*` module; no
`aalen`, `first_passage_ambigu` or `path_ambigu` token in `_base` engine/ or scripts/
(apart from the unrelated `cumulative_incidence` result key in `grading.py`).

**Narrow relation this study stays inside:** a new, unwired, pure reference module plus one
direction-free empirical measurement of how much same-window ordering conventions depart
from refinement by nested-horizon evidence, with an attrition denominator report. It does
not replace any incumbent's labels, does not grade, and does not feed any consumer.

## 3. Estimand

Primary estimand **E** (one trial): over observed test units, the share whose coarse
10-session window touches both barriers (coarse state `ambiguous`) **and** whose admissible
nested-horizon evidence identifies `lower_first`. That is the share of observed units on
which the **optimistic** convention (ambiguous goes to upper) is contradicted by
admissible finer evidence.

    E = #{observed test units: coarse = ambiguous and refined = lower_first} / #{observed test units}

Reported alongside E (descriptive, not verdict-bearing): the symmetric pessimistic
contradiction share E_p (coarse ambiguous, refined `upper_first`); the coarse ambiguous
share; the refined (residual) ambiguous share; identified bounds on the upper-first and
lower-first shares at both resolutions; the optimistic and pessimistic point conventions;
and full-denominator bounds that include every non-observed unit.

## 4. Unit, clocks and cohort

* **Source:** the options signal-episode session-outcome ledger
  (`data/options_signal_episode/outcomes_session.jsonl` immutable prefix plus contiguous
  `outcomes_session_parts/part-000001..000007.jsonl`), plus `episodes.jsonl` for the
  ticker and episode census, and `checkpoint.json` for the baseline record counts.
* **Unit:** one distinct underlying path, keyed by (ticker, `underlying.entry_time`) at the
  `10d` horizon. Many episodes share a path (same ticker, same entry bar), so paths are
  de-duplicated. If duplicate rows for one path disagree on entry price or extrema, the path
  is counted as `invalid` (inconsistent) rather than silently picking one. Episode-weighted
  figures are reported as secondary only.
* **Ticker:** from `episodes.jsonl` by `episode_id`. If an episode is missing there, the
  basename of `provenance.price_source` is used and the fallback is counted.
* **Input clock:** the decision is `horizon_anchor`. The entry is the first hourly bar
  (`underlying.entry_time`, `evidence.entry.bar_time`). The entry price is
  `underlying.entry_price`.
* **Output clock / question clock:** the 10d row's `matured_at` (integer epoch seconds,
  parsed from the ledger string; no wall clock is read).
* **Evidence clock:** for a finer row (eod/1d/3d/5d), max(`matured_at`,
  `provenance.source_available_at`).
* **Cohort:** every episode in `episodes.jsonl` at the pinned prefix (all anchor days in
  the pinned vintage, 2026-08-10 .. 2026-09-25, 28 distinct anchor sessions). Units are
  assigned to dates by the entry session date (UTC date of `underlying.entry_time`).
* **Price basis:** `split_adjusted_polygon_aggregate_ohlc`, 15-minute delay, 3600-second bars.
  Labels are `research_only`, shadow-only, `training_eligible=false`.

## 5. Source vintages and input pins

Data root: `/Users/chriswong/Documents/Cluade/macro-main/data` (read-only, checkout vintage
cdab6268). The files are append-only, so the evaluator reads **exactly the pinned byte
prefix** of each file, verifies its sha256, and refuses to run on a mismatch.

| path (under data/) | bytes | sha256 |
|---|---|---|
| options_signal_episode/episodes.jsonl | 45982874 | a7c53ed59a9fd268470f9b107c8b9665707e31192e23331d2ad9e736f9270652 |
| options_signal_episode/checkpoint.json | 3987 | b5370e086dba0d86f0c41e95c223b8bf30ba6b56ac8ca5b628df2b51b2392505 |
| options_signal_episode/outcomes_session.jsonl | 100471221 | fc02c3f6d224ada2179f89fcf09d63866567e4132d6d6738ccc90c012c9b6311 |
| options_signal_episode/outcomes_session_parts/part-000001.jsonl | 50327529 | a74f35d2d1f73b71e27cfdf0f5b7ae5b11e8750feb853f3eb50aeb2713c52637 |
| options_signal_episode/outcomes_session_parts/part-000002.jsonl | 50330070 | 8e80c5a5d75a253155a94aa5c8c771c21a5ac40e79f1dceeb5fa8960bdc52c40 |
| options_signal_episode/outcomes_session_parts/part-000003.jsonl | 50330244 | 02afa5176952bfb16705d3f2e87b5b3d23aa0d566616d8c14b664c6461a72bab |
| options_signal_episode/outcomes_session_parts/part-000004.jsonl | 50330449 | 52096168b293aec42ac2f4bc203615903ab8c85fac80e21af21de1dff3b3836b |
| options_signal_episode/outcomes_session_parts/part-000005.jsonl | 50330419 | bb1385bd20cf444daadf5125fe47789211d921680e6747c57137a6a57df2ad3f |
| options_signal_episode/outcomes_session_parts/part-000006.jsonl | 50329411 | 2695f96d57a1c90bab3f056a055a063deeb08928f44c3bb042f7ec384414bab8 |
| options_signal_episode/outcomes_session_parts/part-000007.jsonl | 26727345 | 0fa3ba19ab62321dcc8d11368535e18550635085debcf794da3ef2cfb67513f7 |

The finer price source behind these rows (`data/intraday/<TICKER>.parquet`) is **absent**
from the local data checkout, so no sub-hourly re-scan is possible. The only finer
evidence is the ledger's own nested horizon rows. The hourly H60 ledger
(`outcomes_h60.jsonl`) has single-bar paths in which a two-barrier touch is always
ambiguous. It serves only as a requirement-1 exemplar, not as an input to E.

Pre-freeze disclosure: the structural census read statuses, reasons, horizon sets, field
shapes, coverage counters and dates. It did **not** summarize any price, extrema, ret, mfe
or mae value. Two individual records were seen during schema inspection: one H60 row's
mfe/mae (NVDA, first anchor day) and one session row's provenance/time fields. No coarse or
refined first-passage state, barrier, ambiguity count or E value had been computed before
the freeze.

## 6. Method (fixed)

1. **Attrition classification** (module `classify_attrition`) for every episode, at the 10d
   horizon. `complete` maps to `observed`. A missing 10d row while shorter horizons exist
   maps to `administrative_pending` (10d not yet matured at the vintage). `incomplete` with
   a structural horizon reason maps to `administrative_pending`. Delisted, halted, missing
   or any unrecognised reason maps to `informative_unknown`. An episode with **no session
   row at all** maps to `informative_unknown` (never dropped, never benign). Nothing is
   admitted as non-informative in the primary analysis.
2. **Barrier width b** (chosen inside TRAIN only): the median, over de-duplicated observed
   TRAIN units, of (high10d − low10d) / (2 · entry_price). Upper = entry · (1 + b),
   lower = entry · (1 − b). One value of b; no grid, no tuning on TEST.
3. **Coarse state:** `first_passage([(high10d, low10d)], upper, lower)`, a single window.
4. **Nested refinement:** windows = cumulative extrema of the eod, 1d, 3d, 5d and 10d rows
   of the same path, in that order, passed to `first_passage(..., cumulative=True)`. A finer
   row is used only if `evidence_admissible` admits it: evidence clock ≤ question clock;
   rights_ok = (label_authority `research_only` on both rows, same `provenance.price_source`
   file); same_entry = (identical `entry_time`, `evidence.entry.bar_time` and `entry_price`);
   same_price_basis = (identical `provenance.price_basis`). If any of the four finer rows is
   missing, inadmissible or non-nested (first_passage raises `non_nested_extrema`), the unit
   keeps its coarse state and the reason is counted. The refined state comes from
   `refine_state(coarse, nested_state, admissible)`.
5. **E, E_p and bounds** on TEST observed units; `first_passage_bounds` on the full TEST
   denominator (observed + pending + informative + invalid).

## 7. Hypotheses

* H0: E < 1.0 percentage point. Forcing an optimistic same-window order at the 10-session
  resolution is immaterial relative to what nested evidence identifies.
* H1: E ≥ 1.0 pp. The optimistic convention materially overstates the upper-first share, so
  the ambiguity correction (identified states + bounds) is needed.

## 8. Practical effect bar

1.0 percentage point of all observed TEST units (absolute), judged on the lower end of the
95% block-bootstrap interval.

## 9. Baseline and competitors

* **Baseline (reproduced in `evaluate.py --mode baseline`, logged in RUNS.log):** the
  OA-3-style status ruler that separates pending / complete / unavailable / excluded /
  invalid. On this ledger, the evaluator reproduces the per-horizon status/reason mix, the
  checkpoint per-session record counts against episodes per session date, and the
  episode → horizon coverage census, using no outcome value.
* B1 pessimistic / tie-to-stop convention (incumbent `grading._cushion_stop_scan` semantics):
  ambiguous goes to lower.
* B2 optimistic convention: ambiguous goes to upper.
* B3 identified but unrefined (incumbent `tactical_research.first_touch` semantics at the
  coarse window): ambiguous stays ambiguous.
* Proposed: identified **and** refined by admissible nested evidence, with Manski bounds and
  full-denominator disclosure.

## 10. Trial family

Exactly one primary trial: E at the 10d horizon with the train-median b. Secondary
descriptive outputs, which never change the verdict: E_p; the same diagnostic at the 5d
horizon (windows eod, 1d, 3d, 5d); per-ticker contribution; an episode-weighted E; and
`cumulative_incidence` over nested horizon index (eod=0, 1d=1, 3d=3, 5d=5, 10d=10 sessions),
with 10d-pending units as administrative censoring under an asserted calendar-driven
non-informative assumption. Because interval-ambiguous events are present, that call is
expected to return `bounds_only`, and that result is reported as is.

## 11. Outcome windows

Fixed ledger horizons eod, 1d, 3d, 5d and 10d sessions from the entry bar (canonical
`horizon` / `horizon_sessions` values, unchanged). The primary window is 10d.

## 12. Chronological split

Distinct entry session dates are sorted. TRAIN = the first 14 dates, TEST = the remaining
dates. b is estimated on TRAIN only. TRAIN 10d outcome windows run into the TEST calendar
period; the only quantity fitted on TRAIN is the barrier-width quantile, and that overlap is
disclosed. The TEST set is evaluated once.

## 13. Dependence-aware uncertainty and honest N

Circular block bootstrap (module `circular_block_bootstrap`) over the ordered TEST entry
dates. One block item = all TEST units for one date. Block length 5 dates, B = 2000,
seed 19, 95% percentile interval for E (and, descriptively, E_p and the coarse ambiguous
share). Honest N is reported as distinct TEST dates, distinct tickers and distinct paths,
never as episodes or rows.

## 14. Attrition and support reporting

Reported for every analysis: episodes in the cohort; episodes with no session row; episodes
lacking a 10d row (pending); eod-only episodes; incomplete rows by reason; paths that are
invalid or inconsistent; finer-evidence fallbacks by reason (missing horizon, inadmissible
with its reason, non-nested); and the per-date unit counts. Full-denominator bounds are
always printed next to observed-only figures.

## 15. Verdict rule

* **INSUFFICIENT_DATA** if TEST observed units < 200 or TEST dates < 5, or if a pinned input
  fails its sha256 check (naming the exact missing input).
* **KEEP** (the ambiguity correction as a research reference; no edge claim) iff the 95%
  lower bound of E ≥ 1.0 pp **and** the leave-one-ticker-out minimum point E ≥ 0.5 pp
  (the result is not carried by one ticker).
* **REJECT** otherwise: the correction is immaterial at the resolution this data supports.
  The module stays a research reference either way. No production authority follows from
  any verdict.

## 16. Falsifier

Following the brief: if the result is driven by optimistic same-window ordering or by
survivorship/attrition, any inferred edge is rejected, but the ambiguity correction is
retained. Concretely, for this direction-free design: (a) E's interval is the direct
measure of how much optimistic ordering distorts the identified share; (b) if the
full-denominator bounds on the upper-first share are wider than the observed-only bounds
by more than 20 pp, the attrition share is flagged as dominating, and VERDICT.md must say
that observed-only figures cannot be read as cohort-wide; (c) E is a contradiction count
only and is never interpreted as signal accuracy.

## 17. Stop rule

One baseline run and one primary run. After the primary outcome has been read, no re-run
changes b, horizons, split, block length or the verdict rule. A re-run is permitted only to
fix a crash or a logged defect, and it is recorded in RUNS.log and PREREG_AMENDMENT.md. No
repeated holdout search.

## 18. Limitations known at the freeze

Hourly bars only, so the nested windows are coarse and residual ambiguity remains. Most rows
have `uncovered_open_seconds > 0` (pre-first-bar minutes are not observed), so crossings are
lower bounds and `neither` means "not observed to cross". The sub-hourly source is absent
locally. Labels are shadow-only and research-only. There are only 28 anchor dates. No owner
admission exists for a directional question.
