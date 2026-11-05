# Commission 15 — Equity & Options Microstructure Evidence
## Hardened research and implementation recommendation · 2026-10-04

**Status: RESEARCH_COMPLETE / IMPLEMENTATION_PROPOSAL / NO NEW DECISION AUTHORITY.**

This is the complete A–L research commission. It supersedes the recommendations in the uploaded *deep-research-report (19).md* for this commission; it does not supersede protected source law, accepted historical evidence, or an incumbent owner's implementation gates. The audit covers source revisions observed on October 4, 2026. It uses current code, current adjacent program records, official source specifications, and primary research. It does not claim new vendor access, a new empirical result, or current production health from documentation.

**The recommendation is to qualify and extend existing owners, then test a small set of inspectable observations.** The initial job is not to purchase a replacement options tape or create a new market-data plane. Current Macro already contains the canonical ThetaData options store and a measured trade/NBBO path. The Terminal Quote Plane owns the existing shared quote service. Macro owns derived market intelligence and Live Entry Radar owns its event and episode lifecycle. These are different functional boundaries, even when implementations share a repository or host. [M01] [M02] [M03]

### Reading guide

- This file: complete executive recommendation, current state, sources, contracts, intelligence, integration, evaluation, risks, priority, phases, and bounded follow-on commission.
- [Current-state census and hardening log](CURRENT_STATE_AND_HARDENING_LOG.md): exact repository pins, current-versus-historical distinctions, adjacent carriers, and the changes made to the attachment.
- [Primary-source register](SOURCE_REGISTER.md): source-specific coverage, date/version limitations, regulatory changes, rights, costs, and stable primary-source links.
- [Validation protocol and contract examples](VALIDATION_PROTOCOL.md): explicit estimands, proposed thresholds, temporal fixtures, power/falsification program, and acceptance matrix.
- [Evidence manifest](EVIDENCE_MANIFEST.json): input digest, pinned internal source identities, and documentation-only change inventory.

The capitalized status terms below describe the scope actually supported by evidence. A source file can establish implementation, a dated receipt can establish an accepted historical result, and a contemporary operational read can establish present health. Those are not interchangeable.

# A. Executive conclusion

## A1. What Mastermind should build

Build a **microstructure evidence capability through the existing quote, options, Radar, and evaluation owners**, with four separable products:

1. **Execution-context observations:** eligible trade counts and magnitude; pre-trade quote location; spread and displayed size at trades; price-conditioned signed-trade proxies with explicit abstention.
2. **Liquidity-state observations:** time spent at wide spreads, top-of-book depletion, event-based order-flow imbalance, and recovery after shocks. These require a continuous qualified quote stream; a quote attached only to a trade is insufficient.
3. **Options structure and positioning observations:** causal IV/skew/term structure, strike/expiry concentrations, published OI changes, source-linked package facts when available, and separately labelled inventory/Greek scenarios.
4. **Consumer evidence windows:** source-receipted, quality-gated observations bound to the incumbent dislocation or entry decision cutoff. The existing consumer decides what those observations mean; the new capability creates no event lifecycle, portfolio policy, universal score, or trading authority.

The first investment should be in **measurement validity and actual consumption of existing data**. The research found an obsolete no-tape premise, already-completed repairs, accepted observations that should not be rerun, and an unmerged Portfolio Snapshot implementation omitted by the attachment. Buying another feed before resolving these facts would increase data volume without establishing a better decision. [M01] [M04] [M05] [M06]

Priority is high for avoiding poor entries, diagnosing fragile liquidity, and distinguishing short-lived dislocation from price acceptance. Priority is conditional for incremental stock-selection alpha. Microstructure cannot independently establish fundamental value, beneficial ownership, forced-sale necessity, or dealer inventory. Its strongest immediate role is measured timing, abstention and explanation.

## A2. The decisive changes to the original plan

| Original weakness | Hardened ruling |
|---|---|
| Old Massive options probe treated as the current estate | Start with the existing ThetaData resolver, measured trade/NBBO contract, and current Options Intelligence work. Massive catalog capability and historical entitlement failures remain separate facts. |
| Generic assertion that Macro owns all market data | Preserve Terminal Quote Plane authority for the shared quote service; Macro consumes that service and owns derived intelligence. Options source ownership remains with its existing Macro/Theta owner. |
| A new list of universal trade/quote/option schemas | First map required fields to existing contracts. Add only missing leaf fields or a compatible owner-approved revision. No new raw-tape owner, identity authority, replay service, or receipt registry. |
| Trade-with-BBO pilot promises continuous OFI/liquidity metrics | Separate trade-sampled, time-sampled, and quote-event data. Features fail admission when their sampling requirement is unmet. |
| Quote-rule agreement called directional accuracy | Name the estimand: quote concordance, native initiator accuracy, customer demand, position effect, and predictive utility are distinct. |
| Future markouts included in the feature list | Future response/realized spread are labels. Only already-matured trailing outcomes can be features. |
| Known time conflated with historical event time | Separate actual Mastermind possession from hypothetical historical receivability and final-vintage research. |
| One effective-date test at decision time | Join instrument/reference validity at the relevant event's valid time; select assertion/correction generations by decision knowledge time. |
| Depth products treated as interchangeable | NYSE Pillar Depth is sampled/group-aggregated depth; native event/cancellation questions require an appropriate event feed. |
| Generic source-cost classes and old rule references | Include dated fee examples and separate operative 2025–2026 changes from announced 2027–2028 changes. |
| Broad P0 implementation commission | Issue a bounded incumbent qualification and offline measurement wave first. Full quote-event capture, auction studies, consumer shadowing and depth challenges have separate gates. |

## A3. Minimum data for the five requested explanations

These are **nonexclusive hypotheses**, not a classifier whose five probabilities must sum to one. A fundamental repricing can coexist with dealer hedging and depleted liquidity.

| Explanation | Minimum useful microstructure evidence | Independent evidence required for a stronger claim | What must remain unknown |
|---|---|---|---|
| Fundamental repricing | Sustained price acceptance, spread/liquidity state, post-event response, direction/magnitude with coverage | PIT earnings, guidance, filing, product/economic or analyst-expectation change with original release/receipt clocks | Tape alone cannot identify a fundamental cause or intrinsic value. |
| Liquidity dislocation | Valid spread/size history, depth depletion or impact-response change, subsequent recovery; market/sector controls | Status/halts and source continuity; direct depth only when cancellation/replenishment is the question | Displayed liquidity is not hidden liquidity; temporary price reversal is not proof of a unique cause. |
| Forced selling | Selling pressure, liquidity stress and timing around a candidate mechanical event | Observed rebalance, redemption, mandated liquidation, margin/fund event, or another independent constraint | Anonymous sell pressure does not identify who was forced or whether selling was discretionary. |
| Accumulation | Repeated buying or passive absorption proxies, resilience and persistent demand over declared windows | Participant/customer-side labels, lawful ownership evidence at its actual publication time, or independently identified sponsor evidence | Aggressor buying, a block, an ATS print, or a lagged 13F does not prove institutional accumulation. |
| Derivatives-driven move | Causal options/underlying quote context, expiry structure, IV/skew, exposure sensitivity, optionally participant/position-effect labels | Scenario assumptions and independent underlying/catalyst controls; subsequent observation of expected hedging response | Public OI and quote-signed trades do not disclose net dealer inventory or all OTC/cross-asset offsets. |

Present the evidence for and against each explanation, the unsupported identification step, and the next observation that would discriminate them. The output should help the user decide whether an entry is timely or too uncertain, while retaining the existing decision authority.

# B. Current-state census

## B1. Source scope and pins

| Estate | Exact audit revision | What was established |
|---|---|---|
| Mastermind master | 521720b09be2921e996d9396b522b1c4ca62041c | Protected branch; compatible Skillpack 1.0.1 from this same commit, including ACTIVE_EXECUTION and SESSION_RELIABILITY. Portfolio/lenses, held risk, research desk, fundamentals and daily panel inspected. |
| Macro main | 59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc | Current source and relevant research/contracts/Agent OS records; branch API reported protected=false. Do not call this a protected Macro revision. |
| mastermind-terminal master | 1c708450187755160e1a5889b69598a2fcb1f0d1 | Protected branch; dislocations source/route/types and Quote Hub documentation inspected. |
| Research Vault | Macro subsystem engine/research_vault/ at the Macro pin | Private-R2 ingestion, catalog and FTS content system; no signal/score/escalation authority. A separate research repository is not required or inferred. |
| executive-dr-vault | ea422c92bd29800d1f7fb3ae850236cc44d8c890 | Distinct Executive disaster-recovery export repository; README-only tree inspected. Not the market Research Vault. |

The preliminary handoff's Mastermind d1594f3… and the attachment's a2646f4… are historical pins, not current procedure. The attached report's references to unavailable conversation citation identifiers are replaced here by stable file/PR/primary-source references. No private vault corpus was read. [M07] [M08]

Final-cut reconciliation preserved these immutable audit citations. Macro main was observed at 0bbc246fe1c023684bb36ae2ac7795668eafef97 at 08:24:45 UTC; all 30 sampled decisive owner/source blobs were unchanged. Mastermind protected master was observed at 17b9fa1363db6071d338be3373a4fdb11fc0076d at 08:27:36 UTC; all 18 sampled governing procedure and decisive source blobs were unchanged. Terminal's protected master remained at the cited revision. Six selected open/draft adjacent PRs retained their heads/statuses. Exact comparison receipts and the bounded scope of this check appear in the evidence manifest.

## B2. Relevant capability ledger

