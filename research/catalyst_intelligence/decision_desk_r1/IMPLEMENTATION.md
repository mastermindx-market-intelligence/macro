# BioCatalyst Decision Desk R1 — implementation and adoption contract

**2026-10-18 · Presentation consumer ready for integration review. Production integration remains dependent on the retained Bio workstream.**

The accepted Paper design is the product destination. This increment implements the part supported by the current BioCatalyst API: a useful next research task, its main unresolved question, and progressively deeper case inspection. The next production milestone is still one real source change, correctly linked to its company and supporting document, followed by a correction that changes the same case everywhere it appears.

## 1. What this increment implements

`templates/biocatalyst_decision_desk.js` is an independent presentation module. `templates/biocatalyst_decision_desk.css` consumes the existing theme tokens. The component presents one primary question: **what should I review next?**

Each card contains the supplied issuer, a plain-language research task, the supplied milestone wording when usable, the principal unresolved question and a case action. The API supplies the ordering. The component does not convert research priority into investment attractiveness. Cases open Setup, Scenarios, Research and Sources tasks. Optional forecasts no longer occupy the main page as four technical error chips.

The first company slice cannot yet supply its evidence link. Sources states that the link was not supplied by this projection, retains the source wording, and avoids implying that the underlying owner has no evidence. The component accepts the existing registry evidence shape only when its supplied HTTPS URL is also a timing reference. Company evidence requires an explicit compatible projection before it becomes navigable.

Current, conflicted, stale, cancelled/withdrawn, superseded and elapsed-but-uncorroborated records have different meanings. In particular, an old revision does not mean that the underlying event was withdrawn. A past uncorroborated window creates a question about the outcome; it does not imply failure or delay.

The module clears its previous page, detail and count on refresh or an unsuccessful/inconsistent response. It rejects obsolete in-flight completions, binds pagination to one publication and input cut, and requires detail to match the selected row. Accepted payloads are copied and frozen. Authentication and publication selection remain host responsibilities.

## 2. Source lineage and custody

