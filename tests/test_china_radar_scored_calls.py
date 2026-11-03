"""China Divergence Radar — SPEC 1: the scored calls behind the ledger headline.

Render-only tests over ``templates/china_radar.html.j2``: synthetic payloads, no
``data/`` read, no ``site/`` write, no builder ``build()``/``main()`` call.
"""
from __future__ import annotations

import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

TEMPLATE = "china_radar.html.j2"

# The two resolved calls quoted from the committed ledger
# (data/china_radar/ledger.parquet via engine/china_radar_ledger.track_record()).
MISS_ROW = {
    "fired_date": "2026-07-17", "signal_key": "credit_impulse",
    "sector_en": "Banks", "sector_zh": "银行", "sign": "negative",
    "rs_at_fire": 0.63, "fwd_rel": 16.94, "status": "miss", "family": None,
}
HIT_ROW = {
    "fired_date": "2026-07-01", "signal_key": "sector_flow",
    "sector_en": "Semiconductors", "sector_zh": "Semiconductors",
    "sign": "negative", "rs_at_fire": 67.85, "fwd_rel": -21.13,
    "status": "hit", "family": None,
}
# The committed cross-venue call: its rs_at_fire carries the pair z, not a sector RS
# (engine/china_radar.py:718-719), and its outcome is the pair's own convergence.
VENUE_ROW = {
    "fired_date": "2026-07-07", "signal_key": "venue_offshore_gap",
    "family": "venue", "sector_en": "CSI 300 (onshore)",
    "sector_zh": "沪深300（境内）", "sign": "positive",
    "rs_at_fire": 5.5, "fwd_rel": -1.75, "status": "miss",
}

FOOTNOTE_EN = "not a CSI 300 relative return"
FOOTNOTE_ZH = "不是相对沪深300的收益"
WARMUP_EN = "The ledger starts logging"
WARMUP_ZH = "台账从今日起记录背离"


def _make_env():
    """Jinja env mirroring scripts/build_china_radar.py (shape copied from
    tests/test_china_radar_venue.py TestTemplateRender._make_env)."""
    env = Environment(loader=FileSystemLoader(str(_ROOT / "templates")), autoescape=False)
    try:
        from engine import i18n
        env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    except Exception:  # noqa: BLE001
        env.globals.update(td=lambda en: en, tr=lambda en: en, t=lambda en, zh="": en)
    return env


def _radar():
    return {
        "schema": "china_radar.v1", "is_context_only": True,
        "asof": "2026-07-06", "built": "2026-07-06T00:00:00Z",
        "divergences": [], "in_line": [], "n_active": 0, "n_pairs": 0,
        "disclaimer_en": "Context only.", "disclaimer_zh": "仅供参考。",
    }


def _open_rows(count=21):
    """`count` open calls, every fired_date newer than the resolved ones."""
    return [{
        "fired_date": f"2026-09-{i + 1:02d}", "signal_key": f"open_signal_{i:02d}",
        "sector_en": "Sector", "sector_zh": "板块", "sign": "positive",
        "rs_at_fire": None, "fwd_rel": None, "status": "open", "family": None,
    } for i in range(count)]


def _ledger(rows):
    """The committed strip: 52 logged, 2 resolved, 50% held, 50 open."""
    return {
        "schema": "china_radar_ledger.v1", "is_context_only": True,
        "n_total": 52, "n_resolved": 2, "hit_rate": 0.5, "n_open": 50,
        "rows": rows,
    }


def _render(ledger, ic=None):
    return _make_env().get_template(TEMPLATE).render(
        radar=_radar(), ledger=ledger, ic=ic)


def test_scored_table_renders_the_resolved_calls_the_headline_counts():
    """20 newer open rows must not push the two resolved calls off the page."""
    html = _render(_ledger(_open_rows() + [MISS_ROW, HIT_ROW]))
    assert html.count('class="b-miss"') >= 1
    assert html.count('class="b-hit"') >= 1
    assert "+16.9" in html           # MISS_ROW fwd_rel 16.94
    assert "-21.1" in html           # HIT_ROW fwd_rel -21.13
    assert "+0.6" in html            # MISS_ROW rs_at_fire 0.63, one decimal
    assert "+0.63" not in html       # ...and never two
    assert "+67.8" in html           # HIT_ROW rs_at_fire 67.85
    assert "+67.85" not in html
    assert "credit_impulse" in html and "sector_flow" in html


def test_rs_at_fire_is_suppressed_for_venue_rows():
    """A venue row's rs_at_fire is the pair z — never printed as an entry number."""
    html = _render(_ledger(_open_rows() + [MISS_ROW, HIT_ROW, VENUE_ROW]))
    assert "venue_offshore_gap" in html      # the venue call IS scored and shown
    assert "+5.5" not in html                # ...but its rs_at_fire is not
    assert "+5.50" not in html
    assert "-1.8" in html                    # its own outcome still prints
    assert FOOTNOTE_EN in html and FOOTNOTE_ZH in html


def test_open_table_still_renders_and_is_labelled():
    """Both tables carry a bilingual label; the open table keeps its rows[:20] cap."""
    html = _render(_ledger(_open_rows() + [MISS_ROW, HIT_ROW]))
    assert "Scored calls" in html and "已评分判断" in html
    assert "Open calls" in html and "未结判断" in html
    assert "open_signal_19" in html          # 20th open row: inside the cap
    assert "open_signal_20" not in html      # 21st open row: outside it


def test_no_scored_rows_renders_no_empty_table():
    """All-open ledger: no scored table shell; the open table is still labelled."""
    html = _render(_ledger(_open_rows()))
    assert html.count('<table class="data">') == 1
    assert "Scored calls" not in html and "已评分判断" not in html
    assert "RS at fire" not in html
    assert "Open calls" in html and "未结判断" in html


def test_ledger_none_and_zero_paths_unchanged():
    """ledger=None and n_total=0 keep the warm-up callout and render no table."""
    for ledger in (None, {"n_total": 0}):
        html = _render(ledger)
        assert WARMUP_EN in html and WARMUP_ZH in html
        assert '<table class="data">' not in html
        assert "Scored calls" not in html and "已评分判断" not in html


def test_open_table_lists_only_open_calls():
    """Resolved calls sit only in the scored table, never under the Open calls label."""
    html = _render(_ledger(_open_rows(2) + [MISS_ROW, HIT_ROW]))
    i = html.find("未结判断")
    assert i > 0
    tail = html[i:html.find("</table>", i)]
    assert "open_signal_01" in tail
    assert MISS_ROW["signal_key"] not in tail and HIT_ROW["signal_key"] not in tail
    assert 'class="b-' not in tail


def test_all_resolved_ledger_renders_no_open_table():
    """A ledger with no open calls prints no empty Open calls table."""
    html = _render(_ledger([MISS_ROW, HIT_ROW]))
    assert "Open calls" not in html and "未结判断" not in html
    assert html.count('<table class="data">') == 1
