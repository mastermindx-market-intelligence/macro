# Entry Timing W2 — design registration: does entering at first persisted discovery beat following the BUY lane? (2026-10-31, revision 5)

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
unmeasured; N1–N14). r4 → REVISE (P1 the session-cluster bootstrap ignored dependence between
overlapping holds and the floors counted units, not periods; P2 the lane-state rule differed between
code and prose and its "59 BUY rows / 07-31 heal" evidence was an artifact of an unwalked July
parquet; N1–N14). r5 (this revision) keeps ADJ-01..03, corrects ADJ-03's evidence, and adds three
adjudications. Each is stated with its reason so a reviewer can attack the ruling and not only the
text:

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
- **W2-ADJ-03 — both arms are timed by arrival on `origin/main`, not by dates.** The census walks
  the turn_watch documents as it walks the candidate stamps (same digest law as W1 r3), takes the
  **first-parent** arrival commit (a side-branch committer time can predate arrival; round-4 N3),
  reads lane state from the **first-arrival** blob of each stamp date, and uses the **executable**
  lead `t_exec(T1) − t_exec(T0)`. *Evidence corrected in r5:* with all four monthly parquets walked
  (156 first-parent commits, 54 of 54 stamp dates), HEAD differs from the first-arrival basis by
  **154 BUY rows**, all added by two heals — 09-14 (+50 rows, healed 09-16) and 10-19 (+104, healed
  10-21) — and 07-31 is healthy on both bases. The r4 "59 rows / 07-31" figures were a coverage
  artifact of walking 2026-08..10 only, exactly as round 4 said.
- **W2-ADJ-04 — one heal rule, in the code and the prose.** A BUY row counts only if it is in the
  first blob that carried its stamp date and its arrival is knowable at or before `t_disc + K`. A
  later blob that changes a stamp date's BUY set is a HEAL and that session is a GAP for every unit
  (coverage and lane state follow the same rule; the healed rows are never read). Reason: a healed
  row was not the lane as practised; counting it at its heal time would charge producer-outage lag
  and hindsight gating to the incumbent, and admitting it at its stamp date would be look-ahead.
  The conservative rule shrinks the identified set (09-14 and 10-19 become gaps) and is accepted.
