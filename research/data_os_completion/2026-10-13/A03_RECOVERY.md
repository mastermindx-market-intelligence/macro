# A03-1 — release recovery acceptance on the identity reference publish seam

Programme DATA-OS-COMPLETION, work package A03, lane A03-1 (run id `dataos-a03-1`).
Evidence class: **SYNTHETIC hermetic fixtures driven through the REAL publish seam**
(`scripts/build_security_master.py::run_nightly_refresh`, `_restore_artifacts`,
`_write_parquet`). Every generation in this record is SYNTHETIC — one-row Parquets
written into `tmp_path` by a stand-in for `build()`; nothing here is a natural
production event, no market data was read, and no production code was changed.

## Scope

- Start commit: `15bc4a7b392f152518c9fb8b822bd336ddc108b5`; lane branch
  `lane/dataos-a03-1`.
- Six blob pins at the start commit (all verified byte-exact):
  - `scripts/build_security_master.py` = `5ff1082d3e4c76e7d74447793f43c0146a1fa6d3`
  - `tests/test_dataos_security_master.py` = `e6e26ac868700499d01e41f1bdbefb9586d48975`
  - `lib/dataos/identity.py` = `a288b38a707548f19f5701d2c35db2e1e48e5d04`
  - `lib/dataos/read_contract.py` = `460fc9403c28eefc771710cbd5b2ecd43bedfdd5`
  - `.github/workflows/daily.yml` = `9af6ae590dc5c16038934a98cc4ae36dfc5d6ccc`
  - `research/data_os_completion/2026-10-13/D00_SEMANTIC_DECISIONS.md` = `784b6c259815ccdc1324bd7345499699d3c6122c`
- This is acceptance of the **identity reference publish seam**, not of a
  pointer/rollback system — **no generation id, current pointer or rollback
  receipt exists for the identity reference set on main**, so D5/D6 pointer
  semantics are recorded as ABSENT, never as passed.
- Deliverables: `tests/verification/test_a03_recovery.py` (+ the empty
  `tests/verification/__init__.py`) and this record. No file outside the owned
  set was touched (`git diff --diff-filter=M` against the start commit is empty).

## Acceptance map

| id | tests (node ids under `tests/verification/test_a03_recovery.py`) | verdict |
| --- | --- | --- |
| A03.01 — original-target reconciliation after an interrupted publication / lost response | `test_a03_01_build_writes_receipt_after_every_parquet`; `test_a03_01_exception_mid_publish_restores_prior_generation[0-5]`; `test_a03_01_exception_mid_first_publish_leaves_nothing_visible[0-5]`; `test_a03_01_notes_refusal_restores_artifacts_and_receipt`; `test_a03_01_rerun_of_a_complete_generation_is_a_byte_stable_noop` | PASS (handled classes: byte-exact restore to the prior generation, first publish leaves nothing visible, re-run is a byte-stable no-op) |
| A03.01 — the unhandled class (process-level crash) | `test_a03_01_hard_kill_mid_publish_leaves_a_torn_visible_set[1-5]` (PASS characterization of main); `test_a03_f1_torn_visible_set_is_detectable_or_never_visible` | **FINDING A03-F1** (strict xfail) |
| A03.01 — refusal after a tear | `test_a03_f3_refusal_after_a_tear_does_not_certify_the_torn_set_as_last_good` (strict xfail) + `test_a03_f3_twin_observed_refusal_after_a_tear_certifies_the_tear` (PASS twin) | **FINDING A03-F3** |
| A03.02 — rollback cannot erase failed-generation evidence or relabel legacy data | `test_a03_02_prune_conflict_refusal_leaves_a_durable_streak_record` (positive control); `test_a03_02_restore_never_relabels[exception|notes|prune-conflict]`; `test_a03_f2_generic_failure_leaves_a_durable_failure_record` | PASS for the dedicated prune-conflict kind and for no-relabel; **FINDING A03-F2** for generic/notes refusals (strict xfail) |
| A03.03 — source data, prior reads, membership history, ledgers unchanged | `test_a03_03_inputs_and_rails_unchanged_across_every_refusal`; `test_a03_03_prior_read_equals_read_after_restore`; `test_a03_03_generic_failure_does_not_touch_the_streak_sidecar` | PASS (scoped to the inputs/rails/prior reads this seam can touch; membership history and excluded ledgers are not read by the seam at all) |
| A03.04 — no independent writer or transport replays an unresolved/denied effect | `test_a03_04_only_the_owner_seam_writes_the_receipt`; suite discipline: every recovery is driven through `BUILD.run_nightly_refresh` only, and no test writes into the out_dir except the `StagedBuild` stand-in installed over `BUILD.build` | PASS |
| census pins | `test_a03_census_the_validator_rejects_the_seam_receipt_shape`; `test_a03_pending_legs_are_declared` | PASS (records absence, proves nothing exists) |

