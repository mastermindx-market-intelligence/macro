# Executive research verdict

## The decision

**Mastermind should pursue a bounded, research-only test of inventory-conditioned hedge pressure. It should not treat a dealer-inventory estimate or a mechanical pressure map as a validated extreme-price forecast.**

The missing capability is a chain of measurements and conditional models: source-qualified option activity; uncertain signed inventory; fully repriced target hedges; plausible external execution relative to liquidity; and calibrated future outcomes. The current code already supplies important Greek, source, scenario, publication and evaluation foundations. The highest-value next experiment asks whether better inventory information improves forecasts enough to justify the data and engineering cost.

The recommended first slice is a **new SPX/SPXW-to-ES information-value experiment**, comparing prior-OI assumptions, public-flow reconstruction and a scoped participant-informed benchmark on the same fifteen-minute excursion targets. Preserve the accepted P5 SPY/QQQ/IWM next-ten-minute variance experiment. This research changes neither that registration nor any production decision authority. [I01] [I03] [I05]

## 1. What is established, and what remains a hypothesis

| Finding | Research verdict |
|---|---|
| Option Greeks can be repriced to calculate a conditional hedge-target change | Established accounting under the specified inventory, model, reference and hedge convention |
| Public trades plus unsigned OI uniquely identify dealer positions | False in general; observationally equivalent assignments remain |
| Participant-coded buys and sells reduce uncertainty | Yes for the covered transaction universe; absolute starting positions and extra-book risks remain qualified |
| Target hedge changes are actual dealer executions | Unproved; netting, warehouse risk, execution delays and instrument substitution matter |
| Large gamma implies important price impact | Unproved without matched horizon/instrument liquidity and execution assumptions |
| A countercyclical response creates a pin | False as a general implication; damping does not supply an anchored attractor |
| The system can produce useful LOD/HOD/close probabilities | Scientifically plausible, but requires prospective calibration and incremental validation |
| A universal 15:50 auction model covers SPY, NYSE and Nasdaq | Incorrect; use primary-venue phases and historical rule versions |
| This research establishes Mastermind alpha | No; source research and synthetic mechanics are complete, market validation is a later task |

## 2. Inventory is the key information problem

An ask-side option print identifies where execution occurred relative to a quote. It does not reveal customer versus dealer capacity, opening versus closing, a complete package, beneficial intent or a permanent book change. A dealer can also be the passive or aggressive party. Research with richer participant records confirms why customer liquidity provision matters. [R04] [R07]

The correct signed-position identity is simple:

\[
\delta h=q\left(1_{\mathrm{dealer\ buyer}}-1_{\mathrm{dealer\ seller}}\right).
\]

Buying to close a dealer short increases signed holdings; selling to close a dealer long decreases them. Opening/closing matters for OI reconciliation, but is unnecessary when qualified dealer buy/sell quantities already establish the signed transaction increment.

By contrast, one trade changes OI by:

\[
\delta OI=q(o_B+o_S-1).
\]

Both open adds contracts, both close removes them, and a transfer between opening and closing leaves OI unchanged. The same OI change can coexist with positive, negative or zero dealer inventory change. Later OI can constrain feasible histories, but does not uniquely select one; expiry makes next-session OI especially weak for reconstructing the intraday 0DTE path. Reports 03 and 06 provide the proof, competing models, joint-capacity constraints and falsifiers. [R18]

Maintain distinct public-sign, capacity, position-effect and inventory uncertainty. A Bayesian posterior is conditional on assumptions; an unweighted scenario set is not a posterior. Neither becomes a calibrated market forecast merely by receiving a percentage label.

## 3. Full repricing should extend the existing machinery

Current Macro already has GEX/VEX/CEX, a spot-repriced gamma profile and a typed fixed-OI spot × future-time Greek surface. Macro #7306 is merged. Terminal's strike hedge-profile terminology/completeness has also been improved. Those are source advances to preserve. The accepted October 3 contracts already contain endpoint-rehedging reference kernels; this commission extends them rather than rebuilding GEX. [I03] [I11] [I23] [I50] [IPR7306]

For a common price coordinate:

\[
B=-\sum_i h_i m_i\Delta_i,\qquad
Q^{target}=B_1-B_0,\qquad
H=S_1Q^{target}.
\]

Positive H is a modeled purchase requirement. For SPX, B is a risk coordinate, not executable shares. Convert to ES/SPY with native contract multipliers, basis and residual-risk disclosure. A futures reference notional is not cash paid.

The useful field is conditional on inventory, surface motion, time, contract fixing and hedge policy. Gamma, vanna and advancing-calendar charm explain local changes; the exact endpoint difference is the reference near expiry. Separate inherited positions, new net trading and nontrade adjustments. Do not add trade delta again after it has already entered the ending book.

