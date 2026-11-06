# Agent OS V1 / MAS-28 frozen calibration

Operation: `agent-os-v1-closure-20261003-astra-001`.
Ruling: `DEC:MAS28-CALIBRATION-REMAIN-REPORT-ONLY`.

The representative replay is complete as an observation exercise and remains
**PARTIAL_EXECUTION / REPORT_ONLY**. It is not an estimate of estate-wide accuracy.
Implementation, hosted release, and V1 completion are separate acceptance states.

## Immutable inputs and evaluators

- Macro capture/base evaluator: `f9ed175800257b228166dabe8b3ac9a55e74e237`.
- Repaired evaluator: `b09fea5f6d3fb8c1c3cc686dc2247fd15ba8f5d0`.
- Unchanged manifest SHA256: `2e97ad7acd0aec77ef18dbd76a1b3f2bbf8b7d4585e938498615de1917aa71aa`.
- Frozen corpus file SHA256: `c8599aa47f10c86717d0ce74f3a39c5b2805558b953a273d8bb79ccd9a2654bd`.
- Frozen separate label file SHA256: `01a39bf10c5144c79211cb1c427121d72abd613617af16411f0ce7e6d8c5264b`.
- Normalized observation digest: `23f62528c6b586a77ddc52c6b1094e4e676e5b4c5d17217a0bb1804b53804828`.
- Normalized independent ledger digest: `da90d68a4048c6a7102358d37a2c63be6c6291a5c20cb6d238232a791d1b4ecd`.
- Runner SHA256: `2bf77d621e2bbe06a19384fccef2dbbbdc374a98ac881af5e256a8ad55675cbe`.

Sanitized per-case reports and source-byte hashes are committed under
`research/agent_os_calibration/2026-10-04/`. Full observation bodies, exact changed paths,
selection queries, provenance and the independently prepared pre-replay label ledger
are private evidence under
`/Volumes/Mastermind/agent-evidence/agent-os-v1-closure-20261003-astra-001`.
The private corpus is an immutable calibration input, not another organizational store.
Raw bodies and logs are deliberately not published in Git.

## Coverage and independent labeling

The frozen corpus contains 92 real PR observations across Macro, Mastermind and Terminal,
plus a positive hostile control and 46 independently targeted rule mutants. Real header
labels were authored without replay output; the runner requires exact ID and observation
bindings to the separate ledger and rejects label disagreement, duplicates or omissions.
Selection categories overlap; category membership is not 92 disjoint positive controls.

- 23 canonical tracked candidates across all three repositories.
- Five explicit non-final Macro examples: #6106, #6126, #6328, #6383, #7192.
- Five actual records-only, exact `merge-is-done` examples, verified by all changed paths:
  Macro #6388, #6393, #6392, #6087, #6086.
- All 44 hits returned by the frozen exact `Portfolio-Mode: maintenance_exception`
  searches across three repositories (22 Macro, 14 Mastermind, 8 Terminal). Of these,
  34 are canonical maintenance declarations; seven are template text rather than genuine
  positive controls. Search completeness is bounded by those exact recorded queries.
- Four canonical architecture candidates: Macro #6419/#6568 and Terminal #723/#768.
- Two real workstream creation/recovery examples: Macro #6079 and #6216. These carry
  historical declarations; neither is manufactured into a modern `creates_workstream`
  positive control. #6079 exceeds the unchanged value limit; #6216 has extended Completion.
- Required historical anchors: Mastermind #91/MAS-48 and #96/MAS-75, Macro #6104/#6119.
  No immutable native-quorum history was available; that observation stays unavailable.

Current GitHub body/head/base/path snapshots do not reconstruct historical Linear state,
Agent OS state at base, policy epoch, path-policy snapshots, or native acceptance history.
Those unavailable dependencies remain explicit in every report. In particular, a PR body
claiming records-only is insufficient: #6411 has 2,319 actual mixed changed paths.

## Results

