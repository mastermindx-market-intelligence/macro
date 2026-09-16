---
workstream: "WS:PROPHET-US-AVAILABILITY"
session: "sol/prophet-us-panel-authority-20260916-sol-001"
model: sol
ended_because: ci_handoff
prs: [7161, 7163, 7180, 7187]
discoveries:
  - DSC:US-PROPHET-TRACKED-PANEL-CACHE-OVERWRITE-20260916
mission: >
  Restore current-session US Prophet discovery end to end while preserving the
  existing producer, source-bound candidate, reader, publication and browser
  authority planes. Repair PR #7187 on its existing carrier and do not replace
  the separate PR #7180, #7161 or #7163 owners.
state_before: >
  PR #7187 was BUILT_NOT_PROVEN at c21c9be04bbf983bc22f8e3fe6075339bbc9ebef.
  It removed stale reader cache overlays and disclosed the source screen date,
  but its recurrence scan missed multiline path blocks, .yaml workflows and
  duplicate producer steps. Its new Agent OS records also failed schema validation.
changed:
  - path: PR #7187
    what: >
      The existing carrier now normalizes multiline/list cache paths, scans both
      workflow extensions, preserves duplicate producer multiplicity, repairs its
      Agent OS records, corrects operator-facing cache authority comments and
      composes current main history-preservingly. It remains draft and unaccepted.
