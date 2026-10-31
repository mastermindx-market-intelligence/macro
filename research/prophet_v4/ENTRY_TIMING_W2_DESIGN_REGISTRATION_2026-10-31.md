# Entry Timing W2 — design registration: does entering at first persisted discovery beat following the BUY lane? (2026-10-31, revision 4)

**Status: DRAFT — UNFROZEN.** Nothing in this document is registered until (a) an independent
non-author review returns APPROVE-READY-TO-FREEZE on the exact revision, (b) the frozen-field block
below is mirrored into a machine freeze, and (c) the freeze commit SHA is written into this header.
Until then every number here may change, and no outcome, price, grade or paired-race surface has
been or may be read for the population it names. Authority: measurement design only. No trade,
sizing, alert or capability authority follows from any result of this study.

**Revision history.** r1 → REVISE (the "first curated-tier stamp" incumbent was a universe). r2 →
REVISE (ITT primary with T1 = cash judged a selection contrast; coverage gaps inside the window).
r3 → REVISE (P1 interval-censored units had no defined incumbent entry; P2 the placebo at
`t_disc − 5` does not control the selection channel; P3 the discovery-side knowable session was
unmeasured; N1–N14). r4 (this revision) records three seat adjudications, each stated with its
reason so a reviewer can attack the ruling and not only the text:

- **W2-ADJ-01 — the promotable primary is the implementable policy.** Round 2 rejected the
  intention-to-treat contrast as a "selection contrast with a cost asymmetry"; round 3 showed the
  conditional timing contrast cannot be de-biased by a placebo and would promote a rule no one can
  execute (an admission is not known at T0). The seat rules that the only contrast a user can act
  on is *buy at every persisted discovery* versus *follow the BUY lane as practised*: the lane's
  selection skill is part of the incumbent policy, not an artifact, and the cost asymmetry (cash
  pays no round trip) is a property of the compared policies, printed in the decomposition, not
  hidden. Because every admission in R has a producer gap inside its window, this contrast is
  **unidentifiable in R** and is a **P-only** primary; R can neither promote nor reject.
- **W2-ADJ-02 — the timing contrast is a co-condition on exactly identified pairs only.** Pairs
  whose admission is interval-censored have no measurable incumbent entry (a gap session has no
  committed row), so they leave the primary; the two interval bases become descriptive bounds;
  FRAGILE blocks PROMOTE.
- **W2-ADJ-03 — both arms are timed by commits, not dates.** The census now walks the turn_watch
  documents as it walks the candidate stamps (same digest law as W1 r3, earliest commit per
  receipt), lane state is read from the **first-commit** blob of each row (HEAD carries 59 BUY rows
  and two "healthy" sessions that only later heals added), and the lead is the **executable** lead
  `t_exec(T1) − t_exec(T0)`.

