"""Tests for engine.entry_radar.pack_state compact evaluator state file."""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import math
import os
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from engine.entry_radar import indicator_core as ic
from engine.entry_radar import pack_state as ps


def _frame(n: int, seed: int, *, miss: float = 0.0, last_nan: bool = False) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    closes = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, n)))
    if miss > 0:
        closes[rng.random(n) < miss] = np.nan
        closes[-1] = 101.0
    if last_nan:
        closes[-1] = np.nan
    return pd.DataFrame(
        {"close": closes},
        index=pd.bdate_range("2024-01-02", periods=n),
    )


def _floats(state: ic.StochRsiAppendState | ic.RsiMacdHistAppendState | None) -> list[float]:
    if state is None:
        return []
    if isinstance(state, ic.StochRsiAppendState):
        out: list[float] = [state.last_close, state.up_prev, state.dn_prev]
        out.extend(state.rsi_tail)
        out.extend(state.rawk_tail)
        out.extend(state.k_tail)
        return out
    return [state.fast, state.base, state.sig]


def _same(
    a: ic.StochRsiAppendState | ic.RsiMacdHistAppendState | None,
    b: ic.StochRsiAppendState | ic.RsiMacdHistAppendState | None,
) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    fa, fb = _floats(a), _floats(b)
    if len(fa) != len(fb):
        return False
    for x, y in zip(fa, fb):
        if x == y or (math.isnan(x) and math.isnan(y)):
            continue
        return False
    return True


def _tail_equal(a: tuple[float, ...], b: np.ndarray) -> bool:
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if x == y or (math.isnan(x) and math.isnan(y)):
            continue
        return False
    return True


FRAMES = {
    "A": _frame(400, 1),
    "B": _frame(400, 2, miss=0.05),
    "C": _frame(20, 3),
    "D": _frame(400, 4, last_nan=True),
    "F": _frame(50, 6),
}


@pytest.mark.parametrize("name,frame", list(FRAMES.items()))
def test_t1_compact_row_matches_indicator_core(name: str, frame: pd.DataFrame) -> None:
    closes = ps.confirmed_closes(frame)
    row = ps.compact_state_row(name, frame, price_basis="adjusted")
    expected_kd = ic.stoch_rsi_append_state(closes)
    assert _same(row.kd_state, expected_kd)
    if expected_kd is not None:
        expected_hist = ic.rsi_macd_hist_append_state(closes)
        assert _same(row.hist_state, expected_hist)
    else:
        assert row.hist_state is None


def test_t2_state_presence() -> None:
    rows = {n: ps.compact_state_row(n, f, price_basis="adjusted") for n, f in FRAMES.items()}
    assert rows["A"].kd_state is not None and rows["A"].hist_state is not None
    assert rows["B"].kd_state is not None and rows["B"].hist_state is not None
    assert rows["C"].kd_state is None and rows["C"].hist_state is None
    assert rows["D"].kd_state is None and rows["D"].hist_state is None
    assert rows["F"].kd_state is not None and rows["F"].hist_state is None


@pytest.mark.parametrize("name,frame", list(FRAMES.items()))
def test_t3_metadata(name: str, frame: pd.DataFrame) -> None:
    row = ps.compact_state_row(name, frame, price_basis="adjusted")
    assert row.state_through == frame.index[-1].date()
    assert row.n_rows == len(frame)
    assert row.price_basis == "adjusted"


