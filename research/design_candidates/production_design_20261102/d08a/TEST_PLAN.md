# Verification and implementation acceptance tests

## Executed in this design slice

| Suite | Result | What it establishes | What it does not establish |
| --- | --- | --- | --- |
| Source characterization | **41/41 passed**, including **5 expected baseline-gap witnesses** | Exact pinned pure functions, exports, parsers and source identities;34local files match Git blobs | Fixed product behavior, browser acceptance, backend validity or release CI |
| Proposed design witnesses | **27/27 passed** | Consistent illustrative rules for identity/cutoff/late response/return/access/geometry/save outcomes | Production state management, actual navigation/focus or any deployed behavior |
| JPEG evidence verification |8actual before captures decode; dimensions/digests recorded | Durable before artifacts captured through actual Paper/browser reads | After Paper visuals or completed user journeys |
| Supporting SVG | Rasterized with Inkscape and visually inspected | Reviewable source interaction study | Editable Paper, final tokens/shell, interactive prototype or reference acceptance |

Exact machine receipts: [source-test-results.json](evidence/source-test-results.json), [design-witness-results.json](evidence/design-witness-results.json), [capture-manifest.json](evidence/capture-manifest.json). Node24.22.1. No production code was changed. Hosted CI is not asserted green.

### Reproduce

Obtain the34source files listed in evidence/source-manifest.json at their immutable repository commits, under an audit-source directory with terminal/ and macro/ prefixes. These source snapshots are not duplicated into the production repository. Set D08A_SOURCE_ROOT to that directory and run:

~~~sh
D08A_SOURCE_ROOT=/absolute/audit-source node tests/source-characterization.mjs
D08A_SOURCE_ROOT=/absolute/audit-source node tests/design-obligations.mjs
~~~

The first test verifies Git blob identity before importing the source. Node's type stripping reads the original TypeScript; a resolve hook maps only the existing flowdeskStrings alias. No source rewriting, network fetching or product mounting occurs. Test output files are evidence receipts and should be regenerated only for a changed relevant input.

### Five characterized gaps / qualifications

| ID | Observed current behavior | Required owner resolution before implementation acceptance |
| --- | --- | --- |
| G01 |0DTE Screener's zero-denominator share becomes0 through a denominator fallback | Explicit unavailable ratio in A/source display; preserve valid zero numerators separately |
| G02 |Ascending OI mid sort uses null as0 | Missing-last proposed ordering and meaningful no-price state |
| G03 |0DTE board selector trusts flag without expiry/session validation | Separate real-date/source-session qualification; no browser-local date inference |
| G04 |Hot by-premium and by-volume lists share the incumbent family/session/identity pin key | D08 qualifies sourceList context/deduplication semantics against its frozen obligation; no unilateral new key/store |
| G05 |Display projector accepts weaker identity and hardcodes100 arithmetic assumption | Use actual contract validator/receiver admission; never promote display success or100to verified contract terms |

A passing gap witness means the audit reproduced that behavior. It does **not** mean the defect is fixed or the design is approved.

## Required real-path cases after separate build commission

All cases below are **NOT_RUN on a proposed implementation**. Existing before observations are identified separately in SOURCE_AUDIT. Tests need accepted Paper/reference and exact build identity, controlled source/access fixtures and the existing owner test harness.

