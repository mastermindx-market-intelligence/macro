# Commission 11 — Short, Borrow, Securities-Lending & Crowding Intelligence

## Hardened research commission and implementation masterplan

**Research cutoff:** 2026-10-04. **Disposition:** recommend the bounded foundation; hold predictive and decision authority. **Execution status:** research, source audit and documentation only. No production implementation, new market-outcome experiment, procurement, deployment, ranking change or portfolio mutation was performed.

This is the complete A–L replacement recommendation for the supplied report, not an approval to execute it. The original report's useful thesis—separate positioning evidence, temporal integrity, risk before alpha—is retained. Its overstated historical guarantees, incomplete source semantics and overly broad first implementation commission are corrected here. Source IDs resolve in [SOURCES_AND_AUDIT.md](SOURCES_AND_AUDIT.md); acceptance scenarios are specified in [ACCEPTANCE_CASEBOOK.md](ACCEPTANCE_CASEBOOK.md).

**Evidence labels:** OBSERVED_SOURCE means bounded reading of an identified source, not a production test. STORED_RESULT means an existing research artifact was inspected, not reproduced. PROVIDER_CLAIM means a vendor's published description, not independently tested functionality. PROPOSED means architecture or research design introduced by this commission. UNVERIFIED means the necessary evidence was not obtained. These distinctions apply throughout.

## A. Executive conclusion

### A1. What to build

Build a **federated, point-in-time crowding evidence layer** on the existing Macro producers and ownership/options consumers. Do not build another score engine, security master, evaluator, portfolio gate or control plane. The minimum useful product answers six separate questions:

| Dimension | Question | Initial output and authority |
|---|---|---|
| Reported short crowding | How large and persistent is the published short position relative to the appropriate share and liquidity denominators? | Observed quantities and derived ratios; context only |
| Broker borrow stress | What does a named broker quote for financing and sourcing this security? | Provider-scoped indicative fee and censored availability; context only |
| Securities-lending supply/demand | Within a defined provider population, are outstanding loans increasing, supply withdrawing or financing costs rising? | Unavailable until compatible inputs exist; no broker-to-market extrapolation |
| Long ownership crowding | Which disclosed holders are concentrated, and how large are their positions relative to liquidity? | Coverage-qualified ownership and liquidation scenarios, not live fund flow |
| Potential forced-flow exposure | Which explicitly modeled options, fund or index mechanisms could amplify a move? | Existing owner references and scenario assumptions, not observed dealer inventory |
| Reversal/fragility | Which independent legs changed, in what order, and what contradicts the interpretation? | Inspectable transition record; no aggregate probability or automatic action |

The priority is **high for information integrity**, **conditional for risk usefulness**, and **unproven for incremental alpha**. Public data can establish a useful baseline, but not a complete contemporaneous census of bearish exposure. Short-sale activity, reported short positions, outstanding securities loans, lendable inventory and directional intent are different concepts. None should substitute for another merely because it is easier to obtain. [P1–P5]

### A2. The principal changes to the original recommendation

The original report was too permissive about the word “PIT.” A publication date does not prove that today's historical value was the value published then. Nor does public availability prove that Mastermind received, validated or was entitled to the information then. The replacement contract explicitly separates **source-knowable reconstruction** from **actual system replay** and separates economic validity from knowledge validity.

The fresh source audit also found previously underemphasized defects: destructive FINRA revisions; a settlement-date-only FINRA ADV check in ownership crowding; a frozen-feed staleness blind spot; IBKR identifiers discarded during parsing; feature-dependent retention outside the current universe; and an availability lower bound labeled “unlimited.” These are static findings with concrete source witnesses, not claims that a particular production decision was corrupted. [R1–R6]

The current historical SI coverage receipt is dated August 15, ends July 31 and describes an as-restated panel. It does not certify October freshness. The newly merged S&P 1500 leaver-sector substrate is useful adjacent work, but its own receipt says **zero era-correct labels** and 802 of 1,083 leavers unlabeled. It is not a completed historical sector or delisting-return solution. [R7, R11]

The existing SP1-B result remains a binding negative research result for promotion. Its own caveat prevents an unbiased effect estimate, however, so it is neither proof that all crowding information is useless nor permission to reinterpret a positive artifact coefficient as a squeeze strategy. [R8–R9]

### A3. The decision now

Accept the architecture and commission **P0A: immutable capture and replay-contract qualification**, subject to current source law and existing rights. In parallel, permit **P0B: historical feasibility and owner reconciliation**, without market-outcome access. Do not make forward capture wait for a perfect historical universe. Do not launch the original omnibus P0/P1 implementation commission.

After data admission, test a small, frozen set of claims against price, liquidity and existing options information. Commercial lending evaluation is a separately authorized option, not a prerequisite and not categorically forbidden when it solves a demonstrable data-quality problem. A data source can justify its cost through coverage or operational risk reduction without earning alpha authority.

## B. Current-state census and recensus

### B1. Source identities and evidence boundary

The original preliminary Mastermind SHA was not reused as current. These repository identities and default-branch heads were read on October 4:

| Estate | Resolved repository | Source pin |
|---|---|---|
| Mastermind | `mastermindx-market-intelligence/Mastermind` | `521720b09be2921e996d9396b522b1c4ca62041c` |
| Macro | `mastermindx-market-intelligence/macro` | `79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f` |
| Terminal | `mastermindx-market-intelligence/mastermind-terminal` | `1c708450187755160e1a5889b69598a2fcb1f0d1` |
| Research Vault repository | `mastermindx-market-intelligence/executive-dr-vault` | `ea422c92bd29800d1f7fb3ae850236cc44d8c890` |

The protected Mastermind INDEX and applicable procedure files were read from the same Mastermind pin. Macro's observed `main` branch was not marked protected by the branch API; “current source pin” must not be silently relabeled “protected Macro master.” The accessible Vault is private; no private corpus or vendor dataset is copied into this public research packet. Terminal/Vault repository identity is established, but their production behavior and complete semantic contents are not certified. [R12–R16]

The original report's Macro pin was one commit behind the audit pin. The four changed paths concerned a China THS collector and its CI/tests, not the inspected crowding modules. This narrows source drift; it does not retroactively validate the original analysis. The full Macro recursive tree was truncated, so absence from that tree was not used to prove a capability absent. Searches did not establish an existing Commission 11 publication carrier. [R16]

### B2. Capabilities and gaps

