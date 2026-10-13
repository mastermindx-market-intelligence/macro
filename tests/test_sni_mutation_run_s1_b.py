"""MUT5C killing tests for run_s1.py (line 462+) and s1_data.py.

SNI-local DRAFT contract tests. They consume caller-supplied opaque identity
strings and synthetic fixtures; they do not mint issuer or security identifiers
and they do not feed a rank, gate, size, signal, escalation, or trade path.
Authority flags stay false. Each test_mut5c_* docstring names one
non-equivalent mutant that survived the pre-existing importer suite
(file:line, original -> mutated).
"""
from __future__ import annotations

import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "research/single_name_intelligence/residual"))
sys.path.insert(0, str(REPO))

import run_s1  # noqa: E402
from s1_data import (  # noqa: E402
    GitBlobStore,
    IndexOnlySpy,
    InjectableStore,
    _to_date,
)
from s1_synth import sessions_us, walk  # noqa: E402

PX = "data/yahoo/SYN.parquet"
REF = "data/reference/master.parquet"


def _blob_store(tmp_path: Path) -> tuple[GitBlobStore, str, dict[str, str]]:
    """Tiny synthetic git repo with two parquet blobs. Isolated from the CI clone."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    repo = tmp_path / "blobrepo"
    (repo / "data" / "yahoo").mkdir(parents=True)
    (repo / "data" / "reference").mkdir(parents=True)
    pq.write_table(
        pa.table({"Date": [date(2020, 1, 2), date(2020, 1, 3)], "close": [10.0, 11.5]}),
        repo / "data" / "yahoo" / "SYN.parquet",
    )
    pq.write_table(
        pa.table({"security_id": ["SEC:SYN-1"], "issuer_id": ["ISS:SYN-1"]}),
        repo / "data" / "reference" / "master.parquet",
    )
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "add", "data/yahoo/SYN.parquet", "data/reference/master.parquet"],
        cwd=repo, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-c", "user.email=mut5c@example.test", "-c", "user.name=mut5c",
         "commit", "-m", "synth"],
        cwd=repo, check=True, capture_output=True,
    )
    ref = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True,
        capture_output=True, text=True,
    ).stdout.strip()

    def blob_id(path: str) -> str:
        return subprocess.run(
            ["git", "rev-parse", f"{ref}:{path}"], cwd=repo, check=True,
            capture_output=True, text=True,
        ).stdout.strip()

    pins = {PX: blob_id(PX), REF: blob_id(REF)}
    blobs = tmp_path / "blobs"
    blobs.mkdir()
    store = GitBlobStore(repo, ref, pins, workdir=blobs)
    return store, ref, pins


# ---------------------------------------------------------------------------
# run_s1 survivors
# ---------------------------------------------------------------------------


def test_mut5c_run_s1__byte_compare_1(tmp_path):
    """run_s1.py:1113, arith_swap `committed / rel` -> `committed * rel`."""
    a = tmp_path / "committed"
    b = tmp_path / "produced"
    for root in (a, b):
        (root / "results").mkdir(parents=True)
        (root / "observations").mkdir()
        (root / "REPORT.md").write_text("ok\n", encoding="utf-8")
        (root / "LANE_MANIFEST.json").write_text("{}\n", encoding="utf-8")
        (root / "trial_ledger.jsonl").write_text("", encoding="utf-8")
    assert run_s1._byte_compare(a, b) is True


def test_mut5c_run_s1__ledger_equal_1(tmp_path):
    """run_s1.py:1145, return rows(a) == rows(b) -> return None."""
    p = tmp_path / "a.jsonl"
    q = tmp_path / "b.jsonl"
    p.write_text('{"k":1,"ts":"wall-a"}\n{"k":2}\n', encoding="utf-8")
    q.write_text('{"k":1,"ts":"wall-b"}\n{"k":2}\n', encoding="utf-8")
    assert run_s1._ledger_equal(p, q) is True
    r = tmp_path / "c.jsonl"
    r.write_text('{"k":9}\n', encoding="utf-8")
    assert run_s1._ledger_equal(p, r) is False


def test_mut5c_run_s1__tree_equal_1(tmp_path):
    """run_s1.py:1128, cmp_flip `na != nb` -> `na == nb`."""
    a = tmp_path / "ta"
    b = tmp_path / "tb"
    a.mkdir()
    b.mkdir()
    (a / "f.txt").write_text("same", encoding="utf-8")
    (b / "f.txt").write_text("same", encoding="utf-8")
    assert run_s1._tree_equal(a, b) is True
    (b / "g.txt").write_text("extra", encoding="utf-8")
    assert run_s1._tree_equal(a, b) is False


def test_mut5c_run_s1_challenger_apply_1():
    """run_s1.py:603, const_int g[3] -> g[4] in beta_ipca linear form."""
    dates = sessions_us(300)
    aligned = walk(dates, seed=1)
    subj_close = {d: aligned[i] for i, d in enumerate(dates)}
    s = dates[280]
    fill = dates[270]
    coverage = dates[275]
    names = [f"data/yahoo/P{i:03d}.parquet" for i in range(30)]
    ctx = {
        "gamma": [0.1, 0.2, 0.3, 0.4],
        "universe_paths": names,
        "panel_dates": {p: dates for p in names},
        "panel_aligned": {p: walk(dates, seed=i + 2) for i, p in enumerate(names)},
        "spy_close": {d: 100.0 + i for i, d in enumerate(dates)},
    }
    out = run_s1.challenger_apply(ctx, dates, subj_close, s, fill, coverage)
    assert out["state"] == "OK"
    assert isinstance(out["beta_ipca__dc"], float)
    assert isinstance(out["common_ipca__oc"], float)


def test_mut5c_run_s1_evaluate_p03_1(monkeypatch):
    """run_s1.py:511, cmp_flip model == \"M1\" -> model != \"M1\" (challenger attach)."""
    calls: list[str] = []

    class _Win:
        fill_date = date(2020, 1, 3)
        coverage_date = date(2020, 1, 10)

    def _fake_apply(*_a, **_k):
        calls.append("apply")
        return {"state": "FAKE"}

    monkeypatch.setattr(run_s1, "resolve_horizon_window", lambda *_a, **_k: _Win())
    monkeypatch.setattr(run_s1, "last_session_before", lambda *_a, **_k: date(2020, 1, 2))
    def _fake_decomp(model, *_a, **_k):
        return {"model": model, "r__oc": 0.01, "z__oc": 0.0, "abstention": "OK",
                "common__oc": 0.0}

    monkeypatch.setattr(run_s1, "decompose_unit", _fake_decomp)
    monkeypatch.setattr(run_s1, "spec_hash", lambda *_a, **_k: "ab" * 32)
    monkeypatch.setattr(run_s1, "factors_for", lambda *_a, **_k: ())
    monkeypatch.setattr(run_s1, "is_session_fn", lambda _m: (lambda _d: True))
    monkeypatch.setattr(run_s1, "challenger_apply", _fake_apply)

    row = {
        "episode_key": "ek-synth",
        "anchor_session_date": "2020-01-03",
        "coverage_date": "2020-01-10",
        "split": "TRAIN",
    }
    rebuilt = {
        ("P03", c, h): {"rows": [row]}
        for c in ("adr_baba", "hkd_9988", "hkd_0700")
        for h in run_s1.HORIZONS
    }
    d0 = date(2020, 1, 2)
    frames = {
        "BABA": ([d0], {d0: 100.0}, None),
        "9988": ([d0], {d0: 100.0}, None),
        "0700": ([d0], {d0: 100.0}, None),
    }
    out = run_s1.evaluate_p03(None, rebuilt, frames, challenger_ctx={"gamma": [0, 0, 0, 0]})
    baba = out["P03_adr_baba_5"]
    by_model = {r["model"]: r for r in baba}
    assert "challenger" in by_model["M1"]
    assert by_model["M1"]["challenger"]["state"] == "FAKE"
    assert "challenger" not in by_model["M0"]
    assert "challenger" not in by_model["M2"]
    assert calls


