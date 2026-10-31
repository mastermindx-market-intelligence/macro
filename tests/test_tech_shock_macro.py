"""Primary Macro route mount: one compact EOD panel, no stocks-mode regression."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader

from engine.tech_volatility_shock import _missing
from scripts.tech_shock_macro import render_macro_with_shock, snapshot_for_macro

ROOT = Path(__file__).resolve().parents[1]


def _env(dashboard: str) -> Environment:
    return Environment(loader=ChoiceLoader([
        DictLoader({"dashboard.html.j2": dashboard}),
        FileSystemLoader(ROOT / "templates"),
    ]))


def test_mounted_once_after_dashboard_and_before_body_close():
    html = render_macro_with_shock(
        _env('<html><body><main><section id="regime-radar">REGIME</section></main></body></html>'),
        {"tech_shock": _missing("Raw data not restored.")},
    )
    assert html.count('id="tech-volatility-shock"') == 1
    assert html.count('id="regime-radar"') == 1
    assert html.index("REGIME") < html.index('id="tech-volatility-shock"')
    assert html.index('id="tech-volatility-shock"') < html.index("</body>")
    assert "Raw data not restored." in html
    assert "QQQ vs SPY -1.70" not in html
    assert "tech volatility shock" in html.lower()
    assert "Massive/Polygon" in html


def test_old_vm_has_honest_unavailable_panel():
    html = render_macro_with_shock(_env("<html><body>base</body></html>"), {})
    assert "Data unavailable" in html
    assert "Raw EOD source has not been assembled" in html


def test_ambiguous_body_anchor_fails_not_silently_drops_feature():
    with pytest.raises(ValueError, match="body anchor"):
        render_macro_with_shock(_env("<html><main>no body end</main></html>"), {})
    with pytest.raises(ValueError, match="body anchor"):
        render_macro_with_shock(_env("<body></body></body>"), {})

NOW = datetime(2026, 10, 31, 1, 0, tzinfo=timezone.utc)


def _synthetic_readout() -> dict:
    return {
        "status": "ok", "reason": None, "asof": "2026-10-30", "lag_sessions": 0,
        "indices": [
            {"symbol": "SPY", "return_pct": -1.77, "overnight_pct": -1.04,
             "intraday_pct": -0.74, "z60": -3.01, "volume_multiple": 2.07,
             "rank_ytd": 4, "n_ytd": 200, "year": 2026,
             "overnight_share": 58.4},
            {"symbol": "QQQ", "return_pct": -3.47, "overnight_pct": -2.53,
             "intraday_pct": -0.96, "z60": -3.38, "volume_multiple": 2.32,
             "rank_ytd": 2, "n_ytd": 200, "year": 2026,
             "overnight_share": 72.5},
        ],
        "relative_pp": -1.70, "relative_z60": -2.99,
        "session_read": "overnight_dominant",
        "volume_scope": "full_market_day", "price_scope": "xnys_regular_session",
    }


def test_nightly_publishes_small_view_express_uses_it_without_raw_r2(tmp_path, monkeypatch):
    snap = _synthetic_readout()
    monkeypatch.setattr("scripts.tech_shock_macro.tech_volatility_shock.build_snapshot",
                        lambda *, now: snap)
    result = snapshot_for_macro(tmp_path, now=NOW)
    assert result["source_state"] == "raw_daily_store"
    path = tmp_path / "marketdata" / "tech_volatility_shock.json"
    assert path.exists()
    doc = json.loads(path.read_text())
    assert doc["schema"] == "macro.tech_volatility_shock.v1"
    assert doc["snapshot"]["asof"] == "2026-10-30"
    assert doc["source"] == "massive_stock_day_raw_v1"
    original = path.read_bytes()
    monkeypatch.setattr("scripts.tech_shock_macro.tech_volatility_shock.build_snapshot",
                        lambda *, now: {"status": "unavailable", "indices": [], "asof": None})
    retained = snapshot_for_macro(tmp_path, now=NOW)
    assert retained["source_state"] == "published_projection"
    assert retained["relative_pp"] == -1.70
    assert retained["status"] == "ok"
    assert path.read_bytes() == original


def test_published_view_ages_one_completed_session_and_isnt_clobbered(tmp_path, monkeypatch):
    snap = _synthetic_readout()
    monkeypatch.setattr("scripts.tech_shock_macro.tech_volatility_shock.build_snapshot",
                        lambda *, now: snap)
    snapshot_for_macro(tmp_path, now=NOW)
    path = tmp_path / "marketdata" / "tech_volatility_shock.json"
    original = path.read_bytes()
    old = {**snap, "asof": "2026-10-29", "status": "stale"}
    monkeypatch.setattr("scripts.tech_shock_macro.tech_volatility_shock.build_snapshot",
                        lambda *, now: old)
    candidate = snapshot_for_macro(tmp_path, now=NOW)
    assert candidate["asof"] == "2026-10-30"
    assert candidate["source_state"] == "published_projection"
    assert path.read_bytes() == original
    # Monday Nov 2 has completed by the UTC timestamp below.
    later = datetime(2026, 11, 3, 2, 0, tzinfo=timezone.utc)
    aged = snapshot_for_macro(tmp_path, now=later)
    assert aged["status"] == "stale"
    assert aged["lag_sessions"] == 1
    assert "behind" in aged["reason"]


def test_corrupted_published_projection_is_not_displayed(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.tech_shock_macro.tech_volatility_shock.build_snapshot",
                        lambda *, now: {
                            "status": "unavailable", "indices": [], "asof": None,
                            "relative_pp": None, "reason": "Source not restored.",
                        })
    path = tmp_path / "marketdata" / "tech_volatility_shock.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "schema": "macro.tech_volatility_shock.v1",
        "source": "massive_stock_day_raw_v1", "asof": "2026-10-30",
        "snapshot": {**_synthetic_readout(), "relative_pp": 999},
    }))
    result = snapshot_for_macro(tmp_path, now=NOW)
    assert result["status"] == "unavailable"
    assert result["relative_pp"] is None
    assert result["source_state"] == "unavailable"


def test_snapshot_write_failure_keeps_readout_without_claimed_publish(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.tech_shock_macro.tech_volatility_shock.build_snapshot",
                        lambda *, now: _synthetic_readout())
    def fail(*args):
        raise OSError("read-only mount")
    monkeypatch.setattr("scripts.tech_shock_macro._write_projection", fail)
    result = snapshot_for_macro(tmp_path, now=NOW)
    assert result["source_state"] == "raw_daily_store"
    assert not (tmp_path / "marketdata" / "tech_volatility_shock.json").exists()