The synthetic witness passes 62 bounded assertions and shows a practical reason for this discipline. For the commission's invented 6,000-to-5,979, +1.2-IV-point, +20-minute shock, alternative inventory signs reverse modeled pressure. A separate invented inventory-update example also produces a material exact-versus-linear difference. These are mathematical demonstrations, not actual SPX positions or an empirical error estimate.

## 4. The market evidence supports a conditional test

The latest July 2026 Adams–Dim–Eraker–Fontaine–Ornthanalai–Vilkov draft emphasizes inherited expiring positions and distinguishes its calendar identification from noncausal intraday futures relationships. It subsumes two earlier working papers. Amaya and coauthors provide a participant-derived position study with model-counterfactual limits. The current Brogaard–Han–Won author summary reports a different activity-based volatility result; its latest full draft was unavailable here. These are reasons to separate treatments and coverage, not declare one universal 0DTE effect. [R02] [R03] [R05]

Gamma Fragility and order-book research motivate liquidity interaction. They do not give Mastermind an observed percentage of tape controlled by dealers. Test demand relative to expected volume first, then directional executable capacity only when actual event/depth and response evidence exist. Preserve the difference between expected absolute horizon-net demand and gross rehedging turnover. [R01] [R10] [R11]

The existing vanna/charm adjudication remains adverse evidence against simple directional charm. Its surviving conditional concentration/volatility findings and failed narratives must stay in the experiment's controls and negative-result record. [I15]

### An adjacent incumbent already has negative GEX forecast evidence

The final owner census found MAS-260 Exposure Outlook's current record: its tested GEX forecast hypothesis is closed for promotion, while a price/volatility baseline and local shadow/Terminal consumer continue. The underlying negative-test metrics were not available in that record and were not reproduced here. Preserve that ruling, recover the exact existing comparator through its owner, and test genuinely new inventory information without repackaging the rejected hypothesis. Macro #7328 and its local/unpushed continuation are existing owners to reuse. [M01] [IPR7328]

## 5. Nodes and probabilities need different contracts

An **absorption candidate** has countercyclical modeled response with enough potential liquidity significance. An **attractor candidate** requires inward expected pressure from both sides around an anchored root. An **acceleration candidate** has procyclical demand that strengthens along a break path. A **reservoir** is a separate underlying-liquidity hypothesis. These labels are not synonyms for large OI.

The probability model freezes each zone at formation, defines touch and gap-through, and scores rebound-before-breach, breach-before-rebound, unresolved and unobservable states separately. Closing above a level is not the same as holding on first touch.

Today's known low/high creates an important probability mass: the final low may remain the morning low without another touch. Forecast a new extreme, remaining-session high/low quantiles and final-day extreme regions explicitly. Close probabilities use disjoint bins plus overflow, and respect the relation between close and final range. Hazards suit first-passage questions; quantile/distributional models suit extrema and close. Their empirical superiority still needs testing.

## 6. Closing intelligence is an adjacent engine

The pre-publication model uses already-announced index/weight changes, realistic passive-tracking and execution scenarios, dated ETF baskets/net-share observations, allocation and parent-order residual scenarios, historical auction behavior, current liquidity/basis and options pressure. It must not add overlapping headline notional estimates as independent orders.

After official publication, the nowcast uses the venue's actual imbalance, paired interest, reference/indicative/near/far prices where defined, revision dynamics, source health, cutoffs and permissible late orders. The model must distinguish a changed reference-price calculation from newly submitted net shares.

Normal equity-close clocks illustrate why venue identity matters:

| Primary venue | Routine first information | Later phase |
|---|---|---|
| NYSE | 15:50 ET | Current documented D-order entry/change deadline 15:59:50 |
| Nasdaq | 15:50 EOII every 10 seconds | Full NOII every second from 15:55; distinct MOC/LOC rules |
| NYSE Arca | 15:00 ET | Closing freeze 15:59 |

SPY is primary-listed on Arca, so its 15:30 state is already after routine auction publication. NYSE's 2026-36 filing also requires a separate implementation-version gate; legal effectiveness and technology rollout are not interchangeable. [A01] [A07] [A13] [A15] [A44]

SPX official close, SPY's Arca cross, an ES 16:00 mark and CME settlement remain different targets. The closing model cannot silently transform one into another.

## 7. Competitive lessons and acquisition decisions

The 15-profile census answers all 15 commission fields for the named systems and serious additions. Useful product jobs include transaction pressure, standing-book surfaces, hypothetical future repricing, source-quality controls and historical outcome calibration. Public disclosure does not establish a complete dealer book or comparable “accuracy” across different label definitions.

The most consequential distinctions are participant-tagged versus OI/repricing products; genuine native futures-option modeling versus chart-coordinate mapping; and original historical inputs versus replay with a current engine. ZeroGEX is a close functional comparator for zero-flow roots, but its accessible evidence does not establish a validated multi-session close target. Report 04 marks access limits and proprietary unknowns explicitly.

