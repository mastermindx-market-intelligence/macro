# Alternative Data R2 — relationships, coverage and research contract

Status: DESIGN CANDIDATE / IMPLEMENTATION NOT STARTED  
Date: 14 November 2026  
Parent: [Research Explore migration record](../RESEARCH_EXPLORE_SHARED_SHELL_2026-11-14.md)  
Shared architecture: [Engine blueprint](ENGINE_AND_IMPLEMENTATION_BLUEPRINT_2026-11-14.md)  
Paper identities: [Design index](PAPER_DESIGN_INDEX_2026-11-14.md) and [exact inventory](PAPER_INVENTORY_2026-11-14.json)

## 1. User outcome and design scope

A researcher can inspect a company's records, determine which records share one primary origin, read the precise relationship supported by that origin, understand whether a channel has usable coverage, and inspect the research status of a specific cohort. Every source visit returns to the same company, filters, selection and scroll position.

R2 adds six editable pages in Paper file 01M2VWK62FA5S4VVF6G7SBPE5J:

| Page | Root | Purpose |
|---|---|---|
| p-P-1 | AJA-1 | Desktop relationships and exact filing evidence |
| p-Q-1 | APO-1 | Sources and selected-provider coverage inspector |
| p-R-1 | AWC-1 | Dark research status, sample units and earlier evaluations |
| p-S-1 | B7S-1 | Unresolved association at 1024px with the shared collapsed rail |
| p-T-1 | BAO-1 | Mobile filing evidence, lineage and return |
| p-U-1 | BC6-1 | Advanced engine Build board |

These extend the existing Companies, Evidence and mobile views. Figures, records, names and dates in the compositions are synthetic fixtures. Native screenshots establish visual composition only. The controls are designed states, not proof of working requests, navigation or persistence.

## 2. Existing ownership and material source gaps

All source references bind to Macro commit e856ef0200a0c508c78ef9a6666116020e4835d1; implementation uses Terminal's incumbent AppShell and domain owners. Do not introduce a second shell, data collector, snapshot ledger, queue, identity service or evaluation authority.

| Source | Observed behavior | Required consequence |
|---|---|---|
| [engine/altdata_signals.py](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/engine/altdata_signals.py), blob dae7b2db43a0552e8871808f935fc7fd4e280081 | Event-cluster taxonomy groups channel names; unknown channels receive their own cluster | Co-firing is a dependence heuristic. It does not prove record-level independence or independent confirmations |
| [engine/altdata.py](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/engine/altdata.py), blob 6bb05b69e97370652502629fb66314964f79bd84 | build_feed and _safe collapse missing, empty and failed data into empty/default outputs | Current feed alone cannot support confident provider-health or valid-empty states |
| [engine/influence/graph.py](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/engine/influence/graph.py), blob 1907855f7f0a7e5d33588a4a36b6f0fce6a431d3 | Seed logic can synthesize CONTROLS from executive/family ticker affiliation with FACT/confidence labels | Imported labels and confidence cannot establish documentary ownership or control |
| [engine/altdata_brain.py](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/engine/altdata_brain.py), blob a1d0c7f971a4b915623e709497aa0ca06685a82d | Source-owned Article 3 verdict evaluates altdata at horizon 5 from the qledger track record; uses independent n_dates, min_n 25 and min_events 8 | Consume the exact verdict and scope. Count rows and independent dates separately; sample size alone does not grant a positive verdict |

Existing by_ticker.v2 and mastermind.v1 publications remain owners. Add bounded projections and provenance fields to these owners where needed. A new consumer endpoint is permissible only as a projection of an incumbent owner, with no parallel collection lifecycle.

## 3. Record lineage and exact relationship evidence

The minimum consumer envelope carries canonical company/entity ID, source record ID, event-group ID, primary-origin ID, source kind, source URL, precise relationship type, source reference, source/publication date, first-observed time, available effective interval, version and correction predecessor. Absence is explicit; generated time never substitutes for a source clock.

One SEC filing and two provider copies are three records with one primary filing. Preserve all useful records, but group derivations under their origin and explain the grouping on demand. Similar wording or simultaneous channels is not evidence of independence. If origin cannot be established, show lineage unknown rather than manufacture a grouping or confirmation count.

The selected officer specimen states only the officer relationship disclosed by its filing. Role effective date remains unknown when the filing does not establish it. Officer status implies neither ownership nor control. Patent assignee evidence remains a distinct documentary relationship; preserve the existing patent-family deduplication contract.

An imported association without primary support remains unresolved. It can be inspected and traced to its imported record, but cannot be promoted by a confidence number or FACT label. Relationship type, ownership/control and effective dates remain separately unknown. Avoid a force graph on initial load: a short relationship list and exact evidence panel answer the immediate question with less interpretation.

Corrections retain predecessor evidence and observation time. The latest corrected edge does not rewrite what the user could have known at an earlier cut. Canonical entity identity must survive name changes; conflicts between two candidate identities remain unresolved until the incumbent identity owner establishes a resolution.

## 4. Provider and coverage state