| Component | Observed source/state | Assessment and consequence |
|---|---|---|
| FINRA current SI | `collectors/finra.py`; current snapshot and latest-per-settlement history | BUILT_NOT_PROVEN. Corrections replace prior captures; current-universe filter and dropped raw fields limit historical reuse. |
| Historical SI builder | `scripts/backfill_finra_short_interest.py` | BUILT_NOT_PROVEN; explicitly AS_RESTATED. Manual backfill, inferred release lag, no original-vintage proof. |
| Historical SI coverage | 3,888,611 rows; 206 settlements; 48,679 ticker strings; 2018-01-12 to 2026-07-31; receipt generated 2026-08-15 | Stored metadata, not October runtime proof or a unique-security count. |
| FINRA short-volume capture | `collectors/finra_short_volume.py` | BUILT_NOT_PROVEN. Re-fetches recent files but deduplicates with later rows winning; historical generations lost. |
| IBKR borrow | `collectors/ibkr_borrow.py`; dated daily artifacts visible in repository tree | BUILT_NOT_PROVEN. Provider-specific, indicative, same-day overwrite, incomplete identity and receipt clocks. File presence does not prove continuous coverage. |
| Short-pressure axes | `engine/short_pressure.py` | Descriptive authority flags present. Inferred historical lag, frozen-feed freshness issue and missing-column guard inconsistency require admission review. |
| Ownership crowding | `engine/ownership_crowding.py` | Descriptive owner exists. FINRA ADV primary read gates on settlement, not publication; not a sufficient PIT guarantee. |
| Legacy fragility | `engine/crowding.py`, referenced by current owners and prior report | Existing adjacent owner; no greenfield replacement. Detailed implementation not freshly certified in this pass. |
| PSS-CD1 | `engine/personality_crowding_hazard.py` | Existing prospective correlation/dispersion construction with frozen hashes and maturity requirements. Separate scientific identity; do not pool it into C11. |
| Options and Mastermind lenses | Existing options plane; `portfolio/lenses.py` | Existing consumers mix context and authority-bearing lenses. “All existing positioning is display-only” is too broad. No new options engine. |
| S&P 1500 historical-leaver infrastructure | Current membership/sector artifacts and merged Macro #8403 | Partial reuse candidate. Sector receipt has no era-correct labels; not proof of complete delisted prices or returns. |
| Portfolio V3 | Protected architecture document | SPEC_ONLY / RECORDS_ONLY / PRODUCTION_INERT in the inspected specification. Do not presume its future Snapshot consumer exists. |
| Static system census | `data/census/CENSUS.md`, generated 2026-07-16 | Stale source inventory; cannot establish October jobs or capability counts. |
| Market-wide lending supply/utilization | No qualified current canonical contract established by this audit | UNVERIFIED/NOT_ADMITTED, not an exhaustive assertion that no estate file could contain such data. |

Sources: [R1–R15]. Runtime certification would require current artifact and operational receipts from the existing runtime owner; source presence alone is insufficient.

### B3. Concrete failure modes discovered in current code

**FINRA SI:** the current collector collapses corrections on `(settlement_date, ticker)` with `keep=last`. It also uses weekday-only candidate settlement dates, narrows to current cached universe names and drops fields present in the upstream response. A paginated request that stops early can be mistaken for a complete snapshot unless completeness is independently checked. A cached fallback is not proof of a successful refresh. [R1]

**Short-volume:** the normalized schema drops the source `Market` field. Invalid/missing exempt volume becomes zero; a parse failure is thereby converted into a measured absence. The collector's append-only description conflicts with its replacement behavior. FINRA's current official documentation explicitly allows later updated files, contrary to the SI collector's “never revised” comment. [R1, R2, P2–P3]

**IBKR:** the raw format contains stronger identifiers, but the parser retains ticker rather than CON/ISIN/FIGI. Same-day captures overwrite. The out-of-universe tail is retained only above a fee threshold, creating selection dependent on the predictor. The token `>10000000` means a censored lower bound, not infinite supply. These problems are separable from the sensible decision to keep broker inventory distinct from the whole lending market. [R3]

**Consumers:** `ownership_crowding.adv_shares` accepts the current FINRA ADV when settlement precedes the requested anchor, without checking when that ADV was published. `short_pressure.asof_slice` measures staleness against the newest settlement inside the supplied panel; an entirely frozen panel can therefore remain internally “fresh.” Its optional `asof=None` path does not apply a historical availability cutoff. Its missing-ADV-column branch returns a non-thin mask despite a comment promising the opposite. These are source-level counterexamples to broad temporal-safety claims, not completed runtime reproductions. [R4–R5]

### B4. Duplicate and adjacent programs

Preserve SP1, PSS-AF1 and PSS-CD1 scientific identities. SP1's existing preregistration and amendments control historical reproduction; do not silently replace the test after seeing outcomes. Its source records a user-facing “no squeeze” fence and avoid-not-short boundary. This research can discuss squeeze mechanisms, but does not authorize changing that product vocabulary or authority. [R8, R10]

Prophet Cell E/MAS-121 already proposes separate structural fragility, path fragility, crowding/positioning and coverage objects. Its carrier **Macro #6264 is open/draft**, current inspected head `5d6fd20e5716258f4d6aa93811561a3a6463360c`. The body contains older head references; these are not the current candidate identity. The Cell E handoff path was not present on current `main`. Treat this as adjacent proposed architecture requiring reconciliation, not approved runtime truth. [R17]

Portfolio V3 is the eventual consumer boundary for evidence independence, but C11 must remain an upstream producer. Existing source/identity/evaluation owners retain their roles. Module names do not prove an active human assignee; the implementation owner must resolve current custody before editing. [R12–R15]

## C. State of the art and competing explanations

### C1. What the literature supports—and does not

Cohen, Diether and Malloy study lending quantities and fees jointly, motivating a distinction between shifts in loan supply and demand. Saffi and Sigurdsson connect lending constraints with price efficiency in their historical international sample. Hong and coauthors motivate days-to-cover as a liquidity-scaled short-position measure. These are reasons to measure distinct mechanisms, not evidence that Mastermind's available panels can reproduce the published effects. [P16–P18]

Muravyev, Pearson and Pollet show that borrowing costs can absorb much of apparent anomaly profitability in their tested sample. Their separate options research shows that some option-implied return information embeds borrowing costs. This is a targeted warning about overlapping mechanisms, not a claim that every options feature, including every GEX model, is redundant with borrow fees. [P19–P20]

Institutional lending products emphasize supply, outstanding loans, utilization, rates and delivery/history rather than only a single squeeze score. Nevertheless, marketed “PIT” history must be qualified for original vintages, population changes and corrections. A provider's coverage claim is not proof of total-market measurement. [P10–P15]

### C2. Mechanistic hypotheses and rival explanations

