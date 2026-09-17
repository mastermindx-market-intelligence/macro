# SPY 0DTE Credit-Spread Prereg Amendment 4 — finite A0/A1 selection + validation gate

**Date:** 2026-09-17
**Status:** FROZEN PRE-OUTCOME AMENDMENT — **NO TRADE / SCORE / SIZING AUTHORITY**
**Parent prereg:** `research/SPY_0DTE_CREDIT_SPREAD_FORENSIC_PREREG_2026-09-16.md`
**Prior amendments:** sample split / forensic quarantine; source-present zero-bid exits; causal A1 stock-bar/VWAP semantics.
**Research branch before this amendment:** `ba8595c228befce840dac1d0ed727b6e948768d8`

## 1. Why this amendment exists

The parent prereg intentionally left several finite development/validation choices to be frozen after source coverage but before broad economic outcomes: exact candidate ranking inside the $0.08–$0.15 band, the executable A0/A1 direction grid, structural-breach confirmation, primary package synchrony/cost sensitivity, and the validation selection rule. Leaving those choices implicit would create avoidable researcher degrees of freedom once P&L is visible.

This amendment freezes the first falsification wave. It deliberately favors a transparent deterministic A1 over a learned optimizer. No development, validation or final-holdout A0/A1 strategy P&L has been opened while writing it.

## 2. Economic unit and executable-cost law

All research results are one $2-wide spread and are normalized by pre-fee defined risk:

`defined_risk = (2.00 - entry_credit) * 100`

`net_R = net_PnL / defined_risk`

Calendar-session series include `0` on abstain/no-trade sessions; trade-only results are reported separately. This prevents an abstention-heavy policy from appearing superior merely by dropping hard days.

Primary execution remains side-correct OPRA NBBO under Amendments 1–2 and the replay helper. Freeze these additional choices:

- primary two-leg quote synchrony fence: **1.0 second** maximum leg age;
- 0.1s is the strict synchrony sensitivity; 5s/10s are source-availability diagnostics only and cannot rescue a primary 1s failure;
- economic candidate discovery uses the **full same-day-expiration chain** at tick resolution over `[decision−1s, decision+1s]`, with no strike-range truncation. Pre-decision rows only seed the current NBBO; they cannot create an entry timestamp before the decision. The exact decision state is evaluated first, then each subsequent tick state through +1s;
- every source quote row updates current leg state, including zero/non-firm/crossed states that invalidate a previously executable side. Equal-timestamp leg updates are applied together before package evaluation; a filtered older firm quote may never survive a newer invalidating NBBO row;
- for each $2 vertical, the entry is its **first** package state in that window satisfying the 1s leg-synchrony fence and the frozen `$0.08–$0.15` credit band. If none occurs by +1s, that vertical is not an eligible candidate. Five-minute boundary snapshots remain coverage diagnostics only and never define the economic candidate universe;
- 15:55 time close uses the latest synchronized executable package at or before 15:55 whose package observation is no more than **5 seconds** old; otherwise that close is unknown/null;
- source-present zero-bid long exits retain Amendment 2's short-only / zero-liquidation-credit accounting;
- primary fee assumption when no audited account schedule is available: **$0.65 per contract-side**, charged on all four entry/exit contract-sides = $2.60 round trip per spread;
- fee sensitivity: $0.50 / $0.65 / $0.80 / $1.00 per contract-side;
- adverse package-slippage sensitivities reduce entry credit and increase exit debit by **$0.01 each** (S1, $2/spread round trip) and **$0.02 each** (S2, $4/spread round trip). Primary selection uses S0 executable NBBO; S1/S2 never choose a configuration.

If a directly audited fee schedule is recovered **before** broad economic unblinding, it may replace the $0.65 primary assumption by a source-law amendment. It may not be changed after outcomes are visible.

## 3. Frozen A0 candidate selection

At each frozen clock and family, enumerate only executable same-day $2 verticals in the frozen $0.08–$0.15 entry-credit band. Let `S` be the last completed consolidated SPY one-minute close before the decision.

For bull puts, `OTM distance = S - short_strike`; for bear calls, `OTM distance = short_strike - S`. A0 rejects non-positive OTM distance, uses no gamma, IV envelope or event filter, and selects the candidate with:

1. greatest positive OTM distance;
2. then higher executable entry credit;
3. then deterministic short-strike order.