def test_mut5c_run_s1_load_frames_1():
    """run_s1.py:468, const_int d[-1] -> d[-2] in max(last_bar, d[-1])."""

    class _Store:
        def frame(self, path, columns):
            # Later series carry a strictly later last bar so last_bar is
            # taken from d[-1] of a series after the first (the mutated 1
            # is the second d[-1] on the line, col 67).
            if path.endswith("3033.HK.parquet"):
                ds = [date(2020, 1, 2), date(2020, 1, 3), date(2020, 1, 6)]
            else:
                ds = [date(2020, 1, 2), date(2020, 1, 3)]
            return ds, {c: [10.0 + i for i in range(len(ds))] for c in columns}

    frames, last_bar = run_s1.load_frames(_Store())
    assert last_bar == date(2020, 1, 6)
    assert set(frames) == {name for name, _p, _c in run_s1.ALL_SERIES}


def test_mut5c_run_s1_log_p03_configs_1():
    """run_s1.py:849, bool_flip `challenger_ctx is not None and not estimable` -> or."""

    class _Ledger:
        def __init__(self):
            self.rows: list[tuple[dict, str | None]] = []

        def log_trial(self, config, *, family=None, info_cutoff=None, source=None, note=None):
            self.rows.append((config, note))

    ledger = _Ledger()
    ctx = {
        "estimability": {
            "estimable": True,
            "admitted_names": 40,
            "characteristics": 3,
            "train_months_with_valid_cross_section": 80,
        }
    }
    run_s1.log_p03_configs(ledger, ctx)
    ipca_notes = [n for cfg, n in ledger.rows if cfg.get("pair") == "ipca_vs_M1"]
    assert ipca_notes
    assert all(n is None for n in ipca_notes)


