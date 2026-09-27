# Consumer Defensive — native-owner feasibility R5

**Research/design proposal, 2026-09-23. Not an implemented capability, accepted interface extension or final Fable commission.**

Operation `gmi-consumer-defensive-research-20260923-sol-001`; parent `WS:GMI-THEME-GRAPH`; incumbent Macro Draft/HOLD #7792, branch `sol/consumer-defensive-research-20260923`. MISSION_COMPLETE: false. Fable handoff: NOT_ISSUED.

## 1. Decision and evidence boundary

The selected direction is an owner-preserving Consumer Defensive economic interpretation module, not another financial database or theme engine. Use Earnings Intelligence for release/transcript observations and guidance; FIF for actual filing-native financial occurrences and compatible calculations; GMI for admitted thematic relationships; existing financial/market owners for valuation and price context; the shared dossier/template for presentation; and the existing private publication owner for protected member research.

This assessment resolves implementation-location uncertainty. It does not prove that the target companies are covered in production, that a deployed private store is healthy, that cross-type identity composition works, or that the existing shared dossier is already implemented. Where a seam is incomplete, the proposal states the exact limitation rather than assuming an interface from a plan.

Fresh protected Mastermind source: `4c1b3d389286df2a4b5b98a4d4491f2c8a1263f2`; protected-master metadata and compatible INDEX read. INDEX/ACTIVE_EXECUTION/WEB_CEO_DELEGATION/CLOSEOUT same-pin blobs match their complete text already loaded in this continuing conversation. Initial incumbent research head: `6fa549984b98690f06b442db5bae944530788d83`. Fresh Macro main/interface-read pin: `2b2cae6a148f920b5c4e7ebd8df19ed14b159f5a`. The research branch is not rebased: its original base remains `c4da107fe729e46b4d4036b3e0e290390315d0fd`.

Code observations below are from the fresh interface pin, except the explicitly identified unmerged STSI candidate. Search-index excerpts were navigation only and were not treated as current-main source. Direct work reason: PRINCIPAL_JUDGMENT.

## 2. Findings from the actual implementation

### F01 — The public company teaser is not the detailed financial owner

`engine/company_intelligence/contracts.py` defines a closed `company_intelligence_context.v1` surface. Its `PUBLIC_METRICS` includes broad revenue/EPS growth and gross margin alongside narrative-derived metrics. It does not contain the required family of category, channel, pure-versus-mixed price/volume, commercial-right or capital observations. Unknown top-level fields are not a harmless extension. Do not overload summary/highlight text with a hidden machine-readable financial ledger.

### F02 — A reusable earnings extraction seam already exists

`engine/company_intelligence/event_workspace_build.py` binds a supplied Exhibit 99.1 body to CIK/accession, source hash, fiscal event and explicit source-availability/observation clocks. It calls issuer profiles rather than requiring ticker branches throughout the generic builder. `issuer_profiles.py` supplies release-fact, transcript-claim and guidance callables. Additional literal facts use `event_fact.v1`; failed or ambiguous source location emits a typed absence.

The first Consumer Defensive release should add bounded issuer profiles under this owner and prove their native round trip, instead of writing an independent sector extractor/store. Existing identity factories inspected in `production_registry()` cover Apple and four homebuilders; this is an observation about this code path, not a certification of all deployed coverage. Consumer Defensive profiles were not found in that inspected registration path.

### F03 — A source span alone does not prove economic scope

The profile helpers retain source body hash, document ID, byte span, event, metric, value, unit, period and basis. Existing homebuilder parsing explicitly distinguishes quarterly and year-to-date columns. Consumer Defensive needs analogous binding of table heading, row, column, fiscal interval, company/segment and adjustment basis. Finding a literal number is insufficient when the same value appears elsewhere.

The inspected `validate_event_workspace` validates the outer lists and selected invariants, including refusal of a licensed-consensus beat/miss claim. It does not, in the inspected code, perform complete semantic validation of every nested fact's economic scope. Therefore proposed new facts require explicit native validation and discriminating tests; a valid outer workspace alone is not sufficient acceptance.

Use the existing fact shape for bounded literal observations whose scope is fully represented by a registered metric definition plus the native event, period, unit, basis and source receipt. Do not pack JSON into metric names, invent global brand IDs, silently add fields to the closed outer workspace, or claim general multi-dimensional comparability. If those existing fields cannot preserve a required distinction, obtain an explicitly versioned native-owner extension before that distinction ships. Broader revenue-purity and cross-brand joins may remain unavailable in the first slice.

