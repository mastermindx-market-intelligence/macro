# WP02 selection-policy adjudication memo

**Status: RECOMMENDED_NOT_ADOPTED. No 120-issuer selection was made.**

**Recommendation:** adopt jurisdiction-and-activity-relative size slots for this source diagnostic, and retain absolute USD size bands as a mandatory companion field. Keep every accepted count: 120 issuers; five primary-listing strata of 24; six activity groups with four issuers each; two L, one M and one S in each stratum/group; and eight UK, eight Japan and eight EU issuers within INT. Use the exact policy in `RECOMMENDED_SELECTION_POLICY.json`. A relative L slot must be displayed as **relative upper-half**, not as proof of global large-cap status.

This resolves the missing *method choices*. It does not cure the measured missing international frame, establish data rights, classify an actual issuer, or authorize a selector run. The frozen WP02 frame assessment remains the factual account of the inspected estate. Its 21 files are preserved; its principal report SHA-256 is `9ab4ef6dcb81eb0a3185269a851f22d315a2ff45c0be5c67dfb154efa4cfc1e0`.

## 1. What remains law, and what is proposed

The accepted WP02 design is recorded at Macro source revision `4d736c55adb630a4a8eb11b261e31acd0f6dc48b` in [IMPLEMENTATION_MASTERPLAN.md, WP02](https://github.com/mastermindx-market-intelligence/macro/blob/4d736c55adb630a4a8eb11b261e31acd0f6dc48b/research/theme_graph/economic_network_20261008/IMPLEMENTATION_MASTERPLAN.md) and [SOURCING_AND_COMPETITIVE_DILIGENCE.md, §6](https://github.com/mastermindx-market-intelligence/macro/blob/4d736c55adb630a4a8eb11b261e31acd0f6dc48b/research/theme_graph/economic_network_20261008/SOURCING_AND_COMPETITIVE_DILIGENCE.md). The earlier fixed-reference audit measured those requirements; this lane did not obtain a new repository revision.

| Requirement | Preserved |
|---|---|
| Geographic strata | US, mainland China, Hong Kong, Canada, INT; assignment follows primary listing |
| Issuers | 24 per stratum; 120 total; one economic issuer across its dual listings |
| Activity groups | Semiconductor/cloud, industrials, consumer, energy/materials, financials, healthcare |
| Within each stratum/activity | Four issuers: two L, one M, one S |
| Total size slots | 60 L, 30 M, 30 S |
| INT intersection | Eight UK, eight Japan, eight EU, simultaneously with the activity/size quotas |
| Source periods | Annual fiscal labels 2023–2025 and latest actually available 2026 interim/material-event documents |
| Difficult cases | At least 30, at least six per geographic stratum, with independent adjudication |
| Sequence | Freeze policy/frame/cohort and manual evidence annotations before relationship-vendor outputs |
| Unknowns and failures | Preserve missing identity, anonymous disclosure, source failure, refusal and unavailability |

The accepted text does not supply numeric capitalization boundaries, a complete sector crosswalk, valuation/share-count conventions or deterministic tie law. The recommendation therefore makes three **explicit, unadopted semantic choices**:

| Proposed adoption | Exact consequence | What it does not do |
|---|---|---|
| A01: relative size meaning | Use the upper-half/next-quarter/lower-quarter count bands described below, with positive-valued microcaps eligible and absolute tags visible | Does not silently preserve the ordinary meaning of global large/mid/small cap |
| A02: activity and instrument perimeter | Use the six-group evidence rules, a narrow external IaaS/PaaS operator definition for cloud, and public operating-equity/growth-market perimeter | Does not establish a company's sector, venue status or source entitlement |
| A03: reference valuation and clocks | Use reported-share reference capitalization at 30 September 2026, a 9 October public-information cutoff, and an actual later evidence freeze | Does not claim exact unobserved shares at month-end or historical native availability |

**No reduction or redistribution of the 120 quotas is proposed.** If a complete frame cannot satisfy them, publish the actual shortfall. If the principal rejects relative size semantics, the fully specified absolute alternative below is available for explicit adoption; no automatic fallback is allowed.

## 2. Why the recommendation is relative, with an absolute companion

The purpose of this exercise is to diagnose source access, identity joins, relationship evidence, disclosure limitations and revision handling across markets and activities. Equal country and activity counts already make it a designed diagnostic, rather than a capitalization-weighted description of global listed equity. Relative size slots make that objective explicit: they seek variation *within each relevant source environment*.

A fixed USD value answers a different question: whether companies in different markets have comparable equity valuations. That comparison is valuable, so the recommendation preserves both the unrounded USD reference value and a fixed absolute-band tag. It does not let a small absolute company acquire global-large status through a local rank.

### The official methodologies do not establish a universal size law

FINRA's investor-education page, dated 30 September 2022 and still served when read on 9 October 2026, explicitly presents variable conventions. Its example bands distinguish micro below USD250 million, small between USD250 million and USD2 billion, mid between USD2 billion and USD10 billion, large up to USD200 billion and mega above that level. This policy chooses nonoverlapping boundary treatment and merges mega into the absolute L slot. [P01](https://www.finra.org/investors/insights/market-cap)

The live S&P US methodology article's Download linked to a **July 2026** PDF when checked. Its company-level addition thresholds were USD22.7 billion for S&P500, USD8.0–22.7 billion for MidCap400 and USD1.2–8.0 billion for SmallCap600. It describes periodic threshold review and separate float requirements. These are index-entry rules, not a reliable way to infer a current numeric bucket merely from membership in an existing Data OS universe group. [P02](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-indices.pdf), pp.8–9

MSCI's May 2026 full methodology ranks companies by full capitalization while using cumulative free-float capitalization coverage and global size bounds. Its initial large/standard/IMI coverage targets are 70%/85%/99%; global size integrity may take priority over local coverage. The July summary, linked from its current methodology page, confirms the coverage-and-size architecture. **The proposed issuer-count bands are not an implementation of MSCI methodology.** The live latest full-document route failed, so this finding is bound to the dated full document and current-linked summary, not a claimed hash of the latest PDF. [P03](https://www.msci.com/eqb/methodology/meth_docs/MSCI_GIMIMethodology_May2026.pdf), §2.3.3–2.3.4; [P04](https://www.msci.com/eqb/methodology/meth_docs/MSCI_Jul26_GIMIMethod_Summary.pdf)

| Method | Concrete definition | Main advantage | Main failure mode | Decision |
|---|---|---|---|---|
| Global absolute USD | S:250m≤V<2b; M:2b≤V<10b; L:V≥10b; micro excluded from these quotas | Same dollar-size meaning across markets | A thin sector may not contain two L issuers; missing cells cannot be rescued by index labels | Retain as fully specified alternative and descriptive companion |
| Relative within jurisdiction, all six activities pooled | Same 50/25/25 count split, ignoring activity when assigning size | Local-market interpretation | A sector concentrated at one end of its market may still have empty size cells; unrelated sector composition changes its labels | Do not use |
| Relative within jurisdiction and activity | The exact order-statistic rule in §3 | Matches the source-environment diagnostic and quota purpose | Locally upper-half firms can be globally micro; complete denominators cost more to source | **Recommend, subject to explicit semantic adoption** |
| MSCI-style coverage/global bounds | Full-cap ordering, free-float coverage, global limits and maintenance rules | Designed for investable market representation | More dependencies and licensing questions; no guarantee of the diagnostic's sector counts | Do not reproduce for WP02 |

This recommendation must be rejected if the principal's intended headline claim is “equal global dollar size across countries.” It must also be rejected if a complete rank frame cannot be assembled lawfully. Relative ranks computed only from available cap rows would otherwise convert data missingness into a hidden selection criterion.

## 3. Exact numeric boundaries and missing-data law

There are **42 reference pools**: seven primary-listing jurisdiction groups—US, CN_MAINLAND, HK, CA, UK, JP and EU—times six activities. UK, Japan and EU are ranked separately before their candidates enter the INT constraint solver. EU is one specified regional pool, not a claim that its countries constitute one exchange market. There is no additional requirement to select four issuers in each INT country/activity.

For a complete eligible pool of N issuers, order their exact, unrounded reference USD values in descending order:

- k1 = ceiling(N/2)
- k2 = ceiling(3N/4)
- t1 = capitalization at ordinal k1
- t2 = capitalization at ordinal k2
- L: V ≥ t1
- M: t2 ≤ V < t1
- S: 0 < V < t2

An empty pool has no bands. Identical capitalization values are **never split by ticker or hash into different sizes**: the whole tied block goes into the higher applicable band. This can empty a lower band and make the design infeasible. Hashes choose issuers *within* a band; they do not manufacture a valuation distinction.

The 50/25/25 count split is a research design choice aligned with the accepted 2/1/1 sampling ratio. It is not an estimate of the market's capitalization distribution. With four strictly ordered values it yields 2/1/1; with five it yields 3/1/1, from which two of the upper three are selected. With fewer than four issuers, a non-INT activity quota is impossible. Small INT country/activity pools may still supply some bands; the joint solver determines whether other country pools complete the required totals.

**Illustration only:** a synthetic five-issuer pool valued at USD900m,800m,700m,600m,500m produces three L-relative, one M-relative and one S-relative issuers, although every issuer has an absolute S tag. This illustrates the proposed semantics; these values and issuers are not observations or a Canadian cohort.

The reference denominator is every eligible economic issuer in the **frozen declared perimeter**, not the four selected issuers, an ETF's holdings, the rows a vendor happened to return, or the nonmissing subset. Every source-directory row must resolve to an eligible unique issuer or an evidenced exclusion. An unresolved row that could belong to a pool prevents a completeness assertion for that pool. A known eligible issuer with a missing cap produces `CAP_FRAME_INCOMPLETE`; it cannot be dropped and the remainder called market-relative ranks.

Absolute tags use the same reference-cap measure:

| Tag | Exact USD interval |
|---|---|
| MICRO | 0<V<250,000,000 |
| S_ABS | 250,000,000≤V<2,000,000,000 |
| M_ABS | 2,000,000,000≤V<10,000,000,000 |
| L_ABS | V≥10,000,000,000, including mega |

Invalid, zero, negative, unknown or nonfinite cap is not MICRO. It is unknown/refused. There is no Canada-specific threshold, minimum-cap waiver, or reseeding after a difficult result.

## 4. Canada healthcare: material risk, bounded evidence

The preserved fixed-reference audit found **five HealthCare-labelled ticker rows in the 216-row Canadian search artifact**. That artifact was ETF-holdings-derived and lacked the issuer identity, dated cap and primary-listing proof needed by this policy. Its separate 74-symbol Canadian breadth gauge had no healthcare label. These are measurements of those artifacts, not a census of Canadian healthcare issuers. See the unchanged `source_diagnostic_frame_v1/frame_deficiency_receipt.json` and supporting profiles.

Even assuming all five rows eventually proved distinct and eligible—a condition not established—four required selections would leave at most one spare overall. Under the relative rule and five distinct cap values, the middle and lower bands have **no spare at all**. Any missing identity, invalid instrument, absent lawful price or unsuitable activity classification can therefore defeat the current partial pool. This is a concrete reason to treat Canada healthcare as a high-risk frame cell.

The September 2026 S&P/TSX methodology separates Composite and SmallCap universes and derives most capped sectors from Composite membership and GICS categories. S&P also publishes a Venture healthcare index with a different micro-cap parent universe. Those official definitions show why the existing narrow artifact must not stand for the whole national listing perimeter. They do not establish how many WP02-eligible healthcare issuers exist. [P05](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-tsx-canadian-indices.pdf), Highlights; [P06](https://www.spglobal.com/spdji/en/indices/equity/sp-tsx-venture-health-care-sector-index/)

The bounded research did **not** obtain an adequately dated, unit-bound, full-issuer capitalization statistic for the national healthcare perimeter. A search-rendered Venture statistic lacked the bindings needed for use; a guessed capped-healthcare page failed. No eligible issuer names were fabricated. No cap was inferred from ETF weights, index weights, or an index's name. The S&P/TSX *Life & Health Insurance* search result was rejected as a route to the healthcare quota; financial insurance cannot fill it merely because its name contains “health.”

The explicit falsifiers are:

- Absolute policy A fails if the complete, valid Canadian healthcare frame has fewer than two issuers at or above USD10b, fewer than one in USD2b–10b, or fewer than one in USD250m–2b.
- Relative policy B fails if its valid tied-value bands cannot supply 2/1/1. Four ticker rows alone are insufficient.
- Neither policy passes while identity, perimeter or cap completeness is unresolved.
- A failure in this cell remains a failure of the full 120 specification. No healthcare omission, insurer substitution or country reassignment is permitted.

**National absolute-policy infeasibility remains unmeasured.** The stronger defensible conclusion is that feasibility has not been established and the current artifact is exceptionally thin. The future lawful frame route is the already specified exchange/issuer evidence process, covering the adopted Canadian venue perimeter rather than extending the ETF shortlist by hand.

## 5. Valuation, publication and actual evidence availability

The proposed fixed valuation date is **D=2026-09-30**, using local regular-session dates. The public-information cutoff is **K=2026-10-09T00:00:00Z**. The actual retained-evidence freeze **F** is a future principal-receipted timestamp after the inputs exist and before relationship-vendor consumption.

These clocks answer different questions:

| Clock | Meaning |
|---|---|
| Valid-at / measurement date | When a listing, share count, price, corporate action or business fact applies |
| Public-availability bound | When the source statement or revision became available to the public |
| Observation/acquisition time | When Mastermind actually obtained the evidence |
| Frame/cohort freeze F | Which exact retained inputs and decisions were locked before vendor outputs |
| Registry known-at | The incumbent owner's actual recorded knowledge event, if one exists |

A report period is not a publication date. A date-only publication uses the end of that date in its documented local timezone as a conservative upper bound. If the timezone is unknown or that bound crosses K, the assertion is not proven available by K. An actual timestamp can resolve this; an invented midnight cannot.

Use the latest eligible revision publicly available by K that applies to D. A later correction is retained separately and cannot be backdated merely because it concerns an earlier period. All actual observation times remain actual. A historical source obtained after K may support a **reconstruction of public knowledge by K**, but not a claim that Mastermind possessed it at K.

This is consequently a retrospective month-end source diagnostic assembled at F, with information through K. It is **not** a tradable point-in-time universe at the 30 September close: K deliberately extends beyond D, and global local closes and reference FX are not simultaneous. No predictive promotion follows from this design.

Frame metadata may use the most recent applicable primary annual report or prospectus, including a later fiscal label if relevant. That metadata role does not enlarge the accepted relationship-testing corpus of fiscal labels 2023–2025 and 2026 interim/material-event documents. Every actual report carries its own fiscal label, period dates and publication evidence.

## 6. Capitalization and currency: one reproducible reference measure

The selected size measure is **issuer reported-share reference capitalization in USD**. It estimates full residual ordinary-equity value from disclosed components. It is not free float, enterprise value, fully diluted equity, or a claim to have observed the issuer's exact unreported share count at D.

For each unique ordinary economic share class j:

```text
issuer_reference_cap_USD =
  sum_j(
    reported_and_bridged_outstanding_shares_j
    × bound_reference_close_j
    × quoted_price_unit_scale_j
    × USD_per_quote_currency_j
  )
```

Use the latest actual class share-count measurement at or before D, publicly available by K, no more than **183 calendar days** old. Bridge disclosed numeric changes effective between that measurement and D: issuance, cancellation, splits, conversions and treasury changes, each once. A known material action with missing quantities holds the value. Exclude treasury shares, preferred equity, unexercised options/warrants and debt that has not converted.

The 183-day ceiling is a proposed research quality tolerance, not an official market-cap standard. It makes the approximation visible and bounded. Undisclosed buybacks or issuances remain a limitation; their absence from public sources is not evidence that they did not occur. Preserve count date, age, bridge sources and completeness state. A proved correction that changes the size assignment triggers the replacement/correction law below.

Use an official regular-session close on D or the latest preceding official session. The quote may be no more than **five scheduled sessions** and **ten calendar days** old; both limits apply. Stale/suspended status remains visible. A missing price is unknown, not zero. Use a raw historical close consistent with the share basis; a split-adjusted price multiplied by unadjusted historical shares is invalid.

### Share classes and depositary receipts

Sum different ordinary economic classes separately. For A/H or other nonfungible classes, use their own shares, price and currency; do not apply one class price to all equity and then add another class again. For the same fungible class listed on several venues, bind one reference price coordinate before seeing values.

An ADR represents an underlying share ratio rather than a new independent set of company equity; the SEC's definition expressly allows multiples and fractions. If one ADR represents r ordinary shares, divide the ADR price by r to obtain an ordinary-equivalent price. Deposited shares already included in the ordinary count must not be added again. [P10](https://www.investor.gov/introduction-investing/investing-basics/glossary/american-depositary-receipts-adrs)

An unlisted ordinary class can use a listed-class proxy only when source evidence proves identical residual economic rights and a fixed conversion ratio. Record that it is a proxy, not an observed market price. Without that proof, hold the entire issuer cap as `UNPRICED_ECONOMIC_CLASS`; reporting just its conveniently priced class would change the quantity basis.

The reference-counter rule uses a source-designated primary counter. If several equally primary counters remain, choose ascending MIC bytes, then stable security-ID bytes, before observing prices. It must not choose whichever listing gives the preferred capitalization.

### FX

Use one common **ECB reference-rate date**: D if published, otherwise the latest published date no more than five calendar days earlier. Require every needed currency on that same date. ECB's published quotation basis is units of currency per EUR; therefore:

```text
USD_per_X = units_USD_per_EUR / units_X_per_EUR
```

For EUR the denominator is one; for USD the conversion is one. Quoted pence/cents require a separate documented denomination multiplier. There is no automatic HKD peg conversion, CNY/CNH equivalence, present-day FX substitution or unrecorded provider fallback.

ECB presents these as informational reference rates and discourages transaction use. That fits a reference-size diagnostic, while also precluding a claim of executable transaction prices. No current webpage rate has been inserted as the historical rate for D. [P09](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html)

Parse decimal inputs and ratios into exact rationals for comparison. Do not let floating-point artifacts or display rounding decide a threshold or a tied-value block. Retain every component and source binding so an independent recomputation can explain a classification change.

## 7. Instruments, venues and primary listing

Include ordinary equity of operating issuers and equivalent residual-equity units of operating partnerships. A depositary receipt can be a listing line for the same underlying issuer; it does not create a second issuer. Operating banks, insurers and asset managers remain eligible financial companies. A source-proved pre-revenue biotech business can be an operating issuer.

Exclude ETFs, ETNs, mutual/closed-end funds, passive investment vehicles, preferred shares, debt, warrants, rights, derivatives, pre-operating SPACs/blank checks, shells, private-only and OTC-only equity, and professional-investor-exclusive admissions. This is a deliberate source-diagnostic perimeter; it is not a claim that excluded instruments lack economic relationships.

The venue predicate is an issuer-applied primary ordinary-equity admission on an operating national equity exchange or recognized equity growth market in the jurisdiction. An exchange registration entry or a secondary trading line alone does not satisfy it. The SEC register, for example, distinguishes the national-exchange route from futures-only registration, but neither a venue name nor its current presence proves a particular issuer's primary listing at D. [P11](https://www.sec.gov/about/divisions-offices/division-trading-markets/national-securities-exchanges)

| Jurisdiction group | Perimeter to bind before selection |
|---|---|
| US | SEC national equity-exchange status plus actual primary-equity admission; no options/futures/trading-only substitution |
| CN_MAINLAND | Shanghai, Shenzhen and Beijing ordinary-equity admission routes; qualified-retail growth boards are not excluded merely for investor thresholds; no NEEQ/OTC substitution |
| HK | SEHK Main Board/GEM primary or dual-primary lines; secondary-only cannot fill HK |
| CA | Eligible Canadian recognized exchange/growth-market admissions, including the TSX/TSXV/CSE/Cboe Canada routes where actually applicable |
| UK | Qualifying UK primary equity admissions, including growth markets; neither the FCA Official List alone nor the main London segment defines the entire perimeter |
| JP | Qualifying Japanese primary equity exchanges/segments; no silent restriction to TSE or its Prime segment; professional-only admissions excluded |
| EU | Issuer-primary admissions on an EU27 regulated market or qualifying equity-growth MTF; exclude non-EU EEA, UK and Switzerland |

The JSON freezes the 27 EU country codes explicitly. Current EU and UK-government primary lists distinguish EU27 from the wider EEA and Switzerland. [P13](https://european-union.europa.eu/principles-countries-history/eu-countries_en); [P18](https://www.gov.uk/eu-eea)

This table specifies the method perimeter; it is **not** a produced, exhaustive, dated MIC/admission register. The OSC/FCA/FSA/ESMA reads were partly search-rendered or navigation-only, and those limitations remain in the source register. The later frame needs owner-bound venue records and effective intervals, not guessed status from these examples.

### Dual-primary tie rule

Use incumbent canonical economic-issuer IDs. A CIK, LEI, ticker suffix, headquarters country or largest traded volume does not establish primary listing. Keep `NO_ISSUER_EVIDENCE` unresolved; do not deduplicate all missing IDs into one entity or count each ticker as a resolved issuer.

HKEX distinguishes primary, dual-primary and secondary statuses in its own guidance. A sampling tie must therefore preserve all proved primaries rather than rewrite one as the sole legal primary. [P14](https://www.hkex.com.hk/Listing/Rules-and-Resources/Guidance/IPO/Listing-of-Overseas-Companies/Understanding-the-Risks-of-Investing-in-Overseas-Issuers?sc_lang=en), Primary and Secondary Listings

When an issuer has one proved eligible primary jurisdiction group, assign it there. When it has several, deduplicate those groups and choose the one with the smallest domain-separated hash of the fixed seed, incumbent issuer ID and jurisdiction-group ID. This is explicitly an **administrative sampling assignment**. It occurs before size pools are built and cannot be retied to rescue a quota. Within EU, a separate country hash picks a reporting coordinate without adding country quotas.

A proved primary outside the perimeter with only secondary lines inside is outside scope. An uncertain primary remains unknown. Distinct listed parent/subsidiary reporting entities can remain distinct with a common-control flag; ambiguous dual-listed-company economic units return to the identity owner. The selector never invents that adjudication.

## 8. Source-backed six-group assignment

A GICS-like label in a row is not self-authenticating. Use one of two evidence routes:

1. A lawfully supplied, dated issuer-level classification from a regulator, exchange or entitled classification owner, with a frozen one-to-one mapping into the defined group.
2. Primary business and **consolidated external annual revenue** evidence: assign the sole group contributing **more than 50%**. Map disjoint activities once, use consistent periods/units and avoid intersegment double counting.

A pre-revenue issuer can use a primary prospectus/annual description establishing exactly one operating activity, with independent reviewer agreement. Otherwise hold the classification. If primary business evidence materially conflicts with the coded route, record `SECTOR_CONFLICT`; the quota is not a tiebreaker.

GICS's April 2026 methodology uses principal business, revenue, earnings and additional review rules. Our strict-majority fallback is deliberately simpler and is **not** a claimed implementation of GICS. The July 2026 GICS consultation found during research is a proposal, not evidence that its classification changes were adopted. Public methodology also supplies no bulk issuer-classification entitlement. [P07](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-gics.pdf), p.3; [consultation](https://www.spglobal.com/spdji/en/documents/indexnews/announcements/20260717-1484356/1484356_gicsconsultation2026.pdf)

| Group | Positive scope | Important exclusions / interpretation |
|---|---|---|
| Semiconductor/cloud | Semiconductor devices, design/foundry/assembly-test and production equipment; externally sold IaaS/PaaS operations | Broad IT, a cloud customer, internal IT, generic SaaS alone, property-only data centers, or a minority AI/cloud narrative |
| Industrials | Capital goods, industrial services/production and transport/logistics under the frozen activity mapping | Activities already assigned to semiconductors or energy/materials; pure real estate and utilities |
| Consumer | Consumer discretionary/staples businesses such as retail, food, household goods, autos and leisure | Not every company selling to a consumer; generic IT hardware does not acquire this label automatically |
| Energy/materials | Energy extraction/refining/equipment and materials/mining/chemicals/forestry | Utilities do not migrate here simply to fill a slot |
| Financials | Operating banking, credit, capital markets/financial services and insurance | Passive funds; managed healthcare must follow its actual source-backed activity |
| Healthcare | Providers/services/managed care, equipment, medicine, biotech and life sciences | Financial life insurance by name, healthcare property ownership, or recreational products through medical association |

For supplied GICS metadata, 20 maps to industrials; 25/30 to consumer; 10/15 to energy/materials; 40 to financials; 35 to healthcare. The semiconductor detail is narrower than sector45; 45301010/45301020 are compatibility hints only when lawfully supplied for the actual issuer/vintage. No synthetic GICS code is emitted by the primary-evidence route.

The narrow cloud choice intentionally separates external infrastructure/platform operation from thematic association. NIST distinguishes SaaS, PaaS and IaaS as service models; that does not itself define a corporate sector. Choosing only IaaS/PaaS for this slot is an explicit research perimeter decision. A diversified issuer with only a minority cloud operation must qualify through its actual primary activity, rather than receiving a fabricated companywide cloud-revenue allocation. [P08](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-145.pdf), service models

These six groups are not an exhaustive classification of the whole economy. Out-of-scope activities and unresolved conglomerates remain visible. If the principal wants SaaS or additional activity groups included, that requires an amended version before source/vendor outcomes, not a hidden broadening during selection.

## 9. Deterministic selection and the joint INT feasibility algorithm

Use the literal UTF-8 seed **`GMI-WP02-20261009-v1`**. Define:

```text
H(domain, fields...) =
  SHA256(
    concatenate for each string s in [domain, seed, fields...]:
      unsigned_64_bit_big_endian(byte_length(UTF8(s))) || UTF8(s)
  )
```

Use strict UTF-8 and the incumbent identifier bytes exactly; do not trim, case-fold or normalize IDs. Issuer priority is ascending `H("issuer-priority", issuer_id)`, with exact issuer-ID bytes resolving a digest collision. Input order, ticker spelling, market performance and vendor coverage do not enter the priority.

For US, mainland China, HK and Canada, require capacity in every sector/size cell and select the first two L, first one M and first one S by priority. There are 72 such cells and 96 selected issuers if all pass.

INT must be solved jointly. Let each already-deduplicated candidate have exactly one UK/JP/EU group, one activity and one size band. Construct an integer flow network:

- source → each of UK, JP and EU: capacity8;
- each country group → each activity/size cell: capacity equal to the available unique candidates in that intersection;
- each of the18 activity/size cells → sink: capacity2 for L and1 for M or S.

The maximum possible flow is24. A flow of24 saturates all country quotas and every activity/size quota. A smaller value is an infeasibility certificate. Preserve the entire 3×18 capacity matrix, achieved flow and deficient mincut. Since each issuer has exactly one country/cell after deduplication, this aggregation does not conceal cross-cell reuse.

To make the selected solution unique without arbitrary solver costs, iterate candidates in fixed priority order. Tentatively include the next issuer only if it leaves nonnegative residual quotas **and the remaining candidates can still complete all residual quotas by the same flow test**. Otherwise exclude it. Continue until24. This chooses the lexicographically first feasible set under the fixed priority, while preserving a certificate for every forced exclusion that would defeat feasibility.

An actual selector must also verify global distinct issuer count120, five counts24, thirty activity counts4, all90 activity/size demands, INT8/8/8, and the evidence/availability requirements. It must never interpret a syntactically valid hash as proof that the input was adopted or frozen.

### Why independent cell checks are insufficient

A country can have eight candidates in total while all its candidates occupy cells whose combined remaining quota is smaller than eight. Other countries may have enough candidates to make each individual sector/size capacity look adequate. Those marginal checks still cannot produce a jointly valid selection. The maxflow/mincut condition tests exactly that intersection. This is a mathematical failure mode, not an observation about the actual unbuilt international frame.

No actual flow, issuer ranking or selection was executed in this assignment. The JSON and this memo define the method so the principal can adjudicate it before commissioning the bounded selector.

## 10. Correction, replacement and falsifiers

Before freeze, a proved eligibility error can be corrected using source information allowed by K. Preserve earlier versions, recompute deterministically and keep the seed and policy fixed. After cohort selection but before vendor unblinding, an objective correction requires an independently reviewed superseding freeze and a full constrained recomputation. Filling one vacancy manually is not enough when INT intersections or relative ranks change.

After vendor unblinding, the registered headline cohort is not replaced. Retain the original requested120 denominator and separately report corrected eligibility. A new cohort is a new explicitly registered study; the original failure is not erased.

No filing found, no provider match, anonymous disclosure, stale relationship output, extraction refusal, poor document quality and an unfavorable result are **diagnostic outcomes**, not replacement grounds. This rule matters more than a perfect-looking final count.

The difficult-case minimum is also real. Identify actual cases in selected issuers/documents before vendor outputs, under deterministic issuer/document/locator ordering and independent adjudication. Fewer than six authentic stress cases in a stratum remains a shortfall. An outside-cohort challenge supplement needs a separate adopted scope and denominator; it cannot silently fill the original benchmark.

| Finding that would falsify a stronger claim | Required treatment |
|---|---|
| “Large” is relative but presented as equal global dollar scale | Withdraw that comparison; use absolute companion values or adopt absolute policy for a new design |
| Relative L/M/S all occupy one absolute band | Report the concentration; quota balance is not absolute-size diversity |
| A pool omits unresolved or missing-cap eligible issuers | Reject market-relative ranks; expose the unresolved denominator |
| Share ratio, FX direction or share-basis correction changes a selected band | Preserve the erroneous version and follow the correction law |
| Canadian healthcare cannot supply adopted2/1/1 | Record full-design infeasibility; no insurer/REIT/ticker substitution |
| INT marginal counts pass but flow<24 | Fail the joint quota requirement with a mincut |
| Cap/source metadata is publicly available only after K | Exclude it from this vintage; no reconstructed earlier native knowledge |
| Actual source-use/retention rights cannot be established | Hold the affected frame input; this research confers no entitlement |
| Vendor outputs were consumed before freeze/annotation | Blinding requirement fails; no retrospective claim that it passed |
| Fewer than six difficult cases in any stratum | Keep the stress-case acceptance criterion unfulfilled |

A rank definition can be perfectly implemented and still be unsuitable for a substantive claim. No part of this research turns source coverage, thematic similarity or historical market correlation into an economically admitted relationship or a predictive mechanism. All predictive/production authority fields remain null/false.

## 11. Evidence status, bounded search limits and delivery

The recommendation is based on primary methodological/regulatory material and the already accepted immutable frame audit. Web observations are labelled **web-rendered**, **web-rendered PDF**, or **primary search-render only** in `PRIMARY_SOURCE_REGISTER.json`. No web rendering is assigned a source-byte hash. No exchange universe, issuer cap census, provider relationship output, source capture or native runtime was acquired or executed here.

Primary sources cover: FINRA conventions; S&P's current-linked US and September Canadian methodology; MSCI's dated full method and July summary; April GICS method; NIST cloud definitions; ECB quote basis; SEC ADR and venue definitions; HKEX listing distinctions; official EU country scope; and bounded regulator-register navigation. The failed MSCI live full routes, capped-healthcare page, incomplete statistics and partial regulator bodies remain recorded. They are not converted to absent issuers or blanket access denial.

The later principal adoption receipt must identify this policy version, the three semantic decisions, actual adoption time and owner. A subsequent selector must receive exact, reviewable frame/evidence bindings, not this memo as a substitute for data. The principal still owns sourcing entitlement, frame production, issuer adjudication, executable selector scope and any Git publication.

### Files

- `RECOMMENDED_SELECTION_POLICY.json`: exact proposed parameters, formulas, perimeter, counts, deterministic solver law, clocks, exclusions and holds.
- `PRIMARY_SOURCE_REGISTER.json`: primary URLs, versions/locators, evidence levels, bounded failures and rights limitations.
- `SELECTION_POLICY_ADJUDICATION_MEMO.md`: this substantive decision record.
- `ARTIFACT_VALIDATION.json` and `PACKAGE_MANIFEST.json`: final local structural/digest checks and bindings, produced only after the drafts are complete.

**Bounded outcome:** the controllable policy gap now has a concrete recommended resolution. The actual120 cohort remains unselected and unadmitted. The prior measured frame deficiency remains intact.

STOP.