| Capability | Current source/evidence ruling | Implication |
|---|---|---|
| Existing Macro options source | Canonical ThetaData store/resolver and EOD/OI/Greeks tiers exist. T1/AD-1T1 has accepted historical PROVEN_LIVE evidence; current selected-consumer admission and integrity are separate. | Audit existing content and permissions; do not build a second options store. |
| Measured options trade/NBBO | OA-1T implementation exists. Accepted untouched September 17/18 source-to-stage-to-Flow evidence is recorded; remaining completion concerns include durability/integrity/publication. | Preserve accepted evidence and investigate the exact unresolved gate, not another event hunt. |
| Legacy EOD bar-based options direction | Legacy code itself acknowledges the no-tape premise is obsolete for the estate while that particular engine remains bar-based. | Keep bar-based magnitude useful and directional limitations local to the actual path. |
| Sweep versus multileg semantics | The former swept-to-MULTI_LEG defect is already repaired on current main; qualified package evidence is still required. | Preserve repair #7417 and its current behavior. A same-contract sweep is not a package. |
| Flow source clocks | #8201 is merged; source-event diagnostics are distinguished from feature/stage availability clocks. | Extend those fields and the current FS5 consumer contract rather than substitute source event time for decision availability. |
| Options candidate/evaluation lanes | Candidate core/publisher and exact-option evaluator have advanced in source; activation/method gates remain distinct. | Do not create another candidate feed, backtest engine or undocumented holdout. |
| Current options publication example | Pinned site/options_intel_brief.json still describes August 19, 2026; it reports 39/375 and INSUFFICIENT_COVERAGE. | This proves staleness of that repository artifact, not today's host-store coverage. Never generalize its 10.4% to the live estate. |
| Canonical OI history | Existing OI store and historic coverage evidence exist; a fresh content-level coverage/known-time census was not obtained in this research. The repository manifest is an empty stub. | Current root/date coverage and receipt fidelity are an input-qualification gate; neither “zero history” nor “complete history” is justified. |
| Shared equity quote service | Terminal Quote Hub exists; Macro dossier projection explicitly retains Terminal Quote Plane authority. Its documented US modes include delayed/per-second aggregates and a last-trade snapshot leg. | Existing service ownership is established; full consolidated trade/quote-event history is not proved by a latest-price endpoint. |
| Macro quotes.live | Latest-only snapshot contract with whole-file replacement; source timestamps can be synthetic and the wire projection does not preserve every internal timestamp diagnostic. | Not a historical event tape or a valid substitute for an original receipt. |
| Intraday Dislocation + Reclaim | Existing Macro Radar detector/episode owner and Terminal consumer exist. Recent sink/state/catalyst work is distinct from qualifying the producer's current pack and end-to-end consumer. | Reuse episode identity and no-rebuild law. Do not manufacture a new detector or infer freshness from a merged PR. |
| Portfolio V3 Snapshot | NOT_BUILT in protected/default-tree ledger. A separate open draft S0 implementation exists in Mastermind #673 at 0b960590c77101b3f3b5545896423f9ad07b7d56. | Preserve the incumbent draft; no substitute Snapshot or activation. |
| PIT fundamentals and survivorship-aware daily panel | Source implements filing-as-of selection, retained delisted names and PIT membership. This is daily research infrastructure. | Reuse identities and PIT intent, but do not import daily fill/return-neutralization rules into executable intraday labels. |
| Earnings expectations | held_risk contains an earnings_expectation lane, SUE/PEAD and revision fields. | Existing expectation evidence is a control/independent family; a revision field does not prove mature historical analyst vintages. |
| Research/lens reasoning | Existing lenses reject an opaque weighted blend; research desk retains deterministic downstream constraints. | Keep features inspectable and models away from raw tape arithmetic or sizing. |

Source support: [M01] [M04] [M05] [M09] [M10] [M11] [M12] [M13] [M14] [M15] [M16].

The October 4 installed-source receipt records **AD1 INSTALLED_CANARY_ACCEPTED_PRODUCTION_HOLD**: selected-workflow organization admission was unavailable and the recorded M1 free disk was below 200 GiB. This is a dated repository receipt, not a new host measurement. Candidate v2 exists but remains inactive, with all fifteen authority flags false. Its four named prerequisites are oa1t_measured_source_consumer_proven, ad1t2_consumer_availability_production_accepted, campaign_integrity_publication_runtime_accepted, and source_collision_review_clear. A feature diagnostic clears none of these gates. [M38] [M22]

The static Mastermind census was generated July 16, 2026 against 131290a. This is a genuine documentation-freshness finding. It does **not** establish that every contemporary lane lacks health instrumentation. This commission should produce a narrowly scoped microstructure input census and consume existing health fields; a global observability rebuild is outside its scope. [M17]

The preliminary observations about historical analyst revisions, dynamic subtheme identity and institutional-flow maturity are relevant context, not permissions to create those data families here. Existing GMI, expectations and structural-flow work must be treated as adjacent owners. This audit verifies their relevance and current microstructure dependencies; it does not certify their historical data completeness from a headline or expand into their research commissions.

## B3. Adjacent work and no-redo boundaries

- **Options C0:** #6604 is merged, not an open planning carrier. Its accepted flow → package → positioning → candidate → outcome → calibration boundaries remain relevant.
- **OA-1T:** #6576/#6585 and the current recovery workstream own measured trade/NBBO. The September 17/18 accepted observations are preserved. Reuse an equivalent accepted result when scope, inputs, definition and receipt integrity are unchanged. Replay only the exact delta needed for a new or currently unqualified claim, or a named material invalidator; never hunt for a replacement acceptance event.
- **OA-2R:** the completed Theta EOD retrospective association v1.1 study records 60 registered evaluable cells and three within-family BH rejections, with accepted protocol/result/input-manifest receipts. This bounded completed result does not open PIT/known-at, fresh OOS, exact-option economics or production/promotion gates. Preserve its estimand and trial history before considering another EOD association study. [M04]
- **Options repair/validation:** #7417, #8201, #8203, #8318, #8345, #8358, #8377 and the still-unratified #8385 methods carrier must not be flattened into one “options complete” claim.
- **October 3 options research:** the existing research/options_intelligence/2026-10-03 package already covers sources, mechanics, source admission, pilot study and GEX evaluation. Commission 15 supplements its equity/continuous-quote/causal-measurement questions; it does not create a rival options masterplan.
- **Radar and dislocation:** existing Live Entry Radar, fundamental dislocation source research, and Intraday Dislocation + Reclaim are distinct but adjacent. Link evidence to their identifiers, not title-matched synthetic events.
- **Narrative handoff microstructure #8012:** a separate research lane. Shared raw features may be reused; its event sample and hypothesis are not automatically this commission's evaluation universe.
- **Portfolio V3 #673:** active draft source custody and unresolved gates are preserved.
- **Research Vault:** third-party report ingestion remains a content subsystem. It is not a substitute tick store or a newly authorized source of predictive features.

The detailed carrier status and evidence limits are in the census companion. These facts are navigation and evidence, not source-write custody transfers. [M01] [M04] [M05] [M06]

# C. State-of-the-art research and institutional implications

## C1. Measurement before prediction

Cont, Kukanov and Stoikov's order-book event study motivates event-level OFI and liquidity depth as useful explanatory dimensions. Its core relationship is contemporaneous: the imbalance and price change inhabit the same short interval. That does not prove that an OFI value known at the end of one interval predicts the next interval, or that a strategy can trade the observed movement. Mastermind must preserve that time ordering in every empirical claim. [E01]

Trade classification has two separate problems: correctly selecting the quote context, and deciding what inference is justified from it. Options-specific research using proprietary direction labels shows that performance varies by method and classifiable sample. Coverage denominators, market structure and complex trades matter. A quote rule is a benchmark with errors, not universal ground truth. [O28]

The newer Grauer–Schuster–Uhrig-Homburg working-paper abstract explicitly separates **customer demand** from liquidity-taking side: a customer can buy passively while a market maker initiates the execution. Only the current abstract/metadata were verified, so this report draws the conceptual distinction, not a numerical replication claim. [O29]

Pan and Poteshman's opening-volume result relies on a distinctive participant/opening dataset. Their public-signal analysis differs from that headline result. It supports a targeted investigation of participant-labelled evidence; it does not license transferring the published return spread to today's anonymous all-OPRA tape or interpreting quote-rule agreement as customer-opening accuracy. [O30]

## C2. Derivatives mechanics need scenario discipline

Gamma fragility research offers a plausible interaction between hedging exposure, liquidity and intraday response. The empirical exposure is a proxy under assumptions, not a census of every dealer's inventory. Open interest includes positions held by several participant classes, and public trades omit many offsets. [O31]

Mastermind should calculate gross sensitivity and a small number of explicit inventory scenarios. Scenarios are neither observed dealer positions nor confidence intervals. If plausible allocations reverse the sign, preserve that disagreement. A robust relationship may be worth testing even when net dealer sign is unidentified.

For surfaces, arbitrage-aware fitting provides useful consistency checks. However, a smooth curve is not evidence of fresh quotes or correct exercise/dividend assumptions. Gatheral–Jacquier's SVI work motivates constraints; applying a European formulation to American equity-option observations without accounting for early exercise is not automatically valid. [O32]

## C3. SIP, direct feeds and the right resolution

For current five-minute-to-multiday decision support, consolidated trade/quote evidence is the sensible national baseline **when the selected product actually supplies it**. A vendor-normalized “consolidated BBO” may aggregate its dataset's venues rather than represent the official SIP definition. A venue BBO, official protected NBBO, better-priced odd-lot quote, and source-derived composite require distinct scope and method fields. [E02] [E03] [E04]

Direct equity feeds become relevant when the question requires venue-level depth, order addition/cancellation, replenishment or auction detail unavailable in the chosen consolidated stream. An order-event feed and a sampled ten-level product answer different questions. Direct options depth is a later research choice; participant/open-close detail may address the missing inference more directly than additional book levels. [E05] [E06] [O17] [O18]

There is no assumption that lower latency always improves Mastermind. A lower-latency predictor requires a lower-latency admissible decision and a realistic execution benchmark. A 15-minute-delayed consumer cannot claim the benefit of a millisecond source merely because both are present somewhere in the estate. The existing Terminal dislocation display explicitly carries a delayed-data badge. [M12]

## C4. Current rule and archive regimes must be versioned

At this audit cutoff, variable round-lot assignments and 2026 odd-lot top-of-book changes are distinct from later depth and tick-rule changes. The June 11, 2026 SEC order defers the amended half-cent minimum increment and reduced access-fee caps to the first business day of November 2027. A separate January 15 order defers full odd-lot depth inside NBBO to May 2028. Do not treat the older adoption schedule as current behavior. [E07] [E08]

