---
workstream: WS:MARKET-MEMORY-W2C
session: claude/ssd-market-memory-retained-ui-01a1333c-5d535132744300fd
model: codex
ended_because: ci_handoff
mission: Deliver exact retained browsing, current comparison and authorized original
  saved output within the complete Market Memory program.
state_before: Retained APIs and lineage source were installed; the customer surface
  lacked the three exact-selection modes and saved feature projection.
changed:
- path: app/market_memory.py
  what: Add exact catalog and saved routes and current-policy guard for legacy trusted
    routes.
- path: templates/market_memory_retained.js
  what: Render three modes with exact URL selection, source inspection, revocation
    and stale-response protection.
- path: engine/neuralweb/market_memory_retained_saved.py
  what: Preserve original packet and receipt with separately identified five-field
    feature projection.
verified:
- claim: Post-integration authorization, saved output, playback and restart behavior
    passed.
  command: python3 -m pytest -q tests/test_market_memory_retained_saved.py tests/test_market_memory_retained_saved_api.py
    tests/test_market_memory_retained_legacy_guard.py tests/test_market_memory_pit.py
    tests/test_market_memory_playback_api.py tests/test_deploy_update_self_heal.py
    -k "market_memory or import_cached_module_triggers_api_restart"
  result: 249 passed in41.50s;141 unrelated cases deselected.
- claim: Page and auth/state contracts pass.
  command: python3 -m pytest -q tests/test_build_market_memory_page.py
  result: 22 passed in6.21s.
- claim: Synthetic functional and canonical visual matrices are complete.
  command: U1_browser_matrix.cjs and the repository browser capture helper over the
    actual-owner synthetic fixture server.
  result: 24 functional cells and72 rest/hover/focus states; provenance is committed
    under mockups/evidence/market-memory-retained-u1.
unverified:
- claim: Installed authenticated production interface works.
  what_would_verify: Normal hosted CI and merge, installed hashes and actual authenticated
    browser verification of all three modes and redaction.
unresolved:
- Same-tab OAuth intent recovery passes source and browser fixtures; the actual provider round trip remains open.
- Full28-task/49-case program, operational E0 and actual outcome labels remain open.
next_actions:
- Repair hosted findings on PR9228, preserve dependency9181 and take protected release
  through installation.
- Verify actual browser flows and continue L0/E0 source and science work.
do_not_redo:
- Do not reopen August ABSTAINED results or restamp immutable source/experiment evidence.
- Do not replay original Fabric recovery operations or reset root allowance.
danger_areas:
- Fixture evidence is not production acceptance.
- Retained source denial must never fall through to W1A.
prs:
- 6528
- 9170
- 9181
- 9228
---

# Market Memory retained capture and saved-output delivery

Original root: `01a1333c-a475-7052-95a8-72c623fb12e1`. Program remains the full 28 tasks / 49 acceptance cases; parent PR #6528. This handoff records a delivery checkpoint, not program completion.

The retained interface now supports exact historical capture selection, current contextual comparison, and original saved output. Selection preserves generation ID/hash, query, context, capture, subject and cutoff. Source inspection exposes five authorized house values and exact citation spans. Saved output preserves the original packet and receipt while returning an explicitly named feature projection; a projection is never presented as the original full feature bytes. Unknown feature states remain unknown.

Current source authorization runs before trusted payload reads and again before disclosure. The legacy context, as-known-at and playback catalogue routes use the same request-local guard; a source refusal cannot fall back to W1A. Genuine trusted misses preserve W1A behavior. Request reads share the 64MiB owner budget. New retained API modules participate in the incumbent updater's API restart trigger.

Reviewed source includes installed lineage #9140 and consumers #9170, and builds on Research Factory PR #9181. No protocol code pins or incumbent CI jobs were removed. Hosted release and runtime acceptance remain separate from this checkpoint.

## Evidence

- 249 post-integration saved-output, authorization, PIT/playback and import-cache restart checks passed (41.50s).
- 22 page/auth/state/Node-wrapper tests passed (6.21s), including independent state-transition probes.
- Two post-integration CI dependency/ownership checks passed (324.86s).
- 24 functional fixture browser cells cover historical/current/saved × dark/light × EN/ZH × 1440/390. No page errors or horizontal overflow occurred.
- `mockups/evidence/market-memory-retained-u1/` contains the canonical 72-state rest/hover/focus matrix, manifest, dual-theme receipt and explicit synthetic-fixture assurance.
- Design-system, runtime-style and visual-evidence checks passed. Generated asset references use the existing optimizer.
- The browser fixtures come from actual owner APIs over synthetic private stores. They prove the consumer contract, not production population or current-user entitlement.

## Remaining acceptance

Normal hosted CI, protected merge, installed source hashes, and authenticated production browsing remain owed. Prove the three modes through the actual browser, current revocation/sign-out redaction, stale-response suppression and actual saved-output source inspection. Same-tab OAuth intent recovery now passes the strict URL/capsule tests and 20 Chromium callback/refusal fixtures; a real provider round trip remains separately open. Natural source capture and later outcome labels are not inferred from synthetic fixtures.

The four-run recovery packet reached Fabric Integration. Original D0 bytes were recovered and reviewed; defects were repaired in this carrier. Ubuntu0 publisher recovery is refused by its original directory ownership/mode control, with siblings held on that owner path. No carrier switch or duplicate worker occurred. Separate L0 metadata work proceeds after a proven prelaunch Fabric disk-admission failure; no actual labels have been read.

## Exact catalog locator and hosted-CI repair

An exact citation can refer to a capture outside the first catalogue page. The API now accepts a strictly paired query/context locator only with the exact generation ID/hash and offset zero. It locates that pair inside the already authorized pinned population and returns its ordinary page. The client retains the returned offset only after its complete identity checks; an absent pair never substitutes another capture. Five new backend cases and two actual-module state cases cover this path (25 catalogue tests, 12 state cases and 28 adjacent owner tests passed).

Hosted run 38523488771 on 519b137be1fcd1802e67919fb40a921e080bf7bc exposed stale emitted research-screener asset stamps, missing emitted CSS tokens after main integration, and theme-dependent HK/CA proof bindings. The canonical emit/copy/optimizer paths repair those bytes. Both stock-dashboard verifier runs actually passed again on the final source; their receipt and manifest bindings preserve the historical baseline. Template/site sync covers 118 pairs. The final affected asset/receipt suite passed 168 tests and all 20 OAuth browser fixture cases passed again. UI visual-evidence, design-system and P0B closure gates passed. These are local source/fixture results; the next pushed head still owes its own hosted CI, installation and live consumer proof.


## Current-main CI count integration

Exact UI head b3f9739 passed eleven hosted packs; pack zero failed only the packing count regression (643 other contract cases passed). The tested merge included two new Leadership Rotation jobs. Full inference on the current-main union 44cc567d1edf retains all 313 jobs and measures 136/134/130 selected jobs, weights 5678/5475/5441 and ten packs on all probes. Only the template and Prophet job-count ceilings are funded by one for the measured entrants; all suites, dependency scopes, weight limits and runner limits remain unchanged. The thirty expected UI/runtime asset hashes are byte-identical after this main integration. No new product or production claim follows from this CI repair.
