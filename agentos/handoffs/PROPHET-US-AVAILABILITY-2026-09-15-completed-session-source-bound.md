---
workstream: WS:PROPHET-US-AVAILABILITY
session: sol/prophet-us-completed-session-sourcebound-20260915
model: sol
ended_because: ci_handoff
mission: >
  Restore lawful US Prophet availability on weekday pre-close runs by scoring one
  completed NYSE session, preserve the mixed-vintage safety gate, and bind every
  Prophet projection to exact immutable source-board bytes without making Prophet own
  or roll back the independently current customer board.
state_before: >
  On 2026-09-15 the US board ranked a torn panel: 3,038 names ended on completed
  2026-09-14 while 198 names already carried provisional 2026-09-15 daily bars.
  Sixteen candidates survived policy skips, all sixteen failed clock provenance, and
  zero plans originated. The existing gate was correct; producer and clock semantics
  were wrong. China separately carried a 2026-09-15 wrapper over a stale 2026-09-09
  reversal plane.
changed:
  - path: scripts/build_site.py
    what: >
      Captures one UTC observation instant and passes one completed-session cutoff to
      residual alpha and the US stock-library producer.
  - path: scripts/build_stock_library.py
    what: >
      Clips all non-crypto close/high/OHLC scoring inputs before extension,
      dispersion, lottery, technical, entry, alpha, and ranking reads; keeps crypto
      continuous and records raw/provisional reach.
  - path: engine/prophet_bridge.py
    what: >
      Resolves live clocks from the board observation timestamp, preserves exact
      date-only replay semantics, accepts lowercase-t ISO datetimes, and can originate
      from a supplied frozen board object without reopening the mutable path.
  - path: engine/prophet_arena.py
    what: Live and Arena now share the same timestamp-aware price-session authority.
  - path: scripts/build_prophet.py
    what: >
      Publishes content-addressed exact source bytes at
      data/prophet/origination_sources/<raw_sha256>.json.gz and routes live
      origination, Arena, legacy shadow, and gate disclosure through the one frozen
      parsed board object.
  - path: scripts/ci/daily_engine_prophet_nightly.sh
    what: >
      Includes exact immutable source provenance in the zero-origin-safe owned-output
      manifest and verifies frozen bytes across the build.
  - path: scripts/ci/daily_engine_prophet_checkpoint.sh
    what: >
      Extends the existing narrow closed allowlist to immutable source snapshots while
      keeping the mutable live board outside Prophet ownership.
  - path: scripts/ci/daily_engine_commit_outputs.sh
    what: >
      Prevents broad engine publication from leaking uncheckpointed provenance while
      preserving input-only correction ledgers.
  - path: .github/workflows/daily.yml
    what: Wires the existing checkpoint/accepted-source boundary to the new immutable provenance plane.
  - path: docs/superpowers/specs/2026-09-15-prophet-us-completed-session-source-bound-design.md
    what: Records the approved architecture, authority boundaries, failure behavior, and acceptance proof.
  - path: docs/superpowers/plans/2026-09-15-prophet-us-completed-session-source-bound.md
    what: Records test-first execution, independent review disposition, and continuation state.
  - path: agentos/workstreams/WS-PROPHET-US-AVAILABILITY.md
    what: Re-pins the active carrier and exact post-merge production-proof boundary.
  - path: agentos/discoveries/DSC-PROPHET-PRECLOSE-DAILY-BARS-ARE-NOT-COMPLETED-SESSIONS.md
    what: Preserves the provisional-current-date panel-tear discovery and required producer-side response.
  - path: agentos/discoveries/DSC-PROPHET-SOURCE-HASH-NEEDS-A-FROZEN-CONSUMER-OBJECT.md
    what: Preserves the ABA source-binding landmine discovered in adversarial review.