The September 2026 UTP specification also requires attention to fractional quantity encoding and distinguishes operative changes from planned 23/5 hours. Round-lot assignment is an effective-dated listing-market reference; it must not be recalculated from each intraday spot price. [E04] [E09]

Historical archives are mutable in practice. Databento's September 30, 2026 notice schedules retroactive Nasdaq identifier, after-hours and snapshot changes for October 31. On October 4 this is an announced future revision. The implication is to record source archive vintage and raw/input digests, not to presume the future repair has occurred. [E10]

# D. Source landscape and economic selection

Every row below distinguishes an **observed documentation capability** from an **observed Mastermind entitlement**. Documentation has been read; no new licensed sample was acquired. Exact contracts, reseller arrangements, approved users, retention and derived-use terms remain source-admission evidence. Cost classes are planning categories, not quotes.

| Source | Coverage | History | Latency | PIT quality | Corrections | Rights | Cost class | Best use |
|---|---|---|---|---|---|---|---|---|
| Existing ThetaData options lane | Incumbent OPRA options pipeline; actual roots/tiers must be inventoried | Existing retained history; public Standard/Pro dates differ | Incumbent EOD, historical and trade/NBBO paths; exact live mode/config must be observed | Candidate for actual replay only where original receipt/generation exists | Condition dictionary exists; complete historical correction replay still requires proof | Executed current agreement and retained-derived-data rights required | Existing spend; business terms additional | First source to qualify, not replace |
| ThetaData public trade_quote | OPRA trades and attached NBBO with conditions and millisecond clocks | Cataloged tick history differs by tier | Historical request; streaming is a separate product | Strict/inclusive joins and same-millisecond ambiguity require explicit selection | A condition code is not proof of original-to-corrected linkage history | Plan access does not equal commercial redistribution/retention permission | Commercial quote; public business headline is not all-in | Incumbent field/config parity and clock tests [O1] [O2] [O3] [O4] [O5] [O6] [O7] [O8] [O9] |
| CTA/UTP through an entitled redistributor | Official US NMS consolidated trades/quotes, era-specific NBBO/odd-lot fields | Archive and field era dependent | Real time if entitled; archive separately delivered | Strong source primitives; actual archive vintages and collector receipts must be demonstrated | Native cancel/correct/condition semantics | Display, non-display, retention, derived and distribution terms apply | Medium/high, use-specific | National equity baseline under the existing Quote Plane [E03] [E04] |
| NYSE Daily TAQ | Consolidated US historical trades/quotes | Product/date/field-specific archive | Previous-day historical product | Useful benchmark; revised history is not automatically as-seen history | Require current file and correction specification | Commercial historical license | Quote required | Alternative to immediate direct-feed procurement [E11] |
| Databento OPRA.PILLAR | All-OPRA normalized trades/consolidated top-of-book | TCBBO/CMBP-1 from 2023-03-28; older trades/one-minute CBBO from 2013-04-01 | Historical and live offerings differ | ts_event is OPRA consolidator block time; pre-2023 receipt substitutions must be flagged | Current schema/roadmap does not establish native condition/cancel-link completeness | Publisher-specific restrictions and use agreement | Usage plus applicable recurring/exchange costs | Independent quote-location comparator, subject to field-loss audit [O10] [O11] [O12] [O13] [O14] |
| Cboe Option Trades | All-OPRA US stock/ETF/index option prints with vendor NBBO; optional Greeks | Catalog says January 2012 onward | Daily/batch; intraday inquiry separate | Quote-age and underlying alignment need written/sample clarification | Specification's cancellation representation differs from a complete generation ledger | Licensed historical use; some index values need additional rights | Medium/high; quote required | Long-history signing comparator, not assumed receipt truth [O15] [O16] |
| Cboe Open-Close | C1/C2/BZX/EDGX participant, buy/sell, open/close summaries | Uneven EOD/intraday start dates across venues | EOD and intraday interval products; publication clock is decisive | Observed venue sample, not marketwide customer flow | Documented historical conventions and announced future cancellation change | External derived redistribution needs agreement | Commercial specialty | Customer/position-effect evidence and validation labels [O17] |
| Enhanced Cboe TBT | Currently C1, participant-side and execution detail; covered complex links | Catalog says 2019-10-07 onward | T+1 | Useful later labels; cannot enter same-day decisions as observed input | Native execution linking and publication/version still require qualification | Commercial proprietary data | Specialty/quote required | Participant/package measurement benchmark; deduplicate two sides [O18] [O19] |
| Massive options | Public trade/quote products; retired as canonical options source in current program | Trades from 2014-06-02; quotes from 2022-03-07 in catalog | Tier dependent | Joint feature history starts no earlier than required overlapping inputs | Documents conditions/correction/timestamps; original-vintage availability unproved | Current business agreement required; old/retail access is not a current grant | Challenger only if justified | Catalog alternative, not incumbent reactivation [O20] [O21] [O22] |
| OCC/OIC reference and OI | Official cleared OI/reporting and adjusted-contract guidance | Dataset-specific | Daily/publication-dependent | Correct reference and publication semantics matter more than date labels | Series adjustments and corrected publications must be retained | Dataset/use terms; automation not inferred | Low/public to licensed delivery | Validate OI meaning, deliverables and exercise/settlement assumptions [O25] [O26] [O27] |
| FINRA OTC transparency | Delayed ATS/non-ATS aggregate activity | Multi-year public context | Generally two/four-week publication categories, not intraday tape | Valid only after publication | Published revisions possible | Public terms and automated-use requirements | Low | Delayed context; cannot identify current dark-pool buying [E12] |
| IEX HIST | IEX venue only | Rolling 12 months documented | Free T+1 equities files | Useful format tests, not national NBBO | Source-native replay still needs qualification | Attribution/terms apply | Low | Structural fixtures and venue-specific research [E13] |
| Nasdaq TotalView/NOII | Nasdaq depth/auction information within chosen product | Feed/archive version dependent | Direct/live or licensed archive | Native sequence/recovery and exact venue coverage required | Event and archive semantics vary | Proprietary product/licensing | High | Narrow Nasdaq depth or auction challenger [E14] |
| NYSE Integrated | Native venue order-event/trade context | Licensed product/archive dependent | Direct | Appropriate event-level question if input proven | Recovery/rebuild/corrections must be tested | Access/non-display/distribution categories | High/very high | Selected-venue cancellation/replenishment study [E06] |
| NYSE Pillar Depth | Frequency-based ten-level group aggregation | Product dependent | Sampled updates | Sampled depth, not native event reconstruction | Product-specific | Proprietary | High | State-depth challenger only [E05] |
| Standalone auction imbalance products | Primary-venue auction states and indicative values | Feed/archive dependent | Auction-window updates | Auction phase and actual dissemination clocks | Venue rules/corrections | Separate narrower products may be economical | Lower than broad depth, still licensed | Auctions without a national depth build [E15] |
| Direct options depth | Particular exchange book/auction state | Product dependent | Direct | Venue-local; not hidden or all-market book | Source-native contract required | Multiple venue agreements scale cost | Very high at national scope | Defer until a named top-of-book failure justifies it |

### D1. Procurement decisions must be capability-specific

The first comparison is **incumbent coverage versus the exact question**, not vendor brand against vendor brand. A trade-with-NBBO comparator may help validate quote-location measurements. Customer/open-close labels may help a different demand question. A full quote stream is needed for intervening liquidity. A standalone auction feed may be sufficient for auction stress. Direct depth is not the inevitable next step.

For any proposed source, require a quote naming the same instruments, dates, schemas, sessions and use rights that appear in the pilot. Include historical extraction, recurring service, plan/exchange fees, non-display use, display users, external distribution/derived rights, storage/egress, retention after termination, and operational support. A consumer-facing terminal price cannot be used as the budget for an analytical service.

Dated scale examples from NYSE's May 14, 2026 guide illustrate why this matters: Integrated lists $8,400 monthly access and $22,400 for a relevant non-display category; Pillar lists $5,000 access plus a $10,000 non-display category, with other line items; standalone Order Imbalances lists $500 access and $2,000 for a relevant non-display category. These are published examples, not a statement that all categories apply to Mastermind or an all-in reseller quote. [E16]

Storage should be estimated from an authorized sample, with event count and encoded size actually measured. A planning illustration of 50 million 64-byte records is 3.2 GB per session, about 806 GB over 252 sessions before indexes, replicas, raw payloads and egress. This arithmetic is not an estimate of OPRA's actual event rate. Decoding, sustained peak rate, slow-reader loss and correction handling must be costed along with bytes.

**No purchase is recommended for execution in this research commission.** The later owner may request procurement only when the incumbent cannot answer a defined question and the expected incremental utility plausibly covers the full burden.

# E. Canonical data model and temporal semantics

## E1. Extend the existing contracts; do not mint a second system

The attachment's nine universal event/snapshot schemas are a requirements inventory, not a reason to install nine new authorities. The initial implementation must produce a field-by-field reuse/delta map against the incumbent source and consumer contracts.

| Required object | Existing home / interface to inspect first | Minimum additional semantics, only when absent |
|---|---|---|
| Options source data and identity | ThetaData collector, thetadata_store resolver, existing option-reference conventions | Source/API/terminal version, scoped source identity, exact units, received/available clocks, correction/condition fidelity |
| Trade/NBBO measurement | engine/live_flow.py measured block; options.trade_nbbo_microstructure/v1; scripts/build_options_alpha_candidate_feed.py::_microstructure receipt adapter | Quote scope/sampling, join rule/clock basis, precision/age/ambiguity, estimand class, correction lineage and receipt references; flow_signing remains the separate signing/comparator path |
| Options event/feature availability | Existing live_flow event-stage and FS5 availability contract | Do not overwrite stage availability with source-event diagnostics; propagate constituent cutoffs and derivation completion |
| Shared equity source access | Terminal Quote Plane/Quote Hub owner | Qualify a missing historical trade/quote capability under that owner; preserve existing publication/admission service |
| Derived microstructure window | Macro's existing options/entry evidence producers and compatible consumer leaf | Feature definition, sampling basis, cutoff, dependency digests, coverage and withheld reasons |
| Official OI/Greeks/reference states | Existing Theta EOD/OI/Greeks/reference owner | Session described versus publication, adjusted deliverable/exercise terms, model/input vintage |
| Surface or exposure result | Incumbent options surface/GEX/positioning owner | Fit/input/version/coverage, quote ages, scale units and inventory scenario identifier |
| Auction/depth extension | A later accepted existing-data-owner adapter | Native auction type/phase, venue/book scope, sequence/reset/gap and update-sampling semantics |
| Consumer decision snapshot | Existing Radar evidence snapshot/episode; future Portfolio V3 S0 owner | Reference existing immutable decision ID; no new generic Snapshot service |

