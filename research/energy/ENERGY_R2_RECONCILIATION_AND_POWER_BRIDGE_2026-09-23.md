# Energy R2 reconciliation and first R3 power-contract bridge

**Date:** 2026-09-23. **Owner:** Sol. **Operation:** `gmi-energy-sector-research-20260923-sol-001`. **Carrier:** Macro PR #7791, branch `sol/energy-sector-research-20260923`.

Research-only continuation after the R2 core was written. This supplement narrows two stated R2 gaps and establishes the first power-sector commercial case. It does not replace the R2 model, create another current-state owner, admit production evidence or issue a Fable handoff. The cumulative Agent OS checkpoint remains the continuation owner.

## 1. Exact supersession: EOG hedge-table chronology

R2 gap G04 described an unresolved question about a quarter-end report containing later closed periods. A bounded read of the table's introduction resolves the date: it covers contracts settled from January 1 through July 24, 2026 and outstanding as of July 24. The June 30 financial-statement date is not the table's observation date. [P01]

**Superseded:** the claim that the table's source as-of/closed-period chronology remains unresolved.

**Still unresolved:** exact current September exposure, later transactions, the matching forecast production denominator, basis/contract overlap and effective delta. The July 24 book is not a September 23 hedge certificate. Do not compute a current coverage ratio by dividing it by an unrelated quarter's production.

This was a research-context omission, not a demonstrated contradiction in the source. The proper repair is to preserve the explicit table date and the narrower remaining uncertainty. The original R2 artifact and its checked byte identity remain historical evidence; this supplement governs the newly resolved sub-question.

## 2. Exact supersession: EQT/CPV commencement event

CPV's August 12 announcement states that its ten-year Shay gas arrangement begins at the plant's commercial operation and is intended to cover the plant's anticipated gas burn. This supplies a commencement condition that was absent from the R2 source set. The announcement describes 2,100 MW. [P02]

The project page, read on September 23, labels Shay in development and gives an estimated 2027 construction start. Its headline/project description uses approximately 2,100 MW while its FAQ also contains approximately 2,060 MW. Retain that source-local discrepancy rather than silently inventing a precisely reconciled capacity. Publication/update time for the mutable project page was not established. [P03]

**Superseded:** the missing commencement-event portion of R2 gap G05.

**Still unresolved:** a verified calendar commercial-operation date, full pricing formula, guarantees/credit support, actual financing/construction milestones, net economics to each counterparty and actual supply receipts. The secondary 2031 timing claim surfaced in search is not adopted without a suitable primary source. A construction-start target is not a generation-start date.

R2's `start_date: null`, `current_deliveries: null` and `incremental_cashflow: null` remain correct for exact calendar/delivery/earnings fields. A future native representation should add the separately sourced commencement event rather than filling those nulls with an invented date or zero value.

## 3. Identity guard: EQT Corporation is not a name-only join to EQT Infrastructure VII

The July 10 Copia announcement identifies the acquirer as EQT Infrastructure VII. An external aggregated story surfaced under a NYSE:EQT/EQT Corporation URL and described the deal as an EQT Corp acquisition. The issuer-authored release, not that ticker tag, determines the named transaction party. [P04, P05]

This is an external data-quality example, not a claim that Mastermind's live identity system made the same error. Do not create a Copia ownership relationship for the gas producer from this story. Canonical issuer/security resolution belongs to the existing identity owner; no new identifier is minted here. The transaction announcement itself also must not be promoted into evidence that closing occurred.

The reusable research lesson is to resolve the legal party and security before scoring economic relevance. A plausible sector narrative is not a substitute for identity. This matters particularly when an AI/power story appears to corroborate a gas producer's separate, genuine power-linked contract.

## 4. Power-linked gas changes who captures a power-price improvement

The following is original analysis, not a reconstruction of the undisclosed CPV/EQT formula.

A generator using fixed-index gas has one sensitivity to electricity prices; a generator paying a gas supplier a share of power-linked economics has another. To identify the beneficiary, the research must follow the contract on both sides. Adding the supplier's full modeled benefit to an unchanged generator benefit can double count the same economic surplus.

### Transparent hypothetical

Assume a plant heat rate of 7 MMBtu/MWh and a gas contract price equal to 60% of the power price divided by that heat rate. Ignore start-up cost, transport, emissions, fixed costs, taxes, capacity payments and financing. This 60% share is invented solely for the illustration; no source establishes it for CPV or EQT.

At a power price of $50/MWh, hypothetical gas price is $4.285714/MMBtu, fuel cost is $30/MWh, and the plant retains $20/MWh before all other costs. At $80/MWh, gas price becomes $6.857143/MMBtu, fuel cost $48/MWh, and retained contribution $32/MWh.

Of the $30/MWh increase in power revenue, $18/MWh goes into the gas payment and $12/MWh remains at the plant before other costs. The gas producer's incremental payment is not its incremental profit: its own production, transport, hedge and investment costs still matter. Contract floors, caps, dispatch obligations and alternative index elections would alter the result.

