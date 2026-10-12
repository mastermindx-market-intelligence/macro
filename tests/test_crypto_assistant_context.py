"""Pure crypto/vector assistant-context contract.

No customer message is sent. No network. Fixtures are tmp files and in-memory
dicts. The assertions are the properties these functions already implement:
source basis and as-of stay on the quote clock, a missing print is omitted
rather than zeroed, a stale print is not a current print, a historical
question is not planned as a current fact, and a guest does not pass the
protected-evidence gate.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from engine.intelligence_workspace.context_compiler import compile_envelope
from engine.neuralweb import brain_gateway
from engine.neuralweb import market_packet as mp
from engine.neuralweb.native_facts import _render_fact, plan_native_facts

SOURCE_ASOF = "2026-09-26T20:00:00+00:00"
SOURCE_STAMP = "09-26 20:00Z"
EVAL_FRESH = datetime(2026, 9, 26, 20, 10, tzinfo=timezone.utc)
EVAL_STALE = datetime(2026, 9, 26, 21, 40, tzinfo=timezone.utc)


@pytest.fixture
def root(monkeypatch, tmp_path: Path) -> Path:
    monkeypatch.delenv(mp._LIVE_DIR_ENV, raising=False)
    monkeypatch.setattr(mp, "_VPS_LIVE_DIR", tmp_path / "no-vps-live")
    mp._CACHE.clear()
    yield tmp_path
    mp._CACHE.clear()


def _write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


def _quotes(*, eth: dict | None) -> dict:
    quotes = {
        "BTC-USD": {
            "price": 64000.0,
            "changePct": -3.1,
            "delayMin": 1.0,
            "basis": "coingecko-spot",
        }
    }
    if eth is not None:
        quotes["ETH-USD"] = eth
    return {
        "asof": SOURCE_ASOF,
        "source": "fixture-snapshot",
        "quotes": quotes,
    }


def _arm(root: Path, *, eth: dict | None, session_open: bool = True) -> None:
    live = root / "site" / "live"
    _write(live / "quotes.json", _quotes(eth=eth))
    _write(live / "risk_state.json", {
        "session": {"open": session_open, "local_time": "2026-09-26 16:00 EDT"},
        "stale": False,
        "stale_reason": "",
    })


def _btc(packet: dict) -> dict:
    rows = [r for r in packet["tape"]["crypto"] if r["sym"] == "BTC-USD"]
    assert len(rows) == 1
    return rows[0]


def test_crypto_tape_keeps_source_basis_and_asof_off_the_eval_clock(root: Path) -> None:
    _arm(root, eth=None)
    packet = mp.build_packet(root, now=EVAL_FRESH)
    row = _btc(packet)
    assert packet["tape"]["asof"] == SOURCE_ASOF
    assert "asof" not in row
    assert row["basis"] == "coingecko-spot"
    assert row["price"] == 64000.0
    assert packet["basis"] == mp._BASIS_LIVE
    assert packet["stale_warn"] is False
    text = mp.render_digest(packet)
    assert SOURCE_STAMP in text
    assert "09-26 20:10Z" not in text
    assert "ETH" not in text
    assert mp._STALE_PREFIX not in text


def test_missing_crypto_row_is_omitted_and_an_explicit_zero_is_kept(root: Path) -> None:
    _arm(root, eth={"price": None, "changePct": None, "delayMin": 1.0, "basis": "coingecko-spot"})
    omitted = mp.build_packet(root, now=EVAL_FRESH)
    assert [r["sym"] for r in omitted["tape"]["crypto"]] == ["BTC-USD"]
    assert "ETH" not in mp.render_digest(omitted)
    assert "0%" not in mp.render_digest(omitted)

    _arm(root, eth={"price": 0.0, "changePct": 0.0, "delayMin": 1.0, "basis": "coingecko-spot"})
    zeroed = mp.build_packet(root, now=EVAL_FRESH)
    eth = next(r for r in zeroed["tape"]["crypto"] if r["sym"] == "ETH-USD")
    assert eth["price"] == 0.0 and eth["change_pct"] == 0.0
    assert eth["basis"] == "coingecko-spot"
    assert "ETH 0%" in mp.render_digest(zeroed)


def test_stale_crypto_print_stays_the_source_clock_and_is_not_current(root: Path) -> None:
    _arm(root, eth=None)
    packet = mp.build_packet(root, now=EVAL_STALE)
    assert packet["tape"]["asof"] == SOURCE_ASOF
    assert packet["basis"] == mp._BASIS_LIVE
    assert packet["stale_warn"] is True
    text = mp.render_digest(packet)
    assert text.split("\n")[1].startswith(
        "STALE — treat as last known, not current: TAPE (" + SOURCE_STAMP
    )
    assert "21:40Z" not in text


def test_closed_session_clock_is_not_relabeled_live(root: Path) -> None:
    _arm(root, eth=None, session_open=False)
    packet = mp.build_packet(root, now=EVAL_FRESH)
    assert packet["basis"] == mp._BASIS_CLOSED
    assert packet["stale_warn"] is False
    assert packet["tape"]["asof"] == SOURCE_ASOF
    text = mp.render_digest(packet)
    assert "last session's tape (market closed)" in text
    assert mp._STALE_PREFIX not in text


def test_rendered_fact_carries_source_and_asof_and_unavailable_is_not_zero() -> None:
    available, _clause = _render_fact({
        "field_id": "market.price.last",
        "value": 64000,
        "unit": "USD",
        "status": "available",
        "source": {"source_id": "coingecko-spot"},
        "as_of": "2026-09-26",
        "freshness": {"state": "fresh"},
    })
    assert "source=coingecko-spot" in available
    assert "as_of=2026-09-26" in available
    assert "USD 64000" in available

    missing, _clause = _render_fact({
        "field_id": "market.price.last",
        "value": 0,
        "unit": "USD",
        "status": "unavailable",
        "reason_code": "missing",
        "source": {"source_id": "coingecko-spot"},
        "as_of": "1999-11-19",
        "freshness": {"state": "missing"},
    })
    assert "current price: unavailable (missing)" in missing
    assert "source=coingecko-spot" in missing
    assert "as_of=1999-11-19" in missing
    assert "0" not in missing


def test_historical_cursor_is_not_planned_as_a_current_fact() -> None:
    current = plan_native_facts("what is the BTC price")
    assert current is not None
    assert current.symbol == "BTC"
    assert "market.price.last" in current.field_ids
    assert plan_native_facts("what is the BTC price as of 2022-11-09") is None
    assert plan_native_facts("what is the BTC price on 2022-11-09") is None


def test_compiler_keeps_page_and_does_not_rewrite_an_old_capture_to_now() -> None:
    captured = "2026-09-26T20:00:00Z"
    now = datetime(2026, 10, 12, 4, 0, tzinfo=timezone.utc)
    envelope = compile_envelope(
        "what is the backdrop",
        {"ai_context": {
            "schema": "ai_context_client.v1",
            "origin_id": "vector-page",
            "context_revision": 3,
            "captured_at": captured,
            "pinned": [],
            "active": None,
            "ambient": {
                "page": "vector",
                "panel": "cycle-lab",
                "source_id": "btc.decision/v1",
                "shown_as_of": "2026-09-26",
                "historical_cursor": "2022-11-09",
            },
            "effective_context": {"source": "explicit", "entities": [{"type": "security", "id": "ETH"}]},
        }},
        now=now,
        request_id="t20-fixed",
    )
    ambient = envelope["ambient_widget_context"]
    assert ambient["page"] == "vector"
    assert ambient["panel"] == "cycle-lab"
    assert envelope["origin"]["captured_at"] == captured
    assert envelope["context_flags"]["stale"] is True
    assert "effective_context" in envelope["context_flags"]["rejected_fields"]
    assert envelope["effective_context"]["source"] == "none"
    assert envelope["effective_context"]["entities"] == []
    # A scrubber date in the client block must not become the effective entity
    # or the page label. The compiler's echoed ambient keys are still only
    # symbol/timeframe/page/panel (context_compiler.py); source_id and the
    # cursor are not on that surface, which the census records as a gap.
    assert "2022-11-09" not in json.dumps(envelope["effective_context"])
    assert ambient["page"] != "2022-11-09"

    fresh_at = (now - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    fresh = compile_envelope(
        "what is the backdrop",
        {"ai_context": {
            "schema": "ai_context_client.v1",
            "origin_id": "crypto-page",
            "context_revision": 1,
            "captured_at": fresh_at,
            "pinned": [],
            "active": None,
            "ambient": {"page": "crypto"},
        }},
        now=now,
        request_id="t20-fresh",
    )
    assert fresh["ambient_widget_context"]["page"] == "crypto"
    assert fresh["origin"]["captured_at"] == fresh_at
    assert fresh["context_flags"]["stale"] is False


def test_guest_and_unknown_do_not_receive_protected_context(tmp_path: Path) -> None:
    assert brain_gateway._ontology_evidence_allowed("") is False
    assert brain_gateway._ontology_evidence_allowed("unknown") is False
    assert brain_gateway._ontology_evidence_allowed("guest:not-a-customer") is False
    assert brain_gateway._rotation_risk_grounding_digest(
        tmp_path, user_id="guest:not-a-customer", now=EVAL_FRESH,
    ) == ""
    assert brain_gateway._rotation_risk_grounding_digest(
        tmp_path, user_id="unknown", now=EVAL_FRESH,
    ) == ""
