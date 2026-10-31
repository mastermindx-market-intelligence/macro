# EW Forecast Preregistration v1 — Grey Deer × Leadership Rotation Early-Warning, product B — families C-MKT and C-RS — written 2026-10-31 — reads NO outcomes

> **PREREGISTRATION (PHASE 3 of EW-P3.T1).** This file registers two forecast families, `grey_deer_ew_mkt_v1` (C-MKT) and `grey_deer_ew_rs_v1` (C-RS), under the issue contract `grey_deer_ew_forecast_issue.v1`. It was written before any outcome was read. Its author opened no forward log, issue log, label, graded row, claims row or price row, and opened no file under `data/`. The proof is the PR's `git diff --stat` (no `data/` path) and the reader stub's test (§11), which fails on any `data/` access.
> **ORDER OF PRECEDENCE.** (1) The seat's `FROZEN:` reply, quoted verbatim in the contract banner. (2) The frozen contract body, `CLAIM_EVIDENCE_CONTRACT_v1_2026-10-31.md` (blob pinned in §1). (3) This file. Every value below restates (1) or (2), or is an operationalisation listed in §14. A difference between this file and (1) or (2) is a defect. It is repaired by a recorded seat decision, never resolved silently in favour of this file.
> **CLAIMS NO FORECAST.** Nothing here is a validated model, an issued probability or evidence that leadership deterioration predicts anything. No family grants rank, gate, size or execute authority (X1). Product A, the descriptive watch, is EW-P4 and is not scored here. Product C, policy, is out of scope.

| Field | Value |
|---|---|
| Wave | EW-P3.T1 (INCR :44), product B. It amends #10219 and is adopted by #10249. Supersedes nothing. |
| Commissioning seat | Fable CEO seat `00dea969`. Author: ORCH-P3 (Opus orchestrator), PHASE 3. |
| Lifecycle | Draft PR → independent review on the final head → the seat's merge, which is the registration and ratifies the §14 operationalisations → the records lane dates the §2 machine lines → the remaining waves follow the §11 sequence in order. |
| File name | `EW_FORECAST_PREREG_v1_2026-10-31.md`. The date is the draft date, fixed by the seat's reply. The merge date is recorded inside the file (§2), never by renaming. The name is never `..._PREREG_V3.md`. |

---

## 1. Source pins

**Blobs are primary and line numbers secondary (seat AMEND A3).** Every pin in the contract's §1 table applies unchanged. Read TL's `log_declared_budget` at :593 and `register_trials` at :694, per the contract §1 erratum. The pins below are the ones this file adds or that A3 names.

| Ref | Path | Blob | Lines used |
|---|---|---|---|
| CONTRACT | `research/grey_deer/ew_completion_20261031/CLAIM_EVIDENCE_CONTRACT_v1_2026-10-31.md` (FROZEN) | `5270e309927a8a40eb9e72bbd1bda6907a5fe800` | §4 X1–X10, §5 C-MKT, §7 C-RS, §10 SD-01–SD-23, §3.2.1 PIT counts |
| REVIEW | `research/grey_deer/reviews/EW_P3_INDEPENDENT_SCIENCE_REVIEW_2026-10-30.md` | `43682d12d9178b2cf97581de75281e0122b8f16f`, at #10219 head `ff4b0aab3f9c2e0130f4a98d20502dde257ee575` | :100, :104, :112, :115, :121, :126, :131, :135, :140 |
| INCR | `research/grey_deer/EARLY_WARNING_INTEGRATION_INCREMENT_2026-10-30.md` | `95ed92a393751e3be08804bbcb22fbbb9ae22675`, at #10219 head `ff4b0aab3f9c2e0130f4a98d20502dde257ee575` | :44 EW-P3.T1, :45 T2, :46 T3 |
| VF | `engine/vol_forecast.py` | `e2354c5a8fff803bbe1d4be61c7a57bb43c3b3d5` | :22 `realized_vol` |
| YC | `collectors/yahoo.py` | `37547ac57dc7f282a8d3d30a3434dd74f926c005` | :6–8 (`close` is the total-return-adjusted close) |
| PB11 | `research/grey_deer/PULLBACK_PREREGISTRATION_V1_1_2026-10-12.md` (FROZEN) | `53837859164ab1d33785101dc0b464272acd5704` | :423–431 features, :464 standardisation, :470 logistic fit |
| PB1 | `research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md` (FROZEN) | `49a68b5e9c6543d662044b0aa391c4b6e6e6052e` | :188 fit objective, :367 intersection-union |
| T14 | `research/grey_deer/PREREG_DRAFT_T14_LEADER_DAMAGE_2026-10-13.md` (DRAFT; superseded for this label by SD-05a, file untouched) | `178fb479d5da34c2c320b5a53ce5ea266a042c8b` | :61 full-lookback rule, :147 `log rv20`, :152 B0 rule, :153 rv baseline, :155–156 M0/M1 form |
| RDY | `research/grey_deer/RISK_RADAR_PROSPECTIVE_VALIDATION_READINESS_PREREG_2026-09-24.md` | `783eec109cebaada76e2c98f07d991a7c07b86db` | :38–48 floors, :46 cluster rule, :52–65 paired Brier and bootstrap, :67–70 calibration |
| RRS | `engine/risk_radar_scorecard.py` | `1d9d694104d26971d24642cadb6f793ec0d44fd8` | :617 `_quantile`, :631–654 `_moving_block_mean_ci` (returns `[q0.05, q0.95]`), :432 `build` |
| GPF | `engine/grey_deer_pullback_forward.py` | `bbb7ce83113bdbe6c65147beec4ca4fd896cfdbd` | :54 `FORWARD_LOG_NAME`, :381 `_prereg_matches`, :827 `data/grey_deer_pullback` |
| TL | `engine/trial_ledger.py` | `b9b444015549a691b9ab917590cc920ef6c8bb89` | :54 `DEFAULT_PATH`, :593 `log_declared_budget`, :694 `register_trials` |
| CAL | `lib/nyse_calendar.py` | `0ece6439ffe4b081ee7a268fe99b69e1de1216a3` | :121 `is_session`, :137 `sessions_between`, :488 `session_n_forward` (early closes are not modelled, :11) |

