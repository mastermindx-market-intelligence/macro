# Prophet B4 Entry-Policy Calibration — Prospective Same-Tape Preregistration

**Status:** `REGISTERED_OUTCOMES_UNREAD`  
**Registration date:** 2026-09-23  
**Protected procedure at registration:** `Mastermind@b4493b52810a43a413e381a07e1194ca905b4851` / `mastermind.sol_skillpack.v1` 1.0.1 / bootstrap-major 1  
**Macro base:** `dcd501558d2e2e2d1e2070ca7ef4c63298f88350`  
**Machine-readable freeze:** `research/prophet_v4/b4_entry_policy_calibration/PREREG.json`

## Purpose

#7738 correctly marks the first B4 `liquidity_fillability` and `gap_velocity` constants as `INITIAL_OPERATION_CONSTANT_NOT_CALIBRATED`. This registration freezes the first empirical comparison **before any B4 policy outcome is read**. It creates research/evaluation evidence only. It cannot rank, admit, recommend, size, execute, trade, or silently promote a threshold.

The question is not “which threshold makes today’s winners pass?” It is: on the unchanged `EARLY_LEADERSHIP_SECTOR_ROTATION` candidate population, do the initial controls improve fillability/adverse-path quality without destroying strategy coverage or benchmark-relative outcome quality?

## Existing owners remain binding

This study does not recreate any owner:

- #7738 remains the policy owner (`b143e7000b6afa003a15a7f934f4aaf099968d42`).
- #7734 remains the live NBBO/current-session-open measurement substrate (`55e8671317af3219785e7a14e490028a9933daa4`).
- #7584 remains the identity/basis/provenance prerequisite (`87f85e88f75bf037e4f917ee30313444f766bb62`).
- #7581 remains the sole B4 runtime adapter (`39ef2cd48e091d90f12771aab142c2197022aa79`).
- Existing candidate lifecycle, session eligibility, risk ceiling, entry geometry/invalidation, quote/source-health, and outcome/evaluation owners remain authoritative.

The Entry Radar replay estate is reuse precedent only: its PIT vendor plane already defines same-basis OHLC, point-in-time NBBO cost semantics, later-attached outcomes, and conservative missing-NBBO treatment. This registration does **not** promote Entry Radar replay into a live Prophet owner and does not create a second replay/event/outcome store.

## Clock and population law

The cohort begins with the **first prospective B4 observation after this preregistration is accepted and landed**. No historical backfill is allowed. No previous B4 outcome may be reconstructed to enlarge N.

One observation is one pre-B4, strategy-eligible candidate episode at one decision instant. The candidate set is frozen before applying the study cells. Named tickers cannot be inserted, removed, or forced for study convenience. Every cell sees the same eligible observations; unavailable source/basis facts are counted as unavailable rather than silently dropped.

Decision-time facts must be captured before outcomes: candidate/episode identity, strategy/horizon identity, current price, same-basis session open and previous close, owner ATR, bid/ask and NBBO timestamp, source/license identity, basis/provenance receipt, and accepted entry geometry. Outcome fields attach only later.

## Frozen cells

`PREREG.json` freezes eight cells. `C0` is observe-only. `C1` is the current #7738 baseline (50 bps / 300 s; 1.5 / 1.0 / 1.5 ATR). `C2/C3` isolate tighter/wider liquidity. `C4/C5` isolate tighter/wider gap/velocity. `C6/C7` test the two conservative one-axis combinations without opening an unconstrained tuning grid.

There are no post-outcome threshold additions. Any new cell is a new preregistration and consumes a new evidence era.

## Outcomes and evidence floor

Primary horizons are 5 and 10 sessions; 3 and 15 sessions are secondary. Every cell reports the whole scorecard: retained coverage versus C0, net return after measured-or-floor costs, excess versus benchmark and sector, MFE, MAE, target-before-invalidation, invalidation-first, time-to-positive, realized cost basis, and unusable/missing-NBBO rate.

Capacity is **not** modeled by #7738 v1 and this study cannot claim capacity. Source/basis missingness is an outcome of the data path, not permission to exclude difficult rows.

Verdict-grade floor is 300 prospective eligible observations per cell. Counts at 50 and 100 are accrual diagnostics only and cannot promote policy. Reporting must keep confidence intervals and effective N beside point estimates; repeated peeking cannot authorize a threshold change.

## Decision law

The baseline can receive **support for further adjudication**, never automatic promotion, only if all are true:

1. it lies on the observed coverage-versus-adverse-tail Pareto frontier;
2. at least one preregistered adverse-tail endpoint improves versus C0 with confidence support;
3. primary net excess is not confidence-supported worse than C0; and
4. basis/source/clock coverage is sufficient that the comparison is not selection-by-missingness.

The baseline is killed as a gate candidate for this era if it is Pareto-dominated by C0 or a preregistered challenger, worsens adverse-tail behavior without compensating evidence, or cannot be identified because the required decision-time facts are systematically unavailable/incomparable.

Any threshold replacement, gate promotion, recommendation authority, or capacity claim requires a separate owner adjudication after the frozen result exists.

## Exact next executable edge

After #7734 and #7584 are accepted and the incumbent #7581 adapter can observe the owner facts, extend the **existing prospective evaluation path** with this frozen cell set and append-only decision-time stamps. The evaluator must reuse the incumbent outcome ledger/forward ruler and Entry Radar cost semantics where compatible; it must not create a new outcome authority. The first run is capture-only. Outcome attachment occurs only when the declared horizons mature.

Until that edge exists, this carrier is a preregistration receipt, not evidence that the thresholds work.

## Amendment A1 (2026-09-23, pre-capture)

Capture has not started: there is no live B4 runtime on main. This amendment is therefore pre-capture. It makes the following nine changes.

1. `C6` now points to `C2`, and `C7` now points to `C4`. These are aliases, not new evidence, so the study has six distinct configurations: C0 through C5. All eight original labels remain in the record.
2. The study population is the first admissible decision instant for each candidate episode. Reports must show effective N by date and by issuer.
3. Maximum adverse excursion at 10 sessions is the sole primary endpoint. Every other metric and horizon is descriptive support only and cannot rescue a result.
4. Holm correction applies to the five non-control distinct cells, C1 through C5, for the primary endpoint. The declared search family includes the EL H10 timing study registered under D06.
5. At 10 sessions, a cell is non-inferior to C0 only if the lower confidence bound for net excess is at least −25 basis points. A nonsignificant point estimate is not non-inferiority.
6. The round-trip cost value is a 50 basis point floor, not a measured cost. A read using a lower floor is invalid until D08 supplies the measured range.
7. A row refused by a gated cell stays in the study at cash return over the declared horizon; it is never dropped.
8. The fixed look is 300 episodes for each distinct cell. Counts at 50 and 100 are monitoring only. At 150 episodes per cell, if every cell's primary lower bound excludes any improvement, the study stops as rejected.
9. A cell is supported only by the single primary endpoint with its non-inferiority bound; the old any-of-K support path is superseded. Pareto dominance and non-identifiability remain grounds to kill a cell. The original decision-law arrays are preserved under `decision_law.superseded_by_A1`.

The clock law still forbids historical backfill, the cohort start is unchanged, and all research-only authority flags remain false. This record authorizes evaluation only; it does not rank, admit, size, execute, trade, or promote policy.
