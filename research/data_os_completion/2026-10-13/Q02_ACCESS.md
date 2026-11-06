# Q02 — adversarial access at the real handler boundary (lane Q02-1)

Programme DATA-OS-COMPLETION, work package Q02. One new adversarial suite
(`tests/verification/test_access_q02.py`, 73 collected items) plus this record.
VERIFICATION lane: no production code was changed; the one defect found is
pinned as a strict-xfail test asserting the CORRECT behaviour.

## Scope

- Start commit: `ed1497887c99101bd1b8bc5438e281f02466371b` (= origin/main at packet time).
- Seven blob pins at the start commit, verified in step 0.4:

| Path | Blob |
| --- | --- |
| `lib/dataos/web_api.py` | `fc35cdec14c1a83752c6c8f095ed0305218ebafc` |
| `lib/dataos/web_workspace.py` | `450c25fc363272cdff1a58889edbd14c29bffb18` |
| `lib/dataos/web_readers.py` | `753a1cdea027d47bce28eb55ad640acaf159f978` |
| `scripts/data_workspace.py` | `f3763471beb4db2174215bdfc57d17c3692d6568` |
| `lib/dataos/read_contract.py` | `460fc9403c28eefc771710cbd5b2ecd43bedfdd5` |
| `engine/basket_membership_pit.py` | `5c7ba201d505648365ba40ff88c6901b47aef713` |
| `tests/test_basket_membership_pit.py` | `6da5b38759ad945c5781fff213b9f8a6bcfc8d55` |

All fixtures are synthetic licensed-shaped values (e.g.
`{"date":"2026-01-02","symbol":"SYNTH1","close":"101.25"}`); no real market
data, no secret probes, writes only under the pytest temp tree. `lab_run` and
`lab_plan` are out of scope for this lane: they write test-workspace artifacts
and are not access-boundary read paths.

## Entrypoints

- **E1a — the real CLI transport.** `subprocess.run([sys.executable, "-B",
  "<repo>/scripts/data_workspace.py", "--config", <cfg>], input=<request json
  bytes>, capture_output=True, timeout=60, cwd=<tmp>, env=<PATH +
  PYTHONDONTWRITEBYTECODE=1>)`. `cfg` is a host-binding JSON with
  `schema_version` `mastermind.data_workspace_bindings/v1`, a `registry_path`
  (the repo `config/dataset_registry.yml`, read-only) and `roots`. Success is
  rc 0 with one JSON object on stdout; refusal is rc 2 with
  `{"schema_version":"mastermind.data_workspace/v1","error":<CODE>,"error_type":...}`
  (confirmed from `scripts/data_workspace.py::main`).
- **E1b — the same composition in-process.**
  `lib.dataos.web_workspace.load_workspace_config(cfg)` then
  `lib.dataos.web_api.dispatch(workspace, request, config_path=cfg)`; a refusal
  surfaces as `WorkspaceError` with attribute `.code`. Every E1 negative case
  runs over BOTH transports and the two agree on the code (case D1).
- **E2 — the read contract.** Names imported from `lib.dataos.read_contract`
  directly (not the package re-exports): `current`, `reconstruct`, `replay`,
  `select_generation`, `account_coverage`, plus `ViewContract`, `ReadRequest`,
  `ReadMode`, `CurrentEvidence`, `RetainedOutput`, `GenerationRef`,
  `Dependency`, `MemberDisposition`, `SourceSegment`, `Disposition`,
  `ReadRefusal`.
- **E3 — the basket reader.**
  `engine.basket_membership_pit.members_asof(basket_id, date, suite=...)` and
  `coverage(suite)`, with `config.data_dir` redirected to the pytest temp tree
  via the house fixture idiom (`monkeypatch.setattr(config, "data_dir",
  lambda: tmp_path)`, as in `tests/test_basket_membership_pit.py`).

