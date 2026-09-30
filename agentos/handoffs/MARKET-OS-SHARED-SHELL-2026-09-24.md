---
workstream: "WS:MARKET-OS"
session: sol/market-os-shared-shell-design-20260924
model: sol
ended_because: checkpointed_continuation
mission: >
  Deliver instantly understandable shared navigation with advanced depth and long-page
  reading. All tools is mega-menu first; full directory browsing remains available.
state_before: >
  R31 completed the mobile All tools directory, search, no-match recovery and light-theme
  parity on the original Paper carrier. The source-fed pilot was joined to the incumbent
  shared header, but five release-cache assertions still pinned the superseded key/digest.
changed:
  - path: "paper:01M2WGNCX9475G79JRKJTCM08P/p-D-0/45–50"
    what: >
      Completed the mobile All tools directory, search-results and no-match recovery family
      in dark and light themes, then updated the shared journey/state map. These are design
      states of the existing route contract, not runtime navigation or production proof.
  - path: "templates/_all_tools_menu.html.j2 + incumbent shared navigation assets"
    what: >
      Integrated the source-fed All tools dialog through the existing common header,
      navigation-refresh.css and nav_market.js owners. No standalone runtime asset,
      route registry, preference store or duplicate header was introduced.
  - path: "macro / sector_central / reports pilot"
    what: >
      Added strict default-OFF opt-in for exactly the macro overview, Sector Central and
      Research Reports index. Stocks and report-detail pages remain off. Committed pilot
      HTML contains one host/dialog/trigger each.
  - path: "tests/test_nav_hover_bridge.py + tests/test_account_actions.py"
    what: >
      Updated only the three release-contract constants to the shipped key
      20260929-all-tools-menu and payload digest 52711a9a. Production assets were unchanged.
verified:
  - claim: Production controller behavior remains source-driven and fail-closed.
    command: >
      Extract controller bytes from templates/nav_market.js; node --test navigation,
      controller and refresh-boundaries suites.
    result: "97 passed, 0 failed."
  - claim: The source/template/static-page integration is internally coherent.
    command: >
      tests/test_all_tools_menu.py; template/site byte-pair checks; theme emitter check;
      scripts/check_template_site_sync.py; git diff --check.
    result: >
      8 integration tests passed; nav/CSS/account pairs match; theme emitter matches;
      105 template↔site pairs pass; diff check passes. Pilot host counts are 1/1/1 and
      us_stocks is 0.
  - claim: The complete targeted product-chrome contract was run without exclusions.
    command: >
      237 collected tests across account actions/preferences, navigation refresh, nav hover,
      product chrome, nav icons, wide-menu anchor and sector links.
    result: >
      236 passed, 1 failed, 4 deprecation warnings. The only failure is
      test_start_hub_uses_canonical_product_navigation_and_demotes_clock; both its test file
      and scripts/build_vector.py are byte-identical to current origin/main, so it is a
      current-main baseline red unrelated to the three-constant repair.
  - claim: Actual builders consume the shared host.
    command: "python -m scripts.build_reports; python -m scripts.build_sector_central; full build_site attempt"
    result: >
      Reports and Sector Central builders completed and emitted one host each. Full build
      rendered macro.html with the host, then failed in the stocks route on current-main
      Prophet helper compatibility. Exact companion templates were joined from current
      main; render_macro_fast rendered macro again but its reduced environment lacks
      us_stance_projection for stocks. The pilot-off stocks contract is covered by source
      and committed-page tests; no full-build-green claim.
unverified:
  - claim: Production/browser/accessibility acceptance.
    what_would_verify: >
      Consume exact-head CI/review, then complete real three-page browser/device/theme/
      locale/focus/overlay and cold-reader proof on the admitted pilot pages.
  - claim: Permanent resolution of the historical Paper capacity warning.
    what_would_verify: >
      Supported provider/file diagnostics establish the saved-state health and applicable
      limit. R31 writes and scoped cleanup succeeded without a returned warning, but that
      successful batch does not by itself identify or permanently clear the earlier cause.
