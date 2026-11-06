# Header

- Head reviewed: `ab640a6a606b64b1b465fa6c75a2e6d9ca144121` (`git rev-parse HEAD` in the worktree, detached — matches the commission).
- Branch/PR: `claude/healthcare-d1-fda-supply` / PR #7930.
- Files read at head: `collectors/fda_shortages.py` (500 lines), `scripts/build_foresight.py` (diff only, +12/-2), `tests/test_fda_shortages_generation.py` (482 lines), `tests/test_fda_supply_probes.py` (names only).
- Rulings read from `origin/main`: `research/healthcare/hc_program/reviews/SEAT_RULINGS_T02_R1_2026-09-24.md` (R-T02-01…17).
- Commands run: `git rev-parse HEAD`; `git diff --stat origin/main...ab640a6a606b`; `git diff origin/main...ab640a6a606b -- scripts/build_foresight.py`; four adversarial Python scripts executed as `PYTHONPATH=. python3 /tmp/atk{1,2,3,4}.py` from the worktree root plus one inline malformed-value probe; `git diff ... | grep -inE 'glut|tell|all-clear|catching up'`.
- Mode: READ-ONLY. No repo/`data/`/`site/` writes, no `gh`, no git writes, no network. All temp artifacts under `/tmp`.

# Verdict