Observed API notes: `CoverageResult.requested`, `.counts` and
`.qualified_fraction` are properties (not methods); `ReadRefusal.code` is a
`RefusalCode` StrEnum that compares equal to its string.

## Case table

| id | acceptance | entrypoint | action | expected | observed | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| A1 | Q02.01 | E1a+E1b | permitted `read` + `describe` of a synthetic CSV | rows served; `file_version` `statv1:`-prefixed, len 71 | rows served on both transports, identical `result` and version; describe reports 3 rows and the 3 columns | PASS |
| A2 | Q02.01 | E1a+E1b | `read` pinned to ANOTHER file's valid version | `SOURCE_VERSION_MISMATCH`, no row values | refused on both transports; refusal envelope carries code only | PASS |
| A3 | Q02.01 | E1a+E1b | host rewrites the binding without the alias, identical payload re-sent | `ROOT_NOT_BOUND` | refused on both transports (CLI re-reads cfg per process; dispatch reloads the workspace) | PASS |
| A4 | Q02.01 | E1a+E1b | root dir swapped for a new dir at the same path holding byte-identical bytes | pinned read refuses `SOURCE_VERSION_MISMATCH`; unpinned read succeeds with a DIFFERENT version | exactly that, on both transports; same rows, new identity | PASS |
| A5 | Q02.01 | E2 | pinned generation no longer selectable; CURRENT evidence naming a superseded generation; all generations superseded | `STALE_GENERATION` / `STALE_GENERATION` / `UNBOUND_DEPENDENCY` | those three codes, exactly as the code expresses them | PASS |
| A6 | Q02.01 | E3 | unknown basket id | `basis == "unknown_basket"`, empty member list, never a peer's members | `unknown_basket`, `[]`, `pit=False`, note "no basket-scoped observation"; a known basket still answers its own members | PASS |
| B1 | Q02.02 | E2 | `replay` of a receipt-only `RetainedOutput`; one payload byte altered after the sha; intact control | `NO_RETAINED_OUTPUT` / `RETAINED_DIGEST_MISMATCH` / payload served | exactly that; refusals raise before any values exist | PASS |
| B2 | Q02.02 | E1a+E1b | read ok → delete file → identical payload; then byte-identical recreation + old pin | `SOURCE_NOT_FOUND`, then `SOURCE_VERSION_MISMATCH` | exactly that, on both transports | PASS |
| B3 | Q02.02 | E1a+E1b | A→B→A in place with original `mtime_ns` restored | pinned read refuses; new version differs | exactly that — `_version` includes `st_ctime_ns`, which user space cannot set | PASS |
| B4 | Q02.02 | E2 | g1(A) ← g2(B) ← g3(A re-published); clock after g3 | `select_generation` returns g3, never g1; a g1 pin is refused `STALE_GENERATION` | `select_generation` → g3; `reconstruct` binds g3 and serves only g3-tagged rows; pinned g1 → `STALE_GENERATION` (refused and labelled, never a silent CURRENT on g1) | PASS |
| B5 | Q02.02 | E3 | history parquet removed → read inside the former window; then replaced with garbage bytes | `pit=False` with look-ahead note; garbage asserted as observed; read failure must not be `basis == "current_membership"` | removed: `pit=False`, `basis="current_membership"`, note exactly "no PIT history yet — current membership applied backward (look-ahead basis)", `snapshot_date=None`, current members; garbage: same labelling — a read failure presented as an observation of current membership | FINDING (Q02-F1) + OBSERVED-STATE — RESOLVED 2026-10-19 by PR #9654 (claude/dataos-q02f1-2026-10-19): unreadable history now answers basis=membership_unreadable and the basket read refuses MEMBERSHIP_UNREADABLE; strict-xfail removed. |
| B6 | Q02.02 | E2 | coverage account over a frozen population: one MISSING member; duplicated member; disposition outside the population | MISSING stays in the population, counts sum to population, `qualified_fraction` a Fraction < 1; `DUPLICATE_MEMBER`; `COVERAGE_UNRECONCILED` | exactly that: `requested=3`, counts sum 3, `Fraction(2,3)`, `summary()["missing"]=={"NOT_YET_AVAILABLE":1}`; both refusals raise with the expected codes | PASS |
| C1 | Q02.03 | E1b | authorized workspace reads `priv`; guest workspace (no `priv` binding) issues the identical payload in the SAME process | `ROOT_NOT_BOUND`; serialized error carries none of the fixture's distinctive values | refused; the error serializes to its code only — no `Q02-PRIVATE-7f3a` token, no values | PASS |
| C2 | Q02.03 | E1a | the same sequence across two CLI processes | authorized rc 0 with rows; guest rc 2 `ROOT_NOT_BOUND`, no leak | exactly that; stdout+stderr of the guest carry no token, no values, no host path | PASS |
| C3 | Q02.03 | E1b | authorized read → guest read → authorized read pinned to the now-stale version after the file changed | the third read must refuse | `SOURCE_VERSION_MISMATCH` — no response was cached by the payload | PASS |
| C4 | Q02.03 | E2 | `replay` asked for output Y while only X is retained | typed refusal | `NO_RETAINED_OUTPUT` | PASS |
| D1 | Q02.04 | E1a+E1b | parametrized table of all 7 E1 negative cases over both transports | both transports agree on each code | full agreement (7/7): mismatch/revoked/disappeared/sensitive/no-colon/unknown-field/unknown-action | PASS |
| D2 | Q02.04 | E1a+E1b | successful `read` source block | `content_sha256 is None`; basis names the stat identity | exactly that, both transports (see §Source-byte verification) | PASS |
| L1 | Q02.04 | E1a | every CLI refusal envelope | ONE JSON object, keys a subset of the documented error keys; no host path, no traceback, no fixture value | enforced in the suite's CLI helper on every refusal and re-asserted by 5 representative parametrized cases | PASS |
| L2 | Q02.04 | E1a+E1b | 9 hostile refs × 2 transports | each refused with its code, leaks nothing | traversal/`.env`/`.git/config`/`secret_values`/`api_key` → `PATH_REFUSED`; symlink out → `PATH_OR_SOURCE_REFUSED`; hard link (nlink 2) → `REGULAR_PRIVATE_FILE_REQUIRED`; no colon → `INVALID_DATA_REF`; unbound alias → `ROOT_NOT_BOUND` (18/18) | PASS |
| L3 | Q02.04 | E1a+E1b | >16384-byte payload; unknown field; unknown action; NaN constant in CLI stdin | `REQUEST_TOO_LARGE`; `INVALID_REQUEST_FIELDS`; `UNKNOWN_ACTION`; NaN → the code from source | all as expected; NaN → `INVALID_REQUEST_JSON` (`parse_constant` refusal in `_input`), CLI-only as designed | PASS |

