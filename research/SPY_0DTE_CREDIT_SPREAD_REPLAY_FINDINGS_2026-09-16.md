# SPY 0DTE Credit-Spread Replay Findings — first executable case

**Date:** 2026-09-16  
**Status:** PARTIAL FORENSIC EVIDENCE — **NO TRADE / SCORE / SIZING AUTHORITY**  
**Parent prereg:** `research/SPY_0DTE_CREDIT_SPREAD_FORENSIC_PREREG_2026-09-16.md`  
**Replay helper:** `scripts/research/spy_0dte_credit_spread_replay.py`

## 1. Why this record exists

The first bounded real-path replay tests whether a publicly disclosed Caleb Gregory / OPG SPY 0DTE spread can be reconciled against historical executable NBBO rather than midpoint or end-of-day marks. The case is now **development/forensic evidence** and is permanently ineligible for the final untouched holdout.

No raw licensed quote payload is stored in this repository. This record retains only method, derived observations and uncertainties. The existing ThetaData Terminal, option-history quote source and canonical OPRA quote-quality rules are reused; no second market-data store or Terminal was created.

## 2. Source/runtime boundary

A read-only health probe on the already-running ThetaData v3 Terminal returned HTTP 200. No process was started, restarted or reconfigured.

Historical quote source: `/v3/option/history/quote`, tick interval. The replay preserves exact contract identity, source timestamp, bid/ask, displayed side size, exchange and condition. Firm OPRA condition and known-exchange filters match the existing `engine/options_nbbo_cohort.py` source law.

For verticals, package accounting is side-correct:

- entry credit = short-leg bid minus long-leg ask;
- exit debit = short-leg ask minus long-leg bid;
- no midpoint primary result;
- the two independently updating legs must satisfy an explicit package-synchrony fence;
- synchrony is reported on the fixed audit grid `0.1s / 1s / 5s / 10s`; this case may not choose a winning fence post hoc.

## 3. Disclosed case examined

Publicly reconstructed case: SPY 0DTE **755/753 bull put**, session 2026-09-15, described as entered close to the open; public result record says the spread was closed near `$0.02` and reports session P&L of approximately **+$1,067.36**.

The frozen prereg decision clock nearest the disclosure is **09:35 ET**.

## 4. Executable replay result

At the 09:35 boundary, the first qualifying two-leg package forms within milliseconds and implies an executable credit of **$0.13**. That is inside the preregistered `$0.08–$0.15` credit band.

Scanning the later session with executable close accounting finds **no synchronized $0.02-or-better debit by noon**. The best observed executable debit under the 1-second package fence improves approximately as follows:

- before 13:00 ET: `$0.07`;
- before 14:00 ET: `$0.06`;
- before 15:00 ET: `$0.03`;
- first `$0.02` executable close: approximately **15:54:41 ET**.

The target event is synchronized strongly enough to survive the entire preregistered `0.1s / 1s / 5s / 10s` audit grid. This does not prove OPG's actual broker fill time; it proves that the public entry/exit price pair is feasible on the historical NBBO path under conservative leg-side accounting.

## 5. P&L/size triangulation

If the disclosed trade used:

- 127 vertical spreads;
- `$0.13` entry credit;
- `$0.02` exit debit;
- approximately `$0.65` commission per contract-side;

then:

- gross spread capture = `127 × ($0.13 - $0.02) × 100 = $1,397.00`;
- four contract-sides per round trip imply `$330.20` commission at `$0.65` each;
- modeled net = **$1,066.80**;
- residual versus reported **$1,067.36** = **$0.56**.

Equivalently, if 127 spreads and the `$0.13 → $0.02` price path are exact, the fee required to reconcile the public P&L is about **$0.6489 per contract-side**. The near-match is strong evidence for the **127-spread sizing hypothesis plus roughly $0.65/contract-side economics**, but it is not an audited broker record and must remain a hypothesis until another disclosed trade independently reproduces the same sizing/fee mechanics.

## 6. Hidden risk implication

For a `$2`-wide spread entered for `$0.13`, structural maximum loss before fees is `$187` per spread. At 127 spreads that is approximately **$23,749**.

A conditional account-risk calculation is informative but not established fact. If all of the following are true: the experiment started at `$10,000`, the public cumulative net after this session is `$30,298.39`, no capital entered or left the account, and the reported session P&L is included in that cumulative number, then implied pre-session equity is about `$39,231.03`. The 127-spread structural maximum loss would then be about **60.5% of equity**.

That conditional ratio is too striking to ignore, but one case cannot establish a 60% sizing rule. Deposits, withdrawals, reserved buying power, reporting conventions or a different spread count can invalidate the inference. The next forensic task is therefore to recover multiple disclosed trade/P&L pairs and test whether integer spread count repeatedly maps to a stable fraction of contemporaneous equity or another deterministic risk budget.

## 7. What changed

This case materially strengthens the hypothesis that the public OPG record contains enough information to reconstruct more than qualitative direction:

1. the disclosed strikes are consistent with real executable 0DTE quotes near the stated entry window;
2. executable spread economics can explain the reported P&L to sub-dollar residual under a plausible integer spread count and commission rate;
3. therefore **position sizing may be recoverable from repeated P&L reconciliation**, rather than treated as permanently unknowable;
4. however, the observed tail exposure is potentially very large relative to the stated starting account, making risk-rule reconstruction at least as important as entry-rule reconstruction.

## 8. Exact next experiment

Build a multi-case forensic ledger from disclosed OPG sessions with all of: date, direction, exact strikes, approximate entry window, exit target/price and reported session P&L. For every case, independently replay executable NBBO, infer the nearest integer spread count across a conservative fee grid, and test competing sizing hypotheses (fixed contracts, fixed max-loss dollars, fixed percentage of inferred equity, volatility-scaled risk). Reject any sizing hypothesis that does not survive multiple non-adjacent sessions.

Only after sizing/exit mechanics are stable enough to freeze should the broad A0/A1 historical cohort be unblinded. Gamma remains held until A0/A1 are cost-correct and the parent prereg's incremental-value gate is reached.
