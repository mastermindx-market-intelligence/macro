# SPY 0DTE Credit-Spread Prereg Amendment 2 — source-present zero-bid long exits

**Date:** 2026-09-16
**Status:** FROZEN PRE-OUTCOME AMENDMENT — **NO TRADE / SCORE / SIZING AUTHORITY**
**Parent prereg:** `research/SPY_0DTE_CREDIT_SPREAD_FORENSIC_PREREG_2026-09-16.md`
**Amendment 1:** `research/SPY_0DTE_CREDIT_SPREAD_PREREG_AMENDMENT_1_SAMPLE_SPLIT_2026-09-16.md`
**Research code inspected before amendment:** `003955301d35ecfbbb51cdecbd6e48361f602eb0`
**Protected Sol procedure for this continuation:** `mastermindx-market-intelligence/Mastermind@eee809949ee79c0ea1ef922ce74c110b1bb1dddf`, bootstrap major `1`.

## 1. Why this amendment exists

The first deterministic development-only source canary used the first frozen development session (`2023-01-03`) and first frozen decision clock (`09:35 ET`) before any economic outcome, TP/stop crossing, P&L, or label was calculated. The candidate universe contained one bull put and one bear call.

A source-availability probe then requested ThetaData v3 one-minute OPRA NBBO rows from 09:35 through 15:55 for the exact four candidate legs. Both short legs retained positive firm exit asks through 15:55. The long 377 put retained a positive bid through 15:35 and then reported exact bid `0` for 20 rows; the long 391 call retained a positive bid through 11:11 and then reported exact bid `0` for 284 rows. In both cases the source still returned all **381/381** minute rows through 15:55, with a positive ask on every row.

Therefore these states are not missing historical rows. They are source-present one-sided markets in which the long option has no displayed executable bid. Treating them as generic source absence would misclassify ordinary far-OTM decay as missing history. Treating them as a positive sale price would fabricate execution. This amendment freezes a conservative third state before economic outcomes are opened.

## 2. Frozen rule

Entry logic is unchanged. A new spread still requires the frozen positive executable entry sides: short sold at positive firm bid and long bought at positive firm ask. Zero entry sides remain invalid.

For exits:

1. **Normal package close:** if the short has a positive firm ask and the long has a positive firm bid under the frozen quote-condition, exchange, timestamp and synchrony rules, close using `short ask - long bid` exactly as preregistered.
2. **Source-present zero-bid long:** if the short has a positive firm ask, and the exact long-leg source row has `bid == 0` but a positive firm ask, do **not** claim that the long was sold. Close the risk-bearing short at its executable ask, assign the residual long **zero liquidation credit** in the primary accounting, and mark the event `long_liquidation_zero=true` / short-only close.
3. **Missing or invalid long row:** if the long row is absent, malformed, crossed, stale beyond the frozen synchrony rule, or lacks both a positive firm bid and the exact zero-bid/positive-firm-ask state above, the close quote is **unknown/null**. It is never converted to zero.
4. **Invalid short ask:** a zero/missing/non-firm short ask remains non-executable and null. No zero-price short close is allowed.

The zero-bid long state is a conservative lower-bound convention, not an imputed fill. The residual long receives no positive P&L credit in the primary result. The existing full two-leg exit fee assumption remains charged even when the long is carried at zero accounting value, so this rule cannot improve the primary result through a fee reduction.

## 3. What does not change

This amendment does **not** change the frozen date partitions, decision clocks, $2 width, $0.08–$0.15 entry-credit band, candidate families, event law, IV law, TP/stop families, holdout seal, or gamma ablation order. It grants no signal or sizing authority.

The final holdout remains sealed. This rule was created solely from source-schema/executability evidence before any broad A0/A1 strategy outcome was calculated.

## 4. Remaining source gate

Panel-level close-path availability must now distinguish at least three states by date/candidate/time: normal positive-bid package close, source-present zero-bid long short-only close, and genuinely unknown/non-executable close. A0/A1 economic outcomes remain blocked until that coverage receipt is published and the finite development/validation selection logic is frozen.
