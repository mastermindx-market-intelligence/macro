# Q04 PREREG — Trade-sign uncertainty and measurement-error calibration

- Brief: Q04 `Q04_signing_uncertainty` (macro quant assessment 2026-10-08).
- Role: AUTHOR. Served model: Opus 5.5 (`claude-opus-5-5`).
- Code base: staging clone of `origin/main` at `d252f919`; data vintage: `macro-main/data` at `cdab6268` (read-only, licensed retained).
- Reference module: `engine/flow_sign_uncertainty.py` (RESEARCH REFERENCE — NOT WIRED). Evaluator: `evaluate.py` in this directory.
- Procedure context read (read-only, commit unknown):
  - `Mastermind/docs/sol_skills/INDEX.md` sha256 `608aebc84a106f4e3c687f020a7f0e69af88f38e014d4664a376e2be2ddfa220`
  - `Mastermind/docs/sol_skills/ACTIVE_EXECUTION.md` sha256 `fb6a89101ad75512b971b2457f3f419704eae136afa28bac5a646ae69a6ed0dc`
  - `Mastermind/docs/sol_skills/SESSION_RELIABILITY.md` sha256 `817366c630abe31308a09c18caa5249ea4c39c83d74c130496079bb151283076`

## 1. Question

How much of the options-flow trade sign is actually identified, and can sign error be calibrated? The Lee-Ready quote rule and the tick rule assign a sign to every print. Agreement between them, or between a rule and the quote location it was built from, is self-consistency. It is not aggressor accuracy. Accuracy needs labels produced independently of the quote.

## 2. Estimands

