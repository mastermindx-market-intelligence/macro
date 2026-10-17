# Nightglass hardening and independent model research

**Date:** 2026-09-10. **Parent:** WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY. **Carrier:** existing draft PR #7027, continued from `0a754a3c796b162bc5d198c781af24a141538edf`. Records only. Models remain SPEC_ONLY/unadmitted. No production, trading or source-law promotion.

## Scope and evidence

Chairman requested substantially deeper findings, extrapolations and useful models after the first reconstruction. This pass used the previously supplied competitor evidence, fresh independent primary sources, current own-source inspection and newly authored mathematics/synthetic studies. No new Nightglass/member collection, subscription, data purchase, vendor code reuse or third-party clone execution occurred.

Protected Mastermind Skillpack pin: `dd553d1b0b8eed9511da2d3d5ec02cc9cd8edca1` (INDEX/COLD_START/RECONCILE_STATE/CLOSEOUT, v1.0.1/bootstrap1). Internal source context: Macro `382854156416d5839bea9905bf9333d2587d321b`; Terminal `4fa11197a999efda317f1caba8b5b884514daabe`.

The prior checkpoint `NIGHTGLASS_PUBLIC_MECHANICS_2026-09-10.md` remains historical evidence. This addendum tightens particular interpretations; it does not replace OA-0 or grant a DNR exception.

## 1. Correct the benchmark: high hit frequency need not imply an edge

For a zero-drift continuous martingale return starting at zero and stopped at +a or -b, with eventual first-barrier arrival, bounded-stopping conditions, no jumps/overshoot, no costs and full execution, expected terminal return zero implies:

`p(target first) = b / (a + b)`.

A +30% target and -50% stop therefore produce a 62.5% no-edge hit rate, not 50%. An independent seeded simulation of 100,000 symmetric random walks with exact +3/-5 lattice barriers yielded 62.489% upper hits and -0.0088% mean normalized return. This is a diagnostic null, not a claim actual option premiums are physical-measure martingales.

The archived vendor count was 3968/6389 = 62.1067%. Its naive independent-binomial Wilson interval is approximately 60.91–63.29%, containing 62.5%. Dependence between contracts/campaigns requires a further uncertainty audit. This does NOT establish vendor unprofitability: expiry returns, short-side accounting, management and costs differ from a pure two-outcome bracket. It shows that the count alone does not establish positive expectancy.

For a pure bracket and normalized round-trip cost c, `EV=p*a-(1-p)*b-c`, so `p_break_even=(b+c)/(a+b)`. At costs of 1%, 2%, 4% of initial premium, the hurdle becomes 63.75%, 65%, 67.5%. Those are illustrative costs, not observed vendor costs.

The useful research endpoint is executable after-cost policy value relative to geometry-, horizon-, liquidity- and regime-matched opportunities. Target, stop, deadline liquidation, no-entry and missing outcome evidence are separate categories. A stock target reached after option expiry is not an option win.

## 2. OI supports bounds, not a specific trader story

For an unchanged exact contract, ignoring exercise, assignment, adjustments and corrections, let V be traded contracts, d the net OI change, x jointly-opening transactions, y jointly-closing transactions and z transfers with one opening side. Then:

`x-y=d; x+y+z=V; x,y,z>=0`.

Thus `max(d,0) <= x <= floor((V+d)/2)`. For V=1000, d=300, jointly-opening contracts can be 300–650. A 100-contract alert inside that day can contain 0–100 jointly-opening transactions. Aggregate facts do not identify it.

The same aggregate DOES identify the number of opening contract-sides: `2*x+z=V+d=1300` among 2000 sides, or 65%. That is not the 30% net-OI/volume ratio and not the retained portion of one participant's position. The laboratory exhaustively checked small integer feasible sets and alert-subset bounds.

This is measurement mathematics, not resurrection of the killed DOI predictive family. More model capacity can impose priors, but cannot identify a fact that observationally identical histories leave ambiguous. Exercise/correction/identity changes invalidate the simplified equations unless separately accounted for.

## 3. Concrete primary-source opportunity: exchange-labeled measurement research

Cboe's current Enhanced TBT page and January2026 specification describe C1 execution records delivered T+1: buy/sell, opening/closing, capacity, quote context, execution type and linkage. The complex ID specifically links complex-to-complex executions. Other venues are planned, not current. The SEC filing references subscribing-member execution IDs; entitlement-specific linkage and completeness still require confirmation. Sources P1–P3 below.

