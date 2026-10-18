# BEA GVC / GMI — product, design and architecture audit

Date: 2026-10-17. Scope: the existing Macro #9433 / #9444 / #9494 programme, with implementation changes confined to the original #9494 consumer carrier. Chairman requested a holistic Pro-mode audit and substantive design/robustness improvements. This report is implementation evidence, not source-admission or production acceptance.

## Executive finding

The programme has credible offline source preparation and strict nonpublication guards, but its original user outcome is **not complete**: no genuinely admitted BEA L0/L1 generation is connected to the product. Repeating checksum refinements or calling an authenticated 503 endpoint a finished intelligence product would conceal that gap.

The useful product is an **industry import-input research view**: understand geographic allocation, compare accounting years within one vintage, inspect source quality, and take that context into security research. It must not infer named-company suppliers, live trade flows, historical point-in-time availability, rankings or trade sizes from imputed annual industry accounts.

This audit improved the real consumer and its testability while preserving that boundary. It does not declare the currently inaccessible original-source problem resolved.

## Evidence and recovery

Protected procedure: `Mastermind@f381af6758533906865361373addbb0514f86d7d`, skillpack 1.0.1/bootstrap 1. The original GMI workspace and PR branch were retained. The interrupted mainline integration was recovered from `MERGE_HEAD=94cdfd6f72d15b5b7491476a23960c52ff3e4d5b`; its new `c19-wp22-dhi-traversal` import dependency was added without removing any incumbent path. Two canonical CI closure/packing tests passed, and the merge was committed locally as `1a5ccad57d021d48d5ec60bcdece57c77e17390f`. Relative to that accepted mainline, exactly ten mission paths differed and no data path changed. This was a merge **into the feature branch**, not a merge of the PR into protected main.

The existing independent paid Fabric review `gmi-bea-20261017-human-view-security-review-001` returned `REQUEST_CHANGES` on prior head `5cc78cf01cb74caa1a9f5236bb9c43870950cb49`. Its security core passed; its significant release, contract-parity and accessibility findings were valid. This audit consumed that report, checked actual source and browser behavior, and made the changes below. The review is not a current-head GitHub approval.

Direct audit/design implementation was retained for **PRINCIPAL_JUDGMENT**: product meaning, source authority, chart representation and network behavior were interdependent. The small unfinished-merge repair was a **CRITICAL_PATH_SHORTCUT**. A fresh independent review of the resulting immutable head remains a separate acceptance step.

## Findings and implemented corrections

### 1. A prospective status was masquerading as an integrated contract

The old browser expected `PUBLISHED_CURRENT_DESCRIPTIVE`, but the Python serializer could not emit that status and the API could only return 503. Synthetic fixtures had manually added publication flags to demonstrate the charts. That established rendering, not human/machine parity.

The shipped browser now recognizes the **actual** owner vocabulary. All network-delivered candidates remain withheld. Its chart component consumes the real `CANDIDATE_NOT_PUBLISHED` packet only through a testable CommonJS export and always renders an explicit unpublished-research warning. Production mounting cannot call this preview path. No invented public status, admission flag or second publication owner is added.

A client/Python contract test pins schema, edition, years, region IDs, exact field sets, all refusal reasons, integer USD-million representation and commodity count. This is a structural projection of the Data OS/consumer contract, not an independent authorization policy. Future genuine publication must be implemented by the incumbent source and app owners and tested end to end; it cannot be enabled by changing a client flag.

### 2. The only HTTP/browser coverage was outside PR CI

The earlier human/API tests were invoked by `tier-gate` under `gate: data`, not the pull-request code gate. The existing BEA code job now executes source contracts, actual HTTP/paywall/no-store tests and physical Chromium tests. Chromium is a required installed dependency, not a silent skip.

Adding the HTTP import graph initially caused broad wildcard scope inference to select the job on unrelated homepage changes. The correction uses the existing **curated-exclusive** mechanism, with the complete measured concrete import/literal-read closure, fixed view assets and package initializers. The existing curated-set, dependency-closure, ancestor and packing tests remain controlling. No ceiling, exclusion rule or required test is weakened. Current test receipts are recorded in the PR/checkpoint after validation.

### 3. Charts encoded accounting incorrectly or incompletely

Negative regional amounts previously extended rightward like positive amounts and differed only by color. Zero history values inherited a visible minimum-height bar. Historical values were pointer-only titles under an image role.

The rewritten component uses a shared zero baseline: negative regional amounts extend left, negative historical values extend below zero, and zero renders at exactly zero height. Signed numerals reinforce the direction independently of color. Each year has an accessible label and keyboard interaction; an HTML table exposes every year, world amount, annual change and rounding residual. Arrow keys/Home/End select years with visible focus. Accounting-quality counters and signed residuals are shown explicitly, not presented as a confidence score.

The arbitrary Canada-only headline metric was replaced by total industry inputs; Canada remains one of seven equally represented source regions. Earlier years remain retrospective observations from the May-2026 publication, never as-known-then signals.

### 4. The workspace was technically safe but not a coherent research experience

The earlier unavailable page was a large empty sheet with an exact-code form and one generic warning. The new layout has a clear masthead and breadcrumb, compact research query bar, bounded availability state, source record, concise interpretation guidance and expandable evidence. Users can recheck availability, change industry without reloading the shell, navigate back, reveal source details and copy a source reference.

