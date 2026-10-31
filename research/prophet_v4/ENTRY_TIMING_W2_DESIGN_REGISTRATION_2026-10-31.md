# Entry Timing W2 — design registration: does entering at first persisted discovery beat waiting for the BUY-lane admission? (2026-10-31, revision 2)

**Status: DRAFT — UNFROZEN.** Nothing in this document is registered until (a) an independent
non-author review returns APPROVE-READY on the exact revision, (b) the frozen-field block below is
mirrored into a machine freeze, and (c) the freeze commit SHA is written into this header. Until
then every number here may change, and no outcome, price, grade or paired-race surface has been or
may be read for the population it names. Authority: measurement design only. No trade, sizing,
alert or capability authority follows from any result of this study.

**Revision 2 (review round 1 → REVISE).** The round-1 incumbent proxy "first curated-tier stamp"
was shown, on dates and tickers alone, to be a universe tier rather than an admission: 916 of
1,087 opened episodes were already curated before discovery and 77.3% of the 970 with a curated
stamp had zero lag, so the T0−T1 contrast was degenerate by construction. Revision 2 replaces it
with the BUY-lane placement (§3), declares the identity join (§2), pins the price path source and
fill basis to the existing grade producer (§5), makes the primary intention-to-treat (§4), states
the delayed-arm and exit rules (§5), fixes the eligible denominator to turn_watch units (§2), and
declares W2's own futility rule (§7). Every count quoted in this revision was produced by a
dates-and-tickers census (`research/prophet_v4/entry_timing_w2_t1_census.py`, no price, grade, outcome or paired-race
column read); the census is re-run and attached at freeze.

**Separate registration.** This is a new study with its own hypothesis. It does not change, read
into, or borrow samples from the B4 entry-policy calibration preregistration (#7751, amendment A1,
machine freeze `research/prophet_v4/b4_entry_policy_calibration/PREREG.json`), whose population,
H10 MAE primary endpoint, 50 bps cost floor, Holm family, fixed looks and refusal handling are
untouched. It does not change the frozen W3 paired race (`research/prophet_fusion/W3_RACE_PREREG.md`)
or reopen Entry Timing W0. Where this study reuses a B4 or W3 constant it says so and quotes it;
reuse is not amendment. Arms are named `T0…T3` so that no name collides with the B4 cells `C0…C5`
or the August bake-off's "C0 incumbent" lane. A B4 capture instant (`t_auth`), once capture exists,
may appear as a descriptive column only; it is never this study's comparator (review F7).

**Inputs this design stands on (all committed, read-only):** the W1 r2 intake waterfall and
identity replay (`research/prophet_v4/ENTRY_TIMING_W1_INTAKE_WATERFALL_2026-10-31.md`, PR #10277,
head d03acfd0; 27 sessions 2026-08-26 → 2026-10-23, 88,325 inputs / 15,511 mapped / 72,814 refused,
0 refusals resolvable at their session), the SELECTED B1 candidate-episode generation
`peg:23be3409c3a57944dd08e09e38e3b7541926c0f244e9d0d3b4a0b4a8aacedbf9` (1,087 OPENED, all
turn_watch), the US candidate stamps `data/us_prophet_rank/candidates/YYYY-MM.parquet`
(54 stamp dates 2026-07-31 → 2026-10-29; `lane`, `tier`, `featured` populated on 35 of them, last
2026-10-19; `buyable`/`eligible` on all 54), the lane rules in `engine/us_candidate_lanes.py`
(`_classify_buy_row`, `build_candidate_pool`), the grade producer `engine/us_prophet_grades.py`
(next-bar close fill, positional horizons, SPY benchmark from `data/yahoo/SPY.parquet`), the
per-ticker dividend-adjusted close panel `data/yahoo/<TICKER>.parquet` (columns `close_price`,
`close`, `volume`; no open/high/low), the completion brief
(`research/prophet_v4/PROPHET_US_ENTRY_TIMING_COMPLETION_BRIEF_2026-10-31.md` at `e757498822a2`,
§Scientific audit and research design), and the B4/W3 freezes named above.

