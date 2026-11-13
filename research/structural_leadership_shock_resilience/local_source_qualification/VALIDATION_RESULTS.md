# Validation evidence

## Current-main recovery — 2026-11-06

The unchanged original adapter was tested with the first new regression set:
**43 failures / 106 passes / zero errors or skips** across149 cases. A separate
actual subprocess CLI packet with `coverage_by_era=[]` reproduced an
`AttributeError` and no structured report. These failures preceded source repair.

The repair validates nonblank textual receipt metadata, nonempty list/tuple
evidence references, coverage mapping shape and actual canonical calendar
intervals for peers. Interval membership remains start-inclusive/end-exclusive,
with only `None` denoting an open end. Scientific thresholds and all original
source/detector/identity contracts remain unchanged.

Current-main verification of the three original focused targets now passes
**625 tests**, zero failures, errors or skips, in13.10s pytest execution
(14.301s parent wall time), using Python3.14.7 on the admitted host.
The default data guard obtained zero initial dirty entries; the default module
guard recorded zero leaks. Neither guard was disabled or modified. Hosted
Python3.12 execution remains separately owed.

Adapter SHA256:
`e62fde6b06c0cdff76036802ce2345b4f099b7f65d9840816cb490093b474eb6`.
Test module SHA256:
`21ea28ddc8f82762d833e86bf9153059122e4fc70e8787b48627b98df1e422fd`.
Current source receipt SHA256:
`2f4bd25c3d4237e751871268d22751e803a8a2b434d5b136fdf78f68b95238a2`.

The previous actual-data result and October test/review artifacts are preserved
unchanged. New synthetic success does not alter NOT_ADMITTED, grant source rights,
prove population parity, produce scientific estimates or complete the original r2.
Current source-only engineering self-check is not represented as independent review.

## Retained October validation evidence

The counts, revisions and procedures below describe the historical candidate.
Current delivery requirements and the unstarted r2 disposition are recorded in
`EXACT_NEXT_ACTION.md` and the original PR.

Test-first RED: the adapter was absent; F01 failed with the explicit
`research adapter not implemented` assertion. An earlier fixture-import attempt
produced setup errors, was corrected, and is not counted as the behavioral RED.
First GREEN: 54 synthetic tests passed. First combined focused run: 384 passed.

Supplementary RED: 6 failures / 57 passes, exposing the missing stdin path,
calendar argument, study-reference/coverage guards and lagged-factor/cutoff helpers.
After implementation, one CLI firewall defect remained: it treated the metadata
word PREOUTCOME as an outcome value. The correction retained outcome-column and
protected-path rejection while accepting the frozen spec reference.

Additional adversarial REDs exposed same-day timestamp leakage, omitted terminal
cash, and protected-family file-name variants. Each was corrected after its
failing fixture. A further RED rejected security-as-issuer misuse. Static
imports and in-process CLI entrypoint tests give the CI planner an exact,
unambiguous dependency closure; earlier subprocess runs also tested packaging.
The cooldown fixture also tests D+63 versus D+64 explicitly.

Final focused command at this artifact revision:

```sh
python3 -m pytest tests/test_slr_local_source_qualification.py tests/test_winner_autopsy.py tests/test_dataos_identity.py -q --tb=short --basetemp=/Volumes/Mastermind/evidence/slr-p0-source-qualification-01a11e3b/pytest-review-green2
```

Result: **418 passed**, exit 0, 5.48 seconds. Of these, **88** are new synthetic
qualification tests and **330** are incumbent detector/identity tests. The first
two runs had an unrelated pytest cleanup warning on an old temporary Chromium
directory; isolated basetemp runs have no warning. No cleanup of that other
session's directory was attempted.

`python3 -m compileall -q research/structural_leadership_shock_resilience/local_source_qualification`
and `git diff --check` passed. Raw test logs are outside the repository; their
exact digests and last-line summaries are in `LOCAL_TEST_RECEIPTS.json`.

The full repository suite was not run in this sparse carrier: repository law
explicitly forbids that because omitted data/site paths create false failures.
Hosted binding checks remain a separate exact-head release gate. Independent
implementation review and independent Web scientific admission are separate gates;
no self-review is represented as independent approval.

No SLR historical onsets/prices/forward outcomes or protected CR1/AF1/RH1 stores
were read. SEC endpoint access is sample evidence only. Source qualification,
Detector-D population parity, first-shock incidence and science remain blocked.

Independent review of the initial commit returned CHANGES_REQUIRED. Twelve
new counterexamples failed before the repair. The first repair run retained one
missing-clock exception (412 passed / 1 failed); after correction and dated
sector/inception supplementary coverage, the focused suite passed 418 cases.
The initial review return is adjudicated as useful findings, never candidate
approval. A second bounded review must examine the repair candidate.
