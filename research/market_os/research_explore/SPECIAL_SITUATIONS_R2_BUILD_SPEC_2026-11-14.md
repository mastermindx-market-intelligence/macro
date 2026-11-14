# Special Situations R2 — campaigns, announcements and amended terms

Status: DESIGN CANDIDATE / IMPLEMENTATION NOT STARTED. Parent: [Research Explore migration](../RESEARCH_EXPLORE_SHARED_SHELL_2026-11-14.md). R2 extends the accepted R1 event queue, case dossier and 320px reading view. It does not establish production readiness, working prototype interactions, an actionable trade or confirmed collector coverage.

## 1. Product task and design map

The reader should be able to identify the exact campaign or transaction, see what the latest source actually changed, inspect the original evidence and understand whether a calculation is supported. Preserve legal stage, source identity and date precision through every screen. Put source mechanics in the inspector and methodology in a disclosure; uncertainty that changes an answer stays beside that answer.

All entities, documents, amounts, dates and prices on these new pages are synthetic fixtures. They are not verified current events. Fixture identity lives in design metadata and Build references rather than a persistent customer banner.

| Editable Paper view | Size | Root |
|---|---|---|
| [Special R2 · Activist amendment · Candidate](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-2J-1) | 1440 × 1200 | 2MZS-1 |
| [Special R2 · International announcement · Candidate](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-2K-1) | 1440 × 1200 | 2N6M-1 |
| [Special R2 · Compare agreement amendment · Candidate](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-2L-1) | 1440 × 1160 | 2NCV-1 |
| [Special R2 · Cash plus shares · Candidate](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-2M-1) | 1440 × 1200 | 2NIY-1 |
| [Special R2 · Amendment comparison · Mobile](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-2N-1) | 390 × 1160 | 2NPE-1 |
| [Special R2 · Identity, coverage & calculation states](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-2O-1) | 1400 × 1120 | 2NR6-1 |
| [Special R2 · Advanced workflow build contract](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-2P-1) | 1400 × 1200 | 2NTH-1 |

The state sheet presents independent alternative states. Its terminated EX-MA-001 is not a later factual update to the R1 fixture; it is a separate test scenario for lifecycle isolation. Original/held Terminal and Options pages remain untouched.

## 2. Source binding and existing owners

Protected law: Mastermind@199fd4f91ecc426b1d974eb3bf47f5162476cf24. Product baseline: macro@e856ef0200a0c508c78ef9a6666116020e4835d1. Shared shell baseline: mastermind-terminal@fe49f3b5765dd4e10721928716a6a730e78c7ae1.

| Existing Macro owner | Inspected blob | Build boundary |
|---|---|---|
| [engine/special_situations.py](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/engine/special_situations.py) | 4e79fc0b22045917bcb1110092ad402187cddef0 | Existing event/lifecycle/desk integration; add exact case identity and typed projections |
| [engine/activist.py](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/engine/activist.py) | 52279039e08bbf6d494821f02884809fdfe1e91f | Reporting-person resolution and descriptive historical returns |
| [engine/special_arb.py](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/engine/special_arb.py) | 174f87a630703b9eca6aeb40bf84259f734b4f68 | Terms extraction, spread and timing; extend supported consideration models |
| [engine/intl_special_situations.py](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/engine/intl_special_situations.py) | 1d2f389a9af44534de318800354bb881092c0650 | Discovery classification, not authoritative legal stage |
| [collectors/special_intl.py](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/collectors/special_intl.py) | 4e0bb271305d103c67a7272208f66f6715f24265 | Incumbent UK/Canada lanes, market enablement and provider receipts |
| [engine/special_situations_premium.py](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/engine/special_situations_premium.py) | 12e0333862bf7f1aaa4a60c470b38237a7569966 | Typed calculation refusals and pre-announcement reference basis |
| [scripts/build_special_situations.py](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/scripts/build_special_situations.py) | 3e54709abf982a414e48ddcb39a612120cd7f481 | Existing collection/build/publication and thin-store protection |

Do not add a parallel events store, name resolver, collector, entitlement authority, alert runner or route catalog. Replace paid rows_html/setups_html consumption with an additive typed adapter under the incumbent access owner. Terminal AppShell owns account, locale, theme, navigation, global search and history. Rebind current owners and holds before implementation.

## 3. Exact campaign and transaction identity

The current lifecycle groups CIK/category; desk/change projections use ticker/category. These keys can merge distinct agreements or campaigns for one issuer. This is a static source risk, not a claimed reproduced production incident.

A proposed case envelope must carry canonical transaction/campaign ID, subject issuer and security, counterparties/reporting persons, jurisdiction, source record and document version, first observation, occurrence/publication time with precision, predecessor/correction links and owner snapshot. Keep issuer identity separate from case identity. A termination must close its matching agreement only.