Extend the existing collector receipt and producer projection with latest attempt, latest successful valid check, latest available record, expected cadence when known, provider access state, collection state, schema state, selection scope and source cut. Distinguish app entitlement from external-provider access. Never infer either from an empty array.

| State | Required proof | User treatment |
|---|---|---|
| Current | Successful valid receipt within the source's defined freshness rule | Show latest check and original record clock |
| No matching records | Successful valid check for the exact company/window and supported query scope | Show the bounded empty result without implying universal absence |
| Delayed or partial | Explicit missed cadence or partial source receipt | Keep available records with their original clocks and state |
| Provider access unavailable | Explicit provider authorization/access result | Explain inability to retrieve new records; allow valid prior records if entitlement permits |
| Collection or schema error | Typed failed receipt | Expose a scoped reason and read retry; preserve last good data |
| Status unknown | No usable state receipt | Say status is unavailable; do not claim no activity or failed provider access |
| App access restricted | Existing session/entitlement policy | Use the shared shell's access path without exposing protected cached records |

Sources displays one selected channel's inspector. Unknown-state details appear only when that row is selected. “Coverage scope” holds definitions and advanced diagnostics; technical detail is collapsed. The removed always-visible empty-result definition belongs there.

“Check status” refreshes the authorized read projection. It does not start a collector, change credentials, enroll a watch or repair a provider account. Last success and latest attempt remain distinct after a failed refresh. Source cards from different cuts must not be silently mixed into a new coherent status.

## 5. Research evidence and evaluation binding

Read is_context_only and the source-owned article3 verdict dynamically, including granted, reason, lift bound when present, evidence_asof and evaluated_at. Target A1_EXPLAIN is explanatory authority and is not trade authorization. No new universal Alternative Data score or UI-created gate is allowed.

Bind every result to family, evaluator/version, exact horizon and its unit, benchmark, cohort window, evidence vintage and price/evidence cutoff. The Paper fixture uses five trading days; the production horizon basis must be established from the upstream qledger contract and carried explicitly rather than inferred from the integer 5.

The fixture shows 38 signal records and 12 independent outcome dates. These are different units. The minimum sample is 25 independent dates; reaching that floor alone does not satisfy every gate condition. Do not present the sample floor as if evaluation had not run. The visible context-only reason must match the source verdict.

Earlier adjudication remains separate: the [13 August first-cohort report](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/research/ALTDATA_CONVERGENCE_FIRST_COHORT_ADJUDICATION_2026-08-13.md), blob e4b6537278f88a8fef447f4ae83a86326c0d8710, records a historical HOLD with adverse, non-decision-grade evidence and different vintage/clock issues. Do not hardcode that historical HOLD as today's verdict or pool its population into a new cohort.

“Other horizons → 20 trading days” is navigation to a separately bound selection. It shows no active five-day verdict or unsupported zero-outcome claim. A supported zero denominator displays “No eligible outcomes” and no success rate; missing evaluation, failed computation, pending maturity and negative outcomes are different states.

Evaluation time is not evidence time. Preserve both. Evidence availability and a readable historical report do not establish validated forecasting or sizing authority.

## 6. Interaction and responsive contract

Persist navigation state through the shared router: company, date range, active task, selected relationship/source/cohort, evaluator/horizon/version and return anchor. A tab change preserves compatible company/window context; changing scope invalidates incompatible selections visibly. Source links open the source owner with the exact record and a recoverable return.

The 1024px state uses the existing 72px collapsed rail and a 328px relationship list. At 390px, the list becomes a separate step; source evidence is the primary reading surface and a direct return restores the selected company. No horizontally clipped desktop table is compressed into mobile.

Keyboard order follows visible reading order. Rows have accessible names and selected state; Escape dismisses an inspector or disclosure; focus returns to its opener. Dialog focus trapping, 44px touch targets, reduced motion and keyboard source return require implementation proof. Do not treat vector icons or static Paper controls as accessibility acceptance.

## 7. Build sequence and acceptance

1. Extend original producer contracts for lineage, precise edges, coverage receipts and evaluation identity. Preserve compatibility or provide a versioned adapter on the same owner.
2. Expose typed availability and per-selection coverage; reject ambiguous empty/default states as proof of provider health.
3. Implement shared-shell routes, source inspectors, disclosure controls and exact navigation restoration.
4. Prove representative real data paths: primary/derived filing, patent family, unsupported association, correction, access failure with prior records, valid empty selection, unknown health, context-only cohort, separate historical vintage and different-horizon selection.
5. Prove failure transitions: stale source/cut, provider/schema failure, entitlement change, zero denominator, missing evaluation and restored Back/Forward state.
6. Verify actual 390/1024/1440 layouts, light/dark, keyboard/touch and EN/ZH against the accepted design. Finish the remaining family/cross-product design units before product implementation begins.

Acceptance requires truthful producer receipts, authenticated consumer behavior, source links and restored state on the real application path, followed by deployment proof through existing release gates. Screenshots, mocked JSON, green unit checks or a source PR alone do not complete the migration.