verified:
  - claim: The repaired US candidate's bounded release matrix is green.
    command: >
      /Users/chriswong/.cache/mm-venv-mac-builder-3/bin/python -m pytest -q
      tests/test_us_completed_session_panel.py tests/test_prophet_bridge.py
      tests/test_prophet_arena_clock_parity.py tests/test_prophet_durable_checkpoint.py
      tests/test_prophet_r2_boundary.py tests/test_prophet_plan_chronology_audit.py
      tests/test_workflow_file_size.py
    result: 192 passed on candidate aef3120e4ce12616d99869045e07279c27847238.
  - claim: The three nested-Git checks blocked only by the independent review sandbox pass on the host.
    command: >
      python -m pytest -q
      tests/test_prophet_durable_checkpoint.py::test_accepted_source_restore_handles_new_paths_over_a_stale_head
      tests/test_prophet_durable_checkpoint.py::test_accepted_source_restore_withholds_a_true_extra_prophet_file
      tests/test_prophet_durable_checkpoint.py::test_final_engine_cleanup_removes_first_publication_prophet_additions
    result: 3 passed.
  - claim: Independent adversarial review found no remaining actionable defect after the ABA and parser repairs.
    command: >
      Cursor Codex High read-only review of
      38d30def3826c28fa352a00a5211e22e93343b14..aef3120e4ce12616d99869045e07279c27847238.
    result: Zero Critical, Important, or Minor findings.
  - claim: The six adjacent failures are baseline defects, not candidate regressions.
    command: >
      git archive 38d30def3826c28fa352a00a5211e22e93343b14 into a temporary tree, then run
      TestStandoutsSentinelRegistration::test_fresh_us_standouts_no_warning and
      TestDelayedBoardBanner.
    result: >
      The same six failures reproduce on the semantic base: one fixture omits newer
      unrelated surface artifacts and five tests invoke the Jinja template without translator t.
  - claim: PR #7180 preserves its reviewed semantics on the 2026-09-20 current-main integration candidate.
    command: >
      Pin protected Mastermind f3d187976e083f9b102fc49696395b5c1521ebb5 and Macro
      main 3df8685c87c2ea750343ab72da09fd20626cd8d4; compare every shared-path
      candidate hunk and imported functional blob; then run git merge-tree --write-tree
      origin/main 99b9bc18ded963ed5e9b9a4864bfff88a8e1d5ba.
    result: >
      Conflict-free tree 2f5f7f04524d420987d6b948989594dcf4e1431c. The five
      shared paths retain the candidate hunks unchanged; imported calendar, store,
      residual-alpha, and owner-test blobs are byte-identical to the reviewed base.
  - claim: The China sibling availability/data-plane repair is live and should not be retried.
    command: >
      gh run view 35021696056; git merge-base --is-ancestor 4ec24e0f4745
      6e15071e4e22; read current main china_standouts.json, run_status.json, and R2 audit log.
    result: >
      Asia run succeeded on a descendant of the repair; source_asof 2026-09-15,
      exact_date true, available true, degraded false, 99.6% scored coverage,
      100% actionable coverage, no outage flag, china_universe status ok, and CN/HK R2 age 0.0h.
unverified:
  - claim: Required CI/security gates pass on the final documentation-bearing head of PR #7180.
    what_would_verify: gh pr checks 7180 shows every required check successful for the exact final head.
  - claim: A real post-merge US nightly uses one coherent completed-session board and publishes exact source provenance.
    what_would_verify: >
      Natural daily/Prophet run after merge shows non-mixed completed-session receipt,
      immutable source hash/path resolving to exact board bytes, and either lawful new
      originations or an honest no-candidate disposition unrelated to the repaired defects.
  - claim: PR #7187 composes after accepted #7180 without weakening producer/provenance or tracked-panel authority.
    what_would_verify: >
      Build the dependency-ordered integration candidate after #7180 acceptance, rerun
      current-head owner/contract gates, and obtain exact-head review.
  - claim: PR #7457 preserves display-only leader-observation semantics after the accepted #7180 -> #7187 base.
    what_would_verify: >
      Reconcile #7457 once on its original carrier, rerun focused/full owner suites,
      contract-delta and exact-head review, then prove the protected serving boundary.