The dual-agreement proof uses Northstar/Aster EX-MA-001 and Northstar/Boreal EX-MA-003. Terminating the first must leave the second pending, preserve both histories and retain the user's selected agreement. Tender offers, acquisitions, repurchases and activist campaigns must not share a lifecycle merely because issuer/category match.

## 4. Activist amendments and reporting persons

SC 13D/A currently maps to escalation. The R2 view says Amendment filed until an evidence-backed objective change supports a stronger interpretation. Filing activity and campaign intent are distinct.

The Harbor Industrial specimen changes aggregate disclosed ownership from 10.4m shares / 5.2% to 12.2m / 6.1%, using the same 200m-share denominator. The difference is +0.9 percentage points. The Item 4 objective remains Seek two board seats. Latest holdings as of 11 November is distinct from filing on 13 November at 16:00 UTC and first observation at 16:13 UTC.

Retain reporting-person identities, joint-filing scope, share class, beneficial ownership basis, denominator and each source span. Do not sum overlapping holdings of joint reporting persons. Cedar Grove Partners LP + one reporting person is separate from the subject company. Broad normalization that removes CAPITAL, MANAGEMENT, FUND or GROUP is a search aid, not canonical entity identity.

The current activist track record counts filing rows, including amendments, and measures absolute target returns over 60 trading rows. Four priced rows do not prove four independent campaigns. A first available price on/after a filing date does not prove publication-time tradability. Do not display this statistic as campaign success, benchmark alpha or verified predictive skill. Any future evaluation must bind independent campaign units, source-time availability, price basis, benchmark, missing outcomes and sample eligibility.

## 5. International source chronology and coverage

The selected UK announcement separates a 19 October possible offer from a 13 November firm intention. Recommended cash consideration is 280p per ordinary share. Completion is not announced, and shareholder/regulatory conditions are required but not confirmed satisfied.

The issuer website announcement is labeled as such. It is not promoted to a regulatory filing. Preserve publisher, original URL, language, market-resolution method, original publication clock and first observation. The specimen's 07:00 GMT publication and 07:09 UTC observation are separate clocks.

Current international ingestion has UK and Canada market lanes, gated by configuration; runtime enablement was not inspected or changed. News aggregation and direct wire discovery do not prove official RNS/SEDAR coverage. Broader classifier phrases for other regions do not prove those regions are collected. First-match keyword classification is a candidate category, not legal-stage evidence. Listing market does not prove a cross-border transaction; the current projection's hard-coded cross_border value must not become a user-facing fact.

Extend receipts in the existing collector to distinguish disabled, failed, successful-empty, stale retained and unknown coverage. Preserve old records with their real evidence clocks. An empty response after a provider failure must not become No events. Keep market enablement unchanged during design.

