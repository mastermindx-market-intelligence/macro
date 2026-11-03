# Intraday Flow R2 — recovery design and implementation proof

Recorded 2026-11-03T04:27:57.506086+00:00. Original PR10498 remains Draft/HOLD.
This is local candidate evidence, not independent review, hosted CI or served acceptance.
Predecessor: f29d69e431bbc97f89ae8f4486618f5ebde7597b.
Plan/spec commit: e3a9364713e9330be738caa7a6bf5e1452c3581f.
Material source identity: the commit containing this record; no self-referential hash.
HTML SHA256: `a25bcf188e95ac9ac8705d6ae776fb10e52a214ee74344abd1d93b8abc4ce60b`.

## Capability changes

- Clear search removes only the query, preserving theme, setup, grouping, sort and keyboard place. Reset all filters remains separately available.
- Empty recorded watchlist is explicitly unavailable, with a true page-reload action, em-dash setup counts, consistent inspector/footer and no false zero or blank scan body.
- Filtered-empty state stays distinct, escapes and wraps hostile/long Unicode queries, and exposes stable focus targets through async refresh.
- New recovery actions have 44px touch targets. Phone actions stack left of the existing assistant column; actual browser bounds are at or left of x315.
- No classification, freshness, producer, polling, shared-navigation, authentication or publication logic changed. The 15 protected model functions match the predecessor byte-for-byte.

## Verification and adverse controls

1. RED: `python3 -m pytest tests/test_intraday_flow_recovery_ux.py -q --disable-warnings --tb=short` on predecessor product: 16 failed, 2 passed. Missing helper/action/style and unavailable-count assertions failed as intended (`/tmp/intraday-r2-red.log`).
2. Focused GREEN: same command, 18 passed.
3. Scoped regression: `python3 -m pytest tests/test_intraday_flow*.py tests/test_workflow_file_size.py -q --disable-warnings --tb=short` — 301 passed, 12 warnings. First integration run exposed five legacy DOM fixture failures: fake table rows existed while the fixture declared leaders=[]; makeLead now populates the fixture list. All existing assertions retained; no production accommodation or weakened checks.
4. Existing browser suite: `verify_browser.py` against an owned ephemeral loopback server — 515/515 passed, report browser_verification_r2.json.
5. New recovery browser matrix: `verify_recovery.py` — 244/244 passed, 16 screenshots, all SHA256s verified. Desktop/phone × light/dark × EN/ZH; normal combined filters plus isolated empty-watchlist fixture.
6. Visual review found floating-assistant overlap missed by the first 232-check run. A new red browser clearance check reproduced action right-edge343px at width390; the CSS repair places every action at or left of315px. The subsequent244-check run passed.
7. Paired CSS equality, inline JavaScript `node --check`, 15-function predecessor comparison, `git diff --check` and added-diff design-system guard pass (zero new blockers).

Full-repository pytest was not run: this is an owned sparse monorepo worktree, and normal hosted CI supplies broader integration. The actual scoped result is stated rather than mislabeling it full-suite. Existing shared-navigation desktop CLS remains unresolved.

## Paper alignment

Exact file01M2WGNCX9475G79JRKJTCM08P, pagep-26-1. Existing empty-state board6ZK3-1 retained, not duplicated. Guarded direct-app operations:
- intraday-r2-empty-copy-c2-01: text6ZL8-1,6ZL9-1,6ZLE-1 shortened/clarified; second action now Reset all filters.
- intraday-r2-empty-actions-c2-01: action group6ZLA-1 stacks with44px right reserve; both actions minHeight44px; first uses existing dark tokens.
- intraday-r2-empty-finish-c2-01: working indicator released.
All three returned APPLIED_RESPONSE_OBSERVED; screenshot inspected; computed-style readback confirmed direction/width/target dimensions/tokens. This is principal design inspection, not independent visual acceptance.

The previously platform-denied dark-Chinese ticker-row batch remains held and was not retried. Other Paper boards remain samples with stated gaps, not newly claimed complete coverage.

## Data and release fences

Base snapshot unchanged: a8b0f3d6609b844f4e88ba9155414196773e3fb11f04031a3b02cfc192ddc624. Embedded BASE_DATA equals that committed source. Canonical write_page plus make_optimizer used; optimization idempotence verified. No producer run. Recovery images use actual recorded board for search or explicitly named empty-watchlist browser-only TEST FIXTURES; no market observation fabricated or written to feeds.

Next: canonical final source capture, independent exact-candidate source review, current-head CI, remaining Paper/qualified visual and shared-navigation gates. No merge, Ready, un-draft, enqueue or deployment.

## Canonical capture and independent-review request result

Fresh recovery-r2-canonical capture at material source55b651320d79f5a4ebf530eeb0175803b981baaa completed24/24 with all image hashes valid, zero console/response errors and no horizontal overflow. Added visual receipt passed.

Distinct source-review request intraday-recovery-r2-review-20261103-c2-01 was refused before launch by the existing Fabric owner. Controller94761 returned MMX_FABRIC_EXIT=75; status is REQUEST_REFUSED_BEFORE_LAUNCH / EXECUTION_NOT_ELIGIBLE; no result, no reviewerSTART, retry_allowed=false and same_run_replay_allowed=false. No exact causal explanation beyond that classification was returned. It has not been retried, accepted, replaced or routed around. This is not an independent review pass.

Final repeated scoped regression on the committed material source:301 passed,12warnings,14.96s; controller4403 exit0. Visual-receipt validation controller89865 exit0. Both are observed results, not pending promises.