This creates a credible proposed offline measurement panel: test quote-location interpretations against eligible execution mechanisms; measure opening/closing composition; evaluate package associations against eligible linked cases; and identify where abstention is required. It does not expose beneficial-owner identity or informed motive. A buy side is not automatically the aggressor; capacity is not institutional intent.

Delayed labels can supervise measurement research without becoming earlier intraday features. The observations are venue/product/mechanism-selected, so C1 performance cannot be promoted to all-market accuracy without a generalization study. Rights, permitted derived outputs, cost and actual-row delivery remain unverified; no purchase is authorized or performed. This supplements evaluation under existing source ownership, not a parallel live collector.

## 4. Data semantics can dominate model sophistication

Current Cboe Open-Close summaries are cumulative and delivered after their intervals. Summing snapshots100,150,120,160 produces530 rather than the latest160. The negative difference can be a revision, not a burst of bearish trades. Current1-minute documentation distinguishes later bust/cancel handling from the changes announced for November8,2026; those future changes must not be treated as effective on September10. Sources P4–P5.

Cboe also documents historical one-day OI shifts and changed volume denominators in particular venue/date ranges. A column named OI or volume is not sufficient to establish vintage or counting unit. Raw-to-derived joins need dated semantic versions.

A floor agreement clock can differ from booking/receipt time. The same price2.10 lies at the ask of2.00/2.10 and at the bid of2.10/2.20. Using a later quote can invert a label. Event time, available time and later correction time must survive separately. A correction available at40 must not replace the version available at20 in a decision taken at25.

## 5. Uncertainty and repeated evidence

For qualified bullish weight B, bearish weight D and unresolved mass U, a whole-population bullish-weight fraction lies in `[B/(B+D+U), (B+U)/(B+D+U)]` absent further assumptions. At B900,D100,U1000, the classified slice looks90% bullish while the full range is45–95%. These are evidence-share bounds, not price probabilities. Classification-error allowances widen them.

Marginal probabilities need not multiply: p(buy)=0.8 and p(open)=0.7 imply a joint range0.5–0.7; their product0.56 assumes dependence structure not established by those marginals.

A chart, report and watchlist displaying the same observation do not produce three independent confirmations. The equal-correlation illustration gives five votes with correlation0.8 the variance-equivalent count1.19. This is not an empirical estimate of Nightglass correlation, but a reason to measure evidence dependence.

Seven successful and three unsuccessful campaigns yield70%. Counting each success ten times and each loss once yields95.89% without a new successful campaign. This is a counterexample, not an allegation about the vendor's report.

## 6. New own-estate finding: two price engines have different clocks

### Terminal Smart S/R

Actual source, not just the prior guide, was read at `terminal/lib/suites/structure/smartSR.ts`, blob `3dd485f0ba6b2b204b6872f25ff4e8ab4a4c5458`, with `pivots.ts`, blob `22ff06bedcf4c024d8e3ebd82fd49bcd30a55af7`.

The engine clusters confirmed pivots around a fixed first-pivot anchor, distinguishes pending from published levels, measures formation reactions inside the confirmation lag, and emits later holds/breaks using available bars. Its display draws from the earlier anchor while publication happens later. Current ranking, deduplication, labels and retirement affect the later rendered map. Fixed coordinates do not imply the final top-K drawing was available historically.

Its score is touches times mean formation reaction times recency, algebraically a decayed sum of formation reactions. That is not an independently validated probability. A pivot's favorable right-wing response is part of formation evidence, not automatically a post-publication tradable outcome. Cluster-anchor offsets must be considered before claiming the adverse term is always zero.

### Macro current chart digest

`engine/neuralweb/chart_perception.py`, blob `9cf5f1c11d922b2b9ec34f59f922354a2b1a9c17`, is already a read-only machine/analysis price-structure path. Its swing computation uses the current loaded window's latest ATR over the historical scan, appends a provisional final extreme, and level clustering returns centroid prices.

That can serve a current-context summary, but it is not an immutable historical level-publication receipt. Later volatility or new points can change retrospective geometry. This is source-semantic analysis, not a production-failure claim.

A separate bounded pure-function synthetic probe was attempted on the freshly pinged MacStudio, but process-start and session-reconciliation responses timed out without inspectable output or a PID. No result/exit status was observed; it was not retried or counted as a successful experiment. The request contained no repository mutation, loader or persistence action.

