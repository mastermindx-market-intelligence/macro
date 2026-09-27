# BioCatalyst R7 — ranked stock picks and full investment-thesis design

Status: **NORTH-STAR DESIGN CANDIDATE / SYNTHETIC PROTOTYPE / NOT APPLIED TO PAPER / NOT PRODUCTION ACCEPTED**.

Decision owner: Chairman. Design owner: current BioCatalyst Sol session. This specification implements the current product-direction correction, not a real recommendation model. It neither changes the existing Macro #6712 implementation branch nor revives a previously held source, score, rank or trading operation.

Shared decision: `DEC:SECTOR-CATALYST-RECOMMENDATION-NORTH-STAR`.
Shared build contract: [`SECTOR_CATALYST_INVESTMENT_INTELLIGENCE_NORTH_STAR.md`](SECTOR_CATALYST_INVESTMENT_INTELLIGENCE_NORTH_STAR.md).
Mandate: [Macro #6712 / 5851663121](https://github.com/mastermindx-market-intelligence/macro/pull/6712#issuecomment-5851663121).

## 1. The change that matters

R6 improved comprehension but still framed the product as a briefing. The Chairman explicitly requires investment selection: ranked stock recommendations, quantified catalyst outcomes, conditional rerating, priced-in expectations, dates/timeframes and a complete researched thesis. The readable briefing is now a presentation layer of that richer intelligence, not its ceiling.

The first screen answers **what to buy, why, for how long, the expected payoff and the key loss scenario**. A click reveals how the scientific or procurement evidence connects to that equity judgment. The full methodology lives behind the immediate interpretation; it is not replaced by an unexplained score.

R4/R5 rejected primary compositions and their old native preparation are not current instructions. Preserve correct source/missingness fixes and useful interactions, not the briefing-only ceiling or the rejected evidence-browser front door.

## 2. Actual R7 prototype surfaces

The self-contained conversation artifact is `r7/BIOCATALYST_R7_PROTOTYPE.html`, SHA-256 **`06ec96d9d89f4f2137096283c11c5abc3a1e56c49a14782f13188edcdc39878d`**. This filename is an artifact identity, not a claim that the HTML was committed to this repository or applied to Paper.

- Default / `#picks`: ranked Buy ideas, a leading stock thesis, dates, 3/6/12-month views for the biotech examples, expected net return, positive/negative/unresolved outcomes, failure-case magnitude and an explicit excluded/Avoid view.
- `#pick/BIO-A` and other identifiers: Investment thesis; Evidence & probability; Valuation & priced in; Research dossier. Every displayed idea opens its own synthetic company and assumptions.
- The sector selector switches to Defense Procurement, with the same investment grammar and domain-specific evidence. Defense examples are six-month-only; the prototype does not pretend that horizon estimates exist where they do not.
- `#edge`: evidence/forecast/investment validation requirements, not fabricated historical results.
- `#blueprint`: extensive on-design builder notes preserving the complete investment chain and existing owners.

Earlier R4/R5/R6 investigation, historical-cutoff, comparison and rendered-state routes remain reachable as supporting references. Their old test totals are historical evidence, not automatically a new R7 pass.

Dark design: graphite surfaces, luminance depth, restrained blue for action and green/red for actual signed payoff. Light design: cool canvas, white material, borders/shadows and deeper text-grade semantic inks. Mobile uses a single-column reading order and full-width primary action. The top of each new view explicitly labels all companies, probabilities, prices and returns synthetic. No logo, ticker or source attachment is borrowed to imply a real recommendation.

## 3. A leading pick with reconcilable numbers

The six-month BIO-A / Aster Bio example has a fictional $20 reference price and a company-targeted Phase III event on 12 November 2026. Outcomes through 26 March 2027:

| Synthetic state | Probability | Diluted equity price | Gross return |
|---|---:|---:|---:|
| Strong positive | 50% | $36 | +80% |
| Modest positive | 18% | $27 | +35% |
| Delayed/unresolved | 12% | $18 | -10% |
| Negative/failure | 20% | $8 | -60% |

These probabilities sum to one. Positive catalyst probability is 68%; expected price is $26.62; expected gross return is 33.1%; subtracting 1% illustrative friction gives **32.1% net expected return**. The main page rounds this to +32%. It is not a guaranteed target, a validated forecast or a stop-loss limit. The specimen supplies no validated forecast uncertainty interval; export preserves that field as null.

The conditional $36 success value is explained rather than merely asserted: $1.96bn lead-asset value + $220m other assets + $200m projected cash - $40m debt = $2.34bn equity; divided by 65m diluted shares = $36. Other branches use their own financing and diluted shares. The underlying commercial values are invented assumptions; production must expose patients/volume, price, adoption, costs, rights, discount rate, financing and terminal assumptions rather than treating these fixture values as a model.

The reverse-valuation illustration yields about 42% price-implied positive probability against the 68% model view. It fixes the unresolved branch and reuses the same conditional prices, omitting discounting and risk-premium adjustments. The UI states that it is **model-implied, not observed market consensus**, and not independent corroboration. Production requires sensitivity, other-asset value and genuinely independent expectations evidence. Impossible inversions must remain model errors, not silently clamped beliefs.

## 4. Scientific depth, not a press-release summary

The BIO-A dossier demonstrates a fictional randomized Phase II study: 66/120 treated responders versus 18/60 controls, or 55% versus 30%, a 25-percentage-point absolute difference. Its approximate unadjusted interval is shown as an illustration, not a multiplicity-adjusted study result. Four serious adverse events among 120 treated participants versus one among 60 controls do not establish rare-event safety.

The planned pivotal trial has 600 participants, but its endpoint moves from week 16 to week 24. That creates an explicit durability question. The research view puts the favorable efficacy evidence beside the strongest counterargument, rather than treating every earlier positive study as independent proof of phase III success.

Production research must inspect original protocols and amendments, analysis plans, estimands, power, endpoint hierarchy, multiplicity, effect sizes and intervals, population changes, attrition, missingness, safety exposure, class/mechanism risks, comparator quality, manufacturing/inspection, and regulatory precedent. Filings/transcripts add the economic-rights, funding, launch and execution context. Public evidence that is absent remains absent; the specimen attaches no genuine study, FDA review or company filing.

Matched historical priors, structured evidence and evidence-bound LLM judgments may materially influence evaluated forecasts. The displayed 54% -> 64% -> 68% stages are synthetic alternatives, not an additive scoring rule or calibration proof. Proper model development must compare prior-only, structured-only and LLM-enriched candidates on held-out and prospective outcomes through the existing evaluation owner.

## 5. Recommendation is not the same as likely success

The BIO-F exclusion deliberately has an 84% positive-catalyst probability but negative modeled expected return at its reference price. It is labelled **Avoid at this price**. BIO-D also demonstrates that a positive regulatory outcome can coexist with a negative stock-return branch when a narrow label disappoints expectations.

These counterexamples are mandatory design and evaluation cases. Do not sort by approval probability and call that stock selection. The prototype sorts its invented Buy fixtures by arithmetic expected net return solely to demonstrate the UI. Production must consume the existing recommendation/entry policy with uncertainty, risk, concentration, liquidity, cost and horizon constraints. No new browser ranker is authorized by this specimen.

## 6. Defense and future sector profiles

The Defense selector changes the dossier to program/funding evidence, solicitation and award material, competitors, technical performance, execution capacity, orders, margins, working capital and retained economics. The thesis translates a potential win into issuer earnings and valuation rather than displaying the contract ceiling as revenue.

Share the recommendation contract, evidence identity/versioning, scenario grammar, user experience and evaluation discipline. Do not reuse biotech success priors, clinical labels or an all-purpose LLM score in Defense. Other sectors add their own causal evidence and conditional financial models through existing GMI, Company/Event, Financial Intelligence, Alpha and recommendation owners.

## 7. Verification actually performed

`R7_VALIDATION.json` binds the final HTML digest above and records **140 passed / 0 failed** local Chromium assertions. Checks cover default ranked entry, synthetic disclosure, horizon-specific probability/payoff arithmetic, exact stock navigation, dossier tabs, source-missingness labels, downloaded thesis data, clinical fixture arithmetic, diluted equity bridges, return focus, the high-probability/negative-EV exclusion, Defense switching, and layout at 1440/768/390/320 in both themes. Primary mobile action is at least 44px and within the initial 844px viewport. The runs recorded no uncaught browser exceptions or external network requests.

Twenty final captures cover picks, thesis, probability, valuation and dossier at desktop/mobile in both themes. Representative final desktop/light science, desktop/dark valuation and mobile/dark picks were visually inspected; these are local HTML renders, not native Paper screenshots or a human cold-reader study.

The earlier render identified two real classes of defect: the 320px action fell below the intended fold and a dossier tag caused horizontal overflow. Those were repaired and the complete local suite rerun. A separate six-feature presence check distinguishes R6 from the new composition. Counts are structural/interaction assertions, not evidence of clinical calibration or investing performance.

No production source coverage, entitlement, statistical model, real-company valuation, calibration, independent research review, portfolio performance, account persistence, alert delivery, Chinese parity or actual human three-second comprehension is claimed. Shared SC-01 through SC-30 are implementation acceptance obligations, not 30 passed production tests.

## 8. Paper and source continuity

Same Paper file `01M2WGNCX9475G79JRKJTCM08P`, Bio page `p-K-0`, existing new desk `1ECU-0`, content target `1EJZ-0` with heading `1EK0-0`. The shared file reservation remained unreleased in the bounded current check; **zero R7 Paper effects** were attempted. The completed nine-gateway compatibility repair and own indicator cleanup remain DO_NOT_REDO. Old safety-refused actions are not replayed.

After actual existing-owner reservation return/admission, preserve the shared shell and author the recommendation-first R7 content on the same Bio targets. Do not apply old R4 fragments unchanged or create another file to evade same-file custody. Then inspect actual native screenshots and retrieve actual JSX for implementation.

This documentation branch records the cross-sector mandate without taking over Macro #6712 or replacing live owners. Source publication/merge, user design acceptance, native rendering, model acceptance and product deployment are separate outcomes. The next implementation plan must name concrete accepted source/assessment/valuation/recommendation/evaluation seams before changing their behavior.
