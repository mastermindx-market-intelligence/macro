# Off-exchange liquidity-memory and absorption specification

**Status: SPEC_ONLY.** The useful object is a source-qualified history of executions and subsequent price response. A reported off-exchange execution does not identify a beneficial owner, institutional intent, accumulation, distribution, resting liquidity or an unfilled order.

## 1. Extend the existing context owner

The current owners are engine/darkpool_signals.py, engine/darkpool_context.py, scripts/build_darkpool_desk.py, collectors/finra_short_volume.py and collectors/finra_ats_transparency.py. They already own EOD participation, robust trailing unusualness, price-conditioned context and delayed ATS comparisons. The existing context ledger and Data OS should carry qualified derived memory; an intraday shelf experiment does not justify a second tape, ledger or evaluator. The Massive advanced-integration masterplan is a relevant design owner, but a plan is not proof that its proposed tick plane exists. The impossible-participation quarantine belongs to current Macro #7990. [I16] [I32] [I33] [I34] [I35] [I36] [I37] [IPR7990]

Keep three observations separate:

| Observation | What it establishes | What it does not establish |
|---|---|---|
| Consolidated trade identified as off-exchange | A report with a price, quantity, condition and source clock | Dark-pool origin for every print; beneficial ownership; aggressor without eligible quotes |
| Daily short-sale volume | The covered source's marked short-sale activity | Change in short interest or a directional portfolio position |
| Delayed ATS/non-ATS transparency | Published activity by covered venue/firm/week | Contemporaneous intraday liquidity, direction or inventory |

These boundaries preserve the current audit and Commission 15. Exact public-reporting delays, rights and condition fields are in the data matrix; use the source's actual publication vintage. [I08] [I16] [I35] [I36]

## 2. Required observation grain and clocks

Request an authorized projection through the incumbent consolidated-tape owner: immutable source trade identifier, economic execution time if supplied, reporting/receive time, observed time, correction/cancel link, price, shares, sale conditions, tape/market and reporting facility. Preserve whether execution time was supplied or inferred. A late print at a historical execution price is not new liquidity at the receipt-time price.

Join only the immediately preceding eligible quote in the relevant causal clock domain. Carry quote age, quote condition and best bid/ask venue/size. Do not classify a print against a quote received afterward merely because its exchange event time was earlier. Locked/crossed, stale, out-of-sequence, average-price, derivatively priced, opening/closing and other special trades need explicit source-rule treatment. Neither wholesale deletion nor indiscriminate inclusion is acceptable.

Produce parallel eligible and excluded populations with reasons and notional denominators. Retain corrected final history separately from as-seen observations. A duplicate report/cancel must not create two apparent reservoirs.

## 3. Formation of a candidate memory zone

At formation time t, select only already observed eligible executions over a fixed lookback. Cluster log prices with a bandwidth based on an ex-ante volatility scale and minimum tick size; cap zone count and impose a minimum distance between zone centers. Choose bandwidth, decay and minimum sample size in prior training, never to maximize the current day's later retests.

For a frozen zone Z and formation time t:

\[
N_Z(t)=\sum_{k:\,known_k\le t} p_kq_k\,w_t(k)\,K_Z(p_k),
\qquad
C_Z(t)=N_Z(t)/\sum_kp_kq_kw_t(k).
\]

The kernel K is declared, the decay w uses the selected execution/receipt convention, and numerator and denominator use the same eligible population. C is observed concentration, not a percentage of all liquidity. Abnormality compares N with a trailing same-symbol, same-time-of-day distribution excluding the current observation. Corporate-action and share-unit breaks reset or correctly transform the history.

Keep observed print concentration and observed response as separate fields. A large cluster can result from reporting conventions, benchmark execution, aggregation, internalization, adverse selection or broad market movement.

## 4. From concentration to response evidence

A response label uses an explicitly matured horizon. For eligible quote midpoint M around an execution:

\[
R_{k,h}=\log M_{t_k+h}-\log M_{t_k^-}
          -\widehat\beta_{k,t}\,\Delta\log I_{t_k:t_k+h}.
\]

If an aggressor sign a is supportable, aR is signed response; otherwise retain unsigned response. The beta and all controls are trained before t. At decision time u, include this label as a feature only when t+h and the necessary observations are already known by u.

Low impact per unit of historically signed flow may be consistent with absorption. It can also reflect poor signing, midpoint reporting, delayed trades, omitted market controls or benign informational flow. The word **absorption** therefore requires both qualified response evidence and prospective retest validation; concentration alone earns the label **observed execution zone**.

Acceptance/rejection uses the same frozen-zone first-passage law as the node engine. A retest is a new episode after a declared separation interval. Measure rebound-before-breach, breach-before-rebound, residence time, spread/depth behavior and subsequent movement. Unresolved and unobservable cases stay separate. A later retest can update tomorrow's memory, but cannot be inserted into today's earlier feature.

## 5. Cross-session persistence

Persist exact zone formation identity, source/version, initial bounds, notional, response window, mature-at time, past retest count, posterior/empirical response uncertainty and invalidation history. Never redraw yesterday's level to today's low. Corporate actions, stale prices, major news, broken source coverage and repeated qualified breaches can invalidate a memory zone.

A decayed historical score is an explanatory statistic, not a probability. Convert it to a probability only through a model calibrated on separate future episodes. Do not let long-lived zones acquire apparent sample size by counting every overlapping quote as an independent retest.

## 6. Required ablation

Compare matched price/volume zones with identical widths, age and distance; on-exchange execution zones; all-tape concentration; and the added off-exchange condition. Add ordinary VWAP/volume-profile and continuous liquidity covariates first. Residual value must survive report-lag, sale-condition, corporate-action, venue-coverage and news controls.

The prospective outcome is improved touch/hold/break or remaining-range/close probability, not a story about hidden institutions. Use day/episode-clustered uncertainty and a fixed inspection budget through the incumbent evaluator.

**Kill or downgrade if:** the apparent effect disappears after report-time alignment; is entirely driven by corrected/late prints; depends on a tiny unqualified denominator; fails matched on-exchange and price-volume placebos; or adds no proper-score/entry-outcome improvement. A descriptive execution-memory overlay can remain useful even when the directional hypothesis fails, but it must retain that descriptive status.

## 7. Minimal output contract

Zone ID and original bounds; execution versus receipt window; eligible/source volume and coverage; concentration/unusualness; quote quality; sign method and unknown share; matured impact response with horizon; past retest counts/results; decay and invalidation; condition exclusions; current distance; model evidence state; source clocks and correction lineage. Participant identity and intent fields are absent unless a separately licensed source explicitly supplies a limited, qualified category.

The first dealer-pressure slice treats this family as an optional later ablation. It is not a prerequisite for determining whether inventory information adds value.

<!-- Report-local source links. Scope and access limits are in SOURCE_REGISTER.md. -->

[I08]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/market_microstructure/commission15/COMMISSION_15_HARDENED_REPORT.md
[I16]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/DARKPOOL_DESK_AUDIT_AND_UPGRADE_2026-08-05.md
[I32]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/darkpool_signals.py
[I33]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/darkpool_context.py
[I34]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/scripts/build_darkpool_desk.py
[I35]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/collectors/finra_short_volume.py
[I36]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/collectors/finra_ats_transparency.py
[I37]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/MASSIVE_ADVANCED_INTEGRATION_MASTERPLAN_BY_FABLE.md
[IPR7990]: https://github.com/mastermindx-market-intelligence/macro/pull/7990