The no-rebuild conclusion is stronger than before: reconcile existing consumer purposes and first-available/publication contracts rather than create a third price engine. A reviewed source-owned projection or interface extension is preferable to extracting truth from labels/pixels. GEX-derived `levels.v1` remains a different object again.

## 7. More confirmation can make the opportunity worse

For an underlying-level long plan with objective U, boundary L, entry E and minimum reward/risk k:

`(U-E)/(E-L)>=k` implies `E<=(U+k*L)/(1+k)`.

With U103,L99,k1.5, the entry ceiling is100.60. A move from100 to101 improves directional confirmation but reduces geometric reward/risk from3 to1. A fixed cost convention narrows the interval further. These are underlying geometry examples, not automatic option entries.

A useful product state is therefore: evidence improved, but the original entry window expired. Keep thesis plausibility, entry viability and quote executability separate instead of moving the original map to rescue a late entry.

## 8. Correct direction is not exact-option profitability

A stipulated European, non-dividend Black-Scholes example: S100,K105,30days,IV50% gives a call3.69196. After S rises to103, seven days pass and IV falls to30%, its value becomes2.22503, down39.73%. At unchangedIV50%, the same remaining-time example gains15.52%. This is a synthetic valuation, not an American pricing service or market forecast.

A midpoint moving1.00 to1.10 looks+10%; an entry ask1.10 and exit bid1.05 gives-4.55%. Crossing quotes is a declared benchmark, not a claim every actual trader pays it. A limit-order policy must account for delay/nonfill rather than borrowing guaranteed participation.

Deep-ITM stock replacement can have nearly unit delta; it is not mechanically non-directional. Informed intent remains uncertain. This conceptual correction does not authorize removing existing filters or reopening DNR families.

## 9. Coherent target, stop and deadline modeling

Proposed discrete competing hazards hT,hS require `hT+hS<=1`. Survival through j is the product of `1-hT-hS`; cumulative target incidence sums prior survival times hT, and likewise for stop.

At hazards0.12/0.08 for ten steps, target incidence is53.56%, stop35.71%, survival10.74%. Ignoring stops yields a false target figure72.15%. A deadline survivor needs a preregistered terminal-value policy; genuine missing/censored data is a different category.

Maturity-only reporting can also change the observed mixture. In a synthetic equal mixture of short-horizon70% winners and long-horizon40% winners, observing all short cases but only20% of long cases gives65% completed wins versus55% eventual full-cohort wins. No fabricated trade is required.

## 10. Management and gamma counterexamples

A fair two-step price tree100→120/80→140/100/100/60 yields holding P&Ls40,0,0,-40. A half-trim after the first up move yields30,10,0,-40. Both means are zero; trimming lowers standard deviation28.28→25.50 and changes win frequency without generating mean alpha. Actual management value needs fixed-entry comparisons, quantities, adds, cost basis and fees.

The previous UNH half-trim arithmetic remains correct under its quantity assumptions: entry1.61,trims3.00/4.05 leaves25%, banks81.06% of original premium profit, and marks total118.94% if the remainder is valued at4.05. It is not proof of subscriber fills.

For stipulated signed options positions+10000 at strike95 and-100 at105,30days,IV40%,spot100, the interpolated strike-contribution zero is104.895 while the whole portfolio's hypothetical-spot gamma zero is181.717. Numerical and analytic roots agree. The two axes answer different questions. Hedge change `dH=-Gamma*dS` also shows negative gamma sells into a fall under the elementary hedge model, not buys. These are narrative/unit consistency tests with assumed inventory, not a vendor-backend defect claim.

## 11. Three research models, not a new universal score

### M1: measurement/association

Estimate an appropriately calibrated joint state or identified set for execution interpretation, opening/closing and package association, excluding beneficial-owner motive. Begin with transparent stratified quote/mechanism baselines against entitled labels; a more flexible model must improve held-out calibration and supported-domain coverage. Retain abstention, incomplete quantity and alternative packages.

For candidate packages h consuming q_hi of observation i with total observed v_i, require `sum_h x_h*q_hi<=v_i`. Exact linkage is evidence where available; heuristic compatibility is not identity. Never multiply marginal confidence scores or reuse one print across independent packages without accounting.

### M2: conditional outcome and waiting

Bind forecasts to the canonical campaign revision, real structural publication time, entry policy and exact deadline. A small discrete-time multinomial hazard model over target/stop/continue is a coherent initial candidate. Do not fuse new positioning keys into the frozen unsigned FS family. A potential waiting policy compares enter/wait/decline including opportunity costs; later confirmation is not free.

