# Validation evidence

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