| Candidate interpretation | Strongest rival explanation | Discriminating evidence |
|---|---|---|
| Fee increase signals new informed short demand | Inventory withdrawal, broker reallocation or collateral-rate change | Matched-population on-loan and supply changes; fee convention; independent provider corroboration |
| Rising DTC means shorts are building | ADV collapsed while short shares stayed flat | Separate numerator and denominator changes on the same share basis |
| Higher short-sale ratio means more open bearish exposure | Market-making, turnover, venue-share change or offsetting transactions | Do not infer open positions; compare subsequent published SI only as a distinct, delayed observation |
| Concentrated holders create forced-sale risk | Stable long-horizon holders face no correlated funding shock | Holder type, redemption exposure and independently observed outflows, where lawful and timely |
| A rally is a short squeeze | Fundamental news, generic momentum or option hedging | Causal attribution remains unresolved without covering/loan-state evidence; test a price-tail outcome, not an invented squeeze label |
| Vendor data improve predictions | Vendor selects liquid survivors or embeds price/option features | Matched support, raw-field ablation, source lineage, vintage and inclusion audits |

The design implication is not to infer a causal decomposition from fee and availability alone. A price/quantity pair is suggestive, but simultaneous supply and demand shifts, reporting-population changes and measurement errors can defeat identification. Report competing explanations alongside the observed changes.

### C3. Regulation: future opportunity, not imaginary current data

The SEC's December 2025 exemptive order moves the Form SHO compliance date to **January 2, 2028**. The same order places securities-loan reporting on **September 28, 2028** and public dissemination on **March 29, 2029**. FINRA's current SLATE page and a September 30, 2026 SEC notice corroborate the lending schedule. These are currently scheduled dates, not guarantees that a usable endpoint will exist on that day. [P6–P8]

A more important semantic correction: final Rule 10c-1a removed the proposed “available to lend” reporting requirement. Loan amounts have a different dissemination delay from other fields. Therefore SLATE must not be advertised as a future turnkey market-wide utilization denominator. Re-qualify its actual public schema, population, lags and corrections at launch. No future regulatory variable belongs in a 2026 historical feature matrix. [P9]

## D. Source landscape and acquisition policy

**Cost classes below are qualitative diligence categories, not quotes.** Public retrieval is not a blanket commercial-use or redistribution license. Every product needs an entitlement and retention decision before use.

| Source | Coverage and history | Latency / PIT quality | Corrections | Rights / cost class | Best use |
|---|---|---|---|---|---|
| FINRA reported SI | Reported positions; internal reconstruction starts 2018; original historical vintages not established | Twice monthly, publication after settlement; exact schedule preferred | Retain all generations; current internal history is destructive | Public-access source; terms review / low acquisition cost | Canonical reported-position baseline [P1, R1, R6] |
| FINRA daily short-sale files | Facility-scoped activity; consolidated NMS starts Aug 2018 | Same-day evening publication; not an all-venue position census | Original and updated files can coexist | Public access; use terms review / low | Flow context and data-quality cross-check [P2–P3] |
| Exchange SI products | Exchange/product-specific public displays and licensed history | Publication-calendar dependent | Require release/correction archives | Public display or commercial contract / variable | Reconciliation, not additive independent votes; specific feed not qualified here |
| IBKR live shortable file | Broker inventory/indicative rates; existing forward captures | Source snapshot plus actual receipt needed | Mutable intraday; capture all distinct versions | Publicly retrievable endpoint is not permission to republish / low if approved | Broker-scoped stress [R3, P4] |
| IBKR historical indicative rates | Official website describes historical rates through its availability tools | Exact accessible depth, timestamps and entitlement unverified | Unverified historical revision behavior | Account/product terms unresolved / unknown | Feasibility alternative; corrects the overly broad “IBKR has no history” claim [P4] |
| SEC 13F | Delayed manager holdings, incomplete investor population | Filing-publication time, not quarter-end, for knowledge | Preserve amendments and their amendment type | Public filings / low acquisition, meaningful normalization effort | Disclosed long concentration [P5] |
| Issuer ETF holdings and baskets | Fund-specific; archive depth varies | Portfolio effective date differs from first publication | Replacement files need capture generations | Issuer-specific terms / low to commercial | ETF ownership, look-through and rebalance scenarios [P22] |
| Existing options/GEX sources | Reuse actual licensed coverage | Chain/OI release clocks and model version required | Preserve vendor revisions and model versions | Existing entitlements, not assumed new rights / existing | Independent convexity reference, not dealer-book truth [R13] |
| SEC fails-to-deliver | Aggregate outstanding settlement failures, historical files | Delayed releases; not a contemporaneous short book | Archive source versions | Public source / low | Auxiliary settlement-stress context, separately tested [P21] |
| DataLend | Provider markets supply, loan, utilization and rate data plus history | API/history marketed; original-vintage retrieval unverified | API documentation says amendments are reflected; demand explicit as-original support | Commercial retention/display/derived rights / enterprise, quote unknown | Raw lending-state candidate [P10–P11] |
| S&P Global Securities Finance | Provider markets broad lending supply/demand/fees and long history | “PIT” and multi-decade history claims require field-level verification | Correction generations and population stability unverified | Commercial / enterprise, quote unknown | Historical lending-state candidate [P12] |
| FIS Securities Finance Market Data | Global/intraday lending analytics marketed | Exact deliverable/history contract not inspected | Unverified | Commercial / enterprise, quote unknown | Independent lending-market comparison [P13] |
| S3 Partners | Proprietary short estimates, lending and crowding analytics | Modeled estimates are distinct from regulatory SI; historical availability marketed | Require model/input version and original publications | Commercial / enterprise, quote unknown | Estimated-position benchmark; raw and modeled fields kept apart [P14–P15] |
| Form SHO | Future reporting regime, not current C11 historical data | Scheduled compliance from Jan 2028; actual public outputs still require qualification | Future amendment semantics | Regulatory source, future availability | Future aggregated short-position context [P6] |
| Rule 10c-1a / SLATE | Future covered loan reports and public dissemination | Reporting Sep 2028, dissemination Mar 2029 under current relief | Future system must be inspected | Future regulatory source | Loan/rate transparency, not guaranteed full utilization [P7–P9] |

### D1. Short-volume schema correction

FINRA's format defines **ShortVolume as including short-exempt trades**. Accordingly `short_ratio = ShortVolume / TotalVolume`; adding ShortExemptVolume again double counts. Validate `0 <= exempt <= short <= total`, retaining malformed values as invalid rather than replacing them with zero. CNMS and its constituent facility files must not be summed together. Preserve the facility and regular-session scope. These calculations remain activity measures. [P2–P3]

### D2. Commercial qualification, not a vendor beauty contest

