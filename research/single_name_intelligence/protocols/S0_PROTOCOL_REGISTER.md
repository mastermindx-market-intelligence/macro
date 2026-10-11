# S0 Protocol Register: Single-Name Intelligence (Alibaba / Tencent)

**Status:** S0 FROZEN PROTOCOL. This is a research document only. It implements nothing and registers nothing.

**Task graph:** S0, domain O3. Acceptance cases **A22** and **A23**. Requires E0, M0 and V0.

**Companion frozen documents:**
- **IL** = `S0_INDEPENDENCE_LAW.md`, which covers A22: episodes, collapse order and honest-N.
- **SL** = `S0_SPLIT_AND_CONTAMINATION_LAW.md`, which covers A23: immutable splits and visible retirement.

**Evidence base:**

| What | Where it comes from |
|---|---|
| qledger line numbers | `engine/qledger.py` on origin/main `31b9647872e1`. `git diff` over that path is empty back to `e44069e306fd`, the evidence base V0 cites (V0 matrix L5). |
| Trial-ledger line numbers | `engine/trial_ledger.py`, same commit. |
| Grading-statistics line numbers | `engine/grading_stats.py`, `engine/pick_forward_dist.py`, `engine/k3e_eval1_forward.py` and `engine/ai_desk.py`, same commit. |
| V0 | `research/single_name_intelligence/SNI_V0_EVALUATION_SUPPORT_MATRIX.md` and `SNI_V0_EXTENSION_DECISION.md`, on main (PR #8834). |
| E0, M0 and coverage profiles | `SNI_E0_ISSUER_EVIDENCE_QUALIFICATION_2026-10-11.md`, `SNI_M0_MARKET_DATA_QUALIFICATION_2026-10-11.md`, and `config/single_name_intelligence/coverage_profiles/{alibaba,tencent}.yml`, at `43251ca845b2` (PR #8837; byte-identical on origin/main `98a40e3f4b13`). |
| SNI masterplan | `7906ef1c` (PR #8773, draft). |

## 0. Authority (frozen)

| authority → | rank | gate | size | signal | escalation | trade |
|---|---|---|---|---|---|---|
| every S0 protocol, both arms, every row and table of this register, IL and SL | **false** | **false** | **false** | **false** | **false** | **false** |

**First-stage authority is false on all six flags.** Nothing in this register requests, implies or reserves authority. No S0 output is a rank, gate, size, signal, escalation or trade input.

Any later authority would need the separate existing promotion machinery:
- `LADDER_RUNGS` (qledger L3531);
- `PROMOTION_MIN_CI_LOW` (L3540);
- `promotion_check_dispatch` (L4695);
- `emit_ladder_states` (L4738).

For the SNI family it would also need the V0 X5 DISPLAY pin (V0 extension decision L50; matrix row 21). That pin does not exist yet. Its named test is `test_sni_belief_family_is_pinned_display_and_never_promoted`.

## 1. The two arms (binding)

### HISTORICAL arm

This arm covers TRAIN and TUNE only (SL §2). QUARANTINE is never analysed.

- **Status of results.** The arm is DESCRIPTIVE. It is never confirmatory and never presented as a historical forecast.
- **Evidence block.** While the adjustment vintage is unpinned (M0 gap 1), every historical-arm result is **BLOCKED-AS-EVIDENCE**. Exploratory runs are labelled "vintage-unpinned, non-evidential".
- **Statistics used.** It uses only existing primitives that sit **outside** qledger:

| Primitive | File and line |
|---|---|
| `wilson_ci` | `engine/grading_stats.py` L56 |
| `block_bootstrap_ci` | `engine/grading_stats.py` L121 |
| `cone_coverage` | `engine/grading_stats.py` L408 |
| `reliability_curve` | `engine/grading_stats.py` L829 |
| `brier_decomposition` | `engine/grading_stats.py` L914 |
| `pinball` | `engine/pick_forward_dist.py` L578 |
| `mean_pinball` | `engine/pick_forward_dist.py` L586 |
| `brier_score` | `engine/k3e_eval1_forward.py` L213 |

- **No mapping into qledger.** No historical-arm statistic is ever mapped into a qledger grade. No historical forecast is ever reconstructed from current facts.

### PROSPECTIVE arm

This arm is the **only** TEST split.

- **Registration.** Claims are registered through qledger `register` (L2026) **before their window begins**. `_cohort_prospective` (L1722) enforces that.
- **Backfills.** Backfills never count as prospective (V0 matrix row 15).
- **Scope of the grading-primitive column.** Every "grading primitive" cell in §3 describes the prospective arm.

## 2. Registration gate (binding)

**No SNI claim may be registered** until all three of the following have landed:

1. **X5 (DISPLAY pin).** V0 extension decision L50, matrix row 21.
   - The SNI family is pinned DISPLAY in `FAMILY_CONTROL_POLICY` (L1387), with `may_rank`, `may_gate`, `may_size`, `may_signal`, `may_escalate` and `may_trade` all false.
   - The family is excluded from enumeration by `emit_ladder_states` (L4738).
   - The family is excluded from the per-family block of `compute_track_record` (L3435), written out by `emit_track_record` (L3514). That block publishes `site/qledger/track_record.json`.
   - X5 must land in the same PR as X1, or before it (V0 L122).
2. **X1 (family-gated validation).** Validation in `_validate_claim` (L1754) (V0 L46).
3. **X2 (computed spec salt).** The salt is computed in `_prepare_claim` (L1899) and feeds `_claim_id` (L1250) (V0 L47, matrix row 7). It includes the prereg digest of the protocol version (V0 extension decision §7).

Further conditions:

- **PR #8042.** V0 §9 (L119) forbids any qledger registration, batch or backfill edit (X1, X2, X6) while PR #8042 is open. This register makes no claim about #8042's current state.
- **HK legs.** HK legs additionally require X7 (V0 L52, matrix row 14). X7 makes HK prices reachable by the grader's price path, `engine/ai_desk.py::_close_series_uncached` (L236). HK legs also require an explicit same-market HK bench (matrix row 13).
- **No untyped pass-through.** Registering SNI fields under any existing family to skip this gate is rejected (V0 §8 item 5, L115).

**How rows are written until the gate opens:**
- A row whose primitive exists is written **REGISTERED-GATED**.
- A row whose primitive does not exist is written **"NOT SUPPORTED — bridge required"**, with the V0 row named.

No protocol below is registered today.

## 3. Register (13 protocols)

**Status vocabulary:**

| Status | Meaning |
|---|---|
| **REGISTERED-GATED** | The design is frozen and maps to an existing qledger primitive. Registration is blocked on §2. |
| **NOT SUPPORTED — BRIDGE REQUIRED** | No existing qledger primitive. The protocol may not register. The V0 row is named. |
| **NOT SUPPORTED — PROCUREMENT-GATED** | A data-acquisition gate is named. A scoring bridge is also required where stated. |
| **DIAGNOSTIC** | Never a hypothesis test and never registered. |
| **RETIRED-CONTAMINATED** | Reachable only through SL §8. No row holds it today. |
| **RETIRED-SUPERSEDED** | Reachable only through a row's kill rule. No row holds it today. |

**Fixed terms:**
- **Horizons** are always `GRADE_HORIZONS` (L114) = 5/21/63, in the unit `HORIZON_UNIT_TRADING` (L141).
- **"Event independence"** means IL §3 steps 0–6, with per-horizon greedy absorption and analysis sets PRIMARY, SENS-A and SENS-B (IL §4).
- **"Unit independence"** means IL §3 step 7. That covers steps 0–1, claim count-once at step 2, step 4 on the protocol's own units, and steps 5–6.
- **"Time-axis split"** means SL §2: TRAIN `s` < 2024-01-01; TUNE [2024-01-01, 2026-10-01); TEST = prospective claims registered after the S0 freeze and after §2; QUARANTINE otherwise for `s` ≥ 2026-10-01; per-`h` purge. Under it, the name axis is n/a (own-name protocol, SL §3), `event_holdout` is none (SL §4), and membership is sealed per SL §5 and immutable per SL §6.
- **"Visible retirement"** means SL §8: one `TrialLedger().log_trial(...)` row (trial_ledger L126) plus one REG §7 row; status RETIRED-CONTAMINATED; the successor is a new version; nothing is ever refilled.

| id | hypothesis family | unit of analysis | independence rule | split rule | grading primitive (qledger, per V0) | pre-registered null | retirement rule | Status |
|---|---|---|---|---|---|---|---|---|
| P01 | RESID-DIR-US: directional excess of the BABA US ADS (SEC:US-XNYS-BABA) vs a declared same-market US bench | one registered claim per horizon; honest-N = distinct non-overlapping units (IL §3 step 7) | Unit independence | Time-axis split | EXISTING: `grade_claim` (L2698) return/hit (`excess`, `hit`). REGISTERED-GATED on §2 (`register` L2026; `_cohort_prospective` L1722) | H0₁: hit rate = 0.50 per horizon. H0₂: median excess = 0. | Visible retirement | REGISTERED-GATED |
| P02 | RESID-DIR-HK: the same design for 9988.HK (SEC:HK-XHKG-09988) and 0700.HK (SEC:HK-XHKG-00700) vs an explicit HK bench | one registered claim per horizon per HK counter (frozen for the bridged successor) | Unit independence | Time-axis split | NOT SUPPORTED — bridge required. V0 row 14 / X7: the grader price path `_close_series_uncached` (ai_desk L236) does not reach HK prices, so the leg grades `primary_leg_refused` (`COHORT_ROWLESS_PRIMARY_REFUSED` L2861). V0 row 13: `_DEFAULT_BENCH` (L1183) = "SPY" mixes markets and `resolve_claim_market` (L975) / `require_single_clock` (L1159) refuse it | H0: hit rate = 0.50 per horizon (frozen for the bridged successor) | Visible retirement | NOT SUPPORTED — BRIDGE REQUIRED (V0 rows 13, 14) |
| P03 | RESID-SURFACE: normal-vs-abnormal residual surface (transparent rolling market/sector factor baseline plus historical-vol normalisation; IPCA challenger only with lawful point-in-time characteristics) | one unit per horizon (IL §3 step 7) | Unit independence | Time-axis split | NOT SUPPORTED — bridge required. V0 rows 4 and 6: qledger grades single-bench excess only (`grade_claim` L2698 emits `excess = subject_ret − bench_ret`), and there is no factor-residual outcome or scoring path | H0: the challenger's incremental explanation vs the transparent baseline = 0 (historical arm only, descriptive) | Visible retirement | NOT SUPPORTED — BRIDGE REQUIRED (V0 rows 4, 6) |
| P04 | EVT-RESULTS: directional response to results events. Frozen hierarchy: broad event prior → neighborhood → issuer/instrument → bounded own-name. S0 freezes the own-name leg only | one `results`-opened episode per horizon (IL §1, §3 step 4) | Event independence | Time-axis split | US leg EXISTING: `grade_claim` (L2698) return/hit, REGISTERED-GATED on §2. HK legs NOT SUPPORTED — bridge required (V0 row 14) | H0: post-event hit rate = 0.50 per horizon | Visible retirement | REGISTERED-GATED (US leg); HK legs NOT SUPPORTED — BRIDGE REQUIRED (V0 row 14) |
| P05 | EVT-CAPITAL: response to capital-action events (buyback programmes, placements, dividends, major-holder sales) | one `capital_action`-opened episode per horizon. One announced programme = ONE event; executions are evidence rows | Event independence | Time-axis split | As P04 | H0: post-event hit rate = 0.50 per horizon | Visible retirement | REGISTERED-GATED (US leg); HK legs NOT SUPPORTED — BRIDGE REQUIRED (V0 row 14) |
| P06 | EVT-REGULATORY: response to regulatory and material events. Heavy in calendar clusters | one `regulatory_material`-opened episode per horizon | Event independence. Same-day shocks are clustered, never merged (IL §8) | Time-axis split | As P04. A `DISCLOSURE_DATE` anchor is embargoed +1 business day (`TIMESTAMP_QUALITY` L1185; `_entry_anchor` L2672) | H0: post-event hit rate = 0.50 per horizon | Visible retirement | REGISTERED-GATED (US leg); HK legs NOT SUPPORTED — BRIDGE REQUIRED (V0 row 14) |
| P07 | EVT-RESPONSE-WINDOW: intraday response windows around announcements | one intraday window per event (frozen design intent) | Event independence | Time-axis split | NOT SUPPORTED — procurement-gated (M0 gap 7: HK intraday BLOCKED-procurement; BABA intraday 0 rows). No intraday horizon unit exists in qledger (`HORIZON_UNITS` L143 = trading or calendar), so it is also NOT SUPPORTED — bridge required: no V0 row covers an intraday unit (V0 row 3 "Clock" covers `resolve_horizon_window` L352 over those two units only), so the bridge needs a new V0-owned decision | Frozen form only: directional hit inside the window = 0.50 | Visible retirement | NOT SUPPORTED — PROCUREMENT-GATED (+ BRIDGE REQUIRED; no V0 row, new V0 decision needed) |
| P08 | OPT-IMPLIED: options-implied move and skew around events vs realised | one event × expiry (frozen design intent) | Event independence | Time-axis split | NOT SUPPORTED — procurement-gated (M0 gap 6: BABA options stale since 2026-08-21; M0 gap 7: HK options BLOCKED-procurement), and also bridge required (V0 rows 4, 6: no implied-outcome primitive) | Frozen form only: aggregate implied move = realised move | Visible retirement | NOT SUPPORTED — PROCUREMENT-GATED (+ BRIDGE REQUIRED, V0 rows 4, 6) |
| P09 | FCST-RETURN-DIST: short-horizon return quantile distribution vs frozen simple baselines | one registered belief × horizon (IL §3 step 7) | Unit independence | Time-axis split | NOT SUPPORTED — bridge required (V0 rows 4, 6, 7: belief block, family-dispatched scoring X3 with `pinball_mean`, computed salt X2. `sni_belief.v1` is a decision, not code) | H0: mean pinball(registered) = mean pinball(baseline), paired | Visible retirement | NOT SUPPORTED — BRIDGE REQUIRED (V0 rows 4, 6, 7) |
| P10 | FCST-RANGE-INTERVAL: interval/range width and coverage. Conformal long-run coverage is NOT a per-stock, per-regime or finite-window guarantee | one registered interval × horizon (IL §3 step 7) | Unit independence | Time-axis split | NOT SUPPORTED — bridge required (V0 rows 6 and 10: interval scoring sits behind `_matured_window` L2607; named test `test_sni_belief_interval_is_not_scored_before_maturity`) | H0: empirical coverage = nominal (two-sided). H0: width = baseline width | Visible retirement | NOT SUPPORTED — BRIDGE REQUIRED (V0 rows 6, 10) |
| P11 | FCST-EVENT-REACTION-DIST: reaction distribution conditional on event class | one event-opened episode per horizon | Event independence. An event-class holdout is optional, but only if declared at version freeze (SL §4) | Time-axis split | NOT SUPPORTED — bridge required (V0 rows 4, 6: `crps_quantile_approx` / `pinball_mean` under X3) | H0: registered reaction distribution = class-conditional baseline, paired pinball | Visible retirement | NOT SUPPORTED — BRIDGE REQUIRED (V0 rows 4, 6) |
| P12 | KPI-VALUATION: KPI and valuation beliefs | none (never registered) | n/a: display-only research notes. Scenario arithmetic is kept separate from estimated probabilities | n/a | NOT SUPPORTED — bridge required (V0 rows 2, 5: no non-price outcome resolver until the Company Event / Earnings owner ratifies as-first-reported values; E0 gap 4: no admitted financial-metric owner) | n/a: nothing registers | n/a (a future registered form inherits SL §8) | NOT SUPPORTED — BRIDGE REQUIRED (V0 rows 2, 5) |
| P13 | XLIST-BASIS-DIAGNOSTIC: BABA / 9988.HK cross-listing basis | one display row per (interval, pair). Never an analysis unit | n/a: never counted. 9988 and BABA are never one claim | n/a: never registered | NOT SUPPORTED — bridge required (V0 row 19: one claim has one clock, and `resolve_claim_market` L975 refuses mixed-market legs. Per-listing beliefs are joined asynchronously by the C2 guard over `hk_adr_bridge` pairs. KWEB is never a Tencent quote. M0 gap 3: no ADS-ratio owner) | none: diagnostic only | n/a | DIAGNOSTIC — NOT SUPPORTED (V0 row 19) |

**Row count:** 13. Four carry REGISTERED-GATED: P01 on its only leg, and P04, P05 and P06 on their US legs only (their HK legs are NOT SUPPORTED — BRIDGE REQUIRED, V0 row 14). Eight are wholly NOT SUPPORTED: six bridge-required (P02, P03, P09, P10, P11, P12) and two procurement-gated that also need a bridge (P07, P08). One is DIAGNOSTIC: P13. 4 + 8 + 1 = 13. No row is registered in qledger today.

**No row claims full probabilistic forecast support.**

## 4. Grading bridge statement

The only grading primitive that any S0 prospective arm may map to today is qledger `grade_claim` (L2698).
- **What it emits.** It returns `subject_ret`, `bench_ret`, `control_ret`, `excess = subject_ret − bench_ret` and `hit`.
- **When it grades.** Only after maturity (`_matured_window` L2607, `_matured` L2629).
- **What it does not grade.** A refused primary leg grades `primary_leg_refused` (L2861).

**These are directional outcomes.** They are not calibrated probabilities, distributions, intervals, quantiles or KPI beliefs, and they must never be presented as such. Return/hit grading is never called probabilistic.

"Accepted bridge" means exactly the three conditions in V0 extension decision §5 (L70–L80):

> 1. X3 merged, with the §4 tests green.
> 2. A reliability diagnostic (`grading_stats.reliability_curve` for bins, `cone_coverage` for quantiles) computed on **matured, prospective** beliefs only.
> 3. The `WS:EVAL-OS-MEASUREMENT-LAW` owner records acceptance.

**Labelling until all three hold:**
- Any surface that shows an SNI qledger grade labels it "direction right/wrong over N matured beliefs".
- It never labels it forecast skill, calibration or probability accuracy.
- N here is IL honest-N, never a literal row count.

**Other rules:**
- **No SNI belief yet.** No SNI belief exists before X1 lands, so there is no SNI track record (V0 L80).
- **Hindsight is not a forecast.** Hindsight facts about 0700.HK or 9988.HK are outcomes, never historical forecasts.
- **What the bridge does not open.** The bridge does not open registration. Registration is gated separately by §2. The bridge also grants no authority (§0).

## 5. Null-disclosure law

Every null result, prospective or historical-descriptive, is a first-class published output. It carries the following, in this order:

1. **The plain-word null.** For example: "we predicted direction at horizon h; we could not distinguish accuracy from a coin flip."
2. **The analysis set** (IL §4). PRIMARY leads, and SENS-A and SENS-B are shown beside it.
3. **honest-N.** Distinct episodes or units after the full IL §3 collapse. This is the only sample N.
4. **cluster-N** (IL §1).
5. **The literal row count.**
6. **Visible exclusions.** Counts of excluded-and-listed, confounded, absorbed, purged and QUARANTINE episodes.
7. **The test.** Name, sidedness and α, as pre-registered.
8. **The CI.** `wilson_ci` (L56) or `block_bootstrap_ci` (L121), with the block length and the cluster variable named.
9. **The trial count.** For the protocol's TrialLedger family: `literal_n` (L210), `effective_n` (L214) and `declared_budget` (L244). This is the multiple-testing quantity. It is never added to a sample N or confused with one.
10. **The receipt.** It includes:
    - the commit sha;
    - the prereg digest;
    - the REG §6 seal row;
    - the trial-ledger path `data/trial_ledger.jsonl` (`DEFAULT_PATH`, L48) where applicable;
    - every prior look (SL §5).

**How nulls are treated:**
- A null is never hidden.
- A null is never relegated to an inaccessible artifact.
- A null is never re-run on a new split, cohort, horizon, target or bench without a new protocol version (`DEC:PREREG-DESIGN-CHANGE-SUPERSEDES`).
- Historical-arm nulls are labelled DESCRIPTIVE (non-confirmatory).

**Failed models.** A model that fails its pre-declared criterion is killed or held as research. The SNI masterplan §8 binds (L268, at `7906ef1c`): "do not rescue it by changing the target, cohort or horizon after seeing results. Preserve failed hypotheses and contaminated holdouts as evidence."

## 6. Membership Seal table (typed; sealed by S1, empty at S0)

S1 appends one row per `(protocol_id, version, split)` **before any outcome of that version is computed** (SL §5). A TEST row seals the TEST rule: the prereg digest of the version. It does not seal a finite list.

| protocol_id | version | split | manifest_sha256 (or TEST-rule prereg digest) | sealed_at | sealing commit |
|---|---|---|---|---|---|
| — | — | — | — | — | — |

## 7. Retirement Log table (typed; empty at S0)

A row is appended in the same PR that reports a contamination (SL §8 step 2). No protocol row is ever deleted.

| protocol_id | version | split | membership_sha256 | contamination_class | detected_at | evidence_pointer | trial_ledger_family | trial_ledger_config_hash | successor (protocol_id, version) |
|---|---|---|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — | — | — | — |

## 8. Trial budgets (declared at S0)

- **When they are recorded.** S1 records each budget at start through `TrialLedger(...).log_declared_budget(n, family=..., reason=...)` (L159).
- **Floors, not caps.** A declared budget is a **floor** ("FLOOR", L163). `effective_n` returns `max(base, declared, 1)` (L242). Exceeding a budget raises the trial count and the multiple-testing haircut. It is never refused and never hidden.
- **Retirement rows count.** Retirement rows (SL §8) count as trials.
- **Successors.** A successor's budget is at least the carried count.

| protocol_id | TrialLedger family | declared n (floor) | reason |
|---|---|---|---|
| P01 | sni.s0.P01 | 6 | 3 horizons × 2 frozen baselines |
| P02 | sni.s0.P02 | 4 | frozen before the bridge, so a bridged successor cannot claim a fresh budget |
| P03 | sni.s0.P03 | 4 | frozen before the bridge |
| P04 | sni.s0.P04 | 6 | 3 horizons × 2 declared variants (entry timing, bench) |
| P05 | sni.s0.P05 | 6 | as P04 |
| P06 | sni.s0.P06 | 6 | as P04 |
| P07 | sni.s0.P07 | 4 | frozen before procurement |
| P08 | sni.s0.P08 | 4 | frozen before procurement and before the bridge |
| P09 | sni.s0.P09 | 4 | frozen before the bridge |
| P10 | sni.s0.P10 | 4 | frozen before the bridge |
| P11 | sni.s0.P11 | 4 | frozen before the bridge |
| P12 | sni.s0.P12 | 4 | frozen before the bridge. P12 never registers |
| P13 | sni.s0.P13 | 4 | diagnostic. Declared so that no later basis "test" can claim a fresh budget |

## 9. Detail blocks (masterplan §8 freeze list for each protocol)

**Common rules for every block:**
- **Timestamp quality.** Entry anchors must carry a `timestamp_quality` outside {EVENT_DATE, SNAPSHOT_DATE, CORRUPTED} (`TIMESTAMP_QUALITY` L1185; V0 matrix row 3).
- **Input rights.** All input rights are UNVERIFIED (M0 gap 4).
- **Collapse before counting.** qledger `_claim_id` (L1250) plus keep-first `register` (L2026) give claim-level count-once only. They never perform the A22 collapse. The S1 runner applies IL §3 before anything is counted (IL §5).
- **Power.** One-sided α = 0.05 and power 0.80, for a hit rate of 0.60 vs 0.50, require n = ⌈152.5⌉ = **153 independent episodes**:
  - n = ((z₀.₉₅·√(0.5·0.5) + z₀.₈₀·√(0.6·0.4)) / 0.10)²
  - with z₀.₉₅ = 1.645 and z₀.₈₀ = 0.842.
- **Where 153 comes from.** This is O3's computation under masterplan §8 (L260): "Set minimum evidence using a prospective precision/power design, not a universal arbitrary N". The masterplan does not state the number. One issuer produces a handful of episodes a year, so every own-name protocol is **descriptive only**. Inference requires a cohort protocol, which would be a new row with a name axis (SL §3). None is registered at S0.

### P01: RESID-DIR-US

- **Target and timestamp.** The target is the signed excess return of BABA (SEC:US-XNYS-BABA, alibaba.yml L61) vs the declared US bench over each horizon.
  - Direction ∈ {−1, 0, +1} is declared at registration time T_reg (UTC), before the window (`_cohort_prospective` L1722).
  - The observation timestamp is the grade row's grading time.
- **Eligible cohort and exclusions.** The `alibaba` issuer group, graded on the ADS leg only.
  - Windows censored into a declared state are excluded (V0 matrix row 12; `halted` only from a named halt source).
  - Clock or evidence gate failures are excluded and listed.
  - Counter `rmb_89988` (no `security_id`, alibaba.yml L49) is never a subject.
- **Outcome horizon.** 5/21/63 sessions (L114, L141).
- **Data clocks.** `MARKET_US` only, through `CLOCK_CALENDARS` (L190) and `resolve_horizon_window` (L352). Fill is `FILL_NEXT_BAR` (L2476). Windows resolve through the one clock predicate and never a second implementation.
- **Feature set (names only).** Announcement session-part (pre-open / in-session / post-close), trailing realised-vol bucket, bench identity. No feature may read information timestamped after the anchor (SL §7 class 3).
- **Baselines (frozen).**
  - (i) always-long (+1);
  - (ii) sign of the trailing 63-session excess.

  No per-name post-hoc selection.
- **Split rule.** Time-axis split (SL §2). Name axis n/a. `event_holdout` none.
- **Trial budget.** n = 6, family `sni.s0.P01` (§8).
- **Proper score.** None. Hit and excess measure directional accuracy only; they are **not a proper score**.
- **Uncertainty and power.**
  - `wilson_ci` (L56) on the hit rate.
  - `block_bootstrap_ci` (L121) on excess, with block length ≥ h, clustered on the cluster key.
  - 153 episodes is unreachable from one issuer, so the protocol is descriptive only.
- **Non-inferiority / improvement.** None at own-name level.
- **Kill / continue.** Continue as a gated descriptive registration. The protocol becomes RETIRED-SUPERSEDED (a new version) if, 24 months after its first prospective registration, fewer than 20 units have matured and no cohort successor row exists. It is never re-scoped in place.
- **Pre-registered null.** H0₁: hit rate = 0.50 per horizon. H0₂: median excess = 0.
- **Retirement rule.** SL §8.
- **Data gates.**
  - Registration is gated on §2.
  - The historical arm is BLOCKED-AS-EVIDENCE (M0 gap 1).
  - The bench must be like-basis and same-vintage (M0 §3 L141–L148 bench census; §4 L160 like-basis requirement).
  - Rights are UNVERIFIED.
- **Authority flags.** rank, gate, size, signal, escalation and trade are all **false**.

### P02: RESID-DIR-HK (frozen design intent; nothing registers until the bridge lands)

- **Target and timestamp.** The target is the signed excess of 9988.HK (alibaba.yml L37) or 0700.HK (tencent.yml L38) vs an explicit same-market HK bench.
  - Candidate benches are 2800.HK or 3033.HK (M0 §3 L147–L148), like-basis per M0 §4 L160.
  - The bench choice is fixed per version before any registration.
  - Registration precedes the window.
- **Eligible cohort and exclusions.**
  - The HKD counters of the two issuer groups.
  - `rmb_89988` and `rmb_80700` are never pooled and never subjects (no `security_id`).
  - Censoring and gate exclusions as P01.
- **Outcome horizon.** 5/21/63 HK sessions.
- **Data clocks.** `MARKET_HK` through `CLOCK_CALENDARS` (L190), bound to the `_hk_calendar` import (L60, used at L193).
  - Announcements during HK trading hours or the midday break cannot be placed without intraday data (M0 §5 L174–L176).
  - The window therefore starts at the next full session (IL §1 `s(c)`).
- **Feature set (names only).** As P01, plus HK session-part.
- **Baselines.** As P01.
- **Split rule.** Time-axis split.
- **Trial budget.** n = 4.
- **Proper score.** Hit and excess. **Not a proper score.**
- **Uncertainty and power.** As P01. Descriptive only.
- **Non-inferiority / improvement.** None.
- **Kill / continue.** Dormant until X7 lands. After that, the P01 rule applies.
- **Pre-registered null.** H0: hit rate = 0.50 per horizon.
- **Retirement rule.** SL §8.
- **Data gates / why NOT SUPPORTED.**
  - V0 row 14 / X7: `_close_series_uncached` (ai_desk L236) does not reach HK prices, so an HK primary leg grades `primary_leg_refused` (L2861).
  - V0 row 13: the default bench "SPY" (L1183) mixes markets and is refused (`resolve_claim_market` L975, `require_single_clock` L1159).
  - No adjustment-vintage pin exists (M0 gap 1).
  - No HK halt calendar exists (M0 gap 9).
  - Rights are UNVERIFIED.
- **Authority flags.** All **false**.

### P03: RESID-SURFACE

- **Target and timestamp.** The normal-vs-abnormal residual surface: a transparent rolling market/sector factor baseline plus historical-vol normalisation.
  - A contemporaneous decomposition answers "how unusual was this move". It never becomes a pre-move forecast.
  - An IPCA challenger is allowed only with lawful point-in-time characteristics and enough cross-name coverage (masterplan L252).
- **Eligible cohort and exclusions.** As P01 (US leg) until X7.
- **Outcome horizon.** 5/21/63 sessions.
- **Data clocks.** `MARKET_US` (L180) through `CLOCK_CALENDARS` (L190). Factor quantities known at the observation cutoff are kept distinct from quantities forecast at a decision cutoff (masterplan §5.3 L122).
- **Feature set (names only).** Factor-baseline family, normalisation window, list of point-in-time characteristic names.
- **Baselines.** The transparent rolling baseline itself.
- **Split rule.** Time-axis split.
- **Trial budget.** n = 4.
- **Proper score.** Incremental explanation vs the baseline. **Not a proper score** and not available in qledger.
- **Uncertainty and power.** `block_bootstrap_ci` (L121). Descriptive only.
- **Non-inferiority / improvement.** The challenger must beat the baseline out-of-time, from TRAIN to TUNE, to remain in research.
- **Kill / continue.** The challenger is killed or held as research on a failed out-of-time comparison. L268 binds: it is not rescued by changing the target, cohort or horizon.
- **Pre-registered null.** H0: incremental explanation = 0.
- **Retirement rule.** SL §8.
- **Data gates / why NOT SUPPORTED.**
  - V0 rows 4 and 6.
  - The historical arm is BLOCKED-AS-EVIDENCE (M0 gap 1).
  - The HK leg additionally needs V0 row 14.
- **Authority flags.** All **false**.

### P04: EVT-RESULTS

- **Target and timestamp.** The directional post-event excess response for episodes opened by a `results` event, anchored at the opener's `s` on the counting clock (IL §1).
  - The anchor needs evidenced first-public-availability: `CRAWL_BOUNDED`, `PUBLISHER_STATED` or `DISCLOSURE_DATE` (keys of `TIMESTAMP_QUALITY`, L1185).
  - Frozen hierarchy: broad event prior → neighborhood → issuer/instrument → bounded own-name. S0 freezes the own-name US leg only. Neighborhood legs would be cohort protocols, and none is registered.
- **Eligible cohort and exclusions.**
  - PRIMARY excludes episodes flagged `confounded`.
  - SENS-A and SENS-B are reported beside it (IL §4).
  - Censoring as P01.
- **Outcome horizon.** 5/21/63 sessions from `s`.
- **Data clocks.** `MARKET_US` for the BABA leg. HK legs would use `MARKET_HK` (IL §1), but they are currently unreachable (V0 row 14).
- **Feature set (names only).** Event class, anchor session-part, cluster key, bench identity.
- **Baselines (frozen).**
  - (i) always-long;
  - (ii) sign of the trailing 63-session excess;
  - (iii) direction of the all-events pooled prior.
- **Split rule.** Time-axis split. `event_holdout` none.
- **Trial budget.** n = 6.
- **Proper score.** Hit and excess. **Not a proper score.**
- **Uncertainty and power.** As P01, clustered on the cluster key. Descriptive only.
- **Non-inferiority / improvement.** None at own-name level.
- **Kill / continue.** As P01.
- **Pre-registered null.** H0: post-event hit rate = 0.50 per horizon.
- **Retirement rule.** SL §8.
- **Data gates.**
  - The historical arm is BLOCKED-AS-EVIDENCE (M0 gap 1).
  - The BABA next-earnings date is stale (E0 gap 6, `collectors/equity_earnings.py`).
  - There is no forward HK results-date owner (E0 gap 5).
  - HK legs are NOT SUPPORTED (V0 row 14).
- **Authority flags.** All **false**.

### P05: EVT-CAPITAL

- **Target and timestamp.** The directional post-event response for episodes opened by a `capital_action` event (buyback programmes, placements, dividends, major-holder sales).
- **Eligible cohort and exclusions.** As P04.
  - **One announced programme is ONE event.** Execution returns are evidence rows (IL §3 step 2).
  - HK placement coverage misses general-mandate placings such as 9988's (E0 gap 10, `collectors/hk_placements.py`). Those episodes are excluded and listed, never silently dropped.
- **Outcome horizon, clocks, features, baselines, split, score, uncertainty.** As P04.
- **Trial budget.** n = 6.
- **Non-inferiority / improvement.** None (descriptive only).
- **Kill / continue.** As P01.
- **Pre-registered null.** H0: post-event hit rate = 0.50 per horizon.
- **Retirement rule.** SL §8.
- **Data gates.**
  - As P04.
  - `capital_structure` has zero rows for BABA's CIK (E0 L98).
  - BABA's dividend factor is derivable only as `close/close_price` (M0 L70) and is vintage-unpinned.
- **Authority flags.** All **false**.

### P06: EVT-REGULATORY

- **Target and timestamp.** The directional post-event response for episodes opened by a `regulatory_material` event.
  - A regulatory disclosure dated by `DISCLOSURE_DATE` anchors at the first session strictly after the date (IL §1).
  - qledger embargoes it +1 business day (L1185, `_entry_anchor` L2672). A claim whose resolved window does not start at `s` is not registered (IL §1).
- **Eligible cohort and exclusions.** As P04.
  - **Heavy in calendar clusters.** One same-session shock can hit both issuer groups.
  - Clusters are counted as cluster-N and used as the bootstrap cluster variable. They are never merged into one episode (IL §8).
- **Outcome horizon, features, baselines, split, score, uncertainty.** As P04.
- **Trial budget.** n = 6.
- **Non-inferiority / improvement.** None (descriptive only).
- **Kill / continue.** As P01.
- **Pre-registered null.** H0: post-event hit rate = 0.50 per horizon.
- **Retirement rule.** SL §8.
- **Data gates.** As P04, plus: there is no HK halt calendar (M0 gap 9), so HK windows cannot be censored as halted.
- **Authority flags.** All **false**.

### P07: EVT-RESPONSE-WINDOW

- **Target and timestamp (frozen design intent).** An intraday window [t0, t0 + w] on the venue clock, with w declared per version and t0 the evidenced first-public-availability time.
- **Eligible cohort and exclusions.** Events with an evidenced intraday timestamp. Midday-break announcements need intraday data (M0 L176).
- **Outcome horizon.** The declared w. qledger's only horizon units are trading and calendar (L141–L143).
- **Data clocks.** Venue clocks (L190), which carry no intraday segments today.
- **Feature set, baselines.** Names only, as P04.
- **Split rule.** Time-axis split.
- **Trial budget.** n = 4.
- **Proper score.** n/a while gated.
- **Uncertainty and power.** Descriptive only.
- **Non-inferiority / improvement.** None.
- **Kill / continue.** Dormant while gated.
- **Pre-registered null.** Frozen form only: directional hit inside the window = 0.50.
- **Retirement rule.** SL §8.
- **Data gates / why NOT SUPPORTED.**
  - HK intraday is BLOCKED-procurement (M0 gap 7).
  - BABA intraday has 0 rows.
  - The RMB counters have no prices (M0 gap 2).
  - No V0 row covers an intraday horizon unit, so a scoring bridge needs a new V0-owned decision as well.
- **Authority flags.** All **false**.

### P08: OPT-IMPLIED

- **Target and timestamp (frozen design intent).** The options-implied move and skew around events vs the realised move, at declared expiries.
- **Eligible cohort and exclusions.** Events with qualifying option snapshots. Stale snapshots are excluded and listed.
- **Outcome horizon.** To the event window or expiry.
- **Data clocks.** Venue clocks (L190). `SNAPSHOT_DATE` quality is never an entry anchor (L1185).
- **Feature set, baselines.** Names only. Baseline: a realised-vol-matched implied move.
- **Split rule.** Time-axis split.
- **Trial budget.** n = 4.
- **Proper score.** Implied-vs-realised absolute error. **Not a proper score.** Scoring would need V0 row 6.
- **Uncertainty and power.** Descriptive only.
- **Non-inferiority / improvement.** None.
- **Kill / continue.** Dormant while gated.
- **Pre-registered null.** Frozen form only: aggregate implied move = realised move.
- **Retirement rule.** SL §8.
- **Data gates / why NOT SUPPORTED.**
  - BABA options are stale since 2026-08-21, with ThetaData EOD `n_roots` 0 (M0 gap 6, L138).
  - HK options are BLOCKED-procurement (M0 gap 7).
  - There is no qledger primitive (V0 rows 4, 6).
- **Authority flags.** All **false**.

### P09: FCST-RETURN-DIST

- **Target and timestamp.** A registered short-horizon return quantile distribution, one claim per horizon sharing a `belief_id`.
  - Registration precedes the window.
  - Horizons are limited to L114.
  - Direction is derived as sign(q50) and is never the headline score (V0 row 4).
- **Eligible cohort and exclusions.** The protocol's own registered units (IL §3 step 7). Censoring per V0 row 12 (`censoring_state`, X4).
- **Outcome horizon.** 5/21/63 sessions.
- **Data clocks.** `MARKET_US` (L180) through `CLOCK_CALENDARS` (L190) until X7. After X7, `MARKET_HK` with an explicit HK bench.
- **Feature set (names only).** Declared in the prereg instance. No feature reads post-anchor information.
- **Baselines (frozen per version before any registration).** Random-walk quantiles; historical empirical quantiles.
- **Split rule.** Time-axis split.
- **Trial budget.** n = 4.
- **Proper score.** Pinball (`pinball` L578, `mean_pinball` L586) and `cone_coverage` (L408) exist outside qledger, for the historical arm only. The qledger mapping is NOT SUPPORTED: it needs X3 `pinball_mean` and the full §4 bridge.
- **Uncertainty and power.** Paired `block_bootstrap_ci` (L121) with block length ≥ h.
- **Non-inferiority / improvement.** The registered distribution must beat the frozen baseline on mean pinball, paired, to continue.
- **Kill / continue.** Killed or held as research on a failed pre-declared criterion. L268 binds.
- **Pre-registered null.** H0: mean pinball(registered) = mean pinball(baseline), paired.
- **Retirement rule.** SL §8.
- **Data gates / why NOT SUPPORTED.**
  - V0 rows 4, 6 and 7. `sni_belief.v1` is a decision, not code.
  - The historical arm is BLOCKED-AS-EVIDENCE (M0 gap 1).
- **Authority flags.** All **false**.

### P10: FCST-RANGE-INTERVAL

- **Target and timestamp.** Registered central intervals per horizon. An interval is never scored before maturity (V0 row 10, `test_sni_belief_interval_is_not_scored_before_maturity`).
- **Cohort, horizon, clocks, features, baselines, split.** As P09.
- **Trial budget.** n = 4.
- **Proper score.** Width and empirical coverage are judged **together** (`cone_coverage` L408, historical arm only). Long-run conformal coverage is NOT a per-stock, per-regime or finite-window guarantee (masterplan L266).
- **Uncertainty and power.** Paired block bootstrap. Coverage diagnostics run on matured prospective beliefs only (§4 condition 2).
- **Non-inferiority / improvement.** Narrower width at equal coverage than the frozen baseline.
- **Kill / continue.** As P09.
- **Pre-registered null.** H0: coverage = nominal (two-sided). H0: width = baseline width.
- **Retirement rule.** SL §8.
- **Data gates / why NOT SUPPORTED.**
  - V0 rows 6 and 10.
  - The historical arm is BLOCKED-AS-EVIDENCE.
- **Authority flags.** All **false**.

### P11: FCST-EVENT-REACTION-DIST

- **Target and timestamp.** A registered distribution of the reaction from `s` to the horizon, conditional on event class. Registration precedes the window.
- **Cohort and exclusions.** Event independence; PRIMARY excludes `confounded`. An optional event-class holdout must be declared at version freeze (SL §4).
- **Outcome horizon, clocks, features, baselines, split.** As P09, with event conditioning.
- **Trial budget.** n = 4.
- **Proper score.** `crps_quantile_approx` / `pinball_mean` under X3. Historical arm outside qledger only.
- **Uncertainty and power.** Paired block bootstrap clustered on the cluster key. Descriptive only.
- **Non-inferiority / improvement.** Beat the class-conditional frozen baseline.
- **Kill / continue.** As P09.
- **Pre-registered null.** H0: registered reaction distribution = baseline, paired pinball.
- **Retirement rule.** SL §8.
- **Data gates / why NOT SUPPORTED.**
  - V0 rows 4 and 6.
  - HK legs additionally need V0 row 14.
  - The historical arm is BLOCKED-AS-EVIDENCE.
- **Authority flags.** All **false**.

### P12: KPI-VALUATION

- **Target and timestamp.** None registered. KPI and valuation beliefs may be recorded only as display-only research notes (V0 row 2). Scenario arithmetic is always kept separate from estimated probabilities (masterplan L264).
- **Cohort, horizon, clocks, features, baselines, split.** n/a. Nothing registers.
- **Trial budget.** n = 4, declared defensively.
- **Proper score.** None. There is no outcome resolver (V0 row 5).
- **Uncertainty and power / Non-inferiority.** n/a.
- **Kill / continue.** Dormant until two things exist:
  - the Company Event / Earnings owner ratifies an as-first-reported value and a restatement policy;
  - an admitted financial-metric owner exists. Per E0 gap 4, the one present field, `currency`, mislabels RMB figures as HKD.
- **Pre-registered null.** n/a.
- **Retirement rule.** n/a. A future registered form inherits SL §8.
- **Data gates / why NOT SUPPORTED.** V0 rows 2 and 5, and E0 gap 4.
- **Authority flags.** All **false**.

### P13: XLIST-BASIS-DIAGNOSTIC

- **Target and timestamp.** BABA / 9988.HK basis **display rows only**. Each display row binds:
  - the ratio's effective interval;
  - quote timestamps;
  - currency and units;
  - venue calendars;
  - corporate actions;
  - price type;
  - staleness thresholds (masterplan §5.2 L116).

  It is never a hypothesis test, never a forecast and never registered.
- **Cohort and exclusions.** 9988 and BABA are never one claim (V0 rows 13 and 19). `engine/hk_adr_bridge.py` pairs 9988.HK with BABA as `"direct"` (L75) and 0700.HK with KWEB as `"proxy"` (L85). KWEB is never a Tencent quote.
- **Outcome horizon.** None.
- **Data clocks.** `MARKET_US` (L180) and `MARKET_HK` (L182) are kept separate, each through `CLOCK_CALENDARS` (L190). NYSE close on date D precedes the next HK open (M0 L177). That is an ordering fact, not a lead-lag claim.
- **Feature set (names only).** Pair kind, FX leg and clock, staleness threshold.
- **Baselines / Split.** n/a.
- **Trial budget.** n = 4, declared defensively.
- **Proper score.** None. A basis is a diagnostic, not a guaranteed arbitrage.
- **Uncertainty and power.** None published as inference.
- **Kill / continue.** Dormant while there is no ADS-ratio owner (M0 gap 3) and spot CNH is proxied (M0 gap 5).
- **Pre-registered null.** None. Diagnostic only.
- **Retirement rule.** n/a.
- **Data gates / why NOT SUPPORTED.** V0 row 19 and M0 gap 3.
- **Authority flags.** All **false**.
