"""ParquetSpoolSink — disk-backed substrate spool round-trip (P-SCALE-2 lane A)."""
from __future__ import annotations

import dataclasses
import json
import resource
from datetime import date

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from engine.entry_radar import challengers as ch
from engine.entry_radar import live_pack as lp
from engine.entry_radar.pack_spool import (
    ParquetSpoolSink,
    SpoolSubstrate,
    iter_spool,
    load_sidecar,
    read_spool_frame,
    verify_spool,
)
from tests.test_entry_radar_pack_sink import _threshold_cases_without_binding
from tests.test_entry_radar_w4_pack import AS_OF, NEXT_SESSION, build, frame_from_closes, store


def _five_name_pack():
    tickers = sorted(store())[:5]
    return build(tickers=tickers), date.fromisoformat(build(tickers=tickers).next_session)


def _normalize_substrate_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out.index = pd.DatetimeIndex(out.index.values, dtype="datetime64[s]", freq=None)
    out.index.name = None
    return out


def _fill_spool(sink: ParquetSpoolSink, pack: lp.LivePack, next_session: date) -> dict[str, pd.DataFrame]:
    inputs: dict[str, pd.DataFrame] = {}
    for row in pack.names:
        frame = _normalize_substrate_frame(pack.substrate[row.ticker])
        inputs[row.ticker] = frame
        sink.add(row, frame, next_session=next_session)
    return inputs


def test_SP1_round_trip_insertion_order_and_fingerprints(tmp_path):
    pack, next_session = _five_name_pack()
    path = tmp_path / "substrate.parquet"
    sink = ParquetSpoolSink(path)
    inputs = _fill_spool(sink, pack, next_session)
    sub = sink.finish()
    assert isinstance(sub, SpoolSubstrate)
    assert len(sub) == 5
    sidecar = load_sidecar(path)
    assert sidecar["n_names"] == 5
    yielded = list(iter_spool(path))
    assert [t for t, _ in yielded] == [row.ticker for row in pack.names]
    for ticker, frame in yielded:
        pd.testing.assert_frame_equal(frame, inputs[ticker])
        assert lp.substrate_fingerprint(frame) == sidecar["fingerprints"][ticker]


def test_SP2_duplicate_ticker_refused(tmp_path):
    pack, next_session = _five_name_pack()
    path = tmp_path / "s.parquet"
    sink = ParquetSpoolSink(path)
    row = pack.names[0]
    frame = pack.substrate[row.ticker]
    sink.add(row, frame, next_session=next_session)
    with pytest.raises(lp.LivePackError, match="spool_duplicate_ticker:" + row.ticker):
        sink.add(row, frame, next_session=next_session)


def test_SP3_non_frozen_frame_refused(tmp_path):
    pack, next_session = _five_name_pack()
    row = pack.names[0]
    base = pack.substrate[row.ticker]
    path = tmp_path / "s.parquet"
    sink = ParquetSpoolSink(path)
    extra = base.copy()
    extra["extra"] = 1.0
    with pytest.raises(lp.LivePackError, match=f"spool_frame_not_frozen:{row.ticker}"):
        sink.add(row, extra, next_session=next_session)
    sink2 = ParquetSpoolSink(tmp_path / "b.parquet")
    shifted = base.copy()
    shifted.index = shifted.index + pd.Timedelta(hours=1)
    with pytest.raises(lp.LivePackError, match=f"spool_frame_not_frozen:{row.ticker}"):
        sink2.add(row, shifted, next_session=next_session)


def test_SP4_add_after_finish_refused(tmp_path):
    pack, next_session = _five_name_pack()
    path = tmp_path / "s.parquet"
    sink = ParquetSpoolSink(path)
    _fill_spool(sink, pack, next_session)
    sink.finish()
    row = pack.names[0]
    with pytest.raises(lp.LivePackError, match="spool_closed"):
        sink.add(row, pack.substrate[row.ticker], next_session=next_session)


def test_SP5_zero_name_finish_valid_empty(tmp_path):
    path = tmp_path / "empty.parquet"
    sink = ParquetSpoolSink(path)
    sub = sink.finish()
    assert len(sub) == 0
    assert sub == {}
    assert load_sidecar(path)["n_names"] == 0
    assert list(iter_spool(path)) == []
    assert pq.ParquetFile(path).num_row_groups == 0


def test_SP6_read_spool_frame_by_ticker(tmp_path):
    pack, next_session = _five_name_pack()
    path = tmp_path / "s.parquet"
    sink = ParquetSpoolSink(path)
    inputs = _fill_spool(sink, pack, next_session)
    sink.finish()
    ticker = pack.names[0].ticker
    pd.testing.assert_frame_equal(read_spool_frame(path, ticker), inputs[ticker])
    assert read_spool_frame(path, "NO_SUCH_TICKER") is None


