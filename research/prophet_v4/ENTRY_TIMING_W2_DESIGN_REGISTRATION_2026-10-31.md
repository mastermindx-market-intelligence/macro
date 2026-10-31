# Entry Timing W2 — design registration: does entering at first persisted discovery beat waiting for the BUY-lane admission? (2026-10-31, revision 3)

**Status: DRAFT — UNFROZEN.** Nothing in this document is registered until (a) an independent
non-author review returns APPROVE-READY-TO-FREEZE on the exact revision, (b) the frozen-field block
below is mirrored into a machine freeze, and (c) the freeze commit SHA is written into this header.
Until then every number here may change, and no outcome, price, grade or paired-race surface has
been or may be read for the population it names. Authority: measurement design only. No trade,
sizing, alert or capability authority follows from any result of this study.

**Revision history.** r1 → review REVISE (the "first curated-tier stamp" incumbent was a universe:
916/1,087 opened episodes already curated before discovery, 77.3% zero lag). r2 → review REVISE
(two blockers: the intention-to-treat primary with T1 = cash was a selection contrast with a cost
asymmetry; BUY-row coverage has gaps inside the decision window, not only after 2026-10-19). r3
(this revision) declares the estimand (§1), re-derives coverage from producer health with
interval-censored admission and an INCUMBENT_LED class (§2), counts every lag in NYSE trading
sessions (§3), maps every instant to its as-committed knowable session (§5), adds REJECT/RETAIN
rules, quotes B4's futility rule, states the minimum detectable effect, and replaces the
tautological falsifier with a placebo negative control (§7). Every count quoted here comes from
`research/prophet_v4/entry_timing_w2_t1_census.py` v3 run on the freeze basis (committed output
`research/prophet_v4/entry_timing_w2_t1_census_2026-10-31.json`; dates, tickers, lane/tier flags
and commit times only — no price, grade, outcome or paired-race column; the SPY parquet is opened
for its date index only). The census is re-run and attached at freeze.

**Separate registration.** This is a new study with its own hypothesis. It does not change, read
into, or borrow samples from the B4 entry-policy calibration preregistration (#7751, amendment A1,
machine freeze `research/prophet_v4/b4_entry_policy_calibration/PREREG.json`), whose population,
H10 MAE primary endpoint, 50 bps cost floor, Holm family, fixed looks, futility rule and refusal
handling are untouched. It does not change the frozen W3 paired race
(`research/prophet_fusion/W3_RACE_PREREG.md`) or reopen Entry Timing W0. Where this study reuses a
B4 or W3 constant it says so and quotes it; reuse is not amendment. Arms are named `T0…T3` so that
no name collides with the B4 cells `C0…C5` or the August bake-off's "C0 incumbent" lane. A B4
capture instant (`t_auth`), once capture exists, may appear as a descriptive column only; it is
never this study's comparator.

**Inputs this design stands on (all committed, read-only):** Entry Timing W1 r3 (PR #10277, head
d03acfd0: `research/prophet_v4/ENTRY_TIMING_W1_INTAKE_WATERFALL_2026-10-31.md`, 27 sessions
2026-08-26 → 2026-10-23, 88,325 inputs / 15,511 mapped / 72,814 refused, 0 refusals resolvable at
their session, every turn_watch row's document session recovered from its receipt over the full
git history); the SELECTED B1 candidate-episode generation
`peg:23be3409c3a57944dd08e09e38e3b7541926c0f244e9d0d3b4a0b4a8aacedbf9` (1,087 OPENED, all
turn_watch, 1,087/1,087 discovery sessions recovered, all inside 2026-08-26 → 2026-10-23); the US
candidate stamps `data/us_prophet_rank/candidates/YYYY-MM.parquet` (54 stamp dates 2026-07-31 →
2026-10-29; the `lane` column is populated on every stamp date, but curated-tier rows — inside
which the BUY lane is classified — exist on 35 of them, last 2026-10-19; after that date every
stamp is scan-only because the nightly commits were rejected by GH001, the defect PR #10255
repairs); the lane rules in `engine/us_candidate_lanes.py` (`_classify_buy_row`,
`build_candidate_pool`); the grade producer `engine/us_prophet_grades.py` (next-bar close fill,
positional horizons, SPY benchmark from `data/yahoo/SPY.parquet`); the per-ticker
dividend-adjusted close panel `data/yahoo/<TICKER>.parquet` (columns `close_price`, `close`,
`volume`; no open/high/low); the completion brief
(`research/prophet_v4/PROPHET_US_ENTRY_TIMING_COMPLETION_BRIEF_2026-10-31.md` at `e757498822a2`,
§Scientific audit and research design); and the B4/W3 freezes named above.