unresolved:
  - The historical Paper capacity warning is not root-caused. R31 writes succeeded without a returned
    warning, which is not proof that the underlying file-limit condition is permanently resolved.
  - One unexcluded navigation-refresh baseline assertion remains red on current origin/main and this branch.
  - Exact-head CI/review and real-browser acceptance are still owed; no production-release claim exists.
  - R18/R19 and PR7129 persistence-before-rebind obligations remain separate.
next_actions:
  - Push the existing branch and verify the remote head matches the local cumulative checkpoint.
  - Consume exact-head CI/review while keeping PR7949 Draft/HOLD; adjudicate any branch-owned failure.
  - Prove the menu in real browsers on macro.html, sector_central.html and reports.html before any wider enablement.
  - Preserve Paper boards 45–50 and refine exact existing nodes only; do not recreate the menu family.
do_not_redo:
  - Keep PR7949, branch sol/market-os-shared-shell-design-20260924 and the existing WS owner.
  - Preserve R26 canvas effects, R23 source semantics and the incumbent navigation catalogue; no replacement registry/header/assets.
  - Do not redo the accepted three-constant release-contract repair unless the production key or payload changes.
  - Do not treat the Paper capacity warning as a generic page-concurrency or M1/M2 issue.
  - Preserve full-directory fallback, stock search, native anchor behavior and exact regional/deep-link destinations.
danger_areas:
  - PR remains draft and not release-ready; local verification does not substitute for exact-head CI/review or browser proof.
  - Full build generated extensive live-data churn during proof; all unrelated build output was restored before checkpoint.
  - The remaining navigation-refresh failure is baseline debt, not permission to hide it or expand this repair into build_vector.py.
---

# R27 — source-fed mega menu joined to the shared product header

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION
MISSION_COMPLETE: false
EFFECT_UNKNOWN: none
ACTIVE_PHASE: Source adoption, exact release-contract repair and real-path proof.

## Exact identities

Protected procedure: Mastermind@39d0bfd55bf19c2c27322ec691189e63df201c15,
INDEX blob94d1af402598894372858793a5b1931019c5fa77, compatible1.0.1/bootstrap1.
Macro PR7949, branch sol/market-os-shared-shell-design-20260924.
Feature commit cf5d546a17a80832cf2b5edb77e67b36074e5ac0; current-base merge/checkpoint head
111860be99c2e5a03fe9e61681833ebf28be2b70.
Candidate worktree: /Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27.
Current relevant-source compatibility checked against main@744a5b75e8d19db9ec6e0df0542c3123f67d6866;
movement from the earlier observed main revision did not touch the joined navigation/pilot paths.

## Capability delta

Before: All tools was a Paper design plus a default-OFF research component, so users still had to
use the older directory/page path and no common-header pilot consumed the source-fed controller.

After: the existing common product header can render one native dialog host, and the incumbent
nav_market/navigation-refresh owners project the current canonical navigation catalogue into it.
Macro overview, Sector Central and Reports index are the only opted-in families. Search, categories,
locale, focus restoration, disabled/withdrawn destinations, deep links, same/new-tab behavior and
sanitized source SVG shapes stay under the tested existing component contract. Full directory browsing
remains available in-panel. This is BUILT_NOT_PROVEN, not a live release.

## Source boundaries

New host: templates/_all_tools_menu.html.j2, included once after the shared nav. It contains no
standalone CSS/JS URLs and stays hidden/default-OFF without explicit boolean opt-in.
Presentation is appended under ALL_TOOLS_MATERIAL_V1 in template/site navigation-refresh.css.
Behavior is appended under ALL_TOOLS_CONTROLLER_V1 in template/site nav_market.js.
The controller snapshots incumbent anchors at opening; it does not author destination copies or persist
preferences. The existing theme→account→nav asset chain is retained. Its production release key is
20260929-all-tools-menu; the legacy test constants were repaired in f7b2244de881 without changing assets.