# ---------------------------------------------------------------------------
# s1_data survivors
# ---------------------------------------------------------------------------


def test_mut5c_s1_data_GitBlobStore__blob_file_1(tmp_path):
    """s1_data.py:93, return cached blob path -> return None."""
    store, _ref, _pins = _blob_store(tmp_path)
    first = store.schema(PX)
    second = store.schema(PX)
    assert first == second == ["Date", "close"]


def test_mut5c_s1_data_GitBlobStore__blob_file_2(tmp_path):
    """s1_data.py:97, arith_swap Path / filename -> Path * filename."""
    store, _ref, _pins = _blob_store(tmp_path)
    names = store.schema(PX)
    assert names == ["Date", "close"]


def test_mut5c_s1_data_GitBlobStore__git_bytes_1(tmp_path):
    """s1_data.py:54, delete `if r.returncode != 0: raise`."""
    store, _ref, _pins = _blob_store(tmp_path)
    with pytest.raises(RuntimeError, match="git .* failed"):
        store._git_bytes(["not-a-git-subcommand-mut5c"])


def test_mut5c_s1_data_GitBlobStore__git_bytes_2(tmp_path):
    """s1_data.py:53, const_bool capture_output True -> False."""
    store, _ref, _pins = _blob_store(tmp_path)
    raw = store._git_bytes(["rev-parse", f"{store.input_ref}:{PX}"])
    assert isinstance(raw, (bytes, bytearray))
    assert raw.strip()


def test_mut5c_s1_data_GitBlobStore__git_bytes_3(tmp_path):
    """s1_data.py:56, return r.stdout -> return None."""
    store, _ref, _pins = _blob_store(tmp_path)
    raw = store._git_bytes(["rev-parse", "--verify", store.input_ref])
    assert isinstance(raw, (bytes, bytearray))
    assert raw.decode().strip() == store.input_ref


def test_mut5c_s1_data_GitBlobStore__git_bytes_4(tmp_path):
    """s1_data.py:54, cmp_flip returncode != 0 -> == 0 (success would raise)."""
    store, _ref, _pins = _blob_store(tmp_path)
    raw = store._git_bytes(["rev-parse", "--verify", store.input_ref])
    assert raw.decode().strip() == store.input_ref


def test_mut5c_s1_data_GitBlobStore__git_text_1(tmp_path):
    """s1_data.py:59, return self._git_bytes(args).decode() -> return None."""
    store, _ref, _pins = _blob_store(tmp_path)
    text = store._git_text(["rev-parse", "--verify", store.input_ref])
    assert text.strip() == store.input_ref


def test_mut5c_s1_data_GitBlobStore_commit_date_iso_1(tmp_path):
    """s1_data.py:73, bool_flip `ref or self.input_ref` -> `and`."""
    store, _ref, _pins = _blob_store(tmp_path)
    iso = store.commit_date_iso()
    assert isinstance(iso, str) and "T" in iso


def test_mut5c_s1_data_GitBlobStore_commit_date_iso_2(tmp_path):
    """s1_data.py:72, return git show %cI -> return None."""
    store, _ref, _pins = _blob_store(tmp_path)
    iso = store.commit_date_iso()
    assert isinstance(iso, str) and iso[0].isdigit()


def test_mut5c_s1_data_GitBlobStore_frame_1(tmp_path):
    """s1_data.py:119, return (dates, cols) -> return None."""
    store, _ref, _pins = _blob_store(tmp_path)
    dates, cols = store.frame(PX, ["close"])
    assert dates == [date(2020, 1, 2), date(2020, 1, 3)]
    assert cols["close"] == [10.0, 11.5]


def test_mut5c_s1_data_GitBlobStore_index_dates_1(tmp_path):
    """s1_data.py:111, return sorted unique index dates -> return None."""
    store, _ref, _pins = _blob_store(tmp_path)
    got = store.index_dates(PX)
    assert got == [date(2020, 1, 2), date(2020, 1, 3)]


