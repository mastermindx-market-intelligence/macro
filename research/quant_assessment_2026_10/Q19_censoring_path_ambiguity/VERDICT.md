# Q19 VERDICT: INSUFFICIENT_DATA (brief level; no admitted cohort). The exploratory trial REJECTs, and the ambiguity correction is kept as a research reference.

Brief: Q19, first-passage ambiguity and censoring-aware outcome diagnostics.
Author model: Opus 5.5 (model ID `claude-opus-5-5`, as reported by the serving environment).
Pre-registration: `PREREG.md` sha256 `dedbe342c380b950a4b367e6295ad17b09661cec15fcd06f5ebe9aba9a644af6`
(frozen in `FREEZE.log` at Fri Oct 9 10:40:45 UTC 2026, before any outcome was computed).
Amendments:
* `PREREG_AMENDMENT.md` (A1-A13 and Run discipline), sha256 `b306c8bc…`. These are the exact bytes
  RUNS.log entry 2 hashed. They were restored on the finisher pass, after Addendum B had been
  appended in place.
* `PREREG_AMENDMENT_ADDENDUM_B.md`: post-primary disclosures, moved verbatim into their own file.
* `PREREG_AMENDMENT_ADDENDUM_C.md`: finisher pass, written before the reproducibility re-run.
* All of these are hashed in `AMENDMENT_SEAL.log`, a post-hoc seal.
Primary run: `RUNS.log` entry 2, `evaluate.py --mode primary`, exit 0,
`results/primary.json` sha256 `d4ef29bf49e891dce0c3e4bc224cf4159ed461fbad9101f3cc7d87be503b5f02`.
Reproducibility re-run: `RUNS.log` entry 4, the shipped bytes (module `30083c19…`, evaluator
`10e3cbe5…`), exit 0. It produced the byte-identical `primary.json` (`d4ef29bf…`).

## Verdict

**Brief level: INSUFFICIENT_DATA.** The brief admits a cohort only after its owner explicitly
admits the path-dependent question. No owner of the options signal-episode cohort has done so.
The empirical trial below is therefore **exploratory and outside the eligibility gate**. It
supports no KEEP or REJECT on the brief's empirical question. The pure reference module and its
synthetic discriminating tests (requirements 1-6) do not depend on that gate. They are complete.

Blocked action: the owner of `engine/options_signal_episode.py` (the options signal-episode
session-outcome ledger, `data/options_signal_episode/`) explicitly admits a path-dependent
barrier first-passage question for that cohort. No agentos workstream record names this owner,
so the request goes to that module's incumbent owner in the Macro repository.
Until admission, any trial on this cohort stays exploratory.

**Exploratory trial outcome: REJECT** under PREREG section 15 (disclosed, not brief-bearing).
The pre-registered KEEP rule needs the 95% block-bootstrap lower bound of E to be at least
1.0 pp. It is 0.22 pp. The leave-one-ticker-out condition (minimum point E ≥ 0.5 pp) passes at
2.35 pp, but both conditions are required.

What this does and does not say:

* It does **not** show that the optimistic same-window convention is harmless. The point
  estimate (3.40 pp) is above the bar; the interval is too wide to establish it. The honest
  reading is "materiality not established at this resolution and sample", not "immaterial".
* As the falsifier requires (PREREG section 16), the ambiguity correction itself is retained as
  an unwired research reference. No edge, signal, grade, rank, gate or promotion claim follows.
  DNR:KILL-OUTCOME-AUDITION stands: no signal direction was used anywhere.

## Primary estimand (10d horizon, TEST only)

E = share of observed TEST paths whose 10-session window touches both barriers (coarse
`ambiguous`) and whose admissible nested-horizon evidence identifies `lower_first`. That is the
share on which the optimistic convention (ambiguous goes to upper) is contradicted.

| quantity | value |
|---|---|
| barrier half-width b (TRAIN median, 529 TRAIN observed paths) | 0.05356 |
| E point | 24 / 705 = 3.40% |
| E 95% circular block bootstrap (block 5 dates, B=2000, seed 19, 15 blocks) | [0.22%, 9.07%] |
| E_p (pessimistic contradiction, descriptive) | 15 / 705 = 2.13%, CI [1.25%, 3.44%] |
| coarse ambiguous share | 42 / 705 = 5.96%, CI [1.77%, 12.74%] |
| refined (residual) ambiguous share | 3 / 705 = 0.43% |
| LOTO minimum E (drops MU) | 2.35% |
| episode-weighted E (secondary) | 6.06% over 13,531 observed episodes |

## Baselines and the proposed correction (observed TEST paths, upper-first share)

| method | upper-first |
|---|---|
| B2 optimistic (ambiguous goes to upper) | 44.40% |
| B1 pessimistic / tie-to-stop (incumbent `grading._cushion_stop_scan` semantics) | 38.44% |
| B3 identified, unrefined (incumbent `first_touch` semantics) | bounds [38.44%, 44.40%] (width 5.96 pp) |
| Proposed: identified and refined by admissible nested evidence | bounds [40.57%, 40.99%] (width 0.43 pp) |

The refinement narrows the identified bounds from 5.96 pp to 0.43 pp. It resolved 39 of 42 coarse
ambiguous paths (24 to lower-first, 15 to upper-first); 3 stay ambiguous (1 still ambiguous
after refinement, 2 without admissible finer evidence). 49 observed TEST paths had no admissible
finer evidence and kept their coarse state. Across both splits the fallback reasons were
`eod:incomplete|decision_after_target_close` (70 paths, treated as missing per A7) and
`nested:non_nested_extrema` (1 path).

## Honest N and dependence