This is why R3 must model regional electricity prices, gas basis, heat rate, contract formula and dispatch together. A broad label such as 'AI electricity beneficiary' cannot identify the actual cash recipient.

## 5. Future value can change before current earnings

The rule against claiming current delivery from a signed contract is not a rule that the contract has no present economic value. The purpose of the research is partly to identify meaningful changes before they appear in reported earnings, while being honest about what is conditional.

A contract may clarify future pricing or customer commitment. Financing, construction progress and commissioning may each resolve a different uncertainty. Their valuation relevance depends on what was already expected, what obligations the issuer assumes and how much attributable cash remains after required investment. No operational receipt is needed to discuss a future scenario; an operational receipt is needed to claim operations have begun.

A simple timing illustration helps. The R2 hypothetical stream of 100 at the end of each of years one through five has present value 379.078676941 at 10%. Delaying the entire stream by one year, with no other change, reduces that value to 344.616979037, a 9.090909% decrease. This is not an estimate for Shay, and real delays may also change costs, contracted revenues and financing. It shows that timing can matter even when eventual output is unchanged.

Do not assign a guessed completion probability, contract premium or target multiple. Instead, present the conditional paths, the evidence newly available and the missing terms. Point-in-time expectations and valuation data remain required before asserting that the security has become mispriced.

## 6. R3 comparative framework established by this case

The next full tranche should apply the same dated demand scenario to different economic recipients rather than treating all power spending as one theme.

| Recipient | Contract/economic question | Earliest evidence that may change a future estimate | What does not yet prove cash |
|---|---|---|---|
| Gas producer | Who controls pricing, how much volume, at which delivery point and start event? | Executed supply terms, credible demand commitment, improved market access | A project announcement or gas notional alone |
| Merchant generator | What power margin remains after fuel/index sharing, hedges, dispatch and fixed costs? | Contract terms, capacity/energy exposure, actual project progress | Nameplate MW or a regional demand forecast alone |
| Regulated utility | What investment and costs can be recovered, when, and with what financing? | Specific approved recovery and funded implementation milestones | A requested return or corporate capex plan alone |
| Equipment supplier | Which binding orders convert at an attractive margin and require what expansion? | Order terms, pricing, production slots, cost-to-complete and collections | Reservations or project capacity alone |

Keep three distinct questions on the eventual page: **Is the underlying demand credible? Can this business capture attractive economics? What does the current security price already assume?** A positive answer to one is not an answer to the others.

## 7. Additional proposed acceptance cases

These are eight specification cases, not executed application tests. They supplement rather than renumber R2 A01–A36.

1. Preserve an explicit July 24 observation inside a June 30 filing; do not erase the table-specific date.
2. Closing that date question must not fabricate a current hedge-coverage ratio.
3. Represent commercial operation as a commencement event when its exact calendar date is unknown.
4. Never substitute estimated construction start for commercial-operation start.
5. Retain the project page's source-local capacity discrepancy and unknown update time.
6. Reject a name-only Copia/EQT Infrastructure VII to NYSE:EQT issuer join.
7. Do not double count shared power-price economics across gas supplier and generator.
8. Allow conditional future-value research without relabeling it current revenue, a validated forecast or trade authority.

## 8. Boundaries and next action

R2 has seven issuer dossiers and a validated research-input identity. This supplement records additional primary evidence, two narrowed gaps and the commercial framework for R3; it is not the full R3 merchant/utility/equipment study. All ranking, entry, sizing, trading and native-ingestion authority remains false. No product code, canonical identity, live evidence, publisher or runtime state changes are made.

The exact next action is to extend this now-established CPV/EQT framework into the existing Vistra, Duke and GE Vernova seeds, with regional markets, hedge/contract vintages, recovery and financing, binding orders and attributable cash. Do not repeat the source-date or commencement-event investigations just resolved here. Fable remains the later build orchestrator after the principal research/design package is accepted.

## Sources

P01 — EOG Q2 filing, introduction to financial commodity derivative tables, observation date July 24, 2026: https://www.sec.gov/Archives/edgar/data/821189/000082118926000149/eog-20260630.htm

P02 — CPV, August 12, 2026, original gas-netback announcement: https://cpv.com/2026/08/12/cpv-secures-10-year-gas-netback-with-eqt-to-supply-2-gw-cpv-shay-energy-center/

P03 — CPV Shay project page, read September 23, 2026; update time unknown: https://cpv.com/our-fleet/cpv-shay-energy-center/

P04 — EQT Infrastructure VII issuer-authored July 10, 2026 announcement, distributed by PR Newswire: https://www.prnewswire.com/news-releases/eqt-to-acquire-copia-power-a-leading-integrated-power-and-ai-infrastructure-platform-302822622.html

P05 — External aggregated story, used only as evidence of the observed wrong ticker/party attribution, not as truth about acquisition ownership: https://deepscope.com/news/NYSE%3AEQT%3Aeqt-corporation%3Aeqt-to-acquire-ai-infrastructure-platform-copia-power-from-carlyle/

Only authored paraphrases, conditional analysis and locators are retained. Public accessibility does not establish production retention or redistribution rights. The external error example grants no authority to alter a production identity record.