**Prior knowledge disclosed.** The brief records that the curated BUY surface underperformed over a
window overlapping R. The authors knew this before writing r1. It is a reason to expect the
challenger to look good, and it is exactly the direction a selection artifact would also produce;
§1 and §7 are written so that a selection artifact cannot promote.

## 1. Question, estimand and hypothesis

The brief's W2 question, verbatim: *"Given the same pre-policy population and information actually
available at each cut, does a proposed timing rule move executable entry earlier by an economically
useful amount without an unacceptable increase in false starts or missed upside?"*

**Primary estimand — the timing contrast on admitted units (declared conditional).** For the
admitted candidate episodes that the incumbent BUY lane admitted within K sessions of discovery
(§3), the per-episode difference between entering at the first executable session after persisted
discovery (T0) and entering at the first executable session after the BUY-lane admission (T1),
with identical population, fill rule, horizon, cost and outcome. This set is selected by an event
that happens after T0's decision instant (the admission), so the contrast is **conditional on a
post-T0 event** and is labelled so everywhere. The bias direction is argued, not assumed: the lane
admits after its gates pass, and those gates plausibly pass after a favourable post-discovery
move; on such units T0 holds through the move that T1 enters after, so the conditioning
**favours T0**. Consequently a null or negative primary is strong evidence against T0, while a
positive primary is confounded until the placebo negative control in §7 is null. PROMOTE requires
both.

**Secondary estimand — the policy contrast (P only).** "Buy at every discovery" against "follow the
BUY lane as practised", intention-to-treat over every admission with a fully covered decision
window: T1 is cash (SPY-excess 0, no cost) when the lane never admitted inside K. This contrast
mixes timing with the lane's selection skill and carries a built-in cost asymmetry (every entered
arm pays the 50 bps floor, cash pays nothing), so it is reported only as the decomposition
`mean D_policy = p_A · mean D_timing + (1 − p_A) · mean(T0 net excess | not admitted)` with all three
terms printed, never as a promotion basis. In R it is **unidentifiable**: the census finds 0
admissions whose 10-session window is free of producer gaps (§2), so the "cash" class is empty by
coverage, not by behaviour. It becomes identifiable only in P once the producer runs every session.

**H_W2 (one-sided, primary).** On the admitted-within-K units, T0 is not economically inferior to
T1, net of the cost floor, while leading it by at least one session in median. The null is that
T0 is inferior by more than the non-inferiority margin, or leads by less than one session, or
breaches the §6 tolerance, or fails the §7 negative control.