def test_t4_tail_close() -> None:
    row_a = ps.compact_state_row("A", FRAMES["A"], price_basis="adjusted")
    closes_a = ps.confirmed_closes(FRAMES["A"]).to_numpy()
    assert len(row_a.tail_close) == 252
    assert _tail_equal(row_a.tail_close, closes_a[-252:])

    row_f = ps.compact_state_row("F", FRAMES["F"], price_basis="adjusted")
    closes_f = ps.confirmed_closes(FRAMES["F"]).to_numpy()
    assert len(row_f.tail_close) == len(closes_f)
    assert _tail_equal(row_f.tail_close, closes_f)

    row_c = ps.compact_state_row("C", FRAMES["C"], price_basis="adjusted")
    closes_c = ps.confirmed_closes(FRAMES["C"]).to_numpy()
    assert len(row_c.tail_close) == len(closes_c)
    assert _tail_equal(row_c.tail_close, closes_c)

    n600 = 600
    closes600 = np.empty(n600, dtype=np.float64)
    closes600[:200] = 100.0
    closes600[200:540] = np.nan
    closes600[540:] = 102.0
    frame600 = pd.DataFrame({"close": closes600}, index=pd.bdate_range("2020-01-02", periods=n600))
    row600 = ps.compact_state_row("W", frame600, price_basis="adjusted")
    assert len(row600.tail_close) == 461
    assert sum(np.isfinite(np.asarray(row600.tail_close))) == 121
    assert _tail_equal(row600.tail_close, closes600[-461:])

    n300 = 300
    closes300 = np.full(n300, np.nan, dtype=np.float64)
    closes300[-40:] = 99.0
    frame300 = pd.DataFrame({"close": closes300}, index=pd.bdate_range("2021-01-04", periods=n300))
    row300 = ps.compact_state_row("Y", frame300, price_basis="adjusted")
    assert len(row300.tail_close) == 300
    assert _tail_equal(row300.tail_close, closes300)


def test_t5_write_load_roundtrip(tmp_path: Path) -> None:
    rows = [ps.compact_state_row(n, f, price_basis="adjusted") for n, f in FRAMES.items()]
    path = tmp_path / "compact.parquet"
    info = ps.write_compact(path, reversed(rows))
    data = path.read_bytes()
    assert info["sha256"] == hashlib.sha256(data).hexdigest()
    assert info["bytes"] == len(data)
    assert info["rows"] == 5
    assert info["schema"] == ps.SCHEMA_COMPACT

    path2 = tmp_path / "compact2.parquet"
    ps.write_compact(path2, rows)
    assert path2.read_bytes() == data

    loaded = ps.load_compact(path, expected_sha256=info["sha256"])
    assert list(loaded.keys()) == sorted(loaded.keys())
    by_ticker = {r.ticker: r for r in rows}
    for ticker, lrow in loaded.items():
        wrow = by_ticker[ticker]
        assert _same(lrow.kd_state, wrow.kd_state)
        assert _same(lrow.hist_state, wrow.hist_state)
        assert _tail_equal(lrow.tail_close, np.asarray(wrow.tail_close))
        assert lrow.state_through == wrow.state_through
        assert lrow.n_rows == wrow.n_rows
        assert lrow.price_basis == wrow.price_basis

    assert list(tmp_path.glob("*.tmp")) == []


def test_t6_appended_values_match(tmp_path: Path) -> None:
    rows = [ps.compact_state_row(n, f, price_basis="adjusted") for n, f in FRAMES.items()]
    path = tmp_path / "compact.parquet"
    info = ps.write_compact(path, rows)
    loaded_map = ps.load_compact(path, expected_sha256=info["sha256"])
    by_ticker = {r.ticker: r for r in rows}
    prices = (95.0, 100.0, 107.3)
    for ticker, lrow in loaded_map.items():
        row = by_ticker[ticker]
        if row.kd_state is not None:
            for p in prices:
                assert ic.stoch_rsi_kd_appended(lrow.kd_state, p) == ic.stoch_rsi_kd_appended(
                    row.kd_state, p
                )
        if row.hist_state is not None:
            for p in prices:
                assert ic.rsi_macd_hist_appended(
                    lrow.kd_state, lrow.hist_state, p
                ) == ic.rsi_macd_hist_appended(row.kd_state, row.hist_state, p)


def test_t7_load_refusals(tmp_path: Path) -> None:
    missing = tmp_path / "nope.parquet"
    with pytest.raises(ps.CompactStateError) as excinfo:
        ps.load_compact(missing, expected_sha256="0" * 64)
    assert excinfo.value.reason == "compact_absent"

    junk = tmp_path / "junk.parquet"
    junk.write_bytes(b"junk")
    junk_hash = hashlib.sha256(b"junk").hexdigest()
    with pytest.raises(ps.CompactStateError) as excinfo:
        ps.load_compact(junk, expected_sha256="0" * 64)
    assert excinfo.value.reason == "compact_hash_mismatch"

    with pytest.raises(ps.CompactStateError) as excinfo:
        ps.load_compact(junk, expected_sha256=None)  # type: ignore[arg-type]
    assert excinfo.value.reason == "compact_hash_mismatch"

    with pytest.raises(ps.CompactStateError) as excinfo:
        ps.load_compact(junk, expected_sha256=junk_hash)
    assert excinfo.value.reason == "compact_schema"


