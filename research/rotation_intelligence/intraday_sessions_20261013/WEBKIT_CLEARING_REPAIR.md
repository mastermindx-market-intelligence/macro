# Shared tape clearing: WebKit-discovered final repair

Original operation/PR #9196. The published 85d925 source had accepted backend and UI reviews. An additional actual-page WebKit capture found that a denied source refresh cleared the new interval panel but could leave the incumbent overview slim tape visible. The earlier Chromium visibility-only assertion missed this due to route-transition timing. It is a real shared-consumer clearing defect, not a reason to change the source or access policy.

The bounded repair moves the incumbent renderSlimStrip(pulse) call to the start of renderTapeBand(), ahead of the optional full-band and missing-pulse guards. Thus both surfaces process a denied/unavailable null, even when only the slim strip is present. For a normal pulse the call still executes once. No data values, score, request cadence, source, authentication, permissions or new renderer are introduced.

Two exact-shipped-function Node regression cases fail before and pass after the repair. The browser harness now requires the actual visible CSS class to be cleared and then waits for the strip to become hidden, rather than allowing a route transition to provide a false pass.

The complete eleven-suite functional run passes 639 tests with one previously recorded pytest temporary-directory cleanup warning. Four Chromium AND four WebKit actual-Jinja-page cases pass desktop/mobile, dark/light, EN/ZH, keyboard and focus retention, denial clearing in both views, stale removal and expand/collapse without refetch. Zero page-script errors and no horizontal overflow. Captures remain synthetic/local-interception proof, not deployed behavior.

Both engines now retain their console/request observations. The incumbent subsector map logs a caught error because its unrelated data is intentionally stubbed, and the deliberate denial test logs an expected HTTP403. No failed requests or other page-script errors are hidden. These are controlled fixture limitations, not a claim of a clean production console.

Current template SHA256 is c48128c0086ddf710f346c5922e133a592d66f7c31b2f20634ab45fbd63778ed. ui_proof/browser_report.json and ui_proof/webkit/browser_report.json bind all images and checks. The capture script accepts --browser chromium|webkit using the existing installed runtimes; no software was installed.

The PR was returned to draft before this repair; it has never been armed for merge. Backend source blobs are unchanged and its accepted review remains applicable. The existing final UI review remains evidence for unchanged code; one narrow independent review will qualify the moved helper call. Required exact-head CI and normal release/real-path proof remain owed. No Terminal private SSH retry or Executive plugin is used.
