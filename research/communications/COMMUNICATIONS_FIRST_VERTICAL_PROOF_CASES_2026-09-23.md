# Communications First Vertical — Source Examples and Proof Boundary

**Original date:** 2026-09-23. **Revision 2:** 2026-09-24. **Operation:** `gmi-communications-research-20260923-sol-001`.
**Carrier:** Macro Draft/HOLD PR #7794. **Status:** public research examples, not admitted native evidence, live product data, executed application tests or an investment model.

Read with the Communications business-intelligence design and advertising implementation plan. The spec defines the user job; the original plan maps forty CRV requirements, extended to sixty by the numerical review amendment. This companion supplies the original-source numerical and interpretation examples needed for those tasks. It does not grant source-retention/display rights or populate production identity.

## 1. Reporting and expectation scope

Actuals refer to the quarter from 2026-04-01 through 2026-06-30; prior-year growth comparisons use 2025-04-01 through 2025-06-30. Company guidance sources were published before the reported quarter result but refer to that same Q2 2026 metric. They are original company-guidance observations, not a census of later revisions or analyst consensus.

Money remains in the issuer table's source unit. Where the original guide uses USD millions and actuals use USD thousands, the guide is explicitly multiplied by 1,000. The source publication dates below have day precision in this pack; this is not proof of an intraday knowable cutoff. Arithmetic examples never create evidence/issuer/security/retention IDs. Those fields remain null in the portable JSON.

## 2. Primary-source register

The seven selected primary sources were opened in this design phase. Their full reports are not reproduced here. Locators below select exact statements/tables; no inferred source hash or access receipt is supplied.

| ID | Publisher and publication date | Selected source |
|---|---|---|
| M2Q | Meta; 2026-07-29 | https://www.sec.gov/Archives/edgar/data/1326801/000162828026050596/meta-06302026xexhibit991.htm |
| M1Q | Meta; 2026-04-29 | https://investor.atmeta.com/investor-news/press-release-details/2026/Meta-Reports-First-Quarter-2026-Results/ |
| G2Q | Alphabet; 2026-07-22 | https://www.sec.gov/Archives/edgar/data/1652044/000165204426000066/googexhibit991q22026.htm |
| T2Q | The Trade Desk; 2026-08-06 | https://investors.thetradedesk.com/news-and-events/news/news-details/2026/The-Trade-Desk-Reports-Second-Quarter-2026-Financial-Results/default.aspx |
| T1Q | The Trade Desk; 2026-05-07 | https://investors.thetradedesk.com/news-and-events/news/news-details/2026/The-Trade-Desk-Reports-First-Quarter-2026-Financial-Results/default.aspx |
| MG2Q | Magnite; 2026-08-05 | https://investor.magnite.com/news-releases/news-release-details/magnite-reports-second-quarter-2026-results |
| MG1Q | Magnite; 2026-05-06 | https://investor.magnite.com/news-releases/news-release-details/magnite-reports-first-quarter-2026-results |

## 3. Twelve reference calculations

Decimal and Fraction independently evaluate the same transcribed inputs. Agreement checks arithmetic, not source authenticity or statistical usefulness. Six decimals are a reproducibility convention; displayed financial values should follow their source precision.

| ID | Inputs and operation | Reference result | Interpretation and source selector |
|---|---|---|---|
| CV01 | 60801, 47516; pct_change; USD million | 27.959003 percent | Reported issuer growth, not AI revenue growth. [M2Q]: Condensed consolidated income statement |
| CV02 | 18775, 20441; pct_change; USD million | -8.150286 percent | Negative profit growth despite revenue growth; not a cost attribution. [M2Q]: Condensed consolidated income statement |
| CV03 | 31862, 30116, 962; net_cash; USD million | 784.000000 USD million | CFO minus property/equipment purchases and finance-lease principal. [M2Q]: Free cash flow reconciliation |
| CV04 | 60801, 58000, 61000; closed_range; USD million | WITHIN_ORIGINAL_RANGE categorical | Within original company range; not analyst consensus. [M2Q,M1Q]: Current revenue and Q1 CFO outlook |
| CV05 | 63271, 54190; pct_change; USD million | 16.757704 percent | Business-scope growth, not all-issuer growth. [G2Q]: Revenue category table: Google Search & other |
| CV06 | 7303, 7354; pct_change; USD million | -0.693500 percent | Network decline does not become a Search decline. [G2Q]: Revenue category table: Google Network |
| CV07 | 39069, 44924; net_cash; USD million | -5855.000000 USD million | Signed consolidated cash; not a Search-only subtotal. [G2Q]: Non-GAAP free cash flow reconciliation |
| CV08 | 715057, 694039; pct_change; USD thousand | 3.028360 percent | Reported revenue; supplier-cost presentation still requires explanation. [T2Q]: Condensed consolidated statement of operations |
| CV09 | 101577, 116777; pct_change; USD thousand | -13.016262 percent | Reported operating-income change, not a normalized sensitivity. [T2Q]: Condensed consolidated statement of operations |
| CV10 | 715057, 750000; pct_change; USD thousand | -4.659067 percent | Original 750 million floor explicitly multiplied by 1000; below floor, not consensus surprise. [T2Q,T1Q]: Reported revenue and original Q2 outlook |
| CV11 | 189595, 161956; pct_change; USD thousand | 17.065746 percent | Issuer-defined contribution, not GAAP revenue. [MG2Q]: Contribution ex-TAC reconciliation |
| CV12 | 189595, 181000; pct_change; USD thousand | 4.748619 percent | Original 181 million ceiling explicitly multiplied by 1000; not consensus surprise. [MG2Q,MG1Q]: Contribution ex-TAC and original Q2 outlook |

