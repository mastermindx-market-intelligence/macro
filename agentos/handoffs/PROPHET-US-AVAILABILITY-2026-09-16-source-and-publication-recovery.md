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
      python -m pytest -q --basetemp=/tmp/pr7187-pytest-focused2
      tests/test_daily_collect_commit_path.py tests/test_p0_prophet_candidate_board.py
      tests/test_render_run_size_cap.py tests/test_workflow_file_size.py
      tests/test_chat_nav_sync.py
    result: >
      76 passed in 32.23s on the final current-main composition
      aad9ed4be170ec253995c2b40c632d46ee5f9f43 before this final records-only refresh.
  - claim: Records, workflow syntax, chat navigation and differential CI contracts are clean.
    command: >
      python scripts/agentos.py validate; parse all .github/workflows/*.yml and *.yaml
      with PyYAML; python -m scripts.sync_chat_nav; python scripts/check_contract_delta.py
      --base e729d0fd9d48868b49a1911d4098c689b3d373bd
    result: >
      Agent OS reported 0 errors and 86 inherited warnings; 98 workflow files parsed;
      chat nav sync was OK; contract-delta reported 0 introduced and 0 inherited
      findings with exit 0.
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
  - >
    Completed-session panel production can still fail upstream even when reader cache
    authority is correct. The separate input-integrity carrier owns validation/retry;
    #7187 must not fabricate prices or treat its absence as a reader defect.
next_actions:
  - >
    Push this repaired, current-main-composed same carrier by normal fast-forward and
    consume the delivered exact-head checks and independent review. After #7180 is
    accepted, recompose the two carriers on current main, then prove one real
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
Restore current-session US Prophet discovery end-to-end so the user sees the actual dated candidate screen, not an old board beneath a new shell. This continues `WS:PROPHET-US-AVAILABILITY` under the current Chairman’s explicit direction. The original implementation used Mastermind Skillpack pin `7642aea155d2817219135b24246b55c1d7611c66`; this repair continuation is governed by protected `master` at `8ba7deedde164c90298d3e88785d98e02fa5e2d2`. The required Skillpack/source-law blobs are byte-identical to the previously loaded `0fe8074ff953b2ced9025ed40f0f66019c759967` revision. Executive OS owns lifecycle, Agent OS continuity, GitHub implementation, Slack transport. This handoff creates no new runtime Job, worker lease or queue.

## Verified frontier and existing carriers
PR #7180 / `sol/prophet-us-completed-session-sourcebound-20260915` remains open at `99b9bc18ded963ed5e9b9a4864bfff88a8e1d5ba`: completed-session source-bound recovery plus its regression-suite registration. Its Linux pack execution and release decision remain owned by the separate active CI/release carrier; this branch does not modify, rerun or bypass it.

PR #7163 / `claude/prophet-hk-sector-link-20260915` remains open at `e2b5e7a58edc13cbad910c053ebe37d6e31399f2`: the independent HK route/browser-evidence carrier. This branch does not modify or replace it.

This branch, `sol/prophet-us-panel-authority-20260916`, removes 26 redundant read-only cache overlays across seven workflows and replaces the misleading “screened tonight” promise with the actual source date or an explicit unavailable date. The repaired current-main candidate passed 76 owning tests; eight candidate browser cases passed, and exact-key, multiline-path, `.yaml`, and duplicate-seed mutants were rejected. No scoring, ranking, schedule, credential, collector, permission, or market-authority semantics changed.

## Scope, method and user journey
Use the existing Git-tracked US breadth panels, alpha, candidate board, plan source and publishing systems. No new market data, signal engine, calendar, source registry or control plane. Preserve producer seed caches, Russell coverage, candidate/plan separation, counts, ranking thresholds, immutable-source guards, security and entitlements. All repairs are deterministic; no model-derived score/rank/admission or trade decision is introduced. A genuinely fresh zero-candidate screen is valid; never force population to satisfy a display expectation. Missing source dates stay unknown. Historical source-byte conflicts require their existing correction path, never an overwritten immutable record.

## Release order and proof
Consume same-head CI/security and source review, integrate #7180, this input/consumer repair, and #7163 without bypassing guards; reconcile overlapping daily.yml hunks before release. Follow the existing canonical renderer/publisher. Require a real completed-session input through alpha, source-bound candidate/plan artifacts and the served HTML/premium payload. Compare source dates, generation/source digests, counts and explicit new/retained/removed names. Use a real browser on production, not these fixtures. Then repeat through a normal scheduled update before acceptance. Existing #7161 cohort-clock and #7178 regional-band reachability remain separate carriers; do not silently supersede their owners or confuse their builds with release proof.

## Genuine blockers and continuation
The earlier runner-offline observation is superseded. At final reconciliation, the approved organization runners `pc-ci-1`, `pc-ci-2`, and `pc-ci-3` were online and busy draining existing trusted-pack work. Runner recovery, queued-job control, labels and reruns remain owned by the separate active CI session; this carrier does not cancel, duplicate, reroute or bypass that work.

A separate upstream input-integrity carrier is investigating why a completed-session row could contain populated volume but absent Close/High values while a collector still reported success. This reader-authority repair prevents stale cache overlays and discloses the source screen date; it does not fabricate missing closes, introduce a provider fallback, change rankings or claim that upstream panel production is healthy.

Protected `main` movement after integration base `de36a37a3a4738e5cd59db31345790002f2582db` through `e729d0fd9d48868b49a1911d4098c689b3d373bd` is confined to research-vault/Astra Fabric records and the independent seasonality program-watch implementation/tests. The same carrier has history-preservingly joined that current `main`; it must now push by normal fast-forward and consume exact-head CI/security and independent review. After #7180 is accepted, recompose the producer/provenance and reader-authority carriers, then require one real completed-session producer-to-served-board browser receipt before Ready, merge acceptance or `PROVEN_LIVE`. On an ambiguous push/deploy effect, reconcile the original carrier before any repeat. Completed source/evidence repairs must not be rebuilt from scratch.

## 2026-09-17 — accepted gated-date repair completed on the original carrier

Under current Chairman continuation and protected `Mastermind@8b231e8267f09cfb002ed3e87bec14906dce1720`, resumed this original direct operation after matching local/remote `0a076cedd8094e5425e782aca976820e93ed6e8e`, clean tracked state, no Git locks and no active cwd writer. Same carrier #7187; no delegated receiver or sibling source transfer was performed.

Accepted review `5696643747` is now implemented: six literal EN/ZH strings make the candidate wall and toggle screen-neutral and the historical plan wall plan-book-neutral. Actual candidate dates and missing-date behavior remain unchanged. Fifteen discriminating gated cases failed first; 72 existing/new tests then passed. On the preserved real board/book all HTML outside the six strings is identical. Eight browser theme/language/width cases pass with only ordinary source switching and protected-payload 401 fixtures; no authentication or live publication is claimed.

The new cases were otherwise only data-gated, so the existing `washout-turn-organ` code owner now runs a targeted 20-case command. No new job/dependency/timeout or existing run step changed. Evidence is `docs/pr-crops/us-prophet-source-date-20260916/gated-journey-20260917/`. Preserve earlier screenshot/receipts as historical evidence. Next: exact-head CI and genuine independent review, then one accepted source-bound integrated publication; do not replay the expensive input acquisition or restore cache overlays.

The exact source amendments for #7187 and the separately owned #7254 code-gate step compose on prior tested recovery tree c748468a... without manual conflict. Result f7c7533043dd2901c4462a446c133d2cbe601aba passes 555 tests across 12 suites, with all 6,447 Python source files unchanged. This is source-path consumer integration, not a full-PR document merge or a current-main hosted pass. Each complete candidate also composes individually with main 6a6d86bcf0f0720596fc1091b93d928319a1d4fd; that separate proof establishes merge compatibility only. The real local code-gated plan selects washout-turn-organ, so the 20 relevant date cases now have a PR execution route.

## 2026-09-19 — P0 DAG declaration repair on the original carrier

Current procedure was re-pinned to protected `Mastermind@ac6180d0ca9107daae54f9eea6bd4b8aef92d630`. GitHub still showed #7187 open/draft at exact remote head `32c1f16699790e23257d7dba8c785adf4db13a7f`; the original branch was checked out into an isolated linked worktree without resetting or modifying the existing auxiliary tip-guard worktree.

The exact RED reproduced on the clean carrier: `scripts/check_dag_conformance.py --verbose` exited 1 because `.github/workflows/daily.yml / stock_briefs` invoked `scripts.fetch_r2 --dirs stockdata` while `config/dag.yml` declared only `scripts.build_stock_briefs` and `scripts.publish_r2`.

Commit `106f26b8fa17e2f85e858cd766fac29ce1fd4c6f` adds the missing input-materialization declaration before `build_stock_briefs`. It adds no workflow step, divergence waiver, rank/admission/publication authority, lifecycle owner, or control plane.

Fresh local evidence on that commit: DAG conformance reports 27/27 lanes conforming with the two inherited suspect drifts still visible; `tests/test_dag_conformance.py` passed 48 tests; `tests/test_daily_collect_commit_path.py` passed 33 tests; both YAML files parsed; `git diff --check` passed. The pytest runs emitted five inherited temp-cleanup permission warnings each; they are not represented as clean warning-free execution.

A separate local auxiliary worktree at `/Volumes/Mastermind/worktrees/sol-prophet-7187-tipguard` remains on branch `sol/prophet-us-panel-tipguard-20260919` with uncommitted edits to `collectors/breadth.py` and `tests/test_daily_collect_commit_path.py`. No active cwd process or Git lock was observed. Those edits were preserved untouched and are not part of this P0 operation; do not discard, stash, re-home, or claim them through #7187 without a separate ownership reconciliation.

Current Macro `main` observed locally at `6a1670778abc48d6429a3dcddd16bd84c25cb4d0` has material movement in `daily.yml`, `config/dag.yml`, and the commit-path tests, but it does not contain the candidate's stockdata restore or this matching DAG row. Hosted exact-head CI, current-main integrated-tree proof, source review, #7180 composition, and a natural completed-session served-browser journey remain unverified and mandatory.
