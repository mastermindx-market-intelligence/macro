---
workstream: "WS:MARKET-MEMORY-W2C"
session: claude/ssd-market-memory-d1-causal-receipts-eb93e2287b52131a
model: codex
ended_because: ci_handoff
mission: >
  D1: preserve bounded causal diagnostics on the existing source-seal run receipt,
  then prove one ordinary scheduled window after normal deployment.
state_before: >
  The source seal returned not_eligible without observations. MM-G0 established
  that historical transport, no-bar and malformed causes were unrecoverable.
  Chairman directly assigned this D1 package to Codex task
  01a0c829-bb8a-7aa3-9910-35fe72d0e3df and explicitly instructed autonomous completion.
changed:
  - path: scripts/ingest_market_memory_sources_spy.py
    what: >
      Add bounded causal diagnostics to successful and rejected native run receipts;
      retain typed malformed envelopes, omit raw exception/provider content, and
      bind run identity to session, start time and implementation revision.
  - path: engine/neuralweb/market_memory_sources_spy.py
    what: Optional diagnostic reason on SealObservation; predicate and generation semantics unchanged.
  - path: tests/test_market_memory_m0d_v2.py
    what: Native CLI negative/positive controls, implementation identity, bounds and repeat-read checks.
verified:
  - claim: Baseline loses native diagnostics for all seven acceptance fixtures.
    command: >
      Load git show b01b7bd06efec81bd2fe08440f4dde3b1f87c651:scripts/ingest_market_memory_sources_spy.py
      into the scripts.ingest_market_memory_sources_spy module, then pytest -q
      tests/test_market_memory_m0d_v2.py -k d1_native_cli --disable-warnings.
    result: >
      RED: seven KeyError diagnostics failures, covering transport, no bar,
      malformed envelope/results/bar, unstable valid observations and a stable seal.
  - claim: Native diagnostics and existing source/deployment contracts pass locally.
    command: >
      python3 -m pytest -q tests/test_market_memory_m0d_v2.py
      tests/test_market_memory_sources.py tests/test_market_memory_source_deploy.py --disable-warnings
    result: GREEN - 157 passed; unrelated pre-existing pytest temporary-directory cleanup warnings.
  - claim: Current protected source paths did not change since the carrier base.
    command: >
      git fetch origin main; git diff --name-only HEAD origin/main --
      scripts/ingest_market_memory_sources_spy.py engine/neuralweb/market_memory_sources_spy.py
      tests/test_market_memory_m0d_v2.py
    result: No path differences on 2026-09-22; carrier base b01b7bd06efec81bd2fe08440f4dde3b1f87c651.
unverified:
  - claim: D1 is installed and an ordinary scheduled receipt retains the new diagnostics.
    what_would_verify: >
      After exact-head review, CI and merge, inspect the normal /opt/macro deploy,
      then read the source-spy-rest journal for one natural 04:00-04:05 UTC window.
      Preserve the receipt plus service invocation and implementation identities in the PR.
unresolved:
  - MISSION_COMPLETE is false until an ordinary scheduled receipt is preserved.
  - Historical missing causes remain UNKNOWN; this does not settle D2 health or D3 source-clock admission.
next_actions:
  - Finish independent review and exact-head hosted CI on the same carrier, then complete the normal release path.
  - Read and preserve one ordinary scheduled-window receipt; do not force or replay a source-seal window.
do_not_redo:
  - Do not edit the workstream reconciliation path owned by PR 6943.
  - Do not change seal windows, predicate, timers, v1 evidence or v2 admission rules.
  - Do not add a transcript service, observation store, retry owner or market generation for a diagnostic read.
  - Preserve both locked external carriers; only this eb93e2287b52131a carrier owns the edits.
danger_areas:
  - The journal is the existing run-receipt owner; returned Python data alone is not production proof.
  - /opt/macro advances during runs; capture implementation identity before polling.
  - Current host HEAD does not identify an earlier process; retain the receipt's revision and invocation.
---

D1 extends the existing JSON stdout receipt emitted by the service's CLI. The
projection is capped at 128 observations and 16,384 canonical JSON bytes. It
retains total/included counts and explicit completeness/truncation. The seal
predicate still evaluates every collected observation before projection.

The native CLI tests read exactly the JSON a journal consumer receives. Secret
sentinels in transport exceptions and malformed/provider envelopes must be absent
from stdout and logs. A 599-observation fixture proves truncation cannot change
the predicate's unstable result; repeated serialization is deterministic and
later run-start identities differ without touching market generations.

Protected Mastermind procedure was refreshed at
`2e5da23c48e4eed49f14608a5b4ee281f53cb817` (skillpack v1.0.1, bootstrap major 1).
The direct Chairman assignment is the current native task's intent/receiver edge.
This handoff is a continuation checkpoint, not production acceptance or a new
control-plane record. PR evidence will carry final review, CI, merge and native
scheduled-window receipts as they become available.