CV10 and CV12 are proportional differences from a floor and a ceiling, not generic surprise percentages. The real view must first express the correct categorical comparison. A range midpoint is optional reference arithmetic, never a substitute for the original range. Source rounding that overlaps a threshold remains indeterminate.

### A source-label refinement from this pass

Alphabet's selected current release explicitly includes the consolidated non-GAAP free-cash-flow reconciliation used by CV07. Earlier research conservatively described the same calculation as a consolidated cash subtotal. This phase refines the label to a reported issuer-defined reconciliation while preserving the amount, scope and non-GAAP basis. It does not make the result Search-only, change prior source bytes, or normalize away investment. The result remains negative and must survive the shared assertion pipeline.

## 4. Four reviewable example explanations

These are proposed response patterns, not unqualified live recommendations. The implementation must regenerate numerical observations from admitted owner data and apply only templates whose supporting conditions are satisfied. Management causality and house interpretation remain separate from the stated measurements.

**Meta.** The cited quarter combines approximately 28% issuer revenue growth with an approximately 8% decline in reported operating income. Advertising-volume and price observations support stronger monetization, while reported costs limit how much reaches operating profit. The original revenue result is inside the original company range. Do not call it a consensus beat or attribute all issuer costs to advertising or AI. Next evidence to inspect: a comparable profit/cash bridge and whether monetization gains persist without proportionate cost growth. [M2Q,M1Q]

**Alphabet.** Search & other revenue increases while Network revenue declines. The consolidated free-cash-flow measure is negative after capital expenditure. This supports a split business interpretation, not a verdict that every Alphabet activity deteriorated or that Search alone consumes that cash. Next evidence to inspect: the separate operating/capital allocation disclosures needed to connect Search economics to the issuer result. No unsupported segment allocation is filled in. [G2Q]

**The Trade Desk.** Reported revenue increases while reported operating income declines; revenue is below the original company-guidance floor after matching units. These facts do not prove a market-share transfer to another intermediary or a consensus miss. Supplier-cost presentation, established-client spending and operating costs need their disclosed explanations before organic or normalized inferences. Next evidence to inspect: comparable retained economics and the qualified customer-spend trajectory. [T2Q,T1Q; detailed definitions remain in Phase 2]

**Magnite.** Issuer-defined contribution excluding traffic-acquisition costs grows and exceeds the original guidance ceiling. It is not GAAP revenue, and the release's named operating-cash measure is adjusted EBITDA minus capital expenditure rather than the statement-of-cash-flows measure. Next evidence to inspect: the disclosed segment mix and conversion into comparably defined cash, not a mechanically ranked comparison with other companies' margins. [MG2Q,MG1Q]

These templates are deliberately qualified. The first product must still lead with the useful economic finding rather than forcing the investor to read raw source provenance before learning what changed.

## 5. Illustrative interpretation checks

The local check script exercises twelve reference-level properties: exact guidance-boundary inclusion; above/below range; null versus zero; positive-prior percentage domain; explicit unit scaling; within-range versus midpoint; zero-sum budget conservation; loss-turnaround absolute change; no duplicate cash component; and no summing unlike populations. These checks are local demonstrations of the desired semantics, not execution of the proposed production comparison module.