verified:
  - claim: The carrier and related PR identities were reconciled before continuation.
    command: gh pr view 7187 --repo mastermindx-market-intelligence/macro --json headRefOid,state,isDraft,baseRefOid; git rev-parse HEAD origin/main
    result: >
      PR #7187 remained open/draft at c21c9be04bbf983bc22f8e3fe6075339bbc9ebef;
      the repair used the same branch and worktree with no replacement carrier.
  - claim: The three recurrence holes were discriminating REDs before implementation.
    command: >
      python -m pytest -q
      tests/test_daily_collect_commit_path.py::test_us_panel_cache_scan_splits_multiline_action_paths
      tests/test_daily_collect_commit_path.py::test_us_panel_cache_scan_includes_yaml_workflows
      tests/test_daily_collect_commit_path.py::test_duplicate_daily_panel_seed_steps_are_rejected
    result: "3 failed on the pre-fix implementation, then 3 passed after the minimal repair."
  - claim: The current-main composed source candidate passed its owning local matrix.
    command: >
      python -m pytest -q tests/test_daily_collect_commit_path.py
      tests/test_p0_prophet_candidate_board.py tests/test_render_run_size_cap.py
      tests/test_workflow_file_size.py tests/test_chat_nav_sync.py
    result: "76 passed at 2e891d108553dd1f7f8d4258dad8a700982457ef."
  - claim: Records, workflow syntax, chat navigation and differential CI contracts are clean.
    command: >
      python scripts/agentos.py validate; parse all .github/workflows/*.yml and *.yaml
      with PyYAML; python -m scripts.sync_chat_nav; python scripts/check_contract_delta.py
      --base a780b16f53ceb05944fedf04d20b3735182aab52
    result: >
      Agent OS reported 0 errors; 100 workflows parsed; chat nav sync was OK;
      contract-delta reported 0 introduced and 0 inherited findings.
unverified:
  - claim: The delivered exact head passes hosted CI and production browser acceptance.
    what_would_verify: >
      Same-head hosted checks, source review, #7180 composition, merge ancestry and a
      real completed-session producer-to-served-board browser receipt.
unresolved:
  - >
    PR #7180 remains open and overlaps daily.yml; #7187 must be composed after the
    producer/provenance carrier rather than silently superseding it.
  - >
    Linux pack execution is owned by the separate active CI-host recovery session;
    this carrier neither repairs nor bypasses that infrastructure.
next_actions:
  - >
    Consume the delivered #7187 exact-head checks and independent review. After #7180
    is accepted, recompose the two carriers on current main, then prove one real
    completed-session source-to-browser journey before any Ready or merge decision.
do_not_redo:
  - >
    Do not restore tracked US panels from Actions cache in reader workflows, remove
    the daily.collect seed owner, or replace the gitignored Russell same-run handoff.
danger_areas:
  - >
    A cache scanner that treats a multiline action path as one string or deduplicates
    producers by panel path can pass while the stale-overlay failure remains possible.
---

# US Prophet: source and publication recovery

## Mission and authority
Restore current-session US Prophet discovery end-to-end so the user sees the actual dated candidate screen, not an old board beneath a new shell. This continues `WS:PROPHET-US-AVAILABILITY` under the current Chairman’s explicit direction. The original implementation used Mastermind Skillpack pin `7642aea155d2817219135b24246b55c1d7611c66`; this repair continuation is governed by protected `master` at `0fe8074ff953b2ced9025ed40f0f66019c759967`. Executive OS owns lifecycle, Agent OS continuity, GitHub implementation, Slack transport. This handoff creates no new runtime Job, worker lease or queue.

## Verified frontier and existing carriers
PR #7180 / `sol/prophet-us-completed-session-sourcebound-20260915` now carries `99b9bc18ded963ed5e9b9a4864bfff88a8e1d5ba`: completed-session source-bound recovery plus the previously missing regression-suite registration. 192 local release tests and the actual same-head hosted contract-delta passed; the approved Linux packs remained queued. The inactive codex/merge-queue-pilot authority context is not the selected main context; main authority is green.

PR #7163 / `claude/prophet-hk-sector-link-20260915` now carries `8ee5f854c3bf8d859679e4940ab5bdc5a8c2bd8b`: existing correct HK modal route plus explicitly superseding current-source browser evidence, preserving accepted P0B/Canada bytes. 163 exact code-owner tests, the existing full browser matrix, eight modal activations and two no-JS fallbacks passed. Curated owner closure: 34 inputs / zero uncovered. Full local contract-delta exceeded 360s and is not a pass; hosted confirmation is required.

This branch, `sol/prophet-us-panel-authority-20260916`, removes 26 redundant read-only cache overlays across seven workflows and replaces the misleading “screened tonight” promise with the actual source date or an explicit unavailable date. 54 local tests and eight candidate browser cases passed; the exact-key cache mutant was rejected. No other workflow semantics changed.

## Scope, method and user journey
Use the existing Git-tracked US breadth panels, alpha, candidate board, plan source and publishing systems. No new market data, signal engine, calendar, source registry or control plane. Preserve producer seed caches, Russell coverage, candidate/plan separation, counts, ranking thresholds, immutable-source guards, security and entitlements. All repairs are deterministic; no model-derived score/rank/admission or trade decision is introduced. A genuinely fresh zero-candidate screen is valid; never force population to satisfy a display expectation. Missing source dates stay unknown. Historical source-byte conflicts require their existing correction path, never an overwritten immutable record.

## Release order and proof
Consume same-head CI/security and source review, integrate #7180, this input/consumer repair, and #7163 without bypassing guards; reconcile overlapping daily.yml hunks before release. Follow the existing canonical renderer/publisher. Require a real completed-session input through alpha, source-bound candidate/plan artifacts and the served HTML/premium payload. Compare source dates, generation/source digests, counts and explicit new/retained/removed names. Use a real browser on production, not these fixtures. Then repeat through a normal scheduled update before acceptance. Existing #7161 cohort-clock and #7178 regional-band reachability remain separate carriers; do not silently supersede their owners or confuse their builds with release proof.

## Genuine blockers and continuation
At 2026-09-16T03:57Z the existing pc-ci-1/2/3 org runners were offline and all twelve #7180 Linux packs were queued. Native Desktop Commander listed Windows/WSL offline; Tailnet subsequently showed Windows online but winpc-wsl offline, and both authorized SSH reads timed out. Restore the existing WSL distro and CI services; do not add labels, new fallback runners, widen permissions, kill unrelated jobs or waive checks.

Natural daily `35041133038` finished collect successfully and its engine job `104658157677` was queued at the last observation. It was not canceled, restarted or duplicated. Reconcile that exact run before any manual run or rescue. Observe actual current run state; this handoff is not a live runtime receipt.

Stop only at a genuine release/authority gate or real production proof. None of the three candidates is accepted as production-proven here. The next action is restore the existing CI host, consume exact-head outcomes, integrate the same carriers and prove the real current-session board. Completed source/evidence repairs must not be rebuilt from scratch. On an ambiguous push/deploy effect, reconcile its original carrier before any repeat.