### F04 — Source and observation time are already distinct

The earnings builder preserves `source_available_at` as the SEC-acceptance input and carries forward first `observed_at` for an unchanged source revision. A changed source can move the event to corrected without later unchanged rebuilds erasing the correction. Consumer Defensive must consume this behavior. An issuer press release that preceded SEC acceptance has its own source-publication fact; it must not be represented as the existing field's earlier meaning without a supported native extension.

New synthesis uses immutable workspace generation plus interpretation-code revision. A correction invalidates the affected derived explanation through the existing generation chain; it never retroactively edits the earlier explanation or advances its knowledge clock.

### F05 — FIF is an appropriate financial owner, not permission to invent XBRL

`raw_ledger.py` is a bitemporal kernel for document-local XBRL occurrences, contexts, units and source identity. `financial_intelligence_packet.py` provides native entity/query types, bounded packet semantics and distinct historical/retrospective modes, while also retaining an explicitly synthetic golden-fixture path. Those source primitives do not establish a live PG/HSY packet or an unrestricted non-XBRL ingestion service.

Financial statements that are actually XBRL belong with that owner. A hand-read non-GAAP release number is not automatically a filed XBRL occurrence. A fixture passing validation must not be relabeled a real financial packet. No synthetic CIK, occurrence ID or source digest is used for product admission.

### F06 — SEC Company Facts is not a complete source for the proposed detail

The SEC API documentation says the aggregated XBRL APIs use non-custom taxonomies and facts applying to the entire filing entity. It also describes calendar-aligned Frames with differing issuer reporting dates. This makes Company Facts useful for appropriate entity-level facts, not a substitute for all segment, category, pricing or issuer-defined non-GAAP observations. The release-document path above is therefore a material dependency, not optional polish. [P01]

### F07 — K1 is a pointer/composition contract, not a fact warehouse

`contracts/evidence_foundation/README.md` and its vocabulary preserve owner-native object IDs, native clocks, correction capability and all-false decision authority. `fif.packet` currently names a parser, not a physical storage reader. The earnings workspace likewise has a native CIK subject. GMI evidence has an evidence-ID subject.

The K1 recipe input has no validated cross-type bridge-object slot. Native-only/cross-type subjects can therefore refuse a unified security recipe even when individual objects exist. Do not invent a bridge from ticker similarity, a CIK directory or a caller-authored join declaration. Render separately typed owner-local sections where legally composable, with an explicit unresolved cross-owner join. The page must not present those sections as a successfully fused security packet.

### F08 — Robotics curation is not silently available on main

The current `contracts/theme_graph/evidence.v1.schema.json` is still closed and lacks the proposed Robotics `curation_assertion` body. The evidence receipt is not the Consumer Defensive financial store. Preserve Robotics #7773's ownership; do not recreate or self-enroll its candidate field. Existing admitted GMI relations may support navigation; a research category name alone does not become canonical membership or a price basket.

### F09 — Shared dossier work is real but not yet a production prerequisite satisfied

At the interface pin, fetching `contracts/sector_intelligence/sector_dossier_read_model.v1.schema.json` returned 404. The existing source plan names the intended shared composer, publisher and `templates/sector.html.j2`. A targeted current PR read located incumbent #7777: open, unmerged, head `4122e3b7e1524482216fb156f201f8229c14011b`, branch `sol/stsi1-sector-federation-technology-dossier-20260921`. Its five-file slice adds the governed contract; it does not by itself implement the entire shared page/composer.

The candidate contract was read at its exact head. Its outer shape is closed and includes identity, dimensions, changes, children, conflicts, receipts and authority. Do not append an arbitrary Consumer Defensive payload to it or treat its knowledge cutoff as every source's business date. The existing `templates/sector.html.j2` is a cycle/holdings page, not proof of a fully built Consumer Defensive dossier.

Use the accepted shared owner once its actual mount/extension contract is ready. Independent issuer-profile and research work can advance beforehand, but a UI dependency is not permission to fork the shared shell.

### F10 — Public and private earnings publication are different paths

`engine/neuralweb/company_intelligence_reader.py` is explicitly a public R2 marker/generation reader. It checks source objects and bounded sizes and does not fall back to a checkout. Browser-tool inspection of its current workspace manifest URL was unavailable in this session. That is a tool-path limit, not proof of a production outage or zero company coverage.

