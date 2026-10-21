# B23 journey latency acceptance — adversarial review (PR #9947)

- Seat: `lane/pro-source-b23-review-20261021-r1`, ROUTE review, CLASS C1, MODE READ_ONLY
- Reviewed range: `a5498b7e93f3d21390276ebf86b8245e117770ed..cfb8b81fa2b432a117b69f4c5f4e1fb13974f498` (one commit: `cfb8b81fa2b4 prophet r7 B23: journey latency acceptance — lab timing capture, lab serve, latency report (hermetic)`)
- Review standard: frozen spec (seat packets B23 BU1 and BU4+BU5), surfaces 1–8
- Worktree at HEAD == BASE `cfb8b81fa2b4`, clean before and after; mutations ran only in a `/tmp` throwaway copy (removed afterwards; `git status` clean at close)

## Verdict table

| # | Surface | Verdict |
|---|---|---|
| 1 | Hermeticity | PASS |
| 2 | Probe invariant (no subprocess / enumeration in capture module) | PASS |
| 3 | Timing truth (nullable, lab basis, anonymous law unchanged) | PASS |
| 4 | Statistics (nearest-rank p75, nulls, determinism, verdict set) | PASS (2 NOTEs) |
| 5 | Server safety (loopback bind, 403 refusals, append-only journal) | PASS (1 NOTE) |
| 6 | Test realism (two mutations, both caught) | PASS (1 NOTE) |
| 7 | CI registration under `washout-turn-organ` | PASS (1 NOTE) |
| 8 | Custody and collisions | PASS |

**STATUS: PASS_WITH_NOTES** — no BLOCKING finding. Four NOTEs and one mutation-breadth NOTE, none affecting the frozen spec items.

## Required commands (verbatim tails)

```
$ python3 -m pytest -q -p no:cacheprovider tests/test_prophet_journey_lab_serve.py tests/test_prophet_journey_latency_report.py tests/test_capture_page_evidence.py
112 passed in 7.18s

$ python3 -m pytest -q -p no:cacheprovider tests/test_capture_page_evidence.py -k "subprocess or enumeration"
2 passed, 83 deselected in 0.84s        EXIT=0

$ python3 -m pytest -q -p no:cacheprovider tests/test_ci_pack.py -k "exclusive or washout or narrow"
7 passed, 197 deselected in 117.08s (0:01:57)        EXIT=0

$ python3 scripts/capture_page_evidence.py --self-check        EXIT=0
```

Self-check fields quoted: `"ok": true`, `"timing_basis": "lab"`, `"access_captured": ["anonymous"]`, `"timing_keys": ["lcp_ms", "cls", "inp_proxy_ms", "resource_count", "transfer_bytes", "server_timing"]`, `"version": "1.4.0"`.

## Surface 1 — Hermeticity: PASS

- No `data/` exists in this worktree (`ls: cannot access 'data': No such file or directory`; sparse law honored — nothing in the diff or tests materializes it), and the full three-file run above passed anyway: 112/112. All fixtures live in `tmp_path`; `tests/conftest.py` imports only `os`, `subprocess`, `sys`, `pathlib`, `pytest` (env sentinel + write tripwires, no repo imports at collection).
- Import blocks are stdlib-only plus yaml/pytest; nothing imports from the repo at module import time:
  - `scripts/prophet_journey_lab_serve.py:58-69` — `argparse, hashlib, http.server, json, mimetypes, os, sys, threading, time, urllib.parse, pathlib, typing`.
  - `scripts/prophet_journey_latency_report.py:60-68` — `argparse, hashlib, json, math, sys, pathlib, typing` + `yaml` (existing repo test dependency; see surface 8).
  - `tests/test_prophet_journey_lab_serve.py:11-21` and `tests/test_prophet_journey_latency_report.py:11-18` — stdlib + pytest only.
- `spec_from_file_location` loads (module under test is loaded by path, never via repo `sys.path`):
  - `tests/test_prophet_journey_lab_serve.py:27-33` — `spec_from_file_location("prophet_journey_lab_serve_under_test", MODULE_PATH)`, `MODULE_PATH = ROOT / "scripts" / "prophet_journey_lab_serve.py"` (lines 23-24).
  - `tests/test_prophet_journey_latency_report.py:25-31` — `spec_from_file_location("prophet_journey_latency_report_under_test", MODULE_PATH)` (lines 20-22).
  - Pre-existing seam unchanged: `tests/test_capture_page_evidence.py:33-38` — `"capture_page_evidence_under_test"`.