Every count quoted here comes from `research/prophet_v4/entry_timing_w2_t1_census.py` v4 run on the
freeze basis (committed output `research/prophet_v4/entry_timing_w2_t1_census_2026-10-31.json`;
dates, tickers, lane/tier flags, `signal_asof`, `recorded_at` and commit times only — no price,
grade, outcome or paired-race column; the SPY parquet is opened for its date index only). The
census is re-run and attached at freeze.

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
d03acfd0: `research/prophet_v4/ENTRY_TIMING_W1_INTAKE_WATERFALL_2026-10-31.md`; every turn_watch
row's document session recovered from its receipt over the full git history; 0 refusals resolvable
at their session); the SELECTED B1 candidate-episode generation
`peg:23be3409c3a57944dd08e09e38e3b7541926c0f244e9d0d3b4a0b4a8aacedbf9` (1,087 OPENED, all
turn_watch, 1,087/1,087 discovery sessions recovered, all inside 2026-08-26 → 2026-10-23; every
OPENED row `recorded_at` within 2 sessions of its data session, so the generation was written in
near real time); the US candidate stamps `data/us_prophet_rank/candidates/YYYY-MM.parquet` (54
stamp dates 2026-07-31 → 2026-10-29; on the first-commit basis 32 of them carry curated-tier rows,
the last on 2026-10-14; HEAD shows 35 because later heals added curated rows to 07-31, 09-14 and
10-19 — a heal is not the lane as practised; after 10-19 every stamp is scan-only because the
nightly commits were rejected by GH001, the defect PR #10255 repairs); the lane rules in
`engine/us_candidate_lanes.py` (`_classify_buy_row`, `build_candidate_pool`); the grade producer
`engine/us_prophet_grades.py` (next-bar close fill, positional horizons, SPY benchmark from
`data/yahoo/SPY.parquet`); the per-ticker dividend-adjusted close panel
`data/yahoo/<TICKER>.parquet` (columns `close_price`, `close`, `volume`; no open/high/low); the
membership alias records in `data/reference/vendor_aliases.parquet` (1,941 rows, 1,938 securities,
3 with more than one symbol, no validity windows, latest ingest 2026-10-19T06:10:18); the completion
brief (`research/prophet_v4/PROPHET_US_ENTRY_TIMING_COMPLETION_BRIEF_2026-10-31.md` at
`e757498822a2`); and the B4/W3 freezes named above.

**Prior knowledge disclosed.** (a) The brief records that the curated BUY surface underperformed
over a window overlapping R; the authors knew this before r1. (b) The census (dates only) shows
that on the 26 exactly identified R pairs the incumbent admitted on the discovery session itself in
15 cases: the executable lead is 0 for 15 of 26 and its median is 0. If that persists in P, the
timing co-condition fails and the study resolves on the policy contrast alone. Neither fact is an
outcome; both are stated so that no later reading can be presented as a surprise.

## 1. Question, estimands and hypothesis

The brief's W2 question, verbatim: *"Given the same pre-policy population and information actually
available at each cut, does a proposed timing rule move executable entry earlier by an economically
useful amount without an unacceptable increase in false starts or missed upside?"*

**Primary estimand (P only) — the policy contrast, intention-to-treat.** Over every admission unit
with a fully covered decision window, the per-unit difference `D_policy = outcome(T0) −
outcome(T1)` where T0 enters at the first executable session after persisted discovery and T1 is
the BUY lane as practised: it enters at the first executable session after the lane's admission,
and it is **cash** (SPY-excess 0, no cost) when the lane did not admit the security inside K
sessions. The contrast is unconditional on any post-T0 event, so it carries no admission-selection
bias; it mixes the lane's timing with its selection skill and its cost saving on non-admitted
names, and all three are printed through the decomposition
`mean D_policy = p_A · mean D_timing + (1 − p_A) · mean(outcome(T0) | not admitted)`.

**Co-condition — the timing contrast on exactly identified pairs.** On units the lane admitted
inside K with an exact (gap-free) admission and a gap-free pre-window, `D_timing = outcome(T0) −
outcome(T1)` and the executable lead `L = t_exec(T1) − t_exec(T0)`. This set is selected by a
post-T0 event; the direction of that selection plausibly favours T0 (the lane's gates pass after a
favourable post-discovery move, which T0 holds through), so the co-condition is a **guard**, never
a promotion basis: it stops a PROMOTE whose policy gain came only from non-admitted names rallying
("missed upside" in the brief's words) while the lane's own names were entered worse by T0.

**H_W2 (one-sided).** In P, buying at every persisted discovery is not economically inferior to
following the BUY lane, net of the cost floor, AND on the lane's own exactly admitted names T0 is
not inferior to T1 while leading it by at least one executable session in median. The null is
inferiority by more than the margin on either contrast, a median executable lead below one
session, a §6 tolerance breach, or a FRAGILE verdict.

**What is being separated.** Three delays, never merged: discovery → persisted document commit
(the intake clock, W1 and the census document walk), persisted → admitted to the BUY lane (the
incumbent's wait, this study), admitted → executable (the fill rule, §5, identical for every arm).

## 2. Population (frozen before any policy is applied)

| Element | Definition (frozen) |
| --- | --- |
| Admission unit | Every OPENED event in the pinned generation: one per candidate episode, keyed by `episode_id`; `payload.security_id` is the identity (its `identity_epoch` is carried as a column; the alias API resolves by `security_id` only, disclosed), `payload.ticker_at_observation` is a label only. |
| Discovery session `t_disc` | The W1 r3 receipt-recovered document `data_session` of the OPENED row's `source_receipt`: the session whose data the discovery was read from. Knowability is separate (§5). A unit whose receipt is unrecoverable is UNKNOWN (census: 0 of 1,087). |
| Session calendar | NYSE trading sessions = the date index of `data/yahoo/SPY.parquet` (dates only). Every lag, window, cap, horizon, maturity and lead is counted in these sessions. R (2026-08-26 → 2026-10-23) holds 42 sessions. |
| Lane state basis | A row's `lane`/`tier` is read from the **earliest `origin/main` commit blob that carries it**; the stamp of a session is the first blob carrying that `stamp_date`. HEAD is never read for lane state (census: 59 BUY rows and the curated rows of 07-31, 09-14 and 10-19 exist only in later heals). |
| Producer-health coverage | A session is COVERED when its first-commit stamp carries ≥ 1 curated-tier row (the BUY lane is classified inside the curated tier). Every other session is a GAP. In R, 24 of 42 sessions are covered; the 18 gaps are 09-01, 09-02, 09-14, 09-15, 09-18, 09-28, 09-29, 10-07, 10-09, 10-12, 10-13, 10-15, 10-16 and 10-19 → 10-23. A covered zero-BUY session is a legitimate non-admission. |
| Decision window | `[t_disc, t_disc + K]`, K = 10 sessions (frozen). Pre-window `[t_disc − K, t_disc)`. |
| Identity join | Security-first: for each session the security's membership symbol is taken from the alias records and confirmed by `VendorAliasTable.resolve("membership", symbol, on=session) == security_id`; the stamp row is then looked up by (session, symbol). A security with no confirmed symbol on a covered session is UNKNOWN (identity), never "never admitted" (brief: CRI). The alias snapshot is the current one (records carry no validity window; latest ingest 2026-10-19T06:10:18): a disclosed look-ahead on labels only. |
| INCUMBENT_LED | A BUY row for the security on a covered pre-window session (census: 98). Excluded from both contrasts; counted. |
| INCUMBENT_LED_UNKNOWN | No BUY row found but the pre-window contains a GAP, so a prior holding could be hidden (census: 989 of the 989 remaining R units). Excluded from the primary and the co-condition in P; in R, where it is universal, the exact pairs are reported with the flag as a descriptive sensitivity. |
| T1 status per unit | IDENTIFIED_EXACT: first BUY row in the window and no gap at or before it (26). IDENTIFIED_INTERVAL: first BUY row in the window with ≥ 1 gap before it (65): the true admission lies in `[first gap session in the window, observed stamp]`; descriptive only, both bounds printed. CASH: no BUY row and no gap in the window (0 in R). CENSORED: no BUY row and ≥ 1 gap (873). UNKNOWN: on any covered session at or before the first BUY row the security has no confirmed symbol (0) or its curated/BUY stamp has `signal_asof > stamp_date` (25). |
| Refused units | IDENTITY_UNRESOLVED and MISSING_STRUCTURAL_ANCHOR suppressions whose `source_receipt` is a turn_watch document (W1 r3 basis), excluding `ACTIVE_EPISODE_DIFFERENT_ANCHOR`. Reported in the waterfall; not in the eligible denominator of either contrast. |
| Primary units (P) | admissions with a fully covered window and pre-window, status IDENTIFIED_EXACT or CASH, not INCUMBENT_LED(_UNKNOWN), not UNKNOWN, not entitlement-excluded. |
| Co-condition pairs (P) | the primary units with status IDENTIFIED_EXACT. |
| Segment R (retrospective) | Admissions with `t_disc` 2026-08-26 → 2026-10-23 (all 1,087). Coverage makes the primary **empty** (0 CASH) and the strict co-condition set **empty** (every exact pair has a pre-window gap); R yields one descriptive readout — the 26 exact pairs with the pre-gap flag, each interval unit on both bounds — **after** freeze, and it can change no P constant (ADJ-01; review N8). R can neither promote nor reject. |
| Segment P (prospective) | Admissions with `t_disc` after the freeze date. Each P look uses the generation current at the look, pinned by its `peg:` id; admissions are keyed by `episode_id` and never re-read under a later generation. P requires the nightly producer to commit every session (PR #10255); a P session whose first-commit stamp lacks curated rows is a GAP under the same rule, and a unit with a gap anywhere in its window or pre-window is CENSORED / INCUMBENT_LED_UNKNOWN exactly as in R. |
| Entitlement | The Data OS owner's exclusion list is applied before any outcome read; pinned at freeze as `security_id`s; every exclusion counted. |
| Floors | Primary: 300 units at the fixed look. Co-condition: 100 exact pairs. A look with fewer is UNIDENTIFIED. W3's 20-session tripwire is not reused. |

## 3. Decision instants and arms

| Instant | Meaning | Source |
| --- | --- | --- |
| `t_obs` | the bar the anchor was observed on | OPENED `occurred_at`, informational |
| `t_disc` | the discovery document's `data_session` | W1 r3 receipt recovery |
| `c_disc` | the instant the discovery document first reached `origin/main` | census document walk (earliest commit per receipt; 54/54 resolved) |
| `t_cur` | the first covered session ≥ `t_disc` whose first-commit stamp has `lane == "buy"` for the security's confirmed symbol | census, §2 join |
| `c_cur` | the instant that BUY row first reached `origin/main` | census commit walk (earliest blob per (stamp_date, ticker)) |
| `t_vis`, `t_auth` | first public-board visibility; a B4 capture instant | NULL in R; descriptive only |
| `t_exec` | the fill session of an arm | §5 |

**Arms.** Each arm is a rule for `t_exec` given only information committed at or before that session.

| Arm | entry session | Role |
| --- | --- | --- |
| T0 | `k(c_disc) + 1` | challenger: enter at first persisted discovery |
| T1 | `k(c_cur) + 1`, or cash when no admission inside K | incumbent: the BUY lane as practised |
| T2 | `k(c_disc) + 1 + 2` | fixed short wait, k = 2 sessions |
| T2m | `k(c_disc) + 1 + k*` | median-wait mimic; k* = median executable lead over R's exact pairs = **0**, which coincides with T0, so **T2m is UNIDENTIFIED and not in the family** (a k* of 2 would coincide with T2 and be excluded likewise) |
| T3 | union early-turn signal (`engine/us_early_turn.py` `union_admission(price_history, asof)`, completed 3-session buckets, closes only) | in the family only if its fire is reconstructable as-known for ≥ 90% of R exact pairs; the gate is evaluated at freeze on closes before `t_disc` only and the family is fixed then |

`k(·)` is the knowable session of §5. **Lead** `L = t_exec(T1) − t_exec(T0)` in sessions (executable, both arms
through their commits). Census v4 on the freeze basis: 1,087 admissions → 98 INCUMBENT_LED →
989 with a pre-window gap → 26 IDENTIFIED_EXACT (22 / 3 / 1 by discovery month), 65
IDENTIFIED_INTERVAL (observed-stamp lag median 8, earliest-possible median 4), 873 CENSORED, 0
CASH, 25 UNKNOWN (`signal_asof`), 0 UNKNOWN (identity); every exact admission and every discovery
document became knowable exactly 1 session after its date; executable lead on the 26 exact pairs:
0 for 15, 1 for 3, 2 for 2, 3 for 6 (median 0, IQR 0–2). The r2/r3 figures (365 stamped, 96 pairs,
median lead 2) were HEAD-basis and ticker-joined and are superseded.

**Why the BUY lane is the incumbent.** The lane is the surface the product tells a user to act on;
`_classify_buy_row` admits a row only after the buy gates. The curated tier (median 2,932 rows per
stamp) is a universe; the BUY lane (median 61) is an admission. `buyable == True` is a declared
sensitivity (T1b), descriptive.

## 4. Outcomes, horizon, estimator and endpoints

| Element | Definition (frozen) |
| --- | --- |
| Price path | `data/yahoo/<TICKER>.parquet` column `close` (dividend-adjusted), the ticker being the confirmed symbol at each session; benchmark `data/yahoo/SPY.parquet` `close`. Path, column and basis frozen here; the panel's commit SHA is pinned in each look record. |
| Fill | next-session close after the knowable session (`engine/us_prophet_grades.py`: "entry is the close of the bar STRICTLY AFTER the stamp bar"). No open column exists, so no open fill. |
| Hold and exit | H = 10 sessions from each arm's own fill (positional). Time exit at the close of the 10th session after fill. |
| Outcome | `h10_net_excess_bps` = 10,000 × [(close_fill+10 / close_fill) − (SPY_fill+10 / SPY_fill)] − 50 bps for every entered arm; cash = 0, no cost. Long only. Cost floor 50 bps round trip quoted from B4 (`cost_floor_bps_round_trip`). |
| Primary endpoint (P) | mean `D_policy` over primary units. |
| Co-condition endpoint (P) | mean `D_timing` and median `L` over co-condition pairs. |
| Estimator (frozen) | one-sided 95% bounds from a **cluster bootstrap** on the discovery session `t_disc` (units sharing a session are resampled together; a security appearing in several episodes is nested in its sessions), 4,000 resamples, seed 20261031, percentile bound on the resampled mean. No analytic z or t bound is used. |
| PROMOTE (P only, fixed look) | lower one-sided 95% bound of mean `D_policy` ≥ −25 bps (B4's non-inferiority margin, quoted) AND lower bound of mean `D_timing` ≥ −25 bps AND median `L` ≥ 1 AND §6 tolerances hold AND no FRAGILE flag AND n ≥ 300 primary units AND ≥ 100 co-condition pairs. |
| Secondary family (Holm, α = 0.05, fixed at freeze) | `D_policy(T2 − T1)`; `D_policy(T3 − T1)` if T3's gate passes. T2m is out (§3). |
| Descriptive, non-promoting | the decomposition terms; interval units on both bounds; T1b; INCUMBENT_LED(_UNKNOWN) units scored (negative lead); R's 26 exact pairs; the placebo of §7; subgroups by `mdv20_usd` tercile at `t_disc`, anchor era, lead tercile; `t_vis`/`t_auth`. |
| MAE | H10 maximum adverse excursion per arm, diagnostic only (B4's primary; not re-tested). |
| Critical values and power (judgment, not population estimates) | Assumed SD: `D_policy` 500 bps (mostly unpaired, cash units carry T0's full excursion), `D_timing` 400 bps (paired, overlapping holds). Fixed look: policy SE ≈ 29 bps at n = 300, so the lower bound clears −25 only if mean `D_policy` ≥ ≈ +22 bps (the critical value; 80% power at ≈ +47 bps); timing SE ≈ 40 bps at 100 pairs, critical ≈ +41 bps (80% power ≈ +75 bps). A rule with true `D_policy` = 0 passes the policy test about 29% of the time at n = 300 — the test is non-inferiority against −25 bps, not superiority, and PROMOTE says "not worse than the lane", never "better". In R both tests are impossible (no units). |

## 5. Execution model and point-in-time rules

| Rule | Definition (frozen) |
| --- | --- |
| Knowable session `k(c)` | For an artifact first committed to `origin/main` at instant `c` (ET), the first NYSE session whose 16:00 ET close is strictly after `c + 30 min`. Applied identically to the discovery document (`c_disc`) and the BUY stamp (`c_cur`). Census v4: both are 1 session after their date for every R exact pair (26/26 and 26/26). The generation's own `recorded_at` is reported (all 1,087 within 2 sessions) and is not the T0 clock: the document is the persisted discovery; the generation adds identity and the anchor from it. |
| Fill | `t_exec = k(c) + 1`: the close of the session after the knowable session. An intraday commit can never fill at the same session's close. |
| Invalidation anchor | OPENED `payload.structural_anchor.price` (`turn_watch_reset_low`, adjusted-close basis), the same number for every arm. |
| AVOIDED (any arm) | if any session close in `[t_disc, t_exec − 1]` is below the anchor, the arm does not enter; cash 0; recorded AVOIDED. |
| REFUSED | if the fill-session close is below the anchor, no fill; cash 0; counted. |
| False start | an entered arm whose close falls below the anchor within the hold **before** any close ≥ fill + ATR14, ATR14 = mean absolute close-to-close change over the 14 sessions strictly before `t_disc`, the same number for every arm. Flags the unit; the time exit stands. |
| Panel censoring | a hold crossing a session the panel lacks (W3's `session_missing` class) is CENSORED for that arm; counted. |
| Bounds | each endpoint at cost ×1 (primary), cost ×2, with the top 5% of |D| units excluded. A flip of PROMOTE/REJECT under any bound is FRAGILE, and **FRAGILE blocks PROMOTE**. |

## 6. Tolerable additional false-positive cost (declared now)

| Tolerance | Value | Binding |
| --- | --- | --- |
| (i) false-start rate | on co-condition pairs (both arms enter), T0's false-start rate may exceed T1's by at most **10 percentage points** absolute | blocks PROMOTE at the fixed look; descriptive before it (at 100 pairs the resolvable difference is ≈ 15 pp) |
| (ii) false-start loss | over primary units, `mean(min(D_policy, 0) · 1[T0 false start])` ≥ **−25 bps** — T0's false starts alone may not consume the whole non-inferiority margin (at the (i) limit of 10 per 100 that is 250 bps, five cost floors, per false start) | blocks PROMOTE at the fixed look; never a REJECT trigger |
| (iii) missed upside | priced inside `D_policy` by the cash units (T0 enters, T1 holds cash); no separate tolerance | — |

## 7. Looks, multiplicity, dispositions, falsifiers and what cannot happen

| Element | Definition (frozen) |
| --- | --- |
| R look | exactly one, after freeze and after maturity: the first session after `max(t_disc) + 1 + 1 + K + H` = 2026-10-23 + 22 sessions (the exact session is written at freeze); descriptive only; changes no P constant |
| P looks | monitoring at 50 and 100 primary units (no promotion), futility at 150, fixed verdict when **both** n ≥ 300 primary units and ≥ 100 co-condition pairs hold (B4's look counts quoted: `monitoring_only_episode_counts [50, 100]`, `fixed_episode_count_per_distinct_cell 300`); if the pair floor is not met within 6 months of the 300th unit the fixed look is taken as UNIDENTIFIED-terminal |
| Futility (W2's own rule) | at 150 primary units, stop for futility if the upper one-sided 95% bound of mean `D_policy` < −25 bps. B4's rule is different and is quoted, not borrowed: `"futility": {"episode_count_per_cell": 150, "rule": "stop as REJECTED if every cell's primary lower confidence bound excludes improvement"}` |
| REJECT (P only) | upper one-sided 95% bound of mean `D_policy` < −25 bps at the fixed look with the floor met |
| RETAIN_IN_SHADOW | floor met, neither PROMOTE nor REJECT |
| UNIDENTIFIED / FRAGILE / FAILED_TOLERANCE | floor not met or coverage-limited (every R look); a bound flip; a §6 breach |
| Multiplicity | Holm over the §4 secondary family; the primary and its co-condition stand alone |
| Scientific falsifiers (descriptive) | (a) **placebo discovery**: T0 re-run at `t_disc − 5` on the co-condition pairs, same fill, hold and cost, anchor and ATR14 taken at the placebo session; reported beside the real contrast, never a gate (round-3 P2: the placebo window still contains the selected run, so it cannot certify absence of selection); (b) `D_timing` by executable-lead tercile — a cost of waiting predicts no decrease with lead; (c) the decomposition's sign pattern — a policy gain carried entirely by the non-admitted term with a negative timing term is reported as "selection, not timing". |
| Implementation invariant (not a falsifier of H_W2) | every numerator in §4–§6 is computed over primary units or co-condition pairs; adding or removing refused units leaves every numerator identical. |
| Required waterfall | eligible → admissions → `t_disc` recovered → INCUMBENT_LED → INCUMBENT_LED_UNKNOWN → IDENTIFIED_EXACT / IDENTIFIED_INTERVAL / CASH / CENSORED / UNKNOWN → entitlement excluded → AVOIDED → REFUSED → entered → panel-censored → matured → false starts, per arm |
| Dispositions are by rule | never a judgment made after reading outcomes. |

### Cases that must be exercised before any disposition (brief §Cases that can disprove a superficial repair)

| Case | What it must show |
| --- | --- |
| CRI (identity) | a security with no confirmed membership symbol on a covered session is UNKNOWN, never a minted identity or "never admitted"; a renamed security is found under its confirmed symbol (the join is security-first) |
| RCL / CSCO (which row set `t_cur`) | the look record names the first-commit row (`stamp_date`, symbol, `lane`, earliest commit SHA, commit instant ET, knowable session) that set `t_cur`, and shows that HEAD's healed row was not used |
| AMZN / USFD / WM / KO (out of universe vs timing) | a window with a gap and no BUY row is CENSORED, not late; a covered zero-BUY session is a non-admission; a fully covered window with no BUY row is CASH in the policy contrast |
| CTVA + a loser (false start) | a T0 entry that closes below the anchor before +ATR14 is a false start and still exits at H10 |
| STLD / NEM (avoided) | an arm invalidated in `[t_disc, t_exec − 1]` records AVOIDED with cash 0 and stays in the waterfall |
| Incumbent-led name | a security in the BUY lane on a covered pre-window session is INCUMBENT_LED; one whose pre-window has a gap is INCUMBENT_LED_UNKNOWN; neither is in the primary |

## 8. What this registration does not authorize

No outcome read before freeze; no change to B4 #7751 A1, its capture, its cells, or W3; no
historical backfill into P; no new data-purpose grant; no production, board, alert or trade effect.
The B-17 historical population (7,918 C0 episodes, none with a complete 34-session window) is not
this study's R segment and is not substituted by it; B-17 stays null. Required before freeze:
independent non-author review of this exact revision; the Data OS owner's entitlement exclusion
list; the census v4 re-run (both walks) attached; the T3 gate result; and a machine freeze
mirroring §2–§7.

## Frozen-field block (to be mirrored into the machine freeze at freeze time)

```yaml
schema: us.prophet_entry_timing_w2_design/v4
status: DRAFT_UNFROZEN
adjudications: [W2-ADJ-01 policy contrast is the primary (P only), W2-ADJ-02 timing co-condition on exact pairs only, W2-ADJ-03 both arms timed by first commits]
parents: [B4 PREREG.json (quoted constants only), W3_RACE_PREREG.md (session_missing class only), ENTRY_TIMING_W1 r3 (d03acfd0)]
generation_id: peg:23be3409c3a57944dd08e09e38e3b7541926c0f244e9d0d3b4a0b4a8aacedbf9
session_calendar: data/yahoo/SPY.parquet date index (NYSE sessions); all units in sessions
lane_state_basis: earliest origin/main commit blob per (stamp_date, ticker); coverage = first blob carrying the stamp date; HEAD never read for lane state
coverage: session COVERED iff its first-commit stamp has >= 1 curated-tier row; else GAP
identity_join: security-first; membership symbol from alias records confirmed by VendorAliasTable.resolve("membership", symbol, on=session) == security_id; unconfirmed -> UNKNOWN; alias snapshot = current (no validity windows; disclosed look-ahead on labels)
decision_window_K_sessions: 10
pre_window_sessions: 10
incumbent_led: BUY row on a covered pre-window session -> excluded
incumbent_led_unknown: pre-window contains a GAP -> excluded from P primary and co-condition; R descriptive sensitivity
t1_status: [IDENTIFIED_EXACT, IDENTIFIED_INTERVAL (descriptive; bounds = first gap session in window .. observed stamp), CASH (no gap, no BUY), CENSORED (gap, no BUY), UNKNOWN (identity or signal_asof > stamp_date on any covered session at or before the first BUY row)]
primary_units: fully covered window + pre-window; IDENTIFIED_EXACT or CASH; not INCUMBENT_LED(_UNKNOWN); not UNKNOWN; not entitlement-excluded
co_condition_pairs: primary units with IDENTIFIED_EXACT
primary_estimand: D_policy = outcome(T0) - outcome(T1), ITT, T1 = cash (0, no cost) when not admitted inside K; P only; decomposition printed
co_condition: D_timing and executable lead L = t_exec(T1) - t_exec(T0) on co-condition pairs; guard, never a promotion basis
knowable_session: first NYSE session whose 16:00 ET close > first-commit instant + 30 min; applied to the discovery document (c_disc) and the BUY stamp (c_cur)
fill: close of the session after the knowable session (engine/us_prophet_grades.py next-close basis)
price_panel: {path: data/yahoo/<TICKER>.parquet, column: close, benchmark: data/yahoo/SPY.parquet, commit: pinned per look record}
arms: {T0: k(c_disc)+1, T1: k(c_cur)+1 or cash, T2: k(c_disc)+1+2, T2m: UNIDENTIFIED (k_star 0 coincides with T0), T3: union early-turn if gate >= 90% on closes before t_disc}
k_fixed_sessions: 2
k_star_sessions_exact_basis: 0
horizon_sessions: 10
exit: time_exit_at_h10_close
cost_floor_bps_round_trip: 50
estimator: {method: cluster_bootstrap, cluster: t_disc session (securities nested), resamples: 4000, seed: 20261031, bound: one-sided 95% percentile of the resampled mean}
promote: {segment: P only, policy_lower_bound_bps: -25, timing_lower_bound_bps: -25, min_median_executable_lead_sessions: 1, tolerances: hold, fragile: blocks, min_primary_units: 300, min_co_condition_pairs: 100}
reject: {segment: P only, rule: policy_upper_one_sided_95_bound < -25 bps at the fixed look with floor met}
futility_w2: at 150 primary units, policy_upper_one_sided_95_bound < -25 bps (B4 rule quoted, not borrowed)
looks_P: {monitoring: [50, 100], futility: 150, fixed: 300 primary units AND 100 pairs; pair floor deadline 6 months after the 300th unit -> UNIDENTIFIED-terminal}
look_R: {t_disc_from: 2026-08-26, t_disc_to: 2026-10-23, looks: 1, after_freeze: true, may_promote: false, may_reject: false, changes_P_constants: false, maturity_session: set at freeze (2026-10-23 + 22 sessions)}
secondary_family_holm: [D_policy(T2 - T1), D_policy(T3 - T1) if gate passes]
descriptive: [decomposition terms, interval units both bounds, T1b buyable==True, incumbent_led(_unknown) negative lead, R 26 exact pairs with pre-gap flag, placebo T0 at t_disc - 5, mdv20_usd terciles, anchor era, lead terciles, t_vis, t_auth]
avoided_window: [t_disc, t_exec - 1] for every arm
false_start: close < anchor within hold before any close >= fill + ATR14 ; ATR14 = mean |dclose| over 14 sessions strictly before t_disc
tolerance: {false_start_rate_delta_pp_max: 10 (co-condition pairs; binds at the fixed look), false_start_loss_mean_bps_min: -25 (mean of min(D_policy,0)*1[T0 false start] over primary units; binds at the fixed look; never a REJECT trigger)}
bounds: [cost_x1, cost_x2, drop_top_5pct_abs_D]; any flip -> FRAGILE -> blocks PROMOTE
critical_values: {assumed_sd_policy_bps: 500, assumed_sd_timing_bps: 400, policy_n300_critical_mean_bps: 22, policy_n300_80pct_power_bps: 47, timing_n100_critical_mean_bps: 41, timing_n100_80pct_power_bps: 75, pass_rate_at_true_zero_n300: 0.29}
generation_recorded_at: reported per unit (all 1087 R units <= 2 sessions); not the T0 clock
falsifiers_descriptive: [placebo at t_disc - 5, D_timing by lead tercile, decomposition sign pattern]
implementation_invariant: numerators invariant to refused-unit count (not a falsifier of H_W2)
dispositions: [PROMOTE (P only), RETAIN_IN_SHADOW, REJECT (P only), UNIDENTIFIED, FRAGILE, FAILED_TOLERANCE]
authority: measurement only; no trade/sizing/alert; never amends #7751 A1; B4 t_auth descriptive only
```