A separate existing private owner was positively located: `app/earnings.py` authenticates and calls `enforce_site_full(..., always=True)` before private store access. Success and failure carry private/no-store, authorization variance, noindex and nosniff headers. It loads the existing private Research Vault adapter. `engine/earnings_narrative/private_publication.py` validates outside-repository staging, writes immutable content-addressed objects, verifies them, then promotes its pointer.

This resolves the existence of a private publication mechanism, not readiness for an arbitrary new payload. Its record shape is closed (`earnings.tier_payload/v1`), and its current context/record roles have defined semantics. The selected proposal is owner-approved extension/reuse there for protected economic interpretation, not a new bucket, private data mirror, pointer or publisher. Baseline already-public facts remain under their current classification; detailed new member research defaults protected pending actual rights/publication approval.

## 3. Minimum field-to-owner feasibility matrix

The words EXISTING and PROPOSED describe code/interface evidence, not deployment acceptance.

| Required information | Native owner / route | R5 finding | First-slice behavior |
|---|---|---|---|
| Issuer/event/fiscal quarter | Earnings identity, event and profile registration | Existing seam; target registration owed | Required; never guess company/security equivalence |
| Filing/Exhibit identity | earnings_release binding plus collector CIK/accession | Existing seam | Exact retained filing and byte receipts required |
| Reported revenue/EPS | Native release facts or real FIF occurrences | Representation exists; target extraction owed | Required for selected story |
| Organic growth, price, volume, mix | IssuerProfile release facts | New profiles required | Preserve issuer-defined mixed fields and rounding |
| Gross/operating margin | Release/FIF matching measure | Native observation/derived distinction needed | No basis-changing comparison |
| Cash/capex | Financial owner and issuer definition | Coverage unverified | Omit inference or show explicit unavailable bridge |
| Brand/segment contribution | Source scope, native financial facts and admitted GMI relationships | General structured scope incomplete | Selected reported segment only; no guessed brand purity |
| Guidance | Existing IssuerProfile guidance callable | Existing callable currently transcript-oriented | No release-guidance shortcut; explicit owner work if selected |
| Prior management versus actual | Exact immutable events, matching target/basis | Separate comparison proposal | Not a consensus beat; defer until compatible native input |
| Consensus and revisions | Existing licensed expectations owner | Entitlement/producer not proven here | Optional unavailable; no invented market expectation |
| Current valuation | Existing price, financial and valuation owners | Exact target joined read not proven | Do not fabricate forward multiple or fair value |
| Market reaction/leadership | Existing market/leadership owners | Target join unproven | Separate optional contextual section; no ranking change |
| Theme membership | GMI admitted relation/latest-belief reader | Existing semantic owner | Research slice label does not create membership |
| Canonical security join | Data OS plus accepted owner identity bridge | K1 cross-type composition constrained | Native subject retained; link only with valid binding |
| Source history and correction | Earnings manifest v2 / FIF as appropriate | Existing primitives | New generation; no in-place historic rewrite |
| Private member explanation | Earnings private publication and authenticated API | Existing mechanism, new content binding owed | No public mirror; no new store |
| Shared UI and hierarchy | STSI/F04/template owner | #7777 unmerged; full mount not proven | Dependency held, no competing implementation |
| Outcomes/calibration | Existing evaluation owner | Studies proposed; no strategy proof | Research/shadow only; no trade effects |

## 4. Rechecked primary examples and sampling decision

P&G's July 29, 2026 release reports Q4 sales growth of 2% with organic sales unchanged; its quarter and full-year tables must not be confused. This is a useful positive arithmetic/negative interpretation case for the extraction profile. [P02]

Hershey's February 6, 2025 release provides reported 2024 EPS of 10.92 and adjusted EPS of 9.37, with the prior-year adjusted comparator of 9.59 and a reconciliation. It is an explicit HISTORICAL regression case, not the current Hershey dossier. [P03]

The first implementation design should concentrate on demand quality and earnings quality. Existing R2 examples remain the breadth/regression suite; they need not all be first-release launch dependencies. Sample choice is based on source and semantic discrimination, not stock attractiveness. Current production release input must be selected afresh through the native collector, not by hardcoding these research dates or copying the research document into the live store.

## 5. Required next work and explicit non-goals