A field that cannot be added compatibly to a closed schema requires that schema owner's reviewed version transition. Unknown fields must not be silently dropped, fabricated, or pushed through a consumer whose parser does not understand them. This research names requirements, not an adopted schema migration.

The nested Flow telemetry and strict standalone candidate receipt share a schema tag but have different field shapes. Reuse the existing adapter: it takes the original decision's five measured fields, retains the coalesced Flow identity and original event/observation times, takes verified stage available_at, and binds the original decision digest. The closed candidate schema does not accept a copy of the entire nested block. Its semantic event digest is distinct from the original stage-byte prefix receipt; source-clock diagnostics cannot replace scientific availability. [M19] [M37] [M10]

## E2. Existing receipt vocabulary, explicitly different clocks

Use the existing source-receipt vocabulary and add domain clarification where necessary:

| Clock or identifier | Required meaning |
|---|---|
| event_time | Native market event time **only if its source meaning is known**. Preserve clock_basis and precision; OPRA block processing time must not be renamed exchange execution time. |
| as_of | Economic/session/state date described by the observation; not a receipt clock. |
| source_observed_at | Vendor/capture observation if supplied, with named observer. Do not call it Mastermind receipt. |
| source_published_at / source_available_at | Earliest evidenced source dissemination for that particular generation, including licensed delay. Unknown remains unknown. |
| local_received_at | Actual receipt at the authorized incumbent collector, with clock/connection identity. |
| ingested_at | Landing into the existing source store; a retry may be later than first receipt. |
| known_at / available_at | Consumer-usable time under the existing owner contract: no earlier than all required inputs and successful materialization/admission. An erroring parser has not made data usable. |
| effective_from / effective_to | Valid interval of an instrument, deliverable, venue rule, membership or model/reference assertion. This is evaluated at the referenced valid time, usually the market event time. |
| correction_generation | Immutable source/adapter correction version with original/superseding references and its own availability. |
| source_event_id | Existing owner-scoped event identity, retaining its actual grain. In the incumbent candidate receipt it is the coalesced Flow event ID, not an atomic exchange print. Any required native print identifier is separately scoped by dataset/channel/session/instrument and linked through the existing source owner; it must not replace the incumbent field's meaning. |
| source_archive_vintage | Version/download/publication identity of retrospective history, plus immutable input digest. |
| derivation_id | Algorithm/config/schema/model version and deterministic input manifest. |

Timestamp precision must be explicit. Nanosecond encoding is not nanosecond accuracy; milliseconds can contain several quotes and trades. Store exact fixed-point price and quantity with source units; 2026 equity fractional reporting prevents a universal integer-share assumption. Options contract counts, premium multiplier, underlying share-equivalent delta, index level and currency must not be conflated.

## E3. Three evidence modes

1. **Actual decision-as-seen replay.** Proves what Mastermind's admitted consumer possessed at cutoff T using original source generations, local receipts/materialization and the original decision/episode ID. This is the standard for claims about historical Mastermind behavior.
2. **Historical receivability study.** Estimates what a hypothetical entitled observer could have used, using source dissemination plus an explicit latency model. It must state that Mastermind may not have possessed it. Absent original correction vintages, this mode cannot claim faithful first-publication replay.
3. **Final-vintage exploratory study.** Uses the history obtainable today. Useful for development and measurement research; not evidence that the feature was available to a past decision. It cannot qualify production PIT behavior or a historical trading result as as-seen.

Appending immutable records today improves future auditability but cannot recover a lost historical information set. The source mode travels with every study result.

## E4. Correct two-time selection rule

For decision cutoff T, choose each source assertion/correction generation whose **usable knowledge time is no later than T**, and resolve its version according to the source's correction law. For an event at valid time v, join the instrument/reference assertion whose valid interval contains v **and whose assertion generation was known by T**.

~~~text
admissible generation g:
    consumer_available_at(g) <= T
    and required source/status/rights predicates hold

event-reference join:
    reference.effective_from <= event.valid_time < reference.effective_to
    and reference.assertion_available_at <= T

derived feature available_at:
    no earlier than every constituent input's available_at
    and no earlier than successful derivation/admission
~~~

Do not require a historical trade's old reference interval to contain today's decision cutoff. Conversely, a reference correction published tomorrow cannot change yesterday's as-seen result merely because its economic effective date was last month. Final-restated evaluation can be produced separately, linked to the original immutable decision; it never overwrites it.

## E5. Quote association, ordering and correction rules

Select a quote using a documented clock domain and ordering rule. Do not use nearest-neighbor joins that can pick a later quote. Do not impose global ordering across unrelated vendor channels, or infer gapless delivery from a filtered per-instrument sequence. Preserve session/connection reset and sequence rollover.

Theta's current trade_quote documentation permits explicit strict-before versus inclusive joins. Its full-trade stream contains a pre-trade context and subsequent quotes. An asynchronous “latest quote” cache can therefore sign a queued trade against a post-trade quote unless association is retained. A strict millisecond join is conservative but not a proof of sub-millisecond event order; report the excluded/ambiguous fraction. [O1] [O2] [O3]

Separate an economically reconstructed prevailing quote from the quote actually observable to the local consumer. Both can be useful if labelled; only the second with cutoff receipts can prove an as-seen online decision. If a late quote or corrected trade becomes available, emit a later feature generation. Do not silently restate the frozen earlier feature.

Corrections append linked evidence. Scope deduplication to the true source identity; two identical price/size/time rows may be two trades. Unresolved cancellation linkage is quarantined or explicitly excluded, not heuristically applied to an arbitrary original. A schema's correction field does not prove a vendor's retrospective endpoint retains every original generation.

## E6. OI, option identity and IV are separate temporal objects

OI describes outstanding cleared contracts at a session/state boundary and is disseminated later. Theta documents approximate early-morning publication of prior-session OI, but an approximate time is not an actual per-series receipt. No-message, zero, unknown-series, entitlement failure, and delayed ingestion remain different states. A large volume/prior-OI ratio is not evidence that today's trade opened a position. [O5] [O25] [O26]

Option reference identity needs more than a ticker/expiry/strike/right tuple: underlying identity, currency, deliverable basket, premium multiplier, exercise style, AM/PM and cash/physical settlement, last trade/exercise times, adjusted-series status and effective-dated OCC action references. Adjusted deliverables cannot be reduced to a universal 100-share multiplier. Exercise/assignment and expiration can change OI without identifying the intent of any individual trade. [O27]

A surface result must retain the underlying reference used at cutoff, quote-time distribution, bid/mid/ask fitting choice, rates/dividends/borrow/forward assumptions, exercise model, calendar/expiration conventions, interpolation constraints, and failed-node reasons. Model changes create new derivation versions. Missing/stale or arbitrage-inconsistent nodes remain missing; they are not filled with a plausible LLM estimate.

# F. Derived intelligence and deterministic/model boundaries

## F1. Preserve the grain of the observation

A source print, a coalesced contract/poll-batch Flow event, an option episode, a campaign and a multi-contract package are different objects. Current live_flow identity coalesces prints by contract/poll batch. It must not be reused as an exchange execution ID, beneficial-owner ID, parent-order ID or cross-contract package ID. A finer-grained requirement belongs as a source-linked leaf under the incumbent retention owner, with mappings to the already accepted Flow/episode/campaign identities. [M18]

The existing measured block already contains source/NBBO-valid print counts, covered premium, print/premium coverage, at-ask/at-bid/inside/outside shares, spread statistics, quote age and displayed bid/ask size. Its “aggression” labels are price-location arithmetic. P0 should not rebuild those fields or reinterpret them as observed customer intent. First determine which outputs and original inputs are retained, what their exact cutoff is, and which consumer uses them. [M18] [M19]

Current nbbo_valid requires positive trade price, trade size and bid, ask above bid, and finite nonnegative quote age. That mask has no maximum quote-age rule or positive displayed-size condition. Its coverage is conditional on the retained source sample; it does not prove complete market/universe capture or native-condition eligibility. At-bid/at-ask shares are premium-weighted among covered prints; through-market prints are outside and midpoint prints remain inside. Age, condition, size, capture and universe checks therefore need separate qualification. Midpoint separation would be a diagnostic refinement only where retained inputs support it. [M18]

Current coalescing and measured premium use price × size × 100. The more general contract economics below are a qualification requirement, not a claim that current adjusted-series reference inputs are already available. A study must prove standard-contract eligibility or use the reference owner's accepted actual economics. This research changes no live calculation. [M18]

## F2. Feature dependency and availability matrix

