"""Retained-vs-reconstructed evidence mode fences (LR-T06-1 / T06).

The reconstructed sector RS history (engine/sector_cycles.compute) and the
retained rotation ledger receipts (engine/rotation_events.read_ledger_history)
are two disjoint evidence vocabularies.  These fences pin that reconstructed
coordinates can never be confused with retained receipts: a past-date rebuild
never paints today's status at the old date, retained bytes are never rewritten
or deduplicated, and the two mode strings never cross.  Synthetic panels and
temp ledgers only; network-free.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import inputs as engine_inputs  # noqa: E402
from engine import rotation_events as re_  # noqa: E402
from engine import sector_cycles as sc  # noqa: E402
from tests.test_rotation_events import (  # noqa: E402
    _history_closed,
    _history_created,
    _write_history,
)
from tests.test_sector_cycles import _rs_history_panel  # noqa: E402

LEDGER_ROW_MODES = {"RECONSTRUCTED_REPLAY", "RETAINED_LEDGER_UNMARKED"}


@pytest.fixture(scope="module")
def em01_payload():
    """The EM-01 past-asof compute payload, shared by the vocabulary fences.

    Same monkeypatch shape as test_sector_cycles' contract test, but requested
    at a past session so the PIT labelling is observable.
    """
    panel = _rs_history_panel(520)
    past = panel.index[-60]
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(sc, "yahoo_closes", lambda basis="tr": panel.copy())
        mp.setattr(
            sc.config,
            "load",
            lambda: {"engine": {"rs_ranking": {"benchmark": "SPY"}}},
        )

        def fake_build_sector(ticker, meta, closes, win_start, closes_px=None):
            if ticker != "XLK":
                return None
            live = sc._leadership(closes, ticker)
            return {
                "id": "xlk",
                "ticker": "XLK",
                "kind": "sector",
                "name": "Technology",
                "price": [{"x": 2026.0, "v": 100.0}],
                "osc": [{"x": 2026.0, "v": 50.0}],
                "turns": [],
                "proj": None,
                "now": {
                    "phase": "Expansion",
                    "pos": 50,
                    "rs_21d": live["rs_21d"],
                    "rs_63d": live["rs_63d"],
                },
                "rs_history": sc._leadership_history(closes, ticker),
            }

        mp.setattr(sc, "build_sector", fake_build_sector)
        mp.setattr(sc, "_load_baskets", lambda: {})
        mp.setattr(sc, "build_amalgam_family", lambda *args, **kwargs: [])
        data = sc.compute(asof=str(past.date()))
    assert data is not None
    return {"panel": panel, "past": past, "data": data}


def test_em01_past_asof_history_is_labelled_and_never_uses_later_prices(em01_payload):
    panel, past = em01_payload["panel"], em01_payload["past"]
    data = em01_payload["data"]
    as_of = str(past.date())
    declared = data["meta"]["rs_history"]
    rows = data["sectors"][0]["rs_history"]

    assert declared["mode"] == "reconstructed_price_history"
    assert declared["naturally_observed"] is False
    assert declared["as_of"] == data["meta"]["asOf"] == as_of
    assert all(row["date"] <= as_of for row in rows)
    # The rows must be the series rebuilt from the asof-sliced panel only…
    assert rows == sc._leadership_history(panel[panel.index <= past], "XLK")
    # …so today's status can never be painted at the old date.
    assert rows[-1]["date"] != str(panel.index[-1].date())


def test_em02_declared_basis_matches_the_price_source_default(em01_payload):
    assert (
        inspect.signature(engine_inputs.yahoo_closes).parameters["basis"].default
        == "tr"
    )
    assert em01_payload["data"]["meta"]["rs_history"]["basis"] == "tr"


def test_em03_retained_ledger_receipts_are_never_rewritten_or_deduplicated(tmp_path):
    ledger = tmp_path / "events.jsonl"
    original = _history_created(ts="2026-07-02 01:02 UTC")
    later = _history_created(ts="2026-07-05 01:02 UTC")
    later["severity"] = "escalated"   # same lifecycle, later correction-like re-observation
    closed = _history_closed()
    _write_history(ledger, [original, later, closed])

    before = ledger.read_bytes()
    first = re_.read_ledger_history(ledger)
    after_first = ledger.read_bytes()
    second = re_.read_ledger_history(ledger)
    after_second = ledger.read_bytes()

    assert before == after_first == after_second      # reads never rewrite the bytes
    assert first["status"] == second["status"] == "OK"
    created = [e for e in first["rows"] if e["row"]["event"] == "created"]
    assert len(created) == 2                          # the reader never deduplicates:
    assert created[0]["row"] == original              # the original fact is retained…
    assert created[1]["row"]["severity"] == "escalated"   # …alongside the later one
    assert {e["lifecycle_id"] for e in created} == {"xlk:memory->mag7@2026-07-01"}
    assert first["coverage"]["event_counts"]["created"] == 2
    assert first["coverage"]["repeated_lifecycle_event_rows"] >= 1
    # Each entry hashes its own physical line (provenance, not identity).
    physical = before.decode("utf-8").splitlines()
    for entry in first["rows"]:
        assert entry["line_sha256"] == hashlib.sha256(
            physical[entry["line"] - 1].encode("utf-8")
        ).hexdigest()
    assert all(e["mode"] in LEDGER_ROW_MODES for e in first["rows"])

    # A corrupt line fails closed — it is never silently dropped.
    with open(ledger, "a", encoding="utf-8") as fh:
        fh.write("{not json\n")
    bad = re_.read_ledger_history(ledger)
    assert bad["status"] != "OK"
    assert bad["status"] == "INVALID"
    assert bad["rows"] == []
    assert bad["error"] and bad["error"]["code"] == "INVALID_JSON"
    assert bad["error"]["line"] == 4


def test_em04_reconstructed_and_retained_vocabularies_are_disjoint(em01_payload,
                                                                   tmp_path):
    data = em01_payload["data"]
    rows = [row for rec in data["sectors"] for row in rec["rs_history"]]
    assert rows
    assert all(set(row) == {"date", "rs_21d", "rs_63d"} for row in rows)

    ledger = tmp_path / "events.jsonl"
    _write_history(ledger, [_history_created(replayed=True), _history_closed()])
    result = re_.read_ledger_history(ledger)
    assert result["status"] == "OK"
    mode_counts = result["coverage"]["mode_counts"]
    assert set(mode_counts) == LEDGER_ROW_MODES
    assert "reconstructed_price_history" not in mode_counts
    assert all(e["mode"] in LEDGER_ROW_MODES for e in result["rows"])
    # Neither retained-ledger mode string ever appears in the reconstructed payload.
    payload_text = json.dumps(data)
    for mode in LEDGER_ROW_MODES:
        assert mode not in payload_text


def test_em05_reconstructed_history_is_not_an_event_source(em01_payload, tmp_path):
    absent = re_.read_ledger_history(tmp_path / "no_such_ledger.jsonl")
    assert absent["status"] == "MISSING"
    assert absent["rows"] == []

    def all_keys(obj):
        out = set()
        if isinstance(obj, dict):
            for key, val in obj.items():
                out.add(key)
                out |= all_keys(val)
        elif isinstance(obj, list):
            for item in obj:
                out |= all_keys(item)
        return out

    keys = all_keys(em01_payload["data"])
    assert not keys & {"created_tonight", "active", "events"}