Use a written questionnaire and a deliberately difficult sample: name changes, reused tickers, share classes, hard-to-borrow names, delistings, general collateral, corporate actions, zero inventory, holiday boundaries and known corrections. Obtain samples only through an authorized lawful evaluation; this commission did not request or ingest any.

Require field definitions, units, weighted-rate convention, provider population, contributor entry/exit, original publication timestamp, delivery timestamp, original-vintage retrieval, correction and retraction examples, coverage by historical date, identifiers, API/bulk behavior, rate limits, delivery SLO, model methodology versions, raw-versus-estimated flags and a complete rights matrix. “History available” and “PIT” are not sufficient answers.

Score three independent procurement cases: **data integrity/coverage**, **risk-information utility**, and **incremental alpha**. The first can justify a bounded purchase even if the third fails; none grants portfolio authority. Compare total cost of ownership, including security-master work, corrections, egress, retention after termination, model-training restrictions and migration. Keep a vendor-neutral normalized contract and exportable receipts to reduce lock-in. No exact pricing or signed rights were established here.

## E. Canonical data model and temporal law

### E1. Two histories that must never be conflated

**SOURCE_KNOWABLE** asks what an eligible observer could have known from a particular source/version at time t. It requires the original source generation, its publication or transmission time, the applicable entitlement, and truthful historical coverage. It is a counterfactual information-set reconstruction, not Mastermind's actual operating history.

**SYSTEM_REPLAY** asks what Mastermind actually had admitted at time t. It additionally requires local receipt, durable persistence and validation completion. A feed published Friday but received Monday was not in Friday's actual decision information set. A later historical download cannot be inserted backward into actual system replay.

**AS_RESTATED_RESEARCH** is a separate descriptive mode for today's reconstruction of the past. It may support feasibility work and explicitly labeled sensitivity analysis. It does not pass strict vintage admission merely because a conservative publication lag is attached. Historical exclusion of rows based on their eventual revision flag can itself select using future information.

### E2. Minimum common envelope

The following is a proposed logical contract, not a demand to create every field as a new physical table. Adopt equivalent canonical fields where they already exist.

```text
ObservationEnvelopeV1
  observation_id, observation_kind, schema_version
  source_id, source_product_version, source_record_key
  source_snapshot_id, source_generation_id, payload_hash
  security_id, listing_id, ticker_at_event, raw_identifiers{}
  provider_scope, provider_population_version, facility_scope?
  event_time?, event_time_precision, as_of, as_of_precision
  effective_from?, effective_to?                 # economic validity, [from,to)
  source_published_at?, publication_precision, publication_receipt_id?
  available_at?, availability_basis             # source-knowable generation time
  observed_at, ingested_at, validated_at?
  known_at?, known_to?                          # admitted system knowledge interval
  correction_generation, supersedes_id?, operation_kind
  source_receipt_id, identity_receipt_id?, denominator_receipt_ids[]
  rights_policy_id, entitlement_interval?, permitted_use_classes[]
  pit_qualification, coverage_status, quality_flags[]
```

`event_time` can legitimately be null for a stock snapshot with no unique transaction event. Do not invent precision. `as_of` is the economic state represented; `effective_from/to` is not automatically a publication interval. `available_at` belongs to this exact source generation, not the original reporting period. `known_at` is no earlier than the receipt, persistence and validation gates required by the existing admission owner. All instants are UTC with retained source timezone and calendar identifiers. Date-only releases need a documented conservative intraday boundary; they are not automatically available at midnight.

`correction_generation` is monotone within a stable logical record lineage, not across every snapshot of a security. Distinct regular snapshots, corrected snapshots, repeated identical fetches and retractions have different operation kinds. Preserve upstream revision IDs; a local generation number must not imply the provider supplied one.

### E3. Query and correction invariants

A SOURCE_KNOWABLE query at t admits only qualified source generations with `available_at <= t` and valid historical entitlement. A SYSTEM_REPLAY query admits only observations with `known_at <= t < known_to`, with an open upper bound allowed. Neither query can substitute an AS_RESTATED row without visibly changing mode and authority.

Selection is a two-step operation: choose the applicable economic observation, then choose its generation available in the requested knowledge mode. A correction to an older settlement must not become the latest economic snapshot merely because it arrived yesterday. A correction discovered after t cannot alter a previously sealed decision artifact for t; it produces a separate restatement view and lineage.

A repeat fetch of identical bytes adds a receipt, not a new economic event. Distinct bytes require source-aware comparison; they may reflect formatting, added rows, corrections or a new regular snapshot. Retractions need tombstones. Never infer deletion from an incomplete response. Release a new cross-sectional snapshot only after pagination/footer/count checks pass; mixed pages from different source versions require quarantine or a declared incomplete generation.

Historical float, shares, identifiers, sector labels and universe membership obey the same knowledge rules. Security identity itself is effective-dated: CIK identifies an issuer, not necessarily a particular listed share class; ticker is not a permanent key. Do not replace a dead company's tape with its acquirer's or a ticker successor's prices.

### E4. Typed observation payloads

| Contract | Required native quantities | Explicitly optional or unavailable |
|---|---|---|
| `ReportedShortPositionV1` | settlement date, short shares, reporting scope | Reported ADV/DTC, previous quantity, revision/split flags; independently calculated ratios belong to derived fields |
| `ShortSaleActivityV1` | session date, facility scope, short volume, total volume, schema semantics | Exempt subset and corrected-file marker; never cast to a position contract |
| `BrokerBorrowQuoteV1` | broker, source timestamp, indicative fee convention, availability observation | Exact shares or censored interval; no inferred market on-loan or utilization |
| `LendingStateV1` | source population, measure definitions, observation basis | On-loan, lendable supply, utilization, fee/rebate distribution; null when genuinely absent |
| `OwnershipCrowdingViewV1` | references to canonical holdings and liquidity inputs | Tracked shares, holder concentration, ETF look-through, liquidation scenarios; no second raw holdings store |
| `CrowdingEvidenceV1` | decision time, replay mode, input/version references, separate dimension objects | Contradictions, transitions, model scenarios and uncertainty; no required aggregate verdict |

Rate fields retain raw value and unit, normalized decimal/year value when possible, calendar-day convention, currency, collateral type, fee-versus-rebate meaning and indicative-versus-executed status. Do not subtract a rebate from a fee without a sourced economic convention. Quantity ratios require compatible populations, units and timestamps. If a vendor's “lendable” means remaining unused supply rather than total inventory including loans, `on_loan / lendable` is not the same utilization statistic.

