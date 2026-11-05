---
key: MAS28-CALIBRATION-REMAIN-REPORT-ONLY
question: >
  What does the frozen representative V1 calibration establish, and should it change
  the accepted PR-linkage validator's report-only authority?
answer: >
  Retain REPORT_ONLY. Accept the bounded missing-versus-invalid report-wire repair
  subject to exact-head source release checks. The real historical corpus supports
  scoped header judgments, not estate accuracy or enforcement. Preserve all incomplete
  and execution-invalid observations, and do not commission a hard gate.
rationale: >
  Ninety-two real PRs across three repositories and 47 hostile controls were frozen
  before replay, with an independently authored label ledger. One real PR exposed a
  report validator defect: present-invalid fields normalized to null were mistaken
  for literally absent fields. The minimal correction changes only that execution
  failure; 133 existing semantic report hashes remain unchanged and five original
  resource-limit refusals remain invalid. Zero fully observed real cases means real
  complete-denominator false-positive and false-negative rates are unavailable.
alternatives:
  - option: Promote the validator to a merge or execution gate
    why_not: Incomplete historical dependency evidence cannot support that authority or accuracy claim.
  - option: Truncate oversized historical bodies or manufacture missing snapshots
    why_not: It would change frozen observations and conceal operational refusals and uncertainty.
  - option: Treat every observed unlabeled finding as a false positive
    why_not: A finding outside the independent label scope has no adjudicated ground truth.
  - option: Rewrite the 46-rule manifest while fixing the report-wire invariant
    why_not: The defect is in missing-field consistency validation, not the frozen grammar or rule semantics.
evidence:
  - research/MASTERMIND_AGENT_OS_V1_CALIBRATION_2026-10-04.md
  - research/agent_os_calibration/2026-10-04/manifest.json
  - research/agent_os_calibration/2026-10-04/before.json
  - research/agent_os_calibration/2026-10-04/after.json
  - "Evaluator repair b09fea5f6d3fb8c1c3cc686dc2247fd15ba8f5d0; 456 focused tests pass"
  - "Independent quant-coder semantic review and independent explorer exact-object review approve b09fea5f6d3fb8c1c3cc686dc2247fd15ba8f5d0"
  - "Real incomplete judged pairs: R001 8 TP/27 TN; R009 0 TP/27 TN; R011 1 TP/27 TN; R012 6 TP/27 TN; zero scoped FP/FN"
affects:
  - WS:AGENT-OS
  - MAS-28
  - lib/pr_linkage_validator.py
confidence: high
reversibility: easy
decided_by: session
decided_at: 2026-10-04
---

This decision records the commissioned calibration ruling. It preserves the current
46-rule contract and the R028 reconciliation; it does not supersede their source law.
The result is PARTIAL_EXECUTION (exit 2), with every attempted observation represented.
Five real `RESOURCE_LIMIT:value_bytes` results are operational invalids, not semantic
false negatives. All 87 evaluable real cases remain incomplete. The 123 independent
header judgments have 15 TP, 108 TN, zero FP and zero FN; their limited scope must travel
with those counts. Synthetic hostile controls are reported separately.

No workflow runner, enforcement gate, network collector, Linear writer, policy epoch,
new snapshot store, or future enforcement commission is introduced. Any enforcement
review would require a separate assignment and adequate complete observations. W4 and
V1 closure still require their own review, CI, merge and cold-session acceptance.