def test_SP7_verify_spool_pass_and_tamper_refusals(tmp_path):
    pack, next_session = _five_name_pack()
    path = tmp_path / "s.parquet"
    sink = ParquetSpoolSink(path)
    inputs = _fill_spool(sink, pack, next_session)
    sink.finish()
    expected = {t: lp.substrate_fingerprint(f) for t, f in inputs.items()}
    verify_spool(path, expected)
    sidecar = load_sidecar(path)
    from engine.entry_radar.pack_spool import _PARQUET_SCHEMA, _frame_to_table

    victim = pack.names[0].ticker
    pf = pq.ParquetFile(path)
    bad_path = tmp_path / "tampered.parquet"
    writer = pq.ParquetWriter(bad_path, _PARQUET_SCHEMA)
    for ticker, frame in iter_spool(path):
        if ticker == victim:
            frame = frame.copy()
            frame.iloc[0, frame.columns.get_loc("close")] += 1.0
        writer.write_table(_frame_to_table(ticker, frame))
    writer.close()
    (tmp_path / "tampered.parquet.sidecar.json").write_text(
        (tmp_path / "s.parquet.sidecar.json").read_text(), encoding="utf-8")
    with pytest.raises(lp.LivePackError, match=f"spool_fingerprint_mismatch:{victim}"):
        verify_spool(bad_path, expected)
    extra_path = tmp_path / "extra.parquet"
    writer = pq.ParquetWriter(extra_path, pf.schema_arrow)
    for i in range(pf.num_row_groups):
        ticker = pf.read_row_group(i).column("ticker")[0].as_py()
        writer.write_table(_frame_to_table(ticker, inputs[ticker]))
    writer.write_table(_frame_to_table("ZZEXTRA", inputs[victim].copy()))
    writer.close()
    extra_sidecar = dict(sidecar)
    extra_sidecar["row_groups"] = dict(sidecar["row_groups"])
    extra_sidecar["row_groups"]["ZZEXTRA"] = pf.num_row_groups
    extra_sidecar["n_names"] = sidecar["n_names"] + 1
    (tmp_path / "extra.parquet.sidecar.json").write_text(
        json.dumps(extra_sidecar, sort_keys=True), encoding="utf-8")
    with pytest.raises(lp.LivePackError, match="spool_key_mismatch"):
        verify_spool(extra_path, expected)


def test_SP8_proof_tap_parity_with_parquet_spool(tmp_path):
    path = tmp_path / "spool.parquet"
    tap_mem = lp.ProofTapSink(lp.InMemorySink())
    tap_spool = lp.ProofTapSink(ParquetSpoolSink(path))
    build(sink=tap_mem)
    build(sink=tap_spool)
    assert _threshold_cases_without_binding(tap_mem.threshold_cases()) == \
           _threshold_cases_without_binding(tap_spool.threshold_cases())


def test_SP9_memory_rss_growth_bounded(tmp_path):
    path = tmp_path / "big.parquet"
    sink = ParquetSpoolSink(path)
    template = build(tickers=["WASH"]).names[0]
    rss0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    for i in range(300):
        ticker = f"T{i:04d}"
        frame = frame_from_closes([100.0 + (i % 17) * 0.001 + j * 0.0001 for j in range(400)])
        frozen = lp._frozen_frame(
            frame, ticker=ticker, next_session=NEXT_SESSION,
            price_basis=ch.BASIS_ADJUSTED, vintage="")
        row = dataclasses.replace(template, ticker=ticker)
        sink.add(row, frozen, next_session=NEXT_SESSION)
    sink.finish()
    rss1 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # ru_maxrss is KiB on Linux, bytes on macOS — compare delta with a loose cap.
    unit = 1024 if rss1 < 10_000_000 else 1
    growth_mb = (rss1 - rss0) / unit / (1024 * 1024)
    assert growth_mb < 50.0


def test_SB1_finish_returns_spool_substrate(tmp_path):
    pack, next_session = _five_name_pack()
    path = tmp_path / "s.parquet"
    sink = ParquetSpoolSink(path)
    inputs = _fill_spool(sink, pack, next_session)
    sub = sink.finish()
    assert len(sub) == 5
    assert list(sub) == [row.ticker for row in pack.names]
    for t in sub:
        assert t in sub
    assert "NO_SUCH" not in sub
    assert sub.get("NO_SUCH") is None
    with pytest.raises(KeyError):
        sub["NO_SUCH"]
    for t, frozen in inputs.items():
        pd.testing.assert_frame_equal(sub[t], _normalize_substrate_frame(frozen))
    assert sub.fingerprints == load_sidecar(path)["fingerprints"]


def test_SB2_no_frame_cache(tmp_path, monkeypatch):
    pack, next_session = _five_name_pack()
    path = tmp_path / "s.parquet"
    sink = ParquetSpoolSink(path)
    _fill_spool(sink, pack, next_session)
    sub = sink.finish()
    ticker = pack.names[0].ticker
    reads = 0
    real_read = pq.ParquetFile.read_row_group

    def counting_read(self, i, *args, **kwargs):
        nonlocal reads
        reads += 1
        return real_read(self, i, *args, **kwargs)

    monkeypatch.setattr(pq.ParquetFile, "read_row_group", counting_read)
    sub[ticker]
    sub[ticker]
    assert reads == 2
    a = sub[ticker]
    b = sub[ticker]
    assert a is not b
    assert not any(isinstance(v, pd.DataFrame) for v in vars(sub).values())