| Observation | Required inputs | Earliest usable time | Output/guard |
|---|---|---|---|
| Eligible volume, premium/notional, VWAP, volume profile | Eligible corrected trade records; exact units/session/reference | After the records and the feature window are available | Report excluded auction/late/complex/condition volume and eligible denominator. |
| Quote location and at-trade spread/size imbalance | Causal attached pre-trade quote with known scope | After trade plus context plus derivation are available | Trade-sampled statistic, not time-weighted market liquidity. |
| Signed trade proxy | Qualified quote rule or truly supplied native initiator label | After the relevant measurement is available | Keep estimator/label provenance; unknown volume does not become signed zero. |
| Time-weighted spread, time depleted, quote duration | Continuous eligible quote updates, initial state, status/gap handling | After complete measured window and watermark | No indefinite forward-fill through gaps, halts or closed sessions. |
| Top-of-book OFI | Ordered best-price/size transitions in a defined book/consolidation scope | After the completed quote-event window | Not interchangeable with buy-minus-sell executed volume. National-best switches/ties need an explicit rule. |
| Liquidity resiliency | Qualified quote path around an observed shock | After the relevant recovery window | A retrospective recovery outcome; use only matured trailing summaries as current features. |
| Auction pressure | Native phase/type, paired and imbalance quantities, indicative/reference price | Actual dissemination and consumer availability | Not a continuous-market trade; separate opening, closing, reopening and special auctions. |
| Off-exchange share | Consolidated eligible trade reports with source-native facility/condition classification | Reporting and receipt, not assumed execution instant | “Off-exchange” is not “ATS” or “dark pool”; no participant-intent label. |
| Blocks/concentration | Eligible print size/notional versus predeclared absolute and trailing-liquidity thresholds | At completed observation window | A size class, not institutional identity or one parent order. |
| IV/skew/term structure | Causal chain quote cross-section plus underlying/rate/dividend/reference inputs | Latest constituent availability plus fit completion | Report stale/invalid nodes, exercise-model and fit versions. |
| OI change/volume-to-OI | Two published OI states or latest already-known OI | After the later state is actually usable | No intraday opening inference; zero/missing distinction mandatory. |
| Strike/expiry sensitivity | Eligible series OI/Greeks and complete contract scale assumptions | After constituent states are usable | Gross magnitude and separately named inventory scenarios. |
| Markout/realized spread | Pre-trade midpoint and eligible horizon midpoint | At least horizon end plus receipt/derivation | Outcome label for the original trade; never an original-time feature. |

## F3. Define arithmetic and units

For an eligible continuous-market trade, let P be trade price, b/a the selected pre-trade bid/ask, m=(b+a)/2, and q a **labelled** side variable (+1 buy, -1 sell). If side is unknown, side-dependent metrics are null. Using a quote-based q makes the output quote-inferred, not directly observed.

~~~text
quoted_spread_bps = 10000 * (a - b) / m
effective_spread_bps = 20000 * q * (P - m) / m
midpoint_markout_bps(h) = 10000 * q * (m_h - m) / m
realized_spread_bps(h) = 20000 * q * (P - m_h) / m

identity at the same units and endpoints:
effective_spread_bps = realized_spread_bps(h) + 2 * midpoint_markout_bps(h)
~~~

The identity is a deterministic check, not an economic theorem about causation. Midpoint response is affected by subsequent orders and information. Without actual order/fill and counterfactual evidence, do not call it Mastermind's realized execution shortfall or causal impact.

Use past matured response/depth relations, estimated on development data, instead of unstable response divided by nearly zero net signed notional. Report denominator exclusions and liquidity regimes. A later midpoint must meet a frozen endpoint rule; if the market is halted, stale or closed, label unavailable or censored according to the preregistration rather than fabricating a fill.

For standard option contracts, premium magnitude is price × contracts × premium multiplier. A quote-inferred underlying delta-notional proxy is q × contracts × multiplier × delta × underlying price. Option delta already carries call/put sign; do not flip puts a second time.

For a vanilla deliverable, let Gamma be the change in per-unit option delta per unit change in underlying price S. A useful **scenario** scale is the signed dollar value, marked at current S, of the gamma-induced change in option delta exposure for a positive 1% underlying move:

~~~text
option_delta_exposure_change_dollars_1pct = inventory_scenario_sign
    * assumed_inventory_contracts * multiplier * Gamma * S^2 * 0.01

hypothetical_delta_neutral_hedge_adjustment_dollars_1pct =
    -option_delta_exposure_change_dollars_1pct
~~~

inventory_scenario_sign denotes option inventory: positive for long and negative for short. Inventory allocated from OI is an assumption; traded contract count is activity, not outstanding inventory. A trade-count sensitivity may be reported separately and must not enter this inventory identity. Incremental hedge demand has the opposite sign, conditional on a delta-neutral scenario and holding other exposures fixed. The total change in dollar delta exposure also includes the existing delta's spot revaluation; this formula is not total hedge-notional change or gamma P&L. It is a local approximation, with vanna, charm, changing volatility and hidden offsets excluded. Nonstandard deliverables and model conventions require their actual economics or exclusion; a universal multiplier is unacceptable.

## F4. Options classifications that must stay separate

- **quote_location_class:** retain the incumbent mutually exclusive at-bid, at-ask, inside and outside classes with its frozen tolerance/precedence. Through-market prints are outside; midpoint remains inside unless an approved diagnostic explicitly partitions inside into midpoint and non-midpoint. Missing/locked/crossed/stale status belongs in separate quote-quality/admission annotations; an invalid quote does not receive a valid location class. Report any exact-tolerance collision under a deterministic precedence rule, never in two class denominators.
- **aggressor_side:** observed venue initiator only when truly supplied, otherwise a named proxy or unknown.
- **customer_side / participant_capacity:** supplied participant labels or an explicitly validated estimator, otherwise unknown.
- **position_effect:** participant open/close label, not inferred from total daily OI.
- **sweep_condition:** native ISO/condition when present.
- **sweep_cluster:** a transparent inferred same-contract cross-venue cluster, with uncertain common parent.
- **package_membership:** source-linked legs or a separately qualified association; an unlinked cluster remains unlinked.
- **dealer_inventory_scenario:** stated allocation/offset assumptions, not a signed inventory fact.

Reject vendor black-box institutional/sweep/dealer classifications as canonical facts when their inputs, scope and definitions cannot be inspected. They may be retained as separately labelled vendor opinions in an authorized comparative study.

## F5. Deterministic versus model work

| Work | Owner/method | Why |
|---|---|---|
| Parsing, native units, identity resolution, condition eligibility, joins, corrections, coverage and staleness | Deterministic source/data-owner code | These establish the information set and must replay exactly. |
| Spreads, OFI, volume profile, matured responses, IV/Greek calculations, OI/expiry buckets | Deterministic versioned analytics with explicit models where numerical fitting is needed | Reproducible arithmetic and constraints precede language reasoning. |
| Participant/demand estimator | A separately trained and evaluated statistical model, only if labelled evidence supports it | A quote-location rule cannot silently become a participant model. |
| Cheap LLM use | Optional bounded extraction of mechanism references or concise explanations from already qualified observations | No raw tape calculations, timestamps invented from prose, or hidden trade labels. |
| Frontier LLM use | Adjudicate contradictory mechanisms, design falsifiers, review independence and interpretation | Hard judgment, limited to the supplied evidence and declared uncertainty. |
| Portfolio sizing, orders, live gates, candidate activation, event lifecycle | Existing deterministic/admission/consumer owners | This commission grants none of these authorities. |

LLM explanations should be optional for the deterministic data path. Failure or absence of a model cannot turn a valid observation into missing raw data or bypass a stale-source gate. A model explanation has its own generated/available time and source references.

# G. Mastermind integration map

| Producer | Canonical artifact/data owner | Evidence family | Consumer / allowed effect |
|---|---|---|---|
| Existing US equity feed/qualified additional quote capability | Terminal Quote Plane and its approved source retention/receipt owner | Equity trading context / quoted liquidity | Macro evidence producer; no new quote service or frontend raw-data calculator |
| Existing ThetaData collectors/resolver | Canonical options store and raw/measurement receipt owner | Option trade location, magnitude and source quality | Existing live_flow/OA measured block; no alias from coalesced event to atomic print |
| Existing OI/Greeks/reference chain | Options source/structure/positioning owner | Published positioning, IV/expiry and scenario exposure | Existing options intelligence artifacts and research consumers |
| A later approved auction/depth adapter | Existing source owner, with licensed private raw retention | Auction or displayed-book observations | A separately frozen Macro feature challenger, not a second detector |
| Qualified deterministic windows | Incumbent Macro options/entry evidence artifact | Microstructure context with dependency-family tags | Existing Live Entry Radar/dislocation/entry research |
| Existing Radar episodes and frozen decisions | Existing event/episode and evidence snapshot owner | Event/catalyst + microstructure association | Terminal dislocation view; retain episode IDs, delay/quality and knowable time |
| Qualified option candidate/outcome observations | Existing candidate v2 and OA-3 episode/outcome/lifecycle owners; only generic validated quote/parser/math helpers reused from the separate options_nbbo_cohort benchmark | Contract/episode/campaign measurement | Existing evaluator, only after its own preregistration/capture/admission gates; benchmark identity, registries and its 600-second fence do not transfer |
| Future Portfolio S0 consumer | Incumbent Decision Snapshot and source manifest | One correlated evidence family, inspectable subdimensions | Portfolio research after S0 acceptance; no interim duplicate Snapshot |
| Qualified observation packet | Existing research desk | Competing mechanism explanation | Narrative/context only within existing authority |

Source authority and repository location must not be conflated. Terminal can own the shared quote **backend** while its product UI remains a consumer of Macro **intelligence**. The original instruction “no Terminal calculator” should prohibit a parallel detector or analytical feature implementation in the UI; it should not erase Terminal's existing Quote Plane ownership. [M02] [M03] [M12]

The user-facing product goal is a short explanation attached to the existing opportunity: “liquidity is impaired,” “reclaim has/had confirmation at this knowable time,” “options evidence is measured but direction unqualified,” or “insufficient source coverage.” Detail can reveal measurements, sampling basis, source clocks, conflicts and assumptions. The report does not authorize UI changes or relabel a delayed product as live.

All related observations carry a **dependency-family identifier**. Price trend, OFI, trade-sign balance and quote depletion may be different views of the same price/liquidity event. Calls/puts, gamma scenarios and expiry concentrations may share the same OI/Greek inputs. Different vendors redistributing OPRA are not independent information sources simply because they are different companies.

# H. Empirical validation program

## H1. Five different claims, five different tests

