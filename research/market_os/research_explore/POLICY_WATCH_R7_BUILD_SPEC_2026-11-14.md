# Policy Watch R7 — world sources, people and dated research

Status: DESIGN CANDIDATE / IMPLEMENTATION NOT STARTED.
Parent: [Research Explore migration](../RESEARCH_EXPLORE_SHARED_SHELL_2026-11-14.md).
This addendum extends [Policy R6](POLICY_WATCH_R6_BUILD_SPEC_2026-11-14.md). Accepted Now, Pipeline, Central banks, Market memory, Calls, Transmission and Exposure designs remain reference compositions. Complete theme/locale/interaction parity and production acceptance remain open.

## 1. Product decisions and native design map

World answers what was published within a covered source scope. People answers what a source establishes about a person's role or relationship at a relevant date. Dated research preserves an original interpretation and lets the reader inspect newer evidence without silently rewriting the old answer.

Every source title, person, document passage, date, policy, role and value in these R7 compositions is synthetic. Fixture metadata is in the native root and Build reference. The source clocks, availability and role projections are design targets, not claims about live feeds or current office holders.

| Editable Paper page | Format | Root |
|---|---|---|
| [Policy R7 · World source changes · Candidate](https://app.paper.design/file/01M6Y2X53ABR4MME4ATS15B8SH/p-G-1) | 1440 × 1240 · EN light | 4DT-1 |
| [Policy R7 · Treasury source · Analysis unavailable](https://app.paper.design/file/01M6Y2X53ABR4MME4ATS15B8SH/p-H-1) | 1440 × 1240 · EN light | 4KT-1 |
| [Policy R7 · People & documented relationships](https://app.paper.design/file/01M6Y2X53ABR4MME4ATS15B8SH/p-I-1) | 1440 × 1240 · EN light | 4R0-1 |
| [Policy R7 · Dated research & changed evidence · Dark](https://app.paper.design/file/01M6Y2X53ABR4MME4ATS15B8SH/p-J-1) | 1440 × 1240 · EN dark | 4XU-1 |
| [Policy R7 · Sources & coverage · 1024](https://app.paper.design/file/01M6Y2X53ABR4MME4ATS15B8SH/p-K-1) | 1024 × 1160 · EN light | 53L-1 |
| [Policy R7 · Person & evidence · Mobile](https://app.paper.design/file/01M6Y2X53ABR4MME4ATS15B8SH/p-L-1) | 390 × 1240 · EN light | 57I-1 |
| [Policy R7 · 英国政策原文 · Mobile dark](https://app.paper.design/file/01M6Y2X53ABR4MME4ATS15B8SH/p-M-1) | 390 × 1240 · ZH dark | 5J4-1 |
| [Policy R7 · Time, identity & availability states](https://app.paper.design/file/01M6Y2X53ABR4MME4ATS15B8SH/p-N-1) | 1400 × 1240 · EN light | 5B2-1 |
| [Policy R7 · World, people & dated research · Build](https://app.paper.design/file/01M6Y2X53ABR4MME4ATS15B8SH/p-O-1) | 1400 × 1240 · EN light | 5DE-1 |

The Chinese mobile view uses Noto Sans SC, retains an explicitly labeled English source passage and localizes interface labels. It does not disguise a translation or interpretation as the original source.

## 2. Pinned owners and material findings

Macro baseline: e856ef0200a0c508c78ef9a6666116020e4835d1.
Terminal baseline: fe49f3b5765dd4e10721928716a6a730e78c7ae1.
Protected Mastermind pin: 199fd4f91ecc426b1d974eb3bf47f5162476cf24.

| Existing owner | Blob | R7 consequence |
|---|---|---|
| engine/policy_watch_current.py | 7af6bc4bae50b9a3bff2db656dc267a86a93507d | Retain current official projection and independent availability states |
| engine/policy_intent_desk.py | 8ab5dc662c8f9b8ec1e2500e755ebdc8ba0c04c2 | Lifecycle owner retains source-backed stages, corrections and reinstatement |
| engine/uk_policy_brain.py | 318b292fb039932c5a09cdd68e5e0cde5d564c81 | HM Treasury documents, source facts/excerpt and separate model reading |
| engine/europe_news_intel.py | 8e3f0c15bcd48ede2b199afca25e98ddd1a880e9 | Configured EU/UK sources, first-print desk rows and incumbent qbus join |
| engine/influence/graph.py | 1907855f7f0a7e5d33588a4a36b6f0fce6a431d3 | Existing identity/relationship surface; generated labels are not documentary proof |
| data/policy/intel.json | 8309d093709e5e33026f90729bc3057848c184be | Dated 13 July 2026 editorial substrate, not refreshed current truth |
| templates/policy_watch.html.j2 | a7e46126baa488760386b1aa8fb34355bbf1e41c | Fixed THEATER_COPY and Moves in force fallback must not overwrite evidence meaning |
| scripts/build_policy_watch.py | 2990507e6cb23f91de567719e728d33042019473 | Retain publication/integration owner and separate generated-analysis dates |

The current R6 contract links the first two owners. R7 root inspection verified the remaining six at this same pin. These static findings do not establish current runtime configuration or reproduce an incident.

The international/regional view is a read projection over incumbent owners. No new global collector, event registry, graph, office-holder database, lifecycle authority, scheduler or alert owner is authorized by a design. Rendering must not invoke uk_policy_brain.run for collection/model work or influence.graph.build_view, which writes output.

## 3. World: related documents with honest scope

The specimen uses Region = Europe, Topic = Industry & investment and Published = Last 7 days. Region is not a legal jurisdiction: the rows explicitly retain United Kingdom and European Union. An EU-only filter must not admit UK records.

The queue has three separate documents: an HM Treasury consultation on 13 November, a European Commission announcement on 12 November and a Bank of England speech on 11 November. A speech is not a rate decision. Related topics do not merge different legal actions or count as independent confirmations.

A snapshot clock identifies the served response; it does not refresh every source. Each document preserves publication time and precision. UK Recorded remains distinct from publication and from regional first_seen_utc. A document evaluated today but published outside the window must not enter a publication-date filter. Unknown publication time needs an explicit exclusion/unknown-date policy, not substitution with evaluation time.

The selected document shows the source-backed proposed stage and consultation closing date beside the primary source action. Stage must come from lifecycle evidence; a label in old editorial prose cannot establish legal force.

The regional desk's event_id, article item_id and qbus event_key are different. qbus owns event grouping; read_events returns the desk artifact without event_key. Desk accrual keeps the first event_id, while item identity includes source/URL/title. Preserve distinct document identities through the existing qbus item join or an incumbent producer extension; a title/domain grouping cannot silently erase a separate source version.

## 4. UK document: source survives unavailable analysis

The UK owner is an HM Treasury desk, not comprehensive UK government or Bank of England coverage. It can retain document type, source URL, published_iso, doc_version and an excerpt while model classification is unavailable.

The fixture retains November source version 2 in the same explicitly linked policy source series as the July scope notice. Version 2 is the friendly design label for a retained immutable identity. Current latest-record/doc_version fields alone do not prove a historical document archive or source comparison service.

The original English excerpt states a proposed energy-intensity test and unresolved threshold/application process. The legal state remains Proposed, not in force. Comments close on 12 January 2027. This date is synthetic documentary content, not a calculated legal deadline.

Published is 13 November 2026 at 09:00 GMT; Recorded is 09:20 UTC. The current _base_record assigns known_at_iso at evaluation time. Do not relabel it First observed or use it as proof of first public availability. A durable first-observation claim requires a separate immutable owner receipt.

No analysis for this source version is a truthful state. Do not say Pending without an admitted running job. Source, policy history and dated research remain navigable. Stance values supportive/restrictive/mixed/routine are model classifications; they are not legal status, quantified market effect or trade direction.

## 5. People: time, identity and assertion type

The selected person is fictional Dr Maya Ellis. The source-backed fixture chronology is:

| Fact | Date / meaning |
|---|---|
| Industrial Capacity paper authored | 10 February 2025 |
| Appointment announced | 28 August 2025 |
| Adviser role effective start | 1 September 2025 |
| Adviser role end | 30 June 2026 |
| Selected role-as-of date | 13 November 2026; former adviser |
| Separate forum membership start | May 2024, month precision; end unverified |

Announcement and effective start are distinct. The paper predates the role. Do not attach the later adviser title to the author's authority at publication. The role's end does not close the independent forum membership. End unverified does not establish continuing membership.

A role needs person and institution identity, role type, validity interval, date precision, observation clock, source version/span and correction lineage. Role as of is an effective-date query; the separate evidence cut controls what is known. Changing the role date does not automatically create a then-known backtest or change the authored paper.

The title-page passage establishes authorship only. Membership, advice, citation, adoption, ownership and control are separate assertions. Policy adoption remains unestablished in the view. A related policy topic is a discovery link, not adoption evidence.

Policy decision-makers are currently strings without canonical office-holder IDs or validity intervals. Existing graph actor IDs are useful identities but not a verified office registry. The graph can synthesize CONTROLS from actor kind/ticker membership and assign FACT/confidence without a dated supporting record. Do not promote that output into documented control or decision authority. Shortest paths, minimum confidence and alt-data co-firing are not causal influence or relationship verification.

The unresolved-name state retains separate paper-author and office-holder identities until exact evidence supports a merge. Missing dates and URLs must remain missing; graph build time is not an event date.

## 6. Dated research and changed evidence

The dark brief preserves its 13 July 2026 analysis date, version, conditional interpretation and three original source dependencies: 17 June discussion paper, 24 June statistics release and 8 July scope notice. The November version is a separate new-evidence panel. The July analysis is explicitly not reassessed.

Each interpretation needs an analysis identity, author/model identity where recorded, analysis timestamp, source-cut identity, immutable dependency versions and status. The source series must explicitly prove predecessor/revision linkage before the UI claims a newer version. Missing original bytes means comparison unavailable, not unchanged.

Do not replace unavailable July dependencies with a November source or refresh the thesis when the page rebuilds. Keep withdrawals, corrections and supersession inspectable. A fresh source or generated model timestamp does not make the dated intel.json substrate current.

The linked call retains its original criterion and resolution event: publication of final eligibility guidance. Open means unresolved; it is not a positive outcome or a forecast probability. Calls/results ownership remains the R6 incumbent.

Preserve historical Fed profiles/task forces, administration decision-makers and levers, geopolitical theater analysis, rotation context and monitored sources through named Research destinations. Their original dates and evidence classes travel with them. A missing lifecycle projection cannot cause older levers to render as Moves in force.

## 7. Coverage: source availability is not event completeness

The 1024px specimen uses the existing 72px collapsed shell rail and distinguishes the HM Treasury owner from the regional EC/BoE owner. It shows six configured source candidates, not all sources in Europe.

Regional configured source eligibility and live fetch outcome are separate fields. The pinned module reports some deliberately excluded sources as SOURCE_OUTAGE with a distinct rights_state. The consumer must use the reason: Not collected, with official-source access and no retry. It must not imply a transient network failure.

Documents from an excluded publisher are not collected by that lane. Another covered publisher may still mention the same event; source absence does not prove event absence. Last successful check remains Not recorded where no receipt supports one.

The current regional body_sha256 hashes the RSS description, not original full-document bytes. Do not call it a verified full-document hash or use it indiscriminately across desks. Preserve actual original text/retention/rights status through incumbent owners.

Extend owner receipts where needed for successful empty, unavailable, delayed, disabled/excluded and unknown coverage. Keep prior readable records with original evidence clocks. Source, analysis, lifecycle and comparison availability remain independent. The UI must not claim all clocks exist for every source.

## 8. Shared-shell interactions and feature disposition

| Action / capability | Required behavior |
|---|---|
| Open a World record | Bind exact source/document/version; preserve region/topic/publication filter, sort, snapshot, selection and scroll |
| Open a related source | Keep its independent publisher and jurisdiction; preserve the prior source return |
| Change role-as-of | Recompute contextual role projection against the declared evidence cut; do not rewrite the authored document |
| Select a relationship | Open its own type, interval and supporting passage; retain person selection |
| Open source/translation | Distinguish original-language text from translation; return to the same document/version |
| Compare dated research | Retain analysis identity and all original dependencies beside the selected new evidence |
| Navigate Research | Retain World, People, Company exposure, Calls/results, dated profiles/theaters, rotation and source monitoring through named owner destinations |
| Open/close details | Keyboard/touch equivalents; Escape and Back restore focus and exact context |
| Unavailable source/model | Keep unaffected evidence usable; do not fabricate a job or replace a missing value |
| Restricted record | Reuse incumbent account/access behavior and safe return state |

Retain Now/Pipeline/Communications/Central banks/Market memory and deepen World/Influence. Relocate implementation mechanics to source detail and Build references. Remove fixed template overrides that replace source-backed meaning. Block unsupported current-role, full-document-verification, adoption and complete-coverage claims until owner proof exists.

Touch targets need adequate hit areas even where desktop buttons are visually compact. Respect reduced motion, existing theme and locale ownership. All native routes must be admitted through Terminal's route catalog while preserving policy_watch.html compatibility. Static Paper buttons specify interactions; they do not execute them.

## 9. Verification and remaining work

Implementation proof must follow a real authorized producer → typed shared-shell consumer → exact source/version → restored queue. Exercise an old publication evaluated today, EU versus Europe filters, two related announcements, source available/model unavailable, excluded source versus outage, missing predecessor, source correction, paper before appointment, announcement without effective start, ended role with independent membership, and a similar-name identity collision.

Use request/snapshot identity for filters, pagination, source drawers and historical/as-of selection. Verify accessible focus return, 1024px layout, English/Chinese expansion, dark/light contrast and original-language source access. Do not create superficial markup tests or treat static screenshots as persistence/runtime proof.

Nine final compositions were inspected by the principal and bounded read-only reviewers. Corrections included Region labeling, membership uncertainty, source-scope wording, redundant text/actions, spacing and Chinese font styling. A read-operation/module-name collision was reconciled against original receipts and the partially created root before adding only absent modules. The owned Chinese root was replaced to correct malformed font styling; its final identity is 5J4-1. No foreign or held board was modified. All nine final roots received observed guarded finish receipts.

Exact screenshot identities and digests are in [the inventory](PAPER_INVENTORY_2026-11-14.json). The cumulative design set is 92 pages: 72 product/responsive/theme/locale, fourteen Build and six state sheets. Sixteen mobile and four intermediate views are present. This is a design milestone; remaining family follow-through and systematic parity are open. No product source implementation, collector activation, alert enrollment, account mutation, trade, merge or deployment occurred.

Source files can be reviewed at [the pinned Macro tree](https://github.com/mastermindx-market-intelligence/macro/tree/e856ef0200a0c508c78ef9a6666116020e4835d1); precise paths/blobs above bind the findings. The next bounded design unit is Capital Structure's conflict, unavailable-anchor, save-reconciliation and request-restoration states.
