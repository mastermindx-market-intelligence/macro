"""Synthetic quote lineage tests; no vendor authentication or security join."""
from __future__ import annotations

import copy
import json

import pytest

from engine.entry_radar import live_eval as le
from engine.entry_radar import live_ledger as ll
from engine.marketing import live_verify as lv
from lib.quote_native_metadata import SCHEMA, copy_native_metadata, from_native_quote
from tests.test_entry_radar_w4_live import NEXT_SESSION, et_now, one_pass, pack, quote_book


def native(source="polygon", **changes):
    row = {"source": source, "basis": "trade", "ts": 1780000000000,
           "quote_ts": "2026-05-28T00:26:40Z",
           "quote_ts_synthetic": False, "tsSynthetic": False}
    row.update(changes)
    return row


def test_normalizer_preserves_declared_clocks_beside_unchanged_consumed_inputs():
    row = native(ts=None, quote_ts_synthetic=True, tsSynthetic=True)
    row.update(price=123, prevClose=120, changePct=2.5)
    result = lv._quotes_from_snapshot({"quotes": {"aapl": row}})["AAPL"]
    assert result == {"price": 123, "prev_close": 120, "change_pct": 2.5,
        "ts_ms": None, "source": "quotes",
        "native_quote_metadata": {"schema": SCHEMA, **native(
            ts=None, quote_ts_synthetic=True, tsSynthetic=True)}}
    # A synthetic native clock never becomes an actual market timestamp.
    quote = le.read_quote("AAPL", result, now=et_now(32), session=NEXT_SESSION, max_age_min=20)
    assert not quote.usable
    assert quote.to_dict()["native_quote_metadata"]["quote_ts_synthetic"] is True
    assert le.read_quote("AAPL", {k: v for k, v in result.items()
        if k != "native_quote_metadata"}, now=et_now(32), session=NEXT_SESSION, max_age_min=20).state == quote.state


def test_freshest_wins_keeps_metadata_with_its_own_row_and_never_backfills(tmp_path):
    (tmp_path / "site/live").mkdir(parents=True)
    (tmp_path / "data/marketing").mkdir(parents=True)
    def write(rel, row):
        (tmp_path / rel).write_text(json.dumps({"quotes": {"AAPL": row}}))
    write("site/live/quotes.json", dict(native("polygon", ts=9000), price=12))
    write("data/marketing/live_quotes_snapshot.json", dict(native("yahoo", ts=8000), price=11))
    result = lv.load_live_quotes(tmp_path)["quotes"]["AAPL"]
    assert result["price"] == 12
    assert result["native_quote_metadata"]["source"] == "polygon"
    write("data/marketing/live_quotes_snapshot.json", {"ts": 10000, "price": 13})
    result = lv.load_live_quotes(tmp_path)["quotes"]["AAPL"]
    assert result["price"] == 13 and "native_quote_metadata" not in result


@pytest.mark.parametrize("changes", [
    {"source": None}, {"source": "https://secret.example/token"},
    {"source": "x" * 65}, {"basis": "trade\n"}, {"quote_ts": {"unknown": "nested"}},
    {"ts": 10**1000}, {"ts": float("nan")}, {"ts": True},
    {"quote_ts_synthetic": 1}, {"tsSynthetic": "false"},
])
def test_malformed_metadata_is_omitted_without_changing_normalized_price(changes):
    row = native(**changes)
    result = lv._quotes_from_snapshot({"quotes": {"AAPL": dict(row, price=123)}})["AAPL"]
    assert result["price"] == 123 and result["source"] == "quotes"
    assert "native_quote_metadata" not in result


def test_closed_shape_refuses_extra_fields_and_copies_scalars():
    metadata = from_native_quote(native())
    assert metadata is not None
    assert copy_native_metadata(dict(metadata, token="must-not-be-retained")) is None
    copied = copy_native_metadata(metadata)
    copied["source"] = "changed"
    assert metadata["source"] == "polygon"