def test_SB3_one_parquet_handle(tmp_path, monkeypatch):
    pack, next_session = _five_name_pack()
    path = tmp_path / "s.parquet"
    sink = ParquetSpoolSink(path)
    _fill_spool(sink, pack, next_session)
    sub = sink.finish()
    opens = 0
    real_init = pq.ParquetFile.__init__

    def counting_init(self, *args, **kwargs):
        nonlocal opens
        opens += 1
        return real_init(self, *args, **kwargs)

    monkeypatch.setattr(pq.ParquetFile, "__init__", counting_init)
    tickers = [pack.names[i].ticker for i in (0, 1, 2, 0, 1, 2, 0, 1, 2, 0)]
    for t in tickers:
        sub[t]
    assert opens == 1
    sub.close()
    sub[tickers[0]]
    assert opens == 2
    sub.close()
    sub.close()


def test_SB4_build_pack_with_parquet_spool_sink(tmp_path):
    path = tmp_path / "pack_spool.parquet"
    spool_pack = build(sink=ParquetSpoolSink(path))
    mem_pack = build(sink=lp.InMemorySink())
    assert isinstance(spool_pack.substrate, SpoolSubstrate)
    assert set(spool_pack.substrate) == {r.ticker for r in spool_pack.names}
    assert spool_pack.pack_hash == mem_pack.pack_hash
    assert spool_pack.with_proof({"pass": True}).substrate is spool_pack.substrate


def test_SB5_sidecar_fingerprint_receipt_vs_parquet_truth(tmp_path):
    path = tmp_path / "s.parquet"
    spool_pack = build(sink=ParquetSpoolSink(path))
    lp._refuse_substrate_key_mismatch(spool_pack)
    lp._refuse_substrate_fingerprint_mismatch(spool_pack)
    expected = {r.ticker: r.substrate_fingerprint for r in spool_pack.names}
    verify_spool(path, expected)
    victim = spool_pack.names[0].ticker
    sidecar = load_sidecar(path)
    sidecar = dict(sidecar)
    sidecar["fingerprints"] = dict(sidecar["fingerprints"])
    sidecar["fingerprints"][victim] = "0" * 64
    (tmp_path / "s.parquet.sidecar.json").write_text(
        json.dumps(sidecar, sort_keys=True), encoding="utf-8")
    verify_spool(path, expected)
    sub = SpoolSubstrate(path)
    assert sub.fingerprints[victim] != spool_pack.by_ticker()[victim].substrate_fingerprint
    lp._refuse_substrate_key_mismatch(spool_pack)
    lp._refuse_substrate_fingerprint_mismatch(spool_pack)


def test_SB6_build_inversion_proof_parity(tmp_path):
    path = tmp_path / "s.parquet"
    path2 = tmp_path / "s2.parquet"
    spool_pack = build(sink=ParquetSpoolSink(path))
    mem_pack = build(sink=lp.InMemorySink())
    tap = lp.ProofTapSink(ParquetSpoolSink(path2))
    tap_pack = build(sink=tap)
    proof_spool = lp.build_inversion_proof(spool_pack)
    proof_mem = lp.build_inversion_proof(mem_pack)
    proof_tap = lp.build_inversion_proof(
        tap_pack, threshold_cases=tap.threshold_cases())
    assert proof_spool["pass"] is True
    assert proof_spool["cases_total"] == proof_mem["cases_total"]
    assert proof_spool["by_family"] == proof_mem["by_family"]
    assert proof_spool["cases_total"] == proof_tap["cases_total"]
    assert proof_spool["by_family"] == proof_tap["by_family"]


def test_SB7_memory_build_pack_then_inversion_proof(tmp_path):
    path = tmp_path / "big_pack.parquet"
    frames = {
        f"T{i:04d}": frame_from_closes(
            [100.0 + (i % 17) * 0.001 + j * 0.0001 for j in range(400)])
        for i in range(300)
    }
    rss0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    pack = build(frames=frames, sink=ParquetSpoolSink(path))
    lp.build_inversion_proof(pack)
    rss1 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    unit = 1024 if rss1 < 10_000_000 else 1
    growth_mb = (rss1 - rss0) / unit / (1024 * 1024)
    assert growth_mb < 50.0


def test_SB8_zero_name_spool_substrate(tmp_path):
    path = tmp_path / "empty.parquet"
    sink = ParquetSpoolSink(path)
    sub = sink.finish()
    assert isinstance(sub, SpoolSubstrate)
    assert len(sub) == 0
    assert sub == {}
    assert list(iter_spool(path)) == []
    assert list(sub) == []
