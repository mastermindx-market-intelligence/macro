# Rotation Core — protocol header v2 (DRAFT revision 5, NOT FROZEN)

> **Power, stated first.** No test available to us can show a 1–2 pp/yr rotation edge. H1's minimum detectable effects at 80 % power, Holm m = 3, from 1998–2019 variance only, using its actual time in tilt (67–71 % of sessions):
>
> | Window | H1, actual tilt (pp/yr) | Full-tilt proxy: the upper bound of the MDE |
> |---|---|---|
> | Pre-1998 + 2020–2025 pooled | 2.0–2.2 | 2.6 |
> | 2020–2025 alone | 7.2–7.8 | 9.2 |
> | Five forward years | 7.9–8.6 | 10.1 |
> | Ten forward years | 5.6–6.1 | 7.1 |
>
> With the four positive-sign requirements the chance of passing at the MDE is about 63 %. DEFEND fires 2.2–3.3 times a year at every grid point, so the sample is not starved of events; the limit is variance.
>
> The historical tier is a **low-power falsification screen**. 1926–2019 has already been examined for this question by v1 and by Pro run B, including near neighbours of H1 on 1998–2019. **2020–2025 is the only window not yet examined, and it contains about two stress episodes.**

**Basis.** Written on the corrected engine (`0dfec2426e`). No v2 outcome has been computed. The parent freezes; the trial ledger is declared at freeze. Where this Markdown and `protocol_header_v2.DRAFT.json` differ, the JSON governs.

## Question

When conditions turn bad, does tilting from equal weight toward low-beta industries, and back toward high-beta industries, on a two-key signal beat holding the same average mix after costs?

## Prior examination (disclosed, so none of this is called clean)

- **v1:** market timing 1928–1997; sector rules 1998–2019; the Stage D correction moved no conclusion.
- **Pro run B:** ten rules on the French 49 industries, 1926–2019, all negative.
  - Its R7 (breadth divergence) and R8 (washout re-entry) are near neighbours of H1.
  - Its R6 (confluence into defensives) is the near twin of the H3 Sector Intelligence suggested.
  - Counted as 10 consumed trials.
  - **Reproduced locally** on sealed ≤2019 inputs: 3,229 of 3,229 computable cells match, 0 mismatches (`pro_run_B_reproduction/`). The 2,806 cells for the macro rules (R2, R4, R6, R9, R10) need FRED and Shiller inputs that are not on this host, so they are not reproduced and are not cited; only reproduced cells (including R5, R7, R8) may be cited.
  - While inspecting a schema the worker displayed the last three monthly UNRATE values (2026-08 to 10: 4.1, 4.2, 4.1) before truncation. None entered any computation, and UNRATE is not a v2 input; disclosed.
- **`research/DEFENSIVE_ROTATION.md` on Macro main:** a defensive-rotation test on the same funds, headline window 2015-01-01 → 2026-06-18, FALSIFIED / DISPLAY-ONLY. 2020–2025 is untouched by this rule, not by the organisation.
- **2026:** H1 and H2 were shaped by Sector Intelligence's 2026 replay, so 2026 is reported, never scored.
- **What the lead saw of run B:** some of its per-rule era rows (R5–R8), while reading the file to record its trials. No v2 parameter was chosen from them.
- **Kill records cited, not rebuilt:** KILL-DEFENSIVE-FLOOR-BUNDLE, KILL-RS-DISPERSION-GATES, KILL-ROTATION-CYCLE-CONFLUENCE, KILL-HINDENBURG-OMEN, KILL-MCO-THRUST, KILL-FUSED-COMPOSITE.
- **Left out on prior record:** position-in-range as a top signal; fund-flow residual; member-dispersion gates; the index-level breadth thrust.
- **Not proposed (2026 replay only, one hindsight episode), not killed:** relative-strength momentum as a leader read; the turn label.
- **Rates, credit spread and SPY-minus-RSP:** descriptive splits only, never in a trigger.

## Construction (Ken French 49 industries, daily)