- **W2-ADJ-05 — the sampling unit is a calendar block, not a session.** Holds of H = 10 sessions
  discovered up to K + H + 2 sessions apart overlap, so units in different discovery sessions share
  basket-factor exposure that SPY-excess does not remove. The estimator is a circular moving block
  bootstrap over the session calendar (block = 22 sessions), and the floors count distinct discovery
  sessions and blocks, not only units. Reason: a session-cluster bound is anti-conservative under
  that dependence (round-4 P1 shows a design effect of ≈ 2.25 at R's density), and a PROMOTE must
  not be reachable through an inference artifact.
- **W2-ADJ-06 — the −25 bps margin is retained as a differential only; T0 must also not lose.**
  B4's margin is a paired comparison against C0; here T1 is cash on every non-admitted unit, so
  the policy contrast is mostly T0 against cash. PROMOTE therefore also requires the lower bound of
  T0's own mean net excess over primary units to be ≥ 0, and the timing guard binds on its point
  estimate. Reason: a buy-everything policy that loses to SPY net of cost must not promote because
  the lane held cash more often (round-4 N1/N2).

Every count quoted here comes from `research/prophet_v4/entry_timing_w2_t1_census.py` v5 run on the
freeze basis (committed output `research/prophet_v4/entry_timing_w2_t1_census_2026-10-31.json`;
dates, tickers, lane/tier flags, `signal_asof`, `recorded_at` and arrival instants only — no price,
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
stamp dates 2026-07-31 → 2026-10-29, all four monthly parquets walked; on the first-arrival basis 33
of them carry curated-tier rows, the last on 2026-10-14; HEAD shows 35 because later heals added
curated and BUY rows to 09-14 and 10-19 — a heal is not the lane as practised (ADJ-04); after 10-19
every stamp is scan-only because the nightly commits were rejected by GH001, the defect PR #10255
repairs); the lane rules in
`engine/us_candidate_lanes.py` (`_classify_buy_row`, `build_candidate_pool`); the grade producer
`engine/us_prophet_grades.py` (next-bar close fill, positional horizons, SPY benchmark from
`data/yahoo/SPY.parquet`); the per-ticker dividend-adjusted close panel
`data/yahoo/<TICKER>.parquet` (columns `close_price`, `close`, `volume`; no open/high/low); the
membership alias records in `data/reference/vendor_aliases.parquet` (1,941 rows, 1,938 securities,
3 with more than one symbol, no validity windows, latest ingest 2026-10-19T06:10:18; census
snapshot sha256 `ff8a32df8e47…`); the completion
brief (`research/prophet_v4/PROPHET_US_ENTRY_TIMING_COMPLETION_BRIEF_2026-10-31.md` at
`e757498822a2`); and the B4/W3 freezes named above.

**Prior knowledge disclosed.** (a) The brief records that the curated BUY surface underperformed
over a window overlapping R; the authors knew this before r1. (b) The census (dates only) shows
that on the 26 exactly identified R pairs the incumbent admitted on the discovery session itself in
15 cases: the executable lead is 0 for 15 of 26 and its median is 0 (unchanged under the r5 heal
rule — none of the 26 sits on a healed session). If that persists in P, the
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
a promotion basis. What it can do: stop a PROMOTE in which T0 entered the lane's own names worse
than the lane did (the pairs' point estimate must be ≥ 0 and its lower bound ≥ −25 bps, §4). What
it cannot do: certify the absence of selection — the pair set is chosen by a post-T0 event, so a
favourable timing reading is weak evidence, and an unfavourable one is strong.

**H_W2 (one-sided).** In P, buying at every persisted discovery is not economically inferior to
following the BUY lane, net of the cost floor, is not itself a losing policy against SPY net of
cost, AND on the lane's own exactly admitted names T0 is not inferior to T1 while leading it by at
least one executable session in median. The null is inferiority by more than the margin on either
contrast, a T0 lower bound below 0, a timing point estimate below 0, a median executable lead
below one session, a §6 tolerance breach, or a FRAGILE verdict.

**What is being separated.** Three delays, never merged: discovery → persisted document commit
(the intake clock, W1 and the census document walk), persisted → admitted to the BUY lane (the
incumbent's wait, this study), admitted → executable (the fill rule, §5, identical for every arm).

## 2. Population (frozen before any policy is applied)

| Element | Definition (frozen) |
| --- | --- |
| Admission unit | Every OPENED event in the pinned generation: one per candidate episode, keyed by `episode_id`; `payload.security_id` is the identity (its `identity_epoch` is carried as a column; the alias API resolves by `security_id` only, disclosed), `payload.ticker_at_observation` is a label only. |
| Discovery session `t_disc` | The W1 r3 receipt-recovered document `data_session` of the OPENED row's `source_receipt`: the session whose data the discovery was read from. Knowability is separate (§5). A unit whose receipt is unrecoverable is UNKNOWN (census: 0 of 1,087). |
| Session calendar | NYSE trading sessions = the date index of `data/yahoo/SPY.parquet` (dates only). Every lag, window, cap, horizon, maturity and lead is counted in these sessions. R (2026-08-26 → 2026-10-23) holds 42 sessions. |
| Lane state basis (ADJ-04) | The stamp of a session is the **first blob carrying that `stamp_date` on first-parent `origin/main`**; its BUY rows, curated coverage and `signal_asof` are read from that blob only, and its knowable session is that blob's arrival. A later blob that changes the session's BUY set is a HEAL: the session is a GAP for coverage and lane state alike, and the healed rows are never read. HEAD is never read (census: 154 BUY rows exist only in the 09-14 and 10-19 heals; both sessions are GAPs). |
| Producer-health coverage | A session is COVERED when its first-arrival stamp carries ≥ 1 curated-tier row (the BUY lane is classified inside the curated tier) and the session is not healed. Every other session is a GAP. In R, 24 of 42 sessions are covered; the 18 gaps are 09-01, 09-02, 09-14, 09-15, 09-18, 09-28, 09-29, 10-07, 10-09, 10-12, 10-13, 10-15, 10-16 and 10-19 → 10-23. A covered zero-BUY session is a legitimate non-admission. |
| Decision window | `[t_disc, t_disc + K]`, K = 10 sessions (frozen). Pre-window `[t_disc − K, t_disc)`. |
| Identity join | Security-first: for each session **every** membership symbol recorded for the security is confirmed by `VendorAliasTable.resolve("membership", symbol, on=session) == security_id`, and the stamp row is looked up by (session, symbol) for each confirmed symbol (a multi-symbol security loses no row; 3 such securities exist, none among R's exact pairs). The test is applied on every covered window session for every unit — the span does not depend on whether or when the lane admitted (round-4 N7). A security with no confirmed symbol on any covered window session is UNKNOWN (identity), never "never admitted" (brief: CRI). Disclosed limit: records carry no validity window, so the per-session confirmation is currently the same answer on every session; it becomes a real clock when windows exist. Snapshot rule: in P each look resolves identity from the alias blob current on first-parent `origin/main` at the look and pins its sha256 in the look record; a unit resolved at one look is never re-resolved under a later blob, so a later delisting cannot become a future-driven exclusion. R's census used the current snapshot (`ff8a32df8e47…`, latest ingest 2026-10-19), a disclosed look-ahead on labels only. |
| INCUMBENT_LED | A BUY row for the security on a covered pre-window session (census: 98). Excluded from both contrasts; counted. |
| INCUMBENT_LED_UNKNOWN | No BUY row found but the pre-window contains a GAP or a covered pre-window session on which the security has no confirmed symbol, so a prior holding could be hidden (census: 989 of the 989 remaining R units, all by gap, 0 by identity). Excluded from the primary and the co-condition in P; in R, where it is universal, the exact pairs are reported with the flag as a descriptive sensitivity. |
| T1 status per unit | A BUY row is an **admission inside K** only if its session is covered and its knowable session `k(c_cur)` ≤ `t_disc + K` (a row stamped on the last window session arrives one session late and is not inside K: 21 R units, treated as no admission). IDENTIFIED_EXACT: first admission inside K with no gap at or before it (26). IDENTIFIED_INTERVAL: first admission inside K with ≥ 1 gap before it (44): the true admission lies in `[first gap session in the window, observed stamp]`; descriptive only, both bounds printed. CASH: no admission inside K and no gap in the window (0 in R). CENSORED: no admission inside K and ≥ 1 gap (918). UNKNOWN: the security has no confirmed symbol on some covered window session (0) or the row that would set `t_cur` has `signal_asof > stamp_date` in its first-arrival blob (1). |
| Refused units | IDENTITY_UNRESOLVED and MISSING_STRUCTURAL_ANCHOR suppressions whose `source_receipt` is a turn_watch document (W1 r3 basis), excluding `ACTIVE_EPISODE_DIFFERENT_ANCHOR`. Reported in the waterfall; not in the eligible denominator of either contrast. |
| Primary units (P) | admissions with a fully covered window and pre-window, status IDENTIFIED_EXACT or CASH, not INCUMBENT_LED(_UNKNOWN), not UNKNOWN, not entitlement-excluded. |
| Co-condition pairs (P) | the primary units with status IDENTIFIED_EXACT. |
| Segment R (retrospective) | Admissions with `t_disc` 2026-08-26 → 2026-10-23 (all 1,087). Coverage makes the primary **empty** (0 CASH) and the strict co-condition set **empty** (every exact pair has a pre-window gap); R yields one descriptive readout — the 26 exact pairs with the pre-gap flag, each interval unit on both bounds — **after** freeze, and it can change no P constant (ADJ-01; review N8). R can neither promote nor reject. |
| Segment P (prospective) | Admissions with `t_disc` after the freeze date (identity by the look's pinned alias blob, lane state by first-arrival blobs under ADJ-04). Each P look uses the generation current at the look, pinned by its `peg:` id; admissions are keyed by `episode_id` and never re-read under a later generation. P requires the nightly producer to commit every session (PR #10255); a P session whose first-commit stamp lacks curated rows is a GAP under the same rule, and a unit with a gap anywhere in its window or pre-window is CENSORED / INCUMBENT_LED_UNKNOWN exactly as in R. |
| Entitlement | The Data OS owner's exclusion list is applied before any outcome read; pinned at freeze as `security_id`s; every exclusion counted. |
| Floors (ADJ-05) | Primary: ≥ 300 units **and** those units' discovery sessions span ≥ 110 distinct NYSE sessions (≥ 5 full blocks of 22). Co-condition: ≥ 100 exact pairs spanning ≥ 44 distinct discovery sessions (≥ 2 blocks). A look with fewer on any count is UNIDENTIFIED. At R's density (≈ 26 units per covered session) the session floor binds, so the fixed look is ≈ 5–6 months into P. W3's 20-session tripwire is not reused. |

## 3. Decision instants and arms

| Instant | Meaning | Source |
| --- | --- | --- |
| `t_obs` | the bar the anchor was observed on | OPENED `occurred_at`, informational |
| `t_disc` | the discovery document's `data_session` | W1 r3 receipt recovery |
| `c_disc` | the instant the discovery document first arrived on first-parent `origin/main` | census document walk (first-parent arrival per receipt; 54/54 resolved) |
| `t_cur` | the first covered session ≥ `t_disc` whose first-arrival stamp has `lane == "buy"` for a confirmed symbol of the security and whose arrival is knowable ≤ `t_disc + K` | census, §2 join and ADJ-04 |
| `c_cur` | the arrival instant of the first blob carrying `t_cur`'s stamp date (one instant per session; every row of that stamp shares it) | census commit walk |
| `t_vis`, `t_auth` | first public-board visibility; a B4 capture instant | NULL in R; descriptive only |
| `t_exec` | the fill session of an arm | §5 |

**Arms.** Each arm is a rule for `t_exec` given only information committed at or before that session.

| Arm | entry session | Role |
| --- | --- | --- |
| T0 | `k(c_disc) + 1` | challenger: enter at first persisted discovery |
| T1 | `k(c_cur) + 1`, or cash when no admission inside K | incumbent: the BUY lane as practised |
| T2 | `k(c_disc) + 1 + 2` | fixed short wait, k = 2 sessions |
| T2m | `k(c_disc) + 1 + k*` | median-wait mimic; k* = median executable lead over R's exact pairs = **0**, which coincides with T0, so **T2m is UNIDENTIFIED and not in the family** (a k* of 2 would coincide with T2 and be excluded likewise) |
| T3 | union early-turn signal (`engine/us_early_turn.py` `union_admission(price_history, asof)`, completed 3-session buckets, closes only) | in the family only if, for ≥ 90% of R exact pairs, the panel **index** holds every session the signal's lookback needs through `t_disc − 1` with no `session_missing` (an availability check on dates only; no close value is read before freeze — round-4 N9); the family is fixed at freeze and T3 is scored only at the R look |

`k(·)` is the knowable session of §5. **Lead** `L = t_exec(T1) − t_exec(T0)` in sessions (executable, both arms
through their arrivals). Census v5 on the freeze basis: 1,087 admissions → 98 INCUMBENT_LED →
989 with a pre-window gap → 26 IDENTIFIED_EXACT (22 / 3 / 1 by discovery month), 44
IDENTIFIED_INTERVAL (observed-stamp lag median 6, earliest-possible median 4), 918 CENSORED (21 of
them had a BUY row on the last window session whose arrival was knowable one session too late),
0 CASH, 1 UNKNOWN (`signal_asof`), 0 UNKNOWN (identity); every exact admission and every discovery
document became knowable exactly 1 session after its date; executable lead on the 26 exact pairs:
0 for 15, 1 for 3, 2 for 2, 3 for 6 (median 0, IQR 0–2); 0 primary units and 0 strict pairs, so
R spans 0 distinct primary discovery sessions. The r4 figures (65 interval, 873 censored, 25
UNKNOWN) read HEAD for `signal_asof` and walked August onward only; they are superseded.

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
| Estimator (frozen, ADJ-05) | one-sided 95% percentile bounds from a **circular moving block bootstrap** over the NYSE session calendar of the look: the units are grouped into per-session cohorts by `t_disc` (covered zero-unit sessions are empty cohorts and stay in the calendar), a block is **ℓ = 22 consecutive sessions** (K + H + 2, the longest span over which two units' holds can overlap), blocks start at a uniformly drawn session and wrap circularly, enough blocks are drawn to cover the calendar length, and the statistic is the **unit-weighted mean** over the units in the drawn blocks. 4,000 resamples, NumPy `Generator(PCG64(20261031))`, **one index set shared by every endpoint, bound and tolerance** of the look. No analytic z or t bound is used; a per-session cluster bound is reported beside it as a diagnostic only. |
| PROMOTE (P only, fixed look) | lower one-sided 95% bound of mean `D_policy` ≥ −25 bps (B4's non-inferiority margin, quoted, used as a differential only) AND lower one-sided 95% bound of mean `outcome(T0)` over primary units ≥ 0 (ADJ-06: T0 is not a losing policy against SPY net of cost) AND point estimate of mean `D_timing` ≥ 0 AND lower bound of mean `D_timing` ≥ −25 bps AND median `L` ≥ 1 AND §6 tolerances hold AND no FRAGILE flag AND the §2 floors (units, pairs, distinct sessions) are met. |
| Secondary family (Holm, α = 0.05, fixed at freeze) | `D_policy(T2 − T1)`; `D_policy(T3 − T1)` if T3's gate passes. T2m is out (§3). |
| Descriptive, non-promoting | the decomposition terms; interval units on both bounds; T1b; INCUMBENT_LED(_UNKNOWN) units scored (negative lead); R's 26 exact pairs; the placebo of §7; subgroups by `mdv20_usd` tercile at `t_disc`, anchor era, lead tercile; `t_vis`/`t_auth`. |
| MAE | H10 maximum adverse excursion per arm, diagnostic only (B4's primary; not re-tested). |
| Critical values and power (judgment, not population estimates) | Assumed SD: `D_policy` 500 bps (mostly unpaired, cash units carry T0's full excursion), `D_timing` 400 bps (paired, overlapping holds). Assumed dependence: design effect **2.25** on the policy contrast (round-4 P1's figure: an intra-span correlation of 0.05 across ≈ 26 units per session; a larger true correlation raises every number below) and **1.5** on the paired timing contrast. Fixed look at n = 300: policy SE ≈ 29 bps under independence, ≈ **43 bps** with the design effect, so the lower bound clears −25 only if mean `D_policy` ≥ ≈ **+46 bps** (80% power at ≈ +83 bps); timing SE ≈ 40 → ≈ **49 bps** at 100 pairs, critical ≈ **+56 bps** (80% power ≈ +97 bps). A rule with true `D_policy` = 0 passes the policy margin test about **14%** of the time (22% under independence; the r4 figure of 29% was an arithmetic error) — the test is non-inferiority against −25 bps, not superiority, and PROMOTE says "not worse than the lane and not losing", never "better". These are planning numbers; the bound that decides is the block bootstrap's. In R both tests are impossible (no units). |

## 5. Execution model and point-in-time rules

| Rule | Definition (frozen) |
| --- | --- |
| Knowable session `k(c)` | For an artifact whose first blob **arrived on first-parent `origin/main`** at instant `c` (ET; a side-branch committer time is never used), the first NYSE session whose 16:00 ET close is strictly after `c + 30 min`. Applied identically to the discovery document (`c_disc`) and the BUY stamp (`c_cur`). Census v5: both are 1 session after their date for every R exact pair (26/26 and 26/26). |
| Anchor knowability | The generation's `recorded_at` is not the T0 clock (the document is the persisted discovery), but the anchor and identity come from the OPENED payload, so a unit's anchor-dependent rules (AVOIDED, REFUSED, false start) use the payload only if `recorded_at` ≤ the T0 fill instant (16:00 ET of `t_exec(T0)`); otherwise the unit is UNKNOWN (anchor) and leaves the primary, counted. Census v5: 1,087 of 1,087 R units satisfy it. |
| Fill | `t_exec = k(c) + 1`: the close of the session after the knowable session. An intraday commit can never fill at the same session's close. |
| Invalidation anchor | OPENED `payload.structural_anchor.price` (`turn_watch_reset_low`, adjusted-close basis), the same number for every arm. |
| AVOIDED (any arm) | if any session close in `[t_disc, t_exec − 1]` is below the anchor, the arm does not enter; cash 0; recorded AVOIDED. |
| REFUSED | if the fill-session close is below the anchor, no fill; cash 0; counted. |
| False start | an entered arm whose close falls below the anchor within the hold **before** any close ≥ fill + ATR14, ATR14 = mean absolute close-to-close change over the 14 sessions strictly before `t_disc`, the same number for every arm. Flags the unit; the time exit stands. |
| Panel censoring | a hold crossing a session the panel lacks (W3's `session_missing` class) is CENSORED for that arm; counted. |
| Bounds | each endpoint at cost ×1 (primary), cost ×2, and with the top 5% of |D| units excluded — the trim is taken **once** on the full-sample ranking before resampling, and all three bounds reuse the one shared index set. A flip of PROMOTE/REJECT under any bound is FRAGILE, and **FRAGILE blocks PROMOTE**. |

## 6. Tolerable additional false-positive cost (declared now)

| Tolerance | Value | Binding |
| --- | --- | --- |
| (i) false-start rate | on co-condition pairs (both arms enter), T0's false-start rate may exceed T1's by at most **10 percentage points** absolute | blocks PROMOTE at the fixed look; descriptive before it (at 100 pairs the resolvable difference is ≈ 15 pp) |
| (ii) false-start loss, differential | over primary units, `mean(loss_T0 − loss_T1)` ≥ **−50 bps**, where `loss_arm = min(outcome(arm), 0) · 1[arm false start]` (0 for a cash arm) — T0's **additional** false-start money may not exceed one cost floor per unit. Calibration: at the (i) limit of 10 pp more false starts with a mean false-start loss of 300 bps the differential is ≈ −30 bps, inside the tolerance; it binds when T0's extra false starts are both more frequent and deeper than that (≈ 500 bps at 10 pp). The r4 version was one-sided in T0's rate and would have bound on any false-start level. | blocks PROMOTE at the fixed look; never a REJECT trigger |
| (iii) missed upside | T0's missed upside is a unit where T0 is AVOIDED or REFUSED (anchor broken before its fill) and T1 later enters and gains: it enters `D_policy` as a negative term (T0 cash 0, T1 positive). The lane's missed upside (T1 cash on a name T0 bought and that rallied) enters as a positive term. Both are priced inside `D_policy`; no separate tolerance. | — |

## 7. Looks, multiplicity, dispositions, falsifiers and what cannot happen

| Element | Definition (frozen) |
| --- | --- |
| R look | exactly one, after freeze and after maturity: the first session after `max over R units of t_exec(arm) + H` across the arms in the family (the exact session is written at freeze from the census; under the observed knowable shift of 1 it is 2026-10-23 + 22 sessions, but the rule is the maximum observed `t_exec`, not the assumed shift); descriptive only; changes no P constant |
| P looks | monitoring at 50 and 100 primary units (no promotion), futility at 150, fixed verdict at the first session on which **all** §2 floors hold (300 units over ≥ 110 distinct sessions; 100 pairs over ≥ 44) (B4's look counts quoted: `monitoring_only_episode_counts [50, 100]`, `fixed_episode_count_per_distinct_cell 300`); if the pair floors are not met within 6 months of the session on which the primary floors were met, the fixed look is taken as UNIDENTIFIED-terminal |
| Futility (W2's own rule) | at 150 primary units, stop if the upper one-sided 95% block-bootstrap bound of mean `D_policy` < −25 bps; the disposition is **REJECT (futility)** — terminal for this registration, reported as `REJECT_FUTILITY`, never re-looked. B4's rule is different and is quoted, not borrowed: `"futility": {"episode_count_per_cell": 150, "rule": "stop as REJECTED if every cell's primary lower confidence bound excludes improvement"}` |
| REJECT (P only) | upper one-sided 95% bound of mean `D_policy` < −25 bps at the fixed look with the floor met |
| RETAIN_IN_SHADOW | floor met, neither PROMOTE nor REJECT |
| UNIDENTIFIED / FRAGILE / FAILED_TOLERANCE | floor not met or coverage-limited (every R look); a bound flip; a §6 breach |
| Multiplicity | Holm over the §4 secondary family; the primary and its co-condition stand alone |
| Scientific falsifiers (descriptive) | (a) **placebo discovery**: T0 re-run at `t_disc − 5` on the co-condition pairs, same fill, hold and cost, anchor and ATR14 taken at the placebo session; reported beside the real contrast, never a gate (round-3 P2: the placebo window still contains the selected run, so it cannot certify absence of selection); (b) `D_timing` by executable-lead tercile — a cost of waiting predicts no decrease with lead; (c) the decomposition's sign pattern — a policy gain carried entirely by the non-admitted term with a negative timing term is reported as "selection, not timing"; since r5 this pattern also **blocks PROMOTE** through the §4 timing point-estimate condition, so (c) is binding, not only descriptive. |
| Implementation invariant (not a falsifier of H_W2) | every numerator in §4–§6 is computed over primary units or co-condition pairs; adding or removing refused units leaves every numerator identical. |
| Required waterfall | eligible → admissions → `t_disc` recovered → INCUMBENT_LED → INCUMBENT_LED_UNKNOWN → IDENTIFIED_EXACT / IDENTIFIED_INTERVAL / CASH / CENSORED / UNKNOWN → entitlement excluded → AVOIDED → REFUSED → entered → panel-censored → matured → false starts, per arm |
| Dispositions are by rule | never a judgment made after reading outcomes. |
| Dependence diagnostic (descriptive) | per look: the per-session cluster bound beside the block bound, the number of distinct discovery sessions and of full blocks, and the implied design effect; reported, never a gate beyond the §2 floors. |

### Cases that must be exercised before any disposition (brief §Cases that can disprove a superficial repair)

| Case | What it must show |
| --- | --- |
| CRI (identity) | a security with no confirmed membership symbol on a covered session is UNKNOWN, never a minted identity or "never admitted"; a renamed security is found under its confirmed symbol (the join is security-first) |
| RCL / CSCO (which row set `t_cur`) | the look record names the first-arrival row (`stamp_date`, symbol, `lane`, arrival commit SHA, arrival instant ET, knowable session) that set `t_cur`, shows that HEAD's healed row was not used, and shows a healed session (09-14, 10-19 in R) as a GAP |
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
list; the census v5 re-run (both walks) attached; the T3 availability gate result; and a machine freeze
mirroring §2–§7.

## Frozen-field block (to be mirrored into the machine freeze at freeze time)

```yaml
schema: us.prophet_entry_timing_w2_design/v5
status: DRAFT_UNFROZEN
adjudications: [W2-ADJ-01 policy contrast is the primary (P only), W2-ADJ-02 timing co-condition on exact pairs only, W2-ADJ-03 both arms timed by first-parent arrival, W2-ADJ-04 one heal rule (healed session = GAP), W2-ADJ-05 block bootstrap + session floors, W2-ADJ-06 margin differential only + T0 lower bound >= 0 + timing point estimate >= 0]
parents: [B4 PREREG.json (quoted constants only), W3_RACE_PREREG.md (session_missing class only), ENTRY_TIMING_W1 r3 (d03acfd0)]
generation_id: peg:23be3409c3a57944dd08e09e38e3b7541926c0f244e9d0d3b4a0b4a8aacedbf9
session_calendar: data/yahoo/SPY.parquet date index (NYSE sessions); all units in sessions
lane_state_basis: first blob carrying each stamp_date on first-parent origin/main fixes its BUY rows, curated coverage and signal_asof; a later blob changing that date's BUY set = HEAL -> session is a GAP; healed rows never read; HEAD never read
coverage: session COVERED iff its first-arrival stamp has >= 1 curated-tier row AND the session is not healed; else GAP
identity_join: security-first; EVERY membership symbol recorded for the security confirmed by VendorAliasTable.resolve("membership", symbol, on=session) == security_id, on every covered window session for every unit (uniform span); none confirmed -> UNKNOWN; P looks pin the alias blob current on first-parent origin/main at the look (sha256 in the look record; a unit is never re-resolved under a later blob); R census snapshot sha256 ff8a32df8e47d88149d8ac8d8ae54b9b117a3c44cd34cfcd57eebcf0de816306 (disclosed look-ahead on labels)
decision_window_K_sessions: 10
pre_window_sessions: 10
incumbent_led: BUY row on a covered pre-window session -> excluded
incumbent_led_unknown: pre-window contains a GAP or a covered session with no confirmed symbol -> excluded from P primary and co-condition; R descriptive sensitivity
admission_inside_K: BUY row on a covered window session whose knowable session k(c_cur) <= t_disc + K
t1_status: [IDENTIFIED_EXACT, IDENTIFIED_INTERVAL (descriptive; bounds = first gap session in window .. observed stamp), CASH (no gap, no admission inside K), CENSORED (gap, no admission inside K), UNKNOWN (identity on any covered window session; signal_asof > stamp_date on the row that would set t_cur; anchor when recorded_at > T0 fill instant)]
primary_units: fully covered window + pre-window; IDENTIFIED_EXACT or CASH; not INCUMBENT_LED(_UNKNOWN); not UNKNOWN; not entitlement-excluded
floors: {primary_units: 300, primary_distinct_t_disc_sessions: 110, co_condition_pairs: 100, co_condition_distinct_t_disc_sessions: 44, blocks_of_22_sessions_min: 5}
co_condition_pairs: primary units with IDENTIFIED_EXACT
primary_estimand: D_policy = outcome(T0) - outcome(T1), ITT, T1 = cash (0, no cost) when not admitted inside K; P only; decomposition printed
co_condition: D_timing and executable lead L = t_exec(T1) - t_exec(T0) on co-condition pairs; guard, never a promotion basis; binds on point estimate >= 0 and lower bound >= -25
knowable_session: first NYSE session whose 16:00 ET close > first-parent ARRIVAL instant on origin/main + 30 min; applied to the discovery document (c_disc) and the BUY stamp (c_cur, one instant per stamp_date)
anchor_knowability: payload used only if recorded_at <= T0 fill instant; else UNKNOWN (anchor); R 1087/1087 satisfy
fill: close of the session after the knowable session (engine/us_prophet_grades.py next-close basis)
price_panel: {path: data/yahoo/<TICKER>.parquet, column: close, benchmark: data/yahoo/SPY.parquet, commit: pinned per look record}
arms: {T0: k(c_disc)+1, T1: k(c_cur)+1 or cash, T2: k(c_disc)+1+2, T2m: UNIDENTIFIED (k_star 0 coincides with T0; a k_star of 2 would coincide with T2), T3: union early-turn if availability gate >= 90% (panel INDEX through t_disc - 1, no close read before freeze)}
k_fixed_sessions: 2
k_star_sessions_exact_basis: 0
horizon_sessions: 10
exit: time_exit_at_h10_close
cost_floor_bps_round_trip: 50
estimator: {method: circular_moving_block_bootstrap, unit: per-session t_disc cohort over the look's NYSE calendar (empty cohorts kept), block_length_sessions: 22, statistic: unit-weighted mean, resamples: 4000, rng: numpy Generator(PCG64(20261031)), shared_index_set: every endpoint + bound + tolerance of the look, bound: one-sided 95% percentile, diagnostic_only: per-session cluster bound}
promote: {segment: P only, policy_lower_bound_bps: -25, t0_outcome_lower_bound_bps: 0, timing_point_estimate_bps_min: 0, timing_lower_bound_bps: -25, min_median_executable_lead_sessions: 1, tolerances: hold, fragile: blocks, floors: all §2 floors}
reject: {segment: P only, rule: policy_upper_one_sided_95_bound < -25 bps at the fixed look with floor met}
futility_w2: {at_primary_units: 150, rule: policy_upper_one_sided_95_bound < -25 bps, disposition: REJECT_FUTILITY (terminal; B4 rule quoted, not borrowed)}
looks_P: {monitoring: [50, 100], futility: 150, fixed: first session on which every §2 floor holds; pair-floor deadline 6 months after the primary floors are met -> UNIDENTIFIED-terminal}
look_R: {t_disc_from: 2026-08-26, t_disc_to: 2026-10-23, looks: 1, after_freeze: true, may_promote: false, may_reject: false, changes_P_constants: false, maturity_session: set at freeze = first session after max over R units and arms of t_exec + H (observed, not assumed)}
secondary_family_holm: [D_policy(T2 - T1), D_policy(T3 - T1) if gate passes]
descriptive: [decomposition terms, interval units both bounds, T1b buyable==True, incumbent_led(_unknown) negative lead, R 26 exact pairs with pre-gap flag, placebo T0 at t_disc - 5, mdv20_usd terciles, anchor era, lead terciles, t_vis, t_auth]
avoided_window: [t_disc, t_exec - 1] for every arm
false_start: close < anchor within hold before any close >= fill + ATR14 ; ATR14 = mean |dclose| over 14 sessions strictly before t_disc
tolerance: {false_start_rate_delta_pp_max: 10 (co-condition pairs; binds at the fixed look), false_start_loss_differential_mean_bps_min: -50 (mean of loss_T0 - loss_T1 over primary units, loss_arm = min(outcome,0)*1[arm false start], 0 for cash; binds at the fixed look; never a REJECT trigger)}
bounds: [cost_x1, cost_x2, drop_top_5pct_abs_D (trimmed once on the full-sample ranking, before resampling)]; shared index set; any flip -> FRAGILE -> blocks PROMOTE
critical_values: {assumed_sd_policy_bps: 500, assumed_sd_timing_bps: 400, assumed_design_effect_policy: 2.25, assumed_design_effect_timing: 1.5, policy_n300_se_bps: 43, policy_n300_critical_mean_bps: 46, policy_n300_80pct_power_bps: 83, timing_n100_se_bps: 49, timing_n100_critical_mean_bps: 56, timing_n100_80pct_power_bps: 97, pass_rate_at_true_zero_n300: 0.14, pass_rate_at_true_zero_n300_if_independent: 0.22}
generation_recorded_at: reported per unit as an instant against the T0 fill (R 1087/1087 at or before); not the T0 clock
falsifiers: {descriptive: [placebo at t_disc - 5, D_timing by lead tercile], binding_via_promote: decomposition sign pattern (timing point estimate < 0 blocks PROMOTE)}
dependence_diagnostic: [per-session cluster bound, distinct t_disc sessions, full blocks, implied design effect]
implementation_invariant: numerators invariant to refused-unit count (not a falsifier of H_W2)
dispositions: [PROMOTE (P only), RETAIN_IN_SHADOW, REJECT (P only), REJECT_FUTILITY (P only, terminal), UNIDENTIFIED, FRAGILE, FAILED_TOLERANCE]
authority: measurement only; no trade/sizing/alert; never amends #7751 A1; B4 t_auth descriptive only
```
