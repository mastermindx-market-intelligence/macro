---
workstream: "WS:LEADERSHIP-PERSISTENCE-INTELLIGENCE"
session: "Web Sol / Mac-Studio / sol/rotation-persistence-sector-control-rph1-20260912"
model: sol
ended_because: ci_handoff
mission: >
  Execute and repair the outcome-blind RPH-1 daily sector-price control on one existing Draft/HOLD
  carrier. Separate leadership memory, subsequent-return persistence, dispersion/correlation and
  phase-complete 1D/2D/3D MACD outcomes while preserving RPH-0, Temporal Grain and every production
  rank, gate, entry, Prophet, Oracle and portfolio owner.
state_before: >
  PR #7095 existed at exact head c962235abf2c2b731c98693c472a116bc110e110 with a deterministic
  research engine and frozen archive output, but independent review returned REPAIR_REQUIRED. The
  live archive regeneration proof was incorrectly owned by gate: code; source labels were CWD-
  dependent; non-Datetime indexes and timezone-aware labels were not fail-closed; statistical units,
  phase sample spans and leadership sample comparisons were incompletely disclosed; and the quality
  key named a first eligible position as latest.
changed:
  - path: scripts/research/rotation_persistence/sector_control.py and scripts/research/run_sector_control_rph1.py
    what: >
      Require DatetimeIndex source labels, preserve timezone-local session dates, resolve input and
      output paths against one canonical repository root, emit canonical source receipts, disclose
      sector-signal-date units and phase spans, add recent-versus-all leadership comparisons, rename
      first eligible positions truthfully, and expand deterministic Markdown evidence without
      changing the preregistered estimands or authority ceiling.
  - path: tests/test_rotation_persistence_sector_control.py and tests/test_rotation_persistence_sector_cli.py
    what: >
      Add direct formula, tie, endpoint, strict-JSON, sample-window, hierarchy-span, source-index,
      timezone and canonical-path tests. The review defects were observed RED before the minimal
      repairs and the original focused cases remain green.
  - path: tests/test_rotation_persistence_sector_archive.py and .github/ci/legacy-jobs.yml
    what: >
      Isolate the byte-for-byte live Yahoo archive regeneration proof in a dedicated gate: data job;
      keep the code gate purely synthetic so moving archive bytes cannot reject an otherwise valid
      code-only change.
  - path: research/rotation_persistence/sector_control_rph1/result.json and research/rotation_persistence/sector_control_rph1/report.md
    what: >
      Regenerate the committed result from the exact twelve parquet inputs and injected clock. The
      result publishes observation units, sector-date and unique-date counts, signal and completed-
      bar spans, leadership anchors/N/stddev, hierarchy phase samples and the frozen limitations.
  - path: research/rotation_persistence/sector_control_rph1/verification.json
    what: >
      Bind protected procedure, the immutable semantic implementation head/tree, all source/output
      hashes, focused/adversarial proof, code/data gate ownership, current-main no-write integration,
      GitHub HOLD state and the exact hosted-proof gap.
  - path: agentos/workstreams/WS-LEADERSHIP-PERSISTENCE-INTELLIGENCE.md and agentos/handoffs/LEADERSHIP-PERSISTENCE-INTELLIGENCE-2026-09-14-RPH1.md
    what: >
      Describe the actual daily sector-control RPH-1 child without erasing the separate future 23/30-
      session or deeper point-in-time idea, and preserve a cold-stranger continuation packet.
verified:
  - claim: "The exact RPH-1 synthetic suites pass."
    command: >
      PYTHONDONTWRITEBYTECODE=1 /Users/chriswong/Documents/Cluade/Macro Dashboard/.venv/bin/python -m pytest
      tests/test_rotation_persistence_sector_control.py tests/test_rotation_persistence_sector_cli.py
      -q --tb=short -p no:cacheprovider
    result: "31 passed in 47.90s on semantic head 5c7bf21dad34ec68eaf5075a5563de7d5805cda0."
  - claim: "The live archive regenerates committed JSON and Markdown byte-for-byte under gate: data."
    command: >
      PYTHONDONTWRITEBYTECODE=1 /Users/chriswong/Documents/Cluade/Macro Dashboard/.venv/bin/python -m pytest
      tests/test_rotation_persistence_sector_archive.py -q --tb=short -p no:cacheprovider
    result: "1 passed in 78.76s; direct CLI replay also preserved result/report hashes with zero diff."
  - claim: "All preregistered false-green and disclosure boundaries are discriminated."
    command: >
      Run the eleven exact pytest nodes named in sector_control_rph1/verification.json for missing-
      session fill, incomplete tails, warm-up, future endpoints, authority, index/timezone identity,
      final anchor, observation units, phase spans and Markdown evidence.
    result: "11 passed in 18.98s; no named false green survived."
  - claim: "Code/data CI ownership is valid and the live archive suite cannot leak into the code gate."
    command: >
      Validate both legacy manifest gates, then parse the manifest and assert the archive path belongs
      only to sector-control-archive-regeneration with gate:data.
    result: "139 code jobs and 74 data jobs validated; OWNERSHIP_OK job_gate=data code_jobs_checked=139."
  - claim: "Contract-delta does not expose an unowned new suite or exclusive-closure regression."
    command: "/Users/chriswong/Documents/Cluade/Macro Dashboard/.venv/bin/python scripts/check_contract_delta.py --base 8d198b42f6bff491a49b1f3467b56ca4bb673f80"
    result: "contract-delta: 0 introduced, 0 inherited (base 8d198b42f6bf); 680.40s."
  - claim: "The durable Agent OS records are structurally valid."
    command: "PYTHONDONTWRITEBYTECODE=1 /Users/chriswong/Documents/Cluade/Macro Dashboard/.venv/bin/python scripts/agentos.py validate"
    result: "1095 records; 0 errors; 76 unrelated repository warnings."
  - claim: "The semantic head integrates cleanly with the protected-main snapshot used for review."
    command: "git merge-tree --write-tree 22f6759fe6529b4768309332309d52a8ee20526a 5c7bf21dad34ec68eaf5075a5563de7d5805cda0"
    result: "Clean no-write integrated tree de98a17f781e55d114b0443ac33410060d7617ee; direct overlap is only .github/ci/legacy-jobs.yml."
  - claim: "The generated evidence remains research-only."
    command: >
      Inspect result.json authority and run
      tests/test_rotation_persistence_sector_control.py::test_result_contract_is_context_only_and_has_no_trade_authority
    result: >
      is_context_only=true; may_rank, may_gate, may_size, may_trade, may_modify_prophet and
      may_modify_oracle are all false.
  - claim: "The existing PR remains held."
    command: "gh pr view 7095 --json state,isDraft,headRefOid,baseRefOid,autoMergeRequest,labels,mergeable,mergeStateStatus"
    result: "OPEN Draft; exact head/base; no labels; native auto-merge null; MERGEABLE/UNSTABLE."