34 items collected: **31 passed, 3 xfailed (strict FINDINGS), 0 skipped** — run
twice, identical both times.

## D5/D6 conformance (rules quoted from `D00_SEMANTIC_DECISIONS.md` § D00.D5/§ D00.D6)

| rule | observed on main | verdict |
| --- | --- | --- |
| D5.1 "A generation is immutable and complete …; the current pointer moves atomically to a complete generation only" | No generation id and no pointer exist. The producer rewrites the five artifacts IN PLACE with direct, non-atomic writes; completeness is only approximated by write order (receipt last, pinned by the source-order test) and by the restore-on-handled-failure path (byte-exact, pinned by the k-parametrized tests). An unhandled crash leaves a torn visible set (F1). | ABSENT |
| D5.2 "A correction publishes a **new** generation carrying `supersedes=<old generation id>` …" | No `supersedes` anywhere; a correction is an in-place regenerate announced by the `identity inputs advanced — regenerated` notice. The producer receipt carries no generation identity at all (recorded as a GAP in Pending legs). | ABSENT |
| D5.3 "A receipt-only change (identical Parquet bytes, different receipt) is a new generation and a prior refusal cannot disappear because the bytes did not move" | The seam's contract is the opposite direction BY DESIGN: the byte-stable branch rewrites the receipt to the preimage bytes (`byte-stable no-op`, RM4-pinned), so a receipt-only change is discarded, not published; and a generic/notes refusal leaves no memory in the data plane (F2), so nothing prevents the identical attempt re-running the next night as if fresh. | ABSENT (contradicts D5.3 by design) |
| D5.4 "An interrupted publish is `EFFECT_UNKNOWN` until the pointer target is validated against its own receipt; reconciliation reads, it never re-runs the write" | Handled interruptions are reconciled by a RESTORE (a write of the preimage), not by a read; the de-facto reconciliation for a lost response is the re-run, which re-executes the write (idempotently — the byte-stable no-op test). Unhandled crashes stay EFFECT_UNKNOWN with no receipt-vs-pointer validation possible (no pointer, no manifest — F1). | FINDING (A03-F1) |
| D5.5 "Exact replay is promised only when the original output and its material are retained …" | Nothing is retained: no superseded generation stays readable by id, and a failed generation leaves no data-plane trace at all (F2). The only retained history is git. | ABSENT |
| D6 "rollback = pointer revert to the previous complete generation plus Terminal JSON regeneration from it; the superseded generation remains readable" | No pointer to revert; production rollback is a git revert of a `data:` commit — an operator act outside this lane. Terminal JSON regeneration awaits C04 (not on main). | ABSENT (UNFINISHED legs) |

## Interruption matrix

SYNTHETIC generation A published through the real seam, then a generation B
interrupted at write point k (k=0 raises before the first Parquet; k=5 raises
after all five, before the receipt). Observed:

| kind | k | visible labels (master/aliases/iss_master/iss_migr/sec_migr) | receipt | return | CI line |
| --- | --- | --- | --- | --- | --- |
| Exception | 0 | A/A/A/A/A | A | 0 | `::warning title=security-master-nightly::build failed reading identity inputs (…) — keeping last-good artifacts, generated_at not re-stamped` |
| Exception | 1 | A/A/A/A/A | A | 0 | same |
| Exception | 2 | A/A/A/A/A | A | 0 | same |
| Exception | 3 | A/A/A/A/A | A | 0 | same |
| Exception | 4 | A/A/A/A/A | A | 0 | same |
| Exception | 5 | A/A/A/A/A | A | 0 | same |
| hard kill | 0 | A/A/A/A/A | A | raises (uncaught) | (none — no handler runs; daily.yml `|| echo ::warning` catches the exit) |
| hard kill | 1 | B/A/A/A/A | A | raises (uncaught) | (none) |
| hard kill | 2 | B/B/A/A/A | A | raises (uncaught) | (none) |
| hard kill | 3 | B/B/B/A/A | A | raises (uncaught) | (none) |
| hard kill | 4 | B/B/B/B/A | A | raises (uncaught) | (none) |
| hard kill | 5 | B/B/B/B/B | A | raises (uncaught) | (none) |

First publish (no prior generation) × Exception k=0..5: the out_dir is left
with no file at all (newly created files are unlinked). Notes refusal after a
complete write of all six files: all six restored to the prior generation's
bytes. Re-run of a complete generation: byte-stable no-op, receipt bytes equal
the preimage (fresh `generated_at` NOT kept).

## Census

Re-run at the start commit (step 0.6), verbatim:

```
$ git grep -n "identity_publication" -- lib engine scripts app
lib/dataos/identity.py:1229:    _ob_require(pub["schema"] == "mastermind.identity_publication.v1", "publication schema")
rc=0
```

One hit: the validator's own schema check. **No producer of an
`identity_publication` block exists on main.**

```
$ git grep -n "validate_reference_snapshot" -- lib engine scripts app
lib/dataos/__init__.py:76:    validate_reference_snapshot,
lib/dataos/__init__.py:204:    "validate_reference_snapshot",
lib/dataos/identity.py:99:    "validate_reference_snapshot",
lib/dataos/identity.py:1217:def validate_reference_snapshot(receipt_before, artifact_bytes, receipt_after, *,
lib/dataos/identity.py:1412:        checked = validate_reference_snapshot(
rc=0
```

Definition, `__all__`/package re-exports, and exactly ONE call site —
`lib/dataos/identity.py:1412`, inside `_ob_table` (the module's own internal
observation-history constructor). **No non-test, non-internal caller on main;
no caller in `scripts/`, `engine/` or `app/`.** The executable census pin
(`test_a03_census_the_validator_rejects_the_seam_receipt_shape`) additionally
shows the validator refuses the receipt shape the seam actually writes
("snapshot owner context missing" — no `publication` block).

```
$ git grep -n "RECEIPT_NAME\|_receipt.json" -- scripts/build_security_master.py
scripts/build_security_master.py:24:``data/reference/_receipt.json``  ``code_version`` (git sha), per-input sha256, row
scripts/build_security_master.py:120:RECEIPT_NAME = "_receipt.json"
scripts/build_security_master.py:3217:    receipt_path = out_dir / RECEIPT_NAME
scripts/build_security_master.py:4085:        (out_dir / RECEIPT_NAME).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
scripts/build_security_master.py:4093:#: actually change" (RECEIPT_NAME is handled separately — see :func:`run_nightly_refresh`).
scripts/build_security_master.py:4118:#: PERSISTENCE (undeclared on purpose, like ``_receipt.json``): this sidecar rides
scripts/build_security_master.py:4120:#: ``git add data/`` step commits it alongside ``_receipt.json``, which is likewise
scripts/build_security_master.py:4199:    receipt_path = out_dir / RECEIPT_NAME
scripts/build_security_master.py:4283:    before_receipt = _read_bytes_if_exists(out_dir / RECEIPT_NAME)
scripts/build_security_master.py:4400:            (out_dir / RECEIPT_NAME).write_bytes(before_receipt)
rc=0
```