def test_journal_roundtrip_keeps_metadata_and_legacy_points_unknown():
    journal = le.SessionJournal(None)
    record = journal.open_session(session="2026-05-28", ticker="AAPL",
        pack_as_of="2026-05-27", pack_hash="same-pack", price_basis="adjusted")
    metadata = from_native_quote(native())
    assert journal.append_point(record, ts=et_now(30), price=123, basis="trade",
        source="quotes", basis_audit={}, native_quote_metadata=metadata)
    metadata["source"] = "changed"
    encoded = record.to_dict()
    restored = le.JournalRecord.from_dict(encoded)
    encoded["points"][0]["native_quote_metadata"]["source"] = "changed"
    assert restored.points[0]["native_quote_metadata"]["source"] == "polygon"
    assert record.points[0]["native_quote_metadata"]["source"] == "polygon"
    legacy = record.to_dict()
    legacy["points"][0].pop("native_quote_metadata")
    assert "native_quote_metadata" not in le.JournalRecord.from_dict(legacy).to_dict()["points"][0]


@pytest.mark.parametrize("kept_has_metadata", [True, False])
def test_refused_correction_reports_the_kept_points_metadata(tmp_path, pack, kept_has_metadata):
    ledger = ll.LiveEpisodeLedger(tmp_path)
    book = quote_book(pack, multiple=0.97, ts=et_now(30))
    old = from_native_quote(native("polygon"))
    if kept_has_metadata:
        book["quotes"]["WASH"]["native_quote_metadata"] = old
    one_pass(pack, book, now=et_now(32), ledger=ledger, state_dir=tmp_path)
    corrected = copy.deepcopy(book)
    corrected["quotes"]["WASH"]["price"] *= 0.82
    corrected["quotes"]["WASH"]["native_quote_metadata"] = from_native_quote(native("yahoo"))
    result = one_pass(pack, corrected, now=et_now(37), ledger=ledger, state_dir=tmp_path)
    row = next(r for r in result.payload["names"] if r["ticker"] == "WASH")
    assert row["quote"].get("native_quote_metadata") == (old if kept_has_metadata else None)
    assert row["quote_rejected"]["native_quote_metadata"]["source"] == "yahoo"
    assert row["quote"]["price"] == row["observation"]["sampled_close"]
    retained = le.SessionJournal(tmp_path).read(NEXT_SESSION.isoformat(), "WASH")
    assert retained.points[0].get("native_quote_metadata") == (old if kept_has_metadata else None)


def test_optional_metadata_does_not_change_detector_or_episode_results(tmp_path, pack, monkeypatch):
    monkeypatch.setattr(le, "_attach_catalyst", lambda *args, **kwargs: None)
    def without_metadata(value):
        if isinstance(value, dict):
            return {k: without_metadata(v) for k, v in value.items() if k != "native_quote_metadata"}
        if isinstance(value, (list, tuple)):
            return [without_metadata(v) for v in value]
        return value
    ledgers = [ll.LiveEpisodeLedger(tmp_path / name) for name in ("plain", "with_metadata")]
    for quote_minute, now_minute, multiple in [(30, 32, 0.97), (35, 37, 0.96)]:
        book = quote_book(pack, multiple=multiple, ts=et_now(quote_minute))
        enriched = copy.deepcopy(book)
        for row in enriched["quotes"].values():
            row["native_quote_metadata"] = from_native_quote(native(ts=row["ts"]))
        results = [one_pass(pack, quotes, now=et_now(now_minute), ledger=ledger,
                     state_dir=ledger.state_dir)
                   for quotes, ledger in zip((book, enriched), ledgers)]
        assert without_metadata(results[0].payload) == without_metadata(results[1].payload)
        assert results[0].delta == results[1].delta
        assert [e.canonical for e in ledgers[0].episodes] == [e.canonical for e in ledgers[1].episodes]