A0 remains family-specific. The validation grid may choose a bull-put or bear-call baseline, but family-level results must always be shown before any combined headline.

## 4. Frozen deterministic A1 candidate + direction law

A1 uses the causal price/IV/event state from Amendment 3 but grants decision authority only to the minimum transparent subset needed for the first falsification wave. The parent's earlier “maximize conservative expected value” phrase did not define a validated estimator; this amendment therefore freezes a deterministic containment ranking and **holds any learned/estimated-EV ranking without authority** until a separately preregistered estimator earns it.

### 4.1 Containment filter and candidate rank

A bull-put short strike must be at or below the frozen 1-sigma expected-move lower envelope. A bear-call short strike must be at or above the upper envelope. Missing ATM IV / expected-move state => abstain.

For an eligible bull put:

`containment_margin_sigma = (expected_move_lower - short_strike) / expected_move_1sigma_abs`

For an eligible bear call:

`containment_margin_sigma = (short_strike - expected_move_upper) / expected_move_1sigma_abs`

Require margin >= 0 and choose, within the permitted family:

1. greatest containment margin;
2. then greatest raw OTM distance;
3. then higher executable entry credit;
4. then deterministic short-strike order.

### 4.2 Executable direction modes

Only two direction modes have trade authority in the first A0/A1 wave:

- `contrarian_gap`: negative gap permits bull put; positive gap permits bear call; exact flat/no-gap or missing gap => abstain.
- `price_confirmed`: same gap-to-family mapping, but also require Amendment 3's `reversal_from_gap_extreme_flag == 1`; otherwise abstain.

The parent's `dual_candidate` / positive-lower-bound-EV mode remains **preregistered but HELD_NO_AUTHORITY**. No validated EV/probability estimator exists yet, and inventing one now would enlarge the first-wave search space. Both family candidates may be reported diagnostically, but dual mode cannot originate a selected A1 trade or enter validation ranking. Activating it requires a separate pre-holdout amendment and new validation evidence.

### 4.3 Event law

A1 abstains on any frozen FOMC decision day because the known 14:00 event occurs after all three entry clocks and before the 15:55 close boundary. CPI/PPI/NFP fixture releases occur at 08:30 ET, before entry; those sessions remain eligible but their flags must be reported as event slices. A0 remains unconditional and applies no event exclusion.

VWAP slope, range expansion and other causal A1 fields remain mandatory outputs/calibration slices but do not gain hidden threshold authority in this deterministic first wave.

## 5. Frozen TP / risk mechanics

Primary take profit is the preregistered **$0.02 executable package debit**. The 70%/80%/90% capture variants are robustness reports only and cannot select the configuration.

Risk rules remain R0–R4. Structural breach is now exact:

- bull put: first completed 1-minute consolidated SPY bar whose close is **strictly below** the short strike;
- bear call: first completed 1-minute consolidated SPY bar whose close is **strictly above** the short strike;
- zero price tolerance; one completed bar is the confirmation;
- the stop becomes knowable at that bar's end and stays armed until the first subsequent 1-second-synchrony executable package; no stale/backward quote fills it;
- a TP completed before the structural trigger wins; at an identical timestamp the conservative stop takes priority;
- R4 uses the earliest knowable R1 or structural trigger, with the same conservative tie rule.

Therefore structural-stop source coverage requires consolidated one-minute bars from the decision bar through **15:54**; the 15:55 bar itself is future relative to the exact time-close boundary.

## 6. Finite development/validation grid

No credit-band, clock, TP threshold, event threshold, containment-sigma threshold or feature threshold is tuned after outcomes appear.

Selection grid:

- A0: 3 clocks × 2 families × 5 risk rules = **30** configurations.
- A1: 3 clocks × 2 executable direction modes × 5 risk rules = **30** configurations.
- Total primary validation search = **60** fixed configurations.

The held dual mode, TP robustness variants, fee sensitivities, slippage sensitivities, 0.1/5/10s synchrony diagnostics, gamma and exact GEX walls are **not** members of the selection grid.

Development may be used to repair implementation/source defects and inspect failure clusters after all coverage receipts are frozen. It may not add a new configuration after development P&L is visible.

## 7. Validation ranking and gamma-admission gate