Write the full-scale masterplan and the bounded first-vertical design using the above seams. Required pre-build decisions are the native metric/scope validation strategy, targeted issuer registration, private content-binding extension, and shared mount contract. The current principal can specify these and produce acceptance cases without touching another writer's product source.

No new lifecycle, graph, identity master, event warehouse, curation queue, valuation engine, loader, watcher or publication plane. No source-value promotion merely because it appeared in R1-R4. No paid panel or consensus subscription assumed. No consumer-side source fetching or financial recomputation. No research priority promoted into security selection or trade authority. No STSI/Robotics writer takeover.

## 6. Evidence register

All native source paths below are at Macro `2b2cae6a148f920b5c4e7ebd8df19ed14b159f5a`, except N12. Recorded ranges are bounded inspection, not whole-module audits.

| Ref | Path / range | Git blob |
|---|---|---|
| N01 | engine/company_intelligence/contracts.py:1-190 | 750cf16e481e98222e6f078eb6a28ef3e8e45d7f |
| N02 | engine/company_intelligence/event_workspace.py:1-230,290-440,600-745 | efdbd91156b2a94e6e8bdca7e8cae454a6860e68 |
| N03 | engine/company_intelligence/event_workspace_build.py:1-190 | 69d39a58ecc9cfd6143192f29eb2e0f62016aeb5 |
| N04 | engine/company_intelligence/issuer_profiles.py:1-200,280-485 | c8895d3d7527aaa302fe96021bd8c480ce62a2d8 |
| N05 | engine/fundamental_forensics/raw_ledger.py:1-170 | 42ccf3ff0e58ed33d91d9868a5db7b01814c04f5 |
| N06 | engine/fundamental_forensics/financial_intelligence_packet.py:1-180 | 99fb3da6920d0804dbb9a3b36609826b78a38ee4 |
| N07 | contracts/evidence_foundation/README.md:1-160 | a47e898309813636cf167c517492aa569aa296ca |
| N08 | contracts/evidence_foundation/vocabulary.v1.json: owner sections for GMI, FIF, earnings | 1st read was truncated after later unrelated owners; no full-file audit claimed |
| N09 | contracts/theme_graph/evidence.v1.schema.json:1-95 | 83dece15e98b9c8775a584afcd6ee09811dad220 |
| N10 | templates/sector.html.j2:1-95 | 88f9cec586ec2d425697e701825263af760665ff |
| N11 | docs/superpowers/plans/2026-09-21-stsi1-sector-federation-technology-dossier.md:1-125 | 6800ca09cba0e31693c1d17ac23bcffd630ce77e |
| N12 | contracts/sector_intelligence/sector_dossier_read_model.v1.schema.json:1-110 at #7777 head 4122e3b7e1524482216fb156f201f8229c14011b | affc11c5ead2d5213a6b0e268b4bcd8734e3c9fb |
| N13 | engine/neuralweb/company_intelligence_reader.py:1-160 | 47fe7d411434ba9ad321bf825edcf380aabc8e5c |
| N14 | app/earnings.py:1-190 | 3b8251388c8e9ae59b933212a7384faaea61eb27 |
| N15 | engine/earnings_narrative/private_publication.py:1-170 | 0ee93909693893f419f0109f9eba1994d94e2b46 |

Public references read directly in R5; URLs are research locators, not retention receipts:

- P01 SEC, EDGAR APIs, page last reviewed April 8, 2025; non-custom/entity-wide fact scope and Frames calendars: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- P02 P&G issuer release dated July 29, 2026; Q4 and fiscal-year headers, net-sales driver table and non-GAAP definitions: https://www.pginvestor.com/news/news-details/2026/PG-Announces-Fourth-Quarter-and-Fiscal-Year-2026-Results/default.aspx
- P03 Hershey issuer release dated February 6, 2025; reported/adjusted full-year EPS and reconciliation: https://hershey.gcs-web.com/news-releases/news-release-details/hershey-reports-fourth-quarter-and-full-year-2024-financial

A targeted open-PR text search for issuer_profiles returned no results. This is not a planned-write collision clearance. #7777 was separately verified open/unmerged by exact metadata. The public workspace-manifest web read was inaccessible via that tool; no outage or blanket tool/access claim follows. Research writes use the original #7792 carrier. Native repository permission read returned push access; actual write/readback remains the effect proof.

No product tests, production source admission, browser proof, security entitlement audit, independent design review or live valuation join was performed in this assessment. All proposed gaps remain explicit in the forthcoming design. No final Fable handoff or worker START is created here.
