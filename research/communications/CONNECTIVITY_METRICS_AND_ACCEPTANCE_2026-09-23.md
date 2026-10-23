# Communications Phase 5 — Connectivity Metrics and Acceptance Requirements

**Operation:** `gmi-communications-research-20260923-sol-001`. **Carrier:** Macro PR #7794.
**Status:** Proposed research definitions and future acceptance requirements. No production schema, live metrics, implementation tests or investment authority are created.

Read with `TERRESTRIAL_CONNECTIVITY_RESEARCH_2026-09-23.md`. Bracketed references resolve to its public primary-source register. Amounts are in the native issuer currency and stated unit. Current examples are for Q2 2026 unless a guidance or prior-period comparison explicitly says otherwise. Distinct arithmetic methods check the same transcribed inputs; this is not an independent audit of the filings.

## 1. Thirty proposed metric contracts

Each measure requires issuer/business identity, source locator, unit and population, reporting period, publication/knowledge time, observation time, revision and comparison basis. Unknown exposure or unobserved values remain unavailable, never zero. These are diligence requirements to map into existing owners, not a parallel metric registry.

| ID | Measure | Required scope | Failure to prevent |
|---|---|---|---|
| NM01 | Relationship identity | Issuer, business, account/line/household and source scope | Ticker-only or phone/IoT/account equivalence |
| NM02 | Organic net additions | Gross adds, exits, acquisitions and administrative changes | An acquired base or relabeled account treated as demand |
| NM03 | Average service base | Monthly/quarterly average eligible relationships | Period-end stock used for a revenue denominator |
| NM04 | ARPU and ARPA | Product/plan, included services, credits, tax/currency and time | Account revenue compared with phone-line revenue |
| NM05 | Effective price | Cash/recognized price net of discount and bundle allocation | Published plan price assumed fully realized |
| NM06 | Churn and survival | Monthly/annual, voluntary/involuntary, eligibility and reactivation | Summing monthly hazards to claim annual cohort survival |
| NM07 | Acquisition cost | Device subsidy, commission, installation and expense/cash timing | Capitalized expense or handset revenue concealing cost |
| NM08 | Retention cost | Renewal offers, upgrades and support, matched cohort | All discount cost called growth investment |
| NM09 | Household contribution | All products, incremental costs and alternative outcome | Lower selected-cohort churn called proven bundle causality |
| NM10 | Convergence | Numerator, eligible product population and matching method | AT&T home connections compared with Comcast addressable lines |
| NM11 | Availability | Geography, technology, serviceability and observation vintage | Coverage called paying adoption |
| NM12 | Passing/build cohort | Construction vintage, owned/partner network and serviceability | A press-release reach figure called owned plant |
| NM13 | Penetration | Connected eligible customers over same cohort/footprint | Current-quarter additions divided by new passings |
| NM14 | Activation cost and delay | Initial passing cost separated from connection and time-to-cash | Installation interval disappears from NPV |
| NM15 | Capacity utilization | Location/time, busy-hour demand, spectrum and backhaul | National average speed interpreted as spare local capacity |
| NM16 | FWA incremental value | Marginal contribution, incremental costs and displaced use | All network capacity treated as free forever |
| NM17 | Legacy exit costs | Migrated customers, remaining obligations and shutdown milestone | Revenue run-off treated as completed cost removal |
| NM18 | Service/equipment mix | Product basis, subsidies and recognition policy | Equipment decline called equal recurring-service deterioration |
| NM19 | Wholesale/MVNO economics | Payer, host, reseller, retained fee and intercompany basis | Retail and host activity counted as independent households |
| NM20 | JV and partner exposure | Equity percentage, customer ownership, access contract and funding | Off-balance-sheet plant assumed capital-free |
| NM21 | Reported CFO | Accounting regime, operating perimeter and actual cash lines | Adjusted EBITDA less capex relabeled reported operating cash |
| NM22 | Capital investment | Cash capex, vendor financing, equipment, scope and timing | Capex-only measure omits financing-classified network payments |
| NM23 | Lease cash and liability | Principal, interest, starting cash measure and debt convention | Principal deducted twice or lease debt paired incoherently |
| NM24 | Spectrum and commitments | Paid, contracted and conditional obligations separately | Announced transaction treated as paid/completed |
| NM25 | Non-GAAP FCF | Versioned full reconciliation and native exclusions | Company-defined figures compared by name only |
| NM26 | Tax/working-capital quality | Period, timing effects and original/revised cash measures | Tax cash relief extrapolated as permanent margin improvement |
| NM27 | Net claims and distributions | Debt, cash, preferred/NCI, pensions and minority cash entitlements | A partner sale lowers debt while its future claim is ignored |
| NM28 | Per-share economics | Attributable numerator and executed diluted share changes | Repurchase authorization or DRIP treated as zero dilution |
| NM29 | Guidance and expectations | Original/latest event time, same horizon/basis, consensus separate | Prior revision republished in release called a new surprise |
| NM30 | Data rights and coverage | License, geography, observation/publication/revision clocks | Public page date launders old estimates or restricted subscriber data |