This file's own blob cannot appear inside itself. It is pinned in two places outside the file. At the PR head, `CLAIM_EVIDENCE_LEDGER_v1.md` records it. After the §2 dating, the records lane records the **registered blob**: the first blob on `main` in which both machine lines carry dates. The registered blob is the prereg input to every model fingerprint (X5). Any later edit to this file creates a new blob, so it starts a new epoch (§4 X5). A correction after dating goes to a new versioned file, never into this one.

---

## 2. Machine lines — dated once by the records lane at merge

```text
EW_P3_MERGE_DATE_UTC: UNRECORDED
EW_P3_PROSPECTIVE_START: UNRECORDED
```

- **Format.** In multiline mode, exactly one line of this file matches `^EW_P3_MERGE_DATE_UTC: (UNRECORDED|\d{4}-\d{2}-\d{2})$` and exactly one matches `^EW_P3_PROSPECTIVE_START: (UNRECORDED|\d{4}-\d{2}-\d{2})$`. More or fewer matches count as malformed (§11.1 refusal 1).
- **Who dates them.** After the seat merges this file, the seat's records lane replaces each `UNRECORDED` once, in one commit, before any outcome is read.
  - `EW_P3_MERGE_DATE_UTC` is the UTC calendar date of the merge commit on `main`.
  - `EW_P3_PROSPECTIVE_START` is the first NYSE session (CAL) **strictly after** that date.
- **Who reads them.** The reader stub (§11) parses both lines. If either is `UNRECORDED`, it refuses. If the start is not the first CAL session strictly after the merge date, it refuses.
- **Worked example (hypothetical, for checking code only).** Suppose the merge date is 2026-11-02. The start is then 2026-11-03, and the earliest-first-look lower bound (§11.2) is the close of 2027-12-31.

---

## 3. Scope — what is registered and what is not

**Registered (SD-01 = a).** Two families:

| Family | Candidate | Issue contract | Declared trial budget | Primary horizon | Descriptive horizons |
|---|---|---|---|---|---|
| `grey_deer_ew_mkt_v1` | C-MKT (contract §5) | `grey_deer_ew_forecast_issue.v1` | 3 (one per horizon; only the primary gates) | h = 21 | h = 5, h = 10 |
| `grey_deer_ew_rs_v1` | C-RS (contract §7) | `grey_deer_ew_forecast_issue.v1` | 3 (one per horizon; only the primary gates) | h = 21 | h = 5, h = 10 |