| Claim | Appropriate truth/target | What a passing test cannot prove |
|---|---|---|
| Parser/join/correction correctness | Native fixtures, source specification, deterministic replay | Profitable prediction |
| Quote-location measurement | Matched context and another qualified measurement implementation | True aggressor or customer side |
| Initiator/customer/position-effect identification | Correctly scoped independent participant labels with known semantics | Generalization to all venues/eras or successful trading |
| Incremental prediction | Outcomes strictly after decision cutoff, untouched chronological evaluation, incumbent controls | Implementable execution at the displayed midpoint |
| Decision/entry utility | Same incumbent candidates, actual admissible timing, fixed fallback/cost/fill conventions | Real executed performance without actual fills |

A family can remain useful descriptive context when predictive promotion fails. It cannot inherit another family's validation. Full validation detail and proposed numeric planning defaults are in [VALIDATION_PROTOCOL.md](VALIDATION_PROTOCOL.md).

## H2. Preserve existing evidence and trial accounting

The old approximately 0.4108 minute-net-sign result is a historical negative for its exact bar experiment. The broader Theta calibration and current false/suspended signing gates must also be read. Do not use “beat 0.41” as a sufficient promotion criterion: that conflates samples, levels of aggregation, benchmarks and estimands. [M20] [M21]

Keep the accepted September 17/18 OA observations and byte/source receipts unchanged. They are development/accepted system evidence, not a fresh statistical holdout. Existing FS5/OA methods and the unratified #8385 proposal have an owner. Commission 15 may specify a distinct microstructure estimand or submit a required amendment to that owner; it may not silently add another parallel trial or reuse an exhausted holdout. [M04] [M05]

The completed OA-2R retrospective EOD association result also remains accepted within its registered scope. Its 60 evaluable cells and three within-family BH rejections are not fresh forward confirmation and do not support transferring an effect to an entry-timing or exact-option executable outcome. Any proposed overlapping study first compares estimands, input vintages and trial accounting with that package. [M04]

## H3. Bounded feasibility cohort before a power claim

A proposed measurement cohort is SPY/QQQ plus up to 24 PIT-selected single names across three prior-known liquidity strata, with sector balance where feasible. This is a manageable source/measurement sample, **not** a powered national-alpha sample. Selection must use a fixed rule, prior-known metadata and existing permitted consumer universe—not retrospectively chosen winners or unusual-option screenshots.

Observe continuous sessions and explicitly identified earnings/expiry/auction/stress strata. Preserve halts, delistings, option expiry/adjustments, and absent-source windows. A screened event sample and a universe-wide study are different designs; record which is being run.

Initial P0 is measurement-only. The confirmatory consumer experiment opens only after source qualification and frozen definitions.

## H4. Same-candidate prospective entry test

The primary proposed consumer question is:

> On opportunities already nominated by the incumbent detector, does a frozen microstructure overlay improve a defined entry outcome or abstention decision compared with the identical incumbent decision, using only information available to that consumer?

Keep candidate identity, eligibility, intended exposure, permitted decision times, maximum wait, terminal horizon, fallback behavior and cost assumptions fixed. Freeze no more than two challenger policies for the primary test. A separate discovery study is required before claiming the new features improve candidate selection.

Measure all nominated opportunities, including those where source data are absent. The challenger takes its frozen fallback, normally the unchanged incumbent behavior or an explicitly preregistered abstention. Report the common-data subset as a sensitivity, not the only favorable denominator.

Suggested primary label: a fixed-horizon standardized entry-utility difference on the same opportunity, with documented cost/delay/opportunity-loss assumptions. Secondary descriptive labels include 5/30-minute and one/three-session forward response, maximum adverse/favorable excursion, waiting time, missed opportunities, and source-driven abstention. Reuse an accepted incumbent reclaim/barrier label if one exists; otherwise freeze an observable barrier/time definition. Do not define “true forced selling” by the eventual reversal.

A hypothetical fill is a model. A quote-based benchmark does not demonstrate executable depth or priority. Report three distinct result classes when present: price-path utility, simulated execution utility, actual order/fill utility. This commission requires no trading or actual-fill experiment.

## H5. Controls, dependence, missingness and leakage

Controls include prior return/trend, volatility, volume, spread where already present, market/sector movement, time-of-day, liquidity tier, catalyst/earnings state, market regime, options magnitude/expiry and existing candidate confidence. Compare incremental contribution after these controls; an OFI feature that restates the already-observed price move is not independent evidence.

Use chronological development/validation/untouched confirmation. Purge overlapping label windows and keep whole episodes, option packages/campaigns and associated contract observations together. Common-date shocks induce cross-issuer dependence; uncertainty must account for date and issuer/episode clustering or conservative blocks. Random row splits and treating thousands of option legs as independent are prohibited.

Feature normalization and thresholds use training/past data only. Future universe membership, eventual delisting knowledge, future expiries/adjustment mappings, late news, final OI, corrections, revised Greeks and post-decision quotes are explicit leakage tests. Multi-day horizons that overlap are not multiplied into independent observations.

Measure missingness by liquidity, spread, venue, session, volatility, expiry, earnings and stress—not just overall coverage. Missingness is likely informative. A clean sample that disappears during the adverse episodes cannot support a falling-knife avoidance claim.

## H6. Decision gates and kill criteria

Before confirmation, freeze the primary endpoint, minimum useful effect, maximum cost, power rule, horizon, number of challengers and multiple-testing treatment. Infer a sample size from development **cluster-level** variance, not raw trade count. If the affordable forward window cannot resolve the minimum useful effect, publish INCONCLUSIVE and stop promotion; do not lower the hurdle after seeing results.

Demand stable sign/usefulness across the declared strata and reasonable quote-age, lag, correction and source-scope sensitivities. A result driven by one issuer/day, only final-restated data, or an implausible fill model does not pass. Economic benefit must cover recurring rights, collection, storage and maintenance for the accepted use case. No universal signing-accuracy percentage from literature substitutes for these tests.

# I. Risks, failure modes and explicit falsifiers

| Risk | Detection / falsifier | Required disposition |
|---|---|---|
| Vendor timestamp mislabelled as exchange time | Dataset-specific spec disagrees with generic schema or units | Preserve native clock basis; fail features needing finer truth |
| Post-trade quote contamination | Frozen input audit shows a quote selected from after the permitted ordering/cutoff | Reject affected generation; repair association before study |
| Final-correction or final-OI leakage | As-seen and final-vintage cohorts produce different eligibility or apparent benefit | Preserve both modes; no as-seen claim without original generations |
| Synthetic/build clock disguised as source freshness | Internal timestamp diagnostic absent on public/latest wire | Qualify through internal owner receipts; no historical use of projection |
| Spurious continuous OFI | Only trade-sampled or sampled depth updates exist | Rename the sampled feature or obtain authorized required input |
| Unknown-to-zero conversion | Missing/no-message/entitlement/outage becomes zero volume/OI/flow | Fail source/feature admission |
| False volume from duplicated sides/legs | Cboe participant-side or package rows double count one execution | Enforce documented execution/sided-grain accounting |
| False institutional/forced/dealer story | No independent participant/constraint evidence | Mechanism stays hypothesis, not supervised fact |
| Native condition loss | Normalization removes auction/late/complex/correction eligibility | Restrict product use or reject source |
| Dealer scenario sign instability | Equally plausible allocations reverse the interpretation | Publish uncertainty/gross sensitivity; reject signed authority |
| Correlated confirmation | Benefit vanishes after incumbent controls/dependency families | Retain context if useful; reject incremental-alpha claim |
| Stress-selective coverage | Missingness rises in stressed names/sessions or after reconnect | Restrict supported population; deny generalization |
| Clock/regulatory era shift | Old lot, fractional-unit, tick or hours assumptions applied out of era | Version definitions; requalify affected studies only |
| Rights/retention conflict | Required replay/derived use exceeds executed grant | Do not ingest or retain beyond permission; source rejected for that use |
| Vendor lock-in | Replacing source changes hidden definitions/identity without trace | Require field semantics and input/version manifests |
| Statistical overfitting | Reused holdout, too many challengers, row-level pseudo-replication | Amend under incumbent trial owner; no promotion |
| Unqualified live consumer | Merged source/publisher used as proof of actual current path | Require original source → artifact → consumer receipt at admitted cadence |
| Duplicate owner/control path | Proposed work introduces rival quote/event/Snapshot/candidate/replay authority | Reject design |

Rights restrictions do not become exceptions because a result is useful. The later implementation must keep raw licensed inputs and potentially restricted derived records in the existing authorized private owner. GitHub should hold code, contracts, allowed aggregate findings and non-sensitive receipt/digest references, not the commercial tape or private research corpus.

# J. Build priority

| Priority | Recommendation | Completion evidence |
|---|---|---|
| P0 | Reconcile current Theta/Quote Plane contracts, accepted receipts, current content health and consumer gaps | Source/field/rights/receipt census; no duplicate or revoked source |
| P0 | Formalize feature sampling, grain, clock, condition and correction requirements | Incumbent reuse/delta map and adversarial fixtures |
| P0 | Qualify the existing options measured block and retained raw associations | Deterministic quote-context/coverage report; preserved accepted OA history |
| P0 | Establish truthful current data/consumer availability | Content-level health and generation lineage through current owner, not file mtime |
| P0 | Preregister one consumer experiment through incumbent evaluation owners | Frozen candidate/time/label/controls/holdout and power plan |
| P1 | Continuous consolidated equity quote-event capability, if absent and admitted by Quote Plane owner | Required field/rights proof and successful quote-state replay |
| P1 | Continuous options quote/surface capture where trade-sampled context is insufficient | Causal synchronized surface/window coverage |
| P1 | Narrow primary-venue auction sample | Auction phase/clock semantics and incremental value |
| P1 | Cboe participant/open-close/TBT measurement challenger if licensed and justified | Venue-scoped labels; no look-ahead or nationwide extrapolation |
| P1 | Prospective, read-only overlay in incumbent Radar/entry research | Same-candidate prospective utility and declared fallback |
| P2 | Selected native equity depth/cancellation challenger | Incremental value beyond qualified consolidated baseline and full cost |
| P2 | Broader participant/package studies, additional venues | Source linking and benefit justify complexity |
| Defer | National all-venue L3, options depth firehose, colocation, latency-routing stack | No current named consumer justification |
| Defer | Long-horizon microstructure stock-selection authority | Needs independent out-of-sample evidence beyond existing fundamentals/regime |
| Reject | Hard bar-direction restoration by heuristic, LLM trade signing, anonymous-print institutional labels | Invalid measurement/identification |
| Reject | Universal opaque microstructure score or invented dealer truth | Violates inspectability and evidence independence |
| Reject | New event/quote/Snapshot/candidate control planes or live portfolio effects under this commission | Outside owner law and assignment |

