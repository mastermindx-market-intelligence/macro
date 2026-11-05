# Industrials Wave 11 — Adversarial design review

Research cutoff: 23 September 2026. Operation `gmi-industrials-sector-research-20260923-sol-001`; Macro Draft/HOLD PR #7789, branch `sol/industrials-sector-research-20260923`. Entry head `b8641c6717f859f054d4bc2f9b4e91f8bb859b59`. Protected procedure: Mastermind `a7d2b3049e5cdc523e91e61a6e9d70a1cb911157`, Skillpack 1.0.1/bootstrap 1. New read-only interface pin: Macro `d7711a0a08db8008ffe5975bfb3e6b242e4c70bd`; no rebase or custody transfer.

This is the research principal's adversarial self-review, not an independent review, accepted design, production defect report, Fable commission or implementation. It reviews revision 1 of `docs/superpowers/specs/2026-09-23-industrials-result-cash-dossier-design.md`, exact blob `40fd1e3783102c28fe748fe35b927484d4f3dddb`. The prior research remains valid except for the narrow design ambiguities identified below. No live data, identity, rights or deployment is modified.

## 1. Verdict

Revision 1 identifies the correct user job and native owners, but leaves several choices too implicit to give an implementer a reliably bounded task. Do not freeze an implementation plan from it unchanged. The necessary correction is to define an event-scoped financial core, separately gated thematic enrichment, exact source-edition behavior, calculation eligibility, and a complete publication/authorization dependency chain. This does not reduce the sector mission to an earnings page: the shared theme entry and evidenced business context remain required for the eventual complete first vertical.

Missing consensus does not block operating explanation. Missing mandatory source rights, verified identity, an accepted private content role or required event facts does block that delivery. Source-only examples remain negative/partial tests, not the final company workflow. A later shared graph feature must not be made an accidental prerequisite for independently permitted financial-source qualification.

## 2. Newly inspected native evidence

All following paths were read at the interface pin above. These are source-code/contract observations, not live-runtime proof.

| Ref | Path | Exact blob | Material observation |
|---|---|---|---|
| W11-R01 | `engine/company_intelligence/identity.py` | `0e3daabeeebad2482e938f4a3949018dac663a29` | Source-native company/listing representation uses CIK and venue/symbol forms; ListingAlias defaults valid_from to a fixed epoch. A constructor default is not historical alias evidence or a Data OS join receipt. |
| W11-R02 | `engine/company_intelligence/events.py` | `9d839a468ba0de2b2ea090bfe7d3ae698d303c44` | Event identity is issuer/fiscal-period/event-type based, not document hash or publication date. Guidance and results have different supported types. Date coercion can produce midnight, which is not source-time proof. |
| W11-R03 | `engine/company_intelligence/documents.py` | `21ef185557d54e8b4c24c4e84c6f94bf3ea1190b` | Source documents have their own revisions and event bindings. Only text spans are classified replayable; a table-cell address can be address_only. Receipt presence is not semantic cell qualification. |
| W11-R04 | `contracts/statement_cell.v1.md` | `eb47a317bfc06fbb15c6bd99e2d85dd1bcca1986` | Duration columns include start and end; source context/unit/dimensions matter. Conflicting duplicates are ambiguous. Its described delivery is a golden fixture, not a production issuer service for these cases. |
| W11-R05 | `engine/theme_graph/rights.py` | `63ba2b60e9be6615208fab5b53b1fbcb44f4f433` | Registry reads pass through an lru_cache keyed on path. The public-emission permission function is not automatically the private-member display policy. |

The inspected prior private publisher/API, closed transcript packets and K1 composition limitations remain recorded in Wave 10 at `da092e5d4a64dbb7c3958826f8cd60d7cbd02cc5`; this review does not claim those entire interfaces were reread at the new pin. They require exact material compatibility before implementation. One exact default-branch code search for PNR in `data/baskets/membership.json` returned no match; that does not prove absence from the live graph or all theme surfaces. One exact cache-clear call search returned no matches; that does not establish no reload elsewhere.

## 3. Findings to resolve in revision 2

**W11-F01 — Ambiguous first-vertical dependency boundary.** Revision 1 names financial-event, GMI and K1 work without separating which is needed for a single-event explanation. Freeze core financial admission, arithmetic, identity and private display as one capability. Gate additional GMI assertions and cross-owner composition only where consumed. Do not fabricate successful K1 composition or replace the missing graph with another store. The complete theme journey still needs an evidenced existing entry/context; do not force either company into a basket to make the example work.

**W11-F02 — Event, document and correction can be conflated.** Preliminary figures and a final report can refer to the same fiscal result while being distinct documents. A later filing enriches the evidence set; it does not imply the earlier source was incorrect. A guidance update can be a separate owner-native event type. Use incumbent event bindings and document identities, preserve editions, and distinguish enrichment, finalization, correction, duplicate delivery and unrelated corporate news. Do not create date-suffixed events or relabel every final report as an amendment.

**W11-F03 — Numeric receipt alone is insufficient.** Replaying the characters 68 or 1.14 does not prove their currency, scale, period, business, denominator or preliminary/final status. Require the governing row, column, caption and scope evidence, or a validated native structured cell carrying them. Address-only table locations are not byte-replayed facts. No additional parser or global metric catalog is authorized by this requirement.

