# Entry Timing W2 — design registration: does entering at first persisted discovery beat waiting for curated admission? (2026-10-31)

**Status: DRAFT — UNFROZEN.** Nothing in this document is registered until (a) an independent
non-author review returns APPROVE-READY on the exact revision, (b) the frozen-field block below is
mirrored into a machine freeze, and (c) the freeze commit SHA is written into this header. Until
then every number here may change, and no outcome, price, grade or paired-race surface has been or
may be read for the population it names. Authority: measurement design only. No trade, sizing,
alert or capability authority follows from any result of this study.

**Separate registration.** This is a new study with its own hypothesis. It does not change, read
into, or borrow samples from the B4 entry-policy calibration preregistration (#7751, amendment A1,
machine freeze `research/prophet_v4/b4_entry_policy_calibration/PREREG.json`), whose population,
H10 MAE primary endpoint, 50 bps cost floor, Holm family, fixed looks and refusal handling are
untouched. It does not change the frozen W3 paired race (`research/prophet_fusion/W3_RACE_PREREG.md`)
or reopen Entry Timing W0. Where this study reuses a B4 or W3 constant it says so and quotes it;
reuse is not amendment. Arms are named `T0…T3` precisely so that no name collides with the B4 cells
`C0…C5` or the August bake-off's "C0 incumbent" lane.

**Inputs this design stands on (all committed, read-only):** the W1 r2 intake waterfall and
identity replay (`research/prophet_v4/ENTRY_TIMING_W1_INTAKE_WATERFALL_2026-10-31.md`, PR #10277;
27 sessions 2026-08-26 → 2026-10-23, 88,325 inputs / 15,511 mapped / 72,814 refused, 0 refusals
resolvable at their session), the SELECTED B1 candidate-episode generation
`peg:23be3409c3a57944dd08e09e38e3b7541926c0f244e9d0d3b4a0b4a8aacedbf9`, the completion brief
(`research/prophet_v4/PROPHET_US_ENTRY_TIMING_COMPLETION_BRIEF_2026-10-31.md` at
`e757498822a2`, §Scientific audit and research design), and the B4/W3 freezes named above.

## 1. Question and hypothesis

The brief's W2 question, verbatim: *"Given the same pre-policy population and information actually
available at each cut, does a proposed timing rule move executable entry earlier by an economically
useful amount without an unacceptable increase in false starts or missed upside?"*

**Proposed timing rule under test (the candidate).** Enter at the first executable opportunity
after an episode's **first persisted discovery** — the session on which the candidate-episode
intake first recorded the episode (W1 r2 clock) — instead of waiting for the episode's security to
appear in a **curated-tier candidate stamp** (the incumbent proxy, §3). The contrast is chosen for
identification, not for ambition: both instants exist as-known in the committed episode store for
every episode of the historical segment, so the lead between them is measurable without
reconstructing any production policy, and the matched-delay arm separates *waiting* from
*selection* (the curated stamp selects a subset; a fixed delay does not).

**H_W2 (one-sided, pre-declared).** On the same admissions, the candidate arm's H10 net excess
return is non-inferior to the incumbent proxy (lower confidence bound ≥ −25 bps, the B4 bound,
quoted not amended) AND its lead is ≥ 1 session at the median AND its additional false-start cost
is within the tolerance of §6. Failing any one of the three → not promoted. A result that only
shows the incumbent proxy is *selecting* better names (the matched-delay arm matches the incumbent
and the candidate does not) is a selection finding, not a timing finding, and is reported as such.

## 2. Population (frozen before any policy is applied)

