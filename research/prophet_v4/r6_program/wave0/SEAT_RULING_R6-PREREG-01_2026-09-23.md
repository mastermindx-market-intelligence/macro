# Seat ruling R6-PREREG-01 — pre-registration frame for D06/D07/D08 and the #7751 amendment

Fable Meta-CEO seat (session 48cdfd56), operation `prophet-us-fable-meta-ceo-20260923-001`, 2026-09-23. Adjudicates `wave0/OPUS_SCIENCE_SEAMS_AUDIT_2026-09-23.md` (Opus adversarial audit, PARTIAL). Authority: DEC:PROPHET-US-FABLE-META-CEO-DELEGATION (D06 economic margins/endpoints/formal-read law; D07 vintage eligibility; D08 fill/cost/latency). This ruling changes no source, model, policy or product state; it fixes what must be registered before any formal outcome read.

## Verification performed by the seat before ruling

- `ad48105910163e5709c75f28c0ae0edefa8eca57` is the squash of #7751 on `origin/main` (`git branch -r --contains` → origin/main). The frontier's "Merge ad481059…" obligation is satisfied.
- `research/prophet_v4/CELL_G_FLAGSHIP_VOI_MEASUREMENT_LAW_2026-08-22.md` is `SOL_FROZEN_RESEARCH_LAW`; no superseding record under `agentos/decisions/` or `research/DO_NOT_REBUILD.md` cites it. Under R6 §3 it is a current accepted evaluation contract (self-refutation item 1 of the audit fails; B2 stands).
- `research/prophet_v4/b4_entry_policy_calibration/PREREG.json`: C2 and C6 carry identical liquidity/gap parameters, as do C4 and C7 (six distinct configurations of eight labels); `decision_law.baseline_supported_only_if` tests "at least one adverse-tail endpoint"; `clock_law.cohort_start` = FIRST_PROSPECTIVE_B4_OBSERVATION_AFTER_PREREG_MERGE and `historical_backfill: false`. No live B4 runtime exists on main (#7581/#7738 are Draft), so no prospective observation has been captured: the amendment below is pre-capture by construction (self-refutation item 3 fails; M3/M4 stand).
- Whether the Evaluation owner already forbids pooling replay rows was not established from source; B4 is kept at B because its repair is a registration line with no downside.

## Dispositions (audit id → ruling)

| Id | Ruling | Registered consequence |
|---|---|---|
| B1 | ACCEPT | Cycle sleeve: unit of inference = cycle episode. Any Cycle claim is `DESCRIPTIVE_ONLY` unless Cell G effective-cluster floors are met on date, issuer AND cycle axes. H504 is descriptive-only and outside the embargo definition; the embargo is the longest CONFIRMATORY horizon graded. Fold count is computed and published before the first read. |
| B2 | ACCEPT | D06 step 1 binds Cell G as the governing measurement law. Every D06 closure artifact carries the Cell G §3 metric-contract fields: one primary endpoint per experiment; Holm across the registered family; fixed-look default; ≥ 50 matured episodes with N_eff(date) ≥ 20 and N_eff(issuer) ≥ 20; ZERO degradation margin on lead time, actionability and chase for any flagship-early claim; 70 % broad-coverage floor. Departures are forward-only versioned amendments. |
| B3 | ACCEPT | Every "better/earlier than" claim registers its control arms as same-tape computations built by B06: cash; SPY on the same clock with NO forward-fill; a point-in-time sector comparator frozen at decision time or declared `UNAVAILABLE_FIELD`; incumbent V3 on the identical field. A claim whose control is `UNAVAILABLE_FIELD` is capped at descriptive. QLedger's empty control leg is never synthesized. |
| B4 | ACCEPT | D07 registers `PUBLIC_INFO_REPLAY` as a named evidence class with a declared acquisition lag and a sensitivity analysis; it is never pooled with observed-as-run rows, carries no promotion weight, and bodies are read only through `read_event_source_revisions` / `read_all_event_source_revisions`. Per sleeve, D07 states whether any confirmatory read is possible before prospective accrual (Earnings H42: expected NO → prospective accrual is the confirmatory path). |
| M1 | ACCEPT | EL timing primary = same-clock, market-excess, full-opportunity difference (value per capital-day); the absolute result is supporting only; in-sample status of the current regime disclosed. |
| M2 | ACCEPT | Supporting horizons are descriptive-only with no rescue authority; prior legacy-ruler looks (H21/H42/H63) are logged in the trial ledger before the Earnings read; #7751 and the EL H10 timing study are ONE search family; H63 is flagged as crossing the next earnings event. |
| M3 | ACCEPT → amend #7751 before B05 goes live | See amendment spec below. |
| M4 | ACCEPT → same amendment | Alias map collapsing C6→C2 and C7→C4 (six configurations); unit = FIRST admissible decision instant per episode; N_eff(date) and N_eff(issuer) reported with every count; no both-tight cell now (interaction not sought at this stage). |
| M5 | ACCEPT | Q07/Q08 coverage is evaluated at each historical cut among issuers listed then; a terminal-value coverage floor is registered below which the result is `UNESTIMABLE`; the missing cohort is named. |
| M6 | ACCEPT | Q07 registers a finite ordered domain list and the readiness rule BEFORE inspecting any series; `NO_ADMISSIBLE_DOMAIN` is an admissible terminal outcome; domains inspected count in the search family. |
| M7 | ACCEPT | Current-only group membership = retrospective diagnostic with zero confirmatory credit; unit = group-episode; N_eff(theme) ≥ 5. |
| M8 | ACCEPT | Extraction audits are stratified by later outcome; deterministic XBRL facts are used wherever they exist. |
| M9 | ACCEPT | The D08 artifact classifies every fill/cost/latency/capacity field as MEASURED / ESTIMATED / UNKNOWN with its source; one fill convention across arms; a numeric cost range with source; historical pullback-arm fills are bounds only. #7734 supplies live NBBO facts only; #7738 constants stay uncalibrated until measured. |
| M10 | ACCEPT | Fixed look at the registered verdict count plus a futility horizon; every adjudication carries exemplar coverage, current-regime in-sample status, episode honest-N and the missing panel (repo §Adjudication coverage gate). |
| m1–m3 | ACCEPT | Aug-14 PIT-replay rows tagged in the evidence matrix; DNR kills (`FRESH-TICKS-WINDOW`, `STAGE-WIN-GATE`, `S10-MARGIN-RECLAIM`) checked for equivalence and counted as prior looks; Q03 registers `positive_label_id` and a retrieval-volume-matched placebo; Q02 registers the no-pick rule. |

Verdict adopted: D03/D06/D07/D08 are NOT closed. They close only through registration artifacts carrying the rows above, each accepted by an independent external reviewer before the first formal read.

## Amendment spec for #7751 (frozen; pre-capture; build unit `pu_w1_7751_amend`)

Files: `research/prophet_v4/b4_entry_policy_calibration/PREREG.json` and `research/prophet_v4/B4_ENTRY_POLICY_CALIBRATION_PREREG_2026-09-23.md` only (+ the existing test that pins the registration, if one exists). Add an `amendments` array with entry `A1` (date 2026-09-23, `pre_capture: true`, reason = this ruling), and register:

1. `alias_map`: `C6_TIGHT_LIQUIDITY_BASELINE_GAP → C2_TIGHT_LIQUIDITY`, `C7_BASELINE_LIQUIDITY_TIGHT_GAP → C4_TIGHT_GAP`; `distinct_configurations: 6` (C0, C1, C2, C3, C4, C5). Labels are retained for lineage; aliases never count as independent evidence.
2. `population.unit`: "first admissible decision instant per candidate episode" (one row per episode); `effective_n_reporting: ["N_eff_date", "N_eff_issuer"]`.
3. `primary_endpoint`: `mae` (max adverse excursion) at `primary_horizon_sessions: 10`; all other metrics and horizons `supporting_descriptive_only` with no rescue authority.
4. `multiplicity`: Holm correction across the five non-control distinct cells (C1–C5) on the primary endpoint; `search_family` includes the EL H10 timing study registered under D06.
5. `non_inferiority`: net excess vs C0 at H10 must satisfy lower confidence bound ≥ −25 bps; a nonsignificant point estimate is NOT non-inferiority.
6. `cost_floor_bps_round_trip: 50` registered as a FLOOR (not a measurement) pending the D08 measured range; a read using a lower floor is invalid.
7. `refused_rows_treatment`: full-opportunity — a row refused by a gated cell is carried at cash return over the horizon, never dropped.
8. `looks`: fixed look at 300 episodes per distinct cell; interim counts 50/100 are monitoring-only; `futility`: if at 150 episodes per cell the primary lower bound excludes any improvement for every cell, the study stops as REJECTED.
9. `decision_law` rewritten so "supported" requires the single primary endpoint (not any-of-K) plus the non-inferiority bound; "killed" retains the Pareto and non-identifiability rules.

Reviewer exclusion: the amendment's reviewer must not be its author or the seat. The lane's reviewer is GLM-5.3 (independent); the seat adjudicates and merges.
