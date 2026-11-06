"""SPEC W21B-3 — the Impulse strip dates the read: build stamp + tape coverage.

The committed artifact carries as_of (the bar session date), generated_utc (when
the page was built) and with_volume/universe (how much of the tape could be
scored). Before this spec the strip printed only as_of, while the caveat claimed
a nightly rebuild — false for a stale build. Synthetic payloads only, rendered
through scripts.build_impulse._render_html; no network, no site/, no data/.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import build_impulse as bi  # noqa: E402


def _card(tk: str, state: str) -> dict:
    return dict(ticker=tk, name=f"{tk} Corp", sector="Industrials", state=state,
                impulse_score=50, spark_svg=None, accel_z=0.4, vol_vel=1.2,
                runup_20=0.05, dist_50=0.02, days_igniting=0,
                note="Synthetic note.", note_zh="合成备注。")


def _payload(**over) -> dict:
    p = {
        "status": "ok",
        "as_of": "2026-02-06",
        "generated_utc": "2026-02-09 21:00 UTC",
        "universe": 40,
        "with_volume": 38,
        "n_buy": 1,
        "regime": {"state": "calm", "label": "Calm tape", "label_zh": "平静行情",
                   "vix": 20.0, "risk_score": -0.1, "calm": True},
        "counts": {"buy": 1, "igniting": 2, "extended": 1, "coiling": 1,
                   "fading": 1},
        "buy": [_card("B0", "EARLY_IGNITION")],
        "igniting": [_card("I0", "IGNITING"), _card("I1", "IGNITING")],
        "extended": [_card("E0", "EXTENDED_RUN")],
        "coiling": [_card("C0", "COILING")],
        "fading": [_card("F0", "FADING")],
        "cfg": {"vel_fast": 5, "vel_slow": 20},
    }
    p.update(over)
    return p


def _strip(html: str) -> str:
    m = re.search(r'<div class="strip">.*?</div>', html, flags=re.S)
    assert m, "no strip region rendered"
    return m.group(0)


def _caveat(html: str) -> str:
    m = re.search(r'<p class="cav">.*?</p>', html, flags=re.S)
    assert m, "no caveat paragraph rendered"
    return m.group(0)


def test_strip_prints_the_committed_build_stamp():
    # the artifact's generated_utc, not a template-side clock, appears in the strip
    html = bi._render_html(_payload())
    strip = _strip(html)
    assert "2026-02-09 21:00 UTC" in strip
    assert "Built" in strip and "构建于" in strip


def test_strip_prints_the_volume_coverage_pair():
    html = bi._render_html(_payload())
    strip = _strip(html)
    assert "含成交量数据" in strip
    m = re.search(r'With volume data.*?38 / 40\s*</span>', strip, flags=re.S)
    assert m, "no single .stat span carrying the coverage pair 38 / 40"


def test_zero_with_volume_still_prints_the_pair():
    # 0 is a real coverage value, not an absent one — the guard must keep it.
    html = bi._render_html(_payload(with_volume=0))
    strip = _strip(html)
    m = re.search(r'With volume data.*?0 / 40\s*</span>', strip, flags=re.S)
    assert m, "coverage 0 / 40 must still render"


def test_null_with_volume_prints_no_pair_or_none():
    html = bi._render_html(_payload(with_volume=None))
    strip = _strip(html)
    assert "With volume data" not in strip
    assert " / 40" not in strip
    assert "None" not in html


def test_caveat_no_longer_claims_a_night_before_tape():
    html = bi._render_html(_payload())
    assert "night-before tape" not in html
    cav = _caveat(html)
    assert "the public site rebuilds once daily after the US close" not in cav
    assert ("the strip above prints the bars\u2019 session date and the "
            "page\u2019s build time") in cav
    assert "前一晚" not in cav
    assert "实时" not in cav
    assert "申报" not in cav
    assert "上方信息栏列出K线的交易日与本页构建时间" in cav


def test_missing_stamp_renders_todays_strip():
    # absent generated_utc / with_volume: fail soft back to exactly today's strip
    p = _payload()
    del p["generated_utc"]
    del p["with_volume"]
    html = bi._render_html(p)
    strip = _strip(html)
    assert "Built" not in strip
    assert "With volume data" not in strip
    assert "None" not in html
    assert 'As of</span><span class="l-zh">截至</span> 2026-02-06' in strip
