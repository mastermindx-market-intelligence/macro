"""Entry Radar pack builder substrate sink — streaming hand-off and proof tap."""
from __future__ import annotations

import types
from datetime import date, datetime, timezone

import pandas as pd
import pytest

from engine.entry_radar import live_pack as lp
from tests.test_entry_radar_w4_pack import AS_OF, build, frame_from_closes, store


def test_T1_in_memory_sink_matches_default_build():
    default = build()
    with_sink = build(sink=lp.InMemorySink())
    assert default.pack_hash == with_sink.pack_hash
    assert default.names == with_sink.names
    for ticker in sorted(default.substrate):
        pd.testing.assert_frame_equal(
            default.substrate[ticker], with_sink.substrate[ticker])
    assert lp.build_inversion_proof(default) == lp.build_inversion_proof(with_sink)


def _threshold_cases_without_binding(cases):
    return [{k: v for k, v in case.items() if k != "substrate_fingerprint"}
            for case in cases]


def test_T2_proof_tap_collects_threshold_cases():
    tap = lp.ProofTapSink(lp.InMemorySink())
    pack = build(sink=tap)
    default = build()
    assert _threshold_cases_without_binding(tap.threshold_cases()) == \
           lp._proof_threshold_cases(default)
    assert tap.threshold_cases()
    assert lp.build_inversion_proof(
        pack, threshold_cases=tap.threshold_cases()) == lp.build_inversion_proof(default)
    # The tap forwards every frame: the wrapped sink still holds the whole substrate.
    assert sorted(pack.substrate) == sorted(default.substrate)
    assert pack.substrate
    for ticker in default.substrate:
        pd.testing.assert_frame_equal(pack.substrate[ticker], default.substrate[ticker])


class _RecordingSink:
    def __init__(self) -> None:
        self._frames: dict[str, pd.DataFrame] = {}
        self.add_calls: list[tuple[str, date]] = []
        self.events: list[str] = []

    def add(self, row: lp.PackName, frozen: pd.DataFrame, *, next_session: date) -> None:
        self.events.append("add")
        self.add_calls.append((row.ticker, next_session))
        self._frames[row.ticker] = frozen

    def finish(self) -> dict[str, pd.DataFrame]:
        self.events.append("finish")
        return self._frames


class _EmptyFinishSink:
    def add(self, row: lp.PackName, frozen: pd.DataFrame, *, next_session: date) -> None:
        pass

    def finish(self) -> types.MappingProxyType:
        return types.MappingProxyType({})


def test_T3_recording_sink_sees_admitted_names_in_order():
    rec = _RecordingSink()
    tickers = sorted(store()) + ["NOPE"]
    pack = build(sink=rec, tickers=tickers)
    admitted = sorted(n.ticker for n in pack.names)
    assert [t for t, _ in rec.add_calls] == admitted
    expected_session = date.fromisoformat(pack.next_session)
    assert all(ns == expected_session for _, ns in rec.add_calls)
    assert rec.events.count("finish") == 1
    assert rec.events[-1] == "finish"
    assert "NOPE" not in {t for t, _ in rec.add_calls}
    assert any(m.get("ticker") == "NOPE" for m in pack.substrate_missing)


def test_T4_streamed_pack_is_refused_without_its_tapped_cases(tmp_path):
    tap = lp.ProofTapSink(_EmptyFinishSink())
    pack = build(sink=tap)
    default = build()
    assert pack.pack_hash == default.pack_hash
    assert pack.names == default.names
    assert len(pack.substrate) == 0
    tapped = lp.build_inversion_proof(pack, threshold_cases=tap.threshold_cases())
    assert tapped == lp.build_inversion_proof(default)
    assert tapped["by_family"]["threshold_boundary"]["total"] > 0
    # No frames and no tapped cases: the proof must refuse, not pass without the family.
    with pytest.raises(lp.LivePackError, match="lacks"):
        lp.build_inversion_proof(pack)
    # The in-memory saver must refuse a pack whose frames were streamed elsewhere.
    with pytest.raises(lp.LivePackError, match="cannot save"):
        lp.save_pack(pack.with_proof(tapped), tmp_path)
    assert lp.current_pack_identity(tmp_path) is None
    assert not list(tmp_path.rglob("*.parquet"))
    assert not list(tmp_path.rglob("manifest*.json"))


def test_T4b_pack_missing_one_frame_is_refused(tmp_path):
    default = build()
    frames = dict(default.substrate)
    dropped = sorted(frames)[0]
    del frames[dropped]
    import dataclasses
    partial = dataclasses.replace(default, substrate=frames)
    with pytest.raises(lp.LivePackError, match=dropped):
        lp.save_pack(partial, tmp_path)
    assert lp.current_pack_identity(tmp_path) is None


