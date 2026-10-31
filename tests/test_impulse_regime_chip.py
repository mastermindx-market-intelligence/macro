"""Impulse Tracker vol-regime chip (W21B-1) — the page must print the producer's
own regime read beside the derived label: mapped bilingual words only, never a
raw slug, and the read's own date only when it differs from the tape's as_of.

Hermetic: engine.neuralweb.read.load_world_state is monkeypatched to synthetic
vol blocks (the pattern of tests/test_world_state_migrations.py:385-460); the
page renders through scripts.build_impulse._render_html with synthetic payloads.
No network, no data/ or site/ reads.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from engine.neuralweb import read as nw_read  # noqa: E402
from lib import config as cfg  # noqa: E402
from scripts import build_impulse as bi  # noqa: E402

# Shape + values quoted from the committed world_state vol block (seat probe).
VOL_WARNING = {
    "regime": "warning",
    "flags": ["move_stress"],
    "fragility_confluence": 1,
    "asof": "2026-02-09",
    "risk_score": -0.18,
    "vix": 19.99,
}


def _patch_vol(monkeypatch, vol):
    """load_world_state -> {"vol": <vol>}; mirrors the migrations-test pattern."""
    monkeypatch.setattr(nw_read, "load_world_state",
                        lambda *a, **k: {"vol": dict(vol)})


def _strip_side(html, drop):
    s = re.search(r'<div class="strip">.*?</div>', html, flags=re.S).group(0)
    s = re.sub(r'<span class="l-%s">.*?</span>' % drop, "", s, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def _strip_en(html):
    return _strip_side(html, "zh")


def _strip_zh(html):
    return _strip_side(html, "en")


def _card(**over):
    row = {"ticker": "TEA", "name": "Test Name", "sector": "Industrials",
           "impulse_score": 100, "state": "EARLY_IGNITION", "accel_z": 0.8,
           "vol_vel": 1.54, "runup_20": 0.05, "dist_50": 0.02, "dist_200": 0.10,
           "rvol": 1.6, "off_high": -0.03, "days_igniting": 1,
           "just_starting": True, "trend_vel": 0.6, "vel_pct": 4.0,
           "eff_ratio": 1.2, "adv20": 1000000.0, "spark_svg": "",
           "note": "Note EN", "note_zh": "测试备注"}
    row.update(over)
    return row


def _payload(regime, as_of="2026-02-06"):
    return {"status": "ok", "as_of": as_of, "universe": 40,
            "counts": {"buy": 1, "igniting": 0, "extended": 0,
                       "coiling": 0, "fading": 0},
            "buy": [_card()], "igniting": [], "coiling": [],
            "extended": [], "fading": [], "regime": regime, "cfg": {}}


def test_regime_copies_the_producer_state_and_flags(monkeypatch):
    _patch_vol(monkeypatch, VOL_WARNING)
    out = bi._regime()
    assert out["regime"] == "warning"
    assert out["flags"] == ["move_stress"]
    assert out["fragility_confluence"] == 1
    assert out["asof"] == "2026-02-09"
    # the derived read (thresholds pinned in test_world_state_migrations) is intact
    assert out["risk_score"] == pytest.approx(-0.18)
    assert out["vix"] == pytest.approx(19.99)
    assert out["state"] == "calm"
    assert out["label"] == "Calm tape — momentum edge intact"


def test_regime_chip_prints_the_producer_state_not_only_the_derived_label(monkeypatch):
    _patch_vol(monkeypatch, VOL_WARNING)
    html = bi._render_html(_payload(bi._regime()))
    en = _strip_en(html)
    assert "Volatility regime: warning signs building" in en
    assert "bond volatility (MOVE) elevated" in en
    zh = _strip_zh(html)
    assert "波动率状态： 风险信号增多" in zh
    assert "债市波动率（MOVE）偏高" in zh
    # the chip is additive — the derived label still prints
    assert "Calm tape — momentum edge intact" in en
    assert "平静行情 — 动量优势完好" in zh


def test_regime_chip_shows_its_own_date_when_it_differs_from_the_tape(monkeypatch):
    # regime read 2026-02-09 vs tape 2026-02-06 -> the chip carries its own date
    _patch_vol(monkeypatch, VOL_WARNING)
    en = _strip_en(bi._render_html(_payload(bi._regime(), as_of="2026-02-06")))
    assert "as of 2026-02-09" in en
    assert _strip_zh(bi._render_html(_payload(bi._regime(),
                                              as_of="2026-02-06"))).count("截至") == 2
    # agreement -> no extra date noise on the chip
    en2 = _strip_en(bi._render_html(_payload(bi._regime(), as_of="2026-02-09")))
    assert "as of 2026-02-09" not in en2
    assert en2.count("2026-02-09") == 1
    assert _strip_zh(bi._render_html(_payload(bi._regime(),
                                              as_of="2026-02-09"))).count("截至") == 1


def test_flag_slug_never_reaches_the_page(monkeypatch):
    _patch_vol(monkeypatch, VOL_WARNING)
    html = bi._render_html(_payload(bi._regime()))
    assert "move_stress" not in html
    assert "fragility_confluence" not in html
    en = _strip_en(html)
    assert "bond volatility (MOVE) elevated" in en
    # the slug "warning" is never printed bare — only inside its mapped phrase
    assert re.search(r"warning(?! signs building)", en) is None


def test_missing_regime_block_renders_the_existing_label_alone(monkeypatch, tmp_path):
    # (a) world_state absent and the legacy regime file unreadable -> fail-soft
    monkeypatch.setattr(nw_read, "load_world_state", lambda *a, **k: None)
    monkeypatch.setattr(cfg, "data_dir", lambda: tmp_path / "data")
    out = bi._regime()
    assert out["state"] == "unknown"
    assert out.get("regime") is None
    assert out.get("flags", []) == []
    html = bi._render_html(_payload(out))
    assert "Regime unknown" in html and "市场状态未知" in html
    assert "Volatility regime" not in html and "波动率状态" not in html
    assert "None" not in html
    # (b) vol block present but carrying no regime key -> copied None, still silent
    _patch_vol(monkeypatch, {"risk_score": -0.18, "vix": 19.99})
    out = bi._regime()
    assert out["regime"] is None and out["flags"] == [] and out["asof"] is None
    html = bi._render_html(_payload(out))
    assert "Calm tape — momentum edge intact" in html
    assert "Volatility regime" not in html
    assert "None" not in html