def _rewrite(path: Path, table: pa.Table) -> str:
    pq.write_table(table, path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_t8_load_schema_refusals(tmp_path: Path) -> None:
    rows = [ps.compact_state_row(n, f, price_basis="adjusted") for n, f in FRAMES.items()]
    good_path = tmp_path / "good.parquet"
    good_info = ps.write_compact(good_path, rows)
    table = pq.read_table(good_path)
    pyrows = table.to_pylist()

    def load_broken(mutated: pa.Table) -> None:
        bad = tmp_path / "bad.parquet"
        h = _rewrite(bad, mutated)
        with pytest.raises(ps.CompactStateError) as excinfo:
            ps.load_compact(bad, expected_sha256=h)
        assert excinfo.value.reason == "compact_schema"

    load_broken(table.drop_columns(["hist_sig"]))

    meta = dict(table.schema.metadata or {})
    meta[b"schema"] = b"other"
    load_broken(table.replace_schema_metadata(meta))

    r = dict(pyrows[0])
    r["kd_ok"] = True
    r["kd_up_prev"] = None
    load_broken(pa.Table.from_pylist([r] + pyrows[1:], schema=ps.COMPACT_SCHEMA))

    # C carries neither state, so each case below breaks exactly one rule.
    bare = next(r for r in pyrows if r["ticker"] == "C")
    assert bare["kd_ok"] is False and bare["hist_ok"] is False
    rest = [r for r in pyrows if r["ticker"] != "C"]

    r2 = dict(bare)
    r2["kd_last_close"] = 1.0
    load_broken(pa.Table.from_pylist([r2] + rest, schema=ps.COMPACT_SCHEMA))

    r3 = dict(bare)
    r3["hist_ok"] = True
    r3["hist_fast"] = 1.0
    r3["hist_base"] = 1.0
    r3["hist_sig"] = 1.0
    load_broken(pa.Table.from_pylist([r3] + rest, schema=ps.COMPACT_SCHEMA))

    load_broken(pa.Table.from_pylist(pyrows + [pyrows[0]], schema=ps.COMPACT_SCHEMA))

    r4 = dict(pyrows[0])
    r4["kd_rsi_tail"] = r4["kd_rsi_tail"][1:]
    load_broken(pa.Table.from_pylist([r4] + pyrows[1:], schema=ps.COMPACT_SCHEMA))

    r5 = next(r for r in pyrows if r["ticker"] == "A")
    r5b = dict(r5)
    r5b["tail_close"] = r5["tail_close"][-10:]
    others = [r for r in pyrows if r["ticker"] != "A"]
    load_broken(pa.Table.from_pylist([r5b] + others, schema=ps.COMPACT_SCHEMA))

    r6 = dict(pyrows[0])
    r6["hist_ok"] = False
    r6["hist_fast"] = 1.0
    load_broken(pa.Table.from_pylist([r6] + pyrows[1:], schema=ps.COMPACT_SCHEMA))

    _ = good_info


def test_t9_write_refusals(tmp_path: Path) -> None:
    row_a = ps.compact_state_row("A", FRAMES["A"], price_basis="adjusted")
    row_b = ps.compact_state_row("B", FRAMES["B"], price_basis="adjusted")
    target = tmp_path / "out.parquet"

    with pytest.raises(ps.CompactStateError) as excinfo:
        ps.write_compact(target, [row_a, row_a])
    assert excinfo.value.reason == "compact_duplicate_ticker"
    assert not target.exists()
    assert list(tmp_path.glob("*.tmp")) == []

    bad_hist = dataclasses.replace(row_a, kd_state=None, hist_state=row_a.hist_state)
    with pytest.raises(ps.CompactStateError) as excinfo:
        ps.write_compact(target, [bad_hist])
    assert excinfo.value.reason == "compact_schema"
    assert not target.exists()
    assert list(tmp_path.glob("*.tmp")) == []

    bad_tail = dataclasses.replace(row_a, tail_close=row_a.tail_close[:10])
    with pytest.raises(ps.CompactStateError) as excinfo:
        ps.write_compact(target, [bad_tail])
    assert excinfo.value.reason == "compact_schema"
    assert not target.exists()
    assert list(tmp_path.glob("*.tmp")) == []


def test_t10_compact_state_sink() -> None:
    sink = ps.CompactStateSink()
    sink.add("B", FRAMES["B"], price_basis="adjusted")
    sink.add("A", FRAMES["A"], price_basis="adjusted")
    got = sink.rows()
    assert [r.ticker for r in got] == ["A", "B"]

    sink2 = ps.CompactStateSink()
    sink2.add("A", FRAMES["A"], price_basis="adjusted")
    with pytest.raises(ps.CompactStateError) as excinfo:
        sink2.add("A", FRAMES["A"], price_basis="adjusted")
    assert excinfo.value.reason == "compact_duplicate_ticker"

    with pytest.raises(ps.CompactStateError) as excinfo:
        ps.compact_state_row("X", FRAMES["A"].iloc[:0], price_basis="adjusted")
    assert excinfo.value.reason == "compact_empty_frame"

    # A frame without closes is a refusal of this module, not a bare KeyError.
    with pytest.raises(ps.CompactStateError) as excinfo:
        ps.compact_state_row("X", FRAMES["A"].drop(columns=["close"]), price_basis="adjusted")
    assert excinfo.value.reason == "compact_schema"


def test_t11_no_live_pack_import() -> None:
    source = Path(ps.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(ps.__file__))

    def names_live_pack(dotted: str | None) -> bool:
        return bool(dotted) and dotted.split(".")[-1] == "live_pack"

    imports = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports += 1
            for alias in node.names:
                assert not names_live_pack(alias.name), alias.name
        elif isinstance(node, ast.ImportFrom):
            imports += 1
            assert not names_live_pack(node.module), node.module
            for alias in node.names:
                assert alias.name != "live_pack"
    assert imports > 0


@pytest.mark.parametrize("line", [
    "import live_pack",
    "import engine.entry_radar.live_pack",
    "import engine.entry_radar.live_pack as lp",
    "from engine.entry_radar import live_pack",
    "from engine.entry_radar.live_pack import LivePack",
    "from . import live_pack",
    "from .live_pack import LivePack",
])
def test_t11b_the_import_check_sees_every_import_form(line: str) -> None:
    """The check above must reject each way of importing the pack builder."""
    def names_live_pack(dotted: str | None) -> bool:
        return bool(dotted) and dotted.split(".")[-1] == "live_pack"

    hit = False
    for node in ast.walk(ast.parse(line)):
        if isinstance(node, ast.Import):
            hit |= any(names_live_pack(alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            hit |= names_live_pack(node.module) or any(
                alias.name == "live_pack" for alias in node.names)
    assert hit


def _full_compact_metadata(**overrides: bytes) -> dict[bytes, bytes]:
    meta = {
        b"schema": ps.SCHEMA_COMPACT.encode(),
        b"tail_close_purpose": ps.TAIL_CLOSE_PURPOSE.encode(),
        b"canonical_fallback": ps.CANONICAL_FALLBACK.encode(),
    }
    meta.update(overrides)
    return meta


def _good_table_rows() -> tuple[pa.Table, list[dict]]:
    rows = [ps.compact_state_row(n, f, price_basis="adjusted") for n, f in FRAMES.items()]
    # Mirror write_compact column layout.
    ordered = sorted(rows, key=lambda r: r.ticker)
    columns: dict[str, list] = {field.name: [] for field in ps.COMPACT_SCHEMA}
    for row in ordered:
        kd, hist = row.kd_state, row.hist_state
        columns["ticker"].append(row.ticker)
        columns["state_through"].append(row.state_through)
        columns["n_rows"].append(row.n_rows)
        columns["price_basis"].append(row.price_basis)
        columns["kd_ok"].append(kd is not None)
        columns["kd_last_close"].append(None if kd is None else kd.last_close)
        columns["kd_up_prev"].append(None if kd is None else kd.up_prev)
        columns["kd_dn_prev"].append(None if kd is None else kd.dn_prev)
        columns["kd_rsi_tail"].append(None if kd is None else list(kd.rsi_tail))
        columns["kd_rawk_tail"].append(None if kd is None else list(kd.rawk_tail))
        columns["kd_k_tail"].append(None if kd is None else list(kd.k_tail))
        columns["hist_ok"].append(hist is not None)
        columns["hist_fast"].append(None if hist is None else hist.fast)
        columns["hist_base"].append(None if hist is None else hist.base)
        columns["hist_sig"].append(None if hist is None else hist.sig)
        columns["tail_close"].append(list(row.tail_close))
    arrays = [pa.array(columns[field.name], type=field.type) for field in ps.COMPACT_SCHEMA]
    table = pa.Table.from_arrays(arrays, schema=ps.COMPACT_SCHEMA)
    return table, table.to_pylist()


def _assert_load_schema_refusal(tmp_path: Path, table: pa.Table) -> None:
    bad = tmp_path / "bad.parquet"
    digest = _rewrite(bad, table)
    with pytest.raises(ps.CompactStateError) as excinfo:
        ps.load_compact(bad, expected_sha256=digest)
    assert excinfo.value.reason == "compact_schema"


def test_t5a_load_refusals_pin_guards(tmp_path: Path) -> None:
    table, pyrows = _good_table_rows()
    a_row = next(r for r in pyrows if r["ticker"] == "A")

    r1 = dict(a_row)
    r1["hist_ok"] = True
    r1["hist_fast"] = None
    _assert_load_schema_refusal(tmp_path, pa.Table.from_pylist([r1], schema=ps.COMPACT_SCHEMA))

    r2 = dict(a_row)
    r2["kd_ok"] = True
    tail = list(r2["kd_rsi_tail"])
    tail[0] = None
    r2["kd_rsi_tail"] = tail
    _assert_load_schema_refusal(tmp_path, pa.Table.from_pylist([r2], schema=ps.COMPACT_SCHEMA))

    r3 = dict(a_row)
    tc = list(r3["tail_close"])
    tc[-1] = None
    r3["tail_close"] = tc
    _assert_load_schema_refusal(tmp_path, pa.Table.from_pylist([r3], schema=ps.COMPACT_SCHEMA))


def test_t5b_layout_refusals(tmp_path: Path) -> None:
    table, pyrows = _good_table_rows()
    a_row = next(r for r in pyrows if r["ticker"] == "A")

    r4 = dict(a_row)
    r4["n_rows"] = 0
    _assert_load_schema_refusal(tmp_path, pa.Table.from_pylist([r4], schema=ps.COMPACT_SCHEMA))

    r5 = dict(a_row)
    r5["n_rows"] = 10
    r5["tail_close"] = list(r5["tail_close"]) + [1.0, 2.0]
    _assert_load_schema_refusal(tmp_path, pa.Table.from_pylist([r5], schema=ps.COMPACT_SCHEMA))

    reversed_rows = list(reversed(pyrows))
    _assert_load_schema_refusal(
        tmp_path, pa.Table.from_pylist(reversed_rows, schema=ps.COMPACT_SCHEMA))

    meta = _full_compact_metadata()
    del meta[b"tail_close_purpose"]
    _assert_load_schema_refusal(
        tmp_path, table.replace_schema_metadata(meta))

    bad_purpose = _full_compact_metadata()
    bad_purpose[b"tail_close_purpose"] = b"canonical_recompute"
    _assert_load_schema_refusal(
        tmp_path, table.replace_schema_metadata(bad_purpose))


def test_t5c_index_law() -> None:
    frame = FRAMES["A"]
    closes = frame["close"].to_numpy()
    range_frame = pd.DataFrame({"close": closes})
    with pytest.raises(ps.CompactStateError) as excinfo:
        ps.compact_state_row("X", range_frame, price_basis="adjusted")
    assert excinfo.value.reason == "compact_schema"

    rev_index = frame.iloc[::-1].copy()
    with pytest.raises(ps.CompactStateError) as excinfo:
        ps.compact_state_row("X", rev_index, price_basis="adjusted")
    assert excinfo.value.reason == "compact_schema"

    dup = frame.copy()
    dup_idx = list(dup.index)
    dup_idx[-1] = dup_idx[-2]
    dup.index = pd.DatetimeIndex(dup_idx)
    with pytest.raises(ps.CompactStateError) as excinfo:
        ps.compact_state_row("X", dup, price_basis="adjusted")
    assert excinfo.value.reason == "compact_schema"

    ps.compact_state_row("X", frame, price_basis="adjusted")


def test_t5d_write_atomic_on_pq_failure(tmp_path: Path) -> None:
    rows = [ps.compact_state_row(n, f, price_basis="adjusted") for n, f in FRAMES.items()]
    path = tmp_path / "compact.parquet"
    before = ps.write_compact(path, rows)
    old_bytes = path.read_bytes()

    def boom(table: pa.Table, where: str | Path, **kwargs: object) -> None:
        Path(where).write_bytes(b"partial")
        raise RuntimeError("pq write failed")

    with mock.patch.object(pq, "write_table", side_effect=boom):
        with pytest.raises(RuntimeError):
            ps.write_compact(path, rows)
    assert path.read_bytes() == old_bytes
    assert list(tmp_path.glob("*.tmp")) == []


def test_t5e_write_atomic_on_replace_failure(tmp_path: Path) -> None:
    rows = [ps.compact_state_row(n, f, price_basis="adjusted") for n, f in FRAMES.items()]
    path = tmp_path / "compact.parquet"
    before = ps.write_compact(path, rows)
    old_bytes = path.read_bytes()

    with mock.patch.object(os, "replace", side_effect=OSError("replace failed")):
        with pytest.raises(OSError):
            ps.write_compact(path, rows)
    assert path.read_bytes() == old_bytes
    assert list(tmp_path.glob("*.tmp")) == []


def test_t5f_fsync_before_replace(tmp_path: Path) -> None:
    rows = [ps.compact_state_row("A", FRAMES["A"], price_basis="adjusted")]
    path = tmp_path / "compact.parquet"
    calls: list[str] = []

    real_fsync = os.fsync
    real_replace = os.replace

    def track_fsync(fd: int) -> None:
        calls.append("fsync")
        real_fsync(fd)

    def track_replace(src: str | bytes, dst: str | bytes) -> None:
        calls.append("replace")
        real_replace(src, dst)

    with mock.patch.object(os, "fsync", side_effect=track_fsync):
        with mock.patch.object(os, "replace", side_effect=track_replace):
            ps.write_compact(path, rows)
    assert calls == ["fsync", "replace"]


def test_t5g_write_overwrite(tmp_path: Path) -> None:
    row_a = ps.compact_state_row("A", FRAMES["A"], price_basis="adjusted")
    row_b = ps.compact_state_row("B", FRAMES["B"], price_basis="adjusted")
    path = tmp_path / "compact.parquet"
    ps.write_compact(path, [row_a])
    info2 = ps.write_compact(path, [row_a, row_b])
    loaded = ps.load_compact(path, expected_sha256=info2["sha256"])
    assert set(loaded) == {"A", "B"}


def test_t5h_hash_guard_without_isinstance(tmp_path: Path) -> None:
    rows = [ps.compact_state_row("A", FRAMES["A"], price_basis="adjusted")]
    path = tmp_path / "compact.parquet"
    info = ps.write_compact(path, rows)
    good = info["sha256"]

    with pytest.raises(ps.CompactStateError) as excinfo:
        ps.load_compact(path, expected_sha256=None)  # type: ignore[arg-type]
    assert excinfo.value.reason == "compact_hash_mismatch"

    with pytest.raises(ps.CompactStateError) as excinfo:
        ps.load_compact(path, expected_sha256=0)  # type: ignore[arg-type]
    assert excinfo.value.reason == "compact_hash_mismatch"

    with pytest.raises(ps.CompactStateError) as excinfo:
        ps.load_compact(path, expected_sha256=good.upper())
    assert excinfo.value.reason == "compact_hash_mismatch"