## 2. Thirty primary-input arithmetic examples

Research-derived values use six-decimal display precision solely for reproducibility. This is not a claim that source data or forecasts have that accuracy. Exact whole-number bridges use the reported or rounded inputs explicitly described; percentage reconstructions may differ slightly from an issuer's rounded percentage.

| ID / source | Operation | Result | Unit and interpretation |
|---|---|---:|---|
| NC01 [AT1] | `367+279+432` | 1078.000000 | thousand service additions; Not unique households |
| NC02 [AT1] | `5700+400` | 6100.000000 | USD million; Capex plus cash vendor financing, rounded inputs |
| NC03 [AT1] | `10800-5700-400` | 4700.000000 | USD million; Current-quarter company FCF bridge; not a universal formula |
| NC04 [TM1] | `34439+277-16` | 34700.000000 | thousand accounts; Separate reported organic additions and base adjustment |
| NC05 [TM1] | `(152.91/149.87-1)*100` | 2.028425 | percent; Account revenue, not phone ARPU |
| NC06 [TM1] | `(277/318-1)*100` | -12.893082 | percent; Net-account-addition change, not subscriber stock decline |
| NC07 [TM1] | `7500-2703` | 4797.000000 | USD million; Company cash measure in this reporting period |
| NC08 [CH1] | `5776-5969` | -193.000000 | USD million; Residential internet revenue change |
| NC09 [CH1] | `1095-921` | 174.000000 | USD million; Residential mobile service revenue change |
| NC10 [CH1] | `(5776+1095)-(5969+921)` | -19.000000 | USD million; Combined connectivity change; not profit |
| NC11 [CH1] | `174/193*100` | 90.155440 | percent; Revenue-offset illustration; no margin or household equivalence |
| NC12 [BC1] | `(2162/1947-1)*100` | 11.042630 | percent; CFO change, not earnings change |
| NC13 [BC1] | `(1080/763-1)*100` | 41.546527 | percent; Capex change includes new investment/perimeter |
| NC14 [BC1] | `(1042/1152-1)*100` | -9.548611 | percent; Reported company FCF change |
| NC15 [BC1] | `2162-1080-36-12+8` | 1042.000000 | CAD million; Company FCF includes preferred/NCI distributions and adjustment |
| NC16 [BC1] | `1042-258` | 784.000000 | CAD million; FCF after lease-liability principal |
| NC17 [BC1] | `1152-278` | 874.000000 | CAD million; Prior-year FCF after lease liabilities |
| NC18 [BC1] | `(2100+2300)/2-(3300+3500)/2` | -1200.000000 | CAD million; March versus February guide midpoint; not new Q2 revision |
| NC19 [BC1] | `(((2100+2300)/2)/((3300+3500)/2)-1)*100` | -35.294118 | percent; Original/updated midpoint comparison; not consensus surprise |
| NC20 [TU1] | `1342-678-100+10+30-59` | 545.000000 | CAD million; Full scoped company bridge, not CFO less capex alone |
| NC21 [TU1] | `(1342/1166-1)*100` | 15.094340 | percent; CFO change |
| NC22 [TU1] | `(545/535-1)*100` | 1.869159 | percent; Company FCF change |
| NC23 [TU1] | `143-12` | 131.000000 | CAD million; Lower quarterly tax cash payment, not independent earnings growth |
| NC24 [TU1] | `176-100` | 76.000000 | CAD million; Lower non-discretionary lease principal |
| NC25 [TU1] | `0.1875*4` | 0.750000 | CAD/share annualized; Announced distribution; not total expected shareholder return |
| NC26 [RC1] | `1517-695-494+456+211-33+160-117+12-18-16-1` | 982.000000 | CAD million; Company reconciliation contains scoped adjustments |
| NC27 [RC1] | `(1517/1596-1)*100` | -4.949875 | percent; CFO change |
| NC28 [RC1] | `(982/925-1)*100` | 6.162162 | percent; Company-defined FCF change |
| NC29 [RC1] | `1313/1990*100` | 65.979899 | percent; Service-revenue EBITDA margin; rounds to reported 66.0% |
| NC30 [RC1] | `1313/2540*100` | 51.692913 | percent; Research total-revenue ratio; not issuer quoted margin |

