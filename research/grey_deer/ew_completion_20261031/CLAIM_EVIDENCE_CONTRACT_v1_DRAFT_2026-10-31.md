# Claim-to-Evidence Contract v1 — DRAFT — NOT a preregistration; reads NO outcomes; claims no forecast

> **NOT A PREREGISTRATION.** This file registers nothing, freezes nothing, fits nothing and binds no trial budget. Every design value below is a PROPOSAL until the seat's `FROZEN:` reply; the preregistration is a separate PHASE 3 file.
> **READS NO OUTCOMES.** The author opened no forward log, claims row, label, graded row or scored outcome. No file under `data/` was opened. The only `data/` facts used are blob ids and names from `git ls-tree`, commit dates from `git log` on three store paths, and row COUNTS already recorded in the census.
> **CLAIMS NO FORECAST.** No candidate below is a validated model or an issued probability. None is evidence that leadership deterioration predicts anything. Nothing here changes any rank, gate, size or execute authority.

| Field | Value |
|---|---|
| Wave | EW-P3, product B: a separately issued forecast probability. Product A, the descriptive watch, is EW-P4 and is not scored here. Product C, policy, is out of scope. |
| Program | Grey Deer × Leadership Rotation Early-Warning Completion. This is an amendment to #10219, adopted by #10249. |
| Commissioning seat | Fable CEO seat `00dea969`. Author: ORCH-P3 (Opus orchestrator), PHASE 2 of the frozen ORCH-P3 commission. |
| Base | `main` at `e0566cb74e9463a808abae9b8c954c89cb9e1d84`, which contains `1d937d7e2b36` (#10249). |
| Census | GD-EW-P3-C1, taken at `48ac483c`. Every blob pin it records was re-verified identical at `e0566cb7`. |
| Governing spec | `research/grey_deer/ew_completion_20261031/RESEARCH_AND_VALIDATION.md`, blob `283f98e8e165d5064a755d4a443edb0b0b5b30ea`. This draft follows §3 (types and math), §4 items 1–7, §5 (ledger and verdict classes) and §7 (freedom clause). |
| Lifecycle | DRAFT → seat `FROZEN:` reply → PHASE 3. PHASE 3 creates the prereg file, reader stub, test, ledger entry, trial-ledger registration and legacy-jobs registration. None of those exists yet. |

**How to read this file.**
- Each candidate fills R&V §4 items 1–7 as proposals.
- Each candidate also states its disconfirming outcome and names its point-in-time (PIT) checks as separate open facts.
- Every open choice appears exactly once, as a numbered `SEAT DECIDES:` line in §10. Inline text refers to those lines as "→ SD-nn".

---

## 1. Source pins

All blob ids are at `e0566cb7`, and line numbers are in those blobs. The review blob is not on `main`. It is pinned at the #10219 Draft head `ff4b0aab3f9c2e0130f4a98d20502dde257ee575`.

| Ref | Path | Blob | Lines used |
|---|---|---|---|
| R&V | `research/grey_deer/ew_completion_20261031/RESEARCH_AND_VALIDATION.md` | `283f98e8e165d5064a755d4a443edb0b0b5b30ea` | :3, :11, :13–16, :33–37, :39–51, :53–55, :57–71, :86–88 |
| REVIEW | `research/grey_deer/reviews/EW_P3_INDEPENDENT_SCIENCE_REVIEW_2026-10-30.md` (#10219 head) | `43682d12d9178b2cf97581de75281e0122b8f16f` | :24, :100, :104–106, :112, :115, :121, :125–127, :131, :135–136, :140, :144 |
| INCR | `research/grey_deer/EARLY_WARNING_INTEGRATION_INCREMENT_2026-10-30.md` (#10219 head) | `95ed92a393751e3be08804bbcb22fbbb9ae22675` | :44 EW-P3.T1, :45 T2, :46 T3 |
| PB1 | `research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md` (FROZEN) | `49a68b5e9c6543d662044b0aa391c4b6e6e6052e` | :198–206 (INC radar arm, look-ahead disclosure), :315 (`b_h`), :367 (intersection-union) |
| PB11 | `research/grey_deer/PULLBACK_PREREGISTRATION_V1_1_2026-10-12.md` (FROZEN) | `53837859164ab1d33785101dc0b464272acd5704` | :360–371 frozen target `A_i(t,h)`, `Y_i(t,h)` |
| T14 | `research/grey_deer/PREREG_DRAFT_T14_LEADER_DAMAGE_2026-10-13.md` (DRAFT) | `178fb479d5da34c2c320b5a53ce5ea266a042c8b` | :9, :17–25, :31, :40, :59, :101–102, :150–160, :186–197 |
| T13 | `research/grey_deer/PREREG_DRAFT_T13_MECHANISMS_2026-10-13.md` (DRAFT) | `a56e7f6a664ef3beb0b2048b12a2a4e6795e65bd` | :8, :152–154 (not reused; named to avoid duplication) |
| T19 | `research/grey_deer/PREREG_DRAFT_T19_COSTED_PROTECTION_2026-10-13.md` (DRAFT) | `ed9f68d756ddc3993b6093620170b853f47cdfb5` | :24 (`issued_at = logged_at` UTC precedent), :232 |
| LR1 | `research/LEADERSHIP_ROTATION_PREREG_V1.md` (FROZEN) | `9d1313e0fc0c5c9720dc1aeb16c9ebf273d70abe` | :74–76, :113–116, :121, :130–131, :140, :163, :180, :183–192, :216–223, :283–285, :311–312 |
| LR2 | `research/LEADERSHIP_ROTATION_PREREG_V2.md` (FROZEN) | `1fcd151cfc4cdeb321789feb50d3fbb127cce056` | :27–30, :95–97 |
| LR21 | `research/LEADERSHIP_ROTATION_PREREG_V2_1.md` (FROZEN) | `8f48509b65c70f7f3786402cba9b21940a907e83` | :31, :35–36, :45–46, :70–71 |
| RDY | `research/grey_deer/RISK_RADAR_PROSPECTIVE_VALIDATION_READINESS_PREREG_2026-09-24.md` | `783eec109cebaada76e2c98f07d991a7c07b86db` | :38–48 floors, :52–65 paired Brier and bootstrap |
| DR | `research/DEFENSIVE_ROTATION.md` | `e0668e5a6c24c91f1d10d4762f7a9687532668f9` | the FAILED six-part gate, as summarised at R&V :11 |
| GD1 | `research/grey_deer/gd1/GD1_CAUSAL_HYPOTHESIS_LEDGER.md` | `160fc8f9f2c958bf184b4e8271cfa1efa26d4eb4` | row schema (ledger option (i)) |
| GD1C | `research/grey_deer/gd1c/GD1C_GATE_SCORECARD.csv` | `6117738b9106661363a326b1e374f985576108da` | :2 ("PIT cohort membership is not reconstructable for 2016-01-04..2026-07-31") |
| RRA | `engine/risk_radar_audit.py` | `5e11f8f59ee15d6b453b09fbaf56916879b9f73d` | :29–31, :37–47, :50, :102–152, :207, :224, :260, :269–285 |
| RR | `engine/risk_radar.py` | `94222d44ec102e728da5443e2082da73ad29f17f` | :228–240 (`_PROB_CAL`, `_PROB_BASE`), :1306–1326 (`_drawdown_prob`, measure string) |
| LC | `engine/leadership_crack.py` | `cb0a3f468ac1bf2267fb6d0ee57d378b293d3c0b` | :6–20, :40, :78–87, :96–112, :135, :232–290, :375–393, :404–430 |
| TL | `engine/trial_ledger.py` | `b9b444015549a691b9ab917590cc920ef6c8bb89` | :204 `log_declared_budget`, :298 `register_trials` |
| GPF | `engine/grey_deer_pullback_forward.py` | `bbb7ce83113bdbe6c65147beec4ca4fd896cfdbd` | :232 `score_asof`, :381 `_prereg_matches`, :541 `_append_issue_rows` (issuer pattern) |
| GPG | `engine/grey_deer_pullback_forward_grade.py` | `250f20c078c52a3f078752a24af222c5b67758a9` | :236 `_refusal`, :260 `_gate_refusal`, :310 `grade` (grader pattern) |
| RRS | `engine/risk_radar_scorecard.py` | `1d9d694104d26971d24642cadb6f793ec0d44fd8` | :432 `build` (`risk_radar_prospective_validation_readiness.v1`) |
| LRI | `scripts/leadership_rotation_inference.py` | `1f377832625db0895516603b2d1bb5cf7a9677c8` | `verdict()` (LR21 :70–71) |
| CAL | `lib/nyse_calendar.py` | `0ece6439ffe4b081ee7a268fe99b69e1de1216a3` | NYSE session axis |
| ST | `lib/store.py` | `3a0985944f534be7d771c926d73eb49f53aba140` | store reader used by RRA :260 |

---

## 2. Three defects in the independent review, and how this contract corrects them

R&V :16 records that the independent review requested amendments because its protocol contained three defects. This contract does not copy any of them.

| # | Defect (R&V :16) | Where it appeared | Correction in this contract |
|---|---|---|---|
| D1 | A market forecast was used as the baseline for sector targets. | REVIEW :125 (B1 conditions sector events on the issued Radar SPY probability). REVIEW :131 (primary endpoint "vs B1 baseline on E_XCESS"). | The Radar's `drawdown_prob` is used **only** in C-MKT, and only as a comparator for the SPY event. There, target identity is proven three ways: PB11 :365–370, the RRA :273–284 grader, and the RR :228 / :1326 measure ">=5% SPY pullback". For C-SEC and C-RS, every baseline is a probability **of that sector or ratio event itself**, fit to that event. Market information enters only as covariates inside such a model (→ SD-22). The Radar SPY probability is never the sector baseline. |
| D2 | Brier and log loss were proposed for a categorical WATCH. | REVIEW :131 ("paired Brier skill of `CONFIRMED` watch"). | No categorical state is scored by Brier or log loss here. That covers the `leadership_crack` INTACT / CRACKING / BROKEN state (LC :14–18) and the Radar state. A categorical state may appear only as an **input** to a separately versioned issued probability (→ SD-04 option c). Watch scoring belongs to product A (EW-P4) and follows R&V :35. |
| D3 | Independently timed maximum losses were subtracted. | REVIEW :106 (`EXCESS = loss_SEC − loss_SPY`). | C-RS computes the drawdown on the **same-clock ratio trajectory** `W_t = P_SMH,t / P_SPY,t`, under a registered peak rule (R&V :34; → SD-09). Leg losses are shown side by side and never subtracted. Each event is classified BOTH_DOWN, SECTOR_DOWN_MARKET_UP or BOTH_UP, and is never called inflow or outflow (R&V :33). |

---

## 3. What can legally and what can factually be known

Rights and point-in-time (PIT) availability are **separate questions**. Settling the rights does not establish any PIT fact.

### 3.1 Rights

Rights follow the standing Chairman attestation `DEC:COMMERCIAL-DATA-RIGHTS-CHAIRMAN-ATTESTATION-20261023`.

| Source route | Status | Used by |
|---|---|---|
| Yahoo / yfinance data route. The attestation covers the data route, not only the library licence. | APPROVED_BY_CHAIRMAN_ATTESTATION | Every candidate, through `data/yahoo/*.parquet` |
| Massive / Polygon | APPROVED_BY_CHAIRMAN_ATTESTATION | No candidate requires it. It is an optional independent price source for the P-06 check. |
| Tiingo | APPROVED_BY_CHAIRMAN_ATTESTATION | No candidate requires it. Access and enrollment are an open fact (P-07). |
| ThetaData options | APPROVED_BY_CHAIRMAN_ATTESTATION | Not used by any candidate. |
| Writer of `data/baskets/ohlcv/*` (member closes) | **OPEN.** This draft does not establish which provider route writes these files, so the attestation cannot yet be applied. | Only if SD-04 picks option (c). |

### 3.2 Per-store PIT availability

Each row below is an OPEN fact. None is assumed. PHASE 3 or later must check each one, using counts and metadata only, before any read.

| Id | Store (blob at e0566cb7) | What would have to be true | What is witnessed now | Consequence if not established |
|---|---|---|---|---|
| P-01 | `data/yahoo/SPY.parquet` `aa8076350333646730bc304de9a528c6c602a712`, `SMH.parquet` `8ee05c76bdacafbd020cb8880e83eaaa96b1b30b`, `XLK.parquet` `05af6a0d45b23e1e0de10831090da8f378b38046`, `QQQ.parquet` `7684895288699b6af619f4d9820fb5ed2ad3f547` | (a) The vendor `available_at` for each close is known. (b) The as-of-t vintage of total-return-adjusted closes can be recovered. Adjustment rewrites history at each distribution, so the current file is not the as-of-t file. (c) There is one ingested vintage per session. | (a) UNKNOWN. (b) This clone is shallow, with its boundary at 2026-08-21. In it, 75 commits touch `SPY.parquet` and 75 touch `SMH.parquet`, from 2026-08-23 to 2026-10-30. Earlier vintages are OPEN (unshallow remote, R2, or pre-rewrite history), not absent. (c) OPEN. | Reconstructed history is labelled RECONSTRUCTED and is never relabelled original PIT (R&V :48). Prospective rows record the blob of each vintage they use (X5, SD-17). |
| P-02 | `data/baskets/membership.json` `42149e59b72987f8510df149322c41b266aa6f92` | The cohort membership known at each historical session can be recovered. | Three commits are visible, from 2026-08-23 to 2026-10-12. A `removed` field exists (LC :109), but add dates are OPEN. GD1C :2 says PIT membership is not reconstructable for 2016-01-04..2026-07-31. | Member-based inputs are non-PIT before prospective issue. This matters only if SD-04 picks option (c). |
| P-03 | `data/baskets/ohlcv/<member>.parquet` (LC :82–83) | The provider route and the vintage chain of member closes are known. | OPEN (see the rights table). | Same as P-02. |
| P-04 | `data/risk_radar/forward_log.jsonl` (census count: 71 rows, 2026-06-23→2026-10-20; blob `a967f5b4…`) | The rows used as C-MKT comparator B1 carry epoch `2026-09-23-prospective-v1`, a first-writer `issued_at` and one constant `model_fingerprint` (RRA :37–38, :139–152, :224). | The census count of rows under the current fingerprint is OPEN. Git commit time is the independent first-writer witness. | B1 rows from other epochs or fingerprints are never pooled (R&V :14, :63). Rows without B1 are excluded from every arm of C-MKT. |
| P-05 | `data/leadership_crack/forward_log.jsonl` (census count: 45 rows; blob `914703a1…`) | — | Rows carry `logged_at` only, with no model fingerprint or source hash (LC :424–427). | These rows can never be issued-model rows. They are display records only. |
| P-06 | `data/massive`, `data/massive_stock_day`, `data/polygon`, `data/polygon_universe` (directory names only) | Daily bars for SPY, SMH and XLK exist. The history depth, the unadjusted-versus-adjusted basis, the corporate-action records and any as-of vintages are known. | OPEN. The directories were not opened. | Optional. These would provide an independent measure of the Yahoo revision effect. |
| P-07 | Tiingo (no `data/tiingo` directory at e0566cb7) | Authenticated access and technical enrollment are in place. | OPEN. | Optional. |
| P-08 | `data/pit_release_log`, `data/pit_replay` (directory names only) | Either one covers equity price vintages. | OPEN. | Optional. If it covers them, it could close part of P-01(b). |
| P-09 | NYSE calendar (CAL) | The holidays and early closes for the calibration and prospective windows are correct. Only the US calendar applies, since all three instruments are NYSE-listed. CN, HK and CA (R&V :48) do not apply. | Checkable from code. Not yet checked. | A wrong session axis voids the labels for the affected rows (`VOIDED:calendar`). |

---

## 4. Rules common to every candidate

**X1 — Product separation.**
- Each candidate is a product-B issued probability.
- No candidate scores, replaces or relabels the product-A watch.
- No candidate grants rank, gate, size or execute authority (R&V :37).
- No result supports a policy inference.

**X2 — The October-2026 constant-freeze law** (REVIEW :24, :100; R&V :45).
- Every numeric constant must come from one of three sources: (i) a pre-2026-10 retained published table, (ii) existing frozen law, or (iii) a declared design default with its sensitivity band. The constants covered include thresholds, δ, coefficients, margins, base rates, floors and looks.
- October 2026 observations may not set any constant.
- A calibration row is admissible only if its whole label window and feature lookback end on or before the cutoff (→ SD-02).
- Hypotheses discovered in October are confirmed only on later prospective rows that no one has seen.

**X3 — Partitions.** This follows the LR1 :283–285 pattern.
- **P1-DEV** uses reconstructed history up to the cutoff. It is labelled DEVELOPMENT and RECONSTRUCTED, and can yield only DEVELOPMENT_PASS or DEVELOPMENT_FAIL (→ SD-20).
- **QUARANTINE** covers every session after the cutoff up to the prospective start. These rows are neither calibration nor confirmation.
- **P3-PROSPECTIVE** covers issue dates from the first NYSE session after the UTC date on which the PHASE 3 prereg merges. It is the only partition that can yield VALIDATED or NOT_SUPPORTED.

**X4 — Clock chain** (R&V :44; REVIEW :115).

| Clock | Meaning | Witness | Status |
|---|---|---|---|
| `source_session` | NYSE session `t` whose close is the last input | CAL | witnessable |
| `observed_ts` | Close time of `t` (16:00 America/New_York, or the early-close time) | CAL | witnessable |
| `vendor_available_at` | When the vendor first served the `t` close | Yahoo does not record it | UNKNOWN (permitted by R&V :44) |
| `ingested_at` | First commit time of the `data/yahoo` vintage containing `t` | git (P-01) | Witnessed only inside the visible vintage chain |
| `built_at` | Issuer run start | issue receipt (X5) | To be written in PHASE 3 |
| `decision_cutoff` | Latest valid issue time for `t` | frozen rule (→ SD-12) | Proposal |
| `issued_at` | First-writer UTC time of the row; first writer wins | issue receipt | To be written |
| `published_at` | Commit time of the row on `main` | git | To be witnessed |
| `served_at`, `notified_at` | Product B is neither served nor delivered under this contract | — | **NULL by design.** No delivered-lead claim is possible. |
| `outcome_onset` | First session `s ∈ (t, t+h]` at which the event condition holds | reader | Computed at grading |
| `label_mature_at` | Close of session `t+h` | CAL | Computed |
| `graded_at`, `corrected_at` | Grader run time, and the time of any revision (with its ancestry) | grade receipt | To be written |

The leads are measured separately:
- `lead_measurement = onset − source_session`
- `lead_issued = onset − issued_at`
- `lead_delivered` is undefined, because there is no delivery.

No candidate uses k-session confirmation, so no confirmation is backdated. A later variant that does use confirmation takes the confirmation session as its `source_session`.

**X5 — Model and version isolation.** This copies the incumbent pattern in RRA :102–152.
- Every issued row carries a receipt with these fields: `contract`, `epoch`, `family`, `issued_at`, `first_writer_wins: true`, and `model_fingerprint`.
- `model_fingerprint` is the sha256 of three things: the issuer and reader source closure (including CAL and ST), the frozen coefficient file, and the prereg blob.
- **Input vintages are recorded beside the fingerprint, never inside it.** These are the `data/yahoo/<T>.parquet` blobs used. If they entered the fingerprint, every nightly data update would split the cohort (RRA :39–40 states the same rationale).
- C-MKT rows also record the matched Radar `asof` and that row's `model_fingerprint`.
- If SD-04 picks option (c), rows also record the membership blob and the LC blob.
- Any refit or fingerprint change starts a new epoch, and the maturity clock restarts. Epochs are never pooled (R&V :14, :63).
- The existing `leadership_crack` log cannot serve as issued-model rows (P-05).
- Each family is registered with a declared budget through TL :204 and :298, in PHASE 3 only (→ SD-19).

**X6 — Abstention** (REVIEW :112, :135).
- A row ABSTAINS when its source is unqualified, rights-blocked, stale or degraded, or when any leg's close is missing at `t` or at any `s`.
- Labels are never forward-filled. The display ffill at LC :135 does not apply to labels.
- An abstention is never calm and never zero.
- Abstention-during-event counts as a miss.
- Coverage of qualified inputs below 80% gives `SOURCE_LIMITED`.
- The scoring treatment of abstained rows is set by → SD-23.

**X7 — Maturity, dependence and power.**
- **Floors.** Each horizon inherits the Radar maturity floors (RDY :38–48; R&V :55):
  - ≥252 issued sessions;
  - a span of ≥300 days;
  - ≥200 graded rows;
  - ≥20 events and ≥50 non-events;
  - ≥5 overlap-aware event clusters, defined as at RDY :46.
- **Extra floor for C-SEC and C-RS** (REVIEW :121): ≥5 sector or ratio event clusters, and ≥12 adverse outcomes.
- **Honest N** is the cluster count, never the row count.
- **Bootstrap.** Inference uses a circular moving-block bootstrap with block = h and 2000 draws (RDY :61–65). The seed family is set by → SD-15.
- **Power precondition.** A committed synthetic size-and-power artifact must exist before any P3 read, with M ≥ 400 replications. Each family must reach `POWERED_IN_PRINCIPLE`, following the LR21 :35 pattern (→ SD-14).
- **Multiplicity.** Holm is applied across the primary claims of the frozen families (→ SD-11). Secondary horizons are descriptive. Looks follow → SD-15.
- **Dependence between families.** C-SEC and C-RS share the SMH leg, so neither confirms the other.

**X8 — Verdict mapping.** This maps onto R&V :71, using LR21 :45–46 and REVIEW :140.

| Class | Arises from | Condition |
|---|---|---|
| VALIDATED | — | Requires all of the following: the P3 partition only; every floor met; `POWERED_IN_PRINCIPLE`; the SD-13 intersection-union (IU) test passes at the primary horizon after Holm; and the calibration-in-the-large CI contains 0. |
| NOT_SUPPORTED | `NOT_SUPPORTED` | The floors and `POWERED_IN_PRINCIPLE` are met, and either the IU test fails (any required upper bound ≥ 0) or the calibration-in-the-large CI excludes 0. |
| INSUFFICIENT | `IMMATURE`, `UNDERPOWERED`, `INSUFFICIENT`, `CONSISTENT` | A floor is not met, or the size artifact is not `POWERED_IN_PRINCIPLE`. **UNDERPOWERED never maps to NOT_SUPPORTED** (LR21 :45–46). |
| NOT_EXECUTABLE | `NOT_EXECUTABLE`, `SOURCE_LIMITED`, `VOIDED:<k>` | Any of: the issuer is not running (X10); a required PIT or rights fact is refuted; receipts are missing; or coverage is below 80%. |
| (development only) | `DEVELOPMENT_PASS`, `DEVELOPMENT_FAIL` | P1-DEV only. Never maps to any of the four classes. |

**X9 — Grading owner.**
- A PHASE 3 reader stub grades by the GPG pattern (`grade` :310, `_refusal` :236, `_gate_refusal` :260).
- C-MKT may reuse the RRA :273–284 label arithmetic, but not its read of the current mutable store (RRA :260). The reader grades from the vintage named by → SD-17.
- RRS :432 remains the Radar's own readiness owner. This contract does not change it.

**X10 — Engine-lane dependency.**
- Issued rows accrue only when the nightly `daily.yml` `engine:` job runs with `ledger_lane_armed()` (RRA :50).
- That job is the GH001-blocked path that EW-P1 is repairing. Until it runs, P3 accrues nothing, and every family is `IMMATURE`, hence INSUFFICIENT, by construction.
- At one issued row per session, the floors imply the first look comes ≥300 days after the first issued row, plus 21 sessions for the labels to mature.

---

## 5. Candidate C-MKT — leadership deterioration and a broad US market drawdown

**Claim (proposal).** A separately versioned issued probability `P̂_MKT(t,h)` of a ≥5% SPY close-to-close drawdown within `h` sessions adds **one** pre-declared leadership-deterioration input. On identical prospective issued rows, it has a lower expected Brier score than both of these:
- (a) the nested market-only control M0;
- (b) the incumbent Radar `drawdown_prob`.

**Not this.** It is not a sector-loss claim and not a relative-strength claim. No categorical state is scored. It does not reopen the PB11 SPY verdict (0/12 pass, #9122), as T14 :31 also says of itself.

1. **Primary estimand.**
   - **Instrument:** SPY. There is no benchmark leg and no membership.
   - **Event:** `E_MKT(t,h) = 1` iff `A(t,h) = max(0, 1 − min(P_{t+1..t+h}) / P_t) ≥ 0.05`. Otherwise it is 0 once mature. An immature label is absent, never zero.
   - **Target identity.** This event is identical to three existing definitions, which together license comparator B1:
     - the PB11 :365–370 frozen target;
     - the RRA :273–284 Radar grader (base = last close at or before `asof`; window = the next `h` bars; hit iff `min / base − 1 ≤ −0.05`);
     - the RR :228 / :1326 Radar measure.
     REVIEW :104 defines the same event.
   - **Horizons:** `h ∈ {5, 10, 21}` NYSE sessions. The primary horizon is set by → SD-11.
   - **Price basis:** total-return-adjusted Yahoo-route closes. This is the basis LR1 :140 records for the rotation lens. The label vintage is set by → SD-17.
   - **Calendar:** CAL.
   - **Onset:** the first `s` at which `P_s / P_t − 1 ≤ −0.05`.
   - **Existing damage:** → SD-16.
   - **Leadership input `L_t`:** exactly one feature, with no search (→ SD-04).
2. **Clock chain.** X4 applies. The matched Radar row must also satisfy the SD-12 cutoff, or the row leaves every arm's scored set.
3. **Model and version isolation.**
   - **Form:** → SD-06. The proposal is an L2 logistic `M1 = M0 + L_t`, with `M0` built on SPY `dd63` and `log rv20`, in the T14 :155–156 form.
   - **Fitting:** the model is fit once on the SD-02 / SD-03 calibration rows. The coefficient file is frozen and fingerprinted (X5).
   - **Family and budget:** → SD-19.
   - **Relation to T14:** → SD-05. T14 asks the same question of the same label over a retrospective window. That window, 2021-07-06→2026-10-07 (T14 :59), crosses the SD-02 cutoff. T14 is unregistered, with budget 51 (T14 :186–197).
4. **Baselines on identical rows.** Every arm predicts `E_MKT(t,h)` for the same `(t,h)`.
   - **B0:** the unconditional SPY rate (→ SD-21).
   - **M0:** the market-conditional control, fit on the same calibration rows.
   - **B1:** the incumbent Radar issued `drawdown_prob[h]` from the row with the same `asof` and current epoch (RRA :37–38, :207). This is legitimate only because of the target identity proved in item 1 (D1).
   - **B2:** a cheap comparator, an L2 logistic on `log rv20` (the T14 :153 volatility-matched baseline).
   - **Identical rows:** a row is scored only if every arm has a finite probability issued before the cutoff. Otherwise X6 applies.
5. **Dependence and power.** X7 applies, with SPY event clusters as defined at RDY :46. There is no sector floor.
6. **Missingness and rights.**
   - **Rights:** Yahoo route, APPROVED_BY_CHAIRMAN_ATTESTATION.
   - **PIT:** P-01 and P-04 apply, plus P-02 and P-03 if SD-04 picks option (c). X6 applies.
7. **Scorecard.**
   - **Primary:** the SD-13 IU test at the primary horizon. The 90% upper bound of the mean paired Brier delta must be below 0 against M0 **and** against B1. The calibration-in-the-large CI must contain 0.
   - **Descriptive:** log-loss deltas; the deltas against B0 and B2; reliability bins; abstention rate and coverage; H5 and H10; and an `already_down` stratum.
   - **Never reported:** watch metrics.

**Disconfirming outcome.** This applies at the first registered look at which the floors and `POWERED_IN_PRINCIPLE` both hold.
- If the upper bound against **M0** is ≥ 0, the verdict is **NOT_SUPPORTED**: the declared leadership input adds no measurable information about ≥5% SPY drawdowns beyond SPY's own drawdown and volatility state.
- If the candidate beats M0 but its upper bound against **B1** is ≥ 0, the verdict is **NOT_SUPPORTED** for the issued product: it is no better than the incumbent Radar.
- If the calibration CI excludes 0, the verdict is **NOT_SUPPORTED**.

The October 2026 narrative has no bearing on any of these verdicts.

---

## 6. Candidate C-SEC — leadership deterioration and the leadership sector's own loss

**Claim (proposal).** An issued probability `P̂_SEC(t,h)` of an absolute ≥ τ_SEC SMH close-to-close drawdown within `h` sessions adds the same single input `L_t`. On identical prospective rows, it beats two comparators:
- a **market-conditional model of the sector event**;
- a cheap lagged relative-strength comparator.

**Not this.** It is not a market claim. The Radar SPY probability is never its baseline (D1). It does not re-run the FAILED DR study (R&V :11), which tested a different target with a defensive trigger; that failure remains retained science.

1. **Primary estimand.**
   - **Instrument:** SMH (→ SD-07).
   - **Event:** `E_SEC(t,h) = 1` iff `A_SMH(t,h) ≥ τ_SEC`. Here `A_SMH` uses the PB11 :365 formula on SMH's own total-return closes and own session axis, as T14 :21 applies it per cohort.
   - **τ_SEC:** → SD-08.
   - **Horizons:** `h ∈ {5, 10, 21}`.
   - **Instrument identity:** the ETF is the instrument, and changes to its holdings belong to it. The 2011-12 relaunch splice is unverified (LR1 :130–131), so calibration starts by → SD-03. If XLK is ever added, the XLK composition break at LR1 :163 applies.
   - **Existing damage:** → SD-16.
2. **Clock chain.** X4 applies.
3. **Model and version isolation.** `M_SEC` is an L2 logistic on the B1_SEC covariates plus `L_t`, fit to `E_SEC` on the calibration rows. It has its own family and fingerprint (X5; → SD-19).
4. **Baselines on identical rows.** Every arm predicts `E_SEC`.
   - **B0_SEC:** the unconditional SMH event rate (→ SD-21).
   - **B1_SEC:** the market-conditional **sector** rate. This is an L2 logistic of `E_SEC` on SPY `dd63` and SPY `log rv20`, using market information only. Whether the Radar probability may also enter as a covariate is set by → SD-22.
   - **B2_SEC:** an L2 logistic on the trailing 5-session SMH/SPY log relative return. This is the REVIEW :126 naive-rotation comparator, a lagged RS.
   - **Descriptive stratum only:** the Radar calm or watch rows (the gate-silence stratum, REVIEW :127).
5. **Dependence and power.**
   - X7 applies, with SMH event clusters plus the sector floor (≥5 clusters, ≥12 adverse outcomes; REVIEW :121).
   - SMH events overlap heavily with SPY events, so honest N is likely to accrue slowly. In that case the honest verdict is `IMMATURE`; that is not something to engineer around.
6. **Missingness and rights.** P-01 applies to SMH and SPY. Rights are APPROVED_BY_CHAIRMAN_ATTESTATION. X6 applies.
7. **Scorecard.**
   - **Primary:** the IU test. The 90% upper bound of the mean paired Brier delta must be below 0 against B1_SEC **and** against B2_SEC. The calibration CI must contain 0.
   - **Descriptive:** the delta against B0_SEC; log loss; reliability; abstention and coverage; H5 and H10; the gate-silence stratum.

**Disconfirming outcome.** At a mature, powered look:
- If the upper bound against **B1_SEC** is ≥ 0, the verdict is **NOT_SUPPORTED**: the leadership sector's own loss is no more predictable with `L_t` than from market state alone. In other words, the "sector warning" is market beta.
- If it passes B1_SEC but its upper bound against **B2_SEC** is ≥ 0, the verdict is **NOT_SUPPORTED**: it is no better than naive lagged relative strength.

---

## 7. Candidate C-RS — leadership deterioration and a relative-wealth drawdown against the market

**Claim (proposal).** An issued probability `P̂_RS(t,h)` predicts that the same-clock relative wealth of the leadership sector against SPY suffers a registered drawdown of at least δ within `h` sessions. Using `L_t`, it beats two comparators on identical prospective rows:
- a market-conditional model of the **ratio** event;
- naive lagged relative strength.

**Not this.**
- It is not LR1 H1–H3 (LR1 :74–76). Those are mean continuation claims `Y_h = R_{o+h} − R_o` at `h = 20` (LR1 :183–192) on **defensive** pairs (LR1 :113–116), after A1 hysteresis entries (LR1 :216–217).
- It does not take the reserved name `..._PREREG_V3.md` (LR2 :95–97; LR21 :31).
- It does not subtract leg losses (D3).

1. **Primary estimand.**
   - **Ratio:** `W_t = P_SMH,t / P_SPY,t` on same-session total-return closes, which equals `exp(R_t)` with `R_t` as at LR1 :180. The ratio and the peak rule are set by → SD-09.
   - **Proposed event:** the issue-anchored form `A_RS(t,h) = max(0, 1 − min_{s∈(t,t+h]} W_s / W_t)`, with `E_RS(t,h) = 1` iff `A_RS ≥ δ` (→ SD-09).
   - **Both legs shown:** `A_SMH`, `A_SPY` and both leg returns are reported for every event. Each event is classified BOTH_DOWN, SECTOR_DOWN_MARKET_UP or BOTH_UP (R&V :33). None is labelled inflow.
   - **Horizons:** `h ∈ {5, 10, 21}`.
   - **Missing data:** both legs must come from the same session close. A missing leg means ABSTAIN.
2. **Clock chain.** X4 applies.
3. **Model and version isolation.**
   - `M_RS` is an L2 logistic on the B1_RS covariates plus `L_t`, with its own family (X5; → SD-19).
   - The carrier is set by → SD-10.
   - If SD-04 picks option (a) or (b), `L_t` is a registered deterioration state of the same ratio. The claim is then that this state carries information beyond naive 5-session RS.
4. **Baselines on identical rows.** Every arm predicts `E_RS`.
   - **B0_RS:** the unconditional ratio-event rate (→ SD-21).
   - **B1_RS:** the market-conditional ratio-event rate, an L2 logistic of `E_RS` on SPY `dd63` and `log rv20` (→ SD-22).
   - **B2_RS:** the trailing 5-session SMH/SPY log relative return (REVIEW :126).
5. **Dependence and power.** X7 applies, plus the floor of ≥5 ratio-event clusters and ≥12 adverse outcomes (REVIEW :121). C-RS shares the SMH leg with C-SEC (X7).
6. **Missingness and rights.** P-01 applies to both legs from the same vintage. Rights are APPROVED_BY_CHAIRMAN_ATTESTATION. X6 applies.
7. **Scorecard.**
   - **Primary:** the IU test. The 90% upper bound must be below 0 against B1_RS **and** against B2_RS. The calibration CI must contain 0.
   - **Descriptive:** the delta against B0_RS; the both-legs table; the BOTH_DOWN share; the δ sensitivity band from SD-09; H5 and H10.

**Disconfirming outcome.** At a mature, powered look:
- If the upper bound against **B2_RS** is ≥ 0, the verdict is **NOT_SUPPORTED**: the registered leadership-deterioration measure says nothing about the next `h` sessions' relative drawdown beyond naive 5-session relative strength.
- If the upper bound against **B1_RS** is ≥ 0, the verdict is **NOT_SUPPORTED**: the relative drawdown is no more predictable than from market state alone.

---

## 8. Ledger placement — options (i), (ii) and (iii)

R&V :57–69 asks for one claim and evidence row per study, kept inside the existing research owner. It must not be a new runtime table. Trial-budget registration through TL :204 and :298 is required whichever option is chosen; it is accounting, not placement.

| Option | Where | For | Against |
|---|---|---|---|
| (i) | A new section in GD1 (`research/grey_deer/gd1/GD1_CAUSAL_HYPOTHESIS_LEDGER.md`, blob `160fc8f9…`, 83 lines). Its row schema is Role / Evidence for / Evidence against / First-known / Kind / Confidence / What would change it. | It is the existing Grey Deer research owner, so no new ledger is created. | The schema lacks the R&V §5 field families: clocks, issue versus watch, same-row baseline, power, correction ancestry. Adding them is an edit to an existing ledger (PHASE 3, seat-authorised). |
| (ii) | A new file, `research/grey_deer/ew_completion_20261031/CLAIM_EVIDENCE_LEDGER_v1.md`, whose columns are exactly the R&V :61–69 field families, with one row per frozen family × horizon. | It has the full schema. No existing ledger is edited. It lives on the program carrier. | It is a second research ledger beside GD1 unless (i) carries a pointer row. |
| (iii) | Rows in `data/qledger/claims.jsonl` (census: 118,393 rows; blob `34a097d7…`), written through its existing writer. | Machine-queryable. | The availability of its owner (#10079) is not established. Hand writes are forbidden. It is a runtime claims ledger, so it mixes object types. Truncating or rewriting it is never allowed. |

---

## 9. What PHASE 3 would produce after `FROZEN:`, and what it depends on

- **Prereg file:** `research/grey_deer/ew_completion_20261031/EW_FORECAST_PREREG_v1_<merge-date>.md` (→ SD-19), never `..._PREREG_V3.md`. It would copy this contract's frozen values and bind the source pins.
- **Code:** an issuer and reader stub following the GPF and GPG patterns, with its test. It would write receipts per X5 and refuse to issue without its prereg blob, following the GPF :381 `_prereg_matches` pattern.
- **Size-and-power artifact:** synthetic only (X7). It must be committed before any P3 read.
- **Ledger and trial-ledger entries:** a ledger entry per SD-18, the trial-ledger family registration per SD-19, and the legacy-jobs registration.
- **External dependency:** EW-P1 must restore the `daily.yml` `engine:` job (X10). Without it, no row is ever issued.

---

## 10. SEAT DECIDES — canonical numbered list

Each line is one open choice. "Proposal" is the author's recommendation. A `FROZEN:` reply must give every SD a value.

1. SEAT DECIDES: SD-01 — which families to freeze. Options: (a) C-MKT + C-RS; (b) all three; (c) C-MKT only; (d) C-RS only. Proposal (a). C-MKT is the cheapest real test, since its target is identical to the incumbent grader and Radar measure. C-RS is the one sector claim that market beta cannot trivially explain. C-SEC is most exposed to being market beta, and it shares the SMH leg with C-RS.
2. SEAT DECIDES: SD-02 — calibration cutoff (X2). Options: (a) a calibration row is admissible only if its whole label window and feature lookback end on or before 2026-09-29, the last NYSE session before the 2026-09-30 state cited at R&V :13; move the date earlier if the seat dates the episode's onset earlier; (b) origin ≤ 2026-09-29, with labels allowed to run into October; (c) another date. Proposal (a).
3. SEAT DECIDES: SD-03 — calibration start. Options: (a) 2012-01-03 for every family, the first session after the unverified SMH 2011-12 relaunch splice (LR1 :130–131); (b) 2021-07-06, the PB11/T14 window start (T14 :59); (c) 2006 for C-MKT only, the Radar measurement era (RR :228–229). Proposal (a).
4. SEAT DECIDES: SD-04 — the single leadership-deterioration input `L_t`, shared by every frozen family (one input, no search). Options: (a) the SMH/SPY same-clock relative-wealth drawdown from its trailing 63-session peak, `1 − W_t / max(W_{t−62..t})`, on total-return closes (ETF-only, reconstructable subject to P-01); (b) the LR1 :216 A1 z-form applied to SMH/SPY; (c) the `leadership_crack` state one-hot (LC :14–18; member-based, no PIT history, P-02/P-03); (d) the T14 F2 XLK/RSP 20-session change (T14 :102). Proposal (a).
5. SEAT DECIDES: SD-05 — how C-MKT relates to the unregistered T14 draft (same SPY label, leader features, budget 51, window crossing SD-02). Options: (a) T14 stays unregistered and is superseded for this label by C-MKT; the seat records this, and the T14 file is untouched; (b) T14 runs first as C-MKT's development stage, with its window truncated per SD-02 and its feature fixed per SD-04; (c) both run independently with separate budgets. Proposal (a). Option (c) double-spends the same label and feature menu.
6. SEAT DECIDES: SD-06 — C-MKT model form. Options: (a) a standalone L2 logistic `M1 = M0 + L_t`, with `M0` on SPY `dd63` and `log rv20` (T14 :155–156) and the Radar as an external comparator; (b) an incumbent-anchored recalibration `logit p = a_h + b_h·logit(radar p_h) + c_h·L_t`, whose cohort splits whenever the Radar fingerprint changes. Proposal (a).
7. SEAT DECIDES: SD-07 — the C-SEC instrument, if C-SEC is frozen. Options: (a) SMH only; (b) SMH as primary plus XLK as a pre-declared replication charged separately (the T14 :40 pattern; XLK composition break LR1 :163); (c) SMH and XLK pooled, which R&V :43 rejects. Proposal (a).
8. SEAT DECIDES: SD-08 — the C-SEC threshold τ_SEC. Options: (a) 0.05, the symmetric lawful default (REVIEW :105); (b) 0.08, the existing frozen Radar secondary threshold (RRA :29–31); (c) a volatility-scaled value frozen from pre-cutoff tables only. Proposal (a).
9. SEAT DECIDES: SD-09 — the C-RS ratio, peak rule and δ. Options: ratio SMH/SPY or XLK/SPY; peak rule issue-anchored `A_RS = max(0, 1 − min_{s∈(t,t+h]} W_s / W_t)` or a running peak inside `[t, t+h]`; δ = 0.05 as a declared design default (REVIEW :100 (iii)) with sensitivity band {0.03, 0.08} reported descriptively, or another declared default. Proposal: SMH/SPY, issue-anchored, δ = 0.05.
10. SEAT DECIDES: SD-10 — the carrier for C-RS. Options: (a) the Grey Deer EW carrier, as its own family; (b) the LR-W6 Leadership Rotation carrier, with the V3 name still reserved (LR2 :95–97; LR21 :31). Proposal (a). C-RS is a probability product on a leadership ratio, not a continuation claim on a defensive pair.
11. SEAT DECIDES: SD-11 — primary horizon and multiplicity. Options: (a) h = 21 primary for every frozen family, with H5/H10 descriptive and Holm m = the number of frozen families; (b) h = 10 primary (the REVIEW :131 choice); (c) all three horizons gating, with Holm m = 3 × families. Proposal (a). Rationale: h = 21 has the largest frozen base rate in the existing tables (`b_21` = 0.176 at PB1 :315; 0.178 at RR :240) and is the Radar's headline horizon (RR :1324). The cluster floor still binds.
12. SEAT DECIDES: SD-12 — the decision cutoff for a valid issue. Options: (a) `issued_at` must precede the next NYSE session open (09:30 America/New_York) after the source session; late rows leave every arm's scored set and count as lost coverage; (b) before the close of t+1. Proposal (a).
13. SEAT DECIDES: SD-13 — primary scoring composition. Options: (a) intersection-union: VALIDATED needs every required comparator's 90% circular-block-bootstrap upper bound of the mean paired Brier delta below 0 (C-MKT: M0 and B1; C-SEC: B1_SEC and B2_SEC; C-RS: B1_RS and B2_RS), plus a calibration-in-the-large CI containing 0; (b) only the market-conditional comparator gates, and the others are descriptive. Proposal (a). IU needs no further multiplicity adjustment (PB1 :367).
14. SEAT DECIDES: SD-14 — practical margin and the power precondition. Options: (a) a design-default margin of Brier-skill fraction 0.05 relative to each required comparator; `POWERED_IN_PRINCIPLE` requires simulated power ≥ 0.80 at that margin under the X7 floors, with M ≥ 400 synthetic replications, committed before any P3 read; (b) an absolute Brier margin. In both options an underpowered family may still accrue, but its verdict ceiling is INSUFFICIENT. Proposal (a).
15. SEAT DECIDES: SD-15 — look schedule and bootstrap seed family. Options: (a) fixed looks: the first at the first month-end when every X7 floor holds at the primary horizon, at most 3 looks, alpha split equally across looks, seeds `20261031 + h`; (b) a time-uniform confidence sequence (R&V :51), only with a written dependence justification; (c) option (a) but reusing the RDY seed family `240924 + h`. Proposal (a).
16. SEAT DECIDES: SD-16 — existing-damage handling (C-MKT, C-SEC). Options: (a) score all rows, and report an `already_down` stratum descriptively (the instrument at least its threshold below its 63-session max at t); (b) exclude already-down rows from the primary, making it an onset-only target. Proposal (a). Option (b) removes rows exactly when risk is highest.
17. SEAT DECIDES: SD-17 — price vintage for features and labels. Options: (a) features use the vintage present at issue and labels use the vintage present at `graded_at`, with both blob sets recorded; a later revision is a correction with `corrected_at` and ancestry, never a silent re-grade; (b) labels use the as-issued vintage, frozen forever. Proposal (a).
18. SEAT DECIDES: SD-18 — ledger placement: (i) a new section in GD1; (ii) a new file `CLAIM_EVIDENCE_LEDGER_v1.md` on the R&V §5 schema; (iii) qledger rows through its existing writer. Proposal (ii), plus a one-line pointer row in (i) in the same PHASE 3 PR.
19. SEAT DECIDES: SD-19 — names and budgets. Proposal: issue contract `grey_deer_ew_forecast_issue.v1`; trial families `grey_deer_ew_mkt_v1`, `grey_deer_ew_sec_v1`, `grey_deer_ew_rs_v1`; a declared budget of 3 per frozen family (one claim per horizon, only the primary gating), registered through TL :204/:298 in PHASE 3; prereg file `EW_FORECAST_PREREG_v1_<merge-date>.md`, never `..._PREREG_V3.md`.
20. SEAT DECIDES: SD-20 — the development partition P1-DEV. Options: (a) fit on calibration start → 2022-12-30, then run P1-DEV once on 2023-01-03 → SD-02 cutoff, labelled DEVELOPMENT and RECONSTRUCTED; it can return only DEVELOPMENT_PASS or DEVELOPMENT_FAIL; a FAIL is recorded, and the seat then decides whether prospective accrual continues; (b) fit on the whole calibration window, skip P1-DEV and accrue prospectively only. Proposal (a).
21. SEAT DECIDES: SD-21 — source of the B0 unconditional rate. Options: (a) recompute it per family on the SD-02/SD-03 calibration rows under the frozen `(k + 0.5) / (n + 1)` rule (T14 :152); (b) for SPY only, reuse an existing frozen constant: PB1 :315 (0.036 / 0.082 / 0.176) or RR :240 (0.036 / 0.086 / 0.178), which differ at h10 and h21. Proposal (a).
22. SEAT DECIDES: SD-22 — the Radar probability as a covariate in B1_SEC and B1_RS. Options: (a) exclude it, using SPY price-state covariates only, which are reconstructable; (b) include it, in a prospective-only refit. There is no PIT-issued Radar history before 2026-06-23, and the Radar table was measured on 2006–2026, a look-ahead disclosed at PB1 :205–206. Proposal (a). In no option is it the baseline probability itself (D1).
23. SEAT DECIDES: SD-23 — abstention scoring. Options: (a) an abstained row stays in the scored set, with the frozen B0 probability substituted for the abstaining arm (zero-skill imputation); it is also reported as a miss when the event occurs (REVIEW :112); qualified-input coverage below 80% gives `SOURCE_LIMITED`; (b) drop abstained rows from Brier and report coverage separately, which lets selective abstention inflate skill. Proposal (a).

---

## 11. Honest limits stated in advance

- **Prospective rows only.** Only prospective issued rows can produce VALIDATED or NOT_SUPPORTED. Since issuance waits on EW-P1 (X10), no verdict other than INSUFFICIENT or NOT_EXECUTABLE is reachable for at least about 300 days plus label maturity after the first issued row.
- **Power may be the binding constraint.** Sector and ratio event clusters may accrue more slowly than market clusters (REVIEW :121). The synthetic size-and-power artifact may return UNDERPOWERED at any practical margin. If it does, the honest result is INSUFFICIENT, and that would be a research outcome, not a delivery failure (R&V :71).
- **Reconstructed history.** P1-DEV and the calibration rows use current-vintage, total-return-adjusted closes (P-01). They are labelled RECONSTRUCTED, and nothing reconstructed is presented as original point-in-time data.
- **What a failed test means.** A failed family disproves only its own registered claim, not every possible sector effect. Equally, a positive point estimate with a wide interval is not a promotion (R&V :18).
