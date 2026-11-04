# International — Paper design reset, 3 November 2026

## Outcome and scope

The country experience and its research workbench have been substantially rebuilt after the user rejected the preceding local version as 4/10. The revised source is built and browser-verified in the original registered worktree. It is **not deployed**, and the user has not accepted the revised design. Mission completion remains false.

Operation: `intl-country-cockpit-20261018`. Branch: `sol/web-intl-country-cockpit-20261018`. Carrier: Macro draft PR #9596. HEAD remains `851c6abebf01c5c8096e7822436455fd1040152a`; MERGE_HEAD remains `c6ac417f4a1d561f8c80a0a6b1977d5ffec6d090`. The pending two-parent merge is retained without reset, abort, replacement checkout or source-publication bypass.

## What went wrong

The earlier completion evidence established portions of behavior while the user-facing composition remained incomplete. The actual Paper references required a stronger hierarchy, quieter surfaces, readable analysis and a coherent relationship between the country overview and deeper research.

Three concrete source/layout defects compounded that problem. Shared `theme.js` reapplied its older soft-contrast palette, overriding the intended page colors. The site-wide body pseudo-element still painted the ambient background after the page's own aurora was removed. In the workbench, an inactive surveillance wrapper retained 68 pixels of padding, while a two-column unranked list left an incomplete row. A compact notice alone did not repair those composition defects.

The reset reads the actual R12 Country Intelligence and R14 Global Surveillance boards in Paper file `01M3P1TW5Y3XWQC37ADDS8K5AG`. R12 remains the country-research reference. R14 informs surface treatment, density and alignment; its specimen population, market counts and numbers are not product data. The existing country-centered workstream contract remains authoritative.

## Implemented design and UX

- The page consumes dedicated Paper aliases from the shared palette owner, so the light canvas is neutral and the dark version has deliberate surface levels.
- Seven country cards provide a useful next-year forecast scan. India's full fiscal-year label is retained.
- Selecting a country opens one primary dossier. Closing it restores the native summary list, and JavaScript-disabled readers retain the full native disclosures.
- Current economic observations, market trend, drawdown and currency availability share one compact reading band.
- The growth chart occupies the full analysis panel. Historical and projected segments, labels, units, dates and a keyboard-operable values table remain intact. Repeated large forecast tiles were removed.
- Policy, conditional paths, fiscal position and transmission content now have a coherent grid. Substantive explanations have stronger size/contrast than metadata.
- The top entry explicitly names Research tools, and the lower workbench has a clear disclosure affordance. Existing horizon, currency and 13-view destinations retain their controller and URL semantics.
- Unranked market returns appear as aligned rows with each exact calculation window. Missing or unsupported states remain explicit. Scanner is visible when selected; its inactive wrapper leaves no empty band in Overview.

The eight changed runtime/derived paths and exact hashes are in `REPORT.json`. `runtime.patch` is the complete runtime delta from prior checkpoint `6a695db8fb1b789b27760de261e472387784cb9a`. It is a zero-context patch, applied against that baseline with `git apply --unidiff-zero runtime.patch`; reverse validation against the final source passed. The ordinary builder's emitted theme and workspace CSS were synchronized to their plain-copy site assets. Financial calculation and qualification owners were not changed.

## Actual build and verification

Tested runtime source tree: `44e97000aa1c2625f0081fb612666fda4b098b41`.

Ordinary generated page SHA-256: `ae736327bb00ddfd2725b09d3f12a33c614a0ba57ab30051429fb6f28ba06ea8`; 23,104,850 bytes. The build used all 511 hash-verified inputs retained from main `19a896b97ae20f2c12475a0207678f92dc4f335b`, including its genuine collector receipt. The delayed index/FX snapshot is 2026-10-30. This is an isolated ordinary build; no provider data was reacquired and no production file was written.

