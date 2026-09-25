# Frozen two-gate comparison — research, not a live policy

Operation: `theme-entry-two-gate-comparison-20260922-sol-001`, under the existing
Chairman US leadership/Prophet mandate and `WS:PROPHET-US-V4-RECOVERY`.
Carrier: existing macro PR #7669 / `claude/theme-recommendation-reasons-20260921-sol`.
Procedure: protected `Mastermind@9a7ed19091dd82609f8ee405687f16c861c4d8c1`, same-pin
Skillpack 1.0.1/bootstrap 1. Direct execution: PRINCIPAL_JUDGMENT for experimental
identification and acceptance; no worker admission, alternate reviewer identity,
new program, entry engine, publisher or control plane is created.

This document is frozen before computing any historical forward outcomes. Only
input metadata (columns, date ranges, null/duplicate counts) has been inspected.
Input vintage: `macro@1e767a2f5b43f302b0e1068c9a7e60b12aeb98ee`.
Prices end September 18, 2026. They are not today's quotes or a logged-at vintage
replay. The previous single-snapshot finding is a diagnostic lead, not validation.

## Question and existing owners

Do the separate 0.75 clean-entry and 0.85 recommendation relative-strength gates
exclude useful trend participation on a multi-cycle proxy? Does replacing the
extra-admission restriction with a native price-extension bound improve the
tradeoff? Freeze all parameters; do not select or retune a winner after outcomes.

Reuse `scripts/calibrate_baskets.py` for causal relative-price features, panel
breadth, crowding and proxy scoring; `engine.theme_scoring` for the existing
label/recommendation; `engine.basket_score.clean_entry` and `_rsi` for the exact
entry-quality function; `engine.theme_extension._atr_ext` / `STRETCHED` for the
existing per-security close-based extension measure; `lib.nyse_calendar` for
sessions; and `engine.validation` for statistical inference. Record all arms at
generation through the existing `engine.trial_ledger.TrialLedger`, preserving its
canonical prior bytes in this isolated branch. No production threshold changes.

## Five fixed arms, no search

1. `incumbent`: native constructive recommendation AND native clean-entry flag.
2. `entry_veto_only`: retain the existing recommendation. Relax only the .75 veto
   when original native quality is already >= .60 and a copied native call with
   its RS input immediately below .75 passes. Do not award the counterfactual's
   extra .20 quality credit to the original row.
3. `recommendation_veto_only`: keep native clean entry. For a dominant label,
   compare the existing recommendation with a copied call whose RS input is
   immediately below .85. All labels, scores, trend and crowding inputs stay fixed.
4. `both_rs_vetoes`: combine the preceding two ablations, retaining all other
   policy conditions. This is a deliberately unbounded research comparator.
5. `both_with_price_bound`: retain every incumbent selection; admit an additional
   `both_rs_vetoes` selection only when the same security's native close-based ATR
   extension is available and strictly below native `STRETCHED=3`. This is a
   research risk bound, NOT a validated substitute for the production entry rule.

The .85-only arm may be observationally redundant behind the stricter .75 entry
gate. Preserve a zero-delta result instead of manufacturing a different cohort.
Do not change the .75/.85 values, .60 quality floor or extension bound based on
results. No preferred CPU names, optimization grid or retrospective whitelist.

## Universe and decision clock

Use the nine original SPDR sector proxies already declared by the calibration
owner: XLK, XLE, XLF, XLV, XLY, XLP, XLU, XLI, XLB, plus SPY as benchmark. All
native `data/yahoo/<ticker>.parquet` inputs must exist with finite positive closes,
unique ordered session dates and a common last observation. Do not add XLC/XLRE
or individual winners. Keep the complete expected NYSE index; do not forward-fill
missing bars or count a holiday as a session. Report excluded non-session rows
and every missing-data disposition.

Use 504-session warm-up and sample every five expected sessions from that anchor.
Require the trailing 504-session proxy/benchmark window to be complete before
features can qualify. Scalar native functions receive only the decision-time
prefix. Native causal rolling arrays may be computed once for efficiency, with
prefix-invariance tests proving that future prices cannot change earlier features
or arm selections. The native
calibration's cross-sector panel breadth is a PROXY, not historical constituent
breadth. Macro is fixed at neutral zero and MTF/tape legs are omitted consistently:
this is not a full Prophet/backtest of historical published recommendations.

## Outcomes and estimands

A decision at close t cannot earn the t-to-t+1 move. The hypothetical fill is the
next expected session's close, and exits are 5, 21 and 63 sessions after that fill.
Require complete asset/benchmark paths to the endpoint; keep unavailable tail
outcomes null. Charge 10 bps on entry and 10 bps on exit (20 bps round trip),
consistent with the existing rotation cost convention. No slippage precision,
actual execution, account equity or current allocation is implied.

Report per-arm eligible/selected counts, newly selected names versus incumbent,
net absolute and SPY-relative returns, negative-net-outcome rates, and close-path
maximum adverse excursion from the next-close entry (not peak-to-trough drawdown).
Use the native -8% adverse-move reference. Never call a negative return a proven
technical false breakout; it is only an outcome diagnostic.

Primary comparison: 21-session net relative outcome on a fixed per-asset event
budget (each selected proxy gets 1/9, each unselected slot remains zero-return
cash). Pair each arm with incumbent on the SAME fully observed decision dates.
This is a non-compounded event-sleeve score with overlapping windows, NOT portfolio
CAGR, Sharpe, a capital-feasible position ledger or investable performance.
Use native Newey-West inference across chronological date-level differences with
ceil(horizon/5) lags and Benjamini-Hochberg correction across all four noncontrol
21-session comparisons. Publish raw effect sizes and date counts, including zero
and insufficient samples. No performance claim from event-count inflation.

Fixed chronological partitions: development decisions/outcomes strictly before
2018-01-01; assessment decisions from 2018-01-01 onward. Do not let a development
outcome cross the partition; report purged boundary rows. No model is fitted in
either partition. This retrospective partition is not prospective validation.
Report fixed calendar-era summaries and per-security contributions so a single
sector/cycle cannot silently stand for the population.

## Decision consequence and acceptance

An adverse or unstable result rejects broad removal as a proposed automatic
production change. A favorable proxy result only earns further same-decision-time
stock/constituent replay and prospective observation; it does NOT authorize a
live ranking, entry or sizing change. Require valid original/counterfactual tests,
causality/prefix invariance, missing-session and next-close discrimination,
unchanged native recommendations, fixed denominators and clean source custody.
Keep #7650/#7669 release review and production evidence separate. Independent
review remains requested but unconsumed; CI is not approval.