Current-main dashboard/Prophet companion bytes were joined only where required to preserve current
source compatibility. They create no PR diff against current main. Static pilot pages were restored to
current-main bytes before inserting only the 45-line rendered dialog host, avoiding live-data build churn.

## Proof and explicit negative results

Fresh production-byte Node result:97pass/0fail. Fresh integration test:8pass. The full 237-test
contract ran without exclusions:236pass/1 current-main-identical baseline failure/4 warnings. All production
template/site pairs and the theme emitter match. Reports and
Sector builders completed. The 23-minute full build is not green: after rendering macro, it hit a
current-main stocks-helper mismatch in the sparse branch environment; the later fast renderer also lacks
a stocks helper global. These failures do not prove the menu defective and are not hidden as success.

The exact release-key/digest repair is now committed as f7b2244de881. Its red-first run reproduced
all five stale-contract failures; the same five tests then passed after only the three constants changed.
The remaining unexcluded failure is byte-identical to current origin/main and is preserved as baseline debt.
The candidate stays Draft/HOLD until exact-head CI/review and real-browser acceptance are complete.

Paper readback again emitted the explicit file-too-large/further-writes-data-loss warning. No R27 Paper
write, cleanup, finish-marker or carrier failover occurred. Last durable canvas effect remains
shared-shell-r26-confluence-icon-015; native capacity return remains Mastermind927/5884704203.

No merge, deployment, feature enablement outside the three committed pilot pages, account/watchlist/
Portfolio/alert/trade effect, worker, watcher or autonomous continuation exists.

# R32 — release-cache contract repaired; exact-head review remains held

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION
MISSION_COMPLETE: false
EFFECT_UNKNOWN: none
ACTIVE_PHASE: Exact-head CI/review, then admitted-pilot browser acceptance.

Protected procedure was repinned to Mastermind@82a0edf482e694ce6c619022bc2f54cddae50e35,
INDEX blob 94d1af402598894372858793a5b1931019c5fa77, compatible 1.0.1/bootstrap 1.
Source carrier remained the locked existing worktree and original PR7949 branch. Current origin/main was
observed at a4fd495669f21e78a6a734b41a21127722af16bc; it did not change either repaired test file before the edit.

Commit f7b2244de881 changes exactly three constants in two tests: NAV_RELEASE_KEY and RELEASE_KEY now equal
20260929-all-tools-menu, and NAV_PAYLOAD_DIGEST equals 52711a9a. No production asset, pilot flag, route,
registry, preference, page output or runtime behavior changed.

Fresh verification on the resulting tree:
- red-first focused contract: 5 failed for the stale key/digest, exactly as expected;
- focused rerun after repair: 5 passed;
- complete targeted collection: 237 tests, no exclusions; result 236 passed / 1 failed / 4 warnings;
- remaining failure: test_start_hub_uses_canonical_product_navigation_and_demotes_clock;
- tests/test_navigation_refresh.py blob cdc820d156c12e10cc0b242cb3b426ae0e2e654a and
  scripts/build_vector.py blob c5a5be0b5be3e48155f2f8d43b86e7356e0ba859 are identical on HEAD and current origin/main;
- production-controller Node suite: 97 passed / 0 failed;
- shared-host integration: 8 passed;
- template↔site sync: 105 pairs checked / PASS;
- git diff check: PASS.

The source repair is locally proven but not a release. Keep PR7949 DRAFT/HOLD. Exact next action is to push
this same branch, verify remote identity, consume exact-head CI/review and repair only branch-owned failures.
After source admission, prove macro.html, sector_central.html and reports.html across real device/theme/locale/
focus/overlay paths. Preserve Paper boards 45–50 and the journey map; no replacement board family or second
navigation/search authority.