| Field | Frozen value |
|---|---|
| Universe | every intake input row of the SELECTED B1 generation named above, mapped **and** refused, on the W1 r2 session clock; no ticker named by hand, no widening, no favorable subset |
| Unit | an **admission**: one episode (its `episode_id`, security, identity epoch) with its first persisted discovery session `S_disc`; plus one **validly-refused unit** per distinct (ticker, first refused session) that never mapped — carried with its typed class (`IDENTITY_UNRESOLVED` / `ISSUER_UNRESOLVED` / `MISSING_STRUCTURAL_ANCHOR` / `ACTIVE_EPISODE_DIFFERENT_ANCHOR`), no entry under any arm, declared cash return 0, counted in every per-100-eligible denominator |
| Historical segment R | admissions with `S_disc` in 2026-08-26 → the freeze date; 1,087 episodes opened in the generation as of 2026-10-23 (all opened by turn_watch, the only source with a structural anchor); exact counts restated at freeze from the pinned generation |
| Prospective segment P | admissions with `S_disc` after the freeze date, accrued by the existing nightly intake; no backfill |
| Identity | the episode's `security_id` / `identity_epoch` as recorded; as-known membership is the W1 r2 reference clock; the 11,153 reference-widened refusals stay refused in R (append-only ledger), exactly as W1 found them |
| Economic rights | the grader's adjusted basis (W3 grader, §5); the CTVA distribution crossing and any entitlement the Data OS owner has quarantined are excluded by the owner's list, declared at freeze, never by outcome |
| Anchor rule inherited | the turn_watch structural anchor (`reset_low`, adjusted-close basis) carried on the episode's OPENED event; `ACTIVE_EPISODE_DIFFERENT_ANCHOR` rows are refusals of a *second* anchor for an already-open episode and are neither false starts nor misses — they are reported as validly refused (W1 r2 denominator fact 3) |
| Effective N | `N_eff_date` (distinct `S_disc` sessions with a matured H10) and `N_eff_issuer` (distinct issuers), both printed with every estimate; honest-N floor 20 distinct matured admission sessions for any promotion claim (the W3 floor, quoted) |

**Falsifier (binding from freeze):** removing any refused unit may not change any arm's paired
estimate (refused units have no entry under any arm) and must *reduce* every per-100-eligible
figure's denominator visibly. An analysis whose primary improves when a refused class is dropped
is rejected as a population leak.

## 3. Decision instants and arms (the three delays, measured separately)

Per admission the study records six instants, unknown ends null, never imputed:

| Instant | Definition | Availability in R | in P |
|---|---|---|---|
| `t_obs` first source-knowable observation | turn_watch trigger date (`min(trigger.last_date)` = the event's `occurred_at`); candidate stamp session for candidate rows | recorded | recorded |
| `t_disc` first persisted discovery | session of the source document the row was first read from (W1 r2 clock; for turn_watch the document `data_session` recovered by receipt) | recorded | recorded |
| `t_vis` first honest user visibility | first protected board/journey render proven to have shown the episode | **null** unless a committed render receipt proves it; never inferred | from the R7 journey receipts when they exist |
| `t_auth` first policy-authorized entry | B4 C1 first admissible instant | **null** (no durable B4 capture exists for R) | B4 capture rows, read only |
| `t_exec` first executable opportunity | the open of the first session after the instant that defines the arm (a close-confirmed signal is knowable only after its close) | modeled | modeled |
| `t_fill` observed fill | independently observed by its owner | null | null unless supplied |

Lateness is attributed to the interval that actually lengthened (`t_disc − t_obs`,
`t_cur − t_disc`, `t_exec − t_cur`). W1 r2 measured the first of these: 1,376 of 1,694 turn_watch
events have `t_obs` before `t_disc`, by up to months; **`known_at` on a turn_watch event equals
`t_obs` and is therefore never used as a decision instant here.**

Arms, all on the same admissions, all with `t_exec` = next session open and the §5 execution model:

| Arm | Entry instant | Role |
|---|---|---|
| `T0` immediate first-executable | open of `t_disc + 1` | the candidate (enter at discovery) |
| `T1` incumbent proxy | open of `t_cur + 1`, where `t_cur` is the first session on which the episode's security appears in a **curated-tier** candidate stamp (`tier == curated` in `data/us_prophet_rank/candidates/`), `t_cur ≥ t_disc` | the production notion of admission in R; in P it is **replaced** by `t_auth` from the B4 C1 capture and the proxy is reported alongside |
| `T2` prespecified simple delay | open of `t_disc + 1 + k`, **k = 2 sessions**, fixed here before any outcome | isolates waiting per se |
| `T2m` matched delay | open of `t_disc + 1 + k*`, where `k*` = median over admissions with a `t_cur` of (`t_cur − t_disc`), computed once at freeze from the pinned generation's sessions only (no prices) and written into the freeze | matched-delay comparator: same wait as the incumbent proxy, no selection |
| `T3` union early-turn admission | the `engine/us_early_turn.py` union admission instant, if and only if it can be reconstructed as-known from committed artifacts for ≥ 90 % of R admissions | secondary candidate; otherwise **unidentified** in R and declared so at freeze |

Untriggered cases stay in the population: an admission with no `t_cur` (never curated) has no `T1`
entry; its `T0` outcome is reported under **missed upside / avoided loss of the incumbent**, never
dropped and never silently paired.

## 4. Outcomes, horizon, primary and secondary endpoints

| Field | Frozen value |
|---|---|
| Grader | the ONE W3 grader (`engine/us_prophet_w3.py`, `excess_spy`, adjusted basis); reused, not re-implemented; its receipt pinned at freeze |
| Maturity horizon | **H10** sessions after `t_exec` (equal holding period after fill) — the B4/W3 horizon, quoted; a second reading at a **common expiry** `t_cur + 10` from the incumbent admission is reported for every arm so that "same end date" and "same holding period" are both visible |
| Cost floor | **50 bps round trip** applied to every entered arm, the B4 floor until D08 supplies measured costs (quoted) |
| Primary endpoint | paired per-admission difference `T0 − T1` in H10 net excess return (bps), over admissions with both entries |
| Primary decision | promote only if lower one-sided 95 % bound ≥ −25 bps (B4 non-inferiority bound, quoted) AND median lead ≥ 1 session AND §6 false-start tolerance holds; otherwise retain-in-shadow (R) / reject (P) per §7 |
| Secondary endpoints (Holm within the family) | `T0 − T2`, `T0 − T2m`, `T3 − T1` (if identified) on net excess; lead in sessions (`t_exec(T1) − t_exec(T0)`); false-start rate per arm; missed-winner count and return per 100 eligible; maximum adverse excursion within H10; time in capital |
| Inference | paired estimates with a session-cluster block bootstrap (overlapping H10 windows purged by `S_disc` cluster), `N_eff_date` and `N_eff_issuer` printed; by era (pre/post 2026-10-11 reference ingest), by source tier, by liquidity bucket, by regime label as recorded at `t_disc` |

## 5. Execution model and point-in-time rules

* **Knowability.** The nightly records a session after its close; a signal recorded on session S is
  knowable after S's close and executable at the open of S+1. Nothing enters at S's close.
* **Fill.** Full fill at the official open of `t_exec`, no partial fills, no slippage beyond the
  cost floor; price basis: open for entry, adjusted close for invalidation and for the anchor (so a
  bar that touches both entry and invalidation has a defined order: entry at open precedes close).
* **Gaps.** The primary enters regardless of the open gap; a sensitivity bound refuses entries whose
  open gap exceeds 1.5 ATR from the prior close (the B4 C1 `max_open_gap_atr`, quoted) and is
  reported as the conservative bound; the primary is the optimistic bound. A conclusion that flips
  between the two bounds is **unidentified**, not promoted.
* **ATR.** The owner-supplied ATR where the episode carries one; otherwise a 14-session
  close-to-close range proxy from the grader's series, declared here and flagged per admission.
* **Halts, delistings, missing sessions.** Unknown ends null; an H10 window crossing a
  `session_missing` W3 session is reported as censored, never filled from Pages or any later
  vintage. Delistings stay visible as their own row.
* **Freeze before holdouts.** Normalization, the k and k* constants, the exclusion list and the
  arm definitions are frozen at the freeze commit; the R segment is read **once**, after freeze and
  review approval; any later change opens a new version/era of this study, never an amendment of
  the result.
* **Corrections and retractions** in the episode store (`correction_of`) are preserved: a corrected
  OPENED event keeps its original `t_disc`; a retracted episode stays in the population as retracted.

## 6. Tolerable additional false-positive cost (declared now)

**False start** := within H10 after `t_exec`, a session close below the episode's structural anchor
(`reset_low`, adjusted basis) occurs before any close ≥ entry + 1.0 ATR. **Missed winner** := an
admission without a `T1` entry whose `T0` H10 net excess ≥ +1.0 ATR equivalent.

Tolerance, both required: (i) the candidate's false-start rate may exceed the incumbent proxy's by
at most **10 percentage points absolute** on the same admissions — the August bake-off's earlier
lanes ran 22–27 % false bounces against 3.1 % for the actioned incumbent and that regime was judged
unacceptable; this bound keeps the candidate well inside it; (ii) the loss attributable to false
starts (sum of their H10 net excess, bps) per 100 eligible admissions may not exceed the
incumbent proxy's by more than **150 bps per 100 eligible**. Both are printed per 100 eligible
(population denominator, refused units included) and conditional per fill.

## 7. Looks, multiplicity, dispositions and what cannot happen

* **R segment:** one look, after freeze. It can yield **reject** or **retain-in-shadow**, never
  promote — it is a frozen-before-read retrospective read of public outcomes, not a prospective
  test. If `N_eff_date` < 10 it is **unidentified**.
* **P segment:** looks at 50 and 100 admissions are monitoring only and cannot promote; 150 is the
  futility look (stop if the primary's upper bound < 0); 300 admissions per arm is the fixed look
  (the B4 look schedule, quoted). Promotion requires P.
* **Multiplicity:** one primary contrast; Holm over the secondary family of §4; every tried
  variant, including an unidentified `T3`, is counted and reported with the negative results.
* **Dispositions:** promote / retain-in-shadow / reject / unidentified, each with dates,
  denominators, error bands, `N_eff`, and the disproof-case table below. "Promote" means the
  candidate may be proposed to the B4 owner as a distinct future trial; it never alters #7751 A1,
  never changes a production policy by itself, and never confers trade, sizing or alert capability.

### Cases that must be exercised before any disposition (brief §Cases that can disprove a superficial repair)

| Case | What this study must show |
|---|---|
| CRI | the mapped episode and its identity-suppressed siblings appear with their refusal class; signal (`t_obs`), recording (`t_disc`), visibility (`t_vis`, null if unproven) and decision clocks stay separate; nothing minted from ticker/date |
| RCL / CSCO | the field that set `t_cur` is traced; the early receipt and later low are shown on both clocks; what was knowable before and after the turn is replayed, not narrated |
| AMZN / USFD / WM / KO | full population, entitlement, feature rank, shown card and first protected response are four distinct rows; where visibility cannot be proven `t_vis` is null and the earliest retained evidence is shown |
| CTVA + a real loser / no-trigger | entitlement reconciled through the Data OS owner's exclusion list; a winner paired with a prespecified failed starter, no-trigger, halt or invalidation case selected by rule (first in `S_disc` order meeting the §6 definition), never by outcome |
| STLD / NEM | the two known mechanical fires from #5370's fixtures are configuration regressions run against the arm code, never members of R or P |

## 8. What this registration does not authorize

No outcome read before freeze; no change to B4 #7751 A1, its capture, its cells, or W3; no
historical backfill into P; no new data-purpose grant; no production, board, alert or trade effect.
The B-17 historical population (7,918 C0 episodes, none with a complete 34-session window) is not
this study's R segment and is not substituted by it; B-17 stays null. Required before freeze:
independent non-author review of this exact revision; the Data OS owner's entitlement exclusion
list; `k*` computed from sessions only; the grader receipt; and a machine freeze mirroring §2–§7.

## Frozen-field block (to be mirrored into the machine freeze at freeze time)

```yaml
schema: us.prophet_entry_timing_w2_design/v1
status: DRAFT_UNFROZEN
parents: [B4 PREREG.json (quoted constants only), W3_RACE_PREREG.md (grader, floor), ENTRY_TIMING_W1 r2]
generation_id: peg:23be3409c3a57944dd08e09e38e3b7541926c0f244e9d0d3b4a0b4a8aacedbf9
population_unit: admission (episode first persisted discovery) + validly_refused units
segments: {R: {from: 2026-08-26, to: <freeze date>, looks: 1, may_promote: false}, P: {from: <freeze date>, looks: [50, 100, 150, 300]}}
clock: {t_disc: W1 r2 document/observation session, t_exec: next session open, known_at_is_not_a_decision_instant: true}
arms: {T0: t_disc+1, T1: t_cur+1 (R proxy; P uses B4 C1 t_auth), T2: t_disc+1+2, T2m: t_disc+1+k_star, T3: union early-turn if identified}
k_fixed_sessions: 2
k_star: <median(t_cur - t_disc) at freeze, sessions only>
horizon_sessions: 10
common_expiry: t_cur + 10
cost_floor_bps_round_trip: 50
primary: {contrast: T0 - T1, endpoint: h10_net_excess_bps, non_inferiority_lower_bound_bps: -25, min_median_lead_sessions: 1}
false_start: close < reset_low before any close >= entry + 1.0 ATR within H10
tolerance: {false_start_rate_delta_pp_max: 10, false_start_loss_bps_per_100_eligible_delta_max: 150}
honest_n_floor_sessions: 20
multiplicity: Holm over secondary family
dispositions: [promote, retain_in_shadow, reject, unidentified]
authority: measurement only; no trade/sizing/alert; never amends #7751 A1
```