Cash bridge details: NC15 subtracts BCE capex, preferred dividends and NCI distributions and adds the source's acquisition/other-cost adjustment. NC20 subtracts TELUS capex and lease principal and applies its real-estate, other and working-capital reconciling amounts. NC26 follows Rogers' disclosed interest, restructuring/acquisition, program-rights, working-capital, NCI, derivative, pension, other cash and investment-income adjustments in their published order. Do not generalize these formulas to another issuer or period without re-reading that source's definition.

NC18–19 compare the dated February and March guidance ranges shown in BCE's Q2 report. They do not claim that the August publication originated a new reduction. NC29 rounds to the source's 66.0%; NC30 is a separately labeled research ratio, not a correction of the issuer's declared service-revenue margin.

## 3. Twelve synthetic economic illustrations

All inputs below are invented teaching assumptions. They are not observed industry rates, underwriting assumptions, validated coefficients, or company valuations. Cases test an analytical distinction; they do not test application behavior.

| ID | Operation | Result | Assumption and purpose |
|---|---|---:|---|
| NI01 | `100*(1-0.01)**12` | 88.638487 | Year-end survivors per 100 initial customers; constant 1% monthly exit, no reactivation |
| NI02 | `100*(1-0.01*12)` | 88.000000 | Linear approximation, intentionally different from survival calculation |
| NI03 | `500/1000*100` | 50.000000 | Mature cohort penetration |
| NI04 | `(500+100)/(1000+1000)*100` | 30.000000 | Aggregate penetration falls with new build even if mature cohort unchanged |
| NI05 | `-1000+160*(1-(1.10)**(-10))/0.10` | -16.869263 | Ten-year end-year contribution NPV, no residual, assumptions only |
| NI06 | `-1000+180*(1-(1.10)**(-10))/0.10` | 106.022079 | Higher contribution assumption reverses NPV sign |
| NI07 | `-1000+(180*(1-(1.10)**(-10))/0.10)/1.10` | 5.474617 | Same ten cash payments delayed one year, initial cost unchanged |
| NI08 | `1000/((1-(1.10)**(-10))/0.10)` | 162.745395 | Break-even annual contribution under the same ten-year assumptions |
| NI09 | `40-8-10-25` | -3.000000 | Hypothetical FWA gross contribution less service, capacity and displaced use |
| NI10 | `(90-60)/(100-60)*100-100` | -25.000000 | Equity sensitivity to 10% EV decline at fixed claims of 60 |
| NI11 | `100-(45+10+25+20)` | 0.000000 | Cash allocation conservation: network, support, distribution, retained economics |
| NI12 | `50-(30+15+10)` | -5.000000 | Bundle contribution versus household alternative; five-unit cannibalization |

The NPV cases use ten end-year payments, a 1000 initial outflow, a 10% annual discount rate and no residual value. NI07 moves those same ten payments one year later without delaying the initial outflow. They deliberately omit tax, connection timing, financing and maintenance complexities that a real case would require. The purpose is sensitivity and model-boundary discipline, not an investment conclusion.

The survival illustration is not a forecast from reported aggregate churn. Reactivations, price changes and heterogeneous customer behavior would require richer cohorts. The bundle and FWA illustrations require a valid counterfactual before their numerical form could support a real economic conclusion.

## 4. Thirty-two proposed adversarial acceptance cases

