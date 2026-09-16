# SPY 0DTE Credit-Spread Replay Findings — executable forensic cases

**Date:** 2026-09-16  
**Status:** PARTIAL FORENSIC EVIDENCE — **NO TRADE / SCORE / SIZING AUTHORITY**  
**Parent prereg:** `research/SPY_0DTE_CREDIT_SPREAD_FORENSIC_PREREG_2026-09-16.md`  
**Replay helper:** `scripts/research/spy_0dte_credit_spread_replay.py`

## 1. Why this record exists

These bounded real-path replays test whether publicly disclosed Caleb Gregory / OPG SPY 0DTE spreads can be reconciled against historical executable NBBO rather than midpoint or end-of-day marks. Every inspected case is **development/forensic evidence** and is permanently ineligible for the final untouched holdout.

No raw licensed quote payload is stored in this repository. This record retains only method, derived observations and uncertainties. The existing ThetaData Terminal, option-history quote source and canonical OPRA quote-quality rules are reused; no second market-data store or Terminal was created.

## 2. Source/runtime boundary

A read-only health probe on the already-running ThetaData v3 Terminal returned HTTP 200. No process was started, restarted or reconfigured.

Historical quote source: `/v3/option/history/quote`, tick interval. The replay preserves exact contract identity, source timestamp, bid/ask, displayed side size, exchange and condition. Firm OPRA condition and known-exchange filters match the existing `engine/options_nbbo_cohort.py` source law.

For verticals, package accounting is side-correct:

- entry credit = short-leg bid minus long-leg ask;
- exit debit = short-leg ask minus long-leg bid;
- no midpoint primary result;
- the two independently updating legs must satisfy an explicit package-synchrony fence;
- synchrony is reported on the fixed audit grid `0.1s / 1s / 5s / 10s`; no case may choose a winning fence post hoc.

## 3. Case A — 2026-09-15 SPY 755/753 bull put

Publicly reconstructed record: SPY 0DTE **755/753 bull put**, described as entered close to the open; the public result record says the spread was closed near `$0.02` and reports session P&L of approximately **+$1,067.36**. The frozen prereg decision clock nearest the disclosure is **09:35 ET**.

At the 09:35 boundary, the first qualifying two-leg package forms within milliseconds and implies an executable credit of **$0.13**. That is inside the preregistered `$0.08–$0.15` credit band.

Scanning the later session with executable close accounting finds no synchronized `$0.02`-or-better debit by noon. Under the 1-second package fence the best executable debit progresses from roughly `$0.07` before 13:00, `$0.06` before 14:00, `$0.03` before 15:00, to the first `$0.02` close at approximately **15:54:41 ET**. The target event survives the entire preregistered synchrony grid.

If the trade used **127 vertical spreads**, `$0.13` entry, `$0.02` exit and approximately `$0.65` commission per contract-side:

- gross spread capture = `$1,397.00`;
- modeled commission at `$0.65` on four contract-sides per spread = `$330.20`;
- modeled net = **$1,066.80**;
- residual versus reported **$1,067.36** = **$0.56**;
- exact reconciling fee under 127 spreads = about **$0.6489 per contract-side**.

This is strong evidence for the integer-count / roughly-65-cent cost hypothesis, not an audited broker record.

## 4. Case B — 2026-09-03 SPY 764/762 bull put

Public source locator: OPG Trading Service, `OPG Order Flow - Friday 9/4`. The recap states that the prior session used a SPY **764/762 bull put**, received **$10 net credit per spread**, closed roughly two hours into the trade, earned **$976.04**, and brought the reported running 36-session total to **$24,953.27**.

Historical executable NBBO sharply distinguishes the three preregistered clocks:

- **09:35 ET:** first synchronized package implies exactly **$0.10 credit**;
- 09:45 ET: approximately `$0.05` credit;
- 10:00 ET: approximately `$0.04` credit.

The public `$0.10` entry is therefore consistent with the frozen 09:35 clock and inconsistent with waiting until 09:45 or 10:00 under the same conservative package accounting.

