Audited head: 1c3e2215ee395217f2d8349b4e9e41eb028bd497

# Group B, round-11 acceptance audit of PR #7905 (R196 contract, integrity, real release, hosted CI)

## Identity receipts and zero-drift proof (after the re-bind, 2026-09-30T01:18Z)
- `git -C $WT rev-parse HEAD` = 1c3e2215ee395217f2d8349b4e9e41eb028bd497; `git status --porcelain` empty.
- `git log --format='%H %P | %an | %s' --name-status b944cd35..1c3e2215`:
  - 1c3e2215ee39 (parent d5c9b9e87e31) | mastermindx-2 | chore: remove accidental connector test file -> D NOT_A_REAL_PATH
  - d5c9b9e87e31 (parent b944cd3574e0) | mastermindx-2 | x -> A NOT_A_REAL_PATH
- `git diff --name-status $B944 $HEAD`: empty.
- `rev-parse $B944^{tree} $HEAD^{tree}`: 0ea4e6658ef2f97a27e372d773866c706424b93d twice.
- `ls-tree $HEAD NOT_A_REAL_PATH`: empty; `test -e $WT/NOT_A_REAL_PATH`: false.
- Before the stop (00:24Z) the identity was b944cd35, status empty.

Reuse: every run marked [B944] below was made before the re-bind on $B944's tree (identical tree id), reused only because the proof above holds. Runs marked [HEAD] were made after it.

## STATUS: ACCEPT (group B families B0-B4), no release-blocking finding.

## RESULT
Release-blocking findings: none.

