"""Entry Radar pack builder substrate sink — streaming hand-off and proof tap."""
from __future__ import annotations

import types
from datetime import date

import pandas as pd

from engine.entry_radar import live_pack as lp
from tests.test_entry_radar_w4_pack import build, store


def test_T1_in_memory_sink_matches_default_build():
    default = build()
    with_sink = build(sink=lp.InMemorySink())
    assert default.pack_hash == with_sink.pack_hash
    assert default.names == with_sink.names
    for ticker in sorted(default.substrate):
        pd.testing.assert_frame_equal(
            default.substrate[ticker], with_sink.substrate[ticker])
    assert lp.build_inversion_proof(default) == lp.build_inversion_proof(with_sink)


def test_T2_proof_tap_collects_threshold_cases():
    tap = lp.ProofTapSink(lp.InMemorySink())
    pack = build(sink=tap)
    default = build()
    assert tap.threshold_cases() == lp._proof_threshold_cases(default)
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


def test_T4_empty_substrate_mapping_with_proof_tap():
    tap = lp.ProofTapSink(_EmptyFinishSink())
    pack = build(sink=tap)
    default = build()
    assert pack.pack_hash == default.pack_hash
    assert pack.names == default.names
    assert len(pack.substrate) == 0
    assert lp.build_inversion_proof(
        pack, threshold_cases=tap.threshold_cases()) == lp.build_inversion_proof(default)
    assert lp.build_inversion_proof(pack) != lp.build_inversion_proof(
        pack, threshold_cases=tap.threshold_cases())


def test_T5_empty_threshold_cases_omits_threshold_boundary_family():
    default_proof = lp.build_inversion_proof(build())
    empty_thresh = lp.build_inversion_proof(build(), threshold_cases=[])
    assert "threshold_boundary" in default_proof["by_family"]
    assert "threshold_boundary" not in empty_thresh["by_family"]


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
