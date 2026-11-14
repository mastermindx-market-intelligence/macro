# Capital Structure R2 — conflict, historical restore and save recovery

Status: native Paper design and implementation contract. Product implementation and production acceptance have not started in this phase. All displayed companies, quantities, records and save attempts are synthetic design fixtures.

This extends the accepted Capital Today / On a date / Scenario designs. It preserves the frozen U0 journey, exact labels and historical implementation holds. It does not introduce a second solver, scenario store, evidence authority, authentication owner or shared shell.

## 1. Design identity and intended decisions

| View | Native Paper page | Final root | User decision |
|---|---|---|---|
| Sources disagree | [Conflict](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-2Q-1) | 2OLI-1 | Inspect comparable source observations without choosing an unsupported share count |
| Historical inputs unavailable | [Saved historical record](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-2R-1) | 2OR4-1 | Keep the original cutoff and assumptions, then explicitly choose whether to inspect current facts |
| Save not confirmed | [Save recovery](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-2S-1) | 2PLN-1 | Reconcile persistence without blindly repeating a possibly completed save |
| New request loading, 768px | [Request transition](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-2T-1) | 2P29-1 | Understand the requested issuer/date while its result is pending |
| Historical restore, Chinese mobile | [历史情景恢复](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-2U-1) | 2P4N-1 | Read the same refusal and saved assumptions at 390px |
| Save, attribution and access states | [States](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-2V-1) | 2P6K-1 | Distinguish found records, future version conflict, unclassified change and unavailable access |
| Build contract | [Build](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-2W-1) | 2P8Z-1 | Bind the designs to existing owners and explicit missing capabilities |

Five product compositions, one state sheet and one Build sheet are added. The final screenshot identities and digests are in [PAPER_INVENTORY_2026-11-14.json](PAPER_INVENTORY_2026-11-14.json). The shared shell remains Terminal AppShell; the full, collapsed and mobile shells are compositions of that experience, not separate application owners.

## 2. Source binding and preserved law

Product baseline: macro@e856ef0200a0c508c78ef9a6666116020e4835d1. Terminal baseline: mastermind-terminal@fe49f3b5765dd4e10721928716a6a730e78c7ae1. Protected procedure remains Mastermind@199fd4f91ecc426b1d974eb3bf47f5162476cf24.

| Inspected source at the Macro baseline | Blob | Binding contribution |
|---|---|---|
| [U0_JOURNEY_FREEZE.md](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/research/capital_structure/e2e_20261013/U0_JOURNEY_FREEZE.md) | 38e9c14b2b39a0f79795afcd504bfdc6cbd0e4bb | Frozen modes, copy, request identity, history/focus and release holds |
| [issuer_state_contracts.py](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/engine/capital_structure/issuer_state_contracts.py) | 6de4edc5b173002a13418dc12ab822afe8430586 | Quantity states and share-basis conflict semantics |
| [state_bundle.py](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/engine/capital_structure/state_bundle.py) | 386b913877a64aeacdbe028a19c03658ae3e3303 | Currently unavailable share-basis producer |
| [scenario_inputs.py](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/engine/capital_structure/scenario_inputs.py) | 94ca6da0f83349230a07510c99e8a1a5c45cdafd | Five-family generation/as-of binding and typed refusal |
| [saved_scenarios.py](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/engine/capital_structure/saved_scenarios.py) | fa9b9291674cb678805d9daeb3848a28d952df29 | Saved metadata, restore anchor and outcome classification |
| [saved_scenario_store.py](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/engine/capital_structure/saved_scenario_store.py) | 41946eab2ec9e5f7e9abdcdb26b423da5c866c95 | Current merge-duplicates upsert and store failures |
| [app/capital_structure.py](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/app/capital_structure.py) | 67ea69cc96a9af7633546e614f0ee8dc9eac4ebb | Auth, date normalization, save/restore and evidence routes |
| [templates/capital_structure.js](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/templates/capital_structure.js) | 18f793b774002108e9d736e29a248ac46ca964cd | Existing request token and pagination behavior |

Saved-scenario tests were inspected, not executed: test_capital_structure_saved_scenario_api.py blob f2ae018817ee0d9d3356431322d6a2f0ede63b32 and test_capital_structure_saved_scenarios.py blob 8c1c42c8349f3e30334c58e0072dbdbadab3f606, under tests/ at the same pin.

Historical W3/W4 and #8673 holds remain preserved. Their current release status was not requalified. This packet neither lifts a hold nor changes a frozen choice; any later U0 change follows its existing decision process.

## 3. Visual hierarchy and mode fidelity