def test_T5_supplied_cases_must_be_exactly_this_packs():
    default = build()
    default_proof = lp.build_inversion_proof(default)
    assert default_proof["by_family"]["threshold_boundary"]["total"] > 0
    tap = lp.ProofTapSink(lp.InMemorySink())
    pack = build(sink=tap)
    cases = tap.threshold_cases()
    assert [c["case"] for c in cases] == [
        name for row in pack.names for name in lp.threshold_case_names(row)]
    # An empty list for a pack that has solved levels would drop the family.
    with pytest.raises(lp.LivePackError, match="not this pack's"):
        lp.build_inversion_proof(pack, threshold_cases=[])
    with pytest.raises(lp.LivePackError, match="not this pack's"):
        lp.build_inversion_proof(pack, threshold_cases=cases[:-1])
    with pytest.raises(lp.LivePackError, match="not this pack's"):
        lp.build_inversion_proof(pack, threshold_cases=cases + cases)
    foreign = [dict(cases[0], case="ZZZZ:" + cases[0]["case"].split(":", 1)[1])] + cases[1:]
    with pytest.raises(lp.LivePackError, match="not this pack's"):
        lp.build_inversion_proof(pack, threshold_cases=foreign)
    wrong_family = [dict(cases[0], family="micro_path")] + cases[1:]
    with pytest.raises(lp.LivePackError, match="not this pack's"):
        lp.build_inversion_proof(pack, threshold_cases=wrong_family)
    assert lp.build_inversion_proof(pack, threshold_cases=cases) == default_proof
    # A pack that admitted no name has no threshold cases; an empty list is its own.
    nameless = build(tickers=["NOPE"])
    assert nameless.names == ()
    empty = lp.build_inversion_proof(nameless, threshold_cases=[])
    assert empty == lp.build_inversion_proof(nameless)
    assert "threshold_boundary" not in empty["by_family"]


def test_T5b_sinks_serve_one_build():
    for make in (lp.InMemorySink, lambda: lp.ProofTapSink(lp.InMemorySink())):
        sink = make()
        build(sink=sink)
        with pytest.raises(lp.LivePackError, match="reused"):
            build(sink=sink)
        with pytest.raises(lp.LivePackError, match="reused"):
            sink.finish()


class _RefusingSink:
    def add(self, row: lp.PackName, frozen: pd.DataFrame, *, next_session: date) -> None:
        if lp.threshold_case_names(row):
            raise RuntimeError("inner sink refused the frame")

    def finish(self) -> dict[str, pd.DataFrame]:
        return {}


def test_T5c_tap_keeps_no_case_for_a_frame_the_inner_sink_refused():
    tap = lp.ProofTapSink(_RefusingSink())
    with pytest.raises(RuntimeError, match="inner sink refused"):
        build(sink=tap)
    refused = next(
        row for row in build().names if lp.threshold_case_names(row))
    assert lp.threshold_case_names(refused)
    assert not any(
        c["case"].startswith(f"{refused.ticker}:") for c in tap.threshold_cases())


class _CustomPostSink:
    def __init__(self, post) -> None:
        self._frames: dict[str, pd.DataFrame] = {}
        self._post = post

    def add(self, row: lp.PackName, frozen: pd.DataFrame, *, next_session: date) -> None:
        self._frames[row.ticker] = frozen

    def finish(self) -> dict[str, pd.DataFrame]:
        return dict(self._post(self._frames))


def _build_with_post_sink(post):
    tap = lp.ProofTapSink(_CustomPostSink(post))
    return lp.build_pack(
        probe_set=sorted(store()),
        store_reader=lambda t: store().get(t),
        as_of=AS_OF,
        built_at=datetime(2026, 8, 15, 2, 0, tzinfo=timezone.utc),
        sink=tap), tap


def test_T4a_swapped_substrate_keys_refuse_save_and_proof(tmp_path):
    def swap(frames):
        out = dict(frames)
        out["STALE"], out["WASH"] = frames["WASH"], frames["STALE"]
        return out

    pack, _tap = _build_with_post_sink(swap)
    with pytest.raises(lp.LivePackError, match="substrate_fingerprint_mismatch"):
        lp.save_pack(pack, tmp_path)
    assert not lp.pack_root(tmp_path).exists()
    with pytest.raises(lp.LivePackError, match="substrate_fingerprint_mismatch"):
        lp.build_inversion_proof(pack)