**File facts (checked 2026-11-11):**
- The file carries both value- and equal-weighted daily returns, from 1926-07-01.
- Industries with data: 40 in 1926, 43 from 1940, 49 from 1970. Over 1928–1950, 43 have some data and 37 are complete.
- **366 industry-days are missing after the industry became eligible, across 8 industries, up to 2019.** This confirms run B's finding.
- The file is built from the monthly CRSP update, about 4 weeks after month-end. On 2026-11-10 it ran to 2026-09-30.
- **Consequences:**
  - 2026 can be reported on this construction only to 2026-09-30.
  - The rule as tested cannot be run live from this file (see the forward tier).

**Seal.**
- The 2020+ part of every French industry file is sealed by path. Each full file was hashed unopened and locked in `sealed_post2019/`.
- The working copies are truncated at 2019-12-31 using the date field only.
- Nobody on our side has computed anything on French industry data after 2019. The 2020+ data opens once, for the confirmatory run.

**Gap rule (no imputation).**
- An industry enters a leg only after 252 valid daily returns.
- An industry-day with a missing return is dropped from that day's leg average and breadth, and counted.

**Legs.**
- **Formation:** each month-end, each eligible industry's beta to the market is measured over the 252 sessions ending t−1.
- **Offence:** top third by beta. **Defence:** bottom third. That is 16 industries each from 1970, fewer before.
- **Base:** equal weight of all eligible industries.

**Breadth stand-ins.**
- **(i)** Share of offence industries above their own 50-session SMA. Steps are about 6.25 pp, and every grid threshold is a multiple of that step.
- **(ii)** Narrowness: equal- minus value-weighted industry return over 60 sessions. **Descriptive only, in both tiers.**
- **Current-leg rule (R2):** every day, the 126-session breadth history used by the arming key and the washout test is recomputed on the *current* leg's members. Past legs are never stitched together. The relative line stays a chained return series.
- **b is a share (R5)** of the leg's eligible industries: steps of about 6.25 points with 16 members (from 1970), about 7–8 points before 1970.

## Hypotheses (one Holm family, m = 3)

| Id | Rule | Primary contrast |
|---|---|---|
| **H1** | Base: equal weight (NEUTRAL). **ARMED:** relative line within h % of its 126-session high **and** breadth (i) at least b below its 126-session maximum (both on current members). **DEFEND** (defence leg): armed within the last 21 sessions and the relative line closes below its 50-session SMA. **ATTACK** (offence leg): a washout spell starts at the first close with breadth ≤ 25 % and runs while closes stay ≤ 25 %; ATTACK confirms on the first close above 25 % if it is within 20 sessions of the spell's **lowest** close (earliest if tied). Otherwise no ATTACK and the state in force continues. Grid h ∈ {3, 5} %, b ∈ {25, 37.5}: 4 settings, chosen after freeze on 1998–2019 only, all counted. | vs the exposure-matched static mix at H1's average weights, **rebuilt inside every bootstrap resample** |
| **H2** | "Breadth in the arming key adds information": H1 minus the identical rule with breadth removed from ARMED only. The washout breadth is in both arms. | paired daily difference |
| **H3** | Run B's R5 on the beta-sorted legs: hold offence if its 126-session return beats defence's, else defence | vs its matched mix, rebuilt per resample |
| *ablation* | H1 with bills in place of the defence leg on identical dates: **mandatory, reported, not tested** | — |