unresolved:
  - PR #7180 exact-head CI/security proof and merge decision.
  - Natural US production proof; until then the US capability is BUILT_NOT_PROVEN.
  - Dependency-ordered integration of PR #7187 after #7180 acceptance.
  - One history-preserving reconciliation of PR #7457 after the accepted #7180 -> #7187 base.
  - Original W2 fire-drill week and other older workstream done-bar obligations remain outside this bounded producer repair.
next_actions:
  - Monitor PR #7180 checks on its exact final head; repair only candidate-caused failures and never weaken chronology or mixed-vintage gates.
  - Merge #7180 only after required gates, genuine independent approval, and release authority are satisfied.
  - After #7180 acceptance, integrate PR #7187 on its existing carrier.
  - After the accepted #7180 -> #7187 base, reconcile PR #7457 once on its existing carrier.
  - After lawful integration and deployment, record the natural source clock, mixed-vintage state, intake dispositions, immutable source path/hash, protected payload identity, browser result, and subsequent scheduled refresh.
do_not_redo:
  - Do not disable or soften mixed-vintage refusal; the gate correctly protected users from a torn scoring panel.
  - Do not solve provenance by making live site/factordata/us_standouts.json Prophet-exclusive or restoring an older accepted board over a newer customer board.
  - Do not re-open the mutable board path after source freeze; all consumers use the one frozen object.
  - Do not rerun China recovery run 35019907027 or dispatch a duplicate; the successor carrier 35021696056 proved the repair live.
  - Do not repair the six reproduced adjacent baseline failures in PR #7180; they are unrelated and would widen the PR.
  - Do not redo PR #7161; it merged as bdad67069190634b0f38c07bfbc4a39161354be9 on 2026-09-17.
  - Do not absorb PR #7187 or PR #7457 into this branch; preserve the dependency order and one useful capability per PR.
danger_areas:
  - Source-byte and source-object authority must remain identical; boundary hashes alone do not defeat ABA rewrites.
  - Date-only replay and live timestamp semantics are intentionally distinct; changing one can silently restamp historical cohorts or reject valid pre-close boards.
  - Broad engine cleanup must remove only uncheckpointed immutable provenance and must not overwrite correction ledgers.
  - Public R2 remains health-only under DEC:B1-PROPHET-PUBLIC-SPLIT; exact source snapshots and plan books stay private.
  - A green or cancelled overall daily run is not proof of Prophet delivery; inspect the checkpointed artifact and source cohort.
prs: [7180, 7187, 7457, 7161]
discoveries:
  - DSC:PROPHET-PRECLOSE-DAILY-BARS-ARE-NOT-COMPLETED-SESSIONS
  - DSC:PROPHET-SOURCE-HASH-NEEDS-A-FROZEN-CONSUMER-OBJECT
  - DSC:CANCELLED-DAILY-RUN-CAN-STILL-DELIVER-PROPHET
---

## Authority precedence and experience contract

Chairman direction controls scope. The current protected Sol Skillpack commit is
`f3d187976e083f9b102fc49696395b5c1521ebb5`. GitHub owns implementation/evidence;
Agent OS owns continuity; the live US candidate board remains the customer-facing product
artifact and Prophet owns only its derived plans, ledgers, and immutable provenance.

The primary user journey is unchanged: a professional user opens Prophet and receives
fresh, spoon-fed plans and intelligence. Before close, the system may observe provisional
same-day vendor rows, but it scores only the last completed NYSE session. Null or malformed
clock/source state fails closed and preserves the previous accepted projection. Corrections
remain input overlays; raw plan publications remain immutable. All new behavior is
deterministic Python/calendar/provenance logic—no model decides eligibility, rank, size,
or trade authority.

## Stop condition and continuation

Stop this carrier at terminal exact-head hosted CI, genuine independent approval, and
release-owner acceptance for PR #7180. Natural production proof remains a separate
post-integration/deployment gate. A fresh Sol session should load this handoff, protected
Skillpack, PR #7180 exact head/checks, and current main artifacts. Completed implementation,
China proof, and merged PR #7161 are do-not-redo. After #7180 acceptance, integrate PR
#7187 on its existing carrier, then reconcile PR #7457 once on its existing carrier;
EFFECT_UNKNOWN GitHub writes must be reconciled before any retry.