Cache survey (required by the packet): `grep -n "lru_cache\|functools.cache\|_CACHE\|cache" lib/dataos/web_api.py lib/dataos/web_workspace.py lib/dataos/web_readers.py scripts/data_workspace.py` exits 1 — zero matches. There is no memoization layer anywhere in this adapter composition; each dispatch re-opens the source and re-stats it, which is what C3 exercises.

No case was judged inapplicable; every required case above is a real test.

## Findings

**Q02-F1 — an unreadable basket-history parquet is returned as
`basis == "current_membership"`.** `engine.basket_membership_pit.read_history`
(non-strict) swallows a corrupt-parquet exception and returns an empty frame;
`members_asof` then takes the uncovered path and labels the answer as the
CURRENT membership with note "no PIT history yet", i.e. a read failure is
indistinguishable from a store that never had history. The module's own
docstring names the risk ("corruption fails closed instead of masquerading as
absence") but reserves it for `strict=True`, which `members_asof` never
passes. Strict-xfail test:
`test_b5_read_failure_is_not_current_membership` (asserts
`got["basis"] != "current_membership"` on a read failure).

RESOLVED 2026-10-19 by PR #9654 (claude/dataos-q02f1-2026-10-19): unreadable history now answers basis=membership_unreadable and the basket read refuses MEMBERSHIP_UNREADABLE; strict-xfail removed.

5-line reproducer (data dir redirected to a scratch tree):

```python
from engine import basket_membership_pit as pit
pit.append_snapshot(pit.SUITE_THS, asof="2026-07-01", lane="asia")  # stamps real history
pit.history_path(pit.SUITE_THS).write_bytes(b"NOT A PARQUET FILE")
got = pit.members_asof("ths_a", "2026-07-01", suite=pit.SUITE_THS)
(got["basis"], "no PIT history yet" in got["note"])  # -> ('current_membership', True)
```

Adjacent observed state (not filed as a finding): even on the exception path
itself, `members_asof`'s handler sets `note = "read failed (...)"` while
leaving `basis` at its initialised `"current_membership"` — the same
mislabelling in a second shape.

## Mutation sensitivity

Suite run at HEAD in a detached local-only mutation worktree; each mutation is
the smallest edit (≤ 6 changed lines); restore with `git checkout -- lib/
engine/` after each.

| mutation | edit | predicted | observed failing tests | killed |
| --- | --- | --- | --- | --- |
| QM1 | `_version` drops `s.st_ctime_ns` | B3 | `test_b3_aba_in_place_cannot_restore_version[cli]`, `[dispatch]` (2) | YES |
| QM2 | `expected_version != version` check in `_file` removed | A2/A4/B2/B3 | `test_a2_...[cli]`, `[dispatch]`, `test_a4_...[cli]`, `[dispatch]`, `test_b2_...[cli]`, `[dispatch]`, `test_b3_...[cli]`, `[dispatch]`, `test_c3_no_response_cache_across_roles`, `test_d1_...[version_mismatch-...]`, `test_l1_...[version_mismatch-...]` (11) | YES |
| QM3 | `replay` skips its digest comparison | B1 | `test_b1_replay_retained_output_refusals[tampered]` (1) | YES |
| QM4 | `_parts` stops refusing `SENSITIVE_MARKERS` | L2 | `test_l2_path_refusals[secret_values-...-cli]`, `[-dispatch]`, `[api_key-...-cli]`, `[-dispatch]`, `test_d1_...[sensitive_path-...]`, `test_l1_...[sensitive_path-...]` (6) | YES |

Killed **4/4**; no survivors. Baseline mutation runs: every mutated run keeps
the strict xfail in place (QM runs were 61–71 passed + 1 xfailed + failures).

## Source-byte verification

This adapter does **NOT verify source bytes by content hash**. A successful
`read` reports `source.content_sha256 is None` and
`source.file_version_basis == "device_inode_size_mtime_ctime_not_content_hash"`
(case D2). Its "version" is a stat identity, from
`lib/dataos/web_workspace.py`:

```python
identity = [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns]
```

That limit is disclosed on every response, not hidden — and it is a Q02.04
"real source-byte verification" gap for any consumer that needs content
identity: two byte-identical files under swapped directories hold different
versions (case A4), while two different-byte files could in principle share a
stat identity's shape. `st_ctime_ns` in the same line is why A→B→A in place
cannot restore a version even after the original `mtime_ns` is re-stamped
(case B3): ctime is kernel-maintained and cannot be set from user space. E2's
`replay` is the only entrypoint here that binds exact bytes (sha256 over the
retained payload), and B1 proves it refuses rather than regenerating.

## Remaining real-principal gates

What this lane could NOT reach, each with the proof that would close it:

- **The authenticated Studio/MCP transport.** E1b exercises the dispatcher
  with host bindings, but no authenticated principal token flows through a
  Studio/MCP session. Closing proof: an authenticated-transport test driving
  the same `dispatch` composition under two real principals with
  account-scoped bindings.
- **The Terminal data route and its principal-scoped cache.** C1–C3 prove the
  adapter composition holds no replayable state, but the Terminal's own cache
  layer was not exercised. Closing proof: an authorized-then-guest sequence
  driven through the Terminal data route itself.
- **Browser composition.** No browser session consumed these responses. Closing
  proof: an end-to-end browser read (widget surface) observing the same
  qualified/refused envelopes.
- **U03 consumer work**, which has not landed. Closing proof: the U03 consumer
  suite wired against these same entrypoints and run in CI.

Also not yet done: this suite is not wired into CI — the orchestrator applies
the `.github/ci/legacy-jobs.yml` patch (P5's single "introduced" finding names
exactly this).

## Commands

Run from the lane worktree; `PY` = the lane venv interpreter;
`PYTHONDONTWRITEBYTECODE=1` and `-q -p no:cacheprovider` on every pytest.

- **P1** `PY -m pytest tests/verification/test_access_q02.py -rs` (twice):
  `72 passed, 1 xfailed in 12.03s` then `72 passed, 1 xfailed in 12.30s` —
  identical summaries, 73 collected items, 0 skipped.
- **P2** `git diff --name-only ed1497887c99101bd1b8bc5438e281f02466371b HEAD` →
  exactly the three owned paths (`tests/verification/__init__.py`,
  `tests/verification/test_access_q02.py`,
  `research/data_os_completion/2026-10-13/Q02_ACCESS.md`);
  `git diff --diff-filter=M --name-only <base> HEAD` → empty.
- **P3** `PY -m py_compile tests/verification/test_access_q02.py && echo compile-ok`
  → `compile-ok`.
- **P4** `grep -n "datetime.now\|time\.time\|requests\|urllib\|socket\|subprocess\|open(" tests/verification/test_access_q02.py`
  → two hits only: `26:import subprocess` and `116:    proc = subprocess.run(`.
  Both are the E1a CLI transport — the one entrypoint the packet permits
  subprocess for; every file write/read in the suite goes through
  `Path.write_bytes/write_text/read_bytes` on `tmp_path` trees only (no bare
  `open(` anywhere), and no wall clock, network or socket appears.
- **P5** `PY scripts/check_contract_delta.py --base ed1497887c99101bd1b8bc5438e281f02466371b 2>&1 | tail -8`
  → the quoted tail below; the one "introduced" row is the unwired-suite
  finding this lane expects (orchestrator wires CI); 0 inherited.
- **P6** the four mutations of §Mutation sensitivity, run in the detached
  mutation worktree at HEAD and restored after each; killed 4/4.

P5 quoted tail (last 8 lines):

```
contract-delta: probe templates/index.html: head 134 jobs / 5,650 s / 10 packs; base 134 jobs / 5,650 s / 10 packs; ceilings 135 / 5,803 / 10
contract-delta: probe scripts/build_free_content.py: head 133 jobs / 5,451 s / 10 packs; base 133 jobs / 5,451 s / 10 packs; ceilings 134 / 5,600 / 10
contract-delta: probe engine/prophet/plan_book.py: head 128 jobs / 5,413 s / 10 packs; base 128 jobs / 5,413 s / 10 packs; ceilings 129 / 5,600 / 10
contract-delta: head census seconds: closure_and_suites 157.9, probes 61.4, skip_only 13.0, trigger_gaps 21.1
contract-delta: base census seconds: closure_and_suites 166.8, probes 68.3, skip_only 13.1, trigger_gaps 21.0
::error title=contract-delta::tests/verification/test_access_q02.py is a new pytest suite named by no run: step in any workflow — wire it into the job that owns its subject in .github/ci/legacy-jobs.yml, or add a reasoned row to config/unrun_test_waivers.yml
contract-delta: 1 introduced, 0 inherited (base ed1497887c99101bd1b8bc5438e281f02466371b)
contract-delta: wall 292.7 s
```