Starting from 09:35, the first executable package debit at or below `$0.02` appears at approximately **11:15:05 ET**, about 1 hour 40 minutes after entry, consistent with the public description of closing about two hours into the trade.

At `$0.10 → $0.02`, gross capture is `$8` per spread. Under approximately `$0.65` per contract-side, **181 spreads** imply:

- gross spread capture = `$1,448.00`;
- modeled commission = `$470.60`;
- modeled net = **$977.40**;
- residual versus reported **$976.04** = **-$1.36**;
- exact reconciling fee under 181 spreads = about **$0.6519 per contract-side**.

The inferred fee independently agrees with Case A to within about three-tenths of one cent per contract-side.

## 5. Case C — 2026-08-24 SPY 759/757 bull put

Public source locator: OPG Trading Service, `OPG Order Flow - Tuesday 8/25`. This is the strongest public execution disclosure found so far: Caleb states the trade was issued at **09:35 AM**, used a SPY **759/757 bull put**, received **$10 per spread**, was closed for **$2**, nearly two hours later, and produced about **$1,500** profit.

### Executable replay

At exactly 09:35:00 the first conservative cross is `$0.09`, but the first synchronized package at the stated **$0.10** credit appears at approximately **09:35:00.264 ET**, only a few hundred milliseconds later. Within the first minute the conservative cross briefly reaches about `$0.11` as well. Thus the public `$0.10` fill is feasible inside the stated 09:35 entry minute without midpoint assumptions.

The first synchronized executable `$0.02` debit appears at approximately **11:43:12.990 ET**, about 2 hours 8 minutes later, and survives even the strict 0.1-second synchrony fence. This closely matches the public timing description.

### Reporting / size fork

The public `$1,500` figure creates two materially different interpretations:

- **Gross-P&L interpretation:** `$1,500 / $8 ≈ 187.5`, so roughly 188 spreads before transaction costs.
- **Net-P&L interpretation under the repeated ~65-cent cost model:** nearest integer count is **278 spreads**. At 278 spreads, exact reconciliation to `$1,500` requires about **$0.6511 per contract-side**.

The second result is remarkable because its implied cost falls almost exactly between Case A (`$0.6489`) and Case B (`$0.6519`). Three independent public outcomes therefore admit integer spread counts whose implied fee is effectively the same ~65-cent value.

However, 278 two-dollar spreads entered for `$0.10` carry approximately `$52,820` of structural maximum loss before fees. That conflicts with a literal reading of the public `$10,000` challenge-account path, whose reported equity would have been far smaller at this point absent additional capital or materially different buying-power treatment.

Therefore **the fee/count arithmetic is strong, while the capital interpretation is unresolved**. The study must not silently conclude that 278 spreads were actually held in the isolated challenge account until the source of the buying-power disagreement is explained.

## 6. Cross-case sizing evidence and falsifiers

The first two cases briefly suggested a roughly fixed `$1.4k` gross-capture target because they produced `$1,397` and `$1,448` of gross captured premium. **Case C falsifies that provisional rule** if its `$1,500` public profit is interpreted consistently with the later net-realized figures: 278 spreads at `$0.10 → $0.02` imply `$2,224` gross capture before fees.

The current evidence therefore rejects or weakens several naive sizing explanations:

- **fixed contract count:** contradicted by candidate counts 127 / 181 / 278;
- **fixed ~$1.4k gross capture:** falsified by Case C under the common-cost interpretation;
- **simple fixed percentage of inferred challenge-account equity:** not supported and creates buying-power contradictions;
- **purely maximize contracts:** inconsistent with the large variation in candidate count and with the trader's stated conservative framing.

The most defensible surviving hypothesis is broader:

> **H-SIZE-2 — daily cashflow target conditioned by setup quality / buying power:** OPG appears to target a daily dollar-income band and vary spread count with the trade's available cents, perceived safety/quality and/or a capital base that is not fully represented by the public challenge-account narrative.