| Item | Pinned source / status |
|---|---|
| Authoring base | Macro main `b912fd97827cca925a7123aa2012e9765077f3f7` |
| Existing Bio implementation | [Macro #6712](https://github.com/mastermindx-market-intelligence/macro/pull/6712), candidate `ec5c2e2544576f20348c6eadf834fe3cefae8039` |
| Existing Company fact owner | [`company_catalyst_event.v1`](https://github.com/mastermindx-market-intelligence/macro/blob/ec5c2e2544576f20348c6eadf834fe3cefae8039/engine/company_intelligence/events.py) |
| Existing read model | [`biocatalyst_what_matters_next.v1`, schema `1.0.0`](https://github.com/mastermindx-market-intelligence/macro/blob/ec5c2e2544576f20348c6eadf834fe3cefae8039/engine/biocatalyst/what_matters_next.py) |
| Existing detail model | `biocatalyst_wmn_detail.v1`, schema `1.0.0`; selected event, same-generation trial when applicable, related events |
| API seam | `/api/biocatalyst/v1/what-matters-next` and `/api/biocatalyst/v1/what-matters-next/detail` |
| Research method | `biocatalyst.research_triage.v1`, research priority only |
| Accepted design | [Catalyst Intelligence · Decision Desk R1 on Paper](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-20-0) |

Fresh source inspection found unpublished test changes in the incumbent repair checkout at the same #6712 head. This increment was authored in a separate managed workspace and changes only newly named component, test and research-package files. The API capture ran in a second managed workspace pinned to the immutable candidate. The existing repair, historical-event carrier #6389, outcome-accrual carrier #8468 and Catalyst-to-Opportunity carrier #9552 retain their own scopes.

The earlier design proposal's `company_event.v1` reference is superseded by this more specific source finding. The implemented non-fiscal owner extension is `company_catalyst_event.v1`. A proposed `catalyst_case` object is a product composition proposal, not a replacement source authority or an admitted backend contract.

## 3. Host integration

Load the module and stylesheet using the existing template/asset mechanism after the retained Bio owner is ready. Mount inside the existing Bio workbench, preserving its global navigation and advanced research entry points. Authentication uses the host's existing authenticated `fetchJson` implementation.

```javascript
// This function belongs at the existing WMN host seam. Pass real host bindings.
function mountDecisionDesk({root, fetchJson, getContextKey, onCaseChange}) {
  const encode = values => {
    const p = new URLSearchParams();
    Object.entries(values).forEach(([k, v]) => { if (v !== null && v !== undefined) p.set(k, String(v)); });
    return p.toString();
  };
  return BioCatalystDecisionDesk.createDecisionDesk({
    root,
    locale: document.documentElement.dataset.lang || 'en',
    getContextKey,
    onCaseChange,
    loadPage: ({query, cursor, signal}) =>
      fetchJson('/api/biocatalyst/v1/what-matters-next?' + encode({...query, cursor}), signal),
    loadDetail: ({event_fact_ref, issuer_id, generation_id, signal}) =>
      fetchJson('/api/biocatalyst/v1/what-matters-next/detail?' +
        encode({event_fact_ref, issuer_id, generation_id}), signal)
  });
}
```

### Required host behavior

- `loadPage` and `loadDetail` resolve to parsed, unmodified API payloads. They reject HTTP errors with `error.status`; 401/402/403 display access-required, 409 requests a consistent reload, and other unsuccessful/malformed results display unavailable. An empty covered result is distinct from a failed request.
- `getContextKey` returns a nonempty opaque host key covering authorization generation, account/tenant and relevant research context. It must contain no credential. **Call `contextChanged()` synchronously on logout, account/tenant change, entitlement change or context change, including while the component is idle.** This clears previously rendered data immediately. The getter checks at request completion are an additional race guard, not an authentication observer.
- Call `refresh()` to load data. The supported component filters are upcoming horizons 7/30/90/180/365 days, Needs review, and Event history. The last two have `horizon_days: null`; the host must omit null query parameters. Search/family/lane filters are outside this first component seam.
- Call `destroy()` when unmounting. It aborts pending work and prevents later completions from repainting.
- `onCaseChange(selection)` gives the existing host router `{event_fact_ref, issuer_id, tab}` or null. Map this into the host's existing URL state. After loading the relevant list, use `openCase(selection)` to restore a supplied case and task. It returns false if the case is outside the loaded list. The host retains any broader direct-detail routing capability; the component does not fetch another universe to repair a missing case.
- `onNavigate(intent)` is optional. It receives a validated supplied stock/evidence destination. The default is an ordinary anchor. A custom handler must retain the established account/context boundary.
- Synchronize the eventual template/site assets and register the new pytest entry plus its JS/fixture dependency paths in the existing Bio CI job when the retained source owner integrates. This package does not modify the shared CI manifest or the incumbent host files.

The `createController` API is separately exported for response-lifecycle verification. Publication IDs are opaque identifiers. A request counter is not a source revision or an authoritative correction watermark.

## 4. Producer changes needed for the complete user journey

| Order | Existing owner work | Required acceptance evidence |
|---|---|---|
| 1 | Finish the retained #6712 repair: composed timing/revision fields, issuer-master and alias-cut binding, future-cut rejection, optional-estimate coverage semantics, typed stored-contract failures, and template/site synchronization. | Exact repaired head, focused owner/API/publication tests, applicable CI and clean integration custody. |
| 2 | Preserve admitted company evidence through `compose_company_event_rows`. It currently replaces `evidence`, `assets` and `relationships` with empty arrays after the Company adapter retains those projections. | One displayed claim links to its permitted supporting document/anchor and the exact event/source revision. Missing evidence means projection-unavailable, not evidence-absent. |
| 3 | Supply the supported change that earns a signal: prior/current values or the incumbent owner's existing field-change record. | The main statement “what changed” can be reproduced from cited source revisions; reprocessing alone cannot become a business change. |
| 4 | Retain the asset/relationship/exposure fields required for each released claim. | Issuer identity alone never becomes a claim about asset ownership, development rights, revenue or economic materiality. A timeline-only card can ship without the full rights graph if it states the remaining limits. |
| 5 | Enforce correction admission in the existing publication owner. | Once that owner accepts a relevant material correction, affected current interpretations become unavailable or corrected, and an older composer cannot restore an obsolete interpretation. |
| 6 | Wire this presentation into the existing authenticated workbench and its URL/account lifecycle. | Entitled browser proof at the integrated head, including idle logout, direct case routes, an actual current source cut, one later correction, both languages/themes and mobile. |

### The publication fence must be implementable

Use a locally admitted dependency revision watermark in the existing publication owner's transactional store. Admit invalidation and change the current availability state in the same owner transaction. A composer records the admitted input revisions it consumed. Before moving the current pointer, compare that consumed set with the locally admitted current set using the same transactional fence. If a newer required dependency has already been admitted, the older candidate cannot become current. Retain the previous version as historical lineage.

Do not describe this as one transaction across independent upstream databases. The guarantee starts when the existing owner accepts the invalidation; source discovery latency is measured separately. Pointer-last artifact publication alone proves that a complete artifact is selected, not that it remains semantically current. Optional estimates should gate their dependent claims without erasing otherwise valid factual research tasks. Notification/outbox behavior remains with its existing durable owner and requires separate delivery proof.

## 5. Verification and its limits

The fixtures are exact response bytes from the pinned #6712 FastAPI route through its existing TestClient harness. The harness supplies a synthetic owner cut, a fixed evaluation clock and a test authentication override. The nine captured responses cover five upcoming horizons, review/history with null horizons, the default page and same-generation detail. `fixtures/capture-receipt.json` records each SHA-256 and the private/no-store headers. `generate_wmn_fixtures.py` refuses a different Git head.

The fixture uses AMLX as a synthetic identity specimen. It is not a current market case. It also exposes a producer qualification issue: source wording says September 2026 while the fixture interval is September 1–September 1 with day precision. The consumer preserves supplied wording; that replay is not semantic acceptance of the timing extraction.

Run the component checks with:

```bash
node tests/test_biocatalyst_decision_desk.cjs
python -m pytest tests/test_biocatalyst_decision_desk.py -q
python research/catalyst_intelligence/decision_desk_r1/build_preview.py
node tests/verify_biocatalyst_decision_desk.cjs
```

The browser check needs the existing Playwright/Chromium runtime. `CATALYST_CHROMIUM_EXECUTABLE` selects an installed browser; `DECISION_DESK_QA_DIR` chooses an output directory. The standalone replay deliberately labels its synthetic data and simulated conflict/withdrawal/unavailable controls. Its fixture driver is confined to research/QA files and is never a production fallback.

Direct checks cover exact response bytes, optional estimates, asynchronous list/detail races, current-context changes, unsupported contracts, issuer/revision/timing mismatches, complete pagination, superseded/withdrawn semantics, elapsed windows, immutable state and correctly bound links. Browser checks cover the actual rendered tasks, URL restoration, keyboard/focus behavior, correction/error states and 16 EN/ZH × dark/light × 320/390/768/1440 layouts. An independent principal review accepted the bounded component after the historical-revision correction.

This is implementation evidence for the presentation consumer. It does not prove live source admission, entitled runtime access, publication-side correction fencing, validated forecasts or monitoring.

## 6. Research progression under Catalyst Intelligence

The ambitious destination remains a decision system that can identify a dated opportunity, explain its expected mechanism, show the main failure condition and expose the complete supporting research. This current milestone-review slice is the first usable delivery boundary.

1. **Evidence and change qualification:** sample issuer guidance, registry schedules, results and regulatory actions; compare extracted windows and changed fields against expert-labelled source versions. Include ambiguous issuer mappings, omissions and explicit corrections. Measure which review tasks are useful and which alerts create avoidable work.
2. **Separate forecast targets:** clinical outcome, regulatory outcome, economic exposure, market response and investment utility need their own labels, horizon, admissible inputs and evaluation populations. Do not collapse them into one confidence percentage. Retain the existing research owners and the outcome-accrual workstream.
3. **Time-faithful evaluation:** separate source issue time, lawful availability, actual observation, accepted dependency time, composition, publication and realistically actionable market time. Distinguish historical reconstruction from actual-system replay. Test failure and delisting cases, not only eventual successes.
4. **User-value evaluation:** test whether intended users can identify the next action, the main uncertainty and the evidence supporting it within one short review. Compare against an event calendar and existing company research. A prettier screen or a well-calibrated outcome model alone does not establish investment utility.
5. **Sector expansion:** share identity, evidence lineage, publication/correction controls, entitlements, case presentation and evaluation infrastructure. Keep sector-specific event definitions, economics and research models with their domain owners. Reuse the Gov Revenue and Bio workflows before admitting another sector. The active Catalyst-to-Opportunity effort remains a separate consumer workstream until its integration is explicitly reconciled.

The next release gate is concrete: a real issuer-linked source change with an inspectable supporting claim, followed by a later accepted correction that removes or revises the earlier conclusion through the same existing publication and UI path.