| Proof | Result | Boundary |
| --- | --- | --- |
| Focused country, overview, integration and chrome tests | 158 passed | Source/render behavior |
| Country browser matrix | 20 states; seven countries checked in each | 1440, 1024, 768, 390, 320px × EN/ZH × light/dark |
| Additional native journeys | Five groups passed | Country history, native close/restore, reading order and no-JavaScript country/value access |
| Workbench | Eight currency selections passed; Scanner round trip passed in four contexts | Exact return values, machine/display dates, expansion and restoration |
| Canonical visual capture | 30 raw captures; 26 unique rest/interaction observations packaged | Unmodified repository capture tool, actual built page |
| Shared-theme fixture proof | 128 primary/degraded cases and 16 screenshots passed | Exact pinned Chromium 149 / Playwright 1.61.1; fixture proof only |
| Source gates | Design, template/site sync, runtime-style and P0B closure passed | Mechanical/source integrity |
| Visual evidence gate | Passed | Completeness and integrity, not design acceptance |

The principal advisory reviewer inspected the revised desktop, mobile and returns captures and found no concrete remaining visual blocker in those images. That judgment is not formal source/release review or the user's acceptance. The parent additionally inspected the dark English and Chinese desktop/mobile captures.

Failures remain in the archive: the first iteration's literal radii and palette, the second iteration's 4px mobile chart overflow, an unsupported observer CLI flag, the generated workspace CSS synchronization omission, the first tools observer's ambiguous selector, and the P0B parent-receipt binding mismatch. Each has its correction and actual recheck. The P0B unit run passed 143 cases and failed one stale binding assertion; after updating the existing mutable extension to the genuinely reminted receipt hashes, that exact assertion passed. Historical evidence fields were preserved.

## Remaining production issues and publication block

The fresh read-only native publication status returned `REFUSED / NOT_APPLIED / TYPED_GIT_PRECHECK_REFUSED`. The configured publisher's previously established Mastermind/single-parent boundary still has no proved Macro pending-merge path. No commit, push, merge or deployment was attempted. Fresh GitHub metadata confirms PR9596 remains open and draft at the original HEAD. Main has advanced; the latest PR read reports base `bca436e58f7069ff8b52d31074f30726cfecf0e4`. This is not current-main reconciliation.

A fresh cold-load observation still reproduces shared-header movement: the desktop main content moves from y126 to y77 as the search/layout initializes. Observed layout-shift sums were 0.738 at 1440px and 0.281 at 390px. These are two local observations, not field Core Web Vitals. The actual page has 428,715 DOM nodes and about 23.1 MB of uncompressed HTML. Long-session stability and production performance are not accepted. The source trace leads to the shared navigation's JavaScript-owned layout/settings/search initialization; this reset does not install a parallel navigation controller.

Required continuation is concrete: restore supported native Macro pending-merge publication; publish the preserved source through the original carrier; reconcile current main; obtain current-source independent review and hosted full-data CI; resolve the applicable shared-header/performance and actual-parent Saved/focus findings; run the normal renderer/updater; verify actual served country and tools journeys and a subsequent normal refresh. The prior held Fabric attempt remains held. No alternate publisher, raw-Git commit/push, deployment channel or new worker root is authorized by these records.

## Recoverable deliverables

`REPORT.json` binds runtime bytes, proof scopes, observed release status and archive hashes. `source/` preserves the eight runtime/derived files. `rendered-intl.html.gz` is the exact ordinary generated page. The four PNGs are actual browser captures, not mockups.

`reproduction-inputs.tar.gz` retains the exact source-base archive and genuine 511-input archive plus their manifests, allowing the final ordinary build to be reproduced with the recorded overlay. `evidence.tar.gz` retains final browser/source/canonical proofs, earlier failed iterations, Paper reference images/JSX, and all bounded reset scripts. Both archives were read back and checked. Canonical receipts are also staged under `mockups/evidence/intl-design-reset-20261103/`.

This checkpoint is saved in the incumbent local carrier and remains NOT_CANONICALLY_PERSISTED to GitHub. Local source, fixture proof, canonical screenshot integrity, deployment and user acceptance are separate states.