**REJECT** — five BLOCKERs: the 90-generation retention model is inoperative in one direction and *destroys freshly observed rows* in the other (R-T02-14), a torn parquet raises `ArrowInvalid` out of `read_shortage_observation`/`load_shortages_cache` instead of returning `inconsistent=True` (R-T02-11), a failed refresh on an inconsistent pair permanently nulls `selected_capture` (R-T02-03), and a malformed field *value* escapes the pure sweep as an uncaught `TypeError` (R-T02-16 + the module's own "never raises into the build" claim).

# Findings

| ID | Severity | Ruling/law | file:line or command | Counterexample (measured) | Smallest fix |
|---|---|---|---|---|---|
| T02-B1 | BLOCKER | R-T02-14 (absent row ages out after 90 distinct generations) | `collectors/fda_shortages.py:316-322`, esp. `:319` | 95 sequential qualified saves; row `A` went absent at generation `2026-G001`. Measured: `A_still_present=True A.absent_since='2026-G094' dropped_absent_rows=0`. `absent_since_generation` is re-stamped to the *current* generation on every sweep, so no absent row can ever exceed the cap. | Only set `absent_since_generation` when it is currently null: `row["absent_since_generation"] = old_value or generation`. |
| T02-B2 | BLOCKER | R-T02-14 (retention drops *absent* rows only) | `collectors/fda_shortages.py:360-362` | Previous frame = 95 absent rows with distinct `absent_since_generation` (G000…G094) + a new qualified sweep containing one present row `FRESH`. Measured: `promoted=True rows_after=95 FRESH_present=False dropped=1` — the only *live* row was deleted and counted as an absent drop, while all 95 absent rows survived. Cause: `.map(lambda ...)` converts the null `absent_since_generation` of present rows to rank `0`, so `absent.isna()` is never true and every present row falls below `floor_rank`. | Compute the rank on the non-null subset only: `keep = frame["absent_since_generation"].isna() | frame["absent_since_generation"].map(generation_rank).fillna(-1).ge(floor_rank)` — and derive `known` from a persisted generation ledger, not from the surviving frame. |
| T02-B3 | BLOCKER | R-T02-11 (digest mismatch ⇒ `{"rows": None, ..., "inconsistent": True}`) | `collectors/fda_shortages.py:261` (parquet read) precedes `:268` (digest check); escapes via `:483` and `:490` | Saved a qualified observation, truncated the parquet by 40 bytes (a torn write — exactly the crash R-T02-11 exists for). Measured: `read_shortage_observation RAISED ArrowInvalid: Could not open Parquet input source '<Buffer>': Parquet magic bytes not found in footer`, and `load_shortages_cache` re-raised it into the caller. A *valid-but-different* parquet correctly returns `inconsistent=True rows=None capture=None`, so only the corruption path is broken — i.e. the exact case the contract names. | Verify the digest **before** reading the parquet, and wrap the read: on `expected is None or _digest(path) != expected` return the inconsistent dict without touching pyarrow; wrap `pd.read_parquet` in `try/except Exception` → same inconsistent dict. |
| T02-B4 | BLOCKER | R-T02-03 ("the selected capture's `finished_at`/`source_generation` are never rewritten"); R-T02-11 ("the next qualified sweep repairs both files") | `collectors/fda_shortages.py:423` reading `_selected_state`'s nulled capture from `:269` | Qualified save (`source_generation=2026-09-23`) → parquet tampered → one failed refresh. Measured: sidecar `selected_capture` went `2026-09-23` → `None`. The last qualified capture record is destroyed *by a read-only failure*, so the artifact can never again report what it last held, and the "repair on next qualified sweep" promise loses its baseline (including the generation-monotonicity floor of R-T02-12). | In the unqualified branch, carry forward the sidecar's stored `selected_capture` verbatim (`json.loads(sidecar)["selected_capture"]`), never `_selected_state()["capture"]`, which is deliberately nulled on inconsistency. |
| T02-B5 | BLOCKER | R-T02-16 (`KEY_ABSENT` / no silent collision); `collect_shortage_sweep` docstring `:116-117` ("malformed values are rejected as `MALFORMED_ROW`"); module docstring `:18` ("never raises into the build") | `collectors/fda_shortages.py:178` (`rows_by_key[key] = parsed`); `:163-180`; sweep call at `:471-474` sits **outside** the `try` at `:475` | Single upstream record with `package_ndc: ["A","B"]` → `collect_shortage_sweep RAISED TypeError: cannot use 'tuple' as a dict key (unhashable type: 'list')`; same for a dict-valued `initial_posting_date`. A record with `package_ndc: 12345` measured `failure_code=None qualified=True rows=1` — an int key is promoted and will not match the string `"12345"` key of any other generation, silently forking one product into two rows. `MALFORMED_ROW` only fires when the whole row is not a dict (`:165`). | Validate types after `_parse_record`: `if not isinstance(package_ndc, str) or not isinstance(posting_date, str): failure_code = "MALFORMED_ROW"; break` — placed before the `KEY_ABSENT` emptiness test. |
| T02-M1 | MAJOR | R-T02-02 ("never read the wall clock directly inside the pure function") | `collectors/fda_shortages.py:83` (`_parse_record`), called from the sweep at `:168` | `inspect.getsource(M._parse_record)` contains `datetime.now(timezone.utc)`. `clock()` is correctly called exactly twice (measured `clock_calls=2`, `interval=8.0` and `30.0`), but every row still stamps `fetched_utc` from the real wall clock inside the pure function, so the function is not deterministic under a supplied clock and two replays of identical pages produce different parquet bytes. R-T02-10 pins the *signature* of `_parse_record`, not its body. | Pass the sweep's `started` into `_parse_record` via a default-None keyword (`_parse_record(rec, observed_at=None)`), defaulting to `datetime.now` only when called outside the sweep, and have the sweep pass `_iso_utc(started)`. |
| T02-M2 | MAJOR | R-T02-11 (`inconsistent` means a torn pair) | `collectors/fda_shortages.py:267-269` | Fresh directory, no artifact ever saved, one failed refresh (which writes a sidecar with `parquet_sha256: None`). Measured: `read_shortage_observation` → `inconsistent=True rows=None capture=None`. A never-observed feed is indistinguishable from a corrupted pair, so T01's consumer will raise a data-integrity alarm on a cold start. | Branch on `expected is None and not path.exists()` → leave `inconsistent` False (a "no observation yet" state) and reserve `inconsistent=True` for a present-but-mismatching parquet. |
| T02-N1 | MINOR | R-T02-14 (`retention.dropped_absent_rows`) | `collectors/fda_shortages.py:428` | Sidecar with `retention.dropped_absent_rows = 7` + one failed refresh → measured `after=0`. The read path looks under `history_coverage["retention"]`, a key the schema never has. | Read from the sidecar's top-level `retention` block. |
| T02-N2 | MINOR | accuracy of authored prose | `collectors/fda_shortages.py:16` | Module docstring still says the cache is "append-only"; R-T02-14 retention deletes rows, and B2 shows it deleting live ones. | Replace with the R-T02-14 wording already used at `:278-283`. |
| T02-N3 | MINOR | hygiene | `collectors/fda_shortages.py:45` | `HISTORY_COLUMNS` closes with the copy-pasted comment `# polite pacing between pages` (duplicated from `:39`). | Delete. |
| T02-N4 | MINOR | boundary types | `collectors/fda_shortages.py:233`, `:321` | Legacy row's `capture_known` measured as `np.False_`, not a Python `bool`; a consumer doing `value is False` fails. | `bool(...)` at the sidecar/frame boundary or cast the column with `.astype("boolean")` and document it. |
| T02-N5 | MINOR | R-T02-09 (drip is additive) | `scripts/build_foresight.py:111-122` | The new `read_shortage_observation` call shares the existing `try`, so a B3-class raise *after a fully successful fetch* is logged as `fda_shortages drip failed (non-fatal)` — a false failure attribution. Otherwise the diff is behaviourally inert: `fetch_shortages()` is still called exactly once, the receipt is a plain `log.info` (no `::notice`), and nothing else in `main()` changes. | Give the receipt read its own inner `try/except` that logs a distinct message. |
| T02-N6 | MINOR | crash consistency | `collectors/fda_shortages.py:219` | Staging file name is keyed on `os.getpid()` only; two threads in one process share it. | Add `uuid4().hex` (or `os.getpid()`+`threading.get_ident()`). |

# Attacks run

1. **Partial acquisition never promoted** — `collect_shortage_sweep` with page 2 raising `OSError`, `page_size=1, max_pages=3`, then `save_shortage_observation(..., expected_predecessor=None)`. Measured: `qualified=False code=PAGE_FAILED rows=[] parquet_exists=False last_refresh={'attempted_at': '2026-09-23T12:00:08+00:00', 'failure_code': 'PAGE_FAILED', 'partial_rows_observed': 0, 'qualified': False}`. **PASS**
2. **Failure codes from the live reported total** — six synthetic page functions. Measured: `FIRST_PAGE_OUTAGE` (reported_total=None), `COUNT_DRIFT`, `GENERATION_DRIFT`, `REPEATED_PAGE`, `MALFORMED_ROW`, and `CAP_BEFORE_TOTAL` with `reported_total=3000, page_size=2, max_pages=3` → `got=CAP_BEFORE_TOTAL rows=0 reported_total=3000` (live `meta.results.total`, not `MAX_PAGES`). `KEY_ABSENT` for `package_ndc==""` and for `initial_posting_date==""`; two keyless records → `KEY_ABSENT` with `unique_count=0` (never merged). All `rows == []`. **PASS**
   2b. **Malformed field values** (same law, R-T02-16 collision clause) — `package_ndc=["A","B"]` → `TypeError` escaped the pure function; `initial_posting_date={"x":1}` → `TypeError`; `package_ndc=12345` → `failure_code=None qualified=True rows=1`. **FAIL** (T02-B5)
3. **Clock discipline** — instrumented `clock()` counting calls. Measured `clock_calls=2, acquisition_interval_s=8.0 (float)` on the failure path and `calls=2, interval=30.0` on the success path. **PASS**
4. **Predecessor fence and ordering** — `expected_predecessor="deadbeef"` → `reason=PREDECESSOR_MISMATCH, promoted=False, sidecar_unchanged=True, rows=['A']`; then with the CORRECT predecessor and an older generation → `reason=GENERATION_REGRESSION, sidecar_unchanged=True` (so the predecessor check demonstrably runs first); equal generation with a later `started_at` → `promoted=True`. **PASS**
5. **Crash consistency** — (a) valid-but-rewritten parquet → `inconsistent=True rows=None capture=None` **PASS**; (b) parquet truncated by 40 bytes → `read_shortage_observation RAISED ArrowInvalid` **FAIL**; (c) `load_shortages_cache()` on the same artifact → `RAISED ArrowInvalid into the caller` **FAIL** (T02-B3).
6. **Retention model** — status change and single absence transitions behave per R-T02-04/14 (covered by the builder suite and re-confirmed incidentally). 95 sequential qualified saves with row `A` absent from generation 2 onward: `A_still_present=True A.absent_since='2026-G094' dropped_absent_rows=0` **FAIL** (T02-B1). Hand-built predecessor frame with 95 distinct `absent_since_generation` values + one new present row: `rows_after=95 FRESH_present=False dropped=1` **FAIL** (T02-B2). Schema check `retention={'absent_generations_kept': 90, 'dropped_absent_rows': 0}` with no `row_cap` **PASS**. Counter preservation across a failed refresh (seeded at 7) → `after=0` **FAIL** (T02-N1).
7. **Legacy parquet** — 13 incumbent columns, no sidecar: `legacy=True capture=None legacy_rows_capture_unknown=True`; after the first qualified save `earliest_qualified_generation='2026-09-23'` (no backfill), `legacy_rows_capture_unknown=True`, legacy row `capture_known=np.False_`. **PASS** (type nit T02-N4).
8. **`df.attrs["fda_observation"]`** — `fetch_shortages()` and `load_shortages_cache()` both carry exactly `['capture','failed_refresh','inconsistent','last_refresh','legacy']`. **PASS**
9. **Unqualified never rewrites the selected capture** — healthy artifact: `selected_capture` unchanged, `last_refresh.attempted_at='2026-09-25T12:00:05+00:00'` (the failed sweep's own clock) **PASS**; inconsistent artifact: `before=2026-09-23 after=None` **FAIL** (T02-B4).
10. **Sidecar reproducibility** — sidecar bytes are byte-identical to `json.dumps(json.loads(raw), sort_keys=True, indent=2)`. **PASS**
11. **Banned substrings** — `git diff origin/main...ab640a6a606b -- collectors/fda_shortages.py scripts/build_foresight.py | grep '^+' | grep -inE 'glut|tell|all-clear|catching up'` → no match; same grep over the builder test diff → no match. **PASS**
12. **`fetched_utc` as legacy-only** — retained as a row field; but `_parse_record:83` stamps it from `datetime.now` inside the pure sweep. Capture clocks (`started_at`/`finished_at`) are never taken from it. **FAIL on the purity half** (T02-M1).
13. **Atomic-rename claims** — `save_shortage_observation:278-283` states verbatim that atomic rename is not multi-writer fencing, that the fence covers one checkout only, and that cross-checkout divergence is caught by the parquet digest (R-T02-13). No overstatement found. **PASS**
14. **`time.sleep` placement** — `'time.sleep' in inspect.getsource(collect_shortage_sweep) == False`; present only in the `fetch_shortages` closure. **PASS**
15. **Wrapper on first-page outage** — with a persisted qualified baseline: returns the previous frame `['A']`, `failed_refresh=True`, `capture.source_generation='2026-09-20'`; with nothing persisted: returns `None`. **PASS** (but see T02-M2: the cold-start sidecar then reads `inconsistent=True`).
16. **Builder-test falsifiability** — see the next section. **FAIL** for five tests/assertions that cannot discriminate.

Extra (not on the commissioned list): `scripts/build_foresight.py` diff alters nothing but the imports, one `read_shortage_observation` call and one `log.info`, all inside the pre-existing non-fatal `try` — R-T02-09 holds, with the attribution nit T02-N5.

# Probe proposals

Literal bodies for the seat to freeze (stdlib/pandas/pytest/hashlib/json + `collectors.fda_shortages` only). Shared helpers are repeated inside each function on purpose so any one can be lifted alone.

```python
def _t02r_clock(start, finish):
    calls = {"n": 0}
    def tick():
        calls["n"] += 1
        return start if calls["n"] == 1 else finish
    return tick


def _t02r_sweep(generation, records, start=None):
    from datetime import datetime, timezone
    from collectors.fda_shortages import collect_shortage_sweep
    start = start or datetime(2026, 9, 23, 12, tzinfo=timezone.utc)
    finish = start.replace(second=6)
    def fetch_page(skip, limit):
        return {"meta": {"last_updated": generation,
                         "results": {"total": len(records)}},
                "results": list(records[skip:skip + limit])}
    return collect_shortage_sweep(fetch_page, clock=_t02r_clock(start, finish),
                                  page_size=100, max_pages=5)


def _t02r_record(ndc="A", status="Current", posted="2026-03-02"):
    return {"package_ndc": ndc, "generic_name": "Synthetic", "status": status,
            "availability": "Available", "initial_posting_date": posted}


def _t02r_digest(path):
    import hashlib
    sidecar = path.with_suffix(".observation.json")
    return hashlib.sha256(sidecar.read_bytes()).hexdigest() if sidecar.exists() else None


def test_t02r_absent_row_keeps_its_original_absence_generation(tmp_path):
    """T02-B1: absent_since_generation is the generation the row WENT absent."""
    from datetime import datetime, timezone
    from collectors.fda_shortages import (
        read_shortage_observation, save_shortage_observation,
    )
    path = tmp_path / "shortages.parquet"
    predecessor = None
    for index in range(5):
        generation = f"2026-G{index:03d}"
        start = datetime(2026, 1, 1 + index, 12, tzinfo=timezone.utc)
        records = [_t02r_record("A"), _t02r_record("B")] if index == 0 else [_t02r_record("B")]
        outcome = save_shortage_observation(
            _t02r_sweep(generation, records, start=start),
            path=path, expected_predecessor=predecessor,
        )
        assert outcome["promoted"] is True, outcome
        predecessor = outcome["predecessor"]
    rows = read_shortage_observation(path=path)["rows"].set_index("package_ndc")
    assert rows.loc["A", "absent_since_generation"] == "2026-G001"
    assert rows.loc["A", "last_observed_generation"] == "2026-G000"
    assert rows.loc["A", "status"] == "Current"


def test_t02r_retention_drops_absent_rows_only_after_ninety_generations(tmp_path):
    """T02-B1/B2: the cap fires, counts, and never deletes a present row."""
    import json
    from datetime import datetime, timezone
    from collectors.fda_shortages import (
        read_shortage_observation, save_shortage_observation,
    )
    path = tmp_path / "shortages.parquet"
    predecessor = None
    for index in range(95):
        generation = f"2026-G{index:03d}"
        start = datetime(2026, 1, 1, 12, tzinfo=timezone.utc).replace(
            minute=index % 60) + __import__("datetime").timedelta(days=index)
        records = [_t02r_record("A"), _t02r_record("B")] if index == 0 else [_t02r_record("B")]
        outcome = save_shortage_observation(
            _t02r_sweep(generation, records, start=start),
            path=path, expected_predecessor=predecessor,
        )
        assert outcome["promoted"] is True, (index, outcome)
        predecessor = outcome["predecessor"]
    state = read_shortage_observation(path=path)
    present = state["rows"]["package_ndc"].tolist()
    receipt = json.loads(path.with_suffix(".observation.json").read_text())
    assert "B" in present, "the continuously observed row must never be dropped"
    assert "A" not in present, "absent for 94 generations, past the 90-generation cap"
    assert receipt["retention"]["absent_generations_kept"] == 90
    assert receipt["retention"]["dropped_absent_rows"] >= 1


def test_t02r_torn_parquet_reads_as_inconsistent_not_an_exception(tmp_path):
    """T02-B3: a half-written parquet must return the inconsistent dict."""
    from collectors.fda_shortages import (
        load_shortages_cache, read_shortage_observation, save_shortage_observation,
    )
    import collectors.fda_shortages as module
    path = tmp_path / "shortages.parquet"
    save_shortage_observation(
        _t02r_sweep("2026-09-23", [_t02r_record()]),
        path=path, expected_predecessor=None,
    )
    path.write_bytes(path.read_bytes()[:-40])
    state = read_shortage_observation(path=path)
    assert state["inconsistent"] is True
    assert state["rows"] is None
    assert state["capture"] is None
    assert state["last_refresh"] is not None
    original = module._shortages_path
    module._shortages_path = lambda: path
    try:
        assert load_shortages_cache() is None
    finally:
        module._shortages_path = original


def test_t02r_failed_refresh_never_erases_the_selected_capture(tmp_path):
    """T02-B4: an unqualified sweep on an inconsistent pair keeps the record."""
    import json
    from datetime import datetime, timezone
    import pandas as pd
    from collectors.fda_shortages import (
        collect_shortage_sweep, save_shortage_observation,
    )
    path = tmp_path / "shortages.parquet"
    save_shortage_observation(
        _t02r_sweep("2026-09-23", [_t02r_record()]),
        path=path, expected_predecessor=None,
    )
    sidecar = path.with_suffix(".observation.json")
    before = json.loads(sidecar.read_text())["selected_capture"]
    pd.read_parquet(path).assign(generic_name="TAMPERED").to_parquet(path, engine="pyarrow")
    def outage(skip, limit):
        raise OSError("synthetic outage")
    failed = collect_shortage_sweep(
        outage,
        clock=_t02r_clock(datetime(2026, 9, 25, 12, tzinfo=timezone.utc),
                          datetime(2026, 9, 25, 12, 0, 5, tzinfo=timezone.utc)),
        page_size=100, max_pages=3,
    )
    save_shortage_observation(failed, path=path, expected_predecessor=_t02r_digest(path))
    receipt = json.loads(sidecar.read_text())
    assert receipt["selected_capture"] == before
    assert receipt["last_refresh"]["qualified"] is False
    assert receipt["last_refresh"]["attempted_at"] == "2026-09-25T12:00:05+00:00"


def test_t02r_malformed_field_values_are_rejected_not_raised(tmp_path):
    """T02-B5: bad value TYPES yield MALFORMED_ROW; the sweep never raises."""
    from datetime import datetime, timezone
    from collectors.fda_shortages import collect_shortage_sweep
    for bad in (
        {"package_ndc": ["A", "B"], "initial_posting_date": "2026-03-02", "status": "Current"},
        {"package_ndc": "A", "initial_posting_date": {"x": 1}, "status": "Current"},
        {"package_ndc": 12345, "initial_posting_date": "2026-03-02", "status": "Current"},
    ):
        def fetch_page(skip, limit, _bad=bad):
            return {"meta": {"last_updated": "2026-09-23", "results": {"total": 1}},
                    "results": [_bad]}
        result = collect_shortage_sweep(
            fetch_page,
            clock=_t02r_clock(datetime(2026, 9, 23, 12, tzinfo=timezone.utc),
                              datetime(2026, 9, 23, 12, 0, 6, tzinfo=timezone.utc)),
            page_size=100, max_pages=2,
        )
        assert result["failure_code"] == "MALFORMED_ROW", bad
        assert result["qualified"] is False
        assert result["rows"] == []


def test_t02r_sweep_is_deterministic_under_a_supplied_clock():
    """T02-M1: no wall clock inside the pure function."""
    import inspect
    from datetime import datetime, timezone
    import collectors.fda_shortages as module
    source = inspect.getsource(module._parse_record)
    assert "datetime.now" not in source, (
        "_parse_record stamps fetched_utc from the wall clock inside collect_shortage_sweep"
    )
    start = datetime(2026, 9, 23, 12, tzinfo=timezone.utc)
    first = _t02r_sweep("2026-09-23", [_t02r_record()], start=start)
    second = _t02r_sweep("2026-09-23", [_t02r_record()], start=start)
    assert first["rows"] == second["rows"]
    assert first["capture"] == second["capture"]


def test_t02r_cold_start_failure_is_not_an_integrity_alarm(tmp_path):
    """T02-M2: never-observed is not the same state as a torn pair."""
    from datetime import datetime, timezone
    from collectors.fda_shortages import (
        collect_shortage_sweep, read_shortage_observation, save_shortage_observation,
    )
    path = tmp_path / "shortages.parquet"
    def outage(skip, limit):
        raise OSError("synthetic outage")
    failed = collect_shortage_sweep(
        outage,
        clock=_t02r_clock(datetime(2026, 9, 25, 12, tzinfo=timezone.utc),
                          datetime(2026, 9, 25, 12, 0, 5, tzinfo=timezone.utc)),
        page_size=100, max_pages=3,
    )
    save_shortage_observation(failed, path=path, expected_predecessor=None)
    state = read_shortage_observation(path=path)
    assert state["inconsistent"] is False
    assert state["capture"] is None
    assert state["last_refresh"]["failure_code"] == "FIRST_PAGE_OUTAGE"


def test_t02r_dropped_absent_rows_survives_a_failed_refresh(tmp_path):
    """T02-N1: the retention counter is read from the sidecar's own block."""
    import hashlib, json
    from datetime import datetime, timezone
    import pandas as pd
    from collectors.fda_shortages import collect_shortage_sweep, save_shortage_observation
    path = tmp_path / "shortages.parquet"
    pd.DataFrame([{
        "package_ndc": "A", "initial_posting_date": "2026-03-02", "status": "Current",
        "first_observed_generation": "g", "last_observed_generation": "g",
        "absent_since_generation": None, "previous_status": None,
        "status_changed_generation": None, "capture_known": True,
    }]).to_parquet(path, engine="pyarrow")
    capture = {"started_at": "2026-01-01T00:00:00+00:00",
               "finished_at": "2026-01-01T00:00:06+00:00", "source_generation": "g",
               "pages": 1, "page_size": 100, "max_pages": 5, "raw_count": 1,
               "unique_count": 1, "reported_total": 1, "complete": True,
               "atomic_snapshot_proven": False, "acquisition_interval_s": 6.0}
    receipt = {
        "schema": "fda_shortages_observation.v1", "selected_capture": capture,
        "last_refresh": {"attempted_at": capture["finished_at"], "qualified": True,
                         "failure_code": None, "partial_rows_observed": 0},
        "history_coverage": {"earliest_qualified_generation": "g",
                             "legacy_rows_capture_unknown": False,
                             "forward_retention_started_at": capture["finished_at"]},
        "retention": {"absent_generations_kept": 90, "dropped_absent_rows": 7},
        "predecessor": None,
        "parquet_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    sidecar = path.with_suffix(".observation.json")
    sidecar.write_text(json.dumps(receipt, sort_keys=True, indent=2))
    def outage(skip, limit):
        raise OSError("synthetic outage")
    failed = collect_shortage_sweep(
        outage,
        clock=_t02r_clock(datetime(2026, 9, 25, 12, tzinfo=timezone.utc),
                          datetime(2026, 9, 25, 12, 0, 5, tzinfo=timezone.utc)),
        page_size=100, max_pages=3,
    )
    save_shortage_observation(failed, path=path, expected_predecessor=_t02r_digest(path))
    assert json.loads(sidecar.read_text())["retention"]["dropped_absent_rows"] == 7
```

# Builder-test co-variance

The fixtures are **not** generated from the code under test — `_page` (`tests/test_fda_shortages_generation.py:31`) is hand-built JSON, `_sidecar_digest` (`:63`) independently re-implements the sha256 rather than calling `_digest`, and every expected generation string / timestamp is a literal. That part of the suite is honest. The failure mode here is **coverage that stops exactly short of the rulings' load-bearing numbers**, plus four assertions that cannot discriminate:

1. `_clock` (`:38-46`) returns `finish` for **every** call after the first. A regression that called `clock()` once per page would still produce `acquisition_interval_s == 6.0`, so nothing in the builder suite can fail on R-T02-02's "exactly twice". No test counts the calls.
2. `test_disappeared_row_is_retained_with_absence_generation` (`:264`) runs exactly **two** generations. The row goes absent in the second and is asserted at that same generation — so T02-B1 (absent_since re-stamped every sweep) is invisible: the assertion `== "2026-09-23"` is true both under the correct semantics and under the bug. Any test of this rule needs ≥3 generations.
3. **No test anywhere constructs more than two generations.** R-T02-14's entire retention cap — the 90-generation threshold and `retention.dropped_absent_rows` — is asserted by **zero** tests in the file (`grep -c dropped_absent_rows tests/test_fda_shortages_generation.py` → 0). Both T02-B1 and T02-B2 live in that hole, and B2 silently deletes live data.
4. `test_failed_metadata_write_is_not_advertised_as_current` (`:318`) produces the inconsistent state by leaving a **valid** parquet with a stale digest. That is the one corruption flavour the implementation handles; the torn-bytes flavour R-T02-11 actually exists for (T02-B3) is never exercised. The test also stops at `read_shortage_observation` and never performs the *next* failed refresh, which is where T02-B4 destroys `selected_capture`.
5. `test_every_qualified_capture_disclaims_snapshot_proof:481` — `assert type(result["capture"]["atomic_snapshot_proven"]) is bool` is a tautology against `fda_shortages.py:208`, which assigns the literal `False`. It can only fail if someone deletes the literal, which line 482 already catches. Harmless, but it is not evidence of anything.
6. `test_absent_stable_key_disqualifies_without_collapsing_rows` (`:225`) parametrises three *empty/missing* key cases and none of the *wrong-type* cases, so T02-B5's uncaught `TypeError` and the int-key collision pass unchallenged — while `collect_shortage_sweep`'s own docstring (`fda_shortages.py:116-117`) advertises value-level `MALFORMED_ROW` rejection that does not exist.
7. `test_legacy_cache_has_unknown_capture_and_starts_forward_history:314` uses `not bool(rows.loc[...])`, which papers over T02-N4 (the value is `numpy.bool_`). A consumer written to R-T02-15 with `is False` would fail where this test passes.

Sound and genuinely discriminating: `test_interleaved_older_writer_is_refused` (`:346`) — `PREDECESSOR_MISMATCH` vs `GENERATION_REGRESSION` are distinct strings, so it really does pin R-T02-12's ordering; `test_cap_before_total_uses_live_reported_total` (`:196`); the `COUNT_DRIFT`/`GENERATION_DRIFT`/`REPEATED_PAGE` parametrisation (`:141`); and `test_wrapper_returns_previous_qualified_frame_after_failed_refresh` (`:398`).

# Gaps

- The six T01 probes (`test_r8_a18/a19/a20/a21`, `test_r9_a07`, `test_r10_a11`) are out of scope and expected red; not evaluated.
- The `healthcare-fda-supply` job's `paths:` / import-closure contract-delta is excluded by commission and not attacked.
- I did not execute either pytest file (read-only sandbox, and the generation suite imports `scripts.build_foresight`, whose import chain is the lane being repaired). Every finding is therefore measured by direct invocation of `collectors.fda_shortages`, not by test-run outcome; the builder-suite analysis is static plus targeted counterexample construction.
- Multi-process / multi-checkout behaviour of the predecessor fence (R-T02-13) was reasoned from the source, not raced — the ruling explicitly scopes the fence to one checkout and the docstring states the limitation verbatim, so a race probe would not change the verdict.
- Real-endpoint schema drift (e.g. whether openFDA ever emits a non-string `package_ndc`) was not verified — no network. T02-B5 stands on the contract ("`MALFORMED_ROW`", "never raises into the build"), not on an observed upstream payload.
- `python3` here is 3.14 with pandas/pyarrow from the host; parquet-engine behaviour on the CI runner was not independently confirmed.
