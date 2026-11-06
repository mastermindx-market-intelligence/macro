---
key: PROPHET-SOURCE-HASH-NEEDS-A-FROZEN-CONSUMER-OBJECT
claim: >
  Hashing a mutable source path before and after a Prophet build does not prove which
  bytes each consumer used: an A-to-B-to-A rewrite can leave matching boundary hashes
  while live origination, Arena, or a shadow ledger consumed B.
falsifier: >
  Run `python -m pytest -q
  tests/test_prophet_bridge.py::test_origination_uses_supplied_frozen_board_without_rereading_path
  tests/test_prophet_bridge.py::test_build_prophet_reuses_one_frozen_board_after_source_freeze`;
  falsify the claim by making both pass while production consumers still reopen the
  mutable source path after freeze.
so_what: >
  Parse the board once from the exact frozen bytes and pass that object, with isolated
  deep copies where mutation is possible, to live origination, Arena, legacy shadow,
  and index disclosure. Byte snapshots and consumer inputs must share one authority.
kind: architecture
verified_at: 2026-09-15
verified_by: >
  Independent Cursor Codex High review of 4d73bf68b817 identified post-freeze reads in
  scripts/build_prophet.py; RED-first regressions failed on that head and passed after
  repair commit aef3120e4ce1. Exact repaired-head re-review reported zero findings.
scope: [macro, prophet-us, scripts/build_prophet.py, engine/prophet_bridge.py]
confidence: verified
---
