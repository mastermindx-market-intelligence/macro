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

### Executable replay

At the 09:35 boundary, the first qualifying two-leg package forms within milliseconds and implies an executable credit of **$0.13**. That is inside the preregistered `$0.08–$0.15` credit band.

Scanning the later session with executable close accounting finds **no synchronized $0.02-or-better debit by noon**. The best observed executable debit under the 1-second package fence improves approximately as follows:

- before 13:00 ET: `$0.07`;
- before 14:00 ET: `$0.06`;
- before 15:00 ET: `$0.03`;
- first `$0.02` executable close: approximately **15:54:41 ET**.

The target event survives the entire preregistered `0.1s / 1s / 5s / 10s` synchrony audit grid. This does not prove OPG's actual broker fill time; it proves that the public entry/exit price pair is feasible on the historical NBBO path under conservative leg-side accounting.

### P&L / size triangulation

If the disclosed trade used **127 vertical spreads**, `$0.13` entry credit, `$0.02` exit debit and approximately `$0.65` commission per contract-side:

- gross spread capture = `127 × ($0.13 - $0.02) × 100 = $1,397.00`;
- four contract-sides per round trip imply `$330.20` commission at `$0.65` each;
- modeled net = **$1,066.80**;
- residual versus reported **$1,067.36** = **$0.56**;
- exact fee that reconciles the public P&L under 127 spreads is about **$0.6489 per contract-side**.

This is strong evidence for the 127-spread / roughly-$0.65 fee hypothesis, but it is not an audited broker record.

## 4. Case B — 2026-09-03 SPY 764/762 bull put

Public source locator: OPG Trading Service, `OPG Order Flow - Friday 9/4`. The recap states that the prior session used a SPY **764/762 bull put**, received **$10 net credit per spread**, closed roughly two hours into the trade, earned **$976.04**, and brought the reported running 36-session total to **$24,953.27**.

### Entry-clock identification

Historical executable NBBO sharply distinguishes the three preregistered clocks:

- **09:35 ET:** first synchronized package implies exactly **$0.10 credit**;
- 09:45 ET: approximately `$0.05` credit;
- 10:00 ET: approximately `$0.04` credit.

Therefore the public `$0.10` entry is consistent with the frozen **09:35** clock and inconsistent with waiting until 09:45 or 10:00 under the same conservative package accounting. This independently strengthens 09:35 as the OPG-like entry clock for at least this public case.

### Exit replay

Starting from 09:35, the first executable package debit at or below the preregistered `$0.02` target appears at approximately **11:15:05 ET**, about 1 hour 40 minutes after entry. The target is synchronized well inside the 0.1-second fence. This is consistent with the public description of closing about two hours into the trade; it does not prove the exact broker fill timestamp.

### P&L / size triangulation

At `$0.10 → $0.02`, gross capture is `$8` per spread before fees. Under approximately `$0.65` per contract-side, **181 spreads** imply:

- gross spread capture = `181 × $8 = $1,448.00`;
- modeled commission at `$0.65` × four sides × 181 = `$470.60`;
- modeled net = **$977.40**;
- residual versus reported **$976.04** = **-$1.36**;
- exact fee that reconciles the public P&L under 181 spreads is about **$0.6519 per contract-side**.

The inferred fee independently agrees with Case A's `$0.6489` to within about three-tenths of one cent per contract-side. That repeated agreement makes the common ~$0.65 cost model materially more credible than the one-case result alone.

## 5. Cross-case sizing evidence

The two inferred integer sizes differ substantially — **181** versus **127** spreads — so a fixed-contract rule is already disfavored. More interestingly, the *gross captured P&L before commissions* is nearly constant:

| Case | Inferred spreads | Entry → exit | Gross capture |
|---|---:|---:|---:|
| 2026-09-03 764/762 BP | 181 | `$0.10 → $0.02` | `$1,448` |
| 2026-09-15 755/753 BP | 127 | `$0.13 → $0.02` | `$1,397` |

The gross captures differ by only about **3.6%**, despite a ~43% difference in contract count. This creates a new falsifiable sizing hypothesis:

> **H-SIZE-1 — target-capture sizing:** position count may be chosen approximately as a fixed target gross option-income capture divided by expected per-spread capture, rather than as a fixed number of spreads or a fixed fraction of structural max loss.

A rough target near `$1.4k` gross capture fits both inspected cases. Two cases are not enough to accept it. It must survive at least three additional non-adjacent disclosed sessions before it can be frozen as a candidate sizing rule.

### Fixed-equity-risk hypothesis is not supported yet

For Case A, `$2` width and `$0.13` credit imply `$187` structural maximum loss per spread, or about **$23,749** at 127 spreads. Under the very restrictive assumption that the stated `$10,000` start plus reported cumulative net equals actual account equity with no cash flows, that would be about **60.5%** of inferred pre-session equity.

For Case B, `$0.10` credit implies `$190` structural maximum loss per spread, or **$34,390** at 181 spreads. Applying the same restrictive account-equity assumptions to the reported running total would put structural max loss near or above inferred account equity. That inconsistency materially weakens any attempt to infer a stable account-risk percentage from the public running P&L.

Possible explanations include additional brokerage capital, deposits/withdrawals, buying-power conventions, different sizing economics, reporting differences or an incorrect inferred count. Therefore **no equity-risk sizing rule is accepted**. H-SIZE-1 currently explains the two observed integer sizes more parsimoniously, but remains only a hypothesis.

## 6. What changed

The two cases together materially strengthen the reconstructability thesis:

1. exact disclosed strikes map to real executable 0DTE quotes near the stated entry windows;
2. Case B's stated `$0.10` credit independently pins its entry close to 09:35 rather than 09:45/10:00;
3. executable spread paths reproduce the disclosed `$0.02` target timing plausibly in both cases;
4. two independent P&L reconciliations converge on approximately **$0.65 per contract-side** fees;
5. integer position size appears recoverable from public P&L with very small residuals;
6. size varies inversely with captured cents in a way consistent with a roughly fixed gross-income target;
7. the risk layer remains more uncertain than the entry/fee mechanics and could dominate the strategy's true left-tail behavior.

None of this establishes durable alpha. These are mechanism-identification results, not strategy validation.

## 7. Exact next experiment

Recover at least **three more non-adjacent disclosed OPG sessions** containing date, direction, exact strikes, entry credit/window, exit price/target and reported session P&L. For every case:

1. independently replay executable NBBO under the fixed package-synchrony grid;
2. infer nearest integer spread count across the frozen fee neighborhood centered on the now-repeated ~$0.65 observation;
3. report residual rather than forcing an exact fit;
4. compare competing sizing hypotheses: fixed contracts, fixed gross capture, fixed net target, fixed max-loss dollars, fixed percentage of inferred equity and volatility-scaled risk;
5. reject a hypothesis if it requires case-specific tuning or does not survive the additional sessions.

Only after the sizing/exit mechanics are stable enough to freeze should the broad A0/A1 historical cohort be unblinded. Gamma remains held until A0/A1 are cost-correct and the parent prereg's incremental-value gate is reached.
