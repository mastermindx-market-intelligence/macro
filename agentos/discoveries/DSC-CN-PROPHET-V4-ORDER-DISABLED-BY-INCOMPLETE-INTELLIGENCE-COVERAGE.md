---
key: CN-PROPHET-V4-ORDER-DISABLED-BY-INCOMPLETE-INTELLIGENCE-COVERAGE
claim: >
  At Macro eb9e91961ddc4f3043d0dad358602525e66eccda, the 2026-09-07
  cn_prophet_v4 artifact requests intelligence-first ordering but actually uses
  cn_prophet_v3_score because four of 1620 ranked rows have no_edge_evidence;
  the other 1616 measured rows do not keep intelligence ordering active.
falsifier: >
  Read site/factordata/china_standouts.json at the pinned commit and inspect
  ranking.ordering and ranking.input_coverage.intel_interest. A different effective
  order, complete measured coverage, or a different reason/count disproves the
  pinned observation. A later current artifact with genuine complete inputs and
  intel_order_active=true clears the current degradation but does not rewrite
  this historical observation.
so_what: >
  Diagnose the four actual upstream evidence failures and their eligibility before
  proposing another Prophet ranker or changing fallback semantics. Preserve
  measured zero versus missing, disclose requested versus effective method, and
  do not assume that the cn_prophet_v4 version label proves intelligence-first
  ordering. Restoring method activation is not proof of better investment returns.
kind: data
verified_at: 2026-09-08
verified_by: >
  Successful read-only git show of
  eb9e91961ddc4f3043d0dad358602525e66eccda:site/factordata/china_standouts.json
  parsed ranking.ordering and ranking.input_coverage.intel_interest; exact source
  reads of engine/china_board_rank.py:528-596 and
  engine/china_intel_interest.py:284-314 verified the all-measured coverage law and
  no_edge_evidence meaning. See the cited forensic assessment for the complete
  observation boundary and unresolved producer diagnosis.
scope:
  - macro
  - WS:PROPHET-US-V4-RECOVERY
  - engine/china_board_rank.py
  - engine/china_intel_interest.py
  - scripts/build_china_library.py
  - site/factordata/china_standouts.json
confidence: verified
---

# Meaning and continuation

Full assessment and operator continuation:
`research/prophet_v4/ROTATION_INTEGRATION_FORENSIC_ASSESSMENT_2026-09-08.md`.

The source already contains a bounded theme_timing score channel and a separate
intelligence-ordering design. This discovery does not claim China has no sector
integration. It identifies the current effective-order degradation and prevents
another session from mistaking implementation presence or a v4 label for a
working intelligence-first bake.

The exact four ticker identities, eligibility states and failed upstream sources
were not established in this assessment. A later optional host diagnostic was
blocked before execution; it was not retried through another carrier. Do not
fill that gap with guessed names, synthetic zeroes, an assumption that the rows
are ineligible, or an unreviewed coverage-denominator change.

Next bounded action belongs to the existing China source owner after current
carrier/path/effect reconciliation: trace those four records, recover genuine
inputs when possible, and return either an unchanged-formula repair with natural
producer/served-order proof or a separate method-decision request. No source
writer, runtime Job, worker assignment, watcher, deployment, rank/gate/size/trade
change or cross-market owner transfer is created by this discovery.

This records-only finding is not authenticated production acceptance. The supplied
screenshots and committed artifact explain the observed product problem, but the
real entitled production response and browser journey remain separate proof gates.