## 2026-09-16 incident release maintenance

Operation `prophet-us-availability-release-recovery-20260916-sol-001` continues the same PR #7180 under current Chairman direction. The implementation carrier is unchanged; maintenance runs in a separate detached workspace, not the original source checkout.

The introduced hosted contract failure was an unregistered `tests/test_us_completed_session_panel.py`. It is now named in the existing `unrun-data-plane` stock-library freshness step in `.github/ci/legacy-jobs.yml`; no waiver or feature semantic change is used. The combined freshness suites passed 28 tests; the bounded release matrix passed 192 tests in 33.13 seconds; `check_contract_delta.py --base b5ea516d3741141bbcb5c42925b639489bc82a04` returned 0 introduced / 0 inherited. These are local results, not hosted or production acceptance.

GitHub separately reports all existing org CI carriers pc-ci-1/2/3 offline. Their queued jobs require macro-home-canary / ci-linux; the authorized winpc-wsl SSH read timed out. Restore the existing approved host/listeners, not new labels, fallback runners or bypassed gates. Daily run 35041133038 was already collecting and was not canceled or duplicated.

A cache-busted public HTTP read at 2026-09-16T02:56:37Z still exposed data-board-asof=2026-09-11 beneath a Sep-14 page title. PR #7163 remains the independent HK dead-link/browser-evidence release blocker. Complete same-head hosted checks and merge review, then require current completed-session inputs, exact immutable source provenance and visible production output. No live-recovery or workstream-completion claim is made here.

## 2026-09-20 current-main release qualification

Operation `prophet-us-availability-release-qualification-20260920-sol-001` continues
PR #7180 on its original carrier. Protected procedure was reloaded from Mastermind
`f3d187976e083f9b102fc49696395b5c1521ebb5`; no successor or merged equivalent of
#7180 exists. The reviewed implementation head remains
`99b9bc18ded963ed5e9b9a4864bfff88a8e1d5ba`.

Macro main was pinned at `3df8685c87c2ea750343ab72da09fd20626cd8d4`.
A history-preserving synthetic integration produced conflict-free tree
`2f5f7f04524d420987d6b948989594dcf4e1431c`. Five shared paths moved on main, but
candidate hunks remain unchanged; imported calendar, store, residual-alpha, and owner-test
blobs remain byte-identical. No ancestry-only merge was added to the PR.

Current-base local evidence on that exact integrated tree:

- bounded release matrix: 192 passed;
- stock-library freshness plus completed-session CI owner: 28 passed;
- Prophet nightly/checkpoint/publication shell syntax: passed;
- `daily.yml` YAML parse and `git diff --check`: passed;
- Agent OS validation: 1,149 records, 0 errors, 51 inherited warnings.

The prior hosted run `35050886413` is not a candidate failure and must not be treated as
current proof. Its contract-delta gate and six packs passed; six sibling packs were
cancelled, so `ci-gate` correctly failed on missing semantic fragments. Current main now
routes ordinary PR packs to hosted Linux and sets matrix `fail-fast: false`, removing that
specific incomplete-proof mechanism. Do not rerun the obsolete tested tree. Publish this
same-carrier continuity update to trigger one fresh `synchronize` proof, then require
terminal exact-head hosted CI and genuine independent approval. Capability remains
`BUILT_NOT_PROVEN`; no merge, deployment, serving, browser, or natural-refresh proof is
claimed.

Live dependency reconciliation also supersedes the old #7161 continuation edge. PR #7161
merged at `bdad67069190634b0f38c07bfbc4a39161354be9` on 2026-09-17 and is DO_NOT_REDO.
After #7180 acceptance, the active order is #7187 integration, then one history-preserving
#7457 reconciliation. Both remain open draft carriers and must not be recreated or folded
into #7180.