| Case | Exact discriminating scenario | Required proof / owner |
| --- | --- | --- |
| UI01 |Tape filter → inspect row → B contract → source evidence → Back | Same filters,sort,column configuration,row,scroll and focus; A/B/D08 |
| UI02 |Current Tape row click/root filter ambiguity | Inspect opens object; explicit Filter to root retains old drill; keyboard/touch equivalent |
| UI03 |Negative z larger than positive z | Absolute rank retained with signed value,below-baseline copy and actual baseline/n_obs |
| UI04 |Volume > prior OI predicate | Matching events/counts only; no opening-trade or recency claim |
| UI05 |Flagged0DTE expiry mismatch at UTC midnight and DST boundary | Source session zone controls; invalid/mismatch visible/excluded, never silently “today” |
| UI06 |Same ticker different source namespace/listing/adjusted terms | Automatic join refused without actual resolver; NVDA1 and term50/100remain distinct |
| UI07 |Aggregate lacking unique event/contract identity | Original aggregate retained; root-only or source evidence, no synthesized constituent/package/leg |
| UI08 |Later/unknown-availability B book | Explicit later context; no cutoff-qualified event-time evidence |
| UI09 |Same dated URL, changed digest/correction | Original reference retained; new source distinguished; unavailable original bytes honest |
| UI10 |Select SPY then NVDA; SPY resolves last | No SPY value/time/book under NVDA heading; generation and cancellation verified |
| UI11 |Revoke access during pending successful read | Protected data cleared; late response ignored; no cache leakage |
| UI12 |401/403/access uncertainty/absence/rate limit/transport | Distinct actual existing outcomes/copy/actions; no subscription fiction on uncertainty |
| UI13 |Source empty versus filters empty versus invalid Stats | Distinct S03/S04/S31; valid independent modules survive |
| UI14 |Missing OI/hot source | Both capabilities discoverable with exact source/access error; no silent preset substitution |
| UI15 |2000source rows, bounded rendering, sorted/filtered CSV | Full same-array export30Tape/38Screener fields, count/order/source match; formula hardening retained |
| UI16 |Local screens and share | Existing20cap/v1compatibility; local storage error; no data snapshot/sync claim |
| UI17 |Shortlist2–4,duplicate/term/session change | Exact row/list/session preserved; fifth refused, not silently replaced; hot-list disposition settled |
| UI18 |Return after reorder/aged-out/duplicate source ID | No nearest-row selection; safe scan heading/notice; direct entry has named fallback |
| UI19 |Reload/new tab/history Back/Forward | Existing parser/history ownership preserved; transient return loss explicit; no extra closed-route keys |
| UI20 |Focused row receives feed updates | Buffer/count; explicit apply; no auto-reorder/focus steal; source/session of buffered set visible |
| UI21 |Statistics counters/premium/venues | Prospective population and count reconciliation;0%premium coverage remains unavailable; UNKNOWN retained |
| UI22 |Prophet all3lanes | Separate model/candidate/operator scopes and access; no investor action issues a research plan |
| UI23 |Public five tasks and legacy screener/ticker links | Correct public destination/individual source dates/optional module failure; no native-access conflation |
| UI24 |Phone320/390 +long EN/ZH labels | Useful first row visible, exact contract and every local view reachable; no body overflow |
| UI25 |768/1024modal and1280/1440/1600dock with actual C | Width rule and domain minimum; no auto-collapse nav; all fields/actions reachable |
| UI26 |Fractional600/860/1200boundaries and extra local chrome | Continuous geometry; header/gutter/dock decisions independent |
| UI27 |Overlay↔dock with keyboard/Brain/search active | One inspector, correct inert/trap/Escape priority and conditional focus restoration |
| UI28 |400%zoom,200%text,short landscape,software keyboard | Reflow/safe areas/actions usable; local2Dscroll exceptions explicit |
| UI29 |Light/dark/non-color/reduced-motion | Measured final contrast/focus, source meaning preserved, no flashing/animated rank under focus |
| UI30 |Admitted durable save pending/rejection/unknown/readback | Same operation reconciled; Saved only after exact object/revision readback; D23 |
| UI31 |Save versus watch versus operator issue review | Separate explicit action/authority/receipt; no navigation mutation |
| UI32 |Performance at accepted release | Actual p75LCP/INP/CLS for mobile/desktop; bounded subscriptions/render, existing telemetry |

## Evidence acceptance rule

Bind any browser proof to exact accepted source/build, access role, source fixture or real source identity, path, viewport/effective content, theme/locale, outcome and screenshot. A fixture test cannot establish real publisher availability or production entitlement. A server200, Paper rendering, screenshot count, green CI or deployed URL cannot substitute for the complete user journey and named negative cases.