```
$ git grep -ln "data/reference" -- scripts engine lib app .github/workflows
.github/workflows/ci.yml
app/deploy/update.sh
engine/classification_axes/geography.py
engine/company_intelligence/current_context_runtime.py
engine/fundamental_forensics/production_datasets.py
engine/fundamental_forensics/production_provider.py
engine/intelligence_workspace/entity.py
engine/k3e_expectation_surface.py
engine/market_ontology/ticker_cik_census.py
engine/neuralweb/theme_state_adapter.py
engine/prophet_daily_brief_evidence_sources.py
engine/security_state.py
engine/theme_graph/identity_resolution.py
engine/theme_graph/structural_navigation.py
scripts/build_fundamental_forensics.py
scripts/build_security_master.py
scripts/check_theme_graph_contracts.py
scripts/correct_gmi_identity_lineage.py
scripts/ticker_cik_collision_census.py
rc=0
```

Nineteen readers/writers of the reference set across the plane — none of them a
pointer, generation store or rollback path.

## Real-path analysis

Quoted from `.github/workflows/daily.yml` (read-only; blob pin above):

```yaml
      - name: security master — issuer axis nightly refresh (V4-D2B1)
        continue-on-error: true
        run: |
          python3 scripts/build_security_master.py --nightly \
            || echo "::warning::build_security_master.py --nightly exited non-zero (unexpected — the function itself always returns 0; see the traceback above)"
```

```yaml
        if: always() && steps.collectors.outcome == 'success'
        id: commitdata
        ...
          git add data/ site/qledger/
```

What happens to a torn set: a process-level crash inside the refresh exits
non-zero; the step's `|| echo "::warning::…"` swallows the exit and
`continue-on-error: true` launders the step conclusion, so the job stays green.
The later `commit market data` step gates ONLY on
`steps.collectors.outcome == 'success'` — not on the security-master step — so
it runs `git add data/` and commits whatever bytes sit in the reference set:
the torn mix (e.g. B,B,A,A,A) under the PREVIOUS receipt, which still hashes to
the old artifact set only for the three unwritten files. Detection is impossible
from the data plane: the census above shows no producer of the
`identity_publication` manifest and no non-test caller of
`validate_reference_snapshot`, so no reader — human or machine — can validate
the visible set against its own receipt. The committed tear then becomes the
`before` preimage of the NEXT night's restore (FINDING A03-F3).

## Release path