Data rights can determine the viable route. FirmTape's public licensing excludes a competing positioning terminal; an API or paid tier cannot be assumed to permit the intended Mastermind use. The source matrix distinguishes internal analysis, retention/training and external derived outputs. [C55]

Cboe's covered MM buy/sell contract volumes make a ten-minute participant-data trial a candidate. Current C1 schedule components are $3,000/month for ten-minute updates and $1,000 per requested historical month; one-minute updates are $12,000/month. Actual release delays, corrections, history and permitted use are essential. The November 8, 2026 correction change is future at this research cut. No purchase or sample request occurred. [A29] [A30] [A31] [A33]

Theta's current all-Greeks documentation has a one-hour minimum in its latest 0DTE method. Exact-time qualification is necessary in the final hour, and same-price IV refitting must be separated from fixed-IV clock stress. The public documentation does not establish Mastermind's current entitlement or retained raw tape. [A28]

## 8. Implementation sequence and decision rule

The research handoff starts with source/cohort admission, then an additive book-state and endpoint-demand contract through current owners. It compares information arms with identical prices, surfaces, liquidity, clocks and labels. A small registered model block competes against ten baseline families; the 72-feature catalog is a bounded backlog, not an instruction to fit 72 variables.

The proposed primary endpoint is mean quantile loss for normalized next-fifteen-minute ES upside/downside excursions. Remaining-session extrema, zone behavior, close and actual incumbent candidate outcomes are separate secondary families. A proposed 2% useful-loss hurdle, day-block uncertainty, source coverage, latency and stress non-inferiority make the test rejectable. Current B1-RI adapter performance and actual incumbent-policy performance are separate comparisons.

Require separate frozen verdicts for fifteen-minute excursions, remaining-session extremes and the close. If adequate coverage and power rule out useful value from the scoped participant benchmark, stop the tested endpoint claim. Stop broader reconstruction only after all required families rule out useful gain, or make an explicit cost decision that leaves the remaining family unanswered. If the interval remains wide, the result is inconclusive. If raw flow or liquidity explains the gain, use the simpler qualified block. If a gain survives real availability, proceed to prospective shadow capture before probability or policy promotion.

The complete package provides the source census, 20 commissioned reports, 72 rigorously specified candidates, 37-product data matrix, source/claim registers and a rerunnable synthetic witness. It does not contain a deployed collector, a bought feed, trained market coefficients or new trading authority.

<!-- Report-local source links. Scope and access limits are in SOURCE_REGISTER.md. -->

[A01]: https://www.nyse.com/trade/auctions
[A07]: https://www.govinfo.gov/content/pkg/FR-2026-08-18/pdf/2026-16783.pdf
[A13]: https://listingcenter.nasdaq.com/rulebook/nasdaq/rules/nasdaq-equity-4
[A15]: https://www.nasdaqtrader.com/TraderNews.aspx?id=ETA2019-66
[A28]: https://www.thetadata.net/docs/operations/option_history_greeks_all.html
[A29]: https://datashop.cboe.com/cboe-options-open-close-volume-summary
[A30]: https://datashop.cboe.com/documents/Open_Close_10m_Spec_v1.6.pdf
[A31]: https://datashop.cboe.com/documents/Open_Close_1m_Spec_v1.5.pdf
[A33]: https://cdn.cboe.com/resources/membership/Cboe_FeeSchedule.pdf
[A44]: https://www.ssga.com/us/en/institutional/etfs/state-street-spdr-sp-500-etf-trust-spy
[C55]: https://www.firmtape.com/licensing
[I01]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/options_intelligence/2026-10-03/MASTER_PLAN.md
[I03]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/options_intelligence/2026-10-03/CONTRACTS.md
[I05]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/options_intelligence/2026-10-03/options-near-expiry-spec.md
[I11]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/gex_engine.py
[I15]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/OPTIONS_OPEX_VANNA_CHARM_ADJUDICATION.md
[I23]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/options_scenario_surface.py
[I50]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/marketStructure.ts
[IPR7306]: https://github.com/mastermindx-market-intelligence/macro/pull/7306
[IPR7328]: https://github.com/mastermindx-market-intelligence/macro/pull/7328
[M01]: https://linear.app/mastermindx/issue/MAS-260/options-exposure-outlook-research-calibrated-forecasts-and-terminal
[R01]: https://abarbon.com/papers/gamma-fragility
[R02]: https://www.jean-sebastienfontaine.com/papers/0dte-options-volatility.pdf
[R03]: https://cdn.cboe.com/resources/education/research_publications/gammasqueezes.pdf
[R04]: https://www.sec.gov/files/dera-hope-reasonable-prc-2503.pdf
[R05]: https://peterywon.github.io/
[R07]: https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/on-inferring-the-direction-of-option-trades/FDA4541B57F78B2C8DCE129AFC25AAF0
[R10]: https://arxiv.org/abs/1011.6402
[R11]: https://arxiv.org/abs/1104.4596
[R18]: https://www.optionseducation.org/referencelibrary/faq/general-information