Use the full 250-session frozen validation period only after development implementation is fixed. Primary score is mean **calendar-session** `net_R` under S0 / $0.65 fees. **Validation is a finite model/rule-selection surface, not a confirmatory significance surface.** Bootstrap lower bounds below are robustness/selection statistics and must not be reported as familywise-corrected proof after choosing the best of 60 configurations.

For every configuration, compute a deterministic moving-block bootstrap over whole calendar sessions:

- block length: **5 sessions**;
- bootstrap replicates: **10,000**;
- RNG seed: **20260917**;
- sampler: circular moving blocks. For each replicate choose each block start uniformly from the `N` session indices using Python `random.Random(seed).random()`, wrap blocks across the series end, concatenate until `N` observations are filled, then truncate the last block to exactly `N`;
- primary selection statistic: non-interpolated empirical 5th-percentile order statistic (rank `ceil(0.05 * B)`, 1-indexed) of bootstrap mean calendar-session `net_R`; paired A1−A0 inference uses the same procedure on the aligned daily difference series.

A configuration is validation-eligible only if it has at least **100 active trades in development** and **50 active trades in validation**. Missing-source sessions are not abstentions; they are source failures and make the affected configuration non-evaluable until the prereg's coverage law resolves them.

Validation research risk budget (the same numeric tail/slippage budget later applies as a final-holdout pass/fail gate; validation only decides which frozen configuration reaches that future test):

- mean calendar-session net_R > 0;
- 95% expected shortfall >= **-0.50 R**, where ES95 is the arithmetic mean of the worst `ceil(0.05 * N)` calendar-session `net_R` observations;
- worst single-session result >= **-1.05 R** (structural max loss plus cost tolerance);
- S1 adverse-slippage mean calendar-session net_R > 0;
- when total validation net P&L is positive, no single calendar quarter may contribute > **50%** of that total.

Choose A0 as the eligible A0 configuration with the highest bootstrap lower bound. Choose A1 the same way among eligible A1 configurations. Exact score ties use lexicographic configuration ID; no discretionary tie-break.

A1 earns the **gamma-research admission gate** only if its validation lower bound is > 0 **and** the 5-session paired bootstrap lower bound of calendar-session `(A1 net_R - selected A0 net_R)` is > 0, in addition to the risk budget above. Otherwise record `A1_NO_INCREMENTAL_VALUE`; do not rescue it with gamma, dual-EV modeling, another credit band or a new stop invented from the observed losses.

## 8. Multiple-testing law

The 60 development/validation configurations are **not** individually tested on the final holdout. Their multiplicity is paid by selection behind a sealed confirmatory sample: only the fully frozen selected A0/A1 configurations, plus any later A2/A3 configurations frozen by a separate pre-holdout amendment, may enter the one-shot holdout.

Before that holdout is opened, the complete primary confirmatory hypothesis family must be enumerated. Apply **Holm–Bonferroni at familywise alpha 0.05** across that fixed primary family in addition to reporting the parent prereg's block-bootstrap confidence intervals and economic risk gates. Sensitivity grids (fees, S1/S2 slippage, alternate TP capture, 0.1/5/10s synchrony diagnostics) are robustness reports, not extra chances to rescue a failed primary hypothesis.

No validation bootstrap statistic may be described as a post-selection 95% confidence guarantee. No new primary hypothesis may be added after holdout unblinding.

## 9. Final holdout remains sealed after A0/A1 validation

Passing validation does **not** immediately open the 260-session final holdout. If A1 earns gamma-research admission, A2/A3 may be developed/frozen using development+validation evidence under a separate pre-holdout amendment. Only after every intended arm and familywise test set is frozen may the final holdout be opened once.

This prevents sequentially looking at A1 holdout results and then designing gamma to repair them. If A1 fails the validation gate, the final holdout remains sealed and the correct result is a failed baseline / unresolved thesis, not a tuned rescue.

## 10. Remaining pre-outcome source gates

Economic unblinding remains blocked until durable coverage receipts establish:

1. A0/A1 entry package availability at 09:35 / 09:45 / 10:00;
2. causal opening OHLCV/VWAP completeness;
3. full structural-stop underlying path completeness through 15:54;
4. repaired PIT ATM-IV availability;
5. frozen scheduled-event coverage;
6. close-path normal / zero-bid-carry / unknown states plus exact-tick synchrony evidence sufficient for the primary 1s rule.

Coverage inspection may reveal missingness and source defects only. It may not calculate strategy returns, TP/stop outcomes or labels.
