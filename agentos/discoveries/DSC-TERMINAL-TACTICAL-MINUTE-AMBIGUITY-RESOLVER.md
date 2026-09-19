---
key: TERMINAL-TACTICAL-MINUTE-AMBIGUITY-RESOLVER
claim: >
  Macro PR #7275 head afa4a50ec0149928063e6d650a9689b41b67b005 implements a pure research-only resolver plus a bounded client-arrival observability path
  that can disambiguate target-first versus adverse-first inside one five-minute interval only from a complete,
  ordered, adjusted-basis, positive-volume five-minute set of one-minute SessionTape observations; missing or
  malformed evidence remains unavailable and same-minute unresolved order remains ambiguous.
falsifier: >
  Read engine/entry_radar/minute_resolution.py and the TTID1 cases appended to
  tests/test_entry_radar_w4_c3_reader.py on #7275 head afa4a50ec0149928063e6d650a9689b41b67b005. A path that fetches/persists data, emits an entry event,
  sorts/fills incomplete minutes, accepts zero-volume price evidence, or guesses an open-between-thresholds
  same-minute order refutes the claim. Hosted review/CI or a later source head may revise acceptance state.
so_what: >
  TTI no longer needs a second one-minute warehouse merely to resolve selected five-minute path ambiguities.
  After the existing minute source is qualified for the relevant clock/history mode, R1-B or a later Radar evaluator
  can consume this bounded resolver. Do not treat the PR as production proof, historical knowledge-time, a one-minute
  strategy, or permission to open R1-B outcomes before its registered gate.
kind: architecture
verified_at: '2026-09-17'
verified_by: >
  #7275 head afa4a50ec0149928063e6d650a9689b41b67b005. Pre-commit exact-byte proof for the live-arrival projection: complete C3/receipt/resolver suite 83 passed; full existing Radar W1-W6 regression 1515 passed/2 skipped; compileall and diff-check passed. The resolver retains source_clock_proven=false / availability_time_unproven. The reader separately emits source_evidence_class=prospective_fetch_arrival_receipt with authority=source_arrival_observation_only, and the existing live C3 health block projects the latest in-memory receipt without gating detector behavior. Hosted current-head contract/review pending.
scope:
- WS:TERMINAL-TACTICAL-INTELLIGENCE
- WS:LIVE-ENTRY-RADAR
- engine/entry_radar/minute_resolution.py
- tests/test_entry_radar_w4_c3_reader.py
confidence: verified
---

Capability state is BUILT_NOT_PROVEN. PR #7275 requested independent review from mastermindx-2; a review request is not a review result. The resolver itself makes no provider call and carries authority=research_resolution_only.