The light/dark palette follows the house visual vocabulary and existing saved theme preference. The page uses system/house font stacks with no external font download. CSS is a fixed same-origin asset, allowing CSP to use `style-src 'self'` rather than inline stylesheets. Mobile layouts remove horizontal overflow and retain meaningful reading order. Reduced-motion preference and visible keyboard focus are supported. This is a tested accessibility improvement, not a claim of complete WCAG certification.

### 5. Error, identity and asynchronous state needed stronger boundaries

All 26 current owner refusal reasons now have specific explanations. Authentication expiry, entitlement denial, client 422, source-service 503, malformed/oversized response and network timeout are distinct. No raw error content or private path is forwarded into the DOM. A failed request does not imply the source is not produced; the record says “not confirmed” where appropriate.

The controller adds a bounded 10-second request timeout, aborts superseded requests and independently guards response order even when transport ignores abort. The exact raw route segment is split **before** decoding; trailing newline and encoded separators cannot exploit JavaScript's permissive end anchor. Back navigation and manual retry use the same canonical endpoint. There is no polling daemon, retry queue, source cache or alternate transport.

Source and client validation preserve exact integers. A new backend regression closes Python's `False == 0` equality trap in yearly-change packets. Unicode labels, provenance fields and code identity continue to fail closed.

## Architectural boundaries retained

`Existing Supabase cookie/Bearer identity → existing always-on site_full entitlement → fixed source-free HTML/CSS/JS → canonical authenticated industry API → existing Data OS registry/source owner`.

The human shell never reads a provider source file. The API still has no admitted original-byte read binding and returns no industry figures. Browser cookie tests exercise the **real shared cookie parser and require_user dependency**, while substituting the canonical identity resolver and entitlement store with explicit test fixtures; they do not constitute real Supabase account verification.

Do not invent security/listing identities to fit a security-specific read contract around an industry dataset. Do not create a parallel BEA rights, revision, source cache or publication registry. An eventual generation cache must remain under the incumbent Data OS owner and preserve revocation/correction semantics, not merely improve a benchmark.

## Verification design

Tests execute the shipped JavaScript through Node and the actual Python owner, plus physical Chromium with a TestClient bridge to the real FastAPI routes. Coverage includes light/dark desktop and mobile, zero/negative chart geometry, keyboard year selection, data-table parity, no horizontal overflow, source refusal with no visible values, malformed response, out-of-order responses, back navigation, manual retry, real cookie-parser wiring and CSS entitlement/no-store behavior.

Visual captures are labeled by provenance: normal unavailable views use an empty test Registry, while chart screenshots carry a visible **SYNTHETIC TEST FIXTURE / UNPUBLISHED / NOT REAL BEA DATA** watermark. No screenshot or fixture is production evidence. Final counts, immutable SHA, hosted checks and screenshot paths belong in the acceptance receipt rather than being inferred from this report.

## Remaining true completion conditions

1. Existing Data OS owner lawfully resolves the explicitly refused original 2017 Use-axis/workbook inspection and the retained 72-response axis discrepancy. Neither the inspection nor the separately denied native-branch push was retried in this audit.
2. Exact original response/capture identities, edition-specific industry handling, L0/L1 native UTC ingestion/revisions/corrections and all 138 industry views are admitted by their canonical owner. Both source contracts currently remain proposed.
3. The source owner binds one authenticated current generation to the existing consumer; a server contract that genuinely qualifies user-visible values is implemented and independently reviewed. Client flags and self-asserted hashes are insufficient.
4. The actual production browser and machine API prove same-generation values, real auth/entitlement behavior, source-quality limits and correction/revocation handling. Only then should production navigation be linked and product acceptance claimed.

Further work should prioritize those dependencies, not more decorative status reports or redundant checksum layers. This audit materially improves the consumer but does not shrink the programme's original production outcome.

## Verified results for this audit implementation

- **85 tests passed** across the actual source consumer, JavaScript/Python contract parity, physical Chromium browser cases, API/paywall and no-store suites. The browser tests are committed and required; production-source values and real account credentials are not used.
- **Four canonical CI tests passed**: curated job set, complete import closure, ordinary-code packing, and ancestor initializer census. Declaring the previously omitted package initializer in eleven existing GMI import owners reduced blind-spot census rows from **350 to 339**, below the unchanged 344 ceiling.
- The GMI code gate's **748-file concrete dependency scope** was derived from the existing canonical scope compiler plus actual package initializer paths. All literal/import dependencies remain covered; only opaque wildcard fallback spread was removed. The new job is registered in the incumbent curated set, not exempted from it.
- The resumed feature-branch merge's earlier closure tests passed, and the existing source/API/deployment integration tests on the resolved mainline tree had passed **334 tests** before this visual rewrite. Those receipts do not stand in for current-head hosted CI.
- Before/after browser captures are retained in [the verification folder](verification/BEA_GVC_PRO_AUDIT_20261017/README.md). The chart screenshot is visibly marked synthetic/unpublished.

Remaining nonblocking UX: a direct unauthenticated/free-tier navigation still receives the existing backend's standard 401/403 response. The signed-in view now explains expired/denied fetch states and links back to the existing account journey. A future shared HTML interstitial improvement belongs with the incumbent app/paywall owner; it must not introduce a separate auth path.

The final complete deployment self-heal suite also passed **289 tests** after the audit edits. The canonical CI manifest validates at **325 logical jobs / 327 fragments**. These are local exact-worktree results; hosted PR checks, independent current-head review and all native-source/product acceptance requirements remain distinct.