Every case is a written requirement, not an executed product PASS. Fable's eventual implementation packet must map applicable cases to the existing consumer, evidence and calculation owners, with real-path inputs and negative/missing states. No extra control plane is required.

| ID | Challenge | Input/trigger | Required behavior |
|---|---|---|---|
| NA01 | Account growth | 34.439m starting accounts plus 277k organic and -16k adjustment | Show 34.700m; administrative effect separate from churn |
| NA02 | Unique customer claim | Internet and phone additions can overlap | Show service additions; no unsupported unique-household total |
| NA03 | Device mixture | IoT and phones both increase | Preserve categories; no inherited phone ARPU |
| NA04 | ARPU denominator | Account and phone measures share a label | Withhold like-for-like ranking; show definitions |
| NA05 | Convergence denominator | Two incompatible eligible populations | Explain scope split, not a 35.5-point competitor advantage |
| NA06 | Fiber scope | Owned and partner locations combined | Expose ownership basis; no wholly-owned assertion |
| NA07 | Cohort dilution | Mature 50% plus newly built 10% penetration | Show 30% aggregate without claiming mature-cohort decline |
| NA08 | Unmatched build/adds | New passings and customer additions from different cohorts | No invented conversion ratio |
| NA09 | FWA reach | Broad radio coverage but address admission unknown | Availability unknown at household grain; no unlimited capacity |
| NA10 | Network tradeoff | Hypothesis about displaced mobile economics | Scenario label, not measured opportunity cost |
| NA11 | Promotion cohort | Lower churn among self-selected bundled customers | No causal treatment verdict without identification |
| NA12 | Acquired revenue | Frontier/Ziply added to consolidated figures | Preserve acquired scope; no residual organic label without bridge |
| NA13 | Cash vendor financing | AT&T capex excludes a network cash payment | Use explicit 6.1bn investment / 4.7bn FCF at rounded inputs |
| NA14 | Lease bridge | BCE provides both FCF and after-lease FCF | Keep 1042 and 784 distinct; do not deduct 258 twice |
| NA15 | Adjusted CFO confusion | Rogers non-GAAP FCF improves while CFO falls | Show both with full formula; no hidden definition substitution |
| NA16 | Denominator margin | Rogers 66% service margin compared with total-revenue margins | Reconcile 1313/1990 versus 1313/2540 and label |
| NA17 | Tax relief | TELUS lower cash tax improves cash bridge | Do not emit an independent operating-efficiency signal |
| NA18 | Partner claims | Consolidated assets with NCI distributions | Retain minority claims and cash; no free deleveraging |
| NA19 | JV funding | Retailer pays wholesale and equity contributions | Explain both channels without double-counting enterprise cash |
| NA20 | Pending ownership | Agreement subject to closing | Announced status, not current owned asset/member assignment |
| NA21 | Legacy shutdown | Customer run-off precedes geographic decommissioning | Forecast versus achieved saving explicit |
| NA22 | Distribution safety | Positive FCF but payout reset announced | Do not infer old payout is safe or new stock is attractive |
| NA23 | Ticker collision | NYSE:T and TSX:T | Existing exact security identities; no merged issuer record |
| NA24 | Expectation vintage | BCE March change repeated in August report | Original March event clock; no new August revision |
| NA25 | Forecast versus consensus | Company raises guide with no verified consensus vintage | Company-guidance change only, no beat/miss |
| NA26 | Mixed public clocks | Current CRTC page has Q1 and annual observations | Separate time/coverage per field, no unified fresh Q2 stamp |
| NA27 | Rights restriction | Availability public, enriched Fabric/subscriptions restricted | No unauthorized enrichment; keep useful public aggregate data |
| NA28 | Historical survivorship | Restructuring/delisted or acquired operator missing | Report incomplete cohort; do not claim validated full-history edge |
| NA29 | Cash/valuation double count | After-interest cash with another interest deduction | Refuse inconsistent bridge and retain input evidence |
| NA30 | Research/trade boundary | Positive descriptive network thesis | No new Prophet rank, size or trade instruction |
| NA31 | Publication/privacy | Private source in paid dossier | Use incumbent approved access path; no public full-fidelity copy |
| NA32 | Investor completion | User starts from theme and examines evidence | Reach existing company/watchlist route with coherent scope and missing states |