For IBKR `>10000000`, represent `comparison=GT`, `lower_bound=10000000`, `upper_bound=null`. An unknown value, explicit zero, a lower bound, an unavailable security and a parse failure are different states. Changes involving bounds yield bounded changes or abstention, not exact percentages.

### E5. Evidence object and authority

Each of the six dimensions in A1 contains `observations`, `derived_features`, `coverage`, `staleness`, `contradictions`, `scenario_assumptions`, `uncertainty`, `input_refs` and `authority`. The root preserves source-root lineage and economic-dependence families. A family label does not make correlated subfeatures independent votes.

Initial authority is explicit: no rank, size, gate, trade, veto or policy mutation. Descriptive presentation is still subject to rights and existing product vocabulary. Missing supply cannot produce a reassuring LOW risk state. A public-only view may legitimately show reported position, broker stress and model references while market-wide lending stress remains unavailable.

## F. Derived intelligence and model boundaries

### F1. Reported-position features

Keep source-reported DTC and two distinct derived quantities: DTC at the source economic date, and DTC using liquidity actually available at the decision time. Their questions differ. Neither overwrites the other.

`DTC = short_shares / ADV_shares_per_session` has units of sessions but is not a forecast of the time covering will take. SI/float and SI/shares-outstanding require different labels and PIT denominator receipts. Calculate publication-to-publication change in raw short shares, split-consistent change, DTC decomposition, persistence and cohort-normalized ranks only on eligible comparable observations.

For positive quantities, log changes give an exact decomposition: `Δlog(DTC) = Δlog(short_shares) - Δlog(ADV)`. Zero, negative, censored or inconsistent units require a separate branch. Keep sentinel and thin-liquidity flags visible. Cohorts should distinguish ordinary common equity from ETFs, funds, preferreds, warrants, units and other instruments before ranking; listedness alone is insufficient.

### F2. Borrow and lending features

Compute fee levels and changes, availability bounds, within-provider drawdowns in inventory and changes in compatible on-loan/supply measures. A flat large-cap fee distribution does not justify fitting noise, but a dated August observation does not prove future structural constancy. Re-estimate dispersion and coverage prospectively under frozen rules.

Where total lendable inventory L and outstanding loans Q share scope and units, utilization is U=Q/L. For strictly positive compatible observations, `Δlog U = Δlog Q - Δlog L`. This is an accounting decomposition, not causal identification. Rising fees with falling Q may reflect supply withdrawal rather than new bearish demand. Flag population/version changes before interpreting any aggregate jump.

Broker availability decreases can result from allocation changes, inventory transfers or client demand. Do not infer market-wide recall pressure or an inability to locate elsewhere. Historical fee shocks outside the current universe need a stable inclusion denominator; retain all lawfully capturable equities where feasible, or store a complete inclusion/exclusion manifest and acknowledge the resulting estimand.

### F3. Long ownership and passive concentration

For a declared tracked holder population, calculate holder share weights and `HHI = Σw²`, top-holder concentration, ownership breadth and position/ADV stress ratios. A tracked-population HHI is not total-market ownership concentration. Manager/submanager overlaps, shared discretion, options rows and amendments must be reconciled by the existing holdings owner. Form-version changes in reported value units need explicit handling. [P5]

`days_to_exit(p) = tracked_shares / (p × ADV)` is a scenario with stated participation p, not an executable schedule. Show alternative participation rates without selecting the most dramatic one. The model omits endogenous liquidity, competition among sellers and price impact; quantify those only in separately specified scenarios.

ETF ownership and 13F ownership are overlapping views, not additive buckets. Keep fund-held underlying shares separate from institutions holding ETF shares. ETF redemptions may transfer a basket in kind rather than force the fund to sell the corresponding stock immediately. Basket composition and authorized-participant behavior matter; ETF flow alone is not an observed stock-sale instruction. [P22]

### F4. Options and potential forced flows

Consume the existing options owner. Retain chain timestamp, OI as-of/release time, Greeks model, contract multiplier, expiration, corporate-action adjustment and dealer-sign assumptions. Open interest does not identify the dealer's side. Therefore report modeled exposures or sign scenarios rather than unqualified “dealer gamma.” No new GEX calculator or parallel options datastore is recommended.

An options-based flow scenario must specify whether gamma is per-dollar or percentage move, contract units and assumed inventory signs. Zero or missing OI must not be confused with absent exposure. Index rebalance scenarios require announcement-time knowledge, effective date and a documented tracking-assets assumption. Leveraged/inverse fund mechanics remain model scenarios; avoid attributing every closing move to forced activity.

### F5. Fragility, reversals and contradiction handling

Retain independent research legs: position fuel, financing constraint, adverse price move, liquidity constraint and modeled amplification. A component can be present while another is unknown. Do not force a LOW/MODERATE/HIGH classification on incomplete evidence. A large upside price excursion is a valid measurable outcome; calling it a verified short squeeze requires evidence the current public inputs do not directly provide.

Track the sequence of independently observed transitions: fee rise before an SI release, supply contraction before a price move, or a later published decline in SI. A change in reported SI cannot date the precise covering trade within the reporting interval. “Covering-like volume” is not an observed covering quantity.

Useful contradictions include high reported SI with easy broker financing, rising fee with falling on-loan balance, high short-sale activity with unchanged published SI, concentrated long ownership with little ETF exposure, and an adverse move despite stabilizing modeled convexity. Keep these records as competing hypotheses, not errors to be averaged away.

### F6. Deterministic first; bounded LLM use

Deterministic owners control identity, clocks, corrections, rights admission, data quality, denominators, calculations, cohort transforms, state rules, event labels, experiment splits, metrics and authority. A model must not infer a missing utilization number, backdate knowledge, repair canonical shares from narrative, or decide that a source is licensed.

A cheap model may classify documentation changes, propose anomaly categories or draft explanations from already computed fields. A frontier model may compare competing mechanisms, propose falsifiers and synthesize an evidence record for the existing research desk. Both must cite input observations and separate facts from hypotheses. No LLM output enters the canonical numeric plane or grants investment authority. Keep cost and latency proportional to uncertainty: routine descriptive rows need no frontier reasoning.

## G. Integration map and ownership

