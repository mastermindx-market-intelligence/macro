# Prophet CI weight calibration — 2026-11-05

## Finding and correction

Registering four required test modules in existing CI owners increases the existing planner's estimated weight. The same owner IDs are selected before and after; no job or pack is added by any of the three narrow-change probes.

The canonical producer compared published f3c79cfed26286c25592e487939a59fa2dbfc7ec with parent39f792bb3d0902fe46127b455c35f8f98d307080. Both revisions have identical product, test and selector source; only the manifest and the preceding evidence packet differ. It used existing packing_probe_spec, packing_probe_measurements and packing_probe_breaches helpers, with exact manifest Git-blob checks.

| Probe | Jobs before/after | Estimated weight before -> after | Packs before/after |
| --- | --- | --- | --- |
| templates/index.html | 137 /137 | 5912 ->5918 | 10 /10 |
| scripts/build_free_content.py | 137 /137 | 5927 ->5933 | 10 /10 |
| engine/prophet/plan_book.py | 131 /131 | 5668 ->5674 | 10 /10 |

The six-unit increase on every probe is exactly prophet-lab64->66 plus unrun-grading-board40->44. The same-date suite changes washout-turn-organ137->139, but none of these probes selects that owner. All command counts and 800-character buckets are unchanged. These are planner estimates, not measured execution times.

The gate's existing diagnostic at scripts/check_contract_delta.py:1124–1137 explicitly supports re-basing a measured ceiling for intended added coverage, with the measurement recorded in the test docstring. The preceding November4 entry follows this same process.

Only the three breached max_weight literals in tests/test_ci_pack.py move, each by exactly six, with no padding. The existing job ceilings137/138/131, ten-pack ceiling, runtime timeouts, admission behavior, all suites and all selectors are retained.

## Evidence

- paired-measurement.json: exact inputs, source identities, owner-weight attribution, canonical before/after results and selected-ID equality; SHA256 bafd5037a9560b933634237a10e6555abd2bcdecc9e7b1bb7c2582ba987d4266.
- producer-readback.txt: original retained Studio72782 output, completed exit0.
- validation.json /validation.log.txt: focused existing packing-probe regression on the amended source.
- calibration.diff.patch: exact source change.

The accepted Prophet page, protected payload, publication pair and original screenshots are unchanged. This local calibration does not claim current-head hosted CI, merge, deployment or signed-in production acceptance.
