VERDICT: PASS_WITH_NOTES

B4 nightly capture: re-review of repair commit 628cc4c69ec1a561530ac700f862b102242c4770 (PR #9959, parent b2efcfade9dc23f29c63b559ffe13874006596de). ROUTE: review, MODE: READ_ONLY.

Scope: scripts/capture_prophet_b4_same_read.py and tests/test_capture_prophet_b4_same_read.py only. Both files in the b4n_mt_tree export are byte-identical to `git show 628cc4c:<path>` (checked with cmp). In this report, "script:N" means the script at that commit and "test" means the test module.

Summary. Both blockers are closed: F1 and F2 each have a code path and a discriminating test that agree, and each test fails when its fix is reverted. F4, F5, F7, F8 and F9 are closed. F3 is PARTIAL: the repair adds audit fields but does not restrict `--root`, and the commit message relabels "F3" as the digest fix, which was the review's F5. F12 is PARTIAL: some malformed day-file classes still produce a traceback with exit 1. The repair introduced one new minor finding (N1, day-file mode is now 0600) and two nits.

## F1 (was BLOCKING): verdict trace persisted in facts. CLOSED.
- Code:
  - script:128-130 `VERDICT_FIELDS = ("state","entry_open","chase_state","availability_id","blockers","reasons")`.
  - script:329-333 `_facts_without_verdict` strips them.
  - script:134 `VERDICT_TRACE_KEYS`. At script:368-373 the write-time guard refuses a top-level `blockers`/`reasons`. At script:378-385 `_walk_mappings(row["facts"])` refuses either key in any mapping nested in facts. `_capture_row` always calls the guard (script:439).
- Lawful rows are not refused:
  - `unavailable_reasons` is a distinct key, so the guard ignores it.
  - Only `facts` is walked. The evaluator's closed output (prophet_entry_availability.py:499-505) has no nested mapping carrying `reasons`/`blockers` once the top-level pair is stripped (zone, invalidation and source_receipts only).
  - The real-chain EVALUATED row in test_evaluated_row_persists_facts_only_and_round_trips_the_verdict passes under the repair.
  - A probe row with state=EVALUATED, `unavailable_reasons=["IDENTITY_ALIAS_UNRESOLVED"]` and nested facts was accepted.
- Tests:
  - test_row_builder_strips_the_verdict_trace_blockers_and_reasons asserts `row["facts"] == {quote_age_seconds, gate_inputs}`.
  - test_write_fence_refuses_a_smuggled_verdict_trace_anywhere_in_facts covers three cases: top-level, in facts, and nested in a list in facts. The control row passes.
- Discrimination (run): a plugin reverted VERDICT_FIELDS to the old 4-tuple. Result: 3 failed / 17 passed.
  - test_row_builder_strips… fails at `{"blockers","reasons"} <= set(VERDICT_FIELDS)`. Without that line it would still fail, because facts would carry the trace and the guard refuses it.
  - test_write_fence… fails because building the control row raises the refusal.
  - test_evaluated_row_persists… fails because the real row's blockers now trip the guard. This also shows that the guard independently backstops the stripping.
- Docstring overclaim removed: script:40-43 now says the verdict is NOT re-derivable from a row.

## F2 (was BLOCKING): key collision when security_id is None. CLOSED.
- Code:
  - script:486-501 `_row_key_of = (stamp_date, candidate_source_event_id, candidate_generation_id, strategy_definition_id)`.
  - Used at script:558, 570, 569 (sort) and 586.
  - `candidate_source_event_id` is `candidate:{stamp}:{ticker}:{board_definition}` (script:262-264), so it is unique per candidate per stamp regardless of binding.
- Test: test_capture_key_is_the_candidate_source_event_so_unbound_candidates_never_collide. It uses 2 bound and 2 unbound candidates; the unbound ones go through the script's own fallback envelope via a raised RuntimeOwnerFactError, giving security_id None and generation = snapshot id. Expected: exit 0, 4 rows written, 4 distinct keys, and an idempotent second night.
- Discrimination (run): a plugin restored the old security_id key. Result: 2 failed / 18 passed.
  - The F2 test fails with `assert 2 == 0` on the first `--nightly` run. LONE and ORPH collide on `(stamp, None, gen, psd)` with differing bodies, which is the false conflict.
  - test_conflict_reports… also fails because it asserts `conflict[1]` is the source event id.

## F3 (SHOULD_FIX): `--root` accepted with `--nightly`. PARTIAL (minor).
- Not repaired as requested. `--root` is still parsed (script:738-741) and honoured in durable mode (script:631; run at 744-749). There is no `nightly and root is not None` refusal analogous to script:615-620.
- Mitigation only: the run document carries `root_override` and `data_root` (script:704-705), asserted at test:255-260 in the durable test. A durable append can still be redirected to any tree; it is now just visible in the receipt.
- The commit message labels the digest fix as "F3", but that was the review's F5. The ruling it cites (F27) was not found in the seat records (grep of research/ and the git log found only this commit). A waiver of F3 is therefore UNVERIFIED.
- Seat: either refuse `--root` with `--nightly`, or record the waiver.

## F4 (SHOULD_FIX): `--dry-run --nightly` lane-gated and untested. CLOSED.
- Code:
  - script:623 `if nightly and not dry_run and not nightly_advance_enabled()`.
  - The write happens only under `nightly and not dry_run` (script:692-693). The single `mkdir` lives inside `_merge_and_write` (script:580), so a dry run cannot create a directory or file.
- Test: test_dry_run_is_not_lane_gated_builds_every_row_and_writes_nothing (lane=None). It asserts no file and no b4_capture dir.
- Discrimination (run): re-imposing the lane gate before the dry-run branch gives 1 failed (that test).
- Note: the dry run still requires the fixed NATIVE_LIVE_ROOT to exist (script:636-642), and `--live-root` is refused with `--nightly` (script:615). The preview therefore runs only on the production host. This is acceptable.

## F12 (SHOULD_FIX): CaptureDayFileError traceback / exit 1. PARTIAL (minor).
- Code: main catches exactly `CaptureDayFileError` (script:765-775), prints the `{"error":{"type","detail"}}` document and returns 2. Because the except clause is narrow, no other exception class is masked as exit 2.
- Test: test_malformed_committed_day_file_is_a_typed_error_exit_2_and_writes_nothing. It feeds a non-JSON line and checks: exit 2, bytes untouched, no temp sibling. It is discriminating by construction: without the except clause the exception escapes `_run`.
- Residual (probe run against `_merge_and_write`). These malformed classes still escape as tracebacks with exit 1; in each case the file is left untouched:
  - a non-UTF-8 day file: `read_text` raises UnicodeDecodeError, and script:527 catches only OSError;
  - a schema-shaped row with an unhashable key field (e.g. stamp_date a list): TypeError at the `committed[key]` dict use (script:559/567);
  - a committed row containing NaN: ValueError from `allow_nan=False` at script:582-585.
- Fix: widen script:525-528 to `(OSError, UnicodeDecodeError)`, and type-check the key fields in `_read_day_file`.

## F5 (NOTE): conflict carried full bodies. CLOSED.
- Code:
  - script:504-506 `_body_digest` = `"sha256:" + hexdigest`.
  - Both conflict raises (script:561-565 and 574-576) pass digests. CaptureConflictError stores digests only (script:191-198).
  - main prints the key, committed and incoming fields (script:754-763).
- Leak check: the message holds only the key tuple (stamp, source event id incl. ticker, generation id, strategy id), which is identity and not body content, plus two sha256 hex strings.
- Test: test_conflict_reports_body_digests_never_bodies asserts the `sha256:` + 64-hex shape and that `SOMETHING_ELSE` is absent.
- Discrimination (run): `_body_digest` reverted to identity gives 1 failed.

## F7 (NOTE): fence test cwd-relative and vacuous. CLOSED.
- The scan is anchored on `Path(capture.__file__).parents[1]` (test `_capture_stream_consumers`, test_no_product_builder_or_template_reads_the_capture_stream). A positive control plants `scripts/build_planted_consumer.py` in tmp_path and asserts it is reported.
- Residual nit: the three named engine files are still skipped silently when absent (`if not path.is_file(): continue`). A dynamic `importlib` string assembled from parts still evades a grep fence. Both limits are inherent and acceptable for a NOTE.

## F8 (NOTE): fixed temp name, no fsync. CLOSED.
- Code:
  - script:591-593 `tempfile.mkstemp(prefix=".{name}.", suffix=".tmp", dir=target.parent)` gives a unique name in the same directory.
  - script:596-599 write, flush, `os.fsync`.
  - script:600 `os.replace(temp, target)` is the ONLY write to `target`; the payload goes to the temp fd only.
  - script:601-603 `except BaseException: temp.unlink(missing_ok=True); raise` unlinks the temp on any failure, including KeyboardInterrupt.
- Probe (run): with fsync forced to raise OSError, the directory contains only the original day file and the bytes are unchanged.
- Nits:
  - no directory fsync after `os.replace`, so the rename is not crash-durable on every filesystem;
  - if `os.fdopen` itself raised, the raw fd would leak (theoretical).

## F9 (NOTE): widened catch with EpisodeContractError. CLOSED (code; no dedicated test).
- script:167-171 `_CONTRACT_ERRORS = (RuntimeOwnerFactError, EntryAvailabilityContractError, CandidateStateContractError)` is identical to engine/prophet_b4_same_read.py:85-89.
- The sources adapter catches EpisodeContractError internally (prophet_entry_availability_sources.py:782/885/902), so the narrowing removes no lawful per-row path.
- No test pins that an escaping EpisodeContractError propagates. Acceptable for a NOTE.

## NEW findings introduced by the repair
- N1 minor: the day file's permission mode regressed to 0600. `mkstemp` creates the temp with mode 0600, and `os.replace` keeps it.
  - Probe (umask 022): the written day file is `0o600`. The pre-repair `write_text` + `replace` produced 0644 under the same umask.
  - Any reader of `data/us_prophet_rank/b4_capture/**` under another uid (an R2/rsync publisher, a web user, a different runner account) loses read access. Git does not track this bit.
  - Fix: `os.fchmod(handle, 0o666 & ~umask)`, or chmod the temp before the replace.
- N2 nit: the docstring overclaims the guard's reach. script:44-45 says the guard refuses any `blockers`/`reasons` field "anywhere in a row", but the walk covers only the top level and `facts` (script:368-385). `binding`/`receipts` are not walked; a probe row with `binding={"reasons":[...]}` is accepted. This is not a verdict leak today, because binding is the owner-read identity, but the docstring should match the code.
- N3 nit (pre-existing, unchanged by the repair): committed rows read back by `_read_day_file` are re-emitted without `_assert_row_is_lawful`. A hand-tampered day file carrying a verdict token would therefore be rewritten verbatim. Two native rows with the same source event id within one run surface as a "committed" conflict with exit 2. No production rows exist pre-merge.

## Commands run (all read-only with respect to the seat worktree)
- `git show --stat 628cc4c…`, plus cmp of both files against the tree export: identical.
- `git diff b2efcfa 628cc4c -- tests/test_capture_prophet_b4_same_read.py`
- `PYTHONPATH=<tree> python3 -m pytest -p no:cacheprovider -q tests/test_capture_prophet_b4_same_read.py` → **20 passed**, 42 warnings in 3.15s
- The same command with revert plugins (plugin files in scratchpad/rr_plugins, not in the tree):
  - `-p revert_f1` → 3 failed / 17 passed
  - `-p revert_f2` → 2 failed / 18 passed
  - `-p revert_f5` → 1 failed / 19 passed
  - `-p revert_f4` → 1 failed / 19 passed
- A python probe of `_merge_and_write`/`_assert_row_is_lawful` in a mkdtemp dir checked:
  - file mode 0600 (N1);
  - UnicodeDecodeError, TypeError and ValueError escapes (F12 residual);
  - the fsync-failure cleanup (F8);
  - the in-run duplicate conflict (N3);
  - lawful `unavailable_reasons` and `binding.reasons` acceptance (F1/N2).

## UNVERIFIED
- The text of seat ruling F27, and whether it waives F3.
- No CI run and no production-host run were observed (/var/lib/macro-live is absent here).
