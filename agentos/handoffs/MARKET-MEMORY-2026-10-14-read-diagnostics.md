---
workstream: "WS:MARKET-MEMORY-W2C"
session: claude/ssd-market-memory-read-diagnostics-01a1333c-683831c959bf73d7
model: codex
ended_because: ci_handoff
mission: Restore the real Market Memory journey while completing the original program.
state_before: Catalog BUSY did not identify the existing two read-slot holders.
changed:
  - path: app/market_memory.py
    what: Observe admitted read durations and BUSY holders without changing admission or response behavior.
verified:
  - claim: Original route behavior is preserved and observer failures are isolated.
    command: python3 -m pytest tests/test_market_memory_read_observation.py tests/test_market_memory_retained_saved_api.py tests/test_market_memory_retained_catalog.py tests/test_market_memory_retained_consumer.py tests/test_market_memory_playback_api.py -q
    result: 78passed before the additional isolated logging-profile test; four frozen route AST digests match.
unverified:
  - claim: Production catalog availability is repaired.
    what_would_verify: Installed source, real authenticated journey and logs identifying and resolving the held operation.
unresolved:
  - Worker artifact export refused its paths before transport; no alternate transport or replay.
  - Real Google return exposed an independent Settings source-reference loss being repaired in its own carrier.
next_actions:
  - Complete protected delivery, verify installed bytes and inspect actual diagnostic records.
  - Resolve the observed performance cause without widening admission or caching authorization.
do_not_redo:
  - Preserve accepted August ABSTAINED and STOPPED results and frozen E0 membership109.
danger_areas:
  - Observability and CI do not prove performance, evidence utility or study admission.
prs: [6528, 9228, 9281, 9295]
---

Scope remains28tasks and49cases. See research/MARKET_MEMORY_READ_DIAGNOSTICS_2026-10-14.md.
