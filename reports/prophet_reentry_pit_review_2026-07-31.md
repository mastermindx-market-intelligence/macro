# Prophet repeat-admission investigation — historical PIT-readiness review

**Reviewed:** 2026-11-12. **Underlying cohort:** as of 2026-07-31.
**Source:** `data/prophet_postmortem/summary.json` at
blob `be2a3bf09566037636492611b81188626dd7bfb1`.
**Authority:** RESEARCH / DISPLAY ONLY. Not a valid trading backtest, new veto,
ranking factor or proof of real-time deployment.

## Core finding

The Observatory's apparent **+86.53 percentage-point** net benefit is a
**HINDSIGHT UPPER BOUND** over seven losing-tail episodes. All eight cases
had an earlier 10-session episode that *eventually* resolved to a loss of
at least 8%, but that outcome was not settled when the ticker reappeared.
The separate buildable rule (earlier position already down at least 8%
at re-entry) fired **zero times** in the 610 matured-episode window.

The source is a hypothetical **buy-board membership** ledger, next-session
close entry and fixed H=10 exit; it is **not a real trade ledger**. Seven
flagged episodes meet the postmortem's loser gate, which includes SPY-relative
underperformance of 5% or worse even when absolute loss is below 8%.
The eighth, SONO (-2.40%), is *neutral* and excluded from the displayed
loser-tail sum. The eight episode returns sum -88.93pp; do not equate either
sum to a realizable portfolio result.

## Source-backed exploratory cohorts

| Cohort | Episodes | Entry dates | Losers | Winners | Neutral | Mean H10 | Equal-weight total pp |
|---|---:|---:|---:|---:|---:|---:|---:|
| Matured population | 610 | 18 | 132 | 91 | 387 | +1.23% | +749.79 |
| Recent repeat admission | 87 | 16 | 19 | 11 | 57 | +0.86% | +74.73 |
| No recent prior recorded | 523 | 18 | 113 | 80 | 330 | +1.29% | +675.06 |
| Prior mark already ≤ -8% | **0** | 0 | 0 | 0 | 0 | — | 0.00 |
| Repeat + sector avoid/trim | 13 | 8 | 4 | **2** | 7 | +0.09% | **+1.16** |
| Repeat + sector shifted from non-headwind to avoid/trim | 6 | 5 | 2 | 0 | 4 | -1.54% | -9.22 |
| Repeat + entry status buy_now | 4 | 2 | 2 | 0 | 2 | -0.04% | -0.16 |
| Prior resolved ≥8% loss: **HINDSIGHT ONLY** | 8 | 7 | 7 | 0 | 1 | -11.12% | -88.93 |

**Semantics:** `loser` and `winner` are *existing source cohorts*; loss
includes a ≤-5% SPY-excess leg, and winner requires ≥+8% absolute.
Neutral returns still matter. Groups overlap, same-night rows are not
independent, and all total pp are unsized arithmetic. This historical
artifact does **not** attest per-definition-era controlled comparisons
or independent out-of-sample forecasting.

A blanket repeat veto is not supported: the observed repeat-minus-other
mean is only **-0.43pp**. A separate exploratory date-cluster bootstrap
(12,000 same-board-date resamples across 18 matured dates, review seed
1711) gave an approximate interval of **[-1.73,+0.90]pp**. Zero is inside;
this was an exploratory check, **not** confirmatory promotion proof.

### A useful adversarial check

For the 13 repeat recommendations already in a sector marked avoid/trim,
four were loser-tail rows, but **two were winners**. By outcome group,
the totals were losers **-41.83pp**, winners **+21.15pp**, neutrals
**+21.84pp**. A blanket hypothetical exclusion would therefore
forfeit about **+1.16pp** from this subset, before transaction costs,
and cannot be justified by the four losses alone.

The six historical rows with a documented transition into sector headwind
are **AEE, CVSA, BJ, FCPT, ODFL, PTON**. Two are loser-tail, four are
neutral, none are winners, but six cases across five dates are not enough
to infer a reliable causal gate. The comparison selects the nearest
*chronological* earlier board episode, never the earlier episode chosen
using its hindsight resolved loss.

## The eight apparent repeat-loss cases

| Name | Entry date | Previous mark at re-entry | New hypothetical H10 outcome | New entry state |
|---|---|---:|---:|---|
| DCH | Jun 18 | -4.54% | -15.91% | buy_soon |
| ADNT | Jun 22 | -4.63% | -9.61% | wait_pullback |
| SONO | Jun 22 | -3.50% | -2.40% | buy_soon |
| HWKN | Jun 24 | +2.05% | -19.18% | hold |
| P | Jul 06 | +0.76% | -5.02% | await_confluence |
| CVSA | Jul 09 | +1.36% | -11.50% | hold |
| IPGP | Jul 15 | +3.04% | -17.86% | await_confluence |
| ODFL | Jul 21 | +1.31% | -7.45% | bounce_wait |

All dates are 2026. Prior marks are stored historical values, **not yet
independently PIT timestamp-audited**. In the artifact, all four July cases
had sector reco `avoid`; June entry-sector state was not comparably
recorded. None of the eight new entries was `buy_now`: this does not
show eight executed violating trades.

## Reproducible study, constraints and next genuine validation

Use `python -m scripts.prophet_readmission_pit_study --format markdown`
for the versioned read-only analysis of the **current file's** as-of
vintage; its default path is the committed `summary.json`. The CLI
reports both outcome tails, neutral exposure and a seeded date-block
exploratory interval. It does not write, fit a model or change selection.

**PIT repair:** `scripts/prophet_postmortem.py` now uses the last close
**on or before** the board decision date, refuses a mark before the
prior position's actual fill and records the observed close date when
the artifact is regenerated. The July 31 JSON does **not** yet carry
that timestamp; do not backfill assumed observations or claim it is
a fresh November measurement.

**Remaining gates, not silently passed:**
1. Refresh/rebuild from the canonical US board/price source without
   changing the frozen July 31 evidence; require actual output as-of
   and exact observed-close timestamps for every prior mark used.
2. Obtain original per-entry board-definition stamps and evaluate only
   truly comparable era partitions; the pooled historical contrast is
   descriptive and may confound admission revisions.
3. Freeze the next candidate feature/rule *before* collecting an
   independent future period: repeat-board membership combined with
   sector deterioration and explicit entry readiness; no hindsight
   outcome predicates. Test preserved winners, neutral return exposure,
   entry-date clustering and real decision clocks.
4. Differentiate board appearance, recommendation ready-to-act and
   actual transactions; the historical H10 dataset measures the first.
5. Run real Observatory consumer/browser verification after protected
   merge and deployment. Until proven, source changes are BUILT_NOT_PROVEN.

**Disposition:** NO LIVE VETO / NO TRADING-AUTHORITY CHANGE. The question
worth pursuing is whether Prophet is surfacing deteriorating setups in
its buy-board membership despite withheld entry readiness—not a
universal ban on re-admitting recently seen tickers.