- One nuance, not a defect: the report test reads the committed spec at collection time (`COMMITTED_SPEC = ROOT / "config" / "prophet_journey_latency.yml"` line 22, `SPEC = pjr.load_spec(COMMITTED_SPEC)` line 35). That is a data-file read of a declared repo artifact (the matrix under test), not a repo module import; the file is declared in the CI job's paths (surface 7).

## Surface 2 — Probe invariant (d): PASS

- The diff adds no subprocess, glob, iterdir, listdir, walk or scandir call or identifier to `scripts/capture_page_evidence.py`. A direct grep of the module hits only docstring/comment prose narrating the absence of these edges — e.g. `scripts/capture_page_evidence.py:47` ("No subprocess, no directory enumeration, anywhere in this module."), `:1043` ("see the module docstring §8 on why no glob lives here"), `:2085` ("Honest tradeoff against the ``glob(\"*.png\")`` this replaced") — no executable identifier.
- New token-level guard added by this diff (`tests/test_capture_page_evidence.py`, `test_the_module_source_greps_clean_of_subprocess_and_enumeration_tokens`): banned set `{"subprocess", "glob", "iterdir", "listdir", "walk", "scandir"}` checked against `tokenize.NAME` tokens, so prose is not an offender but any identifier anywhere is. Pre-existing AST-level guard at `tests/test_capture_page_evidence.py:1518` (`test_the_module_carries_no_subprocess_or_enumeration_edge`) also green.
- Command quoted above: `2 passed, 83 deselected in 0.84s`, exit 0.
- (The test file itself imports `subprocess` — pre-existing, used to exec the self-check probe; the invariant binds the module under test, not its tests.)

## Surface 3 — Timing truth (a)(b)(c): PASS

(a) Nullable, never synthesized, no zeros for missing metrics:

- `scripts/capture_page_evidence.py:895-898`:
  ```python
  def _null_timing() -> dict[str, Any]:
      """Every timing key present, all null. An unobserved value is null, not 0."""
      return {key: None for key in TIMING_KEYS}
  ```
- `scripts/capture_page_evidence.py:901-922` (`_timing_from`) copies only what the driver reported; unobserved keys stay null; only `server_timing` tuple→list normalization. A driver that reported nothing yields the all-null block (`if not reported: return timing`).
- Browser side, `scripts/capture_page_evidence.py:1654` (inside `_TIMING_SNAPSHOT_SCRIPT`): `inp_proxy_ms: interactions.length ? Math.max.apply(null, interactions) : null,` — null when the driver scripted no interaction, never 0. LCP store starts `null`. (CLS starts `0.0` and `transfer_bytes` sums observed `transferSize` — both are genuinely observed zeros, not filled-in values.)
- Every state row initializes `"timing": _null_timing()` (`scripts/capture_page_evidence.py:1075` area) and is then overwritten by `entry["timing"] = _timing_from(observation)` after evidence harvest — a failed-late load keeps whatever it observed, a no-timing driver keeps nulls.
- Tests pin it: `test_a_driver_without_timing_records_nulls_never_zeros` asserts `all(value is None for value in state["timing"].values())` for both captured and not-captured states.

(b) `timing_basis` is the constant "lab":

- `scripts/capture_page_evidence.py:149`: `TIMING_BASIS = "lab"`; stamped once per manifest at `:1256` (`"timing_basis": TIMING_BASIS,`) and in the self-check envelope at `:2286`. No flag, argument or code path can set another value.
- Consumer side: `scripts/prophet_journey_latency_report.py:249-253` refuses any manifest whose `timing_basis` is not `"lab"` (`SpecError`), pinned by `test_non_lab_manifest_or_wrong_schema_refused`.

(c) Anonymous access law unchanged:

- `scripts/capture_page_evidence.py:162-164` — `ACCESS_ANONYMOUS = "anonymous"`, `GATED_ACCESS_STATES: tuple[str, ...] = ("free", "essential", "pro")`, `GATED_ACCESS_REASON = "requires authenticated session; not automatable without approved fixtures"` — all appear in the diff only as unchanged context; no hunk modifies them. The self-check additions only add timing checks; the access-gap assertions remain (`:2054`).
- Live proof: `--self-check` exit 0, `"ok": true`, `"access_captured": ["anonymous"]`, gated states still disclosed as access gaps.

## Surface 4 — Statistics (e)(f)(g)(h): PASS, 2 NOTEs

(e) Nearest-rank p75 — `scripts/prophet_journey_latency_report.py:125-132`:

```python
def nearest_rank_percentile(sorted_values: Sequence[float], q: float) -> float:
    """Nearest-rank percentile: rank = ceil(q * n), 1-based, on sorted values."""
    n = len(sorted_values)
    if n == 0:
        raise ValueError("nearest_rank_percentile of an empty sample")
    rank = min(max(1, math.ceil(q * n)), n)
    return sorted_values[rank - 1]
```

Hand-check against ceil(0.75·n), 1-based, on ascending 1..n — confirmed both by hand and by loading the module:

| n | ceil(0.75·n) | 1-based rank | value | module returns |
|---|---|---|---|---|
| 1 | 1 | 1 | 1 | 1 |
| 4 | 3 | 3 | 3 | 3 |
| 25 | 19 | 19 | 19 | 19 |
| 30 | 23 | 23 | 23 | 23 |

Unsorted `[10, 1, 7, 4]` → sorted `[1,4,7,10]`, rank 3 → 7 (module: 7). Basis and n on every metric: `_metric_block` (`:447-452`) sets `"basis": BASIS_LAB` and `"n": len(samples)` on both budgeted and unbudgeted blocks. `INSUFFICIENT_SAMPLES` gate at `:470-472` (`if len(samples) < int(required_n or 0)`) returns before any p75, leaving `"p75": None`; config `config/prophet_journey_latency.yml` declares `required_n: 25` (lcp, cls) and `30` (inp). Nulls do not count toward n.

(f) Nulls excluded and counted — `scripts/prophet_journey_latency_report.py:407-413`:

```python
value = timing.get(self.statistics[stat]["manifest_key"])
if value is None:
    self.null_counts[key][stat] += 1
else:
    self.samples[key][stat].append(value)
```

`null_count` rides on every metric block (`:450`); `test_spec3_null_timing_excluded_and_counted_never_zero` pins null_count=5, n=25, p75=123 and `0 not in rc["values"]`.

(g) Byte-determinism, no clock — grep of `scripts/prophet_journey_latency_report.py` for `datetime`, `time.time`, `perf_counter`, `random`, `import time`, `utcnow`, `Date.now`: **zero hits** (exit 1). `--run-time` is a required argument (`:1012-1016`); `report_bytes` (`:848-851`) is `json.dumps(..., sort_keys=True, indent=2) + "\n"`; inputs are sorted before hashing/echo (`:708-712`); cells sorted (`:532-534`); routes sorted (`:547`). `test_spec5_report_bytes_deterministic_no_wall_clock` additionally source-scans the module for clock tokens and asserts argument-order independence.

(h) Closed verdict set, GAP never PASS — `scripts/prophet_journey_latency_report.py:80-90` defines exactly `PASS / FAIL / INSUFFICIENT_SAMPLES / GAP` with `VERDICT_ORDER`; `test_spec6` asserts every cell verdict ⊆ that set. The GAP path in `_metric_block` (`:467-469`) returns before both the insufficient check and the p75 computation:

```python
if gap:
    block["verdict"] = VERDICT_GAP
    return block
```

and the gap flag (`build_cells :499`, `gap = bool(reasons) or not captured_any`) keeps a recorded axis gap a GAP even when a contradictory load exists — `test_spec6` proves it with a gap cell carrying `n == 1`.

NOTE-1 (cosmetic, conservative direction): the `elif by_verdict[VERDICT_GAP]: overall = VERDICT_GAP` branch at `scripts/prophet_journey_latency_report.py:744-745` is unreachable — every GAP cell also increments the `recorded_gap_cells` failure class (budget 0, `:690-695`), so `:740` sets overall FAIL first. A gap can therefore never be smoothed into PASS (spec holds; it surfaces as the harsher FAIL), but the dead branch is misleading to read.

NOTE-2 (unreachable from the real writer): `scripts/prophet_journey_latency_report.py:549` — `elapsed = sorted(float(r.get("elapsed_ms") or 0.0) for r in rows)` — a hand-forged journal line with explicit `"elapsed_ms": null` would enter the server-held-time distribution as 0.0 instead of being excluded/counted. This is the server-journal leg, not a manifest timing metric (the (f) law), `record()` always writes a rounded float, and `load_journal` enforces key presence; still, an exclude-and-count would have been more in the house style.

## Surface 5 — Server safety (i): PASS, 1 NOTE

Bind — `scripts/prophet_journey_lab_serve.py:75` and `:341-343`:

```python
BIND_HOST = "127.0.0.1"                      # :75
...
def __init__(self, root: Path, journal: RequestJournal, port: int = 0) -> None:
    # BIND_HOST only — see contract §1. There is deliberately no parameter.
    super().__init__((BIND_HOST, port), LabServeHandler)
```

No widening surface exists: argparse offers only `--root`, `--journal`, `--port` (`:365-367`); `make_server(root, journal_path, port)` (`:352`) passes no address; `test_spec4_server_binds_127_0.0.0_1_only` asserts `server.server_address[0] == "127.0.0.1"` on the bound socket itself.

Refusals — `resolve_request_path` (`:159-205`): NUL byte `:174-175`; `..` segment `:188-189` ("target traverses above the served root"); absolute-artifact `//`-glued targets `:178-181`; and the containment check runs on the **fully resolved** candidate `:194-202` (`resolved.is_relative_to(root_resolved)`), which catches symlink escapes however spelled. The 403 path journals like any answer (`_answer :278-287` → `_send` → `journal.record`). Pinned by three named tests (dot-dot, absolute/%2F, symlink escape — each asserting 403s **and** journal lines; a symlink that stays inside the root still serves 200).

Journal append-only — `scripts/prophet_journey_lab_serve.py:113`:

```python
self._fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
```

never truncated; `seq` continues from existing lines (`:117-124`); `test_spec4_journal_is_append_only_never_truncated` proves prior lines survive and seq continues (3rd line gets `seq: 3`).

No directory listing: `/` and `…/` resolve to `index.html` or 404 (`:191-204`); no enumeration call exists in the module; `test_root_and_trailing_slash_serve_index_html` covers `/`, `/sub/` (200, index) and `/sub` (404). Every response carries `Cache-Control: no-store` (`:235`, asserted by test).

NOTE-3: methods outside {GET, HEAD, POST, PUT, DELETE} (e.g. OPTIONS, TRACE) fall through to `BaseHTTPRequestHandler`'s built-in 501, which is **not** journaled. All path-escape refusals and all explicitly handled methods are journaled (the spec (i) requirement), so this is an honesty edge of the "every request is journaled" contract prose, not a containment issue — loopback-only plus no read of such requests' targets keeps it inert.

## Surface 6 — Mutation realism: PASS, 1 NOTE

Method: a throwaway minimal copy at `/tmp/b23mut-min` (tests/conftest.py, the report test, the report script, the spec config — conftest is stdlib+pytest only), baseline `15 passed in 0.11s`, then one mutation at a time. The lane worktree was never edited; `git status` clean afterwards; copies removed.

(i) p75 by linear interpolation (rank formula replaced by `pos = q*(n-1)` interpolation) — caught, `2 failed, 13 passed`:

```
tests/...::test_spec2_p75_nearest_rank_known_vectors_n1_4_25_30
>       assert pjr.p75_nearest_rank([1, 2, 3, 4]) == 3
E       assert 3.25 == 3

tests/...::test_server_held_time_distribution_and_edge_timeout_risk
>       assert route["elapsed_ms"]["p75"] == 9.0
E       assert 8.5 == 9.0
```

(ii) Nulls appended as zeros (`self.samples[key][stat].append(0)` instead of `null_counts += 1`) — caught, full file `1 failed, 14 passed`:

```
tests/...::test_spec3_null_timing_excluded_and_counted_never_zero
>       assert lcp["null_count"] == 5
E       assert 0 == 5
```

NOTE-4: mutation (ii) is caught by exactly one test. That test pins the full discipline in one body (`null_count == 5`, `n == 25`, `p75 == 123`, `0 not in rc["values"]`), so the catch is real, but the null discipline has a single sentinel; a future refactor that splits the test could orphan it.

## Surface 7 — CI registration (j): PASS, 1 NOTE