Priority names are recommendations, not admitted work or procurement. A source-rights gate can block one feature family while existing independently lawful measurement research continues.

# K. Proposed implementation phases

The phases below are a dependency sequence for a later accepted program. Each phase has a separate result and proof; none is executed by this research.

| Phase | Existing accountable owner | Bounded work | Exit proof / next gate |
|---|---|---|---|
| 0. Reconciliation and qualification | Options source/Flow owner; Quote Plane owner; principal integration | Pin current owners/PRs; inspect actual lawful input windows and current receipts; resolve source modes, rights and field losses | Signed-off reuse/delta map, accepted-history preservation, source evidence modes, no duplicate acquisition |
| 1. Offline measurement qualification | Existing OA-1T measured-block and capture/receipt owners; separate flow_signing comparator | Reuse equivalent accepted proofs; replay only a new/unqualified claim or material delta against lawful retained inputs; add approved missing diagnostics/fixtures | Qualified measurement with bounded proof, or evidence-backed qualification blocked/defer result; no direction-gate changes |
| 2. Minimum missing data | Existing quote/options source owner | Only if Phase 1 identifies a gap: qualify continuous quote-event or auction input on a bounded universe; procurement separate | Field-complete lawful sample, recovery/gap behavior, actual availability and cost receipt |
| 3. Preregistered offline study | Existing FS5/OA/evaluation owner | Same-candidate study with training-only choices, labels strictly after cutoff, source-mode sensitivity | Frozen report of effect, uncertainty, coverage and economic limitations; negative results retained |
| 4. Prospective consumer shadow | Existing Radar/entry/candidate owner | Read-only augmented evidence, original episode/campaign/decision IDs and fallback; no rank/size/live gate changes | Source → feature → consumer receipts, prospective observation count and latency, all-sample comparison |
| 5. Targeted challenger | Existing source + evaluation owners | One selected native-depth or participant-label question, not automatic national expansion | Incremental utility exceeds baseline and full cost; explicit BUILD/DEFER/REJECT |
| 6. Integration/promotion ruling | Existing principal/consumer and Portfolio S0 owners | Independent review of value and authority; Snapshot integration only after its own acceptance | Separate accepted authority decision; no automatic promotion from this report |

**Stop after Phase 0/1 when the information set cannot be qualified.** A data-quality-only result is valuable. It should identify the exact owner/input needed, not hide failure under a successful schema build. A poor prediction result should stop that feature's promotion even when the data is technically excellent.

If original historical candidate snapshots or input vintages do not exist or cannot be verified through the authorized owner, Phase 3 cannot recreate them. After measurement qualification, a separately admitted prospective Phase 4 study is an available route to collect the required information set. That routing exception does not authorize capture, shadowing or new access within C15-R0.

The planned endpoint is better-supported entry decisions and explanation, not a permanent mandate to retain every message. Retention granularity and horizon follow reproducibility, rights and consumer value. A later source change reopens only affected evidence, not every accepted historical OA result.

# L. Exact bounded follow-on implementation commission

The following is the commission to issue **only if this research is accepted**. It is deliberately narrower than the full phase plan above. This report does not execute it.

~~~text
COMMISSION C15-R0 — INCUMBENT MICROSTRUCTURE INPUT QUALIFICATION
                    AND OFFLINE MEASUREMENT PROOF

MISSION
Qualify the existing ThetaData/OA measured options path and the existing
Terminal Quote Plane interfaces against the accepted Commission 15 research.
Produce a reproducible offline measurement packet and a precise recommendation
for the one next missing-data or consumer experiment, or an evidence-backed
qualification-blocked conclusion when the authorized inputs cannot support it.

This wave may make bounded research/fixture/diagnostic changes after normal
source custody and admission. It grants no source purchase, entitlement upgrade,
live feed activation, production deployment, candidate activation, rank/size/
trade/exit authority, or portfolio mutation.

SOURCE AND CUSTODY
1. Bootstrap the then-current protected Mastermind Skillpack and load all required
   companions from the same commit.
2. Resolve current Macro, Terminal and Research Vault functional owners and pins.
   Research Vault is Macro content ingestion, not Executive DR.
3. Read the latest Options Intelligence/OA recovery workstream and October options
   research package, current signing gates, candidate v2, exact-outcome/capture
   contracts, live_flow event-stage and FS5 availability rules.
4. Reconcile open PRs and active writer/effect state before changing any owner path.
   Preserve #673 Portfolio S0 and current unratified methods; do not claim them.
5. Preserve accepted September 17/18 observations, corrected sweep semantics and
   immutable event/episode/campaign identities. Reopen accepted work only against
   an explicit material invalidator. Preserve completed OA-2R result/trial custody.
6. Use one branch/carrier. Raw licensed data stays in its existing authorized
   private owner; commit only permitted fixtures, definitions, code and summaries.
7. Preserve OA-3's episode/outcome/lifecycle owner. Only generic quote/parser/math
   helpers may transfer from the MomoEdge options_nbbo_cohort benchmark: not its
   identities, registries or 600-second capture fence. OA-3's executable NBBO
   lifecycle/capture gate remains unproven despite the merged pure evaluator.

ALLOWED BOUNDED SURFACES
- Existing ThetaData source/resolver and live_flow/flow_signing/OA measured-block
  interfaces, only where an approved diagnostic or fixture is necessary.
- Existing source receipt/capture/evaluation interfaces, without adding writers.
- Terminal Quote Plane interface/specification inspection; quote acquisition
  changes require its owner-qualified separate admission.
- A research-local experiment manifest and permitted synthetic/adversarial tests.
Do not create a universal market-event database, replay daemon, participant ledger,
package engine, quote hub, Snapshot, candidate feed or portfolio control path.

DELIVERABLE 1 — CURRENT INPUT AND RIGHTS CENSUS
For each used source, record exact product/API/terminal/schema/config versions,
actual entitlement evidence, permitted use/retention/derived/output scope,
instrument and session coverage, history start/end actually inspected, source
granularity, clocks/precision, native conditions, correction linkage and known
losses. Separate documentation claims, historical accepted receipts and current
content reads. Record quote source authority. Never treat an empty repository
stub as the host store or a stale public artifact as current coverage.

DELIVERABLE 2 — FIELD REUSE/DELTA AND SOURCE MODE
Map every requested output to an existing field or an explicitly missing field.
Preserve atomic print versus coalesced Flow event versus episode/campaign grain.
Use the current candidate receipt adapter: source_event_id means coalesced Flow
event there. Its strict field shape differs from the nested measured telemetry.
Bind each study to ACTUAL_AS_SEEN, HISTORICAL_RECEIVABILITY or FINAL_VINTAGE.
Use existing source receipts and scientific availability fields. A local
download today is not historical possession.

DELIVERABLE 3 — OFFLINE MEASUREMENT PACKET
Using only existing authorized retained data:
- reuse equivalent accepted results when inputs, definition, scope and receipt
  integrity are unchanged; reproduce only the bounded delta for a named new or
  currently unqualified claim or explicit material invalidator;
- report retained-sample print/premium coverage and current bid/ask/inside/outside
  classes, spread, quote age, ambiguity, source conditions and excluded volume;
  distinguish these from capture/universe coverage. Midpoint refinement requires
  supported retained inputs; freshness and displayed-size admission are separate;
- report concordance with the named comparator, not accuracy without truth labels;
- preserve separate aggressor, customer, position-effect and package unknowns;
- retain actual correction and stream association evidence when available;
- identify which full quote-event features cannot be calculated from available
  trade-attached quotes.
Do not run a fresh hunt for already-accepted OA events or rerun an exhausted
statistical holdout. Do not imply new predictive proof from deterministic replay.
If original bytes/associations or their permitted use cannot be qualified, take
the evidence-backed blocked exit below; do not obtain replacement sessions or
manufacture missing source history to force this deliverable to pass.

DELIVERABLE 4 — ADVERSARIAL TEMPORAL/SEMANTIC FIXTURES
Prove:
- post-trade/late quotes cannot enter an earlier frozen feature;
- inclusive/strict timestamp rules and same-millisecond ambiguity are explicit;
- source sequence reset/rollover/filtered gaps do not invent event identity;
- trade corrections append and never mutate earlier decision-as-seen outputs;
- reference validity is joined at event valid time, assertion knowledge at cutoff;
- prior-session OI enters only after actual availability, not at its as-of label;
- no-message, zero, missing, entitlement error, halt and outage remain distinct;
- future markouts are labels until mature;
- coalesced event IDs are not atomic/parent/package IDs;
- adjusted deliverables, option units and model versions cannot silently change;
- deterministic replay uses original allowed bytes/manifests, not a reserialized
  substitute for an existing byte-addressed receipt;
- sparse trade BBO cannot pass a continuous OFI/time-weighted-liquidity gate.
If the source cannot prove a case, report unsupported capability and confine the
result. Do not invent fixtures that pretend unavailable source semantics exist.

DELIVERABLE 5 — ONE NEXT-EXPERIMENT PREREGISTRATION
Choose the narrow next question justified by the measurement result:
(A) missing continuous quote input, (B) participant-labelled comparator,
(C) auction sample, or (D) same-candidate entry-context shadow study.
Specify exact consumer identity/cutoff, universe selection, source mode, feature
and fallback definitions, primary endpoint, horizons, controls, dependences,
development/untouched-forward split, trial ownership, minimum useful effect,
cluster-level power/sample rule, rights and total cost cap.
At most two primary challengers; no automatic data purchase or live shadow launch.
Use the existing FS5/OA evaluator owner where applicable. If the study overlaps an
existing cohort/holdout, amend there rather than mint another trial.

