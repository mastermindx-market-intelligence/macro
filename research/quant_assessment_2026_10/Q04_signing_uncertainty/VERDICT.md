# Q04 VERDICT — Trade-sign uncertainty and measurement-error calibration

**VERDICT: INSUFFICIENT_DATA**

- Sidecar (H1): `SIDECAR_INSUFFICIENT_DATA`. Underpowered by the preregistered minimum honest N.
- Served model: Opus 5.5 (`claude-opus-5-5`), role AUTHOR.
- PREREG.md sha256 `b74dae57b5050fc756a374354409740d09d49808a5d419ddd85fe032acdd88fd`, frozen 2026-10-09T09:32:25Z (FREEZE.log), before any outcome was read.
- Decisional run: RUNS.log entry `2026-10-09T09:41:28Z`, exit 0.
- Reproduction: entry `2026-10-09T09:41:58Z`, exit 0, with byte-identical output sha256s.
- Independent audit: PASS_WITH_FIXES (blockers 0, majors 1, minors 3). The finisher made wording, disclosure and logging fixes only, recorded in PREREG_AMENDMENT.md (sha256 `513141ab766b1162ab78e893e6aefa8d89e36ff2d43d7034883c5f1c4f4b7027`, witnessed in FREEZE.log). The fixes changed no estimand, formula, cohort or decision rule.
- Post-audit run: RUNS.log entry `2026-10-09T09:56:38Z`, exit 0. It records code sha256s, and its output sha256s are byte-identical to the decisional run.

**Maintained edge-sign assumption.** Every "identified" sign, bound, share and robustness count below is conditional on one assumption: an at-ask print was buyer-initiated and an at-bid print was seller-initiated. That is the quote rule's own premise, and with no independent label it is untested on retained data. Under it, the bounds [N_id − U, N_id + U] are edge-location-conditional, not sharp identified-set bounds. If any edge print is mis-signed, they are too narrow, and **U is a lower bound on the true unidentified share**. The module exposes this as `EDGE_SIGN_ASSUMPTION`.

## 1. Why INSUFFICIENT_DATA (E1, the brief's primary estimand)

The brief asks for a calibrated P(buyer-initiated | observations) and for signer accuracy. Both require an **independent** aggressor label, and retained local data at vintage `cdab6268` holds none.

**Missing input:** an independently sourced, per-print aggressor-side label for US-listed option prints, joined to the same prints' NBBO. For example, the vendor tcbbo `side` field in `data/options_flow/_dbento_sample.parquet`, the raw cache named by `scripts/calibrate_flow_signing.py`.

Proof that it is absent:

```
ls -l /Users/chriswong/Documents/Cluade/macro-main/data/options_flow/_dbento_sample.parquet   -> exit 1 (No such file or directory)
evaluate.py --mode baseline -> exit 0; results/baseline.json incumbent_raw_cache_present=false, incumbent_rerun_possible=false
```

Every agreement figure that does exist is self-consistency, not accuracy:

| Figure | Kind |
|---|---|
| `signing_gate.json`: per-trade agreement 0.7774 (size-weighted 0.8083, net-sign recovery 0.4108, n = 101,934) | tick rule vs quote rule |
| `tape_signing_sessions.jsonl`: 3 sessions, per-trade agreement 0.6715 / 0.6996 / 0.7197 | `agreement_method = quote_rule_self_consistency` |
| ledger `side` | derived from quote-rule shares (0.60 threshold) |

Falsifier F1 applies, so **no calibrated buy probability is emitted**. `calibrate_buy_probability` raises `IndependentLabelsRequired` for any quote-derived provenance. `disagreement_error_floor` reports only the identified lower bound: the two rules' error rates sum to at least their disagreement rate d, so the larger of the two errors is at least d/2. That is a bound, not an accuracy.

## 2. The one empirical comparison (E2/H1): how much of the sign execution location leaves unsigned

**Measured estimand.** U = 1 − c·(a + b) is the share of an event's premium not printed at an exact NBBO edge. Under the maintained edge-sign assumption it is the share whose sign location does not determine. Without that assumption it is a lower bound on the unidentified share.

**Cohort.** 16,052 ledger events carrying microstructure v1, over 7 sessions (2026-09-17 → 2026-09-25):
- 76,522 of 92,574 ledger rows have no microstructure;
- zero null coverage, share or spread values in the cohort.

**Split.** Train is the 4 earliest sessions (8,909 events); test is the 3 later sessions (7,143 events).
- The decision cohort is the 3,146 contract-disjoint test events: 3,997 of the test events were dropped because their contract also appears in training.
- The time-offset support check failed: 31.3% of events fall outside wall-clock 09:30–16:15, against a 5% limit. This is falsifier F3. Time segments are therefore UNIDENTIFIED, and H1 ran on liquidity-only cells, so model M is numerically the same as competitor B2.
- Tercile edges on `spread_median_pct` fitted on training data: 0.01624 and 0.03096.
- LOSO-chosen shrinkage: k = 20.