**W11-F04 — Similar identity field names can conceal different namespaces.** A CIK-backed company label, legacy venue/symbol security string and Data OS issuer/security/listing are distinct contracts. Defaults in a ListingAlias constructor do not prove historical validity. The exact accepted bridge and period evidence must support any canonical link; no guessed MIC, ticker match or fabricated epoch. Keep source-labelled evidence useful where allowed, but do not count it as the accepted identity-bound dossier.

**W11-F05 — 'Current rights' has an untested refresh dependency.** A same-path cached registry can retain its old contents after the file changes. An isolated characterization must test that condition; it does not prove a live leak or the behavior of a deployed reload mechanism. Before delivery, the existing rights/access owners must define and prove policy-version visibility and revocation behavior, including dependent calculations and narrative. Repeating a cached helper call is not a freshness guarantee. Do not create another rights service.

**W11-F06 — Partial results can contaminate prose.** Hiding an invalid table row while retaining a sentence derived from that row still exposes an unsupported or disallowed conclusion. Bind every material sentence and comparison to its exact operand/source revisions. If one required input is withheld, the dependent assertion must be removed or explicitly limited. Unrelated valid sections remain available. Evidence loss is not a numerical zero or a confident neutral view.

**W11-F07 — Recast accounting and knowledge vintage are separate.** Comparisons may use compatible recast periods for current analysis, but that does not make the recast data knowable at an earlier date. Preserve both perimeter and source edition. Do not accept a period comparison merely because both columns end on the same day; do not reject legitimate quarter-to-prior-year comparisons because their literal dates differ.

**W11-F08 — Derived identity and publication coherence are incomplete.** A projection must bind source object IDs/digests, selected cells, identity-binding revision, formula version, normalization method, selected cutoff/mode and reviewed narrative. Its permission decision is time-of-use policy, not a forever-valid boolean in an immutable object. Corrected cells invalidate every dependent comparison and sentence. Failure of a new publish must not advertise a mixed new/old generation; preserve the existing pointer protocol rather than inventing another publisher.

**W11-F09 — Missingness needs a precedence rule.** A storage/integrity failure is not 'no earnings event'; unauthorized access must not inspect private existence; unavailable consensus is not a total data outage. Distinguish authentication, authorization, rights, artifact integrity, identity, measurement and true absence using the existing owners. The first three are disclosure gates, not mere yellow badges over a leaked body.

**W11-F10 — Test examples are not the sector thesis.** Exponent and Pentair are deliberately difficult correctness cases, not a recommended portfolio or a sufficient industrial-theme universe. First-delivery acceptance must demonstrate the economic task and an existing theme/company return path without assigning new holdings. Channel, contract, fleet, retained-service and client-funds cases stay in the Wave 9 catalog and must not be discarded after the pair works.

## 4. New primary-source qualifications

W11-S01: Exponent June-quarter Form 10-Q, https://www.sec.gov/Archives/edgar/data/851520/000119312526340211/expo-20260703.htm . Note 2 describes percentages of COMPANY revenue: Engineering/Other Scientific time-and-materials 68%, Environmental/Health time-and-materials 12%, and total time-and-materials 80%; the corresponding fixed-price components are 19%, 1%, and 20%. Thus 68% is not a disclosed within-segment mix. The half-year total is 78%, not the quarter's 80%. Note 9 says one client represented 11% of quarterly revenue, while no client exceeded 10% over the half year. These different periods do not conflict. No client name, retention rate, segment profit allocation or exact risk estimate is inferred. The cover identifies EXPO common stock and Nasdaq Global Select Market, but it is not a native Data OS receipt. The exact SEC acceptance index remained unreadable; the signature is still not an acceptance timestamp.

W11-S02: Pentair final release attached to SEC accession `0000077360-26-000042`, https://www.sec.gov/Archives/edgar/data/77360/000007736026000042/q22026pressrelease.htm . Its segment-reorganization section states that residential/irrigation flow moved into Water Solutions effective January 1, with prior comparisons reclassified; Pool is unchanged. The same release describes a separate announced Taco transaction and excludes that anticipated acquisition from full-year guidance. This is a more precise denominator and event-boundary reference, not an ownership-close receipt or a market-reaction study. Its accession-index page remained unreadable.

W11-S03: Pentair July 14 preliminary release, https://investors.pentair.com/news-releases/news-release-details/pentair-announces-chief-financial-officer-transition-and . Preliminary values and management explanations remain preliminary/attributed. Its scheduled final-report date is not the exact later release instant.

All numerical findings are selected original editorial observations from HTML. No raw corpus, full source data or current private product snapshot is published. Repeated mirrors are one lineage, not independent corroboration. No legal opinion or automatic source-rights decision is supplied.

## 5. Next bounded work

Add a binding revision-2 adjudication to the written specification on this same research carrier. It should resolve the ten findings above with explicit dependency boundaries, an owner-role contract, a comparison checklist and executable research-only negative examples. Preserve the original revision and its thirty requirements; add traceable supplemental cases rather than renumbering old ones. Native contracts remain proposed until accepted by their owners. The implementation plan and final Fable handoff remain held.