**Prior knowledge disclosed (review m9).** The brief records that the curated BUY surface
underperformed over a window overlapping R. The authors knew this before writing revision 1. It
is a reason to expect T0−T1 ≥ 0 and is therefore exactly the direction a selection-only artifact
would also produce; §3 and §4 are written to separate the two.

## 1. Question and hypothesis

The brief's W2 question, verbatim: *"Given the same pre-policy population and information actually
available at each cut, does a proposed timing rule move executable entry earlier by an economically
useful amount without an unacceptable increase in false starts or missed upside?"*

**H_W2 (one-sided, primary).** For the same admitted candidate episodes, entering at the first
executable session after persisted discovery (T0) is not economically inferior, net of the cost
floor, to entering at the first executable session after the incumbent BUY-lane admission (T1),
while leading it by at least one session in median. The null is that T0 is inferior by more than
the non-inferiority margin, or leads by less than one session, or breaches the declared tolerance.

**What is being separated.** Three delays, measured separately and never merged: discovery →
persisted (the intake clock, already measured in W1), persisted → admitted to the BUY lane (the
incumbent's wait), admitted → executable (the fill rule). T1 waits for the second delay and T0 does
not; everything else (population, fill rule, horizon, cost, outcome) is identical between arms.
The study is NOT a selection study: an episode's T1 return is read whether or not the BUY lane ever
admitted it (§4, intention-to-treat), so a difference cannot come from T1 cherry-picking the
subset the lane later liked.

## 2. Population (frozen before any policy is applied)

| Element | Definition (frozen) |
| --- | --- |
| Admission unit | Every OPENED event in the pinned generation: one per candidate episode, keyed by `episode_id`; `payload.security_id` + `payload.identity_epoch` are the identity, `payload.ticker_at_observation` is a label only. |
| Discovery session `S_disc` | The W1 r2 receipt-recovered document `data_session` of the OPENED row's `source_receipt` (turn_watch), not `known_at`, not `occurred_at`. Rows whose receipt is unrecoverable (W1 r3: 1 event) are UNKNOWN units. |
| Refused units | IDENTITY_UNRESOLVED and MISSING_STRUCTURAL_ANCHOR suppressions whose `source_receipt` is a turn_watch document (W1 r3 basis), excluding `ACTIVE_EPISODE_DIFFERENT_ANCHOR` (those rows belong to episodes that already mapped, review F9). Candidate-tier and doors refusals are reported in the waterfall but are not in the eligible denominator. "Never mapped" is judged as of the pinned generation, not the future. |
| Eligible denominator | admissions + refused turn_watch units (as above). Tolerance (ii) in §6 is judged **per 100 admissions**; the per-100-eligible version is printed beside it, never substituted. |
| Identity join for T1 (review F2) | Candidate stamps carry `ticker` only. A stamp joins an episode when `VendorAliasTable.resolve("membership", ticker, on=stamp_date)` (the W1 r2 as-known reference, `lib.dataos.identity`) returns the episode's `security_id` within its `identity_epoch`. A ticker that does not resolve on that stamp date gives T1 = UNKNOWN for that stamp, never "never admitted". No identity is minted from a ticker and a date (brief: CRI case). |
| Segment R (retrospective) | Admissions with `S_disc` from 2026-08-26 to 2026-10-23 inclusive in the pinned generation (the generation is pinned as of 2026-10-23; later admissions belong to P). One look. **R can never promote.** R is read only after every R unit's longest window has matured: `S_disc` + 1 + K + H sessions = 2026-10-23 + 21 trading sessions ≈ 2026-11-23; the exact session is written at freeze. |
| Segment P (prospective) | Admissions with `S_disc` after the freeze date. Each P look uses the generation current at the look, pinned by its `peg:` id in the look record; admissions are keyed by `episode_id` and never re-opened or re-read under a later generation. Looks per §7. |
| T1 coverage (review F6) | `lane` is populated only on stamp dates up to 2026-10-19. A unit whose T1 window (§3) contains a stamp date without lane coverage has T1 = CENSORED unless a BUY-lane stamp was already observed earlier in the window. CENSORED and UNKNOWN units are excluded from the primary and counted in the waterfall; they are never scored as "late" or "never". In R, identified T1 therefore requires the full K-session window to end on or before 2026-10-19 (`S_disc` ≤ 2026-10-05); later R admissions are CENSORED for T1 and still scored for T0. |
| Entitlement | The Data OS owner's exclusion list (securities whose price panel may not be used for this purpose) is applied before any outcome read; it is pinned at freeze as a list of `security_id`s, and every exclusion is counted in the waterfall. |
| Minimum identified pairs | 30 primary pairs (admissions with identified T0 and T1) per segment look, else the look is UNIDENTIFIED. This is W2's own floor. W3's 20-session count is a guardrail tripwire inside W3 and is not reused here (review m1). |

## 3. Decision instants and arms

Six instants are recorded per admission; any that cannot be proven as-known is NULL, never imputed.

| Instant | Meaning | Source |
| --- | --- | --- |
| `t_obs` | the bar the anchor was observed on | OPENED `occurred_at`, informational only |
| `t_disc` | the session the discovery was persisted and readable (`S_disc`) | W1 r2 document session |
| `t_cur` | the first stamp date ≥ `t_disc` whose row for the episode's security has `lane == "buy"` | candidates parquet, §2 join, §5 knowability |
| `t_vis` | first session the security was visible on a public board | NULL in R unless proven from committed site artifacts; descriptive |
| `t_auth` | a B4 capture authorization instant | NULL in R; descriptive only in P once capture exists; never the comparator |
| `t_exec` | the fill session of an arm (§5) | derived |

**Arms.** Each arm is a rule for `t_exec` given only information readable at or before that session.

| Arm | `t_exec` | Role |
| --- | --- | --- |
| T0 | `t_disc + 1` | challenger: enter at first persisted discovery (the brief's "immediate" and "candidate" arms coincide here, review n2; stated explicitly, there is no fourth arm) |
| T1 | `t_cur + 1` if `t_cur` ≤ `t_disc + K`, else no entry (cash) | incumbent: the BUY-lane admission, one definition in R and P |
| T2 | `t_disc + 1 + k`, k = 2 fixed | fixed short wait |
| T2m | `t_disc + 1 + k*`, k* = median(`t_cur − t_disc`) in stamp-grid sessions over R's identified pairs, computed from dates only at freeze | median-wait mimic; if k* = 0 or k* = k, T2m is UNIDENTIFIED and stays in the counted family (review F11) |
| T3 | union early-turn signal (`engine/us_early_turn.py`) | only if reconstructable as-known for ≥ 90% of R admissions; the gate is evaluated at freeze and the family is fixed then (review m8) |

`K = 10` sessions is the admission wait cap: an incumbent admission later than 10 sessions after
discovery is treated as no admission within the decision window, and T1 is cash for that unit.
K is a frozen constant, chosen so that T1's hold (§4) can still mature on the same price panel as
T0's within one calendar month.

**Why the BUY lane is the incumbent (review F1).** The lane is the surface the product tells a
user to act on; `_classify_buy_row` in `engine/us_candidate_lanes.py` admits a row only after the
buy gates. The dates-only census over the 1,087 OPENED episodes (ticker join, `opened_session` as
the `t_disc` stand-in; the freeze re-run uses the W1 r2 session and the §2 identity join):

| T1 candidate definition | admissions with a stamp ≥ `t_disc` | never | already before `t_disc` | zero-lag share | median lag (grid sessions) | IQR |
| --- | --- | --- | --- | --- | --- | --- |
| `tier == curated` (rev 1) | 970 | 117 | 916 | 77.3% | 0 | 0–0 |
| `lane == "buy"` (rev 2 T1) | 365 | 722 | 174 | 6.0% | 14 | 5–23 |
| `buyable == True` (sensitivity T1b) | 509 | 578 | 201 | 3.5% | 20 | 9–27 |
| `featured == True` | 84 | 1,003 | 24 | 4.8% | 17 | 5–24 |

The curated tier is a universe (median 2,932 rows per stamp); the BUY lane is an admission (median
61 rows per stamp). "Already before `t_disc`" means the ticker held a BUY-lane row at an earlier
stamp; such a unit's T1 is still the first BUY stamp ≥ `t_disc` (lead 0 if the row persists), and
the flag is reported descriptively. **T1b** (`buyable == True`, full 54-date coverage) is a
declared sensitivity definition, descriptive and non-promoting; it is not in the promotion family.
With the BUY lane, roughly one third of admissions get an identified T1 inside K = 10 (140 of 365
stamped within 10 grid sessions in the census), which is why §2 sets a 30-pair floor and why R
may only inform P's design, never promote.

## 4. Outcomes, horizon, primary and secondary endpoints

| Element | Definition (frozen) |
| --- | --- |
| Price path source | `data/yahoo/<TICKER>.parquet` column `close` (dividend-adjusted), resolved through the §2 identity join at each session; benchmark `data/yahoo/SPY.parquet` `close`. Pinned at freeze by the commit SHA of the panel read. This is the same source and basis the existing grade producer uses. |
| Fill basis | **next-session close** (`engine/us_prophet_grades.py`: "entry is the close of the bar STRICTLY AFTER the stamp bar"). The panel has no open column, so an open fill is not computable from the pinned source; revision 1's open-fill model is withdrawn. This matches the brief's native ruler. |
| Hold and horizon | H = 10 sessions from each arm's own fill (positional on the price index). Exit is a **time exit** at the close of the 10th session after fill. There is no common expiry (review m3 withdrawn). |
| Outcome | `h10_net_excess_bps` = 10,000 × [(close_fill+10 / close_fill) − (SPY_fill+10 / SPY_fill)] − 50 bps. Long only; bid/ask is absorbed in the cost floor (review n3). |
| Cost floor | 50 bps round trip, quoted from B4 (`cost_floor_bps_round_trip`), applied to every entered arm; cash units carry 0. |
| Primary | per-admission paired difference D = outcome(T0) − outcome(T1), **intention-to-treat**: every admission with identified `t_disc` and a non-CENSORED, non-UNKNOWN T1 status contributes; when T1 has no entry inside K the T1 outcome is the declared cash return 0 (review F4). The per-protocol set (both arms entered) is a secondary. |
| Promotion condition (P only) | lower one-sided 95% bound of mean D ≥ −25 bps (B4's non-inferiority margin, quoted) AND median(`t_cur − t_disc`) ≥ 1 session over the per-protocol pairs AND §6 tolerance holds. |
| Secondary family (Holm, α = 0.05, fixed at freeze) | D(T2 − T1), D(T2m − T1), D(T3 − T1) if T3 identified; per-protocol D(T0 − T1). The family is listed in the freeze record and does not change afterwards. |
| Descriptive, non-promoting | T1b sensitivity; subgroup cuts by liquidity tercile of `mdv20_usd` at `t_disc` and by anchor era; `already before t_disc` flag; `t_vis`/`t_auth` columns. "Source tier" is dropped (every admission is turn_watch, review m2). |
| Trough and MAE | the H10 maximum adverse excursion is recorded per arm as a diagnostic only (the B4 primary is MAE; this study does not re-test it). |

## 5. Execution model and point-in-time rules

| Rule | Definition (frozen) |
| --- | --- |
| Invalidation anchor | the OPENED `payload.structural_anchor.price` (`turn_watch_reset_low`, adjusted-close basis), the same number for every arm. |
| Delayed arm before its fill (review F8) | if any session close strictly before an arm's `t_exec` is below the anchor, the arm **does not enter**; its outcome is cash 0 and the unit is recorded as AVOIDED for that arm. This is the economic case for waiting and is scored, not assumed. |
| Fill refusal | if the fill-session close is below the anchor, the arm is REFUSED (no fill, cash 0, counted). |
| False start | an entered arm whose close falls below the anchor at any session within the hold **before** any close ≥ fill × (1 + ATR14 / fill), where ATR14 is the mean absolute close-to-close change over the 14 sessions strictly before `t_exec` (proxy declared because the panel has no high/low; price units, compared to price, review m4). A false start flags the unit; it does not change the time exit. |
| Knowability of `t_cur` (review F5) | a BUY-lane stamp counts only when the row is present in a committed blob of `data/us_prophet_rank/candidates/YYYY-MM.parquet` whose commit is dated on or before the next session's close (the stamps are committed nightly by the us-scan-tier lane; the freeze attaches the commit walk, as W1 r3 did for turn_watch documents). Rows with `signal_asof > stamp_date` (425 in the census) are UNKNOWN for T1. |
| Knowability of `t_disc` | the W1 r2 document session; `known_at` is never a decision instant. |
| Censoring | a unit whose hold crosses a session the price panel lacks (W3's `session_missing` class) is CENSORED for that arm and counted. |
| Bounds (review m7) | every endpoint is reported three ways: at cost ×1 (primary), at cost ×2, and with the top 5% of |D| pairs excluded. A flip of the primary verdict under any bound is reported as FRAGILE. |

## 6. Tolerable additional false-positive cost (declared now)

Base rates come from the W1 r2 population census, not from outcomes. The incumbent's per-protocol
false-start rate is unknown before R is read; the tolerances are therefore absolute.

| Tolerance | Value | Rationale |
| --- | --- | --- |
| (i) false-start rate | T0's rate may exceed T1's by at most **10 percentage points** absolute, per-protocol pairs | a judgment: at ≈ 30–60 identified pairs a 10 pp excess is the smallest difference the look can resolve; smaller excesses are not distinguishable from noise and larger ones would not be worth a one-session lead |
| (ii) false-start loss | the sum over false-start units of (outcome(T0) − outcome(T1)), per 100 admissions, may not be worse than **−150 bps** | a judgment: 150 bps per 100 admissions is three cost floors; a timing rule that burns more than three round trips per 100 admissions in avoidable losses is not "economically useful" even if the mean lead is positive. The per-100-eligible figure is printed beside it. |
| (iii) missed upside | counted on the T1 side: units where T1 was cash (late/never) while T0 entered contribute their D to the primary; no separate tolerance, because the primary already prices it |

## 7. Looks, multiplicity, dispositions and what cannot happen

| Element | Definition (frozen) |
| --- | --- |
| R looks | exactly one, after maturity (§2); R may inform P's constants only through this registration's revision history before freeze; after freeze R changes nothing |
| P looks | monitoring at 50 and 100 identified primary pairs (no promotion), futility at 150, fixed verdict at 300 (the B4 look counts, quoted) |
| Futility (W2's own rule, review F10) | stop for futility at 150 if the upper one-sided 95% bound of mean D < −25 bps; B4's freeze carries no futility criterion and none is attributed to it |
| Multiplicity | Holm over the §4 secondary family; the primary stands alone |
| Dispositions | PROMOTE (P only, §4 condition), RETAIN_IN_SHADOW, REJECT, UNIDENTIFIED (floor or censoring), FRAGILE (bound flip). An R REJECT means P is not launched for that rule; an R PROMOTE-shaped result still cannot promote. |
| Falsifier (review F9) | invariance check: every numerator in §4–§6 (D, false starts, AVOIDED, REFUSED, leads) is computed over admissions only; recomputing after adding or removing refused units must leave every numerator identical and move only the per-100-eligible denominators. A change in any numerator fails the run. |
| Required per-arm waterfall (review m6) | eligible → admissions → identified `t_disc` → T1 identified / CENSORED / UNKNOWN → entitlement excluded → triggered → AVOIDED → REFUSED → entered → CENSORED (panel) → matured → false starts |

### Cases that must be exercised before any disposition (brief §Cases that can disprove a superficial repair)

| Case | What it must show |
| --- | --- |
| CRI (identity) | a ticker that does not resolve on a stamp date yields T1 = UNKNOWN, never a minted identity or "never admitted" |
| RCL / CSCO (which field set `t_cur`) | the freeze record names the exact stamp row (`stamp_date`, `ticker`, `lane`, commit SHA) that set `t_cur` |
| AMZN / USFD / WM / KO (out of universe vs timing) | a unit whose T1 window spans lane-coverage gaps is CENSORED, not late; a unit never in the BUY lane within K is cash, not excluded |
| CTVA + a loser (false start) | a T0 entry that closes below the anchor before +1 ATR is a false start and still exits at H10 |
| STLD / NEM (avoided) | an arm invalidated before its fill records AVOIDED with cash 0, and the unit stays in the ITT primary |

## 8. What this registration does not authorize

No outcome read before freeze; no change to B4 #7751 A1, its capture, its cells, or W3; no
historical backfill into P; no new data-purpose grant; no production, board, alert or trade effect.
The B-17 historical population (7,918 C0 episodes, none with a complete 34-session window) is not
this study's R segment and is not substituted by it; B-17 stays null. Required before freeze:
independent non-author review of this exact revision; the Data OS owner's entitlement exclusion
list; the census re-run with the W1 r2 session and the §2 identity join; `k*` from dates only; the
T3 gate result; the price-panel commit SHA; and a machine freeze mirroring §2–§7.

## Frozen-field block (to be mirrored into the machine freeze at freeze time)

```yaml
schema: us.prophet_entry_timing_w2_design/v2
status: DRAFT_UNFROZEN
parents: [B4 PREREG.json (quoted constants only), W3_RACE_PREREG.md (session_missing class only), ENTRY_TIMING_W1 r3 (d03acfd0)]
generation_id: peg:23be3409c3a57944dd08e09e38e3b7541926c0f244e9d0d3b4a0b4a8aacedbf9
population_unit: admission (OPENED episode) ; eligible = admissions + turn_watch refused units excluding ACTIVE_EPISODE_DIFFERENT_ANCHOR
identity_join: VendorAliasTable.resolve("membership", ticker, on=stamp_date) -> security_id within identity_epoch ; unresolved -> UNKNOWN
segments:
  R: {S_disc_from: 2026-08-26, S_disc_to: 2026-10-23, looks: 1, may_promote: false, read_after_maturity_session: <set at freeze>}
  P: {S_disc_from: <freeze date>, looks: [50, 100, 150, 300], generation_rotation: per-look peg pin, episodes keyed by episode_id}
clock: {t_disc: W1 r2 document session, t_cur: first lane=="buy" stamp >= t_disc proven in a nightly commit, known_at_is_not_a_decision_instant: true}
arms: {T0: t_disc+1, T1: t_cur+1 if t_cur <= t_disc+K else cash, T2: t_disc+1+2, T2m: t_disc+1+k_star, T3: union early-turn if gate passes}
admission_wait_cap_K_sessions: 10
k_fixed_sessions: 2
k_star: <median(t_cur - t_disc) over R identified pairs, dates only, at freeze; 0 or 2 -> T2m UNIDENTIFIED>
fill_basis: next_session_close (engine/us_prophet_grades.py)
price_panel: {path: data/yahoo/<TICKER>.parquet, column: close, benchmark: data/yahoo/SPY.parquet, commit: <set at freeze>}
horizon_sessions: 10
exit: time_exit_at_h10_close
cost_floor_bps_round_trip: 50
primary: {contrast: T0 - T1, analysis: intention_to_treat, cash_return_bps: 0, endpoint: h10_net_excess_bps, non_inferiority_lower_bound_bps: -25, min_median_lead_sessions: 1}
secondary_family_holm: [T2 - T1, T2m - T1, T3 - T1 (if identified), per_protocol T0 - T1]
sensitivity_descriptive: [T1b buyable==True, liquidity terciles mdv20_usd, anchor era, already_before_t_disc]
delayed_arm_rule: {close_below_anchor_before_fill: AVOIDED cash 0, fill_session_close_below_anchor: REFUSED cash 0}
false_start: close < anchor within hold before any close >= fill * (1 + ATR14_proxy / fill) ; ATR14_proxy = mean |dclose| over 14 sessions strictly before t_exec
tolerance: {false_start_rate_delta_pp_max: 10, false_start_loss_bps_per_100_admissions_min: -150, per_100_eligible_printed_beside: true}
bounds: [cost_x1, cost_x2, drop_top_5pct_abs_D]
min_identified_pairs_per_look: 30
futility_rule_w2: upper_one_sided_95_bound_mean_D < -25 bps at 150
dispositions: [PROMOTE (P only), RETAIN_IN_SHADOW, REJECT, UNIDENTIFIED, FRAGILE]
falsifier: numerators invariant to refused-unit count
authority: measurement only; no trade/sizing/alert; never amends #7751 A1; B4 t_auth descriptive only
```