ACCEPTANCE
- Every use is lawful and source/owner-specific.
- No duplicate writers or authority changes.
- Current data/receipt evidence is distinguishable from documentation and history.
- Declare exactly one qualification exit:
  QUALIFIED_MEASUREMENT: equivalent accepted proof or the necessary bounded replay
  supports the named measurement; required temporal/semantic fixtures have no
  unresolved critical failure for that claimed mode.
  QUALIFICATION_BLOCKED_WITH_EVIDENCE: document the scoped missing dependency or
  evidenced access/permission/verification barrier, its owner, unsupported outputs,
  preserved accepted evidence and one separately gated remedy. Distinguish absent,
  denied and unverified. Input qualification is complete; measurement proof stays
  unproven and the affected feature recommendation is DEFER or REJECT.
- Every feature's sampling and required history are actually present or withheld.
- All existing signing/candidate/live authority gates retain their current value.
- The next experiment is build-ready and separately gated; no alpha or live
  acceptance is claimed from this wave.
- Independent review resolves material findings and verifies exact artifact hashes.

RETURN
Exact source/branch/PR/commit, changed-path inventory, input/rights manifest,
reuse/delta contract table, source-mode declaration, qualified measurement result
or documented blocked exit, unknown/coverage report, fixture results or explicit
unsupported cases, immutable receipt references, reviewer
disposition, and one BUILD / DEFER / REJECT / INCONCLUSIVE recommendation.
Stop at this wave's accepted offline result. Do not begin data procurement,
continuous live capture, consumer activation or Phase 2 without its own commission.
~~~

---

## Research conclusion

Mastermind should retain this family as a high-priority **measurement and entry-context capability**, subject to source qualification and independent value tests. The current estate has more relevant implementation than the attachment recognized, and less proven semantic certainty than its “trade direction” language implied. The right next step is a bounded qualification of the existing source-to-measurement path, followed by one discriminating experiment. Additional data earns its place by answering a missing question; no source, schema, model or merged component earns decision authority by existing.

## Source references

Stable primary sources and pinned internal files used in this report follow. Source-specific limits are explained in SOURCE_REGISTER.md; citation does not imply current entitlement or empirical reproduction.

[M01]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/research/OPTIONS_INTELLIGENCE_CONSOLIDATED_MASTERPLAN_2026-08-28.md
[M02]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/app/dossier_quote.py#L12-L17
[M03]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/1c708450187755160e1a5889b69598a2fcb1f0d1/hub/README.md
[M04]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md
[M05]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/research/options_intelligence/2026-10-03/MASTER_PLAN.md
[M06]: https://github.com/mastermindx-market-intelligence/Mastermind/pull/673
[M07]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/engine/research_vault/__init__.py
[M08]: https://github.com/mastermindx-market-intelligence/executive-dr-vault/blob/ea422c92bd29800d1f7fb3ae850236cc44d8c890/README.md
[M09]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/engine/flow_enrich.py#L250-L262
[M10]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/lib/live_flow_event_stage.py
[M11]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/site/options_intel_brief.json#L47-L62
[M12]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/1c708450187755160e1a5889b69598a2fcb1f0d1/terminal/lib/dislocations/source.ts
[M13]: https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/loop/single_name_panel.py
[M14]: https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/loop/fundamentals.py
[M15]: https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/portfolio/held_risk.py#L734-L825
[M16]: https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/portfolio/lenses.py
[M17]: https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/data/census/CENSUS.md
[M18]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/engine/live_flow.py
[M19]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/contracts/options/options.trade_nbbo_microstructure.v1.schema.json
[M20]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/research/execution/THETADATA_TAPE_CONTINUOUS_CALIBRATION.md
[M21]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/data/options_flow/signing_gate.json
[M22]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/engine/options_alpha_candidate_feed.py
[M23]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/1c708450187755160e1a5889b69598a2fcb1f0d1/terminal/app/api/v1/dislocations/route.ts
[M24]: https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/brain/research_desk.py
[M25]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/engine/thetadata_store.py
[M26]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/collectors/thetadata.py
[M27]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/engine/live_quotes.py
[M28]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/scripts/build_live_quotes.py
[M29]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/research/MASTERMIND_DATA_CONTRACTS.md#L967-L1028
[M30]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/research/INTRADAY_DISLOCATION_TERMINAL_PRODUCT_SPEC_V1.md
[M31]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/research/live_entry_radar/INTRADAY_DISLOCATION_CATALYST_FORWARD_READ_EVIDENCE_2026-10-03.md
[M32]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/docs/runbooks/OPTIONS_NBBO_COHORT.md
[M33]: https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/docs/superpowers/specs/2026-09-15-mastermind-portfolio-v3-risk-first-autonomous-manager-design.md
[M34]: https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/docs/superpowers/plans/2026-09-15-mastermind-portfolio-v3-s0-decision-snapshot.md
[M35]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/research/options_intelligence/2026-10-03/SOURCE_ADMISSION_SPEC.md
[M36]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/research/options_intelligence/2026-10-03/PILOT_STUDY_SPEC_V1.md
[E01]: https://arxiv.org/abs/1011.6402
[E02]: https://databento.com/docs/schemas-and-data-formats/tbbo
[E03]: https://www.ctaplan.com/publicdocs/ctaplan/CQS_Pillar_Output_Specification.pdf
[E04]: https://www.utpplan.com/DOC/UtpBinaryOutputSpec.pdf
[E05]: https://www.nyse.com/market-data/real-time
[E06]: https://www.nyse.com/data-products/catalog/integrated-feed
[E07]: https://www.sec.gov/files/rules/exorders/2026/34-105656.pdf
[E08]: https://www.sec.gov/files/rules/exorders/2026/34-104612.pdf
[E09]: https://www.nasdaqtrader.com/TraderNews.aspx?id=UTP2025-28
[E10]: https://databento.com/blog/nasdaq-historical-data-changes-2026-09
[E11]: https://www.nyse.com/data-products/catalog/daily-taq
[E12]: https://www.finra.org/rules-guidance/rulebooks/finra-rules/6110
[E13]: https://www.iex.io/products/market-data-connectivity
[E14]: https://www.nasdaq.com/products/data/equities/nasdaq-totalview
[E15]: https://www.nyse.com/data-products/catalog/imbalances
[E16]: https://www.nyse.com/publicdocs/nyse/data/NYSE_Market_Data_Pricing.pdf
[E17]: https://www.ctaplan.com/publicdocs/ctaplan/CTS_Pillar_Output_Specification.pdf
[E18]: https://databento.com/docs/schemas-and-data-formats/mbp-1
[E19]: https://www.finra.org/filing-reporting/market-transparency-reporting/trade-reporting-faq
[E20]: https://www.iex.io/legal/hist-data-terms
[E21]: https://consolidatedtape.com/faq
[E22]: https://www.nasdaqtrader.com/TraderNews.aspx?id=DTN2026-14
[E23]: https://www.sec.gov/rules-regulations/staff-guidance/trading-markets-frequently-asked-questions/frequently-asked-questions-rule-605-regulation-nms
[O1]: https://www.thetadata.net/docs/operations/option_history_trade_quote.html
[O2]: https://thetadata.net/docs/Streaming/US-Options/Full-Trade-Stream.html
[O3]: https://www.thetadata.net/docs/Articles/Data-And-Requests/Making-Requests.html
[O4]: https://thetadata.net/docs/Articles/Errors-Exchanges-Conditions/Trade-Conditions.html
[O5]: https://www.thetadata.net/docs/operations/option_history_open_interest.html
[O6]: https://www.thetadata.net/docs/Articles/Data-And-Requests/Option-Greeks.html
[O7]: https://thetadata.net/docs/Articles/Getting-Started/Subscriptions.html
[O8]: https://www.thetadata.net/commercial-use
[O9]: https://www.thetadata.net/subscriber-agreement
[O10]: https://databento.com/blog/opra-migration
[O11]: https://databento.com/blog/opra-improvements-coming-soon
[O12]: https://databento.com/docs/venues-and-datasets/opra-pillar
[O13]: https://databento.com/docs/schemas-and-data-formats/tcbbo
[O14]: https://roadmap.databento.com/roadmap/include-opra-trade-conditions
[O15]: https://datashop.cboe.com/option-trades
[O16]: https://datashop.cboe.com/documents/Option_Trades_Specification.pdf
[O17]: https://datashop.cboe.com/cboe-options-open-close-volume-summary
[O18]: https://datashop.cboe.com/enhanced-us-options-trade-by-trade-execution-detail
[O19]: https://datashop.cboe.com/documents/TBT_Spec_v1.0.pdf
[O20]: https://www.massive.com/docs/rest/options/trades-quotes/trades
[O21]: https://www.massive.com/docs/rest/options/trades-quotes/quotes
[O22]: https://www.massive.com/pricing?product=options
[O23]: https://cdn.opraplan.com/documents/OPRA_Pillar_Output_Specification.pdf
[O24]: https://cdn.opraplan.com/documents/OPRA_BBO_Guidelines.pdf
[O25]: https://www.optionseducation.org/referencelibrary/faq/general-information
[O26]: https://www.theocc.com/market-data/market-data-reports/other-market-data-info/batch-processing/daily-open-interest
[O27]: https://www.optionseducation.org/news/splits-happen
[O28]: https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/on-inferring-the-direction-of-option-trades/FDA4541B57F78B2C8DCE129AFC25AAF0
[O29]: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4098475
[O30]: https://www.mit.edu/~junpan/volume.pdf
[O31]: https://abarbon.com/papers/gamma-fragility
[O32]: https://arxiv.org/abs/1204.0646
[M37]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/scripts/build_options_alpha_candidate_feed.py#L108-L166
[M38]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/agentos/handoffs/OPTIONS-ALPHA-INTELLIGENCE-RECOVERY-2026-10-04-installed-source.md#L72-L84
[M39]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/engine/options_flow.py#L23-L34
[M40]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/data/thetadata_eod/_manifest.json
[M41]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/engine/prophet_entry_policy.py#L43-L49
[M42]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/agentos/workstreams/WS-ADVANCED-DATA-OPTIONS.md
[M43]: https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/docs/sol_skills/INDEX.md