The work-package step "exercise current→legacy→current selection through the
existing release path after user reads" is `UNFINISHED: no release path or
pointer exists for the identity reference set`. On main the reference set has
exactly one materialization (the five files plus the receipt in place), selected
implicitly by path; there is no `CURRENT`/`RECONSTRUCT`/`REPLAY` distinction, no
generation id to be "legacy", and therefore no current→legacy→current circuit
to exercise. The nearest existing analogues are (a) git history — any prior
committed state is recoverable by `git revert`/checkout of a `data: daily
collection` commit, an operator act outside this lane, and (b) the seam's
restore path, which this suite does exercise end-to-end (restore = rewrite of
the byte preimage, which is what a pointer-less "rollback" reduces to here).
Exercising the real selection semantics requires the D5.1/D5.2 machinery to
exist first; when it does, the A03.03 prior-read tests in this suite are the
harness to replay against it (read before, roll back, read after, frame-equal).

## Pending legs

`PENDING_LEGS` (module constant, asserted by `test_a03_pending_legs_are_declared`),
verbatim:

```
UNFINISHED: no generation id, current pointer or rollback receipt exists for data/reference; production rollback is a git revert of a data commit (operator act)
UNFINISHED: awaiting C04 LANDED — D6 Terminal JSON regeneration from the rolled-back generation
UNFINISHED: real-inputs leg — hermetic lane, no data/ reads
GAP: producer receipt carries no generation_id / supersedes (D5.1, D5.2)
```

What closes each: (1) the D5.1/D5.2 generation+pointer machinery landing in the
producer (mint generation ids, write the current pointer atomically, keep a
rollback receipt) — then this suite's interruption matrix re-runs against the
pointer, not just the files; (2) C04's Terminal JSON emitter landing
(cross-repo) — then rollback's regeneration half is testable end-to-end; (3) a
non-hermetic lane with data-plane read authorization running the REAL `build()`
over the real identity inputs; (4) the same D5.1/D5.2 change — the receipt
gains `publication.generation_id`/`supersedes`, making
`validate_reference_snapshot` consumable by a real reader.

## Mutation sensitivity

Procedure: `git worktree add --detach <mut> HEAD`; for each mutation make the
smallest edit (≤ 6 changed lines) to `scripts/build_security_master.py` in that
tree only; run this suite there; restore with `git checkout -- scripts/`;
finally `git worktree remove --force <mut>`.

| mutation | edit | failing tests (all kills) |
| --- | --- | --- |
| RM1 — `_restore_artifacts` no longer unlinks files that did not exist before | `if path.exists():` → `if False and path.exists():` (artifacts branch) | `test_a03_01_exception_mid_first_publish_leaves_nothing_visible[1..5]` (5) |
| RM2 — `_restore_artifacts` skips the receipt | early `return` before the receipt branch | `test_a03_01_notes_refusal_restores_artifacts_and_receipt`, `test_a03_02_restore_never_relabels[notes]` (2) |
| RM3 — the generic `except Exception` branch does not call `_restore_artifacts` | handler's restore call deleted | `…_mid_publish_restores_prior_generation[1..5]`, `…_mid_first_publish_leaves_nothing_visible[1..5]`, `…_f3_twin_observed_refusal_after_a_tear_certifies_the_tear`, `…_03_prior_read_equals_read_after_restore` (12) |
| RM4 — the byte-stable branch does not rewrite `before_receipt` | `if before_receipt is not None:` → `if False and …` | `test_a03_01_rerun_of_a_complete_generation_is_a_byte_stable_noop` (1) |
| RM5 — in `build()`, the receipt `write_text` moved before the first `_write_parquet` | receipt line relocated above the master write (2 lines moved) | `test_a03_01_build_writes_receipt_after_every_parquet` (1) |
| RM6 — the prune-conflict branch does not write the streak sidecar | `streak_path.write_text(…)` guarded dead by `None if True else …` | `test_a03_02_prune_conflict_refusal_leaves_a_durable_streak_record`, `test_a03_03_generic_failure_does_not_touch_the_streak_sidecar` (2) |

**Killed 6/6. No survivors.**

## Findings

### FINDING A03-F1 — a torn set with no way to detect it

A process-level crash mid-publish leaves a torn reference set under the previous
receipt, and neither the producer nor any reader can detect it.

Reproducer (5 lines, SYNTHETIC):

1. Publish generation A through `run_nightly_refresh(out_dir)` (staged build "A").
2. Install staged build "B" raising a `BaseException` (not `Exception`) after the second `_write_parquet`.
3. `run_nightly_refresh` propagates the crash; the visible set is now B/B/A/A/A under A's receipt — no handler ran, nothing was restored.
4. In the nightly, `continue-on-error: true` + the `|| echo "::warning::…"` swallow the crash and the job stays green.
5. `commit market data` (`if: always() && steps.collectors.outcome == 'success'`) runs `git add data/` and commits the torn set; the census shows no `identity_publication` producer and no non-test caller of `validate_reference_snapshot`, so nothing can flag it.

Pinned by `test_a03_f1_torn_visible_set_is_detectable_or_never_visible` (strict
xfail: asserts the visible set equals the preimage OR the producer emits the
manifest; both are false on main).

### FINDING A03-F2 — a generic refusal erases every trace of the failed generation

A generic or notes refusal restores the preimage byte-exact (correct) but leaves
NO durable data-plane record that a generation was attempted and refused — only
the CI log line keeps it, and CI logs are not company memory.

Reproducer (5 lines, SYNTHETIC):

1. Publish generation A; install staged build "B" failing with `RuntimeError` at write point k=3.
2. `run_nightly_refresh` returns 0 and prints `::warning … keeping last-good artifacts`.
3. The restore rewrites all six files to A's bytes; B's rows and B's receipt vanish.
4. The out_dir holds no file other than the six artifacts — nothing names the attempt.
5. Contrast the prune-conflict kind, which DOES leave `_nightly_prune_conflict_streak.json` with both counters (positive control passes).

Pinned by `test_a03_f2_generic_failure_leaves_a_durable_failure_record` (strict
xfail: asserts a non-artifact file naming the failed attempt exists; it does not).

### FINDING A03-F3 — a refusal after a tear certifies the torn set as last-good

The restore snapshots `before` from whatever is on disk when the run starts, so
after a torn publish the next refusal restores the TORN bytes and calls them
"last-good".

Reproducer (5 lines, SYNTHETIC):

1. Publish A; hard-kill B at k=2 (torn B/B/A/A/A under A's receipt, per F1).
2. Next run: staged build C fails at k=3 with `RuntimeError`.
3. The generic handler snapshots the torn set as `before`, then restores exactly those bytes.
4. It prints `keeping last-good artifacts` — a mixed-generation set is now the certified baseline.
5. Every later restore defends B/B/A/A/A as if it were a complete generation.

Pinned by `test_a03_f3_refusal_after_a_tear_does_not_certify_the_torn_set_as_last_good`
(strict xfail: asserts the five visible artifacts carry ONE generation label;
on main they carry two) with the PASS twin
`test_a03_f3_twin_observed_refusal_after_a_tear_certifies_the_tear` asserting
the observed B/B/A/A/A and the warning line.

## Commands

Run from the lane worktree; `PY` = the pinned lane venv interpreter; every
pytest invocation prefixed `PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`.

- **P1** `PY -m pytest tests/verification/test_a03_recovery.py -rs` — run twice:
  `31 passed, 3 xfailed` / `31 passed, 3 xfailed` (identical; 34 collected, 0 skipped).
- **P2** `git diff --name-only <base> HEAD` → `tests/verification/__init__.py`,
  `tests/verification/test_a03_recovery.py`,
  `research/data_os_completion/2026-10-13/A03_RECOVERY.md`;
  `git diff --diff-filter=M --name-only <base> HEAD` → empty.
- **P3** `PY -m py_compile tests/verification/test_a03_recovery.py` → `compile-ok`.
- **P4** `grep -n "datetime.now\|time\.time\|requests\|urllib\|socket\|subprocess\|data/" tests/verification/test_a03_recovery.py`
  → 6 hits, lines 45/49/311/560/567: all are PROSE inside `PENDING_LEGS` string
  literals and the F1 xfail reason (the words "data/reference", "data commit",
  "no data/ reads") — no filesystem access; every file write in the suite lands
  under `tmp_path` via the staged build and the seam.
- **P5** `PY scripts/check_contract_delta.py --base <base> 2>&1 | tail -8`:
  `::error title=contract-delta::tests/verification/test_a03_recovery.py is a new pytest suite named by no run: step in any workflow — wire it into the job that owns its subject in .github/ci/legacy-jobs.yml, or add a reasoned row to config/unrun_test_waivers.yml` /
  `contract-delta: 1 introduced, 0 inherited (base 15bc4a7b392f)` — the
  EXPECTED introduced finding naming the unwired test file (the orchestrator
  applies the legacy-jobs patch; this lane does not edit `.github/**`).
- **P6** the mutation procedure above → killed 6/6.