- **Multiplicity.** Holm is applied across the two primary claims, so m = 2 (SD-11a and the seat's reply).
- **C-SEC is NOT frozen and NOT registered.** Contract §6 stays a proposal. Any later C-SEC registration is a **new family**, with its own trial budget, its own model fingerprint and its own prereg. It never draws on the EW-P3 budgets (3 + 3), never reuses a fingerprint or prereg blob from this file, and never enters this file's Holm set (m = 2). The SD-19 name `grey_deer_ew_sec_v1` is **not** registered here. SD-07 and SD-08 are n/a.
- **Not this.**
  - C-RS is not LR1 H1–H3 (LR1 :74–76), and it does not use the reserved name `..._PREREG_V3.md`.
  - C-MKT does not reopen the PB11 SPY verdict.
  - C-RS does not subtract leg losses (D3). Both legs are reported side by side (§7.3).
  - T14 stays unregistered, is superseded for this label (SD-05a), and its file is untouched.
  - No categorical watch state is scored.
  - The October 2026 narrative sets no constant (X2).

---

## 4. Common rules X1–X10 (contract §4), with the adopted SD values

**X1 — Product separation.**
- Each family is a product-B issued probability. It never scores, replaces or relabels the product-A watch.
- No family grants rank, gate, size or execute authority, and no result supports a policy inference.

**X2 — October-2026 constant freeze.**
- Every constant has one of three sources: a pre-2026-10 retained table, existing frozen law, or a declared design default with its sensitivity band. October 2026 observations set none.
- **Cutoff (SD-02a).** A calibration row is admissible only if its whole feature lookback **and** its whole label window end on or before **2026-09-29**.
- **Start (SD-03a).** The calibration start is **2012-01-03** for both families.
- §5.4 gives the symmetric reading of start and cutoff (I-1).

**X3 — Partitions.**

| Partition | Rows | Status | Possible outcomes |
|---|---|---|---|
| P1-DEV | Origins 2023-01-03 → the last origin whose label ends on or before 2026-09-29 (§9) | DEVELOPMENT, RECONSTRUCTED | `DEVELOPMENT_PASS` or `DEVELOPMENT_FAIL` only |
| QUARANTINE | Every session after 2026-09-29 and before `EW_P3_PROSPECTIVE_START` | Neither calibration nor confirmation | None |
| P3-PROSPECTIVE | Issue dates from `EW_P3_PROSPECTIVE_START`, which is the first NYSE session after the UTC merge date (§2) | Prospective | The only partition that can yield VALIDATED or NOT_SUPPORTED |

**X4 — Clock chain.** The contract's X4 table is adopted unchanged. The clocks are:
`source_session`, `observed_ts`, `vendor_available_at` (UNKNOWN), `ingested_at`, `built_at`, `decision_cutoff`, `issued_at` (first writer wins), `published_at`, `served_at` and `notified_at` (both **NULL by design**), `outcome_onset`, `label_mature_at`, `graded_at` and `corrected_at`.
- **`decision_cutoff` (SD-12a).** `issued_at` must precede the next NYSE open (09:30 America/New_York) after `source_session`. A late row leaves every arm's scored set and counts as lost coverage.
- **Leads.** `lead_measurement = onset − source_session` and `lead_issued = onset − issued_at` are reported separately. `lead_delivered` is undefined, so no delivered-lead claim is possible.
- **Confirmation.** No k-session confirmation is used, so nothing is backdated.

**X5 — Model and version isolation.**
- **Receipt.** Every issued row carries `contract`, `epoch`, `family`, `issued_at`, `first_writer_wins: true` and `model_fingerprint`, plus the fields in §10.2.
- **Fingerprint.** `model_fingerprint` is the sha256 over three inputs: the issuer and reader source closure (including CAL and ST), the frozen prospective coefficient file (§9), and this file's registered blob (§1).
- **Input vintages.** The `data/yahoo/SPY.parquet` and `data/yahoo/SMH.parquet` blobs used are recorded **beside** the fingerprint, never inside it.
- **C-MKT extras.** C-MKT rows also record the matched Radar `asof`, `epoch` and `model_fingerprint` (§6.4).
- **Epochs.** A refit or fingerprint change starts a new epoch, and the maturity clock restarts. Epochs are never pooled.
- **Excluded source.** The `leadership_crack` log is not an issued-model source.

**X6 — Abstention.**
- **When.** A row abstains when its source is unqualified, rights-blocked, stale or degraded, or when any leg's close is missing at `t` or at any label session `s`.
- **No fill.** Labels are never forward-filled.
- **Meaning.** An abstention is never calm and never zero. An abstention while the event occurs counts as a miss.
- **Coverage.** Coverage of qualified inputs below 80% gives `SOURCE_LIMITED`.
- **Scoring (SD-23a, scoped by I-5).** An abstaining **arm** stays in the scored set, and the frozen B0 probability is substituted for that arm.

**X7 — Maturity, dependence and power.**
- **Floors per horizon.** ≥252 issued sessions; a span of ≥300 days; ≥200 graded rows; ≥20 events; ≥50 non-events; ≥5 overlap-aware event clusters. A cluster groups event-positive issue rows separated by no more than h positions (RDY :46).
- **C-RS extra floor.** ≥5 ratio-event clusters and ≥12 adverse outcomes (REVIEW :121).
- **Honest N.** The honest N is the number of clusters.
- **Bootstrap.** A circular moving-block bootstrap with block = h and 2000 draws.
- **Seeds (SD-15a).** `20261031 + h`, which gives 20261036, 20261041 and 20261052.
- **Power precondition (SD-14a, §8.5).** A committed synthetic size-and-power artifact must exist before any P3 read.
- **Dependence.** Families are not independent confirmations of each other.

**X8 — Verdict mapping (R&V :71).** The four classes are VALIDATED, NOT_SUPPORTED, INSUFFICIENT and NOT_EXECUTABLE, as in the contract's X8 table.
- `UNDERPOWERED` maps to INSUFFICIENT, **never** to NOT_SUPPORTED.
- `SOURCE_LIMITED` and `VOIDED:<k>` map to NOT_EXECUTABLE.
- `DEVELOPMENT_PASS` and `DEVELOPMENT_FAIL` are P1-DEV-only labels and never map to the four classes.

**X9 — Grading owner.**
- A reader in the GPG pattern grades the rows, from the label vintage that SD-17a names.
- C-MKT may reuse the RRA :273–284 label arithmetic, but not RRA's read of the current mutable store (RRA :260).
- RRS :432 remains the Radar's own readiness owner.

**X10 — Engine-lane dependency.**
- Issued rows accrue only when the nightly `daily.yml` `engine:` job runs with `ledger_lane_armed()` (RRA :50). EW-P1 is repairing that GH001-blocked path.
- Until the job runs, both families are `IMMATURE`, hence INSUFFICIENT, by construction.

**Other adopted values.**
- **SD-04a, the single leadership input.** `L_t = 1 − W_t / max(W_{t−62..t})`, where `W = SMH/SPY` on total-return closes (§5.2). Exactly one input, chosen without search.
- **SD-05a.** T14 is superseded for this label, and its file is untouched.
- **SD-06a.** C-MKT uses a standalone L2 logistic `M1 = M0 + L_t`.
- **SD-09.** C-RS uses SMH/SPY, issue-anchored, with δ = 0.05 and a descriptive band of {0.03, 0.08}.
- **SD-10a.** C-RS lives on the Grey Deer EW carrier as its own family.
- **SD-13a.** Scoring is intersection-union.
- **SD-16a.** C-MKT reports an `already_down` stratum.
- **SD-17a.** Features use the vintage present at issue. Labels use the vintage present at grading. A revision is a correction with `corrected_at` and ancestry.
- **SD-18.** Ledger placement is option (ii) plus a pointer in option (i).
- **SD-19.** The names and budgets above.
- **SD-20a.** Fit discipline, with AMEND A1 (§9).
- **SD-21a.** B0 is recomputed on the calibration rows.
- **SD-22a.** B1_RS uses no Radar covariate.

---

## 5. Shared inputs, features and fit law

**5.1 Inputs and rights.**
- **Source.** The Yahoo route stores `data/yahoo/SPY.parquet` and `data/yahoo/SMH.parquet`, column `close`.
  - That column is the total-return-adjusted close (YC :6–8), so it is the total-return basis.
  - The store also carries `Date`, `close_price` and `volume` (contract §3.2.1). `close_price` is not used.
- **Session axis.** CAL.
- **Rights.** APPROVED_BY_CHAIRMAN_ATTESTATION (`DEC:COMMERCIAL-DATA-RIGHTS-CHAIRMAN-ATTESTATION-20261023`). This attestation covers the data route only. It does not establish PIT availability, which stays an open fact (§13).
- **Same-session rule.** Both legs come from the same session close. A missing leg means ABSTAIN.

**5.2 Features.** Every feature uses closes at or before `t` and needs its full lookback (T14 :61). A window that a library function would still fill is an abstention.

| Feature | Formula | Full lookback |
|---|---|---|
| `dd63_SPY(t)` | `1 − close_t / max(close over the 63 closes ending at t)` (PB11 :429) | 63 closes, `t−62..t` |
| `log rv20_SPY(t)` | `log(realized_vol(close, 20))` (VF :22; T14 :147; PB11 :423) | 21 closes; all 20 simple returns in `(t−20, t]` finite. A non-positive `rv20` means ABSTAIN. |
| `L_t` (SD-04a) | `1 − W_t / max(W_{t−62..t})`, where `W_s = close_SMH,s / close_SPY,s` | 63 same-session ratio values |
| `RS5_t` (B2_RS only) | `log(W_t / W_{t−5})` (REVIEW :126) | 6 same-session ratio values |

`realized_vol` itself accepts a half window: VF :25 sets `min_periods = min(win, max(2, win // 2))`, which is 10 for win = 20. This file requires all 20 returns. A row with fewer is an abstention for every arm that uses `rv20`.

**5.3 Fit law (frozen PB11 :464, :470; PB1 :188).** Every fitted arm is an L2 logistic.
- **Objective.** `z = β0 + x·β`; minimise `Σ_i [log(1 + exp(z_i)) − y_i z_i] + (1/(2C)) ‖β‖²`.
- **Penalty.** `β0` is unpenalized, and `C = 1.0`.
- **Solver.** `scipy.optimize.minimize(method="L-BFGS-B")`, `gtol = 1e-8`, `maxiter = 10000`, starting at zero.
- **Standardisation.** Features are standardised with training moments (mean, and standard deviation with `ddof = 0`). Issue-time features are transformed with the same training moments.
- **Failures.** A zero training standard deviation gives `FEATURE_DEGENERATE`. Non-convergence gives `FIT_NONCONVERGENCE`. Either one voids that arm's coefficient file for that horizon. The wave records it, and the seat decides by recorded decision. There is no silent refit.
- **Horizons.** Each horizon h ∈ {5, 10, 21} has its own fit.

**5.4 Admissibility (SD-02a + SD-03a, symmetric reading — I-1).** An origin `t` is admissible for horizon `h` only if the following all hold:
- every session from its feature-lookback start through its label end `t+h` lies inside **[2012-01-03, 2026-09-29]**;
- all of those closes are present;
- its label is mature.

The first admissible origin is therefore CAL index 62 from 2012-01-03, which is **2012-04-02**. The last admissible origin for `h` is the session h sessions before 2026-09-29. The P-09 counts (contract §3.2.1) are 3,706 sessions in the window, 2,768 in 2012-01-03 → 2022-12-30, and 938 in 2023-01-03 → 2026-09-29.

**5.5 B0 rule (SD-21a; T14 :152).** `B0 = (k + 0.5) / (n + 1)`, where n is the number of admissible fit rows and k the number of events among them. It is computed per family and per horizon on exactly the rows its paired coefficient file was fit on (§9).

---

## 6. C-MKT — `grey_deer_ew_mkt_v1`

**6.1 Estimand.**
- **Instrument.** SPY, with no benchmark leg and no membership.
- **Event.** `A(t,h) = max(0, 1 − min(P_{t+1..t+h}) / P_t)`, and `E_MKT(t,h) = 1` iff `A(t,h) ≥ 0.05`. Otherwise the label is 0 once mature. An immature label is **absent, never zero**.
- **Onset.** The first `s ∈ (t, t+h]` with `P_s / P_t − 1 ≤ −0.05`.
- **Horizons.** h ∈ {5, 10, 21} NYSE sessions. h = 21 is primary (SD-11a).
- **Target identity.** The event is identical to three existing definitions: the PB11 frozen target, the RRA :273–284 grader and the RR :1326 measure. That identity licenses B1.
- **Price basis.** `close` (§5.1).

**6.2 Clock chain.**
- X4 applies.
- The matched Radar row must itself satisfy the SD-12a cutoff relative to the same `source_session`. Otherwise the row leaves every C-MKT arm's scored set and counts as lost coverage (contract §5 item 2).

**6.3 Models.**
- `M0_h`: L2 logistic of `E_MKT(·,h)` on `dd63_SPY` and `log rv20_SPY` (T14 :155–156).
- `M1_h` (the candidate): `M0_h` covariates plus `L_t`.
- Both are fit under §5.3 on the §9 rows.

**6.4 Baselines on identical rows, and the B1 segment rule.** Every arm predicts `E_MKT(t,h)` for the same `(t,h)`.

| Arm | Definition | Role at h = 21 |
|---|---|---|
| B0 | §5.5 | descriptive delta |
| M0 | §6.3 | **required comparator** |
| B1 | The incumbent Radar issued `drawdown_prob[h]`, from the Radar forward-log row with the same `asof` as `source_session`, in the **matched segment** below | **required comparator** |
| B2 | L2 logistic on `log rv20_SPY` (T14 :153) | descriptive delta |

**Identical rows.** A row is scored only if every arm has a finite probability issued before the cutoff. When an arm abstains under X6 because of its **own inputs**, SD-23a substitutes B0. B1 is handled differently, as follows.

**B1 segment rule (I-5).** The P-04 count (contract §3.2.1) found 18 epoch rows across 4 Radar fingerprints.
- **Matched segment.** It is the Radar `(epoch, model_fingerprint)` pair matched by the **first** issued C-MKT row of the current C-MKT epoch. It is recorded in that row's receipt.
- **First row unmatched.** If that first issued row has no in-cutoff Radar match, the segment is the pair matched by the first later issued row that has one, and every earlier row has no B1. If no issued row of the epoch has one, C-MKT has no B1 in that epoch. The choice depends only on issue order and Radar metadata, never on an outcome.
- **Other segments.** A C-MKT row whose same-`asof` Radar row carries a different `(epoch, model_fingerprint)` has **no B1**.
- **Missing or late.** A row with a missing or late Radar row also has no B1.
- **Consequence.** A row without B1 leaves **every** C-MKT arm's scored set, following contract §5 item 2. It is never scored with a substituted B1, because substituting B0 for a missing *comparator* would inflate the candidate's apparent skill. It counts as lost coverage, and coverage below 80% gives `SOURCE_LIMITED`.
- **No pooling.** Segments are never pooled.
- **Honest consequence.** While the Radar fingerprint keeps changing, C-MKT is likely to stay INSUFFICIENT or SOURCE_LIMITED (§15).

**6.5 Dependence and power.**
- X7 applies, with SPY event clusters. There is no sector floor.

**6.6 Missingness and rights.**
- §5.1 and X6 apply.
- P-01 and P-04 are open facts (§13). P-02 and P-03 are NOT REQUIRED under SD-04a (AMEND A2).

**6.7 Scorecard.**
- **Primary (h = 21, §8).** The IU test passes iff both of these hold at the look's Holm-adjusted level:
  - the upper bound of the mean paired Brier delta against **M0** is below 0;
  - the same upper bound against **B1** is below 0.

  In addition, the calibration-in-the-large CI of the M1 residual must contain 0.
- **Descriptive.**
  - log-loss deltas;
  - Brier deltas against B0 and B2;
  - reliability bins (deciles of issued probability);
  - abstention rate and coverage;
  - h = 5 and h = 10: the paired Brier deltas against M0, B0, B1 and B2, never a verdict;
  - the `already_down` stratum (SD-16a): `dd63_SPY(t) ≥ 0.05`;
  - `lead_measurement` and `lead_issued` for events.
- **Never reported.** Watch metrics.

**6.8 Disconfirming outcomes.** These apply at the first registered look where the floors and `POWERED_IN_PRINCIPLE` both hold. Each of the following gives **NOT_SUPPORTED**:
- the upper bound against M0 is ≥ 0;
- the upper bound against B1 is ≥ 0;
- the calibration CI excludes 0.

---

## 7. C-RS — `grey_deer_ew_rs_v1`

**7.1 Estimand (SD-09).**
- **Ratio.** `W_t = close_SMH,t / close_SPY,t` on same-session total-return closes.
- **Event.** `A_RS(t,h) = max(0, 1 − min_{s∈(t,t+h]} W_s / W_t)`, and `E_RS(t,h) = 1` iff `A_RS ≥ δ`, with **δ = 0.05**. The δ ∈ {0.03, 0.08} sensitivity is reported descriptively only.
- **Onset.** The first `s` with `W_s / W_t ≤ 1 − δ`.
- **Labels.** An immature label is absent. A missing leg at `t` or at any `s` means ABSTAIN.
- **Horizons.** h ∈ {5, 10, 21}, with h = 21 primary.

**7.2 Clock chain.**
- X4 applies.
- C-RS has no externally issued arm, so no further cutoff applies.

**7.3 Both legs (descriptive; R&V :33).** Each event reports `A_SMH`, `A_SPY` and both legs' returns from `t` to onset. Each event is classified as one of three:
- BOTH_DOWN (both returns ≤ 0);
- SECTOR_DOWN_MARKET_UP (SMH ≤ 0 < SPY);
- BOTH_UP (both > 0).

At onset the ratio has fallen by at least δ, so the fourth sign case cannot occur. No event is labelled "inflow".

**7.4 Models.**
- `M_RS_h` (the candidate): L2 logistic of `E_RS(·,h)` on the B1_RS covariates (`dd63_SPY`, `log rv20_SPY`) plus `L_t`.
- It is fit under §5.3 on the §9 rows.
- It lives in its own family on the Grey Deer EW carrier (SD-10a).

**7.5 Baselines on identical rows.** Every arm predicts `E_RS(t,h)`.

| Arm | Definition | Role at h = 21 |
|---|---|---|
| B0_RS | §5.5 on `E_RS` | descriptive delta |
| B1_RS | L2 logistic of `E_RS` on `dd63_SPY` and `log rv20_SPY`, with no Radar covariate (SD-22a) | **required comparator** |
| B2_RS | Univariate L2 logistic of `E_RS` on `RS5_t`, under §5.3 (I-3) | **required comparator** |

- **Identical rows.** As in §6.4. An arm abstaining because of its own inputs gets B0_RS (SD-23a).
- **No external arm.** C-RS has no externally issued arm, so it has no segment rule.

**7.6 Dependence and power.**
- X7 applies, plus ≥5 ratio-event clusters and ≥12 adverse outcomes.
- C-RS shares the SPY leg with C-MKT and is not an independent confirmation of it. It also shares the SMH leg with the unregistered C-SEC (contract §7 item 5).

**7.7 Missingness and rights.**
- P-01 applies to both legs from the same vintage.
- §5.1 and X6 apply.

**7.8 Scorecard.**
- **Primary (h = 21, §8).** The IU test passes iff both of these hold at the look's Holm-adjusted level:
  - the upper bound against **B1_RS** is below 0;
  - the upper bound against **B2_RS** is below 0.

  In addition, the calibration CI of the `M_RS` residual must contain 0.
- **Descriptive.**
  - the delta against B0_RS;
  - the both-legs table and the BOTH_DOWN share;
  - the δ band;
  - h = 5 and h = 10: the paired Brier deltas against B0_RS, B1_RS and B2_RS, never a verdict;
  - log-loss deltas;
  - reliability bins;
  - coverage.

**7.9 Disconfirming outcomes.** At a mature, powered look, each of the following gives **NOT_SUPPORTED**:
- the upper bound against B2_RS is ≥ 0;
- the upper bound against B1_RS is ≥ 0;
- the calibration CI excludes 0.

---

## 8. Inference

**8.1 Paired delta (RDY :52–65).** For each scored row `i`, each comparator `j` and outcome `y_i`:

`Δ_ij = (p_candidate,i − y_i)² − (p_j,i − y_i)²`

A negative mean Δ favours the candidate.

**8.2 Bootstrap.**
- **Method.** A circular moving-block bootstrap of the mean, with block = h and 2000 draws. The quantile rule is RRS :617.
- **Seed.** `20261031 + h`.
- **Shared resamples.** For each (family, h, look), one stream of resample indices is drawn from the seed. The same indices are applied to every comparator's Δ series and to the calibration residual series.
- **How the sharing is implemented.** RRS draws its indices from `random.Random(seed)`, and they depend only on the seed, `n` and the block. Calling it with the same seed on equal-length series therefore reuses one index stream. The full reader must keep the 2000 resample means, not only `[q0.05, q0.95]`, because §8.4 needs tail fractions and adjusted quantiles. The arithmetic itself is unchanged.
- **Mean as well as bound.** The reader reports the point mean as well as the bounds. Circular-block resample means are approximately centred on the sample mean (RRS truncates the last block). An upper bound below 0 therefore implies a mean below 0, up to Monte Carlo error.

**8.3 Looks (SD-15a).**
- **First look.** The first month-end at which every X7 floor holds at h = 21 for that family.
- **Number of looks.** At most 3. After the third look, the last verdict stands.
- **Alpha per look.** The base level is one-sided α = 0.05, which is the "90% upper bound", i.e. `q0.95`, the incumbent RRS convention. Look `k` uses `α_k = 0.05 / 3` (I-4).

**8.4 IU, Holm and calibration (I-4).**
- **Base level before adjustment.** The contract's "90% upper bound" (`q0.95`; contract §5 and §7, SD-13a) is the base level. The look split (§8.3) and Holm (m = 2) then tighten it, so the bound actually used is stricter than the contract's literal 90% bound. That composition is I-4, which the seat's merge ratifies.
- **Per-comparator p-value.** `p_j = #{bootstrap mean Δ_j ≥ 0} / 2000`.
- **IU p-value.** The family's IU p-value is `max_j p_j` over its required comparators. IU needs no adjustment within a family (PB1 :367).
- **Holm, m = 2.** At look `k`, the two families' IU p-values are ordered. The smaller is tested at `α_k / 2` and the larger, if the first passes, at `α_k`. Equivalently, the upper bound used is the `1 − α_k/2` or `1 − α_k` bootstrap quantile.
  - A family whose look comes before the other family's is tested at `α_k / 2` (no Holm step-down credit).
  - A family that is INSUFFICIENT or NOT_EXECUTABLE at a look still counts in m.
- **Calibration CI.** The calibration-in-the-large CI stays at the unadjusted 90% `[q0.05, q0.95]` (RDY :67–70). This is conservative against VALIDATED, because a narrower CI is more likely to exclude 0.

**8.5 Power precondition (SD-14a; I-7).**
- **Artifact.** A synthetic size-and-power artifact, committed before any P3 read, with M ≥ 400 replications per family.
- **Simulation setting.** It simulates each family at exactly the X7 floor values (including the C-RS extra floor), with dependence matching block = 21.
- **Alternative.** The alternative is a **Brier-skill fraction of 0.05** relative to each required comparator.
- **Test level.** It applies the strictest per-look level, `α_k / 2 = 0.05/6`.
- **Pass condition.** `POWERED_IN_PRINCIPLE` iff simulated power ≥ 0.80.
- **The margin is not the decision threshold.** The 0.05 margin is the power alternative only. The decision rule stays "upper bound < 0".
- **Underpowered families.** An underpowered family still accrues, but its verdict ceiling is INSUFFICIENT.

---

## 9. Fit discipline — SD-20a with seat AMEND A1

**9.1 Development fit.**
- **Rows.** Calibration window 2012-01-03 → 2022-12-30 (AMEND A1); first admissible origin 2012-04-02 (§5.4, I-1). Fit on admissible rows whose label window ends on or before **2022-12-30**. This is a purge: no development-fit label overlaps a P1-DEV label (I-2).
- **Output.** One coefficient file for all six fitted arms × three horizons, plus the B0 rates, at `research/grey_deer/ew_completion_20261031/fit/EW_COEF_DEV_v1.json`.

**9.2 P1-DEV, run once.**
- **Rows.** Origins 2023-01-03 → the last origin whose label ends on or before 2026-09-29.
- **Model.** The development coefficients only.
- **Labels.** DEVELOPMENT and RECONSTRUCTED.
- **Output.** `research/grey_deer/ew_completion_20261031/fit/EW_P1DEV_RESULT_v1.json`, holding `DEVELOPMENT_PASS` or `DEVELOPMENT_FAIL` per family and its reason code.
- **Rule (I-8).**
  - **PASS.** At h = 21, every reconstructable required comparator's one-sided 95% upper bound (`q0.95`, seed `20261031 + h`, block = h, 2000 draws) is below 0, and the calibration CI contains 0.
  - **FAIL.** Any other result, with one of these reason codes: `DEV_FLOOR` (the X7 event, non-event or cluster floor is not met), `DEV_IU`, `DEV_CALIBRATION` or `DEV_FIT` (a §5.3 failure).
  - **B1 is not reconstructable.** No PIT-issued Radar history exists before 2026-06-23, and the Radar table carries a disclosed look-ahead (PB1 :205–206). So the C-MKT development comparator set is {M0}, and B1 is recorded as `NOT_EXECUTABLE_IN_DEVELOPMENT`.
- **After a DEVELOPMENT_FAIL.** The fail is recorded in the claim-evidence ledger. The seat decides by recorded decision whether prospective accrual continues. There is **no automatic stop** and **no refit on October data**.

**9.3 Prospective fit, once.**
- **Rows.** The full calibration window 2012-01-03 → 2026-09-29 (SD-02a/SD-03a, AMEND A1); its admissible origins run from the first admissible origin 2012-04-02 (§5.4, I-1) → the last origin whose label ends on or before 2026-09-29.
- **Output.** `research/grey_deer/ew_completion_20261031/fit/EW_COEF_PROSPECTIVE_v1.json`, which is the **only** coefficient file in the fingerprint (X5). The development files are retained as development artifacts and are never fingerprinted.

---

## 10. Registered locations and the issue receipt

**10.1 Locations.** Changing a location before the first issued row requires a recorded seat decision.

| Artifact | Path | Writer |
|---|---|---|
| Issue log (append-only, keep-first on `(family, h, source_session, epoch)`) | `data/grey_deer_ew_forecast/issue_log.jsonl` | The issuer, only inside the `daily.yml` `engine:` job with `ledger_lane_armed()` (X10), following the GPF writer pattern |
| Issue refusals | `data/grey_deer_ew_forecast/issue_refusals.jsonl` | Issuer |
| Grade log | `data/grey_deer_ew_forecast/grade_log.jsonl` | Full reader (GPG pattern) |
| Coefficients and P1-DEV result | `research/grey_deer/ew_completion_20261031/fit/` (§9) | Fit wave |
| Power artifact | `research/grey_deer/ew_completion_20261031/power/EW_POWER_v1.json` | Power wave |
| Claim-evidence ledger | `research/grey_deer/ew_completion_20261031/CLAIM_EVIDENCE_LEDGER_v1.md` | Records lane |

**10.2 Receipt fields (X5 + X4).** Each issued row carries:
- the identity fields: `contract`, `epoch`, `family`, `h`, `source_session`, `built_at`, `issued_at`, `first_writer_wins: true`, `model_fingerprint`;
- the fingerprint inputs: `prereg_blob` and `coef_blob`;
- `input_vintages` (`SPY` and `SMH` blob ids, recorded beside the fingerprint);
- the per-arm probabilities and abstention reasons;
- for C-MKT only: `radar_asof`, `radar_epoch`, `radar_model_fingerprint` and `p_B1`.

`served_at` and `notified_at` are NULL.

---

## 11. Reader stub, earliest first look and sequencing (seat AMEND A4; I-6)

**11.1 The stub.** The file is `scripts/grey_deer_ew_forecast_reader.py`. It exposes `SCORER_IMPLEMENTED = False` and **always returns `NOT_EXECUTABLE`**. Its refusals are evaluated in this order, and the first that applies is returned:

| Order | Refusal | Condition | Reads |
|---|---|---|---|
| 1 | `prospective_start_unrecorded` | either §2 machine line is `UNRECORDED`, missing or malformed | this prereg only |
| 2 | `prospective_start_inconsistent` | `EW_P3_PROSPECTIVE_START` is not the first CAL session strictly after `EW_P3_MERGE_DATE_UTC` | CAL |
| 3 | `window_not_elapsed` | the registered prospective window has not reached its earliest first look (§11.2) | CAL and the clock; **no file under `data/` is opened** |
| 4 | `no_receipted_issue` | no row in the issue log carries the `grey_deer_ew_forecast_issue.v1` receipt with a `model_fingerprint` | the issue log only (issued probabilities, never prices or labels) |
| 5 | `scorer_not_implemented` | `SCORER_IMPLEMENTED` is `False` | nothing |

The stub never opens a price store, a label or a grade log, and it never scores. Its test proves the gate-3 refusal with zero `data/` access: any `open` of a `data/` path fails the test. It also proves gates 1, 2, 4 and 5 against temporary inputs.

**11.2 Earliest-first-look lower bound.**
- **Inputs.**
  - Let `S = EW_P3_PROSPECTIVE_START`.
  - `T_min = max(session_n_forward(S, 251), the first session on or after S + 300 calendar days)`. This is the 252-session and 300-day floors, if one row is issued from `S`.
  - `M = session_n_forward(T_min, 21)`. This is the h = 21 label maturity.
  - `L0` = the last NYSE session of `M`'s calendar month.
- **Rule.** The window has elapsed iff the current America/New_York time is after 16:00 on `L0`. CAL does not model early closes, so 16:00 is conservative.
- **It is only a lower bound.** Real issuance starts later (X10), and the event and cluster floors depend on outcomes. The full reader recomputes the first look from actual receipts.

**11.3 Trial-ledger registration code.**
- **Function.** `register_families(ledger)` calls `TrialLedger.log_declared_budget(3, family=<family>, reason=<reason>)` once for each of `grey_deer_ew_mkt_v1` and `grey_deer_ew_rs_v1`. Each reason string names this file and "C-MKT/C-RS primary h21; h5/h10 descriptive".
- **CLI.** A CLI flag runs it against the default ledger path.
- **Tests.** The test exercises the function only against a temporary ledger.

**11.4 CI registration.** One `.github/ci/legacy-jobs.yml` job, `grey-deer-ew-forecast-reader` (`gate: code`, `scope: exclusive`, hermetic). It covers the stub, its test, this prereg, CAL and TL.

**11.5 Sequence after merge (I-6).** Each step must complete before the next.
1. **Records lane.** It dates the §2 machine lines, appends the two declared-budget rows to `data/trial_ledger.jsonl` through `register_families` (§12), and records the registered blob in the claim-evidence ledger. All of this happens before any outcome read.
2. **Power wave.** It commits the §8.5 synthetic artifact, which reads no data.
3. **Fit wave.** Development fit once → P1-DEV once → record the result → prospective fit once → fingerprint.
4. **Issuer.** It follows the GPF pattern and refuses unless `_prereg_matches` holds against the registered blob.
5. **Full reader.** It replaces this stub's `SCORER_IMPLEMENTED = False` and must land **before the first issued row**, because the reader source is in the fingerprint (X5). The issuer refuses while the reader reports `SCORER_IMPLEMENTED = False`.
6. **X10.** EW-P1 restores the `engine:` job.

A step taken out of order is recorded as a deviation by the seat.

---

## 12. Trial-ledger registration — deviation from the packet's in-PR registration

`.github/` and `scripts/` may change in this PR, but `data/` must not, because the proof of zero outcome reads is a diff that touches no `data/` path. The registration therefore lands in two parts:
- **This PR** carries the code (`register_families`) and its test.
- **The append** to `data/trial_ledger.jsonl` (TL :54 `DEFAULT_PATH`) is a records-lane act at merge (§11.5 step 1). It is append-only through `log_declared_budget`. The ledger is never truncated or rewritten.

The `register_trials` lint covers only `validate_*` and `*_phase0/1*` script names, so the stub's name does not trigger it.

---

## 13. PIT facts (counts and metadata only; contract §3.2.1)

| Check | Status | What it means here |
|---|---|---|
| P-01 | **OPEN** for history | SPY has 8,497 rows (1993-01-29 → 2026-10-30) and SMH has 6,642 rows (2000-06-05 → 2026-10-30), from footer metadata only. History is RECONSTRUCTED, which is why P1-DEV is labelled RECONSTRUCTED. Prospective rows record their vintages (X5), so they do not depend on P-01's historical answer. |
| P-04 | **OPEN** (one constant fingerprint is refuted historically) | The forward log has 71 rows. 18 carry epoch `2026-09-23-prospective-v1`, across 4 fingerprints. This leads to the §6.4 segment rule. |
| P-09 | **ESTABLISHED for the calibration and P1-DEV windows** (contract §3.2.1); **OPEN** for future years (AMEND A2) | Session counts as in §5.4. Future years stay checkable from code: the prospective-window session count is re-derived from `lib/nyse_calendar.py` before the first issued row and at each look, because gate 3 (§11.1) depends on the 2027–2028 calendar. |
| P-02, P-03 | **NOT REQUIRED** under SD-04a (AMEND A2) | — |

P-01, P-04 and P-09 must be re-checked by counts and metadata only before the first issued row (AMEND A2). None of them is ever checked by reading a row.

---

## 14. Operationalisations for seat ratification (the seat's merge ratifies them)

Each item below fills a gap in the frozen text without changing a frozen value. A rejection before merge is repaired here. A change after merge is a new versioned prereg.

| ID | Operationalisation | Frozen text it implements |
|---|---|---|
| I-1 | Symmetric admissibility. Feature lookback and label both lie inside [2012-01-03, 2026-09-29], so the first origin is 2012-04-02. The calibration window itself stays 2012-01-03 → 2026-09-29 as AMEND A1 states; its first 62 sessions serve only as feature lookback. | SD-02a, SD-03a |
| I-2 | The development fit uses rows whose labels end on or before 2022-12-30 (purged). P1-DEV origins run 2023-01-03 → the last origin whose label ends on or before 2026-09-29. | A1, SD-20a |
| I-3 | B2_RS is a univariate L2 logistic of `E_RS` on `RS5_t`, which turns the REVIEW :126 return into a probability for Brier scoring. | contract §7 item 4, SD-13a |
| I-4 | One-sided α = 0.05 (`q0.95`); `α_k = 0.05/3` per look; Holm m = 2 using `α_k/2` and then `α_k`; an early-look family is tested at `α_k/2`; the IU p-value is the maximum of the per-comparator tail fractions; the calibration CI stays unadjusted at 90%. | SD-11a, SD-13a, SD-15a, seat reply (m = 2) |
| I-5 | The B1 matched-segment rule, including its fallback when the first issued row is unmatched (the first later issued row with an in-cutoff match fixes the segment; none means no B1 in that epoch). A row with no matched, current, in-cutoff Radar row leaves every C-MKT arm (it is not a B0 substitution). SD-23a substitution applies only to an arm abstaining because of its own inputs. | contract §5 items 2 and 4, SD-23a, X5 |
| I-6 | The reader source is in the fingerprint, so the full scorer lands before the first issue, and the issuer refuses while `SCORER_IMPLEMENTED = False`. | X5, A4 |
| I-7 | The power artifact simulates at the X7 floors (block 21), with alternative BSS = 0.05, level `α_k/2`, M ≥ 400. The margin is not the decision threshold. | SD-14a |
| I-8 | P1-DEV PASS/FAIL rule and reason codes. B1 is `NOT_EXECUTABLE_IN_DEVELOPMENT`, so the C-MKT development comparator set is {M0}. | SD-20a, A1, SD-22 note |

---

## 15. Honest limits stated in advance

1. **Nothing accrues until X10.** Until EW-P1 restores the `engine:` job, both families are IMMATURE, hence INSUFFICIENT. With one row per session from the earliest possible start, the first look is more than 13 months away (§2 worked example: 2027-12-31).
2. **B1 starvation.** The Radar fingerprint has changed 4 times within 18 epoch rows (P-04). Under §6.4, every Radar fingerprint change resets C-MKT's B1-matched coverage. C-MKT may therefore end SOURCE_LIMITED (NOT_EXECUTABLE) or INSUFFICIENT for reasons unrelated to leadership. This is reported, not engineered around. The note for the Radar owner is in the PR body.
3. **The leadership proxy is one sector.** `L_t` uses SMH only. A VALIDATED result would say nothing about other leadership sectors.
4. **Reconstructed history.** Yahoo total-return adjustments revise history, so calibration labels are RECONSTRUCTED (P-01). Prospective labels follow SD-17a corrections with ancestry.
5. **Unknown clock and no delivery.** `vendor_available_at` is UNKNOWN, and with no delivery there is no delivered-lead claim.
6. **Overlapping labels.** Labels overlap, so the honest N is the cluster count. A powered family can still be INSUFFICIENT at every look.
7. **Shared legs.** C-MKT and C-RS share the SPY leg, so neither confirms the other.

## 16. Non-goals

- Not an issuer, not a fit, not a power artifact, and not a scorer. Those are later waves (§11.5).
- No new runtime table, no qledger write and no `data/` change in this PR.
- No change to the Radar, its readiness owner (RRS :432), T13, T14, T19, LR1, LR2, LR2.1, PB1, PB11 or any results file.
- No UI, no delivery, and no rank, gate, size or execute authority.