**E1 (the brief's primary estimand — not estimable locally).** E1 has two parts, both measured against an INDEPENDENT aggressor label:
- the calibrated probability P(aggressor = buyer | print, segment);
- the error rate of the tick, quote and production signers.

Inventory result, established from file presence and schema only, before freeze:
- **No independent aggressor label exists in retained local data.** The raw tcbbo cache that would carry a vendor-disseminated `side` field, `data/options_flow/_dbento_sample.parquet` (named by `scripts/calibrate_flow_signing.py` `SAMPLE_CACHE`), is absent.
- `data/options_flow/tape_signing_sessions.jsonl` records `agreement_method = quote_rule_self_consistency` and says it has no external oracle.
- `data/flow_signals/ledger.parquet` `side` is computed from quote-rule sign shares with a 0.60 threshold (`engine/live_flow.py` `_SIDE_THRESHOLD`). Its `at_ask_share`/`at_bid_share` are execution locations, not buyers.

E1 is therefore INSUFFICIENT_DATA. The missing input is an independently sourced, per-print aggressor-side label for US-listed option prints, joined to the same prints' NBBO. Examples:
- the vendor tcbbo `side` field in `data/options_flow/_dbento_sample.parquet`;
- exchange-disseminated aggressor flags.

No calibrated buy probability is emitted.

**E2 (the one empirical comparison — identified-set width).**
- Unit: one `data/flow_signals/ledger.parquet` event, i.e. one contract coalesced over one poll batch, whose `microstructure_schema` is `options.trade_nbbo_microstructure/v1`.
- Inputs, per event:
  - c = `nbbo_premium_coverage` (null counts as 0);
  - a = `at_ask_share`, b = `at_bid_share` (each null counts as 0).

  The shares are measured on NBBO-valid prints: a two-sided, non-locked, non-crossed quote that is causally prior.
- Unidentified premium share: U = 1 − c·(a + b), clipped to [0, 1]. This is the fraction of the event's source premium whose sign is NOT identified by exact-edge execution location: inside-spread prints, outside-spread prints, and prints with no usable NBBO (no quote, locked, crossed, future quote).
- Identified net share: N_id = c·(a − b).
- Sharp location-only bounds on the net signed share: [N_id − U, N_id + U].
- Label identification: a production `~buy` label is identified-robust iff N_id − U > 0. A `~sell` label is identified-robust iff N_id + U < 0. `mixed` is not applicable.

## 3. Clocks, cohort, sources

- **Input clock.** Event `ts` (recorded string). The time segment uses the recorded wall-clock HH:MM.
  - The stored offset reads `+00:00` while the values fall in exchange hours, so the offset is ambiguous.
  - Support check: if more than 5% of cohort events fall outside wall-clock 09:30–16:15, time segmentation is declared UNIDENTIFIED. All events then go into one time cell and H1 runs on liquidity-only cells.
- **Receipt clock.** `ingested_at`. The ingest-lag distribution (ingested_at − ts) is reported as measured. No lag constant is assumed or applied.
- **Session clock.** `session_date`.
- **Output clock.** Contemporaneous per-event measurement. There is no forward return and no outcome window: the measurement is defined at the event itself.
- **Event order.** Events are kept in the retained order. Every computation is order-free, or uses a stable sort on (session_date, ts, event_id).
- **Cohort.** Every ledger row at vintage `cdab6268` with `microstructure_schema == options.trade_nbbo_microstructure/v1`. Attrition and support are reported:
  - total rows and rows without microstructure;
  - null coverage, null shares and null spread;
  - sessions.
- **Source vintages (sha256):**
  - `data/flow_signals/ledger.parquet` `c14b99cf92c29467d40a823a42e1b8974f018233c76b70d917b403f7a3898b62` (cohort input);
  - `data/options_flow/signing_gate.json` `13bf08a8983a099e6b662e060745e259f7a414b9f53990ec2d7be7fcb3b302af` (incumbent baseline record, read only for preservation);
  - `data/options_flow/tape_signing_sessions.jsonl` `7bda2ef9fa39d1680c32ad7a7c1502ee1a11831e2e43017985fc484fc59c1d98` (incumbent self-consistency record).
- **Support facts known before freeze.** These came from schema and support probes only; no U, no bound and no skill was computed.
  - 92,574 ledger rows over 44 sessions, all `signing_source = tape`.
  - Side counts: mixed 38,182, ~buy 28,304, ~sell 26,088.
  - 16,052 rows carry microstructure v1, spread over **7 sessions**.
  - One example row was printed during the schema probe.

## 4. Hypothesis, competitors, effect bar

- **H1.** A training-fitted segment-shrinkage predictor of U beats the constant training mean on held-out sessions.
  - Cells: liquidity tercile × time segment.
  - Liquidity is `spread_median_pct`, with tercile cut points fitted on training events only, plus a `liq_unknown` cell for null spread.
  - Time segments: open = 09:30–10:30, mid = 10:30–14:30, late = 14:30–16:15, other = everything else.
  - Cell means are shrunk toward the pooled training mean: m_c = (n_c·ȳ_c + k·ȳ)/(n_c + k).
  - k is chosen by leave-one-session-out CV inside training from {0, 5, 20, 80, 320}; ties go to the larger k.
- **Competitors.**
  - B0: the constant training mean, i.e. the honest base-rate abstention baseline. **H1 is M vs B0.**
  - B1: production-implicit zero uncertainty (U = 0, what a label-only consumer assumes). Reported only.
  - B2: liquidity-only shrinkage. Reported only.
- **Metric.** Event-weighted MSE on the decision cohort. Skill = 1 − MSE_M / MSE_B0.
- **Practical effect bar.** Skill ≥ 0.05 AND the 95% session-block bootstrap lower bound > 0.
- **Trial family.** Exactly one decisional test (H1); family size 1. Everything else is descriptive and non-decisional.

## 5. Split and preprocessing

- **Chronological split.** Sort the cohort's distinct sessions ascending. Training = the earliest floor(0.6·S) sessions; test = the remaining later sessions. There are no forward windows, so no embargo is needed.
- **Contract separation.** The decision cohort is the test events whose contract key (root, right, exp, strike) never appears among training events. Attrition from this filter is reported. All test events form a sensitivity cohort only.
- **Training-only fits.** Every fitted quantity is fitted on training events only: tercile edges, cell means, the pooled mean, and k.

## 6. Dependence-aware uncertainty and honest N

- Blocks are sessions. Prints and events within a session are correlated, so honest N = the number of distinct sessions, not rows.
- Uncertainty: session-block bootstrap. Test sessions are resampled with replacement, B = 2000, numpy `default_rng(4041)`, percentile 95% CI.
- Descriptive segment tables use the same session-block bootstrap over all cohort sessions.
- **Minimum honest N for a decision.** At least 4 training sessions AND at least 5 test sessions, each test session holding at least one decision-cohort event.
  - Below that, H1 is INSUFFICIENT_DATA. It is still computed and reported as a measured uncertainty report, never as a decision.
  - Disclosed before freeze: with S = 7, training = 4 and test = 3 sessions. **H1 is expected to be INSUFFICIENT_DATA under this rule.**

## 7. Descriptive outputs (non-decisional)

- Per liquidity × time cell and pooled:
  - events, sessions, gross premium;
  - mean U and premium-weighted U;
  - the share of `~buy`/`~sell` labeled premium that is NOT identified-robust, with session-block CIs.
- Quote-age (median/max ms) distributions.
- Ingest-lag distribution.
- The time-offset support check.

## 8. Falsifiers and stop rule

- **F1 (E1).** Independent labels are unavailable, so no calibrated buy probability is emitted. The module's calibration entry point refuses quote-derived labels.
- **F2 (H1).** If H1 misses the bar, or is underpowered, segment-structured abstention is not supported. Only the pooled measured uncertainty report is retained.
- **F3.** If the time-offset support check fails, time segments are declared unidentified (rule in §3).
- **Stop rule.**
  - The first complete `evaluate.py` run is the decisional run. Later runs are reproductions and must reproduce the same output sha256s.
  - No parameter, cohort, split or metric change after outputs are read. Any change goes into `PREREG_AMENDMENT.md` as a new trial identity.
  - No repeated holdout search.
- **Overall brief verdict rule.** VERDICT = INSUFFICIENT_DATA for E1, naming the missing input in §2. The H1 outcome is recorded alongside as the sidecar result: SIDECAR_KEEP if the bar is met with the minimum honest N, SIDECAR_REJECT if powered and the bar is missed, SIDECAR_INSUFFICIENT_DATA if underpowered.

## 9. Preservation (requirement 6)

- Production signing (`engine/flow_signing.py`), the calibration script (`scripts/calibrate_flow_signing.py`) and the gate file are not edited, imported or overridden.
- The negative delta-adjustment evidence is preserved verbatim as a module constant: tick minute agreement 0.556 vs delta-adjusted 0.526, `improves_direction = False`.
- The sidecar annotates and never changes a production sign.

## 10. Non-duplication

Incumbents found in `_base` (grep for `flow_signing`, `signing_gate`, `aggressor`, `sign_uncertainty`, `manski`, `partial identif`). Each is consumed, cited, or excluded; none is rebuilt.

| Incumbent | Relation |
|---|---|
| `engine/flow_signing.py` (quote/tick/delta-adjusted signing, verdict) | Untouched; not imported. Its delta-adjustment null is preserved. |
| `scripts/calibrate_flow_signing.py` + `data/options_flow/signing_gate.json` | Incumbent baseline. It cannot be rerun: its raw cache is absent (logged in RUNS.log). The gate is unchanged. |
| `scripts/calibrate_thetadata_tape_sessions.py` + `tape_signing_sessions.jsonl` | Self-consistency only; cited as such, never relabeled as accuracy. |
| `engine/live_flow.py` `_coalesce_nbbo_microstructure` (OA-1T execution location) | Consumed as retained ledger fields; not recomputed or replayed. |
| `collectors/flow_signals.py` (ledger harvest) | Data source only. |
| `engine/flow_signals_grade.py` (FS-R2 outcome grader) | No outcome grading here. |
| `engine/tape_flow.py`, `engine/options_flow.py`, `engine/options_intel_brief.py`, `scripts/build_options_prophet.py` (signing consumers) | Not touched. |
| `engine/btc_intraday_cvd.py` (crypto taker-side CVD) | Different market. Not used as option aggressor labels. |
| #8660 TP1 trades/quotes, NBBO joins, correction store, acquisition; #8659 pressure-response | No collector, replay, correction store or markout study. Q04 tests only the sign-identification contribution. |
| #8555 / #7328 / #8684 dealer pressure | No dealer-book or impact claim. |
| #8385 FS-3 calibration decision | No direction label is assigned. |

Standing DNR preserved: DNR:KILL-OUTCOME-AUDITION, DNR:KILL-LLM-ORIGINATION, DNR:KILL-FUSED-COMPOSITE, DNR:KILL-POSITIONING-FUSION, DNR:KILL-REGIME-SCORECARD, DNR:KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR, DNR:KILL-CAUSAL-DAG-ALPHA, DNR:HOLD-PSS-AF1-FINRA, DNR:HOLD-PSS-CD1-CROWDING. No language model originates any sign, score or escalation.