| Cohort | Before complete / incomplete / invalid | After complete / incomplete / invalid |
|---|---|---|
| 92 real historical | 0 / 86 / 6 | 0 / 87 / 5 |
| 47 hostile controls | 33 / 14 / 0 | 33 / 14 / 0 |

The real cohort has **123 independently judged incomplete header/rule pairs** after repair:
R001 8 TP / 27 TN; R009 0 TP / 27 TN; R011 1 TP / 27 TN; R012 6 TP / 27 TN.
Total: **15 TP, 108 TN, zero scoped FP, zero scoped FN**. Before repair: 14 TP, 108 TN,
zero scoped FP/FN over 122 pairs. These are rule-level, limited-scope counts; they are not
123 complete PRs. Every real complete-denominator FPR and FNR is `null`.

The hostile complete subset has 32 TP / 46 TN / zero FP/FN. Its incomplete subset has
14 TP / zero FP/FN. All 46 intended mutant rules appear, but deliberately incomplete
mutants are excluded from complete-denominator rates.

Exactly one observation changes: Macro #7039, previously a report-wire `TYPE_MISMATCH`,
now returns incomplete `REFUSE_METADATA`. Its literally missing Linear field remains
R001, while present-invalid Authority and Completion retain R011/R012. Of the 139 cases,
133 existing semantic hashes are unchanged, one execution failure is repaired, and five
original `RESOURCE_LIMIT:value_bytes` failures remain unchanged: Mastermind #112/#115,
Macro #6079/#6104/#6119. Operational invalids are excluded from semantic confusion counts
and remain visible per case; they are neither silently dropped nor counted as false negatives.

Observed but unjudged real findings after repair (not false-positive claims):

- R042: 87 observations.
- R029: 41 observations.
- R033: 33 observations.
- R040: 31 observations.
- R054: 26 observations.
- R035: 26 observations.
- R003: 22 observations.
- R020: 15 observations.
- R012: 9 observations.
- R011: 9 observations.
- R006: 9 observations.
- R009: 7 observations.
- R005: 7 observations.
- R032: 4 observations.
- R001: 4 observations.
- R043: 1 observations.
- R008: 1 observations.

The largest cluster is R042, missing path-policy observation. Other clusters mix absent
historical dependencies with real authoring shapes; current data cannot adjudicate them.
Every per-rule complete/incomplete count, unresolved dependency and finding ID is retained
in `after.json`, separately from label coverage.

## Minimum repair and validation

The source repair subtracts validated present-invalid field evidence only when comparing
R001's literal `missing_fields` with normalized null fields. The full null set still governs
canonical/legacy report strictness. Manifest, enum values, rule semantics, and authority
remain unchanged. The discriminating regression failed before repair with TYPE_MISMATCH;
after repair all **456 `tests/test_pr_linkage_*.py` tests pass**.

Two independent read-only reviewers approved exact source commit `b09fea5...`: a quant-coder
reviewed metrics, immutable before/after hashes and semantic isolation; a separate explorer
inspected Git objects and the closed report-wire invariant. Neither claims hosted CI or merge.

Replay, in a checkout whose evaluator bytes match the named immutable commit:

```sh
python3 scripts/pr_linkage_calibration.py /Volumes/Mastermind/agent-evidence/agent-os-v1-closure-20261003-astra-001/corpus.v1.json --labels /Volumes/Mastermind/agent-evidence/agent-os-v1-closure-20261003-astra-001/labels-before-evaluation.json --source-sha b09fea5f6d3fb8c1c3cc686dc2247fd15ba8f5d0 --output /tmp/agentos-calibration-replay.json
```

Expected exit is **2**, with a complete PARTIAL_EXECUTION artifact, because the five
resource refusals are preserved. The runner verifies evaluator and manifest bytes against
`git show` at the supplied SHA, replays twice for determinism, and atomically publishes the
report. A failed source pin leaves an existing output untouched. No workflow gate is added.