| Decision cohort (3 test sessions, 3,146 events) | MSE | Skill vs B0 [95% session-block CI] |
|---|---|---|
| B0 constant training mean (U = 0.668) | 0.14263 | — |
| M = B2 liquidity-tercile shrinkage | 0.12475 | **0.1254 [0.1069, 0.1539]** |
| B1 zero uncertainty (U = 0, what a label-only consumer assumes) | 0.48160 | M beats B1 by 0.741 [0.665, 0.785] |

| Sensitivity cohort: all 7,143 test events | Skill M vs B0 |
|---|---|
| | 0.0767 [0.0494, 0.1117] |

**Decision.** The point estimate clears the practical bar (skill ≥ 0.05, CI lower bound > 0). But honest N is 3 test sessions against the preregistered minimum of 5, so **H1 is SIDECAR_INSUFFICIENT_DATA, not KEEP**.
- A bootstrap over 3 blocks has only 10 distinct resamples, so its interval understates uncertainty. The minimum-N rule exists for exactly this case.
- F2 applies: segment-structured abstention is not supported. Only the measured uncertainty report below is retained.

## 3. Retained measured uncertainty report (descriptive; session-block CIs over 7 sessions)

| Cell | Events | Mean U [CI] | Premium-weighted U [CI] | Labeled `~buy`/`~sell` premium NOT robust to the edge-conditional bounds [CI] |
|---|---|---|---|---|
| POOLED | 16,052 | 0.652 [0.626, 0.676] | 0.591 [0.563, 0.615] | **0.763 [0.746, 0.776]** |
| tight spread | 5,689 | 0.548 [0.517, 0.579] | 0.481 [0.456, 0.504] | 0.675 [0.654, 0.703] |
| mid spread | 5,534 | 0.688 [0.656, 0.705] | 0.672 [0.644, 0.688] | 0.835 [0.795, 0.858] |
| wide spread | 4,829 | 0.734 [0.708, 0.753] | 0.735 [0.703, 0.754] | 0.849 [0.815, 0.869] |

Plain reading (each figure holds under the maintained edge-sign assumption, and each is a floor without it):
- At least about 59% of the cohort's premium was not printed at an exact edge, so execution location does not sign it.
- About 76% of the premium the production signer labels `~buy`/`~sell` sits in events whose edge-conditional bounds still straddle zero. If edge prints can be mis-signed, the true share can only be higher. Only 1,713 of 8,751 labeled events are robust to those bounds (result key `labeled_identified_robust`); without the assumption, that count is an upper bound.
- The non-edge share rises with spread width.

These are conditional measurement facts about how much of the label execution location can support. They are not evidence that the labels are wrong, they are not an accuracy figure, and they are not assumption-free identification.

Quote-age and ingest-lag distributions are reported as measured in `results/e2_summary.json`:
- quote-age max: p50 624 ms, p99 126.7 s;
- recorded ingest lag: p50 62.6 ks. The `ts` offset is ambiguous, and no lag constant is applied.

## 4. Limitations

- Microstructure fields exist for only 7 sessions, so H1 cannot reach the preregistered honest N until roughly 5 or more later test sessions accrue under the same contract. A rerun would be a new trial identity through PREREG_AMENDMENT.md.
- U is an edge-location-conditional quantity from coalesced per-event shares, and a lower bound on the unidentified share once the edge-sign assumption is relaxed. It cannot see individual prints, quote conditions or correction lineage. The print-level reference (`classify_print`, `bounds_from_prints`, `order_prints`) is implemented and tested on synthetic data only, because no admitted print-level T/Q tape is retained.
- The time-offset ambiguity (`+00:00` tag on exchange-hours values) blocks time-of-day segmentation. Requirement 5's time dimension is reported as UNIDENTIFIED, not fabricated.
- The decisional RUNS.log entries print `input raw_cache_present sha256=False` for the absent raw cache. That is a presence flag, not a hash. Those historical entries are left unedited. After the audit, evaluate.py logs it as `flag raw_cache_present=False` and opens each RUN entry with code sha256s (see the 09:56:38Z entry).
- Before the decisional run, the engine module's code identity rests on its mtime and the MANIFEST hash, because the decisional RUN entries carry no code hash. The post-audit entry closes this gap for the amended module: its outputs are byte-identical, so the wording edits changed nothing computational.
- One post-audit invocation (09:56:22Z, exit 2) was refused. The amendment's FREEZE.log witness line contained the substring `PREREG.md`, which the hash parser in evaluate.py picked up. The line was reworded and the run repeated. The refusal is kept in RUNS.log.
- No production signing, gate or consumer behavior was changed, and nothing imports the new module.