| Producer | Canonical owner/artifact | Evidence family | Consumer boundary |
|---|---|---|---|
| FINRA SI | Existing Macro collector plus correction-preserving observation backing | Reported short position | Existing short-pressure owner; later qualified evidence view |
| FINRA volume | Existing Macro short-volume owner plus facility/version receipts | Short-sale activity | Context research; never a position field |
| IBKR | Existing borrow collector plus provider-scoped immutable captures | Broker borrow stress | Short-pressure context, with explicit gaps |
| Approved lending provider, if later admitted | Vendor adapter under Macro's data ownership | Network lending supply/demand | Raw lending-state evidence, not vendor-score authority |
| Existing holdings owner | Existing normalized filing/ownership artifacts | Long ownership concentration | C11 reference composition; no holdings fork |
| Existing ETF/fund owner | Existing fund holdings/basket/flow artifacts | Passive exposure and scenarios | Separate overlap-aware dimension |
| Existing options owner | Existing licensed options/GEX artifacts | Modeled convexity | Reference-only reuse; preserve existing authority semantics |
| Price/security/universe owners | Canonical PIT market data and identity | Liquidity and denominator support | Shared calculations; do not create C11 identity truth |
| C11 composition | Thin, versioned evidence view | Separate dimensions and lineage | Research desk, held-risk context, eventually V3 Snapshot |
| Terminal/Prophet | Read model and product composition | Presentation only for C11 | Rights-safe display; no canonical computation or hidden veto |
| Existing evaluation owner | Preregistered experiments and prospective grading | Empirical qualification | Separate promotion decision, not automatic consumer activation |

The concrete producer paths in B are observed. Several downstream integration edges above are **proposed**, not proved deployed. Before implementation, enumerate import paths, job registrations, artifact paths and consuming keys from current source. Resolve existing branches and scientific owners. In particular, new `authority=false` fields do not prove that an older factor consumer ignores a changed data artifact. Keep current convenience snapshots byte-compatible until a separately reviewed migration.

Do not implement V3's Decision Snapshot merely to give C11 somewhere to publish. Emit an upstream artifact compatible with the accepted receipt design; current source must determine the final adapter. Keep Prophet Cell E's draft status visible and do not allow a fragility label to override deterministic entry availability. [R12–R17]

## H. Empirical validation program

### H1. Preserve the existing result without overstating it

The stored SP1-B artifact contains 229,486 events, 200 entry dates and 1,715 ticker strings. Its entry window is **2018-01-25 to 2026-05-12**. Its verdict says the base hypothesis does not replicate, making conditional branches uninterpretable under the preregistration. Its current-universe price panel excludes departed names; it explicitly disclaims unbiased effect sizes. These are stored-result facts, not a rerun performed here. [R9]

Preserve that artifact, preregistration and amendments. First reproduce the original computation on its original frozen inputs if those inputs remain available. If not, report REPRODUCTION_BLOCKED and the missing hashes; do not approximate the old run and call it reproduced. Then register a separate substrate-correction experiment using unchanged hypotheses and clearly enumerated changes. A new population changes the estimand even when the code is unchanged.

### H2. Data-admission gate before outcome access

Admit a research panel only with an explicit instrument population; effective-dated identities and universe membership; delisting/merger outcomes or documented missingness; compatible corporate-action treatment; qualified feature vintages; source publication and receipt modes; appropriate historical denominators; and outcome censoring rules. Reject current sector labels presented as historical labels. Reuse the leaver substrate only within its documented limits. [R6–R11]

A complete universe is not established by counting surviving price columns. Report expected versus observed securities by date, reason for disappearance, liquidity/size/instrument cohorts and feature missingness. Do not delete difficult-to-price bankruptcies or interpret all disappearances as bankruptcies. Where lawful historical prices cannot be obtained, narrow the estimand honestly and withhold broad promotion.

Qualification tiers are `ORIGINAL_VINTAGE`, `VERIFIED_UNCHANGED_RECONSTRUCTION`, `PROSPECTIVE_CAPTURE`, `AS_RESTATED` and `UNKNOWN`. The second requires affirmative original-versus-current evidence, not merely an unset revision flag. The last two cannot support strict vintage claims. Source-knowable historical research and actual system replay must be reported separately.

### H3. Frozen baseline and estimands

Primary estimands are: (i) incremental 21-session residual-return information; (ii) incremental 21-session upper-tail risk information for short-position/lending dimensions; and (iii) incremental 21-session lower-tail risk information for long-crowding dimensions. Upper-tail risk is not labeled a confirmed squeeze. The 1-, 5- and 63-session horizons are secondary diagnostics unless a future preregistration explicitly changes the budget before outcomes are opened.

Baseline B0 includes pre-decision momentum/reversal over short, medium and long windows; size; price level; liquidity/turnover; realized volatility; beta; historical sector when qualified; earnings proximity where available; and the **existing admissible options information**. Fit residualization and normalization using past data only. Do not claim “beyond options” by dropping options for poorly covered names and failing to disclose the change.

Use two reported populations: a matched-support cohort where every compared family is admitted, and a deployment-relevant cohort with declared missingness indicators/abstentions. Explain coverage tradeoffs. Comparing a vendor's best-covered sample against a different public baseline sample is not incremental evidence.

### H4. Bounded experiment budget

Freeze this proposed first budget before any new C11 outcome computation:

| Family | Confirmatory endpoint tests | Diagnostic additions |
|---|---|---|
| Reported SI | 21-session residual return; upper-tail event | Numerator versus liquidity decomposition |
| Short-sale activity | Same two endpoints | Facility-share and momentum controls |
| Broker borrow | Same two endpoints, prospective when history is insufficient | Inclusion-filter and censored-availability sensitivity |
| Long ownership / ETF | 21-session residual return; lower-tail event | Active/passive overlap and liquidation assumptions |
| Optional commercial lending | Same two short-side endpoints only after separate admission | Provider population and vendor-model lineage |

This is **8 confirmatory tests for the four-family public program; 2 additional tests only for an admitted commercial extension**. Each uses a frozen feature bundle and model specification, not an unlimited search over transformations. Secondary horizons and variants are labeled exploratory and cannot be selected as the new primary result after inspection. Register a new experiment generation for any change.

The initial estimator should be a regularized linear/rank model for residual returns and a simple calibrated probabilistic model for tail events. Use price-defined tail labels with an ex-ante threshold rule learned only from the training window; freeze the exact threshold and execution anchor before evaluation. Models are evaluation tools, not new production scores. A semantic gate failure may terminate an experiment before any outcome is read.

### H5. Splits, leakage controls and independent contribution

Do not call already inspected SP1 history an untouched holdout. Historical development, validation and final test dates must be recorded with their prior-access status. When historical contamination cannot be excluded, prospective sealed capture is the decisive holdout. Calendar folds must purge overlapping labels at each boundary, with an embargo at least as long as the maximum tested forward horizon. Issuer identity, not recycled ticker, controls issuer grouping.

Run one-family additions to B0, the sequential public ladder, reverse-order additions and leave-one-family-out comparisons on identical support. Inspect source lineage and conditional contributions, not only raw correlations. For conditional feature permutations, preserve relevant date/cohort structure; an unrestricted shuffle can create an unrealistic null. Interaction claims are exploratory until separately powered and preregistered.