Facts use solid panels. Historical views add a visible cutoff stamp and rule. User assumptions use dashed outlines and dashed underlines, with no glow or simulation theatrics. A scenario result retains the exact line **Facts unchanged · assumptions are yours**, or **事实未变 · 假设由您设定**. The fixed labels **Potential new shares** and **Cash to the company, after fees** remain intact.

The dominant constraint precedes dependent numbers. Source history, comparison basis, original anchor and save-attempt detail are progressive disclosures opened for a concrete investigation. No capacity hero, score, prediction, trade instruction or time scrubber is introduced.

Review moved the unresolved feasibility condition into the calculation panel, before its figures. Its Review conditions action stays beside it. The separate footer was removed. Conflict navigation follows its panel by standard spacing, and historical/mobile assumptions sit directly after the refusal. Chinese values retain units and equivalent meaning rather than mechanically copying English widths.

## 4. Comparable-source conflict

RIVT has two Class A common-share observations, both on an issued-and-outstanding basis and effective 31 October 2026: 95.0 million and 98.0 million. The documents become available on 13 November at 16:10 and 16:18 UTC. Today may show their disagreement; neither observation belongs in a 31 October then-known answer.

A conflict requires the same issuer/security, basis, effective date and corporate-action normalization. Different share classes, denominators or dates are different observations until the owner establishes comparability. ShareBasisResult(conflict) retains at least two candidates and conflict evidence, with selected=None. A contradicted Quantity carries no number. Unknown, withheld, unavailable and not-applicable values likewise cannot become zero.

The interface offers exact passages and comparison basis, with no Use value control or automatic preferred source. Common-share headroom and new-share capacity remain unresolved. The separate registration fixture is USD 120m registered less USD 52m utilized, yielding USD 68m in the same scope. Dollars are not shares, route maxima are not additive, and registered room does not prove issuability.

The pinned producer explicitly publishes share basis as unavailable and has no admitted share-count records. Rendering populated conflicts therefore requires a real producer projection in state_bundle and its incumbent inputs. Existing dataclasses do not establish source coverage. Issued-and-outstanding shares alone also do not settle authorization headroom; class rules, treasury treatment and reservations remain relevant.

## 5. Historical restore with missing inputs

The saved Q4 financing review retains a 31 October 2026 New York end-of-day cutoff and system-availability clock. The saved timestamp, 4 November at 14:25 UTC, is a different fact.

Preserve incumbent _normalize_instant precision: the date becomes **2026-10-31T23:59:59-04:00**, or **2026-11-01T03:59:59Z**. A Saturday calendar cutoff does not silently become Friday market close or a new exclusive-midnight convention.

In this explicit fixture, the available input bundle has as_of=14 November, while the requested historical cutoff is 31 October. The mismatch prevents instruments, share basis, financials, commitments and rules from binding. A later serving date alone would not prove this failure: inspect actual as-of, generation and refusal identity.

Retain saved assumptions and their units; withhold the original numerical result when its body is unavailable. Review current record is explicit navigation to current facts, with a new request identity. It does not relabel a current calculation as the historical result.

The current SavedScenario record stores user/issuer, view/cutoff, assumptions, generations, result identity/digests, rulepack digest, saved time and contract version. It does not store the full result body. Current/scenario restore evaluates saved assumptions at the served as-of; then-known restore retains its cutoff. The response separates saved metadata from a current result. The earlier R1 immutable-version composition is a target requiring retained-result/version support, not proof of an existing guarantee.

## 6. Calculation and persistence are separate outcomes

The fixture assumes 160m authorized common shares, USD 4 per share, USD 60m gross proceeds and fees equal to 2% of gross. Arithmetic yields 15m potential new shares, USD 1.2m modeled fees and USD 58.8m cash after those fees. Other expenses are not represented. The server remains calculation authority; these examples are not a client solver or evidence of feasibility.

The feasibility condition stays unresolved beside the calculation. An unresolved common-share basis cannot become a confident dilution, headroom or funding-capacity result through assumptions.

A timed-out save says **Save not confirmed**, not Save failed or Unsaved. Preserve the current draft using an already approved state owner. Check saved scenarios performs a same-user read before any repeat mutation. A saved copy found proves that a matching record exists; it does not by itself confirm which operation wrote it.

Reconciliation compares issuer/security, scenario/view, assumptions and units, generation bindings and result identity/digest. Labels are not identity. An empty filtered page, incomplete pagination or eventual-consistency read is not proof that nothing was saved. If the owner cannot establish an outcome, retain uncertainty and the draft; do not create a local queue, alternate store or blind retry loop.

At the inspected pin, saved_id excludes label and result/generation identity, and the store upserts with merge-duplicates. A repeated key can overwrite its record. Immutable numbered versions, compare-and-swap/ETags and operation receipts are not established. The version-conflict state sheet is explicitly a future owner extension. It must not ship as a claimed current API.

