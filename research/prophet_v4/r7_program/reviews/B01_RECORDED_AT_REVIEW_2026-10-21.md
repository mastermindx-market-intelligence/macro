# B01 recorded_at writer clock — adversarial review (2026-10-21)

- **Artifact**: `git diff 2ebe9b7d52665ce4b37dbdb5845f4ce5cea879b1..HEAD` at BASE
  `e0acbb96daa58c716714e7ed37582bf8ea94f406` (head of PR #9951, `claude/prophet-r7-b01-recorded-at`).
- **Reviewer lane**: `lane/pro-source-b1rec-review-20261021-r1` (read-only; this file is the only write).
- **Verdict**: **PASS_WITH_NOTES** — frozen spec points 2–6 fully satisfied; point 1 satisfied on
  ordering, non-zero exit and no-receipt, **fails its "without a traceback" clause** (Finding 1,
  SHOULD_FIX). No BLOCKING finding: the guard is not bypassable, writes nothing, and exits non-zero.

## Diff stat (quoted)

```
 .github/ci/legacy-jobs.yml                         |   3 +
 scripts/reconcile_us_candidate_episodes.py         |  12 ++
 .../test_us_candidate_episode_recorded_at_clock.py | 194 +++++++++++++++++++++
 3 files changed, 209 insertions(+)
```

Exactly the three expected files; no other hunk, no engine module, no `config/dag.yml` change.

## Spec point verdicts

### 1. Guard before any read/write, non-zero exit, no receipt, no traceback — PARTIAL (Finding 1)

Ordering **PASS**. The guard is the first statement after argument parsing:

```
scripts/reconcile_us_candidate_episodes.py
664	    args = _parser().parse_args(argv)
665	    if args.nightly and not args.replay and args.recorded_at is not None:
666	        raise ReconcileRefused(
667	            "durable write refused: --recorded-at is a report/replay override; "
668	            "the durable writer stamps its own wall clock"
669	        )
670	    receipt = reconcile(repo_root=args.repo_root, nightly=args.nightly, replay=args.replay, ...
```

The only code executed before the raise is `_parser()` construction; its sole environment touch is
`default=Path.cwd()` at :652 — an OS cwd query, not a store/ledger read, config load or HEAD
resolve. The first store/config reads sit inside `reconcile()`: `nightly_advance_enabled()` at :627
and `_load_and_build`/`_load_existing_ledgers` at :631–634/:406–407 — both unreachable on the
refusal path. Behavioral proof: `tests/test_us_candidate_episode_recorded_at_clock.py:66-80`
monkeypatches `_load_and_build` and `_publish_transaction` to raise `AssertionError` if reached and
asserts `load_calls == []`, empty stdout, and `_snapshot(tmp_path) == {}`. Empirical probe
(subprocess, fresh root): **0 files created**.

Non-zero exit **PASS** (observed exit 1; test :97). No receipt **PASS** (stdout empty; 0 files;
tests :98, :100). **No traceback FAIL** → Finding 1.

### 2. Replay/report with `--recorded-at` remain allowed and read-only — PASS

Structural: the guard requires `not args.replay` (:665), so `--nightly --replay --recorded-at`
proceeds; `reconcile()` computes `durable = bool(nightly and not replay)` (:626) and returns early
at `:635-636 if not durable: return receipt` — strictly before `_publish_transaction` (:642). Every
filesystem-write primitive in the script lives in the publish region :490–621 (`mkdir` :490/:518,
`open("wb")` :491/:582, `os.rename`/`os.replace` :560/:565, `shutil.rmtree` :558/:621);
`_load_and_build` (:403–458) contains none. Behavioral: replay test :103–120 and report test
:123–139 assert `durable_write is False`, the caller clock in the receipt, and full-tree
`_snapshot` equality before/after (`_snapshot` is an `rglob` byte-hash of the entire root,
`tests/test_us_candidate_episode_reconciler.py:28-34`).

### 3. Pre-existing durable clock behaviour unaltered — PASS

The script diff is confined to `main()` (docstring :657–662 + guard :665–669); `reconcile()`,
`_load_and_build`, `_publish_transaction` and `engine/` are byte-identical (diff stat above).
Test :142–157 proves one `_now()` call per run (`clock_calls == [RECORDED_AT]`) with events
stamped; test :160–187 proves a second durable run keeps the committed `OPENED` clock
(:183 `committed["recorded_at"] == RECORDED_AT`), stamps only the new `OBSERVED` event
(:184 `CLOCK_LATER`), reports `appended_events == 1` (:186) over exactly two clock calls (:187).
All pass inside the 144-green battery.

### 4. No engine change; dag.yml production invocation unchanged — PASS

No engine module in the diff. `config/dag.yml:1925-1928` (quoted):

```
1925	      - id: reconcile_us_candidate_episodes
1926	        module: scripts.reconcile_us_candidate_episodes
1927	        args: [--nightly]
1928	        note: "V4-B1 sole durable candidate-episode writer. Runs after Door emission and before all forward graders/W3, refuses durable work without the nightly lane gate, builds one complete immutable generation, and publishes only through atomic HEAD.json replacement. Reads registered inputs without rank/gate/plan/Availability/V3 authority; report and replay modes are read-only."
```

`args: [--nightly]`, no `--recorded-at`; `dag.yml` is untouched by the diff. Production behaviour
is unchanged.

### 5. CI registration — PASS

- Manifest: `.github/ci/legacy-jobs.yml:8595` — `      - "tests/test_us_candidate_episode_recorded_at_clock.py"`
  (6-space indent matching siblings; the path appears exactly once under `paths:`; the only other
  occurrence in the file is the run command at :8654).
- Run step: `:8653-8654` (quoted), immediately after the pre-existing B1 suite step, inside the
  same `prophet-lab` job (job spans :8527–8670; next job `attested-history-guards` at :8671):

```
8653	      - name: US B1 recorded_at writer clock (durable CLI refuses caller clocks)
8654	        run: python -m pytest tests/test_us_candidate_episode_recorded_at_clock.py -q
```

- `yaml.safe_load('.github/ci/legacy-jobs.yml')` → `yaml ok`.
- `prophet-lab` declares **no `scope:` key** (not `scope: exclusive`), so the closure test was not
  strictly required; the import dependency `tests/test_us_candidate_episode_reconciler.py` is
  declared at :8594 regardless. Run anyway: `1 passed, 203 deselected`.

### 6. Seven tests exist and pass; docstring pins the contract — PASS (one crosscheck gap)

7 collected, 7 passed (`7 passed in 1.42s`): `test_cli_durable_recorded_at_is_refused_before_any_read_or_write` (:53),
`test_cli_durable_recorded_at_exits_nonzero_without_a_receipt` (:83),
`test_cli_replay_with_recorded_at_is_allowed_and_read_only` (:103),
`test_cli_report_with_recorded_at_is_allowed_and_read_only` (:123),
`test_cli_durable_without_override_stamps_the_writer_clock_once` (:142),
`test_second_durable_run_keeps_committed_clocks_and_stamps_only_new_events` (:160),
`test_main_docstring_pins_the_writer_clock_contract` (:190). The `main()` docstring :657–662 pins
the writer-clock contract and test :190–194 asserts it. PR-body name crosscheck: see GAPS.

## Findings

### F1 — SHOULD_FIX: the refusal surfaces as an uncaught-exception traceback (spec 1 "without a traceback")

`main()` raises `ReconcileRefused`; the `__main__` wrapper has no catch:

```
scripts/reconcile_us_candidate_episodes.py
676	if __name__ == "__main__":
677	    raise SystemExit(main())
```

Empirical subprocess run (`python -m scripts.reconcile_us_candidate_episodes --nightly
--recorded-at 2026-10-01T00:00:00Z --repo-root <fresh>`): exit 1, stdout empty, 0 files written,
stderr:

```
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File ".../scripts/reconcile_us_candidate_episodes.py", line 677, in <module>
    raise SystemExit(main())
                     ^^^^
  File ".../scripts/reconcile_us_candidate_episodes.py", line 666, in main
    raise ReconcileRefused(
ReconcileRefused: durable write refused: --recorded-at is a report/replay override; the durable writer stamps its own wall clock
```

`test_cli_durable_recorded_at_exits_nonzero_without_a_receipt` (:83–100) asserts `returncode != 0`,
empty stdout, the message **in** stderr and an empty snapshot — it never asserts absence of
`Traceback`, so the suite is green while the frozen clause fails (under-asserted, not vacuous).
Sibling durable-writer CLIs in this repo catch their refusal exceptions at the wrapper and exit
cleanly: `scripts/refresh_boats_history.py:604` (`except RefreshRefused as exc:`),
`scripts/qualify_press_nvda_baseline.py:103`, `scripts/observe_options_matrix_publication.py:1009`,
`scripts/build_macro_suite_pages.py:593`. Severity rationale: every protective property holds
(guard precedes all reads/writes; non-zero exit; no receipt; nothing written) and production never
passes `--recorded-at` (dag.yml :1927), so this is error-surface shape on an operator-misuse path —
not BLOCKING, but the frozen spec names the clause and the fix is a small wrapper catch (the
pre-existing gate refusal at :627–628 shares the same traceback shape and can be fixed in the same
lane).

### F2 — NOTE: `prophet-lab` carries a pre-existing job-level disable

`.github/ci/legacy-jobs.yml:8528` — `if: ${{ false }}` — present verbatim at the parent commit
`2ebe9b7d526`, not introduced by this change. Registration shape required by the spec is satisfied;
this note only flags that the practical CI-execution effect of registering under this job was not
traced through the pack generator in this review.

## Attack surfaces — each dismissed or raised

- **Argparse default not `None` (dead/always-on guard)** — dismissed: `parser.add_argument("--recorded-at")`
  at :650, no `default=`, no `type=` callable; default is `None`, so `is not None` at :665 is live.
  `--corrections`/`--repo-root` use `type=Path` (pure construction, no filesystem access at parse).
- **Any read before the guard** — dismissed: only `parse_args` precedes it; first reads at :627/:631
  are unreachable; monkeypatch test :66–80 and the 0-file probe confirm.
- **`ReconcileRefused` not caught by the CLI wrapper** — **raised as F1** (exit code itself is
  correct at 1; the traceback clause is the failure).
- **`--nightly --replay --recorded-at` secretly writing** — dismissed: :626 `durable=False` →
  early return :635–636; all write primitives at :490–621 unreachable; test :103–120 full-tree
  snapshot equality.
- **Receipt written on the refusal path** — dismissed: guard raises before `reconcile()` is called;
  `_publish_transaction` unreachable; probe wrote 0 files; stdout empty.
- **Duplicate/mis-indented manifest line** — dismissed: exactly one `paths:` entry (:8595,
  6-space indent); `yaml ok`.
- **Run step in a different job than the manifest line** — dismissed: both inside `prophet-lab`
  (:8527–8670) at :8595 and :8653–8654.
- **Tests passing vacuously (message-string-only)** — dismissed: tests assert exit codes, stdout
  receipts, unreachable-read monkeypatches, full-tree snapshots, clock-call counts and
  committed-vs-new clock separation; the one under-assertion (no traceback-absence check) is
  carried by F1.

## Evidence

```
144 passed in 24.41s                       # 5 episode suites (recorded_at_clock, reconciler, identity_retry, episode, wiring)
7 passed in 1.42s                          # tests/test_us_candidate_episode_recorded_at_clock.py alone
1 passed, 203 deselected in 95.60s         # tests/test_ci_pack.py -k curated_exclusive_scopes_cover_their_own_import_closure
yaml ok                                    # yaml.safe_load('.github/ci/legacy-jobs.yml')
EXIT=1, stdout empty, 0 files written      # refusal-path subprocess probe (stderr quoted in F1)
```

## GAPS

- No network in this lane: the PR #9951 body's test-name list could not be fetched, so "exact names
  the PR body lists" was crosschecked only against the 7 collected names quoted in §6.
- Replay/report read-only is proven structurally plus behaviorally on fixture trees; it was not
  exercised against production `data/` (absent from this sparse lane checkout).

## DEVIATIONS

- The ci_pack closure test was run although `prophet-lab` is not `scope: exclusive` (the packet made
  it conditional); run for completeness — it passes.
- The refusal-path probe ran as a subprocess with `--repo-root` under `/tmp` (outside the repo) to
  observe the real error surface; nothing inside the repo was written or edited.
- The single new-test file was re-run alone for a crisp per-file summary line.
