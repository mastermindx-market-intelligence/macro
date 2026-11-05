---
workstream: WS:MARKET-OS
session: claude/ssd-b-f06-exposure-integrity-20261013-04c36efca0280ee5
model: codex
ended_because: blocked
mission: B-F06-4 Research Screener Exposure read integrity through protected publication and actual
  live proof. B retains F06-F13/J1; A retains F01-F05/F00C.
state_before: Macro6819 comment6150182000 identified dormant WatchStore returning anonymous local
  holdings despite an MDXAuth session, and uncertain reads presented as empty. Original proposal bytes
  were unavailable; the new implementation is independently qualified.
changed:
- path: templates/research_screener.html.j2
  what: Fence holdings by session, real store owner, store identity, request generation and cloud-ready
    read state. Distinguish signed-out, unavailable, loading and degraded; preserve ordinary lenses
    and only filter verified holdings.
- path: tests/test_research_screener.py
  what: Execute the real inline script with Node stdlib. Exercise actual dormant WatchStore, cloud
    faults, identity/readiness races, all-closed portfolios, late boot and lens/order behavior.
- path: site/research_screener.html
  what: Full bake from the unchanged committed two-name payload. Normal live.js stamp correction is
    already present on current main; theme remains untouched.
- path: .github/ci/legacy-jobs.yml
  what: Add templates/watchstore.js to the existing research-screener scope; existing CI Node20 supplies
    the harness runtime.
verified:
- claim: Current local full Screener suite passes.
  command: python3 -m pytest tests/test_research_screener.py -q
  result: 51 passed; includes 19 Exposure test functions.
- claim: The Exposure tests discriminate the original defect.
  command: PYTHONPATH=<evidence-root>:$PWD python3 -m pytest tests/test_research_screener.py -q -k
    exposure -p f06_red_baseline
  result: 14 failed / 5 passed against the original HEAD template; same tests are green on the repair.
    The real no-host seeded local-book test is among the red cases.
- claim: Parent found and repaired five candidate gaps before publication.
  command: python3 -m pytest tests/test_research_screener.py -q -k "closed_only or resolved_loading
    or both_public or refresh_invalidates or cache_belongs"
  result: Five new regressions failed on the returned candidate; all pass after parent corrections.
- claim: Committed payload, WatchStore and theme source are preserved.
  command: Compare file bytes with git show HEAD:site/research_screener.json and HEAD:templates/watchstore.js,
    HEAD:templates/theme.css, HEAD:site/theme.css
  result: All byte-equal. Payload SHA256 763e2b5477359116d599a0c6d82e54f5eecb9feb68151d7cd39aa9091741bf6c.
- claim: No uncovered dependency in the changed Screener job.
  command: load_legacy_jobs; infer_job_scopes([replace(research_screener_job, exclusive=False)]);
    _matches_any(declared_paths, inferred_path)
  result: uncovered []; existing Node20 CI runtime verified.
- claim: Added-line design and runtime style guards pass.
  command: python3 scripts/check_design_system.py --mode enforce-added --diff-file <candidate-diff>;
    python3 scripts/check_runtime_style_injection.py; git diff --check
  result: 0 blocking design findings; runtime injection allowances unchanged; diff clean. No visual
    acceptance is implied.
- claim: Mixed malformed books never establish a complete or empty holding set.
  command: python3 -m pytest tests/test_research_screener.py -q -k partial_malformed
  result: 'Failed before the parent repair; passes afterward for mixed open/junk and closed/junk books.
    Full current suite: 51 passed.'
- claim: The original independent review was consumed and accepted once as a diagnostic outcome.
  command: fabric_task.py result b-f06-exposure-review-01a128b7-v1; fabric_task.py accept
    b-f06-exposure-review-01a128b7-v1 --by reviewer; fabric_task.py status b-f06-exposure-review-01a128b7-v1
  result: TERMINAL rc0; ACCEPTED by reviewer with original root and parent. Retained text SHA256
    817ba095a031955bb950d66af8254ac53f327b329363d234cd03b21b07a9f8f0. Four logic findings
    were already covered by parent repairs. Repeated EN/ZH Portfolio invitation shortened; current
    markup already has a whitespace separator, so the missing-space claim is not current.
- claim: Review correction preserves full-page bake and behavior.
  command: Write bake_html(REPO, committed_payload) to site/research_screener.html; python3 -m pytest
    tests/test_research_screener.py -q
  result: 51 passed. Existing dormant-WatchStore test now also asserts the visible unavailable notice
    and Portfolio link; static and post-boot signed-out copy agreement is pinned. No CSS changed.
