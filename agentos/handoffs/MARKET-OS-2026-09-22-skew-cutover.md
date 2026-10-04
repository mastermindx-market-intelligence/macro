---
workstream: "WS:MARKET-OS"
session: claude/mo-a-3-a-f03-w2-3-skew-cutover
model: local
ended_because: complete
mission: >
  W2-3 cutover. Render hosts copy the skew ledger down from R2 and run the
  builder with --emit. They no longer pin the legacy chain.
state_before: >
  origin/main at dd973910e95ea3ad99118fbbc2c83473fe8f1c80 already had the W2-1b
  legacy pin (one OPTIONS_SKEW_LEGACY_CHAIN line in render.yml). The store-host
  accrual lane is the open sibling pull request 7737. Render hosts still have
  no ThetaData store.
changed:
  - path: .github/workflows/render.yml
    what: Removed the job-level legacy pin. Both skew calls pass --emit. A separate step restores options_skew from R2 before the re-render step. The cl_gex comment now says the ledger upsert is a temp file plus rename.
  - path: .github/workflows/engine-render.yml
    what: Removed both export/unset pairs. Both skew calls pass --emit. A separate step restores options_skew from R2 before the re-render step. The leader-radar comment now says the ledger upsert is a temp file plus rename.
  - path: .github/workflows/closing-bell.yml
    what: Removed the export/unset pair. The skew call passes --emit. A separate step restores options_skew from R2 before the parallel band, with the same skip guard as the attention restore.
  - path: scripts/ci/daily_engine_regional_desk_builders.sh
    what: Removed the export/unset pair. The skew call passes --emit. The ledger restore from R2 sits next to the massive_stock_day restore and before the builder.
  - path: tests/test_options_skew.py
    what: The live-caller lock now requires zero legacy pins, --emit on every live call, and the R2 restore before each builder.
verified:
  - claim: The skew lock and the render step-length guard pass.
    command: python -m pytest tests/test_options_skew.py tests/test_public_render_fastlane.py -q
    result: 26 passed in 4.28s, and a review re-run passed 26 in 3.24s
  - claim: The exclusive options-skew-engine registration still covers its closure.
    command: python -m pytest tests/test_ci_pack.py -k curated_exclusive -q
    result: 2 passed, 119 deselected in 179.53s
  - claim: This diff introduces no contract-delta miss.
    command: /Users/chriswong/lanes/venv/bin/python3 scripts/check_contract_delta.py --base origin/main
    result: contract-delta 0 introduced, 1 inherited (base cbd349da2753). That base is origin/main at the moment the final run resolved it. An earlier run on the same diff reported the same 0 introduced against aedf2a50b1a4.
  - claim: The agentos store has no new errors.
    command: /Users/chriswong/lanes/venv/bin/python3 scripts/agentos.py validate
    result: 0 error(s), 90 warning(s). The warnings are pre-existing phantom paths on this sparse checkout.
unverified:
  - claim: GitHub Actions on the pushed head is green.
    what_would_verify: gh pr checks after the push. This packet does not claim that.
  - claim: The first store-host accrual has been published to R2.
    what_would_verify: The seat's receipt from the m1 host after pull request 7737 publishes options_skew. This cutover stays a draft until that receipt exists.
unresolved:
  - GitHub checks on the pushed head are not claimed green.
  - Merge waits on the seat, and on the store host's first R2 publish of the ledger.
next_actions:
  - Keep this pull request a draft. Merge only after the seat has the first m1 receipt that options_skew was published to R2.
  - Do not pin OPTIONS_SKEW_LEGACY_CHAIN back onto the six render-host calls.
do_not_redo:
  - Do not edit engine/options_skew.py or scripts/build_options_skew.py for this cutover. The flag stays available for a local process.
  - Do not make the R2 restore fatal. A failed copy renders the committed ledger and reports ledger_asof.
  - Do not gitignore data/options_skew/snapshots.parquet. Nightly is the only lane that advances the ledger.
danger_areas:
  - options_skew is not yet a data directory in scripts/publish_r2.py on this base. Pull request 7737 adds that registration. Until it is on main, fetch_r2 treats an unknown directory as a site directory.
  - render.yml job render's re-render step was 20424 characters on the base and 20454 after the two --emit tokens and the atomic-write comment. The guard fails above 20500.
---

# Handoff — skew cutover (A-F03-W2-3)

date: 2026-09-22
packet: A-F03-W2-3
branch: claude/mo-a-3-a-f03-w2-3-skew-cutover

Render hosts do not hold the ThetaData store. The store host accrues the ledger and publishes it. These workflows copy that ledger down, then emit the page from it. They do not open a chain.

The nine legacy pin lines are gone from the four caller files. The six launch lines end with --emit. Each of the three workflows restores the ledger in its own step before the step that launches the builder. The nightly desk script restores it before its launch line. A failed restore is a warning. Emit then renders the committed ledger and reports that ledger's as-of time.