The [Takeover Panel Rule 2.4](https://code.thetakeoverpanel.org.uk/tp/rules/rule-2/rule-2-4.html) and [Rule 2.7](https://code.thetakeoverpanel.org.uk/tp/rules/rule-2/rule-2-7.html) informed the distinction between possible-offer and firm-intention announcements. Pages retrieved on 14 November 2026 displayed the 11 December 2023 edition even through View current version. No automatic legal deadline is designed from that observation. Jurisdiction-specific stages need verified source support; do not impose a universal legal stepper.

## 6. Agreement changes and date precision

The comparison binds the original agreement and Amendment 1 to EX-MA-001. Clause 8.1(b) moves the outside date from 31 January to 31 March 2027. These are preserved original/amended values, not overwritten history. Only one term changed.

Company closing guidance remains Q1 2027; the shareholder vote is 18 November with time unspecified; completion is not announced. An outside date, guidance interval, vote and actual completion are distinct fields. Never convert quarter/month-only guidance into an invented day for a polished timeline.

Cash consideration of USD42.50 per target share and a synthetic USD85m termination fee are unchanged. The fee's expanded inspector must retain payer, recipient, trigger and relevant clause. It is not necessarily owed and is not a per-share deduction from consideration. Missing fee conditions cannot be filled by inference.

Field-level comparisons require two retained document versions and source spans. Missing predecessor means comparison unavailable, not unchanged. A corrected extraction preserves both extraction versions, the correction reason and dependent calculations at their original observation cuts.

## 7. Supported consideration and calculation refusals

The current arb parser supplies a price/share and consideration label; it does not implement exchange-ratio, collar, election or proration economics. The R2 calculator requires an extension within that owner before it can ship.

For EX-MA-002, Mariner Software / Vale Systems:
- Cash is USD22 per target ordinary share.
- Ratio is 0.5 acquirer shares per target share.
- The acquirer quote is USD40 per compatible ordinary share.
- Indicative consideration is 22 + 0.5 × 40 = USD42 per target share.
- Target quote is USD39; gross spread is (42 / 39 − 1) × 100 = 7.69%.
- Both quoted inputs are timestamped 13 November at 21:00 UTC.
- Mechanical acquirer-price scenarios of USD36/40/44 yield consideration of USD40/42/44 while the USD39 target quote is held constant. They are user assumptions, not forecasts.

Bind both security identities, corporate-action basis, share/ADR conversion where relevant, quote unit, currency, timestamp and price source. A .L ticker suffix and GBP currency do not establish pence-versus-pound compatibility. When a 280p offer meets a 2.68 quote with unknown units, withhold the spread and expose the missing unit.

Month-only December 2026 guidance cannot support precise-date annualization. The parser's month-end fallback must not leak into the consumer as a known closing day. Election, contingent value, collars, prorations, unmatched securities, stale inputs or unresolved currency conversions need an explicit unsupported/pending state. A cash component alone is never total mixed consideration.

Preserve the premium leaf's typed refusals: ambiguous issuer, absent terms, currency mismatch, missing reference price and announcement chronology unknown. Its pre-first-relevant-announcement close differs from the generic 30-row lookback proxy. Label the selected basis; do not combine them as the same unaffected price.

## 8. Interaction and accessibility

| Action | Required result and retained context |
|---|---|
| Select an amendment | Exact case/source version updates; original queue filter, selection, scroll and return context persist |
| Inspect reporting persons | Canonical identities and joint-filing scope open without treating the subject company as filer |
| Open original/amended clause | Exact retained document anchor opens; return preserves the comparison and current focus |
| Expand unchanged terms | Reveal two actual terms with source spans and fee conditions; no repeated narrative |
| Change calculation input | Mark an explicit scenario, bind compatible security/unit/time and recompute only supported arithmetic |
| Refresh while reading | Retain selected case/version; offer new evidence without silently moving the comparison |
| Source unavailable | Keep permitted last valid content and its date; show scope of missing evidence beside the affected action |
| Mobile comparison | Stack original and amended values and source links; preserve vote/guidance/completion distinctions |
| Close transient detail | Escape/Close restores focus to the originating control; Back/Forward restores route state |

All controls need keyboard equivalents, visible focus and adequate touch hit areas, including 44px targets around compact 40px visual buttons. Respect reduced motion and shell locale/theme settings. Source/type distinctions must not depend on color. Remaining dark/Chinese/intermediate parity and complete interaction states are still design work.

## 9. Meaningful proof before production acceptance

First implement the typed projection and case identity in incumbent owners, then mount the consumer through Terminal's admitted shared-shell route while preserving special_situations.html compatibility. Preserve builder thin-store protection and actual evidence clocks on no-refresh renders; do not make a pure render collect data.

Verification must exercise real authorized producer → typed response → shared-shell consumer → exact source → return. Include two agreements for one issuer, one terminal event, an ownership-only 13D/A amendment, overlapping reporting persons, ambiguous name resolution, source failure with retained records, missing predecessor, corrected term, pence/pounds mismatch, unsupported mixed consideration, quote-time mismatch and month-only guidance. Confirm paid evidence stays behind incumbent authorization and safe navigation survives reauthentication.

Fixtures prove arithmetic and semantic distinctions, not real coverage or saved effects. Later production evidence must identify deployed revision, source snapshots, receipts, actual route and real browser journey. Passing CI, static Paper buttons and a draft PR are not production acceptance.

## 10. Review and evidence

A bounded read-only reasoning review accepted arithmetic, source-stage distinctions and case isolation; it required fee payer/recipient/trigger in expanded detail. A bounded visual review accepted the final international, calculation and amendment screens after completion status, ratio denominator and spacing refinements. Principal inspected activist, mobile, state and Build compositions. All seven roots received observed guarded finish receipts on the sole qualified M1 Paper carrier.

The [SEC beneficial-ownership interpretations](https://www.sec.gov/rules-regulations/staff-guidance/corporation-finance-interpretations/exchange-act-sections-13d-13g-regulation-13d-g-beneficial-ownership-reporting), retrieved 14 November 2026 and labeled last updated 2 September 2026, support treating amendments as changes requiring substantive inspection rather than automatic campaign escalation. These primary references inform semantics; they do not authenticate fictional case facts.

Exact page identities and final screenshot SHA-256 digests are in [the inventory](PAPER_INVENTORY_2026-11-14.json). Build/state boards are internal references, not customer destinations. No product code, collector execution, alert enrollment, trade, merge, deployment or external message occurred in this phase.
