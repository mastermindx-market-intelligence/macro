# Policy Watch R6 — shared-shell design and build contract

Status: DESIGN CANDIDATE. Paper frames and these contracts do not establish implementation, validated intelligence, production availability or release approval.

Assignment: Chairman / ChatGPT4, 14 November 2026. Parent packet: [Research Explore migration](../RESEARCH_EXPLORE_SHARED_SHELL_2026-11-14.md). Existing designs remain intact; this revision uses new, exclusively owned R6 pages in the current Policy file.

## 1. Product job and decisions

The first screen must answer: what source changed, what stage the policy is actually in, and what the reader should inspect next. A broad thesis or prediction must not stand in for a source change. A proposal is not an effective rule; a communication is not a rate decision; a price reaction is not proof of transmission.

The design uses Terminal's existing 224px/72px rail and 64px top bar. The product contributes a content region and local task navigation. It does not create another global navigation, identity, watchlist, alert runner, source store or calendar.

Visible text has a specific job. Page introductions, persistent training text, repeated methodology badges, speculative conviction scores and decorative banners are omitted. Explain an unfamiliar concept in a disclosure or at the relevant decision point. Keep build instructions outside customer-facing frames.

### Paper revision map

File: [Macro and Policy Watch](https://app.paper.design/file/01M6Y2X53ABR4MME4ATS15B8SH/p-5-1).

| Frame | Page | Node | Purpose |
|---|---|---|---|
| Now, desktop light | p-5-1 | 1YI-1 | One material source change, next decisions, changed records and research entry points |
| Change dossier | p-8-1 | 270-1 | Aligned document versions, legal lifecycle and separately qualified transmission |
| Central banks, desktop dark | p-6-1 | 274-1 | Actual target range and dated market-implied pricing shown as distinct measures |
| Now, mobile 390 | p-7-1 | 272-1 | Single-column reading and full-page dossier entry |
| State contact sheet | p-9-1 | 2PR-1 | No changes, delayed source, unavailable comparison, correction, follow conditions and research navigation |
| Build contract | p-A-1 | 2SM-1 | Product, owners, evidence clocks, interaction contract and production proof |

All companies, policy notices, quotations, dates, rate paths and values in the new frames are **synthetic design fixtures**. They are not current market claims. Fixture identity is recorded in frame/build metadata rather than repeated as a product banner. Production must replace the fixture projection with provenance-bound owner data.

The earlier R5 page p-2-0 remains reference for Pipeline, Market Memory, Calls and their additional states. Those flows still need the complete R6 treatment and route-level proof before the Policy design set can be called complete. This is not permission to erase their capabilities.

## 2. Information architecture and discoverability

| Destination | Main task | Preserved deeper capabilities |
|---|---|---|
| Now | Read changes since an explicit review baseline | Official source freshness, legal stage, UK realpolitik and dated analysis |
| Policy pipeline | Inspect policy stages and next decisions | Jurisdiction, theme, date, lifecycle, withdrawn/superseded/corrected/reinstated records |
| Central banks | Compare the decision, statement and market pricing | Statement versions, pricing snapshot, next meeting, funding and FX transmission |
| Market memory | Compare episodes under explicit matching conditions | Regime, event window, asset proxy, price basis, sources and unmatched evidence |
| Research | Continue a specific investigation | Global coverage; People & relationships; Company exposure; Calls & results |

Research opens a named secondary menu; it is not a miscellaneous bucket. Every preserved capability retains a direct URL. Entry from a legacy policy URL must resolve through the admitted shared-shell route while retaining meaningful query state and return context.

A canonical route-catalog decision is required before introducing a native path. Suggested URLs in implementation discussions are proposals until admitted; do not maintain a second hand-written route registry. The source route policy_watch.html remains the compatibility contract.

## 3. Interaction contract

| Starting point | Action and resulting state | Persistence and accessibility |
|---|---|---|
| Now lead or change queue | Open selected policy dossier | Preserve filter set, sort, review baseline, selection and scroll; Back restores them |
| Dossier | Previous/next change | Operate within the same bounded result set; announce changed title; no silent filter reset |
| Dossier comparison | Select source versions | Bind exact immutable versions and dates; scroll aligned passages; source links remain available |
| Comparison unavailable | Read the available current document | Do not substitute a model summary for missing official text |
| Transmission | Inspect each relationship | Fact, interpretation, inference and unresolved mapping remain individually inspectable |
| Company exposure | Open canonical company analysis | Carry issuer identity and return context, not a cloned company page |
| Follow policy | Choose concrete changes and confirm | Use canonical Alerts settings and capabilities; show the actual saved/delivery state |
| Source correction | Compare old and corrected fact | Preserve earlier interpretation and show what became stale; never rewrite history silently |
| Mobile queue | Open full-page dossier | Back returns to selected item and original scroll; no cramped desktop inspector |
| Refresh | Reconcile owner snapshot | Keep selection if still valid; explain removed/withdrawn record; never jump to first row |

A review baseline is an explicit saved version/time with a well-defined scope. If the implementation has no account-backed baseline yet, expose a supported time filter instead of claiming a personalized last review. Do not infer review completion merely from page load.

Desktop keyboard behavior: Tab reaches visible controls in reading order; Enter opens the selected item; Escape closes a transient drawer and returns focus to its trigger; arrow navigation within a queue is documented and does not hijack text fields. Selection and status never depend on color alone.

Animation is limited to short spatial transitions, selection movement and a clear loading state. Respect reduced-motion settings. Do not pulse "live" status.

## 4. Existing owners and reuse

The following are inspected source owners, not new modules to duplicate:

| Owner at Macro pin | Existing responsibility | R6 change boundary |
|---|---|---|
| engine/policy_watch_current.py | Current calendar, headlines, statement and comparison projection; policy_watch_current.v1 | Extend a typed projection only where the design needs missing evidence/state fields |
| engine/policy_intent_desk.py | Deterministic policy lifecycle fold; policy_lifecycle.v1 | Preserve legal-stage semantics, corrections, supersession and reinstatement |
| engine/transmission_chains.py | Transmission relationships | Add inspectable relationship evidence/qualification rather than a new inference engine |
| scripts/build_policy_watch.py | Page/build integration | Retain publication owner and truthful data timestamps during staged migration |
| data/policy/intel.json and lifecycle events | Current evidence/event inputs | No synthetic fixture leakage, duplicate collector or replacement event ledger |
| Terminal AppShell and sharedShell runtime/presentation | Shared chrome, navigation, account, history, theme and language | Mount page content through existing shell admission and contracts |

The shared-shell migration must not fork these owners. A Terminal adapter may translate an existing owner response into a typed view model. It must not silently recalculate policy truth or introduce a competing source of lifecycle status.

## 5. Proposed view-model additions

This section is a **proposed projection contract**, not a claim that new endpoints or fields already exist.

Each response should identify schema version, canonical policy ID, source snapshot/content identity, coverage scope, data-as-of, retrieval status and the echoed request. A list cursor must be bound to its filter and snapshot, so switching jurisdiction cannot append rows from the previous request.

Each source document needs a stable version identity, original source URL, publication time, first observation time, retrieval outcome and exact text availability. A comparison binds two such identities plus the document section/anchor. If the source lacks a time zone or precise date, preserve the uncertainty.

Each lifecycle transition needs the source-backed legal state, effective or scheduled date precision, observation time, predecessor/correction relationship and source refs. Proposed → passed → in force → enforced is not a universal compulsory path: jurisdiction-specific stages and withdrawn, struck-down, superseded, corrected or reinstated conditions must be representable.

Each interpretation needs its own analysis date and the source versions on which it depends. A fresh headline or build must not refresh an old interpretation. A transmission relationship carries its own evidence status and source refs, including explicit unresolved links.

Exposure records reuse canonical issuer identity, product/category evidence and reported segment/geography inputs. A relationship to a policy topic alone cannot become quantified revenue risk. Display unavailable exposure where the chain is not supported.

A view can report current evidence alongside an older analysis only if their clocks are visibly separable. The normal first screen has one relevant source-as-of line; exceptions appear beside the stale or delayed module. Detailed timing belongs in Sources, not repeated across every row.

### Central-bank chart contract

Observed policy is a target range or a single target according to the jurisdiction. The fixture chart represents a target range as a band bounded by two step paths. Market-implied rates are a separately dated series with their instrument/calculation basis available in a disclosure. Their shape cannot be labeled a decision, official path or forecast probability.

The displayed 3.47% fixture must land at 3.47 on the plotted scale. Future meeting dates, time zones, missing curve points and curve coverage must be carried in the data contract. Do not interpolate an unavailable meeting silently. A bank with a different rate convention needs an explicit compatible view, not fabricated range bounds.

## 6. Availability and correction behavior

| Condition | Visible answer | Allowed continuation |
|---|---|---|
| No changes with valid coverage | No new changes since the selected baseline | Open full history or change period |
| Empty filter result | No matching records for these filters | Clear/filter controls; retain coverage context |
| Delayed source with valid previous evidence | Last confirmed document and its actual time | Read the source; bounded refresh; unaffected sources remain usable |
| Newest data invalid | Last valid version, explicitly dated | Diagnose owner validation; do not replace it with zero rows |
| Prior comparison version absent | Comparison unavailable | Current source document remains readable |
| Proposal withdrawn or superseded | Current stage and predecessor relationship | Read the change history; remove no history |
| Effective date corrected | Corrected fact plus previous fact | Review affected saved interpretation |
| Source coverage partial | Covered jurisdictions/topics identified | Missing coverage cannot imply "nothing happened" |
| Follow save failed | Unsaved state with existing user input retained | Retry only after reconciled state; no fake success |
| Alerts capability unavailable | Read-only research still usable | Explain the specific capability at the follow action |
| Expired authorization | Reauthenticate through existing account flow | Preserve safe navigation state; do not expose paid evidence |

## 7. Design system and responsive behavior

Use the existing semantic palette and Inter scale. Desktop: 28px page title, 17px section heading, 14px body and 12.5px secondary text. Do not solve fit problems by shrinking substantive text. Neutral borders and selected fills carry structure; blue denotes an action or series. No colored container rails or ornamental tier badges.

Use the available content width after the shell rail. At narrow widths, collapse the shell through its existing behavior and use a single content column. The dossier comparison may switch to an accessible version toggle/stacked aligned passages; it must not require horizontal scrolling to read sentences.

Verify at 1440 with expanded and collapsed rail, 820/768, 390 and 320. The 390 frame is an authored mobile direction, not proof that every breakpoint already passes. Provide dark/light parity and EN/Chinese expansion before design acceptance. Touch controls need adequate targets even where desktop text is compact.

The state contact sheet and build page are internal design resources. They must never be mounted in the customer route.

## 8. Implementation sequence

1. Rebind current protected source, Terminal admission, actual route catalog and active holds. Confirm no live writer owns overlapping implementation paths.
2. Add typed owner-to-view projection with fixture and real-record parity; preserve existing owner outputs and chronology.
3. Implement the page content in the current shared shell. Keep old destinations and return URLs working until parity is proven.
4. Implement source comparison, queue restoration and the complete mobile reading path.
5. Connect supported follow conditions to the canonical Alerts owner with truthful persistence/delivery receipts.
6. Upgrade missing lifecycle, versioning or exposure evidence in the existing engine, with explicit schema compatibility and replay checks.
7. Complete Pipeline, Market Memory and Research R6 visual states, bilingual/narrow-screen behavior and their source-bound implementations.
8. Use permitted native PR delivery and actual required protections. A merge, deploy and user-path acceptance remain separate receipts.

The current turn is design-first. No product release, production data mutation or alert enrollment is authorized merely by creating these design fixtures.

## 9. Acceptance and meaningful verification

Design acceptance requires a coherent end-to-end journey, all retained capabilities discoverable, populated and degraded states, viewport/language/theme coverage, documented backend gaps, and visual inspection of the final owned nodes.

Implementation acceptance requires representative real source records, actual source versions opened from the UI, legal-stage correction replay, no future-information leakage, missing-source behavior, entitlement checks, account-owned follow persistence, route return restoration and production/browser proof. Use meaningful fixtures that distinguish old and corrected versions and different time bases. Do not add superficial tests that only mirror a component's markup.

Production evidence must identify deployed version, real route, relevant data versions, source receipts and remaining constraints. CI passing is supporting evidence only.

## 10. Pinned references

- Mastermind source law: 199fd4f91ecc426b1d974eb3bf47f5162476cf24.
- Macro: e856ef0200a0c508c78ef9a6666116020e4835d1.
- Terminal: fe49f3b5765dd4e10721928716a6a730e78c7ae1.
- [Macro design doctrine](https://github.com/mastermindx-market-intelligence/Macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/docs/DESIGN_DOCTRINE.md)
- [Master product design system](https://github.com/mastermindx-market-intelligence/Macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md)
- [Shared-shell migration plan](https://github.com/mastermindx-market-intelligence/Macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/research/MASTER_PRODUCT_SHELL_MAKEOVER_MIGRATION_2026-10-08.md)
- [Current Policy implementation](https://github.com/mastermindx-market-intelligence/Macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/research/POLICY_WATCH_CURRENT_R1_IMPLEMENTATION_2026-09-08.md)
- [Current projection](https://github.com/mastermindx-market-intelligence/Macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/engine/policy_watch_current.py)
- [Lifecycle owner](https://github.com/mastermindx-market-intelligence/Macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/engine/policy_intent_desk.py)
- [Shared shell geometry](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/fe49f3b5765dd4e10721928716a6a730e78c7ae1/terminal/components/chrome/shared-shell/shared-shell.css)