Manifest hunk (all four additions sit between job key `washout-turn-organ:` at `.github/ci/legacy-jobs.yml:26187` and the next job `prophet-anticipation-intake:` at `:27256` — i.e. inside washout-turn-organ's `paths:` and `steps:`):

```yaml
       - "scripts/build_turn_watch.py"
+      - "scripts/capture_page_evidence.py"
+      - "scripts/prophet_journey_lab_serve.py"
+      - "scripts/prophet_journey_latency_report.py"
...
+      - "config/prophet_journey_latency.yml"
...
       - "tests/test_washout_turn.py"
+      - "tests/test_prophet_journey_lab_serve.py"
+      - "tests/test_prophet_journey_latency_report.py"
...
+      - name: Prophet B23 journey latency acceptance (lab serve + latency report, hermetic; loads the scripts by path)
+        run: python -m pytest tests/test_prophet_journey_lab_serve.py tests/test_prophet_journey_latency_report.py -q
```

- Paths coverage of what the two new tests load: `tests/test_prophet_journey_latency_report.py` loads `scripts/prophet_journey_latency_report.py` (`MODULE_PATH`, line 21) **and** `config/prophet_journey_latency.yml` (`COMMITTED_SPEC`, line 22) — both declared. `tests/test_prophet_journey_lab_serve.py` loads `scripts/prophet_journey_lab_serve.py` (line 24) — declared. All fixtures are inline/tmp_path; neither test opens anything else from the repo. Coverage complete.
- `prophet-anticipation-intake` untouched: the diff has no hunk at or beyond `:27256`; verified against job-key listing.
- CI pack: `7 passed, 197 deselected in 117.08s`, exit 0 — no failure, so the parent-manifest comparison case does not arise.

NOTE-5: `scripts/capture_page_evidence.py` in washout's `paths:` is surplus for the declared step — neither new test loads that module (the report tests hand-build BU1-shaped fixtures; the `module_ref` string is not a load), and no washout step runs `tests/test_capture_page_evidence.py` (at BASE that suite runs in the probe-selected `product-experience-capture` job, `.github/ci/legacy-jobs.yml:33264-33281`, which is untouched). A surplus paths entry can only over-trigger the job, never miss a run — harmless, listed for honesty.

## Surface 8 — Custody and collisions: PASS

`git diff --stat a5498b7e93f3d21390276ebf86b8245e117770ed..HEAD` names exactly the eight declared files:

```
 .github/ci/legacy-jobs.yml                   |    8 +
 config/prophet_journey_latency.yml           |  106 +++
 scripts/capture_page_evidence.py             |  208 ++++-
 scripts/prophet_journey_lab_serve.py         |  400 ++++++++++
 scripts/prophet_journey_latency_report.py    | 1062 ++++++++++++++++++++++++++
 tests/test_capture_page_evidence.py          |  220 ++++++
 tests/test_prophet_journey_lab_serve.py      |  290 ++++++
 tests/test_prophet_journey_latency_report.py |  582 ++++++++++
 8 files changed, 2874 insertions(+), 2 deletions(-)
```

- None of `scripts/build_prophet.py`, `engine/prophet_opportunity_presentation.py`, `templates/_prophet_setup_detail.html.j2`, `scripts/build_turn_watch.py`, `engine/news_impact/`, `.claude/`, `sol/` appears in the stat — all untouched (build_turn_watch.py appears only as unchanged context in the paths hunk).
- No secrets: a scan of the diff for `R2_`, `_KEY=`, `_SECRET`, `_TOKEN`, `password`, `BEGIN PRIVATE` matched only the new test's own name (`test_the_module_source_greps_clean_of_subprocess_and_enumeration_tokens`) and `tokenize.generate_tokens` — no credential material.
- No network at import time: both new scripts' import blocks are quoted in surface 1; nothing opens sockets at import (the server binds only in `make_server`/`main`).
- No new dependency: the only external import added anywhere is `yaml` in the report script; PyYAML is already a standard test dependency at BASE (e.g. `tests/test_marketing_reply_voice.py`, `tests/test_metabolism_v2b.py` `import yaml`), and the CI job's pytest environment already runs yaml-consuming suites.

## GAPS

- The Playwright driver paths (`_TIMING_INIT_SCRIPT`/`_TIMING_SNAPSHOT_SCRIPT` wiring in `_PlaywrightDriver`, `scripts/capture_page_evidence.py:1575-1832`) are exercised only at the source level: no browser exists in this lane (by design — the tests are hermetic and `# pragma: no cover - needs a browser` documents the seam). The JS was reviewed by reading, not by driving a real browser; that is the packet's own scope (`self-check` covers the canned seam).
- `tests/test_ci_pack.py -k "exclusive or washout or narrow"` passed, so the parent-vs-diff manifest bisect the packet asks for on failure was not applicable.
- The full-tree throwaway copy the packet suggests was impractical (large `site/` tree; the archive run was stopped); the mutation leg used a minimal copy containing exactly the files under mutation and their loaders, with a green baseline run before mutating. Nothing about the mutations depends on the wider tree (conftest is stdlib+pytest only).

## Deviations

- None material. The throwaway copy for surface 6 was minimal (six files) rather than a full tree copy, with an unmutated green baseline in that copy first; rationale and file list in GAPS.

SESSION END: PROVEN_OUTCOME
