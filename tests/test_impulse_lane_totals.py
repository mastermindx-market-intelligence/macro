"""SPEC W21B-2 — the Impulse page section headers must carry true lane totals.

The builder caps each lane list (scripts/build_impulse.py _CAPS) but also ships
`counts` with the un-capped totals. Before this spec the igniting/fading headers
printed only the capped length, so a reader could not see how wide the roll-over
or how deep the accelerating bench really is. Synthetic payloads only, rendered
through the real builder template; no network, no site/, no data/.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import build_impulse as bi  # noqa: E402


def _card(tk: str, state: str) -> dict:
    """One synthetic card carrying every field the card macro reads."""
    return dict(ticker=tk, name=f"{tk} Corp", sector="Industrials", state=state,
                impulse_score=50, spark_svg=None, accel_z=0.4, vol_vel=1.2,
                runup_20=0.05, dist_50=0.02, days_igniting=0,
                note="Synthetic note.", note_zh="合成备注。")


def _cards(lane: str, n: int, state: str) -> list[dict]:
    return [_card(f"{lane}{i}", state) for i in range(n)]


def _payload(**over) -> dict:
    p = {
        "status": "ok",
        "as_of": "2026-02-06",
        "generated_utc": "2026-02-09 21:00 UTC",
        "universe": 40,
        "with_volume": 38,
        "n_buy": 2,
        "regime": {"state": "calm", "label": "Calm tape", "label_zh": "平静行情",
                   "vix": 20.0, "risk_score": -0.1, "calm": True},
        "counts": {"buy": 2, "igniting": 9, "extended": 1, "coiling": 3,
                   "fading": 7},
        "buy": _cards("B", 2, "EARLY_IGNITION"),
        "igniting": _cards("I", 3, "IGNITING"),
        "extended": _cards("E", 1, "EXTENDED_RUN"),
        "coiling": _cards("C", 3, "COILING"),
        "fading": _cards("F", 3, "FADING"),
        "cfg": {"vel_fast": 5, "vel_slow": 20},
    }
    p.update(over)
    return p


def _sec_cnt(html: str, en_label: str) -> str:
    """The rendered text of the .cnt span that follows the h2 naming en_label."""
    i = html.find(en_label)
    assert i != -1, f"section label not found: {en_label}"
    seg = html[i:i + 1500]
    m = re.search(r'<span class="cnt">(.*?)</span>', seg, flags=re.S)
    assert m, f"no .cnt span after label {en_label}"
    return re.sub(r"<[^>]+>", "", m.group(1)).strip()


def _strip(html: str) -> str:
    m = re.search(r'<div class="strip">.*?</div>', html, flags=re.S)
    assert m, "no strip region rendered"
    return m.group(0)


def test_fading_header_prints_the_total_the_artifact_carries():
    # counts.fading = 7 with three capped cards: the header must read "3 / 7".
    html = bi._render_html(_payload())
    assert _sec_cnt(html, "Fading — rolling over") == "3 / 7"


def test_igniting_header_agrees_with_the_strip():
    # counts.igniting = 9 with three capped cards: header "3 / 9", strip "9".
    html = bi._render_html(_payload())
    assert _sec_cnt(html, "Accelerating — momentum building") == "3 / 9"
    assert "<b>9</b>" in _strip(html)


def test_strip_carries_a_fading_stat():
    html = bi._render_html(_payload())
    strip = _strip(html)
    m = re.search(r'Fading</span>.*?<b>7</b>', strip, flags=re.S)
    assert m, "no Fading stat with value 7 in the strip"
    assert "转弱" in strip


def test_total_is_omitted_when_the_lane_is_not_capped():
    # extended 1 with one card renders "1", never "1 / 1"; an uncapped igniting
    # or fading lane must omit the pair too (kills the always-print mutant).
    html = bi._render_html(_payload())
    assert _sec_cnt(html, "Already ran — no entry") == "1"
    assert "1 / 1" not in html
    p = _payload(counts={"buy": 2, "igniting": 3, "extended": 1, "coiling": 3,
                         "fading": 3})
    html2 = bi._render_html(p)
    assert _sec_cnt(html2, "Accelerating — momentum building") == "3"
    assert _sec_cnt(html2, "Fading — rolling over") == "3"
    assert "3 / 3" not in html2


def test_null_state_page_is_unchanged():
    # status != "ok": the empty banner renders and no counts access raises.
    html = bi._render_html({"status": "no_data"})
    assert "Impulse data is not available for this build." in html
    assert "本次构建暂无冲量数据。" in html
    assert 'class="strip"' not in html
    assert 'class="cnt"' not in html