Use date-block resampling and issuer-aware dependence treatment. Twenty thousand overlapping stock-day rows are not twenty thousand independent experiments. Report raw N, distinct issuers, dates, episodes, effective independent blocks and concentration by a few events. Training, model selection, threshold choice, cohort ranks and winsorization cannot use future folds.

Negative controls include intentionally future-shifted publication clocks to demonstrate leakage sensitivity, irrelevant matched features, broken-identity fixtures and same-sample price-only reconstructions. A future-shifted positive control is never a deployable model. Preserve every failed and null result in the existing experiment registry.

### H6. Metrics, decision rules and power

For returns report OOS rank IC, incremental predictive loss/partial fit, sector/size/liquidity-adjusted spreads and stability. For tail risk report precision-recall behavior, Brier/log loss, calibration, recall at a fixed alert budget and false-positive burden. Compare confidence intervals for **paired incremental performance**, not separate significance tests that happen to differ.

Proposed statistical gate: family-level multiplicity control at 5% across the registered confirmatory family, with a dependence-aware resampling check. This is a research design choice, not a universal truth. Economic materiality and acceptable alert burden must be fixed from the intended product decision before holdout access. No result earns promotion merely because a p-value crosses a threshold.

Set sample size through power simulation using training-era prevalence and observed issuer/date dependence. Require the confidence interval to distinguish the predeclared minimum useful effect. If it cannot, the conclusion is UNDERPOWERED, not proof of no effect. An arbitrary 90-day shadow or a borrowed event-count rule from PSS-CD1 is not sufficient; that program's maturity gate belongs to its own construction.

For an avoid/de-risk use, compare the existing strategy, the same strategy excluding flagged names, and a fixed replacement/cash rule under matched exposure and costs. Avoiding a stock pays no borrowing fee but can lose upside, create cash drag and add turnover. Hypothetical short strategies additionally require executable borrow assumptions, dynamic fees, recalls, buy-ins, financing and transaction costs; C11 does not authorize such a strategy.

### H7. Promotion, demotion and kill criteria

Distinguish outcomes: DATA_QUALIFIED, CONTEXT_USEFUL, RISK_MODEL_QUALIFIED and ALPHA_QUALIFIED. Passing one does not imply the next. Passing one dimension does not promote siblings or existing consumers. Prospective performance must be compared with frozen historical expectations after labels mature; repeated threshold changes restart the experiment identity.

Stop a predictive branch when source rights or historical identity cannot support its estimand; future corrections are required to obtain its result; missingness explains the apparent effect; incremental value vanishes against momentum/liquidity/options; benefit is concentrated in one episode without replication; the uncertainty interval excludes useful benefit; or costs/false alerts negate utility. Preserve descriptive capture when it remains lawfully useful. An unstable sign can disqualify a return model while leaving a separately validated volatility model possible; do not collapse all use cases into one verdict.

**No new empirical readout is claimed in this commission.** The delivered product is an auditable experimental specification and evidence-gated masterplan.

## I. Risk register and mitigations

| Risk | Detection / mitigation | Residual limitation |
|---|---|---|
| Publication, receipt or correction leakage | Two replay modes, generation-specific clocks, sealed decisions | Original vintages may be irrecoverable |
| Current-survivor and ticker-reuse bias | Effective-dated identity, departed-name coverage, explicit delisting handling | Historical prices may remain unavailable |
| Denominator mismatch | Raw numerator/denominator/time/units retained; split-consistent tests | Free float is provider-defined and revisable |
| False market scope | Mandatory broker/network/facility scope and population version | No provider is assumed to observe everything |
| Incomplete snapshots or source freeze | Expected release calendar, receipt completeness, current decision-clock age | Source outages still cause abstention |
| Correlated evidence | Source-root lineage, matched-support ablations, conditional tests | Statistical independence is estimand-dependent |
| Selection on fee or coverage | Full lawful capture or inclusion manifest; stable-cohort analysis | Existing filtered history cannot be unfiltered retrospectively |
| Ownership overlap | Existing holdings owner resolves shared discretion and ETF look-through | Disclosed holdings omit some holders and current changes |
| Model false precision | Show assumptions/bounds and unavailable legs; no unearned probability | Actual dealer books and covering trades remain unobserved |
| Vendor lock-in | Neutral schema, raw-field provenance, termination/export rights | Proprietary models may remain non-portable |
| Rights and sensitive material | Explicit use-class admission; no raw vendor/private corpus in public GitHub | Retrieval access alone does not establish a license |
| Product authority creep | Consumer contract audit, negative tests, no hidden rank/gate wiring | Human interpretation can still overreact to labels |
| Regulatory drift | Recheck official release/schema before activation | Announced dates can move again |
| Research optional stopping | Frozen budget, prior-access ledger, all nulls retained | Very rare events may require long prospective observation |

FTD data warrant a particular boundary: an outstanding settlement-failure balance is not a new-flow count or evidence of naked shorting. Do not sum daily outstanding balances as cumulative new fails. An exchange threshold list is another settlement-status artifact, not a short-book census. Neither source has demonstrated incremental C11 value here. [P21]

## J. Build priority

**P0A — prevent irreversible information loss.** Qualify source rights; retain immutable future SI, short-volume and IBKR captures with source/receipt clocks and identifiers; preserve legacy artifacts without relabeling them; add completeness, freshness and correction receipts. Scope stays under existing producers, initially inert to consumers.

**P0B — make research questions answerable.** Resolve current owners/collisions; inventory actual historical vintages, identities, universe membership, delisting returns, denominator history and options support; quarantine invalid PIT claims; specify the minimum credible historical estimand. This work can run independently of P0A without opening outcomes.

**P1 — public evidence and controlled evaluation.** After admissions, implement separate descriptive dimensions and reference existing ownership/options artifacts. Reproduce SP1 if its frozen inputs permit, register substrate changes, run the bounded validation program and prospective shadow. No broad historical promise for IBKR's short local capture period.

**P2 — targeted commercial and auxiliary studies.** Separately authorize source samples or a paid pilot only with a named missing capability, rights, budget and comparison protocol. Evaluate FTD, richer holder-flow and rebalance information only under additional hypotheses. A successful data-quality purchase need not be represented as an alpha victory.

**Defer:** broad international expansion; intraday multi-prime aggregation; complex squeeze ML; self-built options engines; Form SHO/SLATE features before actual publication; all-market utilization without a valid denominator; calibrated squeeze probabilities without sufficient labeled evidence.