The save API evaluates the posted anchor again before persisting; it does not automatically rebase that anchor. A moved served as-of can therefore refuse the save. If generations change while the posted anchor remains valid, the evaluated result may differ from the preview. Bind saved metadata to the generations and result identity from that single evaluation, without a second generation read. Inspect save attempt can expose a client request’s identity and known transport outcome, but cannot fabricate a server receipt. Public saved-record responses omit user identity.

## 7. Typed restore and access outcomes

A successful HTTP transport does not imply a usable calculation. A restore HTTP 200 can carry an unusable typed outcome.

| Outcome or condition | Consumer behavior |
|---|---|
| no_change | Show the corresponding verified result identity and its anchor |
| correction | Explain only the correction established by spanning evidence |
| new_events | Attribute only verified intervening events |
| source_outage | Preserve saved metadata/assumptions and name source unavailability |
| inputs_unavailable | Name affected families; preserve cutoff; withhold numerical result |
| scenario_rejected | Retain draft assumptions and present the typed invalid condition |
| changed_unattributed | State that a change cannot be classified; do not invent issuance or correction |
| saved_scenario_identity_drift | Suppress the numerical result and surface the typed 503 recovery path |
| absent or foreign private record | Same neutral unavailable 404 after authentication/authorization |
| public clock not separately modeled | Keep that limitation explicit; do not substitute system history under a public label |

The refusal mapper distinguishes source outage, missing families, as-of mismatch and rejected scenario. Identity drift with the same generations is not a routine revision. Shared caches and logs must not leak a private saved record through labels, identifiers or existence differences.

## 8. Request, navigation and evidence contract

The calculation key remains (issuer_id, mode, cutoff, clock, scenario_id). Every result, error, disclosure and paginated response must match it. On issuer/mode/date changes, clear old numerical content from the new context immediately; a late RIVT result must never appear under ALTA.

The 768px composition keeps ALTA, On a date, the requested cutoff and clock visible while loading. Cancel request aborts that read and leaves a clear canceled/no-result state for the requested identity. It does not silently restore an earlier issuer’s result beneath the new heading.

Opening a source or constraint inspector changes focus through replaceState only. Issuer, mode, cutoff or scenario changes create history entries. Back, Forward, Escape and close restore selection, scroll and focus without a new calculation when only focus changed. Nested actions must not also activate their parent row. Loading/status announcements should be concise and announced once; keyboard focus remains visible.

The existing issuer loader has a request token; inspected loadMoreEvents lacks the same guard. Treat this as a static risk to verify, not a reproduced production incident. Guard every paginated request and invalidate it on calculation-key change.

Current evidence endpoints accept issuer/manifest/span and echo current/system context. They do not accept the full historical/scenario identity. Extend that incumbent evidence owner before promising exact mode-bound evidence. Validate the permitted source locator and binding; never fetch an arbitrary URL or loosen authorization to fill a drawer.

## 9. Build sequence and acceptance

First reconcile existing held carriers and release conditions. Then extend admitted share inputs, historical input retention and typed evidence binding within incumbent owners. Decide and implement retained-result/version/CAS/operation-receipt capabilities before exposing R1 version controls as working features. Preserve existing restore semantics until an authorized contract change is explicit.

Frontend integration follows design-phase closure through Terminal AppShell. Reuse its auth, route/history, theme, locale, search and context owners. Model transient calculation status separately from save status. Keep backend diagnostics in inspectors/Build notes, with plain useful product copy.

Meaningful proof must cover real admitted source observations; conflict comparability; unit-safe constraints; all five historical family bindings; exact cutoff conversion; post-cutoff observations; unavailable original result; every restore outcome; authenticated own/foreign/absent records; save timeout followed by original-target reconciliation; source changes between preview and save; full request and pagination races; inspector Back/Forward/focus return; and accessible narrow/theme/locale layouts.

Read source tests are evidence of existing expectations, not executed validation. Paper screenshots prove composition and copy, not interactive controls, network effects, source coverage or deployed bytes. Existing historical holds, full cross-product parity, frontend/backend work and real browser acceptance remain open.

## 10. Review and preservation

Principal and bounded reasoning reviewers checked source meanings, date precision, fixture arithmetic and visual hierarchy. Final QA repaired detached navigation, excessive card gaps, the calculation’s distant feasibility condition and Build wording. Final page/root identities, screenshots and finish receipts are recorded in the cumulative inventory.

All original Capital compositions and foreign/held Paper scopes are preserved. The owned save-recovery root was replaced once for the reviewed layout and reconciled to 2PLN-1. No product code, collector, account save, message, watch enrollment, trade, merge or deployment was performed.
