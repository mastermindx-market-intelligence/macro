"""The intraday overlay build (scripts.build_live_overlay) + Mastermind emit v2.

The offline path is load-bearing: it must always emit a VALID overlay (NaN-safe,
every leg stale, falling back to baseline) with no network — now including the
market-context + per-region session blocks. Also pins the Mastermind emit v2
(alloc weights + asof in JSON).
"""
from __future__ import annotations

from datetime import datetime
import json

from scripts import build_live_overlay as blo
from scripts import build_masterminds as bmm


def test_universe_includes_gtaa_assets():
    uni = blo.build_universe()
    assert isinstance(uni, list) and uni
    assert "SPY" in uni and "GC=F" in uni
    assert len(uni) <= int((blo.config.load().get("live") or {}).get("max_universe", 150))


def test_offline_build_emits_valid_v2_overlay(tmp_path, monkeypatch):
    # Pin the input universe/baseline so this schema contract does not require
    # production data to be materialized in a sparse checkout.
    monkeypatch.setattr(blo, "build_universe", lambda: ["SPY", "GC=F"])
    monkeypatch.setattr(blo, "_load_baseline", lambda ticker, close: {
        "ticker": ticker, "asof": "2026-09-30", "tech": {"close": 100.0},
    })
    # site_dir=tmp_path: output never lands in the repo's real site/ tree
    res = blo.build(offline=True, limit=8, site_dir=tmp_path)
    assert res["status"] == "ok"
    site = tmp_path
    raw = (site / "live" / "overlay.json").read_text()
    assert "NaN" not in raw                         # allow_nan=False -> never invalid JSON
    out = json.loads(raw)
    assert out["schema"] == "live.overlay.v2"
    assert out["n_quotes"] == 0 and out["n"] >= 1
    for rec in out["tickers"].values():
        assert rec["stale"] is True and "tech" in rec and "region" in rec
    # Existing globe regions plus independently eligible Stock Connect.
    assert set(out["sessions"]) == {
        "us", "cn", "hk", "ca", "connect", "jp", "kr", "tw", "gb", "eu",
    }
    assert "VIX" in out["market"] and "band" in out["market"]["VIX"]
    assert (site / "live_config.js").exists()


def test_offline_allocations_are_stale_marked(tmp_path):
    blo.build(offline=True, limit=4, site_dir=tmp_path)
    out = json.loads((tmp_path / "live" / "overlay.json").read_text())
    for region in out.get("allocations", {}).values():
        for card in region["cards"]:
            for leg in card["alloc"]:
                assert leg["stale"] is True and leg["live_price"] is None


def test_market_session_block_shape(tmp_path):
    blo.build(offline=True, limit=2, site_dir=tmp_path)
    out = json.loads((tmp_path / "live" / "overlay.json").read_text())
    us = out["sessions"]["us"]
    assert {"region", "open", "local_time", "state", "timezone",
            "calendar_verified", "checked_at", "valid_until", "expected_session",
            "next_open", "data_frozen", "source_urls"} <= set(us)
    assert us["region"] == "us" and us["timezone"] == "America/New_York"
    assert isinstance(us["local_time"], str) and isinstance(us["data_frozen"], bool)
    if us["calendar_verified"]:
        assert isinstance(us["open"], bool) and us["source_urls"]
    else:
        assert us["open"] is None and us["state"] == "unverified"
    checked = datetime.fromisoformat(us["checked_at"])
    expires = datetime.fromisoformat(us["valid_until"])
    assert checked.tzinfo is not None and expires > checked
    assert datetime.fromisoformat(us["next_open"]).tzinfo is not None
    assert datetime.fromisoformat(us["expected_session"]).date().isoformat() == us["expected_session"]
    # The other five venue clocks retain their incumbent shape.
    assert set(out["sessions"]["jp"]) == {"region", "open", "local_time"}


def test_live_config_js_carries_worker_url(tmp_path):
    blo.write_live_config(tmp_path)
    js = (tmp_path / "live_config.js").read_text()
    assert "LIVE_QUOTES_URL" in js and "LIVE_POLL_SEC" in js


def test_resolve_worker_url_env_override_and_https_guard(monkeypatch):
    # env var overrides config + strips a trailing slash (turn-on via a GitHub repo variable)
    monkeypatch.setenv("LIVE_QUOTES_WORKER_URL", "https://q.example.workers.dev/")
    assert blo.resolve_worker_url() == "https://q.example.workers.dev"
    # a non-https value is rejected so a malformed variable can't break live.js
    monkeypatch.setenv("LIVE_QUOTES_WORKER_URL", "http://insecure.dev")
    assert blo.resolve_worker_url() == ""
    # empty env -> falls back to config.yml (default "")
    monkeypatch.delenv("LIVE_QUOTES_WORKER_URL", raising=False)
    assert blo.resolve_worker_url() == str((blo.config.load().get("live") or {}).get("quotes_worker_url", "") or "")


def test_masterminds_snap_v2_carries_alloc_and_asof():
    if not hasattr(bmm, "_snap"):
        import pytest
        pytest.skip("build_masterminds._snap (v2 alloc emit) is a main-only refactor not "
                    "yet on feat/signal-engine-buy-filter; auto-reactivates after merge")
    cards = [{"key": "mm_moderate", "name_en": "MM Moderate", "cagr": 11.5,
              "sharpe": 1.1, "maxdd": -24.0}]
    ress = [{"asof": "2026-06-20", "gross_now": 1.4,
             "alloc": [{"asset": "SPY", "weight": 40.0},
                       {"asset": "GC=F", "weight": 20.0}]}]
    snap = bmm._snap(cards, ress, "2026-06-21 08:20 UTC")
    assert snap["schema"] == "masterminds.latest.v2"
    assert snap["asof"] == "2026-06-20" and snap["stale_after_min"] == 1440
    c0 = snap["cards"][0]
    assert c0["alloc"][0]["asset"] == "SPY" and c0["gross_now"] == 1.4
