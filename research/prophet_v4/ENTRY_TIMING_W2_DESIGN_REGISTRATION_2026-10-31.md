# Entry Timing W2 — design registration: does entering at first persisted discovery beat following the BUY lane? (2026-10-31, revision 8)

**Status: FROZEN 2026-10-31.** Independent non-author review PASS on revision 8 at `51ea53823b8e`
(round 8, Opus reviewer, read-only); the three prescribed nits at `90c54a11784097` were confirmed by the
same reviewer as the only change. The frozen-field block below is mirrored into the machine freeze
`research/prophet_v4/entry_timing_w2/PREREG.json` (built by `research/prophet_v4/entry_timing_w2_freeze.py`
from dates, ids and panel DATE indexes only), which also records the freeze inputs: the pinned census
(walk `a7eef2ce9737`, inputs digested), the per-unit population file
`research/prophet_v4/entry_timing_w2_units_2026-10-31.json` (1,087 R units: 26 exact / 44 interval /
918 censored / 98 incumbent-led / 1 unknown), the Data OS entitlement exclusion list (none exists —
pinned EMPTY under the owner role; a later list applies from its own pin), the T3 availability gate
(26 of 26 exact pairs hold the 120-session 3-day-bucket lookback through `t_disc − 1`: **T3 is in the P
Holm family**, descriptive at R), and the R maturity session (**2026-11-19** = first session after the
latest admissible T3 fill `t_disc + K + 1` plus H; observed T0/T1/T2 alone would give 2026-11-10). Freeze
commit SHA: FREEZE_COMMIT_SHA_PENDING (written by the commit that follows the freeze record; the
`sha256_at_freeze` in the record is this file's digest at that freeze commit, before this line changed).
No outcome, price, grade or paired-race surface has been read for the population it names. Authority:
measurement design only. No trade, sizing, alert or capability authority follows from any result of this study.

**Revision history.** r1 → REVISE (the "first curated-tier stamp" incumbent was a universe). r2 →
REVISE (ITT primary with T1 = cash judged a selection contrast; coverage gaps inside the window).
r3 → REVISE (P1 interval-censored units had no defined incumbent entry; P2 the placebo at
`t_disc − 5` does not control the selection channel; P3 the discovery-side knowable session was
unmeasured; N1–N14). r4 → REVISE (P1 the session-cluster bootstrap ignored dependence between
overlapping holds and the floors counted units, not periods; P2 the lane-state rule differed between
code and prose and its "59 BUY rows / 07-31 heal" evidence was an artifact of an unwalked July
parquet; N1–N14). r5 → REVISE (B1 the futility and monitoring looks carried no session floor; B2 a
22-session block is shorter than the dependence it must absorb, the floors must count full blocks, and
a percentile bound alone is anti-conservative with few blocks; M1 the "arrival" instant was the pushing
bot's commit clock; M2 a late-knowable BUY row ended the window scan; M3 exact units with a gap after
admission entered the strict set; M4 the anchor gates were applied to T1, which the lane never uses;
M5 the `origin/main` walk was unpinned; m1–m5; n1). r6 → REVISE (B1 the YAML avoided window still
said "every arm"; M1 the t(B − 1) bound ignored the lag-1 autocorrelation of adjacent block means; M2
the walk SHA was read after the walk, not pinned for it; m1–m7; n1–n2). r7 → REVISE (no blocker;
N1 the +1-clock readouts existed for R only, so P had no bound on unwitnessed arrival clocks; N2 the
census could not be re-run at the pinned SHA; N3–N8 text, constant, rationale and test nits). r8
(this revision) keeps ADJ-01..10 and changes no hypothesis, endpoint, floor, tolerance or critical value. Each is stated with its reason so a reviewer can attack the ruling and not only the
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
  bootstrap over the session calendar (block = 22 sessions in r5; 44 since ADJ-07), and the floors count distinct discovery
  sessions and blocks, not only units. Reason: a session-cluster bound is anti-conservative under
  that dependence (round-4 P1 shows a design effect of ≈ 2.25 at R's density), and a PROMOTE must
  not be reachable through an inference artifact.
- **W2-ADJ-06 — the −25 bps margin is retained as a differential only; T0 must also not lose.**
  B4's margin is a paired comparison against C0; here T1 is cash on every non-admitted unit, so
  the policy contrast is mostly T0 against cash. PROMOTE therefore also requires the lower bound of
  T0's own mean net excess over primary units to be ≥ 0, and the timing guard binds on its point
  estimate. Reason: a buy-everything policy that loses to SPY net of cost must not promote because
  the lane held cash more often (round-4 N1/N2).
- **W2-ADJ-07 — the block is 44 sessions, the floors count full blocks, and the more conservative of
  two bounds decides.** Block length ℓ = 44 = 2 × (K + H + 2): twice the longest span over which two
  units' holds can overlap, so a block boundary splits far fewer dependent pairs than ℓ = 22 did. Two
  one-sided 95% bounds are computed at every deciding look — the circular moving block bootstrap
  percentile bound and a Student-t bound with B − 1 degrees of freedom on the mean of the B full
  non-overlapping block means — and the more conservative decides. The fixed look needs ≥ 5 full
  blocks (220 calendar sessions) and futility ≥ 3 full blocks; the monitoring looks print point
  estimates only. Reason: once units within a block are correlated, the information in a block
  saturates at σ²ρ however many units it holds, so **the sample size is the number of blocks**; a
  bootstrap over ≤ 3 effective blocks understates the tail, and t(B − 1) is the honest small-sample
  statement. The time cost (≈ 10–11 months of P before the fixed look) is accepted over an
  inference artifact (round-5 B1/B2).
- **W2-ADJ-08 — the arrival clock is the commit clock corrected by a server witness.** The
  first-parent `%cI` instant on `origin/main` is the pushing bot's clock, not GitHub's receipt. Census
  v7 corrects every first-arrival commit to max(commit instant, earliest check-suite `createdAt`
  on branch `main` for that commit — a server-side witness created on push; suites on other branches
  are ignored, round-6 m5): a witness exists for 31 of 44 stamp
  commits and 23 of 54 document commits, every witness lies within 2 minutes after the commit
  clock, and no knowable session changes. Commits without a witness keep the commit clock and are
  listed. The R readout **and every deciding P look record** (futility, fixed) are also reported
  with `c_disc` shifted +1 session alone, `c_cur` +1 alone and both +1 — descriptive on P, never a
  substitute for the registered clock (m5; round-7 N1). Reason: a bot clock could run early (a push
  rejected by GH001 and retried later carries the earlier commit clock, and witness coverage falls
  from late September on); the witness bounds the error where it exists and the uniform +1 readout
  bounds it where it does not, on both looks (round-5 M1).
- **W2-ADJ-09 — T1 is the lane as practised and never reads the anchor.** The BUY lane's admission
  gates live in `engine/us_candidate_lanes.py` `_classify_buy_row`; the lane does not know the
  discovery anchor, so AVOIDED and REFUSED apply to T0, T2 and T3 (challenger rules that declare the
  anchor as their invalidation) and never to T1, which enters at `k(c_cur) + 1` whenever the lane
  admitted inside K. The anchor is a measurement yardstick for T1's false-start flag only (so §6 (i)
  compares both arms against one number), never a gate. Reason: gating T1 on the anchor would
  contrast the challenger with a lane that was never run; ADJ-01's implementable policy must be
  contrasted with the implemented one (round-5 M4). H_W2, §5 and §6 (iii) are restated.
- **W2-ADJ-10 — the t bound's standard error is inflated for block-mean autocorrelation.** Holds
  straddle a block edge, so adjacent full-block means are positively correlated (under the overlap
  model of ADJ-05 the lag-1 autocorrelation is ≈ 0.10–0.17 at R's density). The t(B − 1) bound of
  ADJ-07 therefore uses SE = (SD of block means / √B) × √((1 + 2r(B − 1)/B) / (1 − 2r/B)) with
  r = max(observed lag-1 autocorrelation of the adjacent block means, 0.17) — ≈ 1.17× at B = 5 —
  and the look record reports the observed r, the r used and the factor. The block bootstrap is
  left uncorrected: independently drawn blocks omit the same edge covariance, so it carries the same
  downward bias, and the conservative-of-two rule makes the inflated t bound the honest floor
  (round-7 N5). Implemented in `research/prophet_v4/entry_timing_w2_estimator.py` (`se_inflation`,
  `full_block_t_bounds`) with tests. Reason: round-6 M1 — with the naive SE the t bound was
  anti-conservative by 8–17% at B = 5, and the "conservative of two" rule only helps if each bound is
  honest on its own.

Every count quoted here comes from `research/prophet_v4/entry_timing_w2_t1_census.py` v7 run on the
freeze basis (committed output `research/prophet_v4/entry_timing_w2_t1_census_2026-10-31.json`;
dates, tickers, lane/tier flags, `signal_asof`, `recorded_at` and arrival instants only — no price,
grade, outcome or paired-race column; the SPY parquet is opened for its date index only). The
census is re-run and attached at freeze. v7 resolves `origin/main` **once at start-up** and passes that
SHA (`a7eef2ce9737`) to every git read of both walks, recording it in each walk's output and in the
freeze basis (the ref moved between two same-day runs, which is why the pin is a frozen field —
round-5 M5, round-6 M2); reports skipped stamp blobs (0), skipped document blobs (0; round-6 m7) and
stamp dates split across monthly files (0) (m5); corrects arrival instants by the server witness
restricted to check suites on `main` (`--server-arrival`, ADJ-08; 31/44 and 23/54 commits carry one,
0 carry a suite on another branch); counts late-knowable BUY rows **once per unit** (21 units, 23
rows; round-6 m4); and exports the knowable-shift distributions for all 54 stamp dates, all 54
receipts and all 1,087 R units (round-5 m4).

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
following the BUY lane as practised (which never applies the discovery anchor — ADJ-09), net of the
cost floor, is not itself a losing policy against SPY net of
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
| Lane state basis (ADJ-04) | The stamp of a session is the **first blob carrying that `stamp_date` on first-parent `origin/main`** (walked at a pinned SHA recorded in the census and in every look record — v7 `a7eef2ce9737`, resolved once at start-up; a heal landing after a look's pinned SHA is descriptive only and never re-states a unit; round-5 M5); its BUY rows, curated coverage and `signal_asof` are read from that blob only, and its knowable session is that blob's arrival. A later blob that changes the session's BUY set is a HEAL: the session is a GAP for coverage and lane state alike, and the healed rows are never read. HEAD is never read (census: 154 BUY rows exist only in the 09-14 and 10-19 heals; both sessions are GAPs). |
| Producer-health coverage | A session is COVERED when its first-arrival stamp carries ≥ 1 curated-tier row (the BUY lane is classified inside the curated tier) and the session is not healed. Every other session is a GAP. In R, 24 of 42 sessions are covered; the 18 gaps are 09-01, 09-02, 09-14, 09-15, 09-18, 09-28, 09-29, 10-07, 10-09, 10-12, 10-13, 10-15, 10-16 and 10-19 → 10-23. A covered zero-BUY session is a legitimate non-admission. |
| Decision window | `[t_disc, t_disc + K]`, K = 10 sessions (frozen). Pre-window `[t_disc − K, t_disc)`. |
| Identity join | Security-first: for each session **every** membership symbol recorded for the security is confirmed by `VendorAliasTable.resolve("membership", symbol, on=session) == security_id`, and the stamp row is looked up by (session, symbol) for each confirmed symbol (a multi-symbol security loses no row; 3 such securities exist, none among R's exact pairs). The test is applied on every covered window session for every unit — the span does not depend on whether or when the lane admitted (round-4 N7). A security with no confirmed symbol on any covered window session is UNKNOWN (identity), never "never admitted" (brief: CRI). Disclosed limit: records carry no validity window, so the per-session confirmation is currently the same answer on every session; it becomes a real clock when windows exist. Snapshot rule: in P each look resolves identity from the alias blob current on first-parent `origin/main` at the look and pins its sha256 in the look record; a unit resolved at one look is never re-resolved under a later blob, so a later delisting cannot become a future-driven exclusion. R's census used the current snapshot (`ff8a32df8e47…`, latest ingest 2026-10-19), a disclosed look-ahead on labels only. |
| INCUMBENT_LED | A BUY row for the security on a covered pre-window session (census: 98). Excluded from both contrasts; counted. |
| INCUMBENT_LED_UNKNOWN | No BUY row found but the pre-window contains a GAP or a covered pre-window session on which the security has no confirmed symbol, so a prior holding could be hidden (census: 989 of the 989 remaining R units, all by gap, 0 by identity). Excluded from the primary and the co-condition in P; in R, where it is universal, the exact pairs are reported with the flag as a descriptive sensitivity. |
| T1 status per unit | A BUY row is an **admission inside K** only if its session is covered and its knowable session `k(c_cur)` ≤ `t_disc + K` (a row stamped on the last window session arrives one session late and is not inside K: 21 R units, treated as no admission). IDENTIFIED_EXACT: first admission inside K with no gap at or before it (26). IDENTIFIED_INTERVAL: first admission inside K with ≥ 1 gap before it (44): the true admission lies in `[first gap session in the window, observed stamp]`; descriptive only, both bounds printed. CASH: no admission inside K and no gap in the window (0 in R). CENSORED: no admission inside K and ≥ 1 gap (918). UNKNOWN: the security has no confirmed symbol on some covered window session (0) or the row that would set `t_cur` has `signal_asof > stamp_date` in its first-arrival blob (1). |
| Refused units | IDENTITY_UNRESOLVED and MISSING_STRUCTURAL_ANCHOR suppressions whose `source_receipt` is a turn_watch document (W1 r3 basis), excluding `ACTIVE_EPISODE_DIFFERENT_ANCHOR`. Reported in the waterfall; not in the eligible denominator of either contrast. |
| Primary units (P) | admissions with a fully covered window and pre-window, status IDENTIFIED_EXACT or CASH, not INCUMBENT_LED(_UNKNOWN), not UNKNOWN, not entitlement-excluded. |
| Co-condition pairs (P) | the primary units with status IDENTIFIED_EXACT. |
| Segment R (retrospective) | Admissions with `t_disc` 2026-08-26 → 2026-10-23 (all 1,087). Coverage makes the primary **empty** (0 CASH) and the strict co-condition set **empty** (every exact pair has a pre-window gap, and 26 of 26 also have a gap inside the window after admission — census v7, round-5 M3); R yields one descriptive readout — the 26 exact pairs with the pre-gap flag, each interval unit on both bounds — **after** freeze, and it can change no P constant (ADJ-01; review N8). R can neither promote nor reject. |
| Segment P (prospective) | Admissions with `t_disc` after the freeze date (identity by the look's pinned alias blob, lane state by first-arrival blobs under ADJ-04). Each P look uses the generation current at the look, pinned by its `peg:` id; admissions are keyed by `episode_id` and never re-read under a later generation. P requires the nightly producer to commit every session (PR #10255); a P session whose first-commit stamp lacks curated rows is a GAP under the same rule, and a unit with a gap anywhere in its window or pre-window is CENSORED / INCUMBENT_LED_UNKNOWN exactly as in R. |
| Entitlement | The Data OS owner's exclusion list is applied before any outcome read; pinned at freeze as `security_id`s; every exclusion counted. |
| Floors (ADJ-05, ADJ-07) | Primary: ≥ 300 units. Co-condition: ≥ 100 exact pairs. Calendar: the look's discovery calendar holds ≥ **5 full non-overlapping blocks of 44 sessions** (≥ 220 NYSE sessions from the first P discovery session), each full block containing ≥ 1 primary unit and ≥ 1 co-condition pair. A look with fewer on any count is UNIDENTIFIED. At R's density (≈ 26 units per covered session) the unit and pair counts are met long before the block floor, so the fixed look falls ≈ 10–11 months into P; the time cost is accepted (ADJ-07). W3's 20-session tripwire is not reused. |

## 3. Decision instants and arms

| Instant | Meaning | Source |
| --- | --- | --- |
| `t_obs` | the bar the anchor was observed on | OPENED `occurred_at`, informational |
| `t_disc` | the discovery document's `data_session` | W1 r3 receipt recovery |
| `c_disc` | the arrival instant of the discovery document's first blob on first-parent `origin/main`: commit clock corrected by the server witness (ADJ-08) | census v7 document walk (54/54 resolved; witness for 23, none changes the session) |
| `t_cur` | the first covered session ≥ `t_disc` whose first-arrival stamp has `lane == "buy"` for a confirmed symbol of the security and whose arrival is knowable ≤ `t_disc + K` | census, §2 join and ADJ-04 |
| `c_cur` | the arrival instant of the first blob carrying `t_cur`'s stamp date (one instant per session; every row of that stamp shares it), commit clock corrected by the server witness (ADJ-08) | census v7 commit walk (witness for 31 of 44 stamp commits; none changes the session) |
| `t_vis`, `t_auth` | first public-board visibility; a B4 capture instant | NULL in R; descriptive only |
| `t_exec` | the fill session of an arm | §5 |

**Arms.** Each arm is a rule for `t_exec` given only information committed at or before that session.

| Arm | entry session | Role |
| --- | --- | --- |
| T0 | `k(c_disc) + 1` | challenger: enter at first persisted discovery |
| T1 | `k(c_cur) + 1`, or cash when no admission inside K | incumbent: the BUY lane as practised |
| T2 | `k(c_disc) + 1 + 2` | fixed short wait, k = 2 sessions |
| T2m | `k(c_disc) + 1 + k*` | median-wait mimic; k* = median executable lead over R's 26 exact pairs (gap-tolerant, since the strict set is empty; the median stamp lag is also 0 and both are reported — round-5 m2) = **0**, which coincides with T0, so **T2m is UNIDENTIFIED and not in the family** (a k* of 2 would coincide with T2 and be excluded likewise) |
| T3 | union early-turn signal (`engine/us_early_turn.py` `union_admission(price_history, asof)`, completed 3-session buckets, closes only) | in the family only if, for ≥ 90% of R exact pairs, the panel **index** holds every session the signal's lookback needs through `t_disc − 1` with no `session_missing` (an availability check on dates only; no close value is read before freeze — round-4 N9); the family is fixed at freeze: if the gate passes, T3 is a member of the P Holm family; at the R look it is descriptive only (round-5 m3) |

`k(·)` is the knowable session of §5. **Lead** `L = t_exec(T1) − t_exec(T0)` in sessions (executable, both arms
through their arrivals). Census v7 on the freeze basis: 1,087 admissions → 98 INCUMBENT_LED →
989 with a pre-window gap → 26 IDENTIFIED_EXACT (22 / 3 / 1 by discovery month), 44
IDENTIFIED_INTERVAL (observed-stamp lag median 6, earliest-possible median 4), 918 CENSORED (21 of
them — 23 rows — had a BUY row inside the window whose arrival was knowable only after `t_disc + K` —
stamp lag 9 for 4 rows, 10 for 19; the window scan continues past such a row, round-5 M2),
0 CASH, 1 UNKNOWN (`signal_asof`), 0 UNKNOWN (identity); every exact admission and every exact pair's
discovery document became knowable exactly 1 session after its date (26/26 each); over all 1,087 R
units the discovery document became knowable 1 session after its data session for 1,076 and 2 sessions
after for 11 (flagged LATE_DISCOVERY_ARRIVAL; the timing readout is also reported without them);
executable lead on the 26 exact pairs:
0 for 15, 1 for 3, 2 for 2, 3 for 6 (median 0, IQR 0–2); 0 primary units and 0 strict pairs (all 26 exact pairs
also carry a gap after admission — round-5 M3), so R spans 0 distinct primary discovery sessions and
0 full blocks. The r4 figures (65 interval, 873 censored, 25
UNKNOWN) read HEAD for `signal_asof` and walked August onward only; they are superseded.

**Why the BUY lane is the incumbent.** The lane is the surface the product tells a user to act on;
`_classify_buy_row` admits a row only after the buy gates. The curated tier (median 2,932 rows per
stamp) is a universe; the BUY lane (median 61) is an admission (both medians are HEAD-basis descriptive counts, healed rows
included; no rule reads them — round-5 n1). `buyable == True` is a declared
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
| Estimator (frozen, ADJ-05, ADJ-07) | Two one-sided 95% bounds are computed and the **more conservative decides** (the lower of two lower bounds; the higher of two upper bounds): (a) the percentile bound of a **circular moving block bootstrap** over the NYSE session calendar of the look — units grouped into per-session cohorts by `t_disc` (covered zero-unit sessions are empty cohorts and stay in the calendar), block length **ℓ = 44 consecutive sessions** (2 × (K + H + 2), twice the longest span over which two units' holds can overlap), blocks starting at uniformly drawn sessions and wrapping circularly, ⌈N/ℓ⌉ blocks with the last cut back so exactly the N calendar sessions are drawn, statistic = the **unit-weighted mean** over the units in the drawn blocks; 4,000 resamples, NumPy `Generator(PCG64(20261031))`, **one index set shared by every endpoint, bound and tolerance** of the look; (b) a Student-t bound with **B − 1 degrees of freedom** on the mean of the **B full non-overlapping block means** (blocks of 44 sessions aligned from the first session of the look's calendar; the trailing partial block is in (a) and not in (b); a block's mean is the unit-weighted mean of its units; **SE = (SD of block means / √B) × √((1 + 2r(B − 1)/B)/(1 − 2r/B))** with r = max(observed lag-1 autocorrelation of adjacent block means, 0.17) — ADJ-10, ≈ 1.17× at B = 5; B ≥ 5 at the fixed look, so t₀.₉₅(B − 1) ≤ 2.132). Both bounds are computed by `research/prophet_v4/entry_timing_w2_estimator.py` (`deciding_bounds`). The look record names which bound decided and reports the observed and used r. A per-session cluster bound is reported beside both as a diagnostic only. |
| PROMOTE (P only, fixed look) | deciding lower one-sided 95% bound (ADJ-07) of mean `D_policy` ≥ −25 bps (B4's non-inferiority margin, quoted, used as a differential only) AND the deciding lower bound of mean `outcome(T0)` over primary units ≥ 0 (ADJ-06: T0 is not a losing policy against SPY net of cost) AND point estimate of mean `D_timing` ≥ 0 AND the deciding lower bound of mean `D_timing` ≥ −25 bps AND median `L` ≥ 1 AND §6 tolerances hold AND no FRAGILE flag AND the §2 floors (units, pairs, full blocks) are met. |
| Secondary family (Holm, α = 0.05, fixed at freeze) | `D_policy(T2 − T1)`; `D_policy(T3 − T1)` if T3's availability gate passes at freeze (P only; T3 is descriptive at R). T2m is out (§3). |
| Descriptive, non-promoting | the decomposition terms; interval units on both bounds; T1b; INCUMBENT_LED(_UNKNOWN) units scored (negative lead); R's 26 exact pairs; the placebo of §7; subgroups by `mdv20_usd` tercile at `t_disc`, anchor era, lead tercile; `t_vis`/`t_auth`. |
| MAE | H10 maximum adverse excursion per arm, diagnostic only (B4's primary; not re-tested). |
| Critical values and power (judgment, not population estimates; restated on block means — ADJ-07, ADJ-10) | The planning unit is the full block of 44 sessions, because the information in a block saturates: for m units of SD σ sharing an intra-block correlation ρ, the block mean's variance is σ²(1 + (m − 1)ρ)/m → σ²ρ as m grows, so at R's density (≈ 1,100 units per block) the block mean of `D_policy` has SD ≈ σ√ρ ≈ **100–112 bps** (σ = 500 bps, ρ = 0.04–0.05, the correlation round-4 P1 used; a larger ρ raises every figure). With B = 5 full blocks the naive SE of the mean of block means is ≈ 45–50 bps and the ADJ-10 factor (1.17 at r = 0.17) makes it ≈ **52–59 bps**; t₀.₉₅(4) = 2.132, so the t lower bound clears −25 bps only if mean `D_policy` ≥ ≈ **+86 to +100 bps** (80% power at ≈ **+136 to +155 bps**); a rule with true `D_policy` = 0 passes the t margin test ≈ **10–11%** of the time (noncentral t with the SE estimated from 4 df, not the central-t 9% quoted in r6 — round-6 m2; the deciding rule takes the lower of two bounds, so this is an upper limit on its pass-at-zero rate). The r5 figures (SE ≈ 43, critical ≈ +46, pass-at-zero 14%) assumed that unit count still bought information inside a block and are withdrawn; the r6 figures (SE 50, critical +82, power +125, pass-at-zero 9%) omitted ADJ-10 and the noncentrality and are superseded. Timing on co-condition pairs does **not** reach saturation: at ≈ 20 pairs per block (100 pairs over 5 blocks) the block mean of `D_timing` has SD ≈ √(σ²(1 + 19ρ)/20) ≈ **119–125 bps** (σ = 400), SE ≈ 62–65 bps after the factor and the lower-bound condition needs mean `D_timing` ≥ ≈ **+107 to +114 bps**; the point-estimate ≥ 0 condition is weaker than that and does not bind first (r6's "SE ≈ 40, critical +60, point estimate binds first" used the saturation limit that 20 pairs cannot reach — round-6 m3). PROMOTE says "not worse than the lane and not losing", never "better". These are planning numbers; the bound that decides is §Estimator's. In R both tests are impossible (no units, no full blocks). |

## 5. Execution model and point-in-time rules

| Rule | Definition (frozen) |
| --- | --- |
| Knowable session `k(c)` | For an artifact whose first blob **arrived on first-parent `origin/main`** at instant `c` — the commit clock corrected by the server witness where one exists (ADJ-08; ET; a side-branch committer time is never used), the first NYSE session whose 16:00 ET close is strictly after `c + 30 min`. Applied identically to the discovery document (`c_disc`) and the BUY stamp (`c_cur`). Census v7: both are 1 session after their date for every R exact pair (26/26 and 26/26); over all 54 receipts the shift is 1 session for 37 and 2–11 for 17 (documents of the 2026-08-21 and 09-04 data sessions that reached `origin/main` days later; inside R only 11 units carry a 2-session shift), and over all 54 stamp dates it is 1 for 32, 2 for 12 and 3–16 for 10. Every unit is timed by its own receipt's and stamp's arrival, never by a modal shift. |
| Anchor knowability | The generation's `recorded_at` is not the T0 clock (the document is the persisted discovery), but the anchor and identity come from the OPENED payload, so a challenger arm's anchor gates (AVOIDED, REFUSED — T0, T2, T3 only, ADJ-09) and every arm's false-start flag use the payload only if `recorded_at` ≤ the T0 fill instant (16:00 ET of `t_exec(T0)`); otherwise the unit is UNKNOWN (anchor) and leaves the primary, counted. Census v7: 1,087 of 1,087 R units satisfy it (`recorded_at_le_t0_fill`). |
| Fill | `t_exec = k(c) + 1`: the close of the session after the knowable session. An intraday commit can never fill at the same session's close. |
| Invalidation anchor | OPENED `payload.structural_anchor.price` (`turn_watch_reset_low`, adjusted-close basis), the same number for every arm. |
| AVOIDED (T0, T2, T3 — never T1, ADJ-09) | if any session close in `[t_disc, t_exec − 1]` is below the anchor, the challenger arm does not enter; cash 0; recorded AVOIDED. T1 enters whenever the lane admitted inside K; its only gates are `_classify_buy_row`'s. |
| REFUSED (T0, T2, T3 — never T1, ADJ-09) | if the fill-session close is below the anchor, no fill; cash 0; counted. |
| False start | an entered arm whose close falls below the anchor within the hold **before** any close ≥ fill + ATR14, ATR14 = mean absolute close-to-close change over the 14 sessions strictly before `t_disc`, the same number for every arm. Flags the unit; the time exit stands. |
| Panel censoring | a hold crossing a session the panel lacks (W3's `session_missing` class) is CENSORED for that arm; counted. |
| Bounds | each endpoint at cost ×1 (primary), cost ×2, and with the top 5% of |D| units excluded — the trim is taken **once** on the full-sample ranking before resampling, and all three bounds reuse the one shared index set. A flip of PROMOTE/REJECT under any bound is FRAGILE, and **FRAGILE blocks PROMOTE**. |

## 6. Tolerable additional false-positive cost (declared now)

| Tolerance | Value | Binding |
| --- | --- | --- |
| (i) false-start rate | on co-condition pairs (both arms enter) **excluding ENTERED_BELOW_ANCHOR pairs** — a pair whose T1 fill close is already below the anchor is flagged `ENTERED_BELOW_ANCHOR`, counted in the waterfall and kept in every other endpoint, but left out of this rate's denominator for both arms, because the false-start rule would flag such a T1 mechanically (round-6 m6; the excluded pairs are ones on which T1 is a false start by construction and T0 is usually one too — T1's below-anchor fill falls inside T0's hold for 1 ≤ L ≤ 10, and with L = 0 T0 is REFUSED and the pair is not in this rate at all — so each excluded pair contributes fs₀ − 1 ≤ 0 to the difference and removing them raises T0's measured excess toward the +10 pp limit: conservative against PROMOTE, round-7 N6) — T0's false-start rate may exceed T1's by at most **10 percentage points** absolute | blocks PROMOTE at the fixed look; descriptive before it (at 100 pairs the resolvable difference is ≈ 15 pp) |
| (ii) false-start loss, differential | over primary units, `mean(loss_T0 − loss_T1)` ≥ **−50 bps**, where `loss_arm = min(outcome(arm), 0) · 1[arm false start]` (0 for a cash arm) — T0's **additional** false-start money may not exceed one cost floor per unit. Calibration: at the (i) limit of 10 pp more false starts with a mean false-start loss of 300 bps the differential is ≈ −30 bps, inside the tolerance; it binds when T0's extra false starts are both more frequent and deeper than that (≈ 500 bps at 10 pp). The r4 version was one-sided in T0's rate and would have bound on any false-start level. | blocks PROMOTE at the fixed look; never a REJECT trigger |
| (iii) missed upside | T0's missed upside is a unit where T0 is AVOIDED or REFUSED (anchor broken before its fill) and T1 later enters and gains: it enters `D_policy` as a negative term (T0 cash 0, T1 positive). The lane's missed upside (T1 cash on a name T0 bought and that rallied) enters as a positive term. T1 is never AVOIDED or REFUSED (ADJ-09), so the lane's only missed upside is cash. Both are priced inside `D_policy`; no separate tolerance. | — |

## 7. Looks, multiplicity, dispositions, falsifiers and what cannot happen

| Element | Definition (frozen) |
| --- | --- |
| R look | exactly one, after freeze and after maturity: the first session after `max over R units of t_exec(arm) + H` across the arms in the family (the exact session is written at freeze from the census; under the observed knowable shift of 1 it is 2026-10-23 + 22 sessions, but the rule is the maximum observed `t_exec`, not the assumed shift); descriptive only, reported also with `c_disc` shifted +1 session alone, `c_cur` +1 alone, both +1, and without the LATE_DISCOVERY_ARRIVAL units (ADJ-08, round-6 m5); changes no P constant |
| P looks | monitoring at 50 and 100 primary units (point estimates and the waterfall only — no bound, no promotion, no futility; round-5 B1), futility at the first session with ≥ 150 primary units **and** ≥ 3 full blocks of 44 sessions, fixed verdict at the first session on which **all** §2 floors hold (300 units; 100 pairs; ≥ 5 full blocks, each holding a unit and a pair) (B4's look counts quoted: `monitoring_only_episode_counts [50, 100]`, `fixed_episode_count_per_distinct_cell 300`); if the pair floors are not met within **126 sessions** (≈ 6 calendar months; counted in §2 sessions, round-7 N7) of the first session on which the primary-unit floor and the full-block floor both hold, the fixed look is taken as UNIDENTIFIED-terminal; every deciding P look record also carries the three +1-clock readouts (ADJ-08) |
| Futility (W2's own rule) | at the futility look (≥ 150 primary units and ≥ 3 full blocks), stop if the **deciding** upper one-sided 95% bound of mean `D_policy` (the higher of the block-bootstrap and t(B − 1) upper bounds, ADJ-07) < −25 bps; the disposition is **REJECT (futility)** — terminal for this registration, reported as `REJECT_FUTILITY`, never re-looked. B4's rule is different and is quoted, not borrowed: `"futility": {"episode_count_per_cell": 150, "rule": "stop as REJECTED if every cell's primary lower confidence bound excludes improvement"}` |
| REJECT (P only) | deciding upper one-sided 95% bound (ADJ-07) of mean `D_policy` < −25 bps at the fixed look with the floors met |
| RETAIN_IN_SHADOW | floor met, neither PROMOTE nor REJECT |
| UNIDENTIFIED / FRAGILE / FAILED_TOLERANCE | floor not met or coverage-limited (every R look); a bound flip; a §6 breach |
| Multiplicity | Holm over the §4 secondary family; the primary and its co-condition stand alone |
| Scientific falsifiers (descriptive) | (a) **placebo discovery**: T0 re-run at `t_disc − 5` on the co-condition pairs, same fill, hold and cost, anchor and ATR14 taken at the placebo session; reported beside the real contrast, never a gate (round-3 P2: the placebo window still contains the selected run, so it cannot certify absence of selection); (b) `D_timing` by executable-lead tercile — a cost of waiting predicts no decrease with lead; (c) the decomposition's sign pattern — a policy gain carried entirely by the non-admitted term with a negative timing term is reported as "selection, not timing"; since r5 this pattern also **blocks PROMOTE** through the §4 timing point-estimate condition, so (c) is binding, not only descriptive. |
| Implementation invariant (not a falsifier of H_W2) | every numerator in §4–§6 is computed over primary units or co-condition pairs; adding or removing refused units leaves every numerator identical. |
| Required waterfall | eligible → admissions → `t_disc` recovered → INCUMBENT_LED → INCUMBENT_LED_UNKNOWN → IDENTIFIED_EXACT / IDENTIFIED_INTERVAL / CASH / CENSORED / UNKNOWN → entitlement excluded → AVOIDED → REFUSED → entered → panel-censored → matured → false starts, per arm |
| Dispositions are by rule | never a judgment made after reading outcomes. |
| Dependence diagnostic (descriptive) | per look: both §4 bounds and which decided, the per-session cluster bound beside them, the number of distinct discovery sessions and of full blocks, the SD of the block means, and the implied design effect; reported, never a gate beyond the §2 floors. |

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
list; the census re-run (both walks, `--server-arrival`, `--main-sha a7eef2ce9737` so the walk reproduces `walk_sha_R`; a later SHA may be used only by updating `walk_sha_R` in the same revision, round-7 N2) attached; the T3 availability gate result; and a machine freeze
mirroring §2–§7.

## Frozen-field block (to be mirrored into the machine freeze at freeze time)

```yaml
schema: us.prophet_entry_timing_w2_design/v8
status: DRAFT_UNFROZEN
adjudications: [W2-ADJ-01 policy contrast is the primary (P only), W2-ADJ-02 timing co-condition on exact pairs only, W2-ADJ-03 both arms timed by first-parent arrival, W2-ADJ-04 one heal rule (healed session = GAP), W2-ADJ-05 block bootstrap + session floors, W2-ADJ-06 margin differential only + T0 lower bound >= 0 + timing point estimate >= 0, W2-ADJ-07 block 44 + full-block floors + conservative-of-two-bounds, W2-ADJ-08 commit clock corrected by server witness, W2-ADJ-09 T1 never reads the anchor, W2-ADJ-10 t-bound SE inflated for block-mean autocorrelation]
parents: [B4 PREREG.json (quoted constants only), W3_RACE_PREREG.md (session_missing class only), ENTRY_TIMING_W1 r3 (d03acfd0)]
generation_id: peg:23be3409c3a57944dd08e09e38e3b7541926c0f244e9d0d3b4a0b4a8aacedbf9
session_calendar: data/yahoo/SPY.parquet date index (NYSE sessions); all units in sessions
lane_state_basis: first blob carrying each stamp_date on first-parent origin/main fixes its BUY rows, curated coverage and signal_asof; a later blob changing that date's BUY set = HEAL -> session is a GAP; healed rows never read; HEAD never read; walked at the pinned origin/main SHA below (per look record in P)
walk_sha_R: a7eef2ce9737
walk_sha_rule: "origin/main resolved once at census start-up, or passed as --main-sha (ancestor of origin/main) so the WALK reproduces; working-tree inputs (candidate parquets, generation events, SPY calendar, receipt map) are digested in the census output inputs block and must match for a freeze-basis re-run (round-7 N2, round-8 nits 1-2); the SHA is passed to every git read of both walks and recorded in each walk's output (never the symbolic ref)"
arrival_clock: "first-parent commit instant corrected to max(commit, earliest check-suite createdAt on branch main for that commit; suites on other branches ignored); witness 31/44 stamp commits + 23/54 document commits, 0 on another branch, none changes a session; commits without a witness keep the commit clock and are listed; R readout and every deciding P look record (futility, fixed) also reported with c_disc +1 alone, c_cur +1 alone, both +1 (descriptive; round-7 N1)"
anchor_gates: "AVOIDED and REFUSED apply to T0, T2, T3 only; T1 enters whenever the lane admitted inside K (gates = _classify_buy_row); the anchor is a false-start yardstick for every arm, never a gate for T1"
late_discovery_arrival: "unit whose discovery document became knowable > 1 session after its data session; flagged, kept; timing readout also reported without them (R: 11 of 1,087)"
late_knowable_buy_rows: "BUY rows inside K whose stamp became knowable after t_disc + K are skipped and the window scan continues; counted once per unit (R: 21 units, 23 rows; stamp lag 9 for 4 rows, 10 for 19)"
coverage: session COVERED iff its first-arrival stamp has >= 1 curated-tier row AND the session is not healed; else GAP
identity_join: security-first; EVERY membership symbol recorded for the security confirmed by VendorAliasTable.resolve("membership", symbol, on=session) == security_id, on every covered window session for every unit (uniform span); none confirmed -> UNKNOWN; P looks pin the alias blob current on first-parent origin/main at the look (sha256 in the look record; a unit is never re-resolved under a later blob); R census snapshot sha256 ff8a32df8e47d88149d8ac8d8ae54b9b117a3c44cd34cfcd57eebcf0de816306 (disclosed look-ahead on labels)
decision_window_K_sessions: 10
pre_window_sessions: 10
incumbent_led: BUY row on a covered pre-window session -> excluded
incumbent_led_unknown: pre-window contains a GAP or a covered session with no confirmed symbol -> excluded from P primary and co-condition; R descriptive sensitivity
admission_inside_K: BUY row on a covered window session whose knowable session k(c_cur) <= t_disc + K
t1_status: ["IDENTIFIED_EXACT", "IDENTIFIED_INTERVAL (descriptive; bounds = first gap session in window .. observed stamp)", "CASH (no gap, no admission inside K)", "CENSORED (gap, no admission inside K)", "UNKNOWN (identity on any covered window session; signal_asof > stamp_date on the row that would set t_cur; anchor when recorded_at > T0 fill instant)"]
primary_units: fully covered window + pre-window; IDENTIFIED_EXACT or CASH; not INCUMBENT_LED(_UNKNOWN); not UNKNOWN; not entitlement-excluded
floors: {primary_units: 300, co_condition_pairs: 100, full_blocks_of_44_sessions_min: 5, calendar_sessions_min: 220, each_full_block_has: "primary unit and co-condition pair", futility_full_blocks_min: 3}
co_condition_pairs: primary units with IDENTIFIED_EXACT
primary_estimand: D_policy = outcome(T0) - outcome(T1), ITT, T1 = cash (0, no cost) when not admitted inside K; P only; decomposition printed
co_condition: D_timing and executable lead L = t_exec(T1) - t_exec(T0) on co-condition pairs; guard, never a promotion basis; binds on point estimate >= 0 and lower bound >= -25
knowable_session: first NYSE session whose 16:00 ET close > first-parent ARRIVAL instant on origin/main (commit clock corrected by the server witness) + 30 min; applied to the discovery document (c_disc) and the BUY stamp (c_cur, one instant per stamp_date)
anchor_knowability: payload used only if recorded_at <= T0 fill instant; else UNKNOWN (anchor); R 1087/1087 satisfy
fill: close of the session after the knowable session (engine/us_prophet_grades.py next-close basis)
price_panel: {path: data/yahoo/<TICKER>.parquet, column: close, benchmark: data/yahoo/SPY.parquet, commit: pinned per look record}
arms: {T0: "k(c_disc)+1", T1: "k(c_cur)+1 or cash; never anchor-gated", T2: "k(c_disc)+1+2", T2m: "UNIDENTIFIED (k_star 0 coincides with T0; a k_star of 2 would coincide with T2)", T3: "union early-turn if availability gate >= 90% (panel INDEX through t_disc - 1, no close read before freeze); P Holm family member if the gate passes, descriptive at R"}
k_fixed_sessions: 2
k_star_sessions_exact_basis: 0
k_star_basis: median executable lead over R exact pairs (gap-tolerant, descriptive); median stamp lag also 0
horizon_sessions: 10
exit: time_exit_at_h10_close
cost_floor_bps_round_trip: 50
estimator: {method: "conservative of circular_moving_block_bootstrap percentile bound and student_t bound with B-1 df on full non-overlapping block means", unit: "per-session t_disc cohort over the look's NYSE calendar (empty cohorts kept)", block_length_sessions: 44, block_alignment_for_t: "from the first session of the look's calendar; trailing partial block excluded from the t bound only", statistic: unit-weighted mean, resamples: 4000, rng: "numpy Generator(PCG64(20261031))", shared_index_set: every endpoint + bound + tolerance of the look, bound: "one-sided 95%; lower = min of the two lower bounds, upper = max of the two upper bounds; the look record names which decided", t_bound_se_inflation: "sqrt((1 + 2r(B-1)/B) / (1 - 2r/B)), r = max(observed lag-1 autocorrelation of adjacent full-block means, 0.17); observed r, used r and factor recorded per look (ADJ-10)", implementation: research/prophet_v4/entry_timing_w2_estimator.py, diagnostic_only: per-session cluster bound}
promote: {segment: P only, bound: deciding (ADJ-07), policy_lower_bound_bps: -25, t0_outcome_lower_bound_bps: 0, timing_point_estimate_bps_min: 0, timing_lower_bound_bps: -25, min_median_executable_lead_sessions: 1, tolerances: hold, fragile: blocks, floors: all §2 floors}
reject: {segment: P only, rule: deciding policy_upper_one_sided_95_bound < -25 bps at the fixed look with floors met}
futility_w2: {at_primary_units: 150, at_full_blocks_min: 3, rule: deciding policy_upper_one_sided_95_bound < -25 bps, disposition: "REJECT_FUTILITY (terminal; B4 rule quoted, not borrowed)"}
looks_P: {monitoring: "[50, 100] primary units; point estimates and waterfall only, no bound", futility: "first session with >= 150 primary units and >= 3 full blocks", fixed: "first session on which every §2 floor holds; pair-floor deadline 126 sessions (~6 calendar months) after the primary unit floor and block floor are met -> UNIDENTIFIED-terminal", clock_sensitivities: "every deciding look record also reports c_disc +1, c_cur +1, both +1 (descriptive)"}
look_R: {t_disc_from: 2026-08-26, t_disc_to: 2026-10-23, looks: 1, after_freeze: true, may_promote: false, may_reject: false, changes_P_constants: false, maturity_session: "set at freeze = first session after max over R units and arms of t_exec + H (observed, not assumed)", sensitivities: ["c_disc +1 session alone", "c_cur +1 session alone", "both +1 session", "without LATE_DISCOVERY_ARRIVAL units"]}
secondary_family_holm: [D_policy(T2 - T1), D_policy(T3 - T1) if gate passes]
descriptive: [decomposition terms, interval units both bounds, T1b buyable==True, incumbent_led(_unknown) negative lead, R 26 exact pairs with pre-gap flag, placebo T0 at t_disc - 5, mdv20_usd terciles, anchor era, lead terciles, t_vis, t_auth]
avoided_window: "[t_disc, t_exec - 1] for T0, T2 and T3 only (ADJ-09); T1 is never AVOIDED"
refused: "fill-session close below the anchor -> no fill, cash 0, counted; T0, T2 and T3 only (ADJ-09); T1 is never REFUSED"
t1_entered_below_anchor: "co-condition pair whose T1 fill close < anchor -> class ENTERED_BELOW_ANCHOR; counted in the waterfall, kept in every endpoint except the (i) false-start rate, where the pair leaves the denominator for both arms (conservative against PROMOTE)"
false_start: close < anchor within hold before any close >= fill + ATR14 ; ATR14 = mean |dclose| over 14 sessions strictly before t_disc
tolerance:
  false_start_rate_delta_pp_max: 10
  false_start_rate_population: "co-condition pairs excluding ENTERED_BELOW_ANCHOR; binds at the fixed look"
  false_start_loss_differential_mean_bps_min: -50
  false_start_loss_definition: "mean of loss_T0 - loss_T1 over primary units; loss_arm = min(outcome, 0) * 1[arm false start], 0 for cash; binds at the fixed look; never a REJECT trigger"
bounds: [cost_x1, cost_x2, "drop_top_5pct_abs_D (trimmed once on the full-sample ranking, before resampling)"]
bounds_rule: "shared index set; any flip -> FRAGILE -> blocks PROMOTE"
critical_values: {planning_unit: full block of 44 sessions, assumed_sd_policy_bps: 500, assumed_sd_timing_bps: 400, assumed_intra_block_correlation: 0.04-0.05, block_mean_sd_policy_bps: 100-112, blocks: 5, t_095_df4: 2.132, se_inflation_factor_r017_B5: 1.17, policy_se_bps: 52-59, policy_critical_mean_bps: 86-100, policy_80pct_power_bps: 136-155, pass_rate_at_true_zero: "0.10-0.11 (noncentral t, 4 df; upper limit for the deciding rule)", timing_pairs_per_block: 20, block_mean_sd_timing_bps: 119-125, timing_se_bps: 62-65, timing_critical_mean_bps: 107-114, point_estimate_binds_first: false, r5_and_r6_figures: superseded}
generation_recorded_at: reported per unit as an instant against the T0 fill (R 1087/1087 at or before); not the T0 clock
falsifiers: {descriptive: [placebo at t_disc - 5, D_timing by lead tercile], binding_via_promote: decomposition sign pattern (timing point estimate < 0 blocks PROMOTE)}
dependence_diagnostic: [both bounds and which decided, per-session cluster bound, distinct t_disc sessions, full blocks, SD of block means, implied design effect]
implementation_invariant: numerators invariant to refused-unit count (not a falsifier of H_W2)
dispositions: ["PROMOTE (P only)", RETAIN_IN_SHADOW, "REJECT (P only)", "REJECT_FUTILITY (P only, terminal)", UNIDENTIFIED, FRAGILE, FAILED_TOLERANCE]
authority: "measurement only; no trade/sizing/alert; never amends #7751 A1; B4 t_auth descriptive only"
```