The application acceptance set is CRV-01 through CRV-60 across the implementation plan and numerical amendment. It additionally requires native round-trip, actual clocks, rights/identity, unauthorized-request denial before source access, logout-race protection, fixed coverage denominators, bilingual dual-theme layouts, real company/watchlist behavior and alternate-mirror negative proof. None of those application outcomes was executed by the arithmetic helper.

## 6. Fixture and production boundaries

The portable `COMMUNICATIONS_FIRST_VERTICAL_REFERENCE_CASES_2026-09-23.json` exports this document's twelve examples. It is not an extra source owner. Production code must not load the research or tests directory as an accepted current source. Test-native assertions and identity receipts must be explicitly synthetic and use the existing owner's test grammar; real native IDs, source digests, entitlements and source generations come only from actual admission.

Required source/identity fields are intentionally unassigned in this reference pack. Missing source-retention evidence is not cured by placing a URL in a field named digest. An accepted public report is not a license for republishing a proprietary consolidated product snapshot. All actual publication follows the existing owner rights/private-transport decision.

The first application may display latest accepted evidence while reporting that its completeness against all newer releases is unqualified. It may not call the old Q2 examples current merely because this file is served today. Corrections and newer admitted observations recompile the affected results; the historical examples remain unchanged as tests.

## 7. Historical verification of revision 1

The local helper evaluated twelve source-input cases using Decimal and Fraction and checked their expected labels/units. Document checks verify the sixteen specification sections, eight implementation tasks, forty unique acceptance IDs, source-ID closure, parseable Python plan examples, no placeholder markers, intentional null native IDs and exact file hashes. The twelve illustrative checks are explicitly reference-level only.

Not verified here: the proposed product schema, shared-contract acceptance, actual private owner placement, live source admission, live identity joins, full repository Agent OS validation, CI, production application behavior, Fable pickup or deployment/browser acceptance. The checkpoint and native write/readback receipts identify exactly which documents were persisted.


## 8. Consolidated first-screen examples (revision 2)

This revision converts Phases 11 and 12 into concrete content for design sections 7–11 and plan Tasks 3/4/6/7/8. It does not create a new wire schema or renderer. The shared-foundation amendment at `890e0da179dbb92b2bf7b07ad2fec06f2adcf264` still supersedes the original separate GET/client instructions. The numerical amendment at `d67a312c7cd5cbf9f3b8af9a8911374e8b54e7de` still controls bounds, comparison identity and cash-role/sign binding. No source-custody or shared-interface acceptance is implied.

The Chairman will manually deliver the eventual package to a NEW Fable session later. No dispatch, receiver search, upstream notification or watcher is authorized by this consolidation. Semiconductors remains the shared implementation dependency, not the Communications recipient.

**Three separate dimensions:** the economic direction of a finding, the completeness of its evidence, and the attractiveness of the security. A fully supported decline is not a data failure. A complete descriptive view is not a buy/sell conclusion. Readiness cannot depend on whether the reported numbers are favorable.

The first screen retains the fixed public example roster and its economic-role order. For each business it shows one conclusion and two decisive observations. Supporting calculations, original-guide comparison and source limits expand beneath that answer. These examples concern the quarter ended June 30, 2026; serving them in September does not make them September observations. All native identities, rights decisions, private receipts and company routes remain to be qualified.

| Example | Headline | Two decisive observations (current / prior, original source unit) | Supporting detail, not an extra headline |
|---|---|---|---|
| E01 Meta | Revenue growth did not translate into higher reported operating income. | Consolidated revenue 60,801 / 47,516; operating income 18,775 / 20,441; USD million | AB01 operating-cost bridge and AB02 cash bridge. Original revenue range comparison stays separate. |
| E02 Alphabet | Search and Network moved in different directions. | Search & other 63,271 / 54,190; Network 7,303 / 7,354; USD million | AB03 advertising partition; AB04 sequential consolidated cash, explicitly a different scope and interval. |
| E03 The Trade Desk | Revenue rose while reported operating income fell. | Consolidated revenue 715,057 / 694,039; operating income 101,577 / 116,777; USD thousand | AB05 operating-cost bridge. Below the original company floor is not a consensus miss. |
| E04 Magnite | Contribution ex-TAC and reported gross profit increased. | Contribution 189,595 / 161,956; GAAP gross profit 130,785 / 108,379; USD thousand | AB06 cost-side and AB08 channel views explain the same contribution outcome; AB07 explains gross profit. |

