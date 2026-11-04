# International production implementation — 4 November 2026

## Outcome and release status

The rejected local shell has been replaced with a country-centered Paper implementation and a substantially smaller initial document. The final ordinary build and local browser journeys are qualified; production installation, formal current-head review, hosted checks, actual-parent acceptance and subsequent normal refresh remain separate release gates. **MISSION_COMPLETE: false.**

This is the continuation of operation `intl-country-cockpit-20261018`, branch `sol/web-intl-country-cockpit-20261018`, and draft Macro PR #9596. The original source worktree and held effects remain in custody. Protected procedure is pinned at Mastermind `2b12028b3910303e85d8e591fd40bb35c779ab78`.

## What went wrong

The earlier green tests did not establish design acceptance. The Chairman explicitly rejected the earlier local version as 4/10, and that rejection remains part of the record. The source and rendered-page inspection found concrete implementation defects:

- The page emitted 23,104,850 bytes of HTML and 422,633 elements before the visitor selected a research view. Dossiers alone contributed 300,704 elements by rendering ten contexts across 64 catalogue jurisdictions.
- The visual hierarchy was dominated by legacy controls and warnings. An inactive surveillance wrapper left a blank band, while useful country observations and projections lacked a clear reading order.
- Shared navigation geometry changed after load. The observed local layout-shift sums were 0.7376887 on desktop and 0.2813956 at 390px before the bounded header adoption.
- The enhanced Dossier picker exposed dozens of unavailable markets as a large disabled wall. Scanner values, labels and source badges crowded each other, with a reproduced 399px document at a 390px viewport.
- Publication capability had refused the original Macro pending merge. That was a real release dependency, not evidence that the local product had been deployed.

The new fragment architecture revealed an additional integration issue before publication: the default Caddy asset rules would have routed its already-public presentation through registration/paywall checks. The candidate now contains the narrow serving and cache policy needed by those assets. No installed Caddy change is claimed.

## Design and workflow

The design follows the actual Paper R12 country boards and R14 visual composition references in file `01M3P1TW5Y3XWQC37ADDS8K5AG`. Reference values remain specimens; only qualified existing product inputs populate the page.

The country page uses restrained neutral surfaces, a compact seven-economy forecast strip, a visible economic/market observation band, a growth path with exact values, and readable policy, conditions and fiscal sections. Country selection, native disclosures, source dates, missing-data states, fiscal-year labels and keyboard/history behavior are retained. Qualified returns with unequal windows show their own calculation dates and are not falsely ranked.

Research tools remain discoverable beneath the country workflow. The Dossier picker now presents the seven selectable markets. Scanner cards separate labels, values, context and evidence badges. Mobile research views remove redundant nested padding, use a two-column question grid and clock group, and wrap controls and long source labels inside the viewport. Existing state, Inspector, Scenario, Library and Saved owners are retained.

## Deferred presentation and initial-load cost

`lib/intl_workspace_fragments.py` is a pure presentation emitter called by the ordinary International builder after generation binding and before `write_page`. It does not compute returns, forecasts, risk or source qualification.

Dossier, Scanner and Coverage move to 84 stable JSON presentation assets. Country, Overview, Compare, Macro, Risk, History/Scenario, Library and Inspector remain eager. The initial country page requests no fragment. Thirty descriptors bind exact bytes, SHA-256, generation, context and market membership. Dossier bundles contain only the selected jurisdiction across ten contexts.

The controller requests same-origin assets with no-store caching and an exact-hash query; validates bytes, digest, envelope, generation, context, market, roots and executable markup; then attaches only an eligible active view. Late replies cannot overwrite a newer selection. Loading, retry, source-change reload and failure states are explicit. Cache limits are six JSON entries/4 MB, with only the active deferred panel retained and a temporary Scenario origin pin. Native disclosure references are bounded and detached nodes are released.

Final HTML is 3,844,803 bytes, an 83.4% reduction. Raw HTML elements fall to about 66,681, an 84.2% reduction. These are deterministic build measurements. Local browser timings and layout-shift sums are diagnostic observations, not field p95, a real-device SLA or a claim about production traffic.

The shared-header change reuses the bounded geometry and native no-JavaScript partial from existing Macro #9495 commits `39dca322`, `ed94ad75` and `5370b9f5`. It introduces no second navigation JavaScript owner. Observed post-adoption layout-shift sums were 0.0701576 on desktop and 0.00436317 at 390px; dark/ZH samples were 0.0340429 and 0.00413274.

## Ordinary publication and access boundary

The final release seed contains one coherent ordinary-build `site/intl.html` plus all 84 assets. Every descriptor was checked against the installed source-worktree bytes before the generated access test passed. This is source-worktree seeding, not deployment.

The exclusive `/assets/intl-workspace/` namespace contains only rendered public presentation. It is added to the public access policy and to the two Caddy registration-asset exclusions, with a dedicated `Cache-Control: no-store` rule that also covers `?v=<sha>`. It is not enrolled in the one-year immutable cache rule. Raw country data, macro inputs and API boundaries retain their existing restrictions.

Actual Caddy 2.11.4 adaptation verifies the precise semantic delta across both serving configurations: two new no-store routes and four matcher exclusions. After removing exactly those additions and normalizing only the two input-config filename entries that Caddy inserts, all other route ordering and fields are identical.