- claim: Hosted CI passed on the pre-copy-correction head 09e5fb3c581116f698759e2c95725d8a9980dcad.
  command: gh pr view 9191 --repo mastermindx-market-intelligence/macro --json headRefOid,statusCheckRollup
  result: All 12 packs, contract-delta, ci-gate, fence-pack, self-mod-fence and ci-authority/main
    succeeded in CI run 38492155965 and fence run 38492156003. This does not qualify a later head.
unverified:
- claim: Final-head CI and implementation-outcome acceptance.
  what_would_verify: Require concluded applicable checks after the review copy/test correction; then
    record the original implementation outcome once. Browser and live proof stay separate.
- claim: EN/ZH dark/light 1440/390 browser evidence and authenticated live repaired page.
  what_would_verify: Chris must first confirm the Chrome extension UI is dismissed/completed. Then
    resume the three saved task tabs, inspect real captures, and after protected merge verify deployed
    page behavior.
- claim: Protected CI, merge and live delivery.
  what_would_verify: Exact final-head required checks, ordinary protected merge, covering render/publication
    and actual live browser read. Draft/source tests are not delivery.
unresolved:
- Chrome refused reload at 2026-10-13T23:46Z because another extension UI is open. Chris was asked
  once; no repeat question or browser control without confirmation.
- Independent Qwen review is complete and accepted once as diagnostic work. Original implementation
  remains unaccepted pending final-head qualification; source stays on this single carrier.
- Three task tabs retain temporary viewport/preferences and are marked for handoff. Cleanup follows
  browser clearance; do not sign out the existing authenticated session.
- On head 09e5fb3c581116f698759e2c95725d8a9980dcad the separate codex/merge-queue-pilot check
  failed with context_active=false, inactive_base_context and allowed=true. Applicable main context
  and aggregate CI gate passed. No override or policy change; later heads require their own CI.
next_actions:
- Finish exact final-head CI and original implementation acceptance once. Original independent review
  is closed; no new review, result read or acceptance replay without a material source regression.
- Keep the carrier draft and unarmed until browser acceptance is complete. Once the existing browser
  gate is cleared, finish controlled matrix and then normal protected CI/merge/live proof.
- Restore local original ZH/dark and clear its tab-specific viewport override; verify live authenticated
  ZH/dark/1728x694 restoration and close only the three task tabs when proof is finished.
do_not_redo:
- Original implementation b-f06-exposure-adoption-01a128b7-v1 completed and exported once. Do not
  recreate it or confuse its new patch with the proposal hash.
- Original observe-run refused rc75 original_run_observation_unconfirmed. No current-output, recovery,
  alternate reader/carrier, cancellation or lease action.
- F12 PR980, J1 PR967, F11 evidence, PR931/935/939/941/946/947 and Terminal release-owner work remain
  closed. Historical unresolved Fabric runs stay frozen.
- Adjacent PR7849 at 722d2c5065574b83e7db02d597ff4b829c256e67 owns its theme source/cache stamp. Do
  not take over its carrier or adopt its unmerged theme stamp.
danger_areas:
- Unknown holdings never establish an empty portfolio. Loading null is a normal public WatchStore
  contract; all-closed is a valid verified empty.
- Readiness can change while the owner id remains constant; invalidate published and pending holdings
  on every existing auth/readiness refresh.
- Local controlled fixtures are not authenticated populated-cloud or production race proof; no portfolio/account
  writes are authorized here.
prs:
- 9191
---

# F06 Exposure repair continuation

Original root and assigning parent: `01a128b7-bd2b-7a91-891d-39d38f74ad55`.

The canonical local continuation is `/Volumes/Mastermind/evidence/marketontology-fabric-repair-01a128b7/CONTINUATION_RECEIPT.json`, entry `f06_exposure_integrity`. Its evidence root contains the original packet, retained stdout, export receipt, patch, red/green output and browser baseline. The implementation stdout SHA256 is `af9ac15449db8b97b3d1e7499c83e96406901283db252aeb11dc56c153f0b545`; exported patch SHA256 is `077970f0493852a14d1b8f21dd5fba64be525b964b5c1088244230322e33f1e7`. Export matched the advertised manifest; parent corrections and tests are separate from that original result. The independent review `b-f06-exposure-review-01a128b7-v1` is accepted once as diagnostic work. The implementation outcome still awaits final-head qualification; no browser, merge or live acceptance is claimed.

This is a partial delivery record. The MarketOntology programme remains incomplete.
