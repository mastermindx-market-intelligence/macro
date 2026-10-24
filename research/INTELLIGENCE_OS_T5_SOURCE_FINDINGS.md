# T5 source/data findings through output health

`python3 scripts/build_output_health.py --source-findings` consumes exactly one canonical T4 build and prints `postmortem.source_findings.v1`. Default JSON and summary modes are unchanged. The derived view is not persisted or used to route, rank, gate or size anything.

The existing postmortem owner supplies a new pure `classify_source_findings(view)` function. Its prior Prophet episode classifier, taxonomy, thresholds and aggregation remain unchanged. No episode, claim, grade or price history is read by this projection.

An exact producer/content parser diagnostic can establish `data_issue` while the retained health state remains null and the assessment says `could_not_look`. Generic parse codes, size caps, empty stores and unrecognized diagnostics remain `unclassified`.

`stale_feature` requires the named required input, a unique owned upstream row in the same snapshot, exact dependency attribution, the upstream's own content-decided stale state, a usable clock and finite age exceeding its positive SLA. The owner’s explicitly disclosed naive-clock coercion is retained; no new freshness calculation or calendar is introduced. Upper-bound attribution, missing/ambiguous inputs, reader-only or dependency-only clocks, absent SLA and insufficient evidence remain unclassified.

Groups count output/reason pairs within one supplied snapshot. One output can occur in several groups. The counts are health observations, not failed-engine counts, independent trials, causal failure rates or longitudinal identities. Healthy complete outputs are separately retained with null classification and `no_failure_observed`. Nulls and unavailable output counts stay explicit.

Qualification: 125 affected tests pass, including the real resolver-to-classifier and CLI paths. Independent review accepted both reproduced clock fixes. All 23 existing postmortem definitions and the entire prior module prefix are unchanged. The existing code-gated intelligence-registry job owns these tests; its two exact scope additions cover the new pure owner and the T12 authority-policy document dependency. Hosted containing-head selection and delivery remain owed.

This completes the narrow source/data T5 subset. Outcome-dependent classes such as false_breakout, empirical cross-engine clustering and the broader historical programme remain open. See `research/evidence/eval-os-tier-query-20261014/t5-acceptance.json`.