def test_T4b_replaced_substrate_frame_refuse_save_and_proof(tmp_path):
    def tamper(frames):
        out = dict(frames)
        frame = frames["WASH"].copy()
        frame.iloc[0, frame.columns.get_loc("close")] *= 1.37
        out["WASH"] = frame
        return out

    pack, _tap = _build_with_post_sink(tamper)
    with pytest.raises(lp.LivePackError, match="substrate_fingerprint_mismatch"):
        lp.save_pack(pack, tmp_path)
    assert not lp.pack_root(tmp_path).exists()
    with pytest.raises(lp.LivePackError, match="substrate_fingerprint_mismatch"):
        lp.build_inversion_proof(pack)


def test_T4c_extra_substrate_key_refuse_save_and_proof(tmp_path):
    def extra(frames):
        return {**frames, "ZZZ": frames["FLAT"]}

    pack, _tap = _build_with_post_sink(extra)
    with pytest.raises(lp.LivePackError, match="substrate_key_mismatch"):
        lp.save_pack(pack, tmp_path)
    assert not lp.pack_root(tmp_path).exists()
    with pytest.raises(lp.LivePackError, match="substrate_key_mismatch"):
        lp.build_inversion_proof(pack)


def test_T4g_load_pack_refuses_tampered_substrate_parquet(tmp_path):
    pack = build()
    proof = lp.build_inversion_proof(pack)
    lp.save_pack(pack.with_proof(proof), tmp_path)
    parquet_path = lp.pack_root(tmp_path) / pack.as_of / "substrate.parquet"
    flat = pd.read_parquet(parquet_path)
    ticker = pack.names[0].ticker
    mask = flat["ticker"] == ticker
    flat.loc[mask, "close"] = flat.loc[mask, "close"] * 1.01
    flat.to_parquet(parquet_path, index=False)
    with pytest.raises(lp.LivePackError, match="manifest"):
        lp.load_pack(tmp_path)


def test_T4d_honest_in_memory_sink_save_load_prove(tmp_path):
    pack = build(sink=lp.InMemorySink())
    proof = lp.build_inversion_proof(pack)
    assert proof["pass"]
    lp.save_pack(pack.with_proof(proof), tmp_path)
    loaded = lp.load_pack(tmp_path)
    assert loaded is not None
    assert loaded.pack_hash == pack.pack_hash
    assert lp.build_inversion_proof(loaded) == proof


class _MinimalInnerSink:
    def __init__(self) -> None:
        self._frames: dict[str, pd.DataFrame] = {}

    def add(self, row: lp.PackName, frozen: pd.DataFrame, *, next_session: date) -> None:
        self._frames[row.ticker] = frozen

    def finish(self) -> dict[str, pd.DataFrame]:
        return self._frames


def test_T4f_sink_reuse_guards():
    tap = lp.ProofTapSink(_MinimalInnerSink())
    pack = build(sink=tap)
    with pytest.raises(lp.LivePackError, match="reused"):
        tap.add(pack.names[0], pack.substrate[pack.names[0].ticker],
                next_session=date.fromisoformat(pack.next_session))
    with pytest.raises(lp.LivePackError, match="reused"):
        tap.finish()

    sink = lp.InMemorySink()
    build(sink=sink)
    with pytest.raises(lp.LivePackError, match="reused"):
        sink.add(pack.names[0], pack.substrate[pack.names[0].ticker],
                 next_session=date.fromisoformat(pack.next_session))


def test_T6_with_proof_substrate_identity():
    tap = lp.ProofTapSink(_EmptyFinishSink())
    empty_pack = build(sink=tap)
    proof = lp.build_inversion_proof(empty_pack, threshold_cases=tap.threshold_cases())
    with_proof = empty_pack.with_proof(proof)
    assert with_proof.substrate is empty_pack.substrate

    default = build()
    default_proof = lp.build_inversion_proof(default)
    copied = default.with_proof(default_proof)
    assert copied.substrate is not default.substrate
    assert set(copied.substrate) == set(default.substrate)


def test_T7_threshold_cases_for_accepts_iso_or_date():
    pack = build()
    compared = 0
    for row in pack.names:
        frame = pack.substrate.get(row.ticker)
        if frame is None:
            continue
        iso_cases = lp.threshold_cases_for(row, frame, next_session=pack.next_session)
        date_cases = lp.threshold_cases_for(
            row, frame, next_session=date.fromisoformat(pack.next_session))
        assert iso_cases == date_cases
        compared += len(iso_cases)
    assert compared > 0


def test_T8_proof_tap_threshold_cases_returns_fresh_list():
    tap = lp.ProofTapSink(lp.InMemorySink())
    build(sink=tap)
    first = tap.threshold_cases()
    first.append({"mutated": True})
    second = tap.threshold_cases()
    assert second == tap.threshold_cases()
    assert not any(c.get("mutated") for c in second)