**What is being separated.** Three delays, never merged: discovery → persisted (the intake clock,
measured in W1), persisted → admitted to the BUY lane (the incumbent's wait, this study), admitted
→ executable (the fill rule, §5, identical for every arm).

## 2. Population (frozen before any policy is applied)

| Element | Definition (frozen) |
| --- | --- |
| Admission unit | Every OPENED event in the pinned generation: one per candidate episode, keyed by `episode_id`; `payload.security_id` + `payload.identity_epoch` are the identity, `payload.ticker_at_observation` is a label only. |
| Discovery session `t_disc` | The W1 r3 receipt-recovered document `data_session` of the OPENED row's `source_receipt`, not `known_at`, not `occurred_at`. A unit whose receipt is unrecoverable is UNKNOWN (census: 0 of 1,087). |
| Session calendar | NYSE trading sessions = the date index of `data/yahoo/SPY.parquet` (dates only). Every lag, window, cap, horizon and maturity in this document is counted in these sessions; the stamp grid is never a unit. R (2026-08-26 → 2026-10-23) holds 42 sessions. |
| Producer-health coverage | A session is COVERED when a candidate stamp for that date carries at least one curated-tier row (the BUY lane is classified inside the curated tier, so a zero-curated stamp cannot admit anyone and a missing stamp cannot either). Every other session is a GAP. In R, 26 of 42 sessions are covered; the gaps are 09-01, 09-02, 09-15, 09-18, 09-28, 09-29, 10-07, 10-09, 10-12, 10-13, 10-15, 10-16 and every session from 10-20 on. A zero-BUY day that is covered is a legitimate "no admission". |
| Decision window | `[t_disc, t_disc + K]`, K = 10 sessions (frozen). |
| INCUMBENT_LED | A unit with a BUY-lane row for its security on any covered session in `[t_disc − K, t_disc)`: the incumbent held the name before the discovery, so a BUY stamp after `t_disc` is a re-admission, not the incumbent's entry. Excluded from the primary; counted in the waterfall (census: 98). |
| T1 status per unit | IDENTIFIED_EXACT: first BUY stamp in the window with no gap before it (31). IDENTIFIED_INTERVAL: first BUY stamp in the window with at least one gap before it (65) — the true admission lies in `(last covered session before the gap, observed stamp]`, so the primary uses the **earliest possible** admission (the first gap session: conservative for the lead, and for D it moves T1 toward T0) and reports the observed-stamp version as the optimistic bound. CASH: no BUY stamp and no gap anywhere in the window (0 in R). CENSORED: no BUY stamp and at least one gap in the window (892). UNKNOWN: any stamp for the security on a covered session before its first proven BUY stamp in the window has `signal_asof > stamp_date` or does not resolve through the identity join (1 + 0). |
| Identity join for T1 | Candidate stamps carry `ticker` only. A stamp joins an episode when `VendorAliasTable.resolve("membership", ticker, on=stamp_date)` (`lib.dataos.identity`, the W1 reference) returns the episode's `security_id` within its `identity_epoch` ("membership" is not a clocked vendor, so no `decision_at` applies). A non-resolving stamp makes the unit UNKNOWN, never "never admitted". No identity is minted from a ticker and a date (brief: CRI case). |
| Refused units | IDENTITY_UNRESOLVED and MISSING_STRUCTURAL_ANCHOR suppressions whose `source_receipt` is a turn_watch document (W1 r3 basis), excluding `ACTIVE_EPISODE_DIFFERENT_ANCHOR`. Candidate-tier and doors refusals are reported in the waterfall but are not in the eligible denominator. "Never mapped" is judged as of the pinned generation. |
| Eligible denominator | admissions + refused turn_watch units. Tolerance (ii) in §6 is judged **per 100 primary units**; the per-100-eligible version is printed beside it, never substituted. |
| Segment R (retrospective) | Admissions with `t_disc` from 2026-08-26 to 2026-10-23 inclusive in the pinned generation (all 1,087). One look, after maturity. **R can never promote and, being coverage-limited (892 of 1,087 units censored), can never REJECT either**: R yields a descriptive readout of the primary on its 96 identified pairs and informs P's constants only through this registration's revision history before freeze. |
| Segment P (prospective) | Admissions with `t_disc` after the freeze date. Each P look uses the generation current at the look, pinned by its `peg:` id in the look record; admissions are keyed by `episode_id` and never re-opened or re-read under a later generation. Looks per §7. P requires the nightly producer to commit every session (PR #10255); a P session without a healthy stamp is a GAP under the same rule. |
| Entitlement | The Data OS owner's exclusion list (securities whose price panel may not be used for this purpose) is applied before any outcome read; it is pinned at freeze as a list of `security_id`s and every exclusion is counted in the waterfall. |
| Minimum identified pairs | 30 primary pairs per segment look, else the look is UNIDENTIFIED. R has 96. This is W2's own floor; W3's 20-session count is a guardrail tripwire inside W3 and is not reused here. |

## 3. Decision instants and arms

Six instants are recorded per admission; any that cannot be proven as-known is NULL, never imputed.

| Instant | Meaning | Source |
| --- | --- | --- |
| `t_obs` | the bar the anchor was observed on | OPENED `occurred_at`, informational only |
| `t_disc` | the session the discovery was persisted (`data_session`) | W1 r3 document session |
| `t_cur` | the first covered session ≥ `t_disc` whose stamp has `lane == "buy"` for the episode's security (earliest-possible basis when interval-censored, §2) | candidates parquet, §2 join |
| `t_vis` | first session the security was visible on a public board | NULL in R unless proven from committed site artifacts; descriptive |
| `t_auth` | a B4 capture authorization instant | NULL in R; descriptive only in P once capture exists; never the comparator |
| `t_exec` | the fill session of an arm (§5) | derived from the knowable session, §5 |

**Arms.** Each arm is a rule for `t_exec` given only information readable at or before that session.

| Arm | entry session | Role |
| --- | --- | --- |
| T0 | `k(t_disc) + 1` | challenger: enter at first persisted discovery (the brief's "immediate" and "candidate" arms coincide; there is no fourth arm) |
| T1 | `k(t_cur) + 1` | incumbent: the BUY-lane admission, one definition in R and P |
| T2 | `k(t_disc) + 1 + 2` | fixed short wait, k = 2 sessions (frozen) |
| T2m | `k(t_disc) + 1 + k*` | median-wait mimic; k* = median earliest-possible lag over R's identified pairs = **2 sessions** (census v3), which equals the fixed k, so **T2m is UNIDENTIFIED and is not in the family** (declared now, not at readout) |
| T3 | union early-turn signal (`engine/us_early_turn.py`) | only if reconstructable as-known for ≥ 90% of R primary units; the gate is evaluated at freeze and the family is fixed then |

`k(·)` is the knowable session of §5. Lead = `t_cur − t_disc` in sessions (earliest-possible
basis). Census v3 on the freeze basis (W1 r3 sessions, identity join, producer-health coverage,
NYSE sessions): 1,087 admissions → 98 INCUMBENT_LED → 96 identified pairs (31 exact + 65 interval;
by discovery month 54 / 36 / 6), 892 CENSORED, 0 CASH, 1 UNKNOWN; earliest-possible lead median
2 sessions (IQR 1–4), 18 zero-lead pairs; observed-stamp lead median 6. For comparison the r2
screening table (opened_session stand-in, ticker join, stamp-grid lags) gave for the BUY lane 365
stamped / 722 never / 6.0% zero lag / median 14 grid sessions; those figures are superseded.

**Why the BUY lane is the incumbent.** The lane is the surface the product tells a user to act on;
`_classify_buy_row` in `engine/us_candidate_lanes.py` admits a row only after the buy gates. The
curated tier (median 2,932 rows per stamp) is a universe; the BUY lane (median 61) is an admission.
`buyable == True` is kept as a declared sensitivity definition (T1b), descriptive and non-promoting.

## 4. Outcomes, horizon, primary and secondary endpoints

| Element | Definition (frozen) |
| --- | --- |
| Price path source | `data/yahoo/<TICKER>.parquet` column `close` (dividend-adjusted), resolved through the §2 identity join at each session; benchmark `data/yahoo/SPY.parquet` `close`. The path, column and basis are frozen here; the panel's commit SHA is pinned **in each look record** (R matures after any near-term freeze). |
| Fill basis | **next-session close** (`engine/us_prophet_grades.py`: "entry is the close of the bar STRICTLY AFTER the stamp bar"), applied to the knowable session (§5). The panel has no open column, so no open fill. |
| Hold and horizon | H = 10 sessions from each arm's own fill (positional on the price index). Exit is a **time exit** at the close of the 10th session after fill. No common expiry. |
| Outcome | `h10_net_excess_bps` = 10,000 × [(close_fill+10 / close_fill) − (SPY_fill+10 / SPY_fill)] − 50 bps for every entered arm. Long only; bid/ask is absorbed in the cost floor. |
| Cost floor | 50 bps round trip, quoted from B4 (`cost_floor_bps_round_trip`). In the policy contrast only, cash units carry 0 and no cost; the asymmetry is printed in the decomposition (§1). |
| Primary | per-unit paired difference D = outcome(T0) − outcome(T1) over the §2 IDENTIFIED (exact + interval, earliest-possible basis) units, INCUMBENT_LED excluded. |
| Promotion condition (P only) | lower one-sided 95% bound of mean D ≥ −25 bps (B4's non-inferiority margin, quoted) AND median lead ≥ 1 session over the same units AND §6 tolerance holds AND the §7 negative control is null AND ≥ 300 primary units (the fixed look). |
| Secondary family (Holm, α = 0.05, fixed at freeze) | D(T2 − T1); D(T3 − T1) if T3's gate passes; the policy contrast decomposition (P only). The family is listed in the freeze record and does not change afterwards. |
| Descriptive, non-promoting | observed-stamp (latest-possible) basis for interval units; T1b sensitivity; INCUMBENT_LED units scored with T1 at the start of their continuous BUY run (negative lead); subgroup cuts by liquidity tercile of `mdv20_usd` at `t_disc` and by anchor era; D by lead tercile; `t_vis`/`t_auth` columns. |
| Trough and MAE | the H10 maximum adverse excursion is recorded per arm as a diagnostic only (the B4 primary is MAE; this study does not re-test it). |
| Minimum detectable effect | Assumed SD of D = 400 bps — a judgment from the design, not a population estimate (10-session single-stock SPY-excess returns run roughly 500–600 bps SD; the paired overlapping holds reduce it). At n = 96 the one-sided 95% standard error is ≈ 41 bps, so the lower bound clears −25 bps only if mean D ≥ ≈ +42 bps; at n = 300, SE ≈ 23 bps and mean D ≥ ≈ +13 bps suffices. PROMOTE is therefore not expected before the 300-unit look and is impossible in R. |

## 5. Execution model and point-in-time rules

| Rule | Definition (frozen) |
| --- | --- |
| Knowable session `k(·)` | For a stamp or document committed to `origin/main` at time `c` (ET), `k` = the first NYSE session whose 16:00 ET close is strictly after `c + 30 min`. The instant is read from the **earliest** commit blob that contains the row (the monthly parquets are rewritten by later heals). Census v3 walked 275 commits and 2,164 BUY rows: every R `t_cur` stamp becomes knowable 1 session (70 units) or 2 sessions (26 units) after its stamp date, never on it. The same rule maps `t_disc` through the turn_watch document commit recorded by the W1 r3 walk; the freeze attaches both walks. |
| Fill | an arm fills at the close of the session after its knowable session (`t_exec = k(·) + 1`, §3). An intraday commit can therefore never be filled at the same session's close. |
| Invalidation anchor | the OPENED `payload.structural_anchor.price` (`turn_watch_reset_low`, adjusted-close basis), the same number for every arm. |
| AVOIDED (delayed arm) | if any session close in `[t_disc, t_exec − 1]` is below the anchor, the arm **does not enter**; outcome cash 0; recorded AVOIDED. The window starts at `t_disc` for every arm, T0 included. |
| REFUSED | if the fill-session close is below the anchor, the arm does not fill; cash 0; counted. |
| False start | an entered arm whose close falls below the anchor at any session within the hold **before** any close ≥ fill + ATR14, where ATR14 is the mean absolute close-to-close change (price units) over the 14 sessions strictly before **`t_disc`**, the same number for every arm. A false start flags the unit; it does not change the time exit. |
| Censoring | a unit whose hold crosses a session the price panel lacks (W3's `session_missing` class) is CENSORED for that arm and counted. |
| Bounds | every endpoint is reported at cost ×1 (primary), cost ×2, with the top 5% of |D| pairs excluded, and on the latest-possible admission basis. A flip of the primary verdict under any bound is reported as FRAGILE. |

## 6. Tolerable additional false-positive cost (declared now)

Base rates come from the W1 r3 population census, not from outcomes; the incumbent's false-start
rate is unknown before R is read, so the tolerances are absolute judgments, stated as such.

| Tolerance | Value | Rationale (judgment) |
| --- | --- | --- |
| (i) false-start rate | T0's rate may exceed T1's by at most **10 percentage points** absolute over the primary units | one false start in ten admissions is the most a one-to-two-session lead could plausibly pay for; at n = 96 the resolvable difference is ≈ 20 pp, so (i) binds only from the 300-unit look and is reported descriptively before that |
| (ii) false-start loss | the sum over false-start units of (outcome(T0) − outcome(T1)), per 100 primary units, may not be worse than **−150 bps** | three cost floors per 100 admissions; a rule that burns more than three round trips in avoidable losses is not "economically useful" whatever its mean lead |
| (iii) missed upside | counted on the T1 side inside the policy contrast (P only): cash units where T0 entered contribute their D; no separate tolerance, because the decomposition prices it |

## 7. Looks, multiplicity, dispositions, falsifiers and what cannot happen

| Element | Definition (frozen) |
| --- | --- |
| R look | exactly one, after maturity: the first session after `max(t_disc) + 1 + max(K, 2) + 2 + H` sessions = 2026-10-23 + 23 sessions (the exact session is written at freeze); descriptive only (§2) |
| P looks | monitoring at 50 and 100 primary units (no promotion), futility at 150, fixed verdict at 300 (B4's look counts, quoted: `monitoring_only_episode_counts [50, 100]`, `fixed_episode_count_per_distinct_cell 300`) |
| Futility (W2's own rule) | stop for futility at 150 if the upper one-sided 95% bound of mean D < −25 bps. B4's own rule is different and is quoted, not borrowed: `"futility": {"episode_count_per_cell": 150, "rule": "stop as REJECTED if every cell's primary lower confidence bound excludes improvement"}`. |
| REJECT | upper one-sided 95% bound of mean D < −25 bps with the floor met, or tolerance (ii) breached at the fixed look; P only |
| RETAIN_IN_SHADOW | the residual: floor met, neither PROMOTE nor REJECT |
| UNIDENTIFIED / FRAGILE | floor not met or coverage-limited (every R look); a bound flip (§5) |
| Multiplicity | Holm over the §4 secondary family; the primary stands alone |
| Negative control (scientific falsifier) | **placebo discovery**: for the same primary units, re-run T0 at a pseudo-discovery session `t_disc − 5` (same fill, hold, cost, anchor); if the placebo contrast's upper one-sided 95% bound is not at least 25 bps below the real contrast's point estimate, the real contrast is attributed to drift or selection, PROMOTE is blocked and the look is recorded FAILED_NEGATIVE_CONTROL. A second descriptive falsifier: D should not decrease with lead tercile if waiting has a cost; a monotone decrease is reported. |
| Implementation invariant (not a falsifier of H_W2) | every numerator in §4–§6 is computed over primary units only; adding or removing refused units must leave every numerator identical. |
| Required per-arm waterfall | eligible → admissions → `t_disc` recovered → INCUMBENT_LED → T1 IDENTIFIED_EXACT / IDENTIFIED_INTERVAL / CASH / CENSORED / UNKNOWN → entitlement excluded → AVOIDED → REFUSED → entered → CENSORED (panel) → matured → false starts |
| Dispositions are by rule | every disposition follows the prespecified outcome rules above, never a judgment made after reading outcomes. |

### Cases that must be exercised before any disposition (brief §Cases that can disprove a superficial repair)

| Case | What it must show |
| --- | --- |
| CRI (identity) | a ticker that does not resolve on a covered stamp date makes the unit UNKNOWN, never a minted identity or "never admitted" |
| RCL / CSCO (which field set `t_cur`) | the freeze record names the exact stamp row (`stamp_date`, `ticker`, `lane`, earliest commit SHA, commit time ET, knowable session) that set `t_cur` |
| AMZN / USFD / WM / KO (out of universe vs timing) | a unit whose window contains a gap and no BUY stamp is CENSORED, not late; a covered zero-BUY session is a legitimate non-admission; a unit never in the BUY lane within a fully covered window is CASH in the policy contrast only |
| CTVA + a loser (false start) | a T0 entry that closes below the anchor before +ATR14 is a false start and still exits at H10 |
| STLD / NEM (avoided) | an arm invalidated in `[t_disc, t_exec − 1]` records AVOIDED with cash 0 and stays in the waterfall |
| Incumbent-led name | a security in the BUY lane within the 10 sessions before `t_disc` is INCUMBENT_LED and out of the primary; its negative-lead score appears only in the descriptive table |

## 8. What this registration does not authorize

No outcome read before freeze; no change to B4 #7751 A1, its capture, its cells, or W3; no
historical backfill into P; no new data-purpose grant; no production, board, alert or trade effect.
The B-17 historical population (7,918 C0 episodes, none with a complete 34-session window) is not
this study's R segment and is not substituted by it; B-17 stays null. Required before freeze:
independent non-author review of this exact revision; the Data OS owner's entitlement exclusion
list; the census re-run (v3, both commit walks) attached; the T3 gate result; and a machine freeze
mirroring §2–§7.

## Frozen-field block (to be mirrored into the machine freeze at freeze time)

```yaml
schema: us.prophet_entry_timing_w2_design/v3
status: DRAFT_UNFROZEN
parents: [B4 PREREG.json (quoted constants only), W3_RACE_PREREG.md (session_missing class only), ENTRY_TIMING_W1 r3 (d03acfd0)]
generation_id: peg:23be3409c3a57944dd08e09e38e3b7541926c0f244e9d0d3b4a0b4a8aacedbf9
session_calendar: data/yahoo/SPY.parquet date index (NYSE sessions); all units in sessions
primary_estimand: timing contrast T0 - T1 on IDENTIFIED admitted-within-K units, conditional on post-T0 admission (bias favours T0; negative control required)
secondary_policy_contrast: {segment: P only, itt: true, cash_return_bps: 0, cash_cost: none, report: decomposition p_A * D_timing + (1 - p_A) * T0_net_excess_not_admitted}
population_unit: admission (OPENED episode); eligible = admissions + turn_watch refused units excluding ACTIVE_EPISODE_DIFFERENT_ANCHOR
coverage: session COVERED iff a stamp with >= 1 curated-tier row exists for it; else GAP
decision_window_K_sessions: 10
incumbent_led: BUY row on a covered session in [t_disc-K, t_disc) -> excluded from primary
t1_status: [IDENTIFIED_EXACT, IDENTIFIED_INTERVAL (earliest-possible basis primary; latest-possible bound), CASH (no gap, no BUY), CENSORED (gap, no BUY), UNKNOWN (unit-level)]
identity_join: VendorAliasTable.resolve("membership", ticker, on=stamp_date) -> security_id within identity_epoch; unresolved -> UNKNOWN
knowable_session: first NYSE session whose 16:00 ET close > earliest-commit time + 30 min; applied to BUY stamps and turn_watch documents
fill: close of the session after the knowable session (engine/us_prophet_grades.py next-close basis)
price_panel: {path: data/yahoo/<TICKER>.parquet, column: close, benchmark: data/yahoo/SPY.parquet, commit: pinned per look record}
arms: {T0: k(t_disc)+1, T1: k(t_cur)+1, T2: k(t_disc)+1+2, T2m: UNIDENTIFIED (k_star == k), T3: union early-turn if gate >= 90%}
k_fixed_sessions: 2
k_star_sessions: 2
horizon_sessions: 10
exit: time_exit_at_h10_close
cost_floor_bps_round_trip: 50
primary: {endpoint: h10_net_excess_bps, non_inferiority_lower_bound_bps: -25, min_median_lead_sessions: 1, min_units: 30}
secondary_family_holm: [T2 - T1, T3 - T1 (if identified), policy_contrast_decomposition (P only)]
sensitivity_descriptive: [latest_possible_admission, T1b buyable==True, incumbent_led negative lead, liquidity terciles mdv20_usd, anchor era, D by lead tercile]
avoided_window: [t_disc, t_exec - 1] for every arm
false_start: close < anchor within hold before any close >= fill + ATR14 ; ATR14 = mean |dclose| over 14 sessions strictly before t_disc
tolerance: {false_start_rate_delta_pp_max: 10, false_start_loss_bps_per_100_primary_units_min: -150, per_100_eligible_printed_beside: true}
bounds: [cost_x1, cost_x2, drop_top_5pct_abs_D, latest_possible_admission]
mde: {assumed_sd_D_bps: 400 (judgment), n96_min_mean_D_bps: 42, n300_min_mean_D_bps: 13}
segments:
  R: {t_disc_from: 2026-08-26, t_disc_to: 2026-10-23, looks: 1, may_promote: false, may_reject: false, maturity_session: set at freeze (2026-10-23 + 23 sessions)}
  P: {t_disc_from: freeze date, looks: [50, 100, 150, 300], generation_rotation: per-look peg pin, episodes keyed by episode_id}
futility_rule_w2: upper_one_sided_95_bound_mean_D < -25 bps at 150 (B4's rule quoted, not borrowed)
reject_rule: upper_one_sided_95_bound_mean_D < -25 bps with floor met, or tolerance (ii) breached at 300; P only
negative_control: placebo T0 at t_disc - 5 on the same units; PROMOTE blocked unless placebo upper bound <= real point estimate - 25 bps
implementation_invariant: numerators invariant to refused-unit count (not a falsifier of H_W2)
dispositions: [PROMOTE (P only), RETAIN_IN_SHADOW, REJECT (P only), UNIDENTIFIED, FRAGILE, FAILED_NEGATIVE_CONTROL]
authority: measurement only; no trade/sizing/alert; never amends #7751 A1; B4 t_auth descriptive only
```