**Exits are by state, not by the calendar (R1).**
- **DEFEND** ends at an ATTACK confirm (next-close execution), or at the first month-end on which the relative line closes above its own 50-session SMA; then NEUTRAL.
- **ATTACK** ends at a DEFEND trigger, or at the first month-end at least 63 sessions after entry; then NEUTRAL.
- A state is never exited on its entry day. A trigger on a month's last session stands; the month-end test first applies at the following month-end.
- **Same-day DEFEND trigger and ATTACK confirm:** DEFEND wins, and the day is counted.
- **Re-triggering the state already in force** is ignored and does not reset its clock. (Lead's decision; the rulings did not cover it.)

**Fixed settings, not in the grid:** arming memory 21 sessions; ATTACK minimum hold 63 sessions; washout threshold 25 %; recovery within 20 sessions of the spell's lowest close; breadth SMA 50; look-back 126; trigger SMA 50.

**Grid selection.** Highest 1998–2019 excess over the matched mix; exact ties go to the more conservative setting (smaller h, then larger b). H2's price-only control and the cash ablation inherit the selected point; there is no second selection.

**H1 against R7.** R7 is prior negative evidence against H1's breadth key. H1 differs in three ways:
- it requires a second key, a break of the relative line after arming;
- its legs are beta-sorted and re-formed monthly from data to t−1, not fixed named groups;
- it starts from equal weight.

**Signals-only table (1998–2019, rev 5 rules, trough clock, no returns computed; `v2_power/signals_table_D.*`).**

| Book | Armed share (no memory / with 21) | DEFEND entries/yr | ATTACK entries/yr | Share N / D / A | Median, longest spell N / D / A | Same-day conflicts |
|---|---|---|---|---|---|---|
| H1 h3 b25.0 | 11.8% / 33.5% | 2.55 | 2.91 | 32% / 15% / 53% | 22,115 / 12,52 / 63,84 | 0 |
| price_only h3 b25.0 | 37.0% / 52.6% | 3.23 | 2.96 | 26% / 21% / 53% | 16,115 / 13,64 / 61,84 | 0 |
| H1 h3 b37.5 | 7.6% / 26.9% | 2.23 | 2.87 | 33% / 14% / 53% | 28,150 / 13,52 / 64,84 | 0 |
| price_only h3 b37.5 | 37.0% / 52.6% | 3.23 | 2.96 | 26% / 21% / 53% | 16,115 / 13,64 / 61,84 | 0 |
| H1 h5 b25.0 | 19.7% / 47.7% | 3.32 | 3.10 | 30% / 21% / 49% | 21,115 / 12,79 / 39,84 | 0 |
| price_only h5 b25.0 | 49.8% / 65.3% | 4.05 | 3.14 | 26% / 27% / 47% | 17,115 / 13,79 / 31,84 | 0 |
| H1 h5 b37.5 | 13.7% / 40.5% | 3.05 | 3.10 | 31% / 19% / 50% | 23,115 / 12,79 / 39,84 | 0 |
| price_only h5 b37.5 | 49.8% / 65.3% | 4.05 | 3.14 | 26% / 27% / 47% | 17,115 / 13,79 / 31,84 | 0 |

**Washout spells (same for every grid point and arm):** 179 spells; length median 3, longest 59, 22 longer than 20 sessions; sessions from low to recovery median 2, longest 54; **164 fire ATTACK (92%), 15 do not.**

- **The 20-session limit does little work:** ATTACK confirms on nearly every washout spell. Reported, not adjusted.
- The earlier 7.6–19.7 % armed shares were **without** the 21-session memory; with it they are 27–48 % (price-only 53–65 %).
- Every grid point fires both states; DEFEND enters 2.2–3.3 times a year. None is degenerate.
- **ATTACK is held about half of all sessions** (47–53 %), so H1 is mostly an offence tilt with defensive episodes, not mostly equal weight.
- Same-day conflicts: none. The price-only control does not depend on b.
- **Descriptive split:** H1's excess over the matched mix will be reported separately for DEFEND, ATTACK and NEUTRAL days (no extra trial).
- **Revision note:** the washout clock was changed from the spell's first close to its lowest close at draft stage, on Sector Intelligence's clarification of its own proposal, before any return was computed. A counts-only table and a variance-only power line under the first-close clock had already been pushed in revision 4 (`1faa76396b`) before the ruling arrived; that variant is not reported here.

**H3 choice.** Sector Intelligence's trend-and-Sahm with defensives is the near twin of run B's R6, which showed no benefit. R5 is the simplest direct control, and I have no better-motivated candidate.

## Yardsticks (every window)

- SPY (French market before 1993).
- RSP (from 2003; before that, the equal-weight market proxy, stated).
- Equal weight of all industries: the base.
- **The exposure-matched static mix: binding.**

**Per-episode table, descriptive, no extra trial.** For H1 and its price-only control: was ARMED on at the price peak, and how many sessions before or after the peak did the trigger fire?

## Two tiers

**Historical tier.**
- **Selection:** on 1998–2019.
- **Opening:** one opening of 2020–2025, plus pre-1998 (1928–1997).
- **Not scored:** 2026 is reported only (industries to 2026-09-30).
- **Pass:** all of the following.
  - Holm p < 0.05 on the pooled contrast.
  - Point estimate > 0 in pre-1998, in 2020–2025, and in both pre-1998 eras (1928–45 and 1946–97).
  - Drawdown no worse than the matched mix.
  - Holds at 2× costs.
- **Best label:** "survives falsification on history". Never "confirmed", and never a product claim.

**Tradable second confirmation.**
- Both keys are computed on the industry portfolios. Only execution moves to the SPDR sector funds.
- **Fund legs:** three highest and three lowest trailing-252-session-beta funds, data to t−1, re-formed monthly, among funds with at least 252 sessions of history.
- **Workability:** nine funds from 1998-12 make three per leg workable from 1999-12. XLRE (2016-10) and XLC (2019-06) enter by the 252-session rule only, with no special case.
- **Named mapping:** XLK against XLP/XLU/XLV is reported beside it as descriptive only, labelled as carrying hindsight.
- **Veto:** a pass on industries with a negative fund point estimate in 2020–2025 is reported as **"signal not shown to be tradable"**.
- **My view:** this does not weaken the test, because it can only remove passes. With three funds per leg the veto is noisy and will sometimes fire on noise.

**Forward tier (the only tier that can support "called it before it happened").**
- **Rules and record:**
  - Rules and inputs are frozen at freeze, and a dated nightly record starts when the implementation is ready.
  - 2026 entries are rehearsal only. The first scored formation is the later of the first full month after freeze and readiness, and the first month-end with 126 recorded nights of as-written member breadth. The look-back is never reconstructed.
  - Clocks: `decided_at` is the row's own last-price date, never the file name or run time; a row one session behind is recorded as such. Roster and weights come from a holdings snapshot dated on or before the night, carrying the snapshot's own date.
  - One efficacy read at 5 years, counted from the first scored formation. Quarterly checks cover completeness and clocks only; there is no tuning from interim looks.
- **Owner: QLedger.** One claim per decision or state change, recording:
  - family;
  - decided_at and exec_at;
  - state and weights;
  - header sha and commit;
  - matched-mix definition;
  - input vintage timestamps;
  - falsifier.
- **Input contract, in member terms.** Sector Intelligence's nightly per-member file carries, from its first night:
  - S&P 500 membership flag and GICS sector as of that night, with the source named;
  - trailing 60-session total return;
  - price vintage timestamp;
  - index weight from their daily fund-holdings snapshots, held from 2026-06-11 and carrying the snapshot's own date.

  The roster is the vendor subsector members plus that night's S&P 500 members.
  - **Legs:** sector funds, chosen by the trailing-beta rule.
  - **Breadth:** the share of the leg's sectors' S&P 500 members above their own 50-session SMA, on that night's roster.
  - **Narrowness (descriptive only):** equal- minus cap-weight member return over 60 sessions.
    - **Fallback, decided before the first scored night and not after:** if the weight field proves unusable, use equal weight within sector minus the sector fund's return.
  - **Two measurements, not one series.** The historical industry stand-in and the forward member breadth are two measurements of the same idea, not one continuing series. The vendor subsector tree is descriptive only.
- **Missing before it can start:**
  - PR #11024 merged;
  - the per-member price-state file landed;
  - a nightly issuer writing QLedger claims from the frozen v2 code;
  - 126 recorded nights of as-written member breadth before the first scored formation. (Breadth itself exists from the first file: each row carries the member's close relative to its 50- and 200-day averages.)

## What the pass rule does to power (D variance only)

| True edge | P(Holm significant) | P(significant **and** all four sub-windows positive) |
|---|---|---|
| 2.6 pp/yr (the MDE) | 0.80 | **0.63** |
| 2.0 pp/yr | 0.56 | 0.43 |
| 1.0 pp/yr | 0.16 | 0.12 |

The sign requirements cut the pass chance at the MDE from 80 % to about 63 %; the 2020–2025 sign (6 years) costs most of it. The drawdown and 2× cost conditions cut it further. **A fail is not evidence of no effect:** at a true 2 pp/yr edge this test fails more often than it passes.

## Trial ledger at freeze

- **`rotation_core_v2`:** 9 (H1 grid 4, H2, H3, cash ablation, tradable version, named mapping).
- **Run B:** 10 consumed, negative.
- **Carried:** v1's 36.

Harness: the corrected v1 engine; t+1 execution; stationary bootstrap block 21 (sensitivity 63), B = 10,000. Nothing here sizes, gates or trades.
