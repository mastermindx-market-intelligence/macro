# BioCatalyst R11 — Trial discovery and prospective observation

Status: DESIGN CANDIDATE; product implementation and production proof are not started.  
Date: 14 November 2026. Parent: [Research Explore migration](../RESEARCH_EXPLORE_SHARED_SHELL_2026-11-14.md).  
This addendum preserves R10 Milestones, Changes and explicit Peer matrix. All NCT9000000x records and values in Paper are synthetic fixtures.

## 1. Outcome and authored surfaces

A researcher can narrow the configured observed trial set using literal registry facts, inspect a source record, explicitly choose trials for comparison, and investigate a newly observed difference without confusing observation time with effective time or clinical outcome.

| View | Paper page | Root | Purpose |
|---|---|---|---|
| Trial screen | [R11 Trial screen](https://app.paper.design/file/01M6Y34XE4JKS3A40GMMZ954JE/p-A-0) | 32C-0 | Six factual rows; exact two-trial selection; stable completion ordering |
| First-seen | [R11 First-seen](https://app.paper.design/file/01M6Y34XE4JKS3A40GMMZ954JE/p-B-0) | 3AV-0 | Observation event list, interval and complete before/after detail |
| Date range, 768px | [Date filters](https://app.paper.design/file/01M6Y34XE4JKS3A40GMMZ954JE/p-C-0) | 3P8-0 | Full-interval containment with 72px rail |
| Coverage | [Coverage inspector](https://app.paper.design/file/01M6Y34XE4JKS3A40GMMZ954JE/p-D-0) | 3SD-0 | Four observing, one baseline-only and one unavailable trial |
| Mobile, 390px | [First-seen mobile](https://app.paper.design/file/01M6Y34XE4JKS3A40GMMZ954JE/p-E-0) | 3YK-0 | Single-event reading and return path |
| Interaction states | [Availability and recovery](https://app.paper.design/file/01M6Y34XE4JKS3A40GMMZ954JE/p-F-0) | 45Z-0 | Generation change, baseline-only, valid empty and unavailable |
| Build | [R11 build contract](https://app.paper.design/file/01M6Y34XE4JKS3A40GMMZ954JE/p-G-0) | 48A-0 | Source contracts, state behavior, gaps and real-path proof |

Exact final screenshot hashes belong to [the inventory](PAPER_INVENTORY_2026-11-14.json). Static visual acceptance does not prove controls, network calls or persistence.

## 2. Source pin and existing capabilities

Use Macro `e856ef0200a0c508c78ef9a6666116020e4835d1`:

- [app/biocatalyst.py](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/app/biocatalyst.py): `trial_screen`, `trial_screen_facets`, `trial_prospective_changes`, `_prospective_model_events`, `_prospective_window`, `_public_trial`, `trial_detail`.
- [engine/biocatalyst/trial_screen.py](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/engine/biocatalyst/trial_screen.py): `_screen_row`, `_matches`, `_row_order`, `_facet_for_dimension`, `_build_model`.

The five factual views remain Milestones, Trial screen, Peer matrix, Changes and First-seen. There is no score, probability, efficacy rank, materiality ranking or implied trading conclusion. Sponsor matching does not resolve issuer ownership. Registry completion is not a readout; current registry results status does not establish whether a company announced results elsewhere.

## 3. Trial screen contract

`GET /api/biocatalyst/v1/trials:screen` takes sponsor, intervention, study_type, phase, status, condition, primary_completion_from, primary_completion_to, cursor and limit. All supplied filters combine with AND.

Sponsor is a normalized source-name substring. Intervention matches name or source alias substrings. Condition matches source condition strings. Phase, status and study type are exact normalized values. No ontology expansion, ticker resolution or generic keyword search is implied. The main filter row exposes Condition, Phase, Status and Primary completion; More filters contains Sponsor, Intervention and Study type.

The order is fixed: primary completion interval start, interval end, then NCT ID. Unknown completion dates follow dated rows. The arrow in the heading communicates this fixed order; it is not an unsupported sort menu.

### Full source-interval containment

A source value of March 2027 represents March 1–31. A date query must contain that entire period. March 15–31 therefore excludes it. Year-only dates require a range containing the full year. A missing usable interval is excluded when either date bound is active. The UI must not invent an exact day, silently change containment to overlap, or treat an excluded date as no underlying trial.

The 768px filter state gives a concrete interval example and a **Use the full month** action. That action changes the draft range; Apply commits it and restarts pagination. Cancel/Escape leaves the committed range unchanged and restores trigger focus. Keyboard date entry and touch date selection must have equal meaning. Dates are inclusive.

### Facts and facets

Render source state, not a universal dash. Null, missing, not applicable, parser degraded and license restricted remain distinct. Use a short cell label and accessible disclosure when needed. Preserve estimated/actual enrollment and date type. Source fields remain accessible in trial detail.

Only Phase, Status and Study type have server facets. A facet ignores its own selected value while honoring the remaining filters. Multi-phase trials can belong to more than one phase bucket; never sum phase bucket counts into a total. Sponsor/condition counts are not fabricated.

Rows and facets are separate requests without a shared public generation identity. Matching response clocks are a minimum consistency check, not a proof that all source state is identical. The implementation should expose a stable opaque cut identity from the existing committed bundle or otherwise establish a tested coherent response contract. On mismatch, refresh deliberately instead of combining old counts with new rows.

### Explicit comparison

Checkboxes collect exact NCT IDs, not inferred peers. The persistent selection tray names the selected trials and hands them to the existing peer-set resolver. The accepted 2–100-ID contract and comparability review remain authoritative. A filter change may hide a selected trial without silently dropping its identity; the selection inspector must disclose hidden selections. Before comparing after a refresh, validate that each selected record is still resolvable. Unknown or unavailable selections need explicit resolution, not silent substitution.

## 4. First-seen contract

`GET /api/biocatalyst/v1/trials/prospective-changes` returns differences first observed between successful polls. It does not reconstruct Registry Record History. The list is newest observation first, with a stable source sort.

The selected event shows **First seen** at the upper observation bound and **After** at the prior bound. Both use explicit UTC in the designed specimen. Never relabel the upper bound as effective time, amendment date or clinical development. The external action says **Open current registry record**, because that is the supplied evidence URL.

Supported filters are one exact change_kind, last_30d/last_90d/last_180d/all window, optional custom dates, q, phase, status and condition. The design uses **Primary completion** for `primary_completion_date`; it does not imply a union of completion kinds. Search and phase/status/condition evaluate the current trial record, not its attributes at the event time.

The server effective window uses inclusive UTC civil dates and the generation's latest observation as anchor, with generation time fallback when needed. Browser today does not shift it. A narrower selection cannot shift the global window anchor. Selected coverage freshness is separate.

### Complete immutable events

A change-kind filter selects an event, not a filtered subset of its operations. Retain the entire returned event. The matching field can be highlighted; the other changes remain available. Preserve total_exact_operation_count, display_change_count and omitted_operation_count. An event with zero displayable operations still remains an event under All and must say details are unavailable rather than no change.

The primary specimen shows three changes (completion, enrollment and endpoint) and a truthful three-of-three count. Larger events need progressive disclosure with an explicit remaining count and no false claim that an excerpt is complete.

## 5. Coverage projection gap and required upgrade

The current public response exposes aggregate `prospective_coverage`: selected earliest coverage start, selected latest observation, active/baseline-only/unavailable counts. Its aggregate state is active if any selected trial is active. It does not certify complete selected coverage.

The internal per-NCT model contains coverage_started_at, baseline_established_at, last_observed_at and accrual_state, but these are not exposed as a public per-trial coverage object. `GET /trials/{nct_id}` adds registry history, not this prospective object.

**Required before implementing the six-row coverage inspector:** extend the existing authenticated Bio projection with a bounded per-NCT coverage response bound to the same committed generation. Reuse existing source validation and entitlement. Include exact NCT identity, explicit state, available clocks and source coverage reason. Do not create another collector, persistence owner or arbitrary aggregation service.

Do not infer trial coverage from event rows: an observed trial with no differences is absent from that list. Do not simulate exact identity through q=NCT fanout: q is substring matching across fields. A projection failure must stay unavailable; no guessed baseline or inferred historical backfill.

Exactly one observation is **Baseline only**. At least two valid observations can support prospective comparison. Missing prospective artifacts are **Unavailable**. Keep counts even when the aggregate is active. A quiet valid window, a baseline-only trial and an unavailable source are different user states.

## 6. Recovery, routing and interaction

Both pages use Terminal AppShell and existing route/auth/context owners. The supported path is Research → BioCatalyst → factual view → selected NCT/event → source → Back. Preserve filters, sort, selected identities, event focus and scroll. Browser Back/Forward must not silently recompute a different selection.

Screen and prospective cursors are signed and bound to query and generation; Screen also binds the caller. Opaque cursors are not portable saved-view state. Filter edits reset them.

| State | User behavior | Required engine/frontend behavior |
|---|---|---|
| Valid zero results | Explain no matching trials/events and provide relevant filter action | Keep the valid query, observed coverage and window |
| Baseline only | Explain that one observation cannot yet form a comparison | No fabricated events or historical backfill |
| 409 generation change | Load current results; keep filters and exact selection identities | Discard old cursor and prevent mixed-generation pages |
| 400 invalid query | Highlight invalid date/filter or reset stale cursor | Do not disguise validation failure as empty data |
| 503 projection unavailable | Scoped unavailable state with retry and usable alternate route | No partial malformed results presented as complete |
| Account/access failure | Shared account/entitlement flow | No source outage diagnosis or data leak |
| Missing/restricted/degraded fact | Short cell label and reason disclosure | Preserve typed source state |

At 390px the selected event replaces the list and has an explicit return link. At intermediate width use the existing 72px collapsed rail, not a second shell. Dialogs require focus trapping, trigger restoration and Escape; lists require meaningful row names and accessible selected state. Color alone must not encode selection or source state. Theme and Chinese locale expansion remain part of the cross-product design/proof unit.

## 7. Acceptance before release

1. March-only and year-only dates preserve precision and obey full containment; an unknown date is excluded under active bounds.
2. Trial result order is stable and no unknown date is plotted as a specific day.
3. Multi-phase counts are non-additive; rows/facets cannot silently mix data cuts.
4. Exact selected NCT IDs survive filtering, detail and Back; unavailable records cannot be replaced by guessed peers.
5. A matching event still exposes all returned changes, including a truthful omitted-operation count.
6. First-seen equals observation upper bound, with prior bound retained and no effective-time claim.
7. One baseline and no event renders Baseline only; mixed 4/1/1 coverage remains mixed.
8. A no-change trial appears in the new coverage projection even though it has no event row.
9. Pagination restart preserves context and cannot append another generation to old rows.
10. Empty, access-denied, unavailable and typed missing facts stay distinguishable.
11. Prove real authenticated producer → API → Terminal consumer → original source → return navigation at 1440, 768 and 390px, with keyboard and touch.
12. No alert enrollment, new watchlist, trade authorization or clinical prediction is inferred from these views.

## 8. Review record and limits

Principal inspected all initial compositions and repaired row/footer overlap, a footer gap, close icons, collapsed-rail icon consistency and mobile spacing. A bounded read-only reviewer accepted four desktop/intermediate compositions and caught the unsupported union label and per-NCT projection gap; both were incorporated. Its mobile image request timed out without a visual result; mobile acceptance relies on principal inspection, not that review. Final screenshot evidence is inventoried separately.

Paper controls are specifications. The design phase and Draft PR remain open. Engine upgrades, product code, binding tests, deployed browser proof and original mission acceptance remain owed.