def test_mut5c_s1_data_GitBlobStore_list_dir_1(tmp_path):
    """s1_data.py:65, return sorted ls-tree names -> return None."""
    store, _ref, _pins = _blob_store(tmp_path)
    got = store.list_dir("data/yahoo")
    assert isinstance(got, list)
    assert any("yahoo" in p or p.endswith(".parquet") for p in got)


def test_mut5c_s1_data_GitBlobStore_read_columns_1(tmp_path):
    """s1_data.py:126, return column dict -> return None."""
    store, _ref, _pins = _blob_store(tmp_path)
    got = store.read_columns(REF, ["issuer_id", "security_id"])
    assert got["security_id"] == ["SEC:SYN-1"]
    assert got["issuer_id"] == ["ISS:SYN-1"]


def test_mut5c_s1_data_GitBlobStore_rev_parse_ref_path_1(tmp_path):
    """s1_data.py:68, return rev-parse blob id -> return None."""
    store, _ref, pins = _blob_store(tmp_path)
    got = store.rev_parse_ref_path(PX)
    assert got == pins[PX]


def test_mut5c_s1_data_GitBlobStore_schema_1(tmp_path):
    """s1_data.py:105, return schema names -> return None."""
    store, _ref, _pins = _blob_store(tmp_path)
    assert store.schema(PX) == ["Date", "close"]


def test_mut5c_s1_data_GitBlobStore_verify_pin_1(tmp_path):
    """s1_data.py:81, cmp_flip `got != want` -> `got == want` (match would raise)."""
    store, _ref, pins = _blob_store(tmp_path)
    assert store.verify_pin(PX) == pins[PX]


def test_mut5c_s1_data_GitBlobStore_verify_pin_2(tmp_path):
    """s1_data.py:84, return got -> return None."""
    store, _ref, pins = _blob_store(tmp_path)
    assert store.verify_pin(PX) == pins[PX]


def test_mut5c_s1_data_GitBlobStore_verify_pin_3(tmp_path):
    """s1_data.py:81, delete `if got != want: raise` PIN MISMATCH guard."""
    store, ref, pins = _blob_store(tmp_path)
    bad = GitBlobStore(store.repo_root, ref, {PX: "0" * 40}, workdir=tmp_path / "blobs-bad")
    with pytest.raises(RuntimeError, match="PIN MISMATCH"):
        bad.verify_pin(PX)
    assert store.verify_pin(PX) == pins[PX]


def test_mut5c_s1_data_IndexOnlySpy_list_dir_1():
    """s1_data.py:191, return self._store.list_dir(prefix) -> return None."""
    store = InjectableStore({
        "data/yahoo/A.parquet": {"Date": [date(2020, 1, 2)], "close": [1.0]},
        "data/yahoo/B.parquet": {"Date": [date(2020, 1, 2)], "close": [1.0]},
        "other/x.parquet": {"Date": [date(2020, 1, 2)], "close": [1.0]},
    })
    spy = IndexOnlySpy(store)
    got = spy.list_dir("data/yahoo/")
    assert got == ["data/yahoo/A.parquet", "data/yahoo/B.parquet"]
    assert spy.calls == ["list_dir"]


def test_mut5c_s1_data_IndexOnlySpy_schema_1():
    """s1_data.py:183, return self._store.schema(path) -> return None."""
    store = InjectableStore({
        "p": {"Date": [date(2020, 1, 2)], "close": [1.0]},
    })
    spy = IndexOnlySpy(store)
    assert spy.schema("p") == ["Date", "close"]
    assert spy.calls == ["schema"]


def test_mut5c_s1_data_InjectableStore_commit_date_iso_1():
    """s1_data.py:166, return '1970-01-01T00:00:00+00:00' -> return None."""
    store = InjectableStore({})
    assert store.commit_date_iso() == "1970-01-01T00:00:00+00:00"


def test_mut5c_s1_data_InjectableStore_read_columns_1():
    """s1_data.py:162, return column dict -> return None."""
    store = InjectableStore({
        "p": {"Date": [date(2020, 1, 2)], "close": [1.5], "vol": [3.0]},
    })
    got = store.read_columns("p", ["vol", "close"])
    assert got["vol"] == [3.0]
    assert got["close"] == [1.5]


def test_mut5c_s1_data__to_date_1():
    """s1_data.py:32, return v.date() on datetime -> return None."""
    assert _to_date(datetime(2020, 1, 2, 15, 30, 0)) == date(2020, 1, 2)
    assert _to_date(date(2020, 1, 2)) == date(2020, 1, 2)
    with pytest.raises(TypeError):
        _to_date("2020-01-02")