This is directly supported by Caleb's repeated public description of a **$500–$1,000 daily goal** and his separate statement that he typically targets about **$10 credit per spread**. The observed wins commonly land in the several-hundred-to-low-thousand-dollar range. This hypothesis is intentionally wider than a fitted sizing formula and requires more exact-position evidence before becoming deterministic.

### Material disagreement ledger — challenge capital

Public sources say the experiment began by moving `$10,000` into a new account and later describe that account as growing from realized profits. At the same time, the three-case cost reconciliation can imply a spread count whose defined-risk collateral exceeds the equity implied by those same public totals.

At least one assumption is therefore wrong or incomplete. Candidate explanations include:

1. the newsletter's per-day profit is not consistently net of the same contract costs;
2. the `$1,500` Case C figure is rounded/gross while later cent-precise figures are net;
3. additional capital/buying power existed outside the stated challenge sleeve;
4. the inferred count is wrong because the actual package execution improved materially over the conservative quote-cross path;
5. another fee convention applies to one or more legs/orders;
6. public reporting combines accounting conventions that are not broker-statement equivalent.

The research must preserve this disagreement instead of choosing the explanation that makes the strategy look cleanest.

## 7. Additional public process rules now recovered

The archive adds several deterministic behavior constraints that matter for the future A1 baseline:

- **09:35 is a real operational clock**, not merely a convenient backtest clock; Case C explicitly names it and Cases A/B independently fit it.
- Caleb repeatedly states a **$500–$1,000 daily cashflow objective** and around **$10 credit per spread** as a typical target.
- On flat opens he describes waiting for an **extreme move**: a drawdown can set up a bull put; a spike can set up a bear call.
- On gap days he frequently attempts to place the spread beyond the already-extended move, seeking mean reversion, IV contraction and theta decay.
- He explicitly **sat out a FOMC day** because the event removed his perceived edge, and separately delayed trading until after a scheduled Fed speech. This validates scheduled-event abstention as part of the reconstructed process rather than a backtest-only safety patch.
- The documented loss case establishes that strong directional order flow can overwhelm gamma containment; avoiding/reducing those regimes is a primary research target.

These are descriptive recovered rules, not validated alpha.

## 8. What changed

Three exact disclosures now show that:

1. exact public strikes map to real executable 0DTE quotes near the stated entry windows;
2. the stated `$0.10` entries on two cases are feasible essentially at 09:35;
3. the stated `$0.02` exits occur on the historical NBBO path at timings consistent with the public recaps;
4. three independent integer-count reconciliations cluster around an implied **~$0.65 per contract-side** cost convention;
5. simple fixed-contract, fixed-gross-target and fixed-equity-risk sizing rules do not survive all three cases;
6. public capital/account reporting is not yet internally sufficient to identify actual deployed buying power;
7. risk-rule reconstruction remains at least as important as entry-rule reconstruction because the strategy's left tail can dominate many small wins.

None of this establishes durable alpha. These are mechanism-identification results, not strategy validation.

## 9. Exact next experiment

The next critical dependency is no longer “is 09:35 / `$0.10→$0.02` plausible?” — that is now strongly supported. It is to resolve **reporting convention + position size + risk budget** without contaminating the eventual holdout.

Recover additional exact-position evidence, prioritizing a disclosed **losing trade** and at least two more winning sessions with strikes/credit/P&L. For every case:

1. replay executable NBBO under the fixed package-synchrony grid;
2. infer integer counts under both gross-P&L and net-P&L interpretations;
3. compute the implied fee rather than presuming one convention;
4. compute defined-risk collateral and compare it with every available contemporaneous capital statement;
5. reject any interpretation that needs session-specific accounting tricks;
6. preserve contradictions as missing evidence rather than forcing a clean sizing formula.

In parallel, build the broad **A0/A1 coverage manifest only** — dates with eligible 09:35/09:45/10:00 SPY 0DTE quote coverage, underlying path and scheduled-event state — without yet unblinding strategy P&L across the final holdout. Gamma remains held until A0/A1 are cost-correct and the parent prereg's incremental-value gate is reached.