* 15 TEST dates with observed units (16 TEST dates in all), 56 tickers, 705 observed paths,
  1,241 TEST paths in the full denominator. Paths, not episodes, are the unit.
* The 24 contradictions are concentrated. By date: 2026-09-04 (2), 09-08 (5), 09-09 (4),
  09-10 (5), 09-11 (7), 09-17 (1); zero on the other 9 dates. By ticker: MU 8, AMD 5, MRVL 5,
  SOXX 4, QCOM 1, SMH 1. This is one semiconductor-heavy cluster over about six sessions, so the
  effective number of independent episodes is small. That is why the block-bootstrap interval
  is wide. LOTO alone cannot detect this sector-level clustering.

## Attrition and support (falsifier (b) fires)

| TEST class | paths | reason |
|---|---|---|
| observed | 705 | complete 10d row (A1) |
| informative_unknown | 402 | no session row at all (never treated as benign) |
| administrative_pending | 122 | 10d not yet matured at the vintage (never counted as a loss) |
| invalid | 12 | duplicate path rows disagree |

Full-denominator bounds on the upper-first share are [23.05%, 66.48%] (width 43.4 pp) against an
observed-only width of 0.43 pp: an excess of 43.0 pp, above the 20 pp falsifier threshold.
**Observed-only figures in this study cannot be read as cohort-wide.** The 4,093 episodes
(643 paths across all dates) with no session row dominate the uncertainty, not the ordering
convention.

The cause-specific Aalen-Johansen cumulative incidence (`cumulative_incidence`) returned
`bounds_only`, with failed conditions `informative_or_invalid_censoring_present` and
`interval_ambiguous_events_present`. That is the pre-registered expectation: no point survival
estimate is identifiable here, and none is reported. The bounds at 10 sessions are upper
[56.6%, 66.5%] and lower [13.2%, 23.0%].

## Secondary (never verdict-bearing)

At 5d (same b, finer windows eod/1d/3d): E = 5 / 812 = 0.62%, CI [0.00%, 2.13%]; coarse
ambiguous 0.86%, refined 0.12%. Shorter windows cross both barriers far less often, as expected.

## Baseline reproduction

`evaluate.py --mode baseline` (RUNS.log entry 1, exit 0, `results/baseline.json` sha256
`6fc9ec37d8d3e30dd4084a6c2b53c18a4213a17413f4f85908b9e61ec70eacc0`) reproduces the OA-3-style
status ruler on this ledger: per-horizon status/reason mix, checkpoint record counts against
episodes per session date (exactly 2x on all 28 dates), and the episode-to-horizon coverage
census. It reads no outcome value. Provenance caveat: the baseline was produced by an earlier
`evaluate.py` (`ea8e6f68…`), not the shipped evaluator, and those bytes were not preserved. It was
not re-run, because only one re-run is allowed. It feeds no verdict (Addendum C, C7).

## Provenance and amendment timing (finisher pass)

* **Module bytes.** The primary used module `bd11dc00…`. Verdict prose was later written into
  the docstring (`7852c07d…`), and the `bd11dc00` bytes were not preserved. The finisher removed
  all verdict text from the module, which now points only to this file. It then re-ran
  `--mode primary` ONCE under the shipped module and evaluator, for reproducibility only
  (Addendum C, C4; RUNS.log entry 4). `primary.json` came out byte-identical (`d4ef29bf…`), so
  the shipped code reproduces every number above. The verdict stays bound to entry 2.
* **Amendment timing cannot be witnessed.** RUNS.log entry 2 proves only that the
  `PREREG_AMENDMENT.md` bytes (`b306c8bc…`) existed when the primary started. It cannot show
  they were written before any outcome was read. The claim that A1-A13 preceded the primary is
  the author's statement. `AMENDMENT_SEAL.log` is a post-hoc seal and does not establish
  earlier timing.
* **Undated units.** `results/attrition.csv` now labels the 26 undated pending units `UNDATED`,
  not `TRAIN`. This is a label-only change: per-class totals and every verdict-bearing number
  are unchanged. RUNS.log manual entry 3 (structural diagnostic) is reproducible from the shipped
  `undated_diag.py` (`2a1687fe…`).

## Limitations

* Hourly bars only. The sub-hourly source (`data/intraday/<TICKER>.parquet`) is absent from the
  local checkout, so the only finer evidence is the ledger's own nested horizons. Residual
  ambiguity remains (3 paths), and `uncovered_open_seconds > 0` on most rows means crossings are
  lower bounds.
* 28 anchor dates, 15 informative TEST blocks; the effect sits in one sector cluster.
* TRAIN 10d windows run into the TEST calendar period. Only b is fitted on TRAIN; disclosed in
  PREREG section 12.
* 26 undated administrative-pending units (134 episodes, none observed) are excluded from both
  splits (Addendum B, B1). They are now labelled `UNDATED` in `results/attrition.csv`.
  Including them could only widen the full-denominator bounds. They are not re-dated, because
  that could move the date split (forbidden by PREREG section 17).
* No cohort owner has admitted any path-dependent question for this cohort. That is why the
  brief-level verdict is INSUFFICIENT_DATA and the trial is exploratory. The study is
  direction-free by design. Labels are research-only, shadow-only, `training_eligible=false`.
* Q19 does not depend on any sibling brief.

## Disposition

The module `engine/outcome_first_passage_ambiguity.py` stays a research reference
(`RESEARCH_ONLY = True`), unwired, imported by nothing. No production, grading, calibration,
trial-ledger or qledger change is proposed. A future owner who admits a path-dependent question
should first close the no-session-row attrition (402 TEST paths) and obtain admissible
sub-hourly evidence. Without both, any first-passage win rate on this cohort is bounds-only.