unverified:
  - claim: "An independent reviewer accepts the exact immutable record head."
    what_would_verify: >
      A separate read-only Opus reviewer checks the resulting commit and tree, frozen formulas,
      source/result hashes, phase completeness, sample disclosure, owner boundaries, tests, current-
      main comparison and current checks, then returns PASS / ACCEPTED_HOLD without modifying it.
  - claim: "Hosted code proof executes on the exact immutable record head."
    what_would_verify: >
      Dispatch ci.yml once on the existing branch with expected_sha bound to that exact head and
      reconcile the resulting semantic evidence. Main-owned trusted executor run 34936708141 already
      failed closed before execution because PR #7095 does not target main; that refusal is not proof.
  - claim: "Hosted archive regeneration executes before merge."
    what_would_verify: >
      An approved branch-safe data-gate lane. The current data-health workflow is main-only, so this
      remains an explicit pre-merge hosted gap; the local byte-replay and gate ownership proofs are
      green but must not be mislabeled as hosted execution.
  - claim: "The observed daily control improves a production investment decision."
    what_would_verify: >
      A separately preregistered Temporal Grain / Entry Truth consumer study with point-in-time replay,
      exact lower-grain identity, execution assumptions and a defined utility metric. RPH-1 itself
      cannot establish that claim.
unresolved:
  - >
    The archive is daily Yahoo close data through 2026-09-09. It is not vendor-chart parity, exact
    intraday identity, or point-in-time constituent/theme reconstruction.
  - >
    Recent five-session leadership rank persistence and subsequent-return persistence are distinct
    estimands and may have opposite signs; neither authorizes a trade.
  - >
    Phase-pooled MACD rows are non-independent because phases share daily source sessions. Phase-
    specific rows are primary, and hierarchy labels are archive-specific descriptive evidence only.
next_actions:
  - "Commit and normally push this exact record assembly on the existing branch; do not amend, rebase, reset or force-push."
  - >
    Obtain one fresh independent immutable-head review because candidate-owned blobs changed after
    c962235; review reuse is FULL_REREVIEW_REQUIRED.
  - >
    Dispatch ci.yml once on the exact record head, reconcile candidate versus inherited failures, and
    preserve the main-only archive-hosting gap explicitly.
  - >
    Replace the stale PR body, preserve Draft/HOLD, and park only after accepted review. Never mark
    Ready, merge, deploy, or connect a production consumer.
do_not_redo:
  - "Do not create a sibling RPH-1 branch, PR, workstream, score, state store, event plane or timeframe authority."
  - "Do not modify RPH-0 PR #7064 or reinterpret its published-theme result as this sector-price control."
  - "Do not forward-fill missing sessions, retain incomplete bars, shorten MACD warm-up, use contemporaneous outcomes or pool phases as independent samples."
  - "Do not turn hierarchy labels into a product regime, rank, gate, entry or trade instruction."
  - "Do not move the live archive regeneration proof back into gate: code."
danger_areas:
  - >
    Leadership rank memory and predictive return persistence can have opposite signs. Any summary that
    calls both persistence without naming the estimand is misleading.
  - >
    A timezone-aware parquet index must keep its stored local session label; UTC conversion can move a
    late-evening label into the next date and silently alter the common panel.
  - >
    Recent hierarchy labels can change materially by forward horizon and window. They are descriptive
    archive controls, not a selected production timeframe.
  - >
    The trusted main-owned executor and data-health lane both reject non-main targets by design. Do not
    convert those refusals into semantic failures, and do not bypass them by retargeting the PR.
prs: [7095]
---

# Summary

RPH-1 has one repaired semantic carrier whose data normalization, formulas, sample units, phase spans,
live regeneration and code/data CI ownership are explicit and reproducible. The exact archive contains
2,067 complete sessions from 2018-06-19 through 2026-09-09; the evidence remains bounded to a daily
sector-ETF control and carries zero rank, gate, sizing, trading, Prophet, Oracle or portfolio authority.
The current closure path is one immutable record commit, independent review, exact-SHA hosted code
reconciliation, a truthful PR body, and PARKED / HOLD-FOR-SOL on the existing Draft PR.
