---
workstream: "WS:MARKET-OS"
session: sol/market-os-shared-shell-design-20260924
model: sol
ended_because: checkpointed_continuation
mission: >
  Deliver instantly understandable shared navigation with advanced depth and long-page
  reading. All tools is mega-menu first; full directory browsing remains available.
state_before: >
  R26 completed the native desktop mega-menu content but the original Paper file again
  emitted an explicit further-writes-may-cause-data-loss warning. The source-fed R23
  component remained a default-OFF research package rather than the shared product header.
changed:
  - path: "paper:01M2WGNCX9475G79JRKJTCM08P/p-D-0/3MNS-0"
    what: >
      R27 performed read-only reconciliation only. The desktop design remains visible;
      the file-specific capacity warning repeated, so no R27 canvas mutation was sent.
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
  - claim: Broad unaffected product-chrome behavior remains green except explicit holds.
    command: >
      Targeted pytest set across product chrome, navigation refresh, nav hover, account,
      controls and adjacent navigation packs, excluding six named known assertions.
    result: "230 passed, 6 deselected, 4 deprecation warnings."
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
      Resolve the held release-test constants, run the full unexcluded suite and CI,
      then real three-page browser/device/theme/locale/focus/overlay and cold-reader proof.
  - claim: Safe further Paper writes.
    what_would_verify: >
      Existing preservation/capacity owner establishes the original file's saved-state
      health, applicable limit and supported safe recovery. No R27 mutation tested it.
unresolved:
  - Paper's warning remains file-specific and active; actual loss, numeric threshold and cause are unknown.
  - Production cache key is now 20260929-all-tools-menu and computed nav payload digest is 52711a9a.
  - Existing tests still pin 20260913-account-actions / 7f766d93. The exact edit to update
    those three constants was explicitly blocked before dispatch; EFFECT_NONE, no retry or alternate carrier.
  - Five cache-key assertions therefore remain intentionally failing; a sixth deselected baseline
    assertion in test_navigation_refresh is unchanged on current main and unrelated to this feature.
  - Native phone/light menu states and remaining design refinements are still outstanding.
  - R18/R19 and PR7129 persistence-before-rebind obligations remain separate.
next_actions:
  - On a permitted source-write surface, update only:
      tests/test_nav_hover_bridge.py NAV_RELEASE_KEY=20260929-all-tools-menu,
      NAV_PAYLOAD_DIGEST=52711a9a; tests/test_account_actions.py
      RELEASE_KEY=20260929-all-tools-menu.
  - Run the full targeted suite without exclusions, then consume exact-head CI/review. Keep PR7949 Draft/HOLD.
  - Prove the menu in real browsers on macro.html, sector_central.html and reports.html before any wider enablement.
  - Resume exact existing Paper nodes only after supported original-file capacity recovery; do not recreate the menu.
do_not_redo:
  - Keep PR7949, branch sol/market-os-shared-shell-design-20260924 and the existing WS owner.
  - Preserve R26 canvas effects, R23 source semantics and the incumbent navigation catalogue; no replacement registry/header/assets.
  - Do not replay the refused release-test edit through another tool/carrier in the unchanged refusal state.
  - Do not treat the Paper capacity warning as a generic page-concurrency or M1/M2 issue.
  - Preserve full-directory fallback, stock search, native anchor behavior and exact regional/deep-link destinations.
danger_areas:
  - PR remains draft and not release-ready; the candidate deliberately carries five stale release-test assertions until lawfully updated.
  - Full build generated extensive live-data churn during proof; all unrelated build output was restored before checkpoint.
  - Browser proof was not retried because its prior administrator gate has not materially changed.
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
preferences. The existing theme→account→nav asset chain is retained. Its production release key was
moved to 20260929-all-tools-menu; required legacy test constants are the only held source repair.

Current-main dashboard/Prophet companion bytes were joined only where required to preserve current
source compatibility. They create no PR diff against current main. Static pilot pages were restored to
current-main bytes before inserting only the 45-line rendered dialog host, avoiding live-data build churn.

## Proof and explicit negative results

Fresh production-byte Node result:97pass/0fail. Fresh integration test:8pass. Fresh broad unaffected
suite:230pass/6deselected. All production template/site pairs and the theme emitter match. Reports and
Sector builders completed. The 23-minute full build is not green: after rendering macro, it hit a
current-main stocks-helper mismatch in the sparse branch environment; the later fast renderer also lacks
a stocks helper global. These failures do not prove the menu defective and are not hidden as success.

An attempted exact update of the release-key/digest constants was blocked by the platform before dispatch.
No file changed. Under current refusal law this turn did not rephrase, change carrier or make a second
attempt. The current source payload digest after whitespace repair is52711a9a. Until those assertions are
lawfully updated and the unexcluded suite is green, the candidate stays Draft/HOLD.

Paper readback again emitted the explicit file-too-large/further-writes-data-loss warning. No R27 Paper
write, cleanup, finish-marker or carrier failover occurred. Last durable canvas effect remains
shared-shell-r26-confluence-icon-015; native capacity return remains Mastermind927/5884704203.

No merge, deployment, feature enablement outside the three committed pilot pages, account/watchlist/
Portfolio/alert/trade effect, worker, watcher or autonomous continuation exists.
