"""W21B-4: the impulse card prints its committed evidence chips.

The producer already ships ``price``, ``rvol`` and ``off_high`` on every card
(``scripts/build_impulse.py`` ``_card``), but the template printed no last
close, only one of the two volume legs the legend names, and no distance off
the 52-week high. These tests render synthetic buy-lane cards shaped like the
committed UNH row through the real ``_render_html`` and pin the three new
chips (EN and zh legs), the ``is not none`` guards (0.0 is a real value), and
the card's single-anchor shatter law.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import build_impulse as bi  # noqa: E402


def _unh_card(**overrides) -> dict:
    """One buy-lane card shaped like the committed UNH row of impulse.json."""
    card = {
        "ticker": "UNH",
        "name": "UnitedHealth Group",
        "sector": "Health Care",
        "price": 395.62,
        "impulse_score": 100,
        "state": "EARLY_IGNITION",
        "just_starting": True,
        "days_igniting": 1,
        "accel_z": 0.8,
        "vel_pct": 0.016,
        "impulse_macd": 1.32,
        "eff_ratio": 0.56,
        "trend_vel": 0.82,
        "runup_5": 0.052,
        "runup_20": 0.054,
        "dist_50": 0.023,
        "dist_200": 0.107,
        "off_high": -0.0933,
        "rvol": 1.57,
        "vol_vel": 1.54,
        "adv20": 2143374563.0,
        "spark_svg": "",
        "note": "Igniting now — accel z +0.8, volume +54%, only +5% over 20d.",
        "note_zh": "刚刚点火 — 加速度 z +0.8，量+54%，20日仅 +5%。",
    }
    card.update(overrides)
    return card


def _payload(card: dict) -> dict:
    """Minimal status-ok payload rendering exactly one buy-lane card."""
    return {
        "status": "ok",
        "as_of": "2026-10-14",
        "universe": 1502,
        "counts": {"buy": 1, "igniting": 0, "extended": 0,
                   "coiling": 0, "fading": 0},
        "regime": {"state": "calm", "label": "Calm tape",
                   "label_zh": "平静行情", "vix": 19.99},
        "buy": [card],
        "igniting": [],
        "coiling": [],
        "extended": [],
        "fading": [],
        "cfg": {"min_dollar_vol": 3000000.0},
    }


def _card_html(card: dict) -> str:
    """Render the one-card payload; return the single ic-card anchor block."""
    html = bi._render_html(_payload(card))
    blocks = re.findall(r'<a class="ic-card".*?</a>', html, flags=re.S)
    assert len(blocks) == 1, f"expected exactly one card, got {len(blocks)}"
    return blocks[0]


def test_card_prints_the_last_close():
    # The committed UNH row carries price 395.62; the card prints it as a chip.
    out = _card_html(_unh_card())
    assert "close 395.62" in out
    assert "收盘 395.62" in out


def test_card_prints_relative_volume_alongside_the_volume_ratio():
    # The legend names two volume legs; BOTH are visible on the card.
    out = _card_html(_unh_card())
    assert "📊 +54%" in out            # the existing vol_vel leg stays
    assert "rel. volume 1.6×" in out   # the committed rvol leg
    assert "相对成交量 1.6倍" in out


def test_card_prints_distance_off_the_52_week_high():
    out = _card_html(_unh_card())
    assert "-9% vs 52-week high" in out
    assert "距52周高点 -9%" in out
    # 0.0 is a real value (the committed IFF case): print it, never drop it.
    out_zero = _card_html(_unh_card(off_high=0.0))
    assert "0% vs 52-week high" in out_zero


def test_null_evidence_renders_todays_card():
    card = _unh_card(price=None, rvol=None, off_high=None)
    out = _card_html(card)
    # The four existing chips are unchanged...
    assert "⚡ +0.8" in out
    assert "📊 +54%" in out
    assert "+5%/20d" in out
    assert "+2% vs 50d" in out
    # ...and none of the three new labels nor a raw None leaks.
    for absent in ("close", "rel. volume", "52-week high",
                   "收盘", "相对成交量", "距52周高点", "None"):
        assert absent not in out


def test_card_stays_a_single_anchor():
    # The card is an <a>; chips are spans — never nest an anchor (:4-5 law).
    out = _card_html(_unh_card())
    assert out.count("<a ") == 1
    assert out.count("</a>") == 1