Notes (non-blocking, one line each):
- n-B-1 (observation, R196): within the searched bounds the body raises only TypeError among the five (the B-R10-B2 site, facts[*].source_span.document_id as list/dict, 11/11 runs on Q3's non-envelope route); ValueError, ArithmeticError, LookupError, AttributeError and the subclasses UnicodeDecodeError/KeyError/IndexError/ZeroDivisionError/OverflowError have no real input found, so their conversion is proven only by patched-body probes (fail-closed coverage limit).
- n-B-2 (observation, R196 cost): an injected KeyError in the legacy per-fact loop (inj3) fails only 1 of 1491 envelope-suite cases (a tamper case, r2 test_r139_s0...), but 145 of the 16 economic-observations suites in the same gate job, including controls; the gate as a whole catches it, the eleven envelope suites alone would not.
- n-B-3 (host): the two release-parser neighbour failures are `[cpython-3.12.2-python-org]` cases whose subprocess runs /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 and fails closed with "document-term parser runtime fingerprint is not released" (tests/test_capital_structure_document_terms.py:811); the test file and parser are unchanged since $R10HEAD. Host interpreter, not a candidate defect.
- n-B-4 (method): the commission-style run of my probe file inside the r10tree via a path outside that tree imported $HEAD's engine (34 passed, contaminated); the re-run with the file inside r10tree is the valid one (31 failed, 3 passed).

## B0 [B944]: group A's round-10 probe file, copied unchanged, run from my copy
- 3.12.13: 305 passed in 5.74s. 3.14.7: 305 passed in 5.66s. Every outcome passes, as the seat testified.

## B1: R196's contract
- Probe file `test_envelope_audit_probes_r11_b.py` (34 cases). [HEAD] fresh copy of $WT: 3.12.13 34 passed in 8.94s; 3.14.7 34 passed in 8.86s. [B944] same, 34/34 both.
  - At $R10HEAD (engine file replaced by git show, probe file inside that tree): 31 failed, 3 passed (the three untampered-acceptance cases pass; the wrapper cases fail because it does not exist; the TypeError case raises the raw TypeError, B-R10-B2).
  - Cases: untampered Q1/Q2/Q3 accepted with 20 rows; B-R10-B2 construction ([], ["x"], {}, {"a":1}): body raises TypeError, entry raises EconomicObservationError "a value has the wrong type or range where the validator reads it (TypeError)" with __cause__ a TypeError; all ten classes (five + five subclasses) by patched body: exact message naming type(exc).__name__, __cause__ is the raised instance; EOE passes as the same object with __cause__ None; RuntimeError, RecursionError, NotImplementedError, AssertionError, NameError, UnboundLocalError, ImportError, OSError, MemoryError, StopIteration, a custom Exception, KeyboardInterrupt, SystemExit, GeneratorExit propagate as the same object; _UNREADABLE is exactly the five; a malformed positional call raises TypeError before the body runs.
- Real-input inventory [B944]: the seat walker with g2common's validate pointed at `_validate_selected_facts` (the body, unwrapped), 3.14, Q3:
  - non-envelope route: 50,482 runs, baseline refused by the redirect, 50,471 refused, 11 EXC, all TypeError at facts.source_span.document_id (9 dict, 2 list). Wrapper converts all (probe above).
  - envelope route: alarm at 1,500 s after 28,619 of 50,482 runs: 0 EXC, 28,359 refused, 43 accepted JSON-equal, 217 accepted-different, all in fiscal_period (7, n-B1/n-B2) or sources[0] (210, n-B2); no facts[*] path accepted. Partial, see GAPS.
- Body-bug injection (cost claim) [B944], 3.12, eleven envelope suites (1,491 cases), trees with the injected engine (the counts prove the injected module was imported):
  - inj1, unconditional KeyError in `_validate_envelope_rows`' per-row loop (before line 464): 614 failed, including controls test_r193_control_the_unedited_workspace..., test_r195_control_the_unedited_workspace..., test_r190_control_..._is_accepted, test_r189_control_...
  - inj2, KeyError only for pg_diluted_eps in the same loop: 599 failed, including the same controls.
  - inj3, KeyError only for pg_diluted_eps in the non-envelope per-fact loop (after line 702): 1 failed in the envelope suites; 145 failed of 824 run in the 16 economic-observations suites (e.g. r13 test_x12_extractor_own_workspace_validates[*], r14 test_x11_honest_workspace_validates[*]).
  - Controls catch a hidden body regression on both routes; the seat's claim holds (see n-B-2).
- Untampered acceptance unchanged: the real-release demo output (below) is JSON-identical between $R10HEAD's engine and $HEAD's on 3.12 (b3_out_venv312_min.json vs b3_out_r10tree_v2.json), and all frozen controls pass at $HEAD.

## B2: integrity
## B2 integrity (git)
- `git diff --stat $R10HEAD $HEAD -- tests/ .github/`:
  .github/ci/legacy-jobs.yml | 3 +-; tests/test_pg_envelope_f1_probes_r10.py | 374 +++; 2 files changed, 376 insertions(+), 1 deletion(-)
- `git diff --name-status $R10HEAD $HEAD` (whole tree): M legacy-jobs.yml; M engine/company_intelligence/economic_observations.py; A OPUS_T1_ENVELOPE_AUDIT_R10; A SEAT_RULING_T1_ENVELOPE_R10; A tests/test_pg_envelope_f1_probes_r10.py. So test_pg_envelope_f1.py, _r1.._r9, tests/fixtures/pg_envelope/ are byte-identical; only economic_observations.py changed under engine/.
- `git log --format='%h %an | %s' $R10HEAD..$HEAD --name-only`: f89350d38d59 (freeze) -> legacy-jobs.yml, OPUS_..._R10, SEAT_RULING_..._R10, tests/..._r10.py; b4234d0877dc (R195) -> economic_observations.py; 98032fecc35c (R196) -> economic_observations.py; b944cd3574e0 (records) -> SEAT_RULING_..._R10 only, 2 lines changed (lines 31 and 132, the non-envelope walk wording). Matches the commission.
- legacy-jobs.yml hunk: the dossier job adds `tests/test_pg_envelope_f1_probes_r10.py` to `paths:` and appends it to the run line; nothing else.
- Gate line [B944], 3.12.13 venv312_min (pytest+pyyaml), the job's full run line incl. the R10 suite: 2315 passed, 174 skipped, 12 warnings in 462.55s; wall 466 s against timeout-minutes 20 (1,200 s).
- `tests/test_ci_pack.py -k curated_exclusive` [B944]: 2 passed, 143 deselected on 3.12 (110.5s) and 3.14 (106.5s).
- Eleven envelope suites: 3.14.7 [B944] 1491 passed in 431.40s; 3.12 inside the gate line above (all passed).
- Six release-parser neighbours [B944], /opt/homebrew/bin/python3.12: 2 failed, 287 passed; the two are the [cpython-3.12.2-python-org] cases, explained in n-B-3.

## B3: the real release [B944]
- Extracted script sha256 8dafb2c36e5c5a305679a868aac81e658d9e2ae6218a3c599b072d66371c52c3, equal to the pin in the demonstration file.
- 3.12.13 and 3.14.7: sources 6/6; FY26Q1/Q2/Q3 each 20 of 20, accepted; fy25_q4_layout, fy26_q4_layout, colgate, q3_under_q2_scope 0 present, accepted typed absences; tampered refused 9/9; failures 0. Output JSON identical across interpreters and identical to $R10HEAD's engine.
- Table check (b3_table_check.py): 79 rows/cells of sections 1-4 of the demonstration file against the script's output (values, oracle, EDGAR bytes at the receipt span, byte offsets, period, sha256, byte counts, refusal details, tamper refusals): 0 mismatches on both interpreters.

## B4: hosted CI and merge proof (re-bind B4)
Read 1 (2026-09-30T01:18:40Z):
- gh pr view: {"autoMergeRequest":null,"headRefOid":"1c3e2215ee395217f2d8349b4e9e41eb028bd497","isDraft":true,"labels":[],"mergeStateStatus":"CLEAN","mergeable":"MERGEABLE"}
- run 36650749017: {"conclusion":"success","headSha":"1c3e2215...","name":"ci","status":"completed"}
- run 36650748772: {"conclusion":"success","headSha":"1c3e2215...","name":"fences","status":"completed"}
- checks: ci-plan, contract-delta, ci-pack-0..11, ci-gate pass (run 36650749017); fence-pack pass (run 36650748772); ci-authority pass (run 36651274200); ci-authority/main, capability-broker, grader-manifest, self-mod-fence pass; trusted-ci and three fork-only jobs skipping. Verbatim in logs/b4_read1.txt.
- ci-authority/codex/merge-queue-pilot: fail (reported separately by Sol's ruling; outside STATUS).
Merge proof:
- ls-remote: refs/heads/main 9b613935ba9a461394c3dddc5a50c4fcad28aa70; refs/pull/7905/head 1c3e2215ee39...; refs/pull/7905/merge 35a074c23450465deb9b70059b2c61d6c41d4010.
- gh api commits/35a074c2: parents [a0d842d82940f8f64310b70acfcb078a4540e7df, 1c3e2215ee39...]; a0d842d8 is an ancestor of origin/main (merge-base --is-ancestor rc=0), a main commit.
- `git merge-tree --write-tree origin/main $HEAD` with origin/main 9b613935ba9a: rc=0, tree c3685ec3564d6fee73d95a58715d190efb97d27e, no conflicts.
Read 2: verbatim in logs/b4_read2.txt (summarised in the return). Final identity recorded there.

## EVIDENCE
Logs: logs/job1.log (gate, curated_exclusive, neighbours), logs/job2.log (3.14 suites, B0), logs/qa.log (B3, probes, injections), logs/qb.log + walk/*.jsonl (direct-body walks), logs/b4_read1.txt, logs/b4_read2.txt, logs/mergetree.txt, b3_out_*.json, b3_table_check.py.

## GAPS
- Direct-body envelope walk on Q3 stopped at its 1,500 s alarm after 28,619 of 50,482 runs; Q1/Q2 and 3.12 were not walked by group B (the walk inventories exception classes, which do not depend on the interpreter; R195's walk is group A's A2).
- Gate line, curated_exclusive, neighbours, B0, B3 and the injections were run on $B944's tree (identical tree id), not re-run after the re-bind.
- Injection runs on 3.12 only; FAILED names in qa.log are the last 40 per run (counts are complete).

## DEVIATIONS
- The first B4 read was taken at 00:24Z on b944cd35 under the original B4; the re-bind B4 reads replace it.
- A kill/re-copy of the injection trees was rejected by the stop; the runs finished with symlinked config/lib/tests. The failure counts (614/599/145) show the injected engine was imported.