## 5. Ten candidate subtheme mechanisms for economic exposure mapping

These local research identifiers are not admitted canonical themes or basket membership. Each row states a possible earnings mechanism and the evidence needed to investigate it. Current issuer anchors locate relevant disclosures, not a list of recommended beneficiaries. Exposure magnitude remains undisclosed or unmodeled unless the source itself supplies it.

| Research ID / candidate mechanism | Source-bound business anchors | What would make the economics improve | Disconfirming evidence or missing qualification |
|---|---|---|---|
| NH01 Premium-plan realization | AT&T wireless; Verizon Consumer; T-Mobile postpaid [AT1,VZ2,TM1] | Retained service contribution rises after credits, subsidies and churn | Promotions or acquisition mix explain growth; payer cohorts not comparable |
| NH02 Fixed-mobile household retention | AT&T advanced home; Charter/Comcast convergence [AT1,CH1,CM1] | Incremental household survival value exceeds cross-sell discount and service cost | Selected customers would have stayed anyway; cheaper bundle cannibalizes receipts |
| NH03 Fiber cohort maturation | BCE/Ziply; AT&T owned/partner footprints [BC1,AT1] | Same build cohorts connect and retain customers fast enough to earn construction cost | Aggregate penetration obscures vintages; remaining activation cost consumes value |
| NH04 Residual radio-capacity monetization | Operator FWA disclosures and dated T-Mobile capacity methodology [AT1,VZ1,FW1] | Incremental broadband contribution exceeds added capacity cost and displaced mobile value | Busy-hour congestion, admission limits or reinvestment overwhelm apparent low capex |
| NH05 Cable revenue replacement | Charter residential internet/mobile; Comcast domestic convergence [CH1,CM1] | Combined retained relationship contribution stabilizes despite legacy/product losses | Mobile revenue grows but household contribution falls or wholesale costs rise |
| NH06 Legacy fixed-cost release | AT&T legacy migration [AT1] | Verified geographic closure actually removes cost after customer migration | Remaining customers keep network costs alive; timing exceeds the model horizon |
| NH07 Retail/infrastructure partnership | T-Mobile fiber JVs; AT&T partner reach [TM2,AT1] | Better capital productivity after access fees, equity funding and minority claims | Capex moves outside consolidation without lower total economic cost |
| NH08 AI infrastructure capital productivity | BCE AI Fabric; TELUS infrastructure investment [BC1,TU1] | Funded capacity attracts economically adequate contracted utilization | Near-term cash demand increases without verified utilization, pricing or project returns |
| NH09 Canadian challenger expansion | Quebecor telecom/mobile versus incumbent source scopes [QB1,BC1,RC1,TU1] | Retained contribution grows after integration, acquisition and network costs | Footprint/mix changes explain apparent advantage; no matched competitor cohort |
| NH10 Cash retention and financing resilience | Issuer cash/claim disclosures; Frontier historical contrast [AT1,TM2,BC1,TU1,RC1,H1] | Matched-horizon recurring cash covers necessary reinvestment and claims with lower refinancing risk | Temporary tax/working-capital relief, pending disposals or new obligations dominate |

Each future exposure record should bind business, role, geography, financial line, time horizon, magnitude basis and source to the existing GMI/evidence contracts. A direct operational sensitivity is not the same as a stock-price sensitivity. Review candidate overlap before creating any new canonical concept; use a narrower assertion under an existing concept where appropriate. Do not sum exposures that describe the same cash stream.

## 6. Validation scope and handoff boundary

The companion's 30 primary-input examples and 12 synthetic illustrations were checked using Decimal and exact Fraction arithmetic. Whole-number bridges also match the expressly recorded expected values. Source-ID resolution and complete metric/case sequences are checked locally. These methods verify arithmetic and document structure, not the correctness of every transcription, causal interpretation, live source feed or production behavior.

No full repository validator, CI acceptance, original-vintage backtest, application test or browser proof was executed for this chapter. No design approval or Fable receiver is implied. Public portable JSON exports reproduce these research examples; the owning research remains this existing PR. Current cumulative continuation belongs at `agentos/handoffs/GMI-COMMUNICATIONS-RESEARCH-2026-09-23.md`.