The existing renderer stages `site/`; the updater recursively copies it to `site.served/`; neither needs a new publishing mechanism. The exact helper is added to the renderer's source trigger. The existing Terminal parent constructs its legacy child at `https://www.mastermind-x.com`, so its fragment URLs also resolve there; no second beta/app JSON proxy is introduced.

## Verification and evidence

`REPORT.json` binds source files, build and asset identity, receipts and the read-back-verified archive. `implementation-evidence.tar.gz` contains the actual generated output, source snapshots, verification scripts, raw logs, browser captures and failure history.

The completed checks include:

- Final controller suite: 188/188, including the 16 deferred cases and existing view/controller suites; no skips or cancellations.
- Focused Python build/render/country coverage: 170 passed in the recorded earlier pass; final partition/frozen-builder/header/nav coverage: 122 passed. These suites overlap; do not add them into a unique total.
- Serving/access tests: 54/54, plus the final regenerated descriptor/asset boundary check after the R8 seed.
- Shared-theme P0B: 128 actual browser cases and 16 screenshots; 144 receipt-integrity tests and closure guard passed.
- Actual ordinary-page country/rest states, seven-country selection, deferred views, 21 Dossier selections, eager tools, Inspector return, Scenario cancel/confirm and no-JavaScript access, within the separate receipts' exact scopes.
- Final research visual pass at 1440 light/EN, 390 light/EN, 1440 dark/ZH and 320 dark/ZH: no page errors or horizontal overflow, seven selectable markets and text contained within its cards.
- Final canonical recapture:26 unique observations (16 rest cells and10 real hover/focus interactions), with the full templates/site delta integrity guard PASS. These are mechanical evidence and visual review inputs, not formal design acceptance.
- Template/site synchronization, runtime style rules, Chat navigation synchronization, design tokens, CI trigger closure and authored-source guards, as named in the final report.

The build uses the same 511 hash-verified committed inputs from `19a896b97ae20f2c12475a0207678f92dc4f335b`. No provider data was reacquired. The source snapshot retains its own observation dates and genuine unavailable/stale states. A missing temporary input copy was restored byte-for-byte from the immutable R3 reproduction archive; the cause of that disappearance is unproven.

## Preserved failures and limitations

Failed receipts remain failed. The first full-page observer stopped after successful country/deferred checks on an unavailable Dislocations context. The next journey observer assumed a desktop Scenario tab that exists only on mobile. A subsequent setup attempt closed an already-open tools disclosure. Corrected selectors/declared contexts completed the intended journeys; the original receipts and logs remain available.

The initial Scanner mobile capture exposed a real long-badge overflow and led to the CSS repair. Some R6 capture filenames were reused by the R7 observer before packaging, so not every earlier failed receipt still has its original matching PNG. That evidence limitation is disclosed; the failed logs/receipt and current successful captures are preserved. R8 release filenames are unique.

The first Caddy comparison used the wrong expected expansion count and compared Caddy's generated input-filename hide entries. Its failed receipt remains. The corrected semantic proof accounts for the actual two-server expansion and normalizes only the evidenced filename fields.

The setup-only diagnostic receipts marked RUNNING are historical setup artifacts, not claims of active background execution. No production, external review, authenticated access or accepted live FX result follows from local test success.

## Original carrier and next executable actions

Protected Macro main `bb3b7273f1e9ccb869b6500c97871093eb22005a` is genuinely integrated in the original worktree. Its final increment from005232 contains9,123 data-only paths with no overlap or runtime changes; the exact raw Git delta was verified after three-tree integration. Before publication, HEAD remains `851c6abebf01c5c8096e7822436455fd1040152a`; original MERGE_HEAD remains `c6ac417f4a1d561f8c80a0a6b1977d5ffec6d090`. The native publisher now supports the required Macro two-parent fences; status is proven, commit/push are not yet claimed by this report.

1. Validate and stage the exact candidate, retain fewer than 3,000 changed paths, and commit through the typed publisher with exact HEAD, integrated-base and prepared-tree fences.
2. Read back commit, parents, tree, index and worktree. Only then clear stale merge metadata with ordinary `git merge --quit`, preserving source identity, and push the exact new HEAD through the same publisher.
3. Verify remote/GitHub identity and exact-head CI. Commission one distinct bounded, read-only independent review through the original Web Fabric root and parent if actual native strict-route admission succeeds.
4. Preserve Draft/HOLD and obtain formal current-head review disposition. The blocking review `5723137485` remains separate from a paid technical verdict or an older approval.
5. Complete the applicable actual-parent, current-main F10 and 15-minute W3U release conditions, then the normal renderer/updater and installed serving-policy adoption.
6. Verify actual www/beta/app/Terminal journeys, the existing once-only full-history FX acceptance path, and a subsequent normal refresh. Obtain user design acceptance.

Held Fabric run `intl-20261022-workspace-transport-query-r2` remains terminal, execution not eligible, execution absence unproven and retry false. It is not replayed, accepted, reconstructed or replaced by a new source review.

Historical superseded static previews and visual images were consolidated only after exact member-hash verification and an active-consumer check. Their immutable archives and restore manifests preserve every archived byte. JSON operation/effect/review receipts and executable verification sources remain at their original paths. This preserves original custody while meeting the PR's changed-path fence.

This report is a release-candidate evidence artifact. It is not a new queue, deployment owner, authorization grant or acceptance receipt.
