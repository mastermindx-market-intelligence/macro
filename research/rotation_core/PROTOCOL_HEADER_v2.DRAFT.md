# Rotation Core — protocol header v2 (DRAFT revision 2, NOT FROZEN)

> **Power, stated first.** No test available to us can show a 1–2 pp/yr rotation edge. Minimum detectable effects at 80 % power, Holm m = 3, from 1998–2019 variance only:
>
> | Window | MDE (pp/yr) |
> |---|---|
> | Pre-1998 + 2020–2025 pooled | 2.6 |
> | 2020–2025 alone | 9.2 |
> | Five forward years | 10.1 |
> | Ten forward years | 7.1 |
>
> Detecting 2 pp/yr would take about 127 clean years; 1 pp/yr about 509.
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
- **Sector Intelligence's leave-outs** are kept, with their records.
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
- **(ii)** Narrowness: equal- minus value-weighted industry return over 60 sessions.

## Hypotheses (one Holm family, m = 3)

| Id | Rule | Primary contrast |
|---|---|---|
| **H1** | **ARMED:** the offence/defence relative line is within h % of its 126-session high **and** breadth (i) is ≥ b pp below its own 126-session peak. **DEFEND** (defence leg) when, while armed, the line closes below its 50-session SMA. **ATTACK** (offence leg) when breadth (i) washes out to ≤ 25 % and recovers above 25 % within 20 sessions. Otherwise base. Grid h ∈ {3, 5} %, b ∈ {25, 37.5} pp: 4 settings, chosen after freeze on 1998–2019 only, all counted. | vs the exposure-matched static mix at H1's average weights, **rebuilt inside every bootstrap resample** |
| **H2** | H1 minus the identical rule without the breadth key (price-only control, same h) | paired daily difference |
| **H3** | Run B's R5 on the beta-sorted legs: hold offence if its 126-session return beats defence's, else defence | vs its matched mix, rebuilt per resample |
| *ablation* | H1 with bills in place of the defence leg on identical dates: **mandatory, reported, not tested** | — |

**H1 against R7.** R7 is prior negative evidence against H1's breadth key. H1 differs in three ways:
- it requires a second key, a break of the relative line after arming;
- its legs are beta-sorted and re-formed monthly from data to t−1, not fixed named groups;
- it starts from equal weight.

**Arming check (point G, 1998–2019, signals only, no returns computed).**
- The armed fraction on breadth (i) is 7.6–19.7 % across the grid.
- The price key alone is on 37–50 % of sessions, so breadth removes more than half of the price-key days.
- Not degenerate, so (i) is kept. Stand-in (ii), at 6.9–9.8 %, is recorded and not used.

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
  - 2026 entries are rehearsal only. The first scored formation is the first full month after freeze and readiness.
  - One efficacy read at 5 years. Quarterly checks cover completeness and clocks only; there is no tuning from interim looks.
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
  - **Narrowness:** equal- minus cap-weight member return over 60 sessions.
    - **Fallback, decided before the first scored night and not after:** if the weight field proves unusable, use equal weight within sector minus the sector fund's return.
  - **Two measurements, not one series.** The historical industry stand-in and the forward member breadth are two measurements of the same idea, not one continuing series. The vendor subsector tree is descriptive only.
- **Missing before it can start:**
  - PR #11024 merged;
  - the per-member price-state file landed;
  - the weight source confirmed (otherwise the fallback);
  - a nightly issuer writing QLedger claims from the frozen v2 code;
  - 50 nightly states per member before breadth is defined.

## Trial ledger at freeze

- **`rotation_core_v2`:** 9 (H1 grid 4, H2, H3, cash ablation, tradable version, named mapping).
- **Run B:** 10 consumed, negative.
- **Carried:** v1's 36.

Harness: the corrected v1 engine; t+1 execution; stationary bootstrap block 21 (sensitivity 63), B = 10,000. Nothing here sizes, gates or trades.