E01's house interpretation concerns the reported cost/revenue bridge, not proven returns on AI. E02 does not allocate consolidated cash to Search or infer that all businesses deteriorated. E03 does not normalize an accounting presentation without a reviewed bridge. E04 keeps issuer-defined contribution separate from GAAP revenue and does not count derived TAC as independent confirmation. These are explanations of selected facts, not a sector winner ranking. [M2Q,G2Q,T2Q,MG2Q]

**What could change the read:** E01 examines later monetization-to-profit/cash conversion after required investment. E02 examines category-level monetization, distribution costs and investment conversion. E03 examines comparable customer spending and retained contribution. E04 examines the persistence of connected-TV contribution and conversion to profit/cash under consistent definitions. These are research questions, not thresholds, estimates, forecasts or automatic watchlist instructions.

The portable reference pack supplies author-prepared EN/ZH versions of each conclusion, role, interpretation, limitation and next observation. Each short field is bounded to 240 characters. This is semantic-content checking, not independent localization acceptance or proof that a 390px viewport renders it well.

## 9. Claim-scoped degradation instead of whole-card silence

A sentence is allowed only while the specific inputs supporting that sentence remain qualified. Losing a prior-period observation removes a growth statement, not the current reported level. Losing the exact old interpretation binding after a correction removes that interpretation, not a newly qualified fact. Losing rights suppresses the affected material before serialization; it is not an invitation to show stale private prose.

The following S-identifiers are research-example labels, NOT new runtime states, native entities or extra release requirements. The offline replay uses an author-supplied prerequisite table. It neither enforces real access nor validates source-language meaning.

| Case | Changed condition | Retain / withhold | Existing CRV coverage |
|---|---|---|---|
| S01 | Original guide qualified; final history/consensus not qualified | Show original-guide comparison, withhold stronger labels | 23,24,37 |
| S02 | Prior-period evidence absent | Show current level; remove growth/profit-divergence headline | 02,17,24 |
| S03 | Current evidence unavailable | No current headline/derived result; separately verified public navigation may remain | 02,16,57 |
| S04 | Original guide absent | Show operating and cash evidence; no invented guidance comparison | 23,24 |
| S05 | Corrected source no longer matches interpretation or guide rule | Show newly qualified fact; withhold old explanation/comparison | 10,51 |
| S06 | Period or population incompatible | Show individual levels; no numerical comparison | 17,47–50 |
| S07 | Source rights revoked | Suppress dependent private facts and sentences; no stale cached copy | 26,32,60 |
| S08 | Cash reconciliation incomplete | Show unaffected facts; no fictional residual component | 19,54–56 |
| S09 | Security identity unresolved | Business description remains; no guessed stock route | 13,14,59 |
| S10 | Company navigation works but no save occurred | Show verified link; do not claim watchlist success | 15,37 |
| S11 | A deliberate save has its own receipt | Only then report the existing action's success | 37 |
| S12 | New Q3 guide appears where original Q2 guide is absent | Q3 does not fill the Q2 gap | 09,17,49 |
| S13 | An analyst premise appears inside a CFO turn | Do not manufacture issuer guidance | 09,17,24 |
| S14 | Later expense update concerns another period/measure | Keep the original revenue comparison; separate the later event | 09,10,24 |
| S15 | Another peer grows faster | No inferred transfer of advertising budgets or market share | 21,40 |
| S16 | Account entitlement denied | No private output; at runtime denial must precede owner reads | 26,27,31,32 |
| S17 | Inputs may span incompatible generations | No mixed ready comparison or old explanation; a level needs its own validation | 10,38,51 |
| S18 | Complete final-history evidence becomes available | A separate final-guide comparison may be qualified; original remains distinguishable | 09,17,23 |
| S19 | Qualified consensus vintage becomes available | A separate consensus comparison may be qualified; no trading authority follows | 17,23 |
| S20 | A candidate final statement lacks complete history/rule | Do not promote it to final issuer guidance | 09,17,23 |

S18/S19 are hypothetical qualification paths, not current research achievements. The public authored four-company roster can remain four when evidence is unavailable; counts, labels or fingerprints must not reveal denied underlying records. This is not permission to expose which restricted source is missing. The shared owner supplies coherent access and generation behavior; this document adds no permissions cache or polling loop.

## 10. Guidance meaning, fresh copy and correction behavior

Phases 11/12 remain source authority for the detailed examples. The original-guide comparisons are supported as research; final-pre-result histories remain unqualified for all three selected companies. Alphabet has no matched numerical revenue guide in the selected set, not proof that it never guides.

Match target period and business/metric meaning before selecting by issuance date. Distinguish original-guide delivery, latest within a named reviewed collection, and final issuer guidance before the result. A later result/new-guide release cannot silently rewrite the preceding quarter's expectation. Same-day dates alone cannot establish intraday knowability.