def test_FU1_load_pack_refuses_extra_ticker_in_parquet(tmp_path):
    pack = build()
    proof = lp.build_inversion_proof(pack)
    lp.save_pack(pack.with_proof(proof), tmp_path)
    parquet_path = lp.pack_root(tmp_path) / pack.as_of / "substrate.parquet"
    flat = pd.read_parquet(parquet_path)
    extra = flat.loc[flat["ticker"] == "FLAT"].head(1).copy()
    extra["ticker"] = "ZZZ"
    flat = pd.concat([flat, extra], ignore_index=True)
    flat.to_parquet(parquet_path, index=False)
    with pytest.raises(lp.LivePackError, match="substrate_key_mismatch"):
        lp.load_pack(tmp_path)


def test_FU2_nonfinite_fingerprints_and_index_shift_refused():
    idx = pd.date_range("2026-01-05", periods=3, freq="B", tz="UTC")
    base = pd.DataFrame({"high": [1.0, 2.0, 3.0], "low": [0.5, 1.5, 2.5],
                         "close": [0.8, 1.8, 2.8]}, index=idx)
    nan_frame = base.copy()
    nan_frame.iloc[0, 0] = float("nan")
    pos_frame = base.copy()
    pos_frame.iloc[0, 0] = float("inf")
    neg_frame = base.copy()
    neg_frame.iloc[0, 0] = float("-inf")
    fps = {lp.substrate_fingerprint(f) for f in (nan_frame, pos_frame, neg_frame)}
    assert len(fps) == 3
    shifted = base.copy()
    shifted.index = pd.date_range("2026-01-05 23:00", periods=3, freq="D", tz="UTC")
    with pytest.raises(lp.LivePackError, match="substrate_index_not_normalized"):
        lp._refuse_substrate_index_not_normalized(shifted, ticker="X")


def test_FU2b_old_fingerprint_version_manifest_refused(tmp_path):
    import json

    pack = build()
    lp.save_pack(pack, tmp_path)
    manifest_path = lp.pack_root(tmp_path) / pack.as_of / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["substrate_fingerprint_version"] = 1
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")),
                             encoding="utf-8")
    with pytest.raises(lp.LivePackError, match="fingerprint_version_mismatch"):
        lp.load_pack(tmp_path)


def test_FU3_swapped_case_fingerprints_refused_and_pass_recomputed():
    tap = lp.ProofTapSink(lp.InMemorySink())
    pack = build(sink=tap)
    cases = tap.threshold_cases()
    tampered = [dict(c) for c in cases]
    stale_i = next(i for i, c in enumerate(tampered) if c["case"].startswith("STALE:"))
    wash_i = next(i for i, c in enumerate(tampered) if c["case"].startswith("WASH:"))
    tampered[stale_i]["substrate_fingerprint"], tampered[wash_i]["substrate_fingerprint"] = (
        tampered[wash_i]["substrate_fingerprint"], tampered[stale_i]["substrate_fingerprint"])
    with pytest.raises(lp.LivePackError, match="case_fingerprint_mismatch"):
        lp.build_inversion_proof(pack, threshold_cases=tampered)
    lied = [dict(c) for c in cases]
    lied[0]["pass"] = True
    lp.build_inversion_proof(pack, threshold_cases=lied)
    assert lied[0]["pass"] is (lied[0]["expected"] == lied[0]["observed"])


def test_FU4_pack_hash_mismatch_when_manifest_tampered(tmp_path):
    pack = build()
    lp.save_pack(pack, tmp_path)
    manifest_path = lp.pack_root(tmp_path) / pack.as_of / "manifest.json"
    text = manifest_path.read_text(encoding="utf-8")
    manifest_path.write_text(text.replace(pack.pack_hash, "0" * len(pack.pack_hash)),
                             encoding="utf-8")
    with pytest.raises(lp.LivePackError, match="pack_hash_mismatch"):
        lp.load_pack(tmp_path)


def test_FU5_load_compact_duplicate_ticker_listed_twice(tmp_path):
    import hashlib

    import pyarrow as pa
    import pyarrow.parquet as pq

    from engine.entry_radar import pack_state as ps

    row_a = ps.compact_state_row("A", frame_from_closes([1.0, 2.0, 3.0]), price_basis="adjusted")
    row_b = ps.compact_state_row("B", frame_from_closes([2.0, 3.0, 4.0]), price_basis="adjusted")
    ps.write_compact(tmp_path / "c.parquet", [row_a, row_b])
    table = pq.read_table(tmp_path / "c.parquet")
    rows = table.to_pylist()
    rows.insert(1, dict(rows[0]))
    dup_path = tmp_path / "dup.parquet"
    pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), dup_path)
    digest = hashlib.sha256(dup_path.read_bytes()).hexdigest()
    with pytest.raises(ps.CompactStateError, match="listed twice"):
        ps.load_compact(dup_path, expected_sha256=digest)
