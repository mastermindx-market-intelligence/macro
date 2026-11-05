---
workstream: WS:PROPHET-US-V4-RECOVERY
session: 01a11e89-b35d-7a81-9404-5fce2c6170cb / sol/prophet-daily-brief-compositor-20260930
model: codex
ended_because: ci_handoff
mission: Complete the existing four-market Daily Desk through native evidence and authenticated production
  journeys. Repair the original Daily Brief compositor after the human explicitly chose PR8249 and reopened
  its source repair.
state_before: Original PR8249 at873ebc4c retained a40-line malformed-input regression diff and three existing
  variants. The human selected this original implementation, preserving the other variants and native
  owner/selection obligations.
changed:
- path: engine/prophet_daily_brief.py
  what: Harden malformed owner inputs, preserve independent latest quote and B4 clocks, reject stale or
    incomparable equal-clock quote facts, derive health/decision after reason/blocker validation, and
    suppress unusable Plan relations.
- path: tests/test_prophet_daily_brief.py
  what: Preserve the original dirty regression functions and add independent quote, malformed owner, inconsistent
    Plan, and review-discovered fail-closed discriminators.
- path: .github/ci/legacy-jobs.yml
  what: Preserve the original Daily Brief code proof together with current-main expanded strategy and
    MI-S2 registration steps during integration.
prs:
- 8249
verified:
- claim: Original dirty malformed-input regression functions and decorators were preserved.
  command: Compare ASTs against daily-brief-preintegration-preserved-20261012/tests/test_prophet_daily_brief.py
    and retained original40-line patch.
  result: Four original dirty test functions/decorators are identical; original bytes retained before
    any source integration.
- claim: The first independent review identified two real defects, which the parent reproduced before
    fixing.
  command: python3 -m pytest tests/test_prophet_daily_brief.py -q -k "malformed_b4_lists_close_decision_and_health_before_presentation
    or same_clock_incomparable_b4_quote_cannot_authorize_latest_price"; retained exact command and results in
    daily-brief-review-findings-parent-red-20261012.log.
  result: Nine RED failures on the reviewed source,130 intentional deselections; malformed B4 lists and
    incomparable equal-clock quote facts no longer retain an entry-cleared decision after repair.
- claim: The corrected compositor passes on actual current-main dependencies.
  command: Merge f65b8376395d8ea9a619acbd58cf9a7dee4ed835 normally on the original carrier; python3 -m
    pytest tests/test_prophet_daily_brief.py -q.
  result: 139 passed, zero skips or deselections,13.39 seconds. Source7e1b10cedc53124efa7ea8ed7d15ce66bdc3a61995b22f9870372fe9cf73dcaf;
    test49390edd6128125b00e4728c5282c75c2049231cfdb908180049f0c91e03f8a3.
- claim: Corrected-source independent review approves the supplied bytes within its declared scope.
  command: fabric_task.py result and accept prophet-daily-brief-corrected-review-01a11e89 --by reviewer;
    canonical status readback and daily-brief-corrected-review-adjudication-20261012.json.
  result: APPROVE and original-root/parent VALIDATED_OUTCOME. Reviewer independently recomputed all six
    source/test/dependency hashes and inspected the two repaired paths plus adjacent cases. Retained report
    is 8218 bytes. Missing engine.stock_identity prevented full imports; a disclosed three-name helper
    import stub supported only narrow helper probes. Parent 139 actual-dependency tests remain separate.
- claim: Materialized current-main CI planner checks and inferred owner selection pass.
  command: python3 -m pytest tests/test_ci_pack.py::test_real_manifest_has_non_vacuous_derived_scopes
    tests/test_ci_pack.py::test_curated_exclusive_scopes_cover_their_own_import_closure -q;
    canonical infer_job_scopes and select_jobs for the two owned source/test paths.
  result: 2 passed in 277.56 seconds. Canonical planner selects washout-turn-organ for each path after
    inference across the 210-code-job manifest. The original missing-hook sparse-checkout failure is
    preserved separately. Hosted authoritative plan and final semantic evidence remain required.
- claim: Released object comparison and current main compose without changing the reviewed Brief subject.
  command: git merge --no-ff --no-commit a278075e6197e12ae13d37354813dccd9e70043a;
    compare exact bytes of the two reviewed files and four dependencies to fc165a8b29fd97750e7716ad6f45ba9e117d21b8;
    rerun the two affected canonical planner tests.
  result: Only the shared workstream narrative conflicted; both histories are preserved with an accurate
    current prefix. All six reviewed files are unchanged. Both planner checks pass again, and the existing
    washout-turn-organ owner remains the inferred execution owner. No new source review is needed for
    unchanged reviewed bytes. PR8874 is merged to a278075e6197; its 88 logical jobs and 310 passing proof
    steps are closed evidence. Brief exact-head hosted checks remain separate.
unverified:
- claim: Exact-head hosted CI, source release and product integration are complete.
  what_would_verify: Normal exact-head semantic CI and merge; then native producer provenance/access
    binding and authenticated Daily Brief journey.
unresolved:
- Today/standouts already owns candidate selection/order in scripts/build_stock_library.py::main. Current
  rows lack the four-field native candidate binding. The actual producer must issue provenance for its
  unchanged selection once native binding exists; the consumer cannot invent it.
- Ticker-keyed plan_relation is UI context only, not Task2 native Plan evidence. Do not extract served
  assessment/evidence from private Lab. Canada native Plan remains unavailable until its owner exists.
- 'The old Grok review returned a usable REJECT summary but its full artifact is not accepted: historical
  raw-to-normalized capture binding is unavailable. New corrected-source review is a distinct subject;
  no replay of the old generation.'
next_actions:
- Publish this original reviewed branch and consume normal exact-head release gates.
- Complete actual native owner/selection bindings before integrating the Brief into the four-market product;
  preserve all other custody/refusal gates.
do_not_redo:
- Do not create a fourth assembler, ticker-join candidate generations, synthesize owner/review receipts,
  or add a second selector.
- Do not retry closed old Fabric artifacts or reopen accepted B03/Return/source/runtime checks.
- The human approvals supersede only P1a8444 integration refusal6029541334 and original DailyBrief8249
  source repair refusal5924461491; all other holds remain.
danger_areas:
- Latest quote cannot renew B4, assessment or Plan clocks, recompute entry policy, or create ranking/trading
  authority.
- String/schema validation does not authenticate native provenance or access; the eventual caller retains
  that responsibility.
- Source acceptance is narrower than product availability or four-market production acceptance.
---

This repair preserves the original Daily Brief carrier. The existing programme checkpoint remains https://github.com/mastermindx-market-intelligence/macro/issues/6817#issuecomment-6107291350.