**Reject:** short volume as SI; broker availability as market supply; settlement-date information joins; restored current values masquerading as original vintages; current-only universe/sector/float applied historically; uncensored infinity; one fused cross-family vote; vendor backtests as Mastermind validation; LLM-generated canonical numbers; any new crowding authority path under this research commission.

## K. Sequenced implementation recommendation

| Phase | Owner boundary | Deliverable | Acceptance / stop condition |
|---|---|---|---|
| G0: acceptance and fresh source | Existing program/source owners | Accepted research identity, current pins, collision map, rights scope | Stop on ambiguous owner or conflicting protected law |
| F1: capture contract | Existing Macro collector/data owner | Native capture envelope, immutable receipts, coherent snapshot manifest | Casebook temporal, identity, censoring and completeness cases pass; consumers unchanged |
| F2: historical feasibility | Existing security/price/research owners | Per-family coverage/vintage matrix and realistic estimand | No invented original vintages, historical sectors or delisting values |
| F3: public evidence | Existing short/ownership/options owners plus thin C11 composition | Independent context objects and contradictions | Scope/rights/freshness exposed; missing does not mean safe |
| F4: experiments | Existing evaluation owner | SP1 reproduction status, frozen C11 tests, null-inclusive readout | Data-admission, access-history and statistical/economic gates satisfied |
| F5: optional provider pilot | Data-rights/procurement owner plus evaluator | Raw-field bake-off, coverage/rights/cost comparison | Separate approval; fail closed on retention or original-vintage ambiguity |
| F6: prospective shadow | Existing evidence/evaluation consumers | Sealed daily evidence and matured evaluation | Power and alert burden sufficient; no automatic promotion |
| F7: independent authority decision | Canonical portfolio/Prophet/Eval owners | Per-dimension, per-consumer promotion or rejection | Separate commission and authority law; no bundled promotion |

F1 and F2 may proceed in parallel after G0. F3 does not need F2 to manufacture historical completeness: it can initially emit honest prospective context. F4 cannot use inadmissible history simply because implementation capacity is idle. F5's schema/rights feasibility may happen earlier under explicit authorization; opening labeled vendor outcomes waits for its frozen comparison protocol.

Do not provide false calendar precision. Size work only after owners inspect current artifacts and schemas. The first implementation wave is deliberately smaller than the original follow-on: no universe rebuild, broad feature factory, vendor integration, evaluator replacement or production consumer switch.

Rollback is append-preserving: disable the new shadow producer or restore a consumer pointer through its existing owner, but never delete captured vintages to recreate the old world. Historical retractions and corrected views remain auditable. Migration acceptance distinguishes byte-identical old outputs from intentional changes, each separately approved.

## L. Exact bounded follow-on implementation commission

> **Issue only after this research is accepted. This text has not been executed.**

### C11-F1 — Immutable capture and replay-contract qualification

**Mandate.** Under the existing Macro source/data owners, implement a bounded, consumer-inert capture foundation for FINRA reported short interest, FINRA daily short-sale activity and the existing IBKR shortable snapshot. The outcome is recoverable source generations with truthful identity, scope, clocks, correction lineage and rights—not a production crowding signal.

**Required start.** Follow the then-current Mastermind bootstrap/source law. Pin Mastermind and Macro; consume current INDEX and applicable procedures from the same protected Mastermind revision. Record the immutable accepted research commit, this commission identity and current owner/collision checks. Reconcile SP1/PSS and Prophet Cell E without rewriting their scientific identities. Post required pickup/START receipts only through the existing operational owner after gates clear. Do not create a new task, retry or orchestration registry.

**Admission.** Confirm rights for retention, internal processing and intended storage. Public/keyless retrieval is not a rights grant. Stop the affected source if rights are unresolved; continue independent schema/test work. Inspect the actual current raw format and any existing source-receipt contract before creating a new field. Select at most the three existing producers above; no vendor purchase or new source-family integration.

**Allowed changes.** Add or adopt the common envelope and immutable content-addressed capture/manifest behavior. Retain provider identifiers and raw source timestamp; record actual observation, persistence and validation clocks separately. Distinguish regular snapshots, identical re-fetches, corrections and retractions. Preserve coherent file/page generations; check source footer/counts where available. Represent IBKR quantity bounds honestly and retain source scope. Provide a read-only replay query or contract-level adapter proving source-knowable and actual-system modes do not collapse into one.

**Historical boundary.** Inventory existing SI/volume/borrow archives without relabeling them. Keep as-restated data explicitly as-restated. No historical backfill claim without original-generation evidence. No new market-outcome run, survivorship reconstruction or SP1 redesign in this wave. A separate F2/F4 owner handles those tasks after admission.

**Consumer boundary.** No changes to current ranking, gate, allocation, execution, paper-account or product policy. Preserve current convenience outputs until a separately reviewed consumer migration. Do not add a squeeze label, probability, composite, agreement count used for decisions, GEX engine, security master, Decision Snapshot implementation or Terminal-owned canonical calculation.

**Required proof.** Deliver exact source/base/head identities; changed-path list; source and normalized schema samples using synthetic or lawfully retained data; rights receipts; deterministic duplicate/correction/retraction and incomplete-pagination tests; publication-versus-settlement and receipt-delay tests; censored-availability and missing-value tests; same-ticker/different-listing cases; source-freeze detection; immutable legacy-output comparison; and a consumer/import/config diff establishing no new authority wiring. Use the acceptance casebook as required scenarios, not as a substitute for testing the real owner integration.

**Operational acceptance.** Publish a scoped PR under the existing repository workflow. Bind tests and review to the exact candidate head. Do not merge, deploy or start scheduled production capture merely because the report contains this commission; obtain the separately required implementation and operational approval. Report SOURCE_ONLY / BUILT_NOT_PROVEN until real runtime receipts support stronger claims.

**Stop conditions.** Stop and return the exact blocker when source ownership conflicts, schema semantics cannot be resolved, rights fail, original history is being invented, mutable source pages cannot produce a coherent generation, changes would widen authority, or current protected law conflicts with the accepted design. Do not substitute another source or reset an experiment to hide the blocker.

**Success.** The three existing source families have a reviewed, tested, lossless capture/replay foundation that can preserve new observations without changing investment behavior. Success does not mean historical alpha, full-market utilization, a reliable squeeze forecast, or permission to trade.

---

## Completion boundary

This research delivers a current-source recensus, documented static defects, primary-source regulatory corrections, a typed temporal architecture, a bounded validation program, phased owner-compatible recommendations and an exact first implementation commission. It does not certify production liveness, reproduce SP1, open vendor samples or demonstrate new predictive value. Those limitations are explicit gates in the plan rather than silently deferred assumptions.