Preserve the specific meaning of an outlook change. A scoped expected expense may coexist with revenue reaffirmation. It does not establish cash paid or a revised historical revenue outcome. A quoted analyst premise does not become management guidance because it appears beneath a CFO label. A headwind already included in the starting outlook is not deducted again; only a supported change relative to that embedded assumption may alter a modeled scenario. Unquantified inclusion cannot justify a numerical adjustment.

**Two kinds of rounding:** display compression and source precision. Rendering an exact printed USD-thousand value in millions with one decimal place is a presentation transformation. It does not reveal the original source's underlying rounding method. Keep original printed values, scale conversion and any supported source bounds available in detail. Display-equal values cannot manufacture threshold certainty.

For example, the UI may say: 'Published values match; the underlying threshold comparison is indeterminate.' Author-prepared Chinese: '公布数值相同；底层数值是否跨越阈值尚无法确定。' A derived interval must preserve dependency: the same uncertain input minus itself is zero, not two independent errors. Consumer recipes must not invent correlation assumptions.

On a partial correction, retain exactly what was newly qualified and name the comparison still incomplete. Alternative Magnite partitions do not become independent confirmation and are never added together. A current corrected observation displayed today cannot silently replace what was knowable in a historical replay.

No source observation here is treated as a September live signal, financial recommendation or validated forecast. Existing Prophet, Portfolio and evaluation owners retain their separate authority.

## 11. Integration into the existing eight tasks

Task3 adapts the eight AB accounting examples and reviewed comparison/cash/rounding rules into accepted native test grammar. Task4 implements the conditional explanations and fixed coverage; it must remove unsupported sentences, not only null out a number. Task6 renders the same meanings in both languages/themes with existing shared client controls. Task7 replaces every synthetic/native-null field through actual lawful source, identity, rights and private admission. Task8 proves the real user journey plus the scoped adverse cases above.

The baseline plan remains eight tasks. CRV-01..CRV-60 remain the release requirements. This document supplies examples for those requirements, not twenty extra release gates or a new scoring system. The proposed separate GET/client remains superseded by the shared-foundation amendment. Do not implement a second renderer, evidence store, guidance parser, alert scheduler or source registry from the portable fixture fields.

The source code `research/communications/replay_communications_explanation_cases.py` is an OFFLINE REFERENCE CHECKER. Its companion JSON is a public research specimen, not the application's wire schema. Production must not load either as current evidence. The local test module tests that checker only; it does not import GMI/K1/F04 or exercise an API, browser, private store or watchlist. False but self-consistent author annotations remain a known blind spot.

The next substantive design step after this consolidation is a single-document execution reconciliation: integrate the baseline plan's superseded shared-file/route instructions and these examples into one current reading surface for the eventual new Fable receiver, preserving all sixty obligations. Do not commission that receiver now. Reopen the failed historical-source search only on materially better permitted coverage.

## 12. Revision-2 verification and source limits

The four Q2 issuer pages were reopened on September 24 and their selected displayed financial inputs checked. Original-guide and later-guidance examples are retained from the pinned Phases 11/12 studies, not newly certified complete histories. No provider subscription, source retention receipt, live native identity, shared implementation acceptance or current private binding was obtained.

The reference pack fixes four bilingual panels, eight reported-measure pairs, eight bilingual state messages and twenty annotated scenarios. Its replay checks 75 retain/withhold expectations. Eleven local tests examine the checker, including negative controls and the false-annotation blind spot; they are not eleven application tests. The original calculation cases CV01–CV12 remain unchanged. Exact script/data/doc/checkpoint hashes and executed receipts are recorded by the current continuation rather than assumed from these statements.

Source and design references: Phase11 accounting study `0cdd2f65573263d2c5433d5d9a86e68b3ef0fdf4` (blob `ede6b8e6c031065874c90dd5febfd953395a1584`); Phase11 target-period study `4d1e0135ca7726f74227f3c4440a9b0859f4b71e` (blob `611ba25ad6239676774d1db9a81b9a745595a18c`); Phase12 qualification `2722fc72b4eafc11558f089d08c57d3d13b3c47e` (blob `0ad5cbf6a36838d3a95ac68e31418b01ef7fd6d6`). The baseline design remains `d65263dc15a8dc3ddded35b1529c535c881175bd`, with numerical/shared amendments as identified above. No shared upstream state was refreshed or modified for this domain-only consolidation.