The counter-trend bearish question needs its own cohort. Relative underperformance in a rising market is not necessarily absolute downside or a winning put. Match catalysts, liquidity, horizon and geometry using known-at-decision regime information, never future index behavior.

### M3: instrument/management economics

Evaluate allowed expressions over underlying/IV/time/quote scenarios and a declared quantity/exit policy. Short-option premium, spread debit, capital risk and portfolio return use different denominators. Start with clearly labeled scenario analysis; a validated joint return policy is a separate milestone.

For uncertain states z and allowed action a, compare expected utility and its sensitivity over a justified uncertainty set, rather than acting on the best-case package interpretation. These mathematical proposals do not authorize real sizing, brokerage orders or a new risk-control plane.

### Evaluation and product proof

Preregister the existing-policy, activity-only, price-plan-only and combined baselines. Use both shared-candidate paired comparisons and full-policy comparisons including new opportunities/rejections. Retain all candidates, revisions, abstentions and no-entry outcomes under existing owners. Cluster inference by campaign/session; audit quote lag, source drift, future-shifted controls, missing inputs, trial count and horizon mix.

A seeded study of500 identical null policies per repetition selected training winners averaging72.652%, while their fresh tests averaged62.452%. Count the entire search, not only the winning model. Calibration or conformal terminology cannot repair leakage or guarantee finance coverage without assumptions.

The smallest useful product slice remains a real measured canonical event/campaign rendered with first-available evidence, uncertainty, source-backed levels and coherent/expired-entry reasoning. It needs real-path browser/machine proof. A trained notebook or new schema is not completion.

## 12. Verification, limits and continuation

The local packet contains24 original algebra/synthetic studies and47 passing unit tests, including exhaustive small integer OI feasible sets, payoff identities and finite-difference Greek checks. Eight intentionally wrong mathematical variants were all rejected. The earlier42 arithmetic checks were independently rerun and passed. These are not market backtests, production tests, out-of-sample alpha, or vendor-source execution.

No private model, actual AI provider, live scheduler receipt, subscriber fill or profitable market policy was recovered. Repository-wide Agent OS validation and hosted review are not claimed for this draft. Proposed models remain unadmitted.

**Exact next research action:** prepare one scoped measurement-panel preregistration with rights, entitled fields, clock semantics, supported domain and evaluation criteria. No data acquisition/fitting begins without its gates. In parallel, the existing OA owner must reconcile the already-merged OA-1T natural-RTH receipt; do not repeat implementation. AD-1T2, OA-3, OA-4/5 and current DNR gates retain their ownership.

## Primary-source pointers

P1 Cboe TBT specification v1.0 Jan12,2026: https://cdn.cboe.com/resources/membership/US-Options-Trade-By-Trade-Execution-Detail-Specification.pdf

P2 Current Cboe TBT product: https://datashop.cboe.com/enhanced-us-options-trade-by-trade-execution-detail

P3 SEC34-104415 Dec16,2025: https://www.sec.gov/files/rules/sro/cboe/2025/34-104415.pdf

P4 Cboe Open-Close product and dated historical conventions: https://datashop.cboe.com/cboe-options-open-close-volume-summary

P5 Current1-minute specification v1.5: https://datashop.cboe.com/documents/Open_Close_1m_Spec_v1.5.pdf

P6 OIC OI: https://www.optionseducation.org/news/open-interest-why-it-matters

P7 OIC option price behavior: https://www.optionseducation.org/referencelibrary/faq/option-price-behavior

P8 CME gamma: https://www.cmegroup.com/education/courses/option-greeks/options-gamma-the-greeks

P9 Pan/Poteshman: https://www.nber.org/papers/w10925

P10 Savickas/Wilson classification study: https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/on-inferring-the-direction-of-option-trades/FDA4541B57F78B2C8DCE129AFC25AAF0

P11 Competing-risk mathematics: https://pmc.ncbi.nlm.nih.gov/articles/PMC3135581/

P12 Conformal beyond exchangeability: https://arxiv.org/abs/2202.13415

P13 Backtest overfitting: https://escholarship.org/uc/item/4w1110bb

P14 Execution-policy study, indexed abstract: https://academic.oup.com/rfs/article-abstract/33/11/4973/5732665

All examples marked synthetic are newly authored deductions; primary papers support context/methodology, not a claimed replication or present-day trading edge.
