"""CC-2 — the Country Cycles page words the withheld turn-hazard instead of hiding it.

Synthetic fixtures only: no site/ or data/ read, no network. Rendered through an
Environment mirroring scripts/build_country_cycles.py:133-141 (FileSystemLoader,
autoescape=False, the engine.i18n globals with the same English-only fallback). The
producer records `now.hazard.unavailable_reason` as a machine token; the page may only
ever show the builder's fixed human wording for it.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.build_country_cycles import _hazard_availability  # noqa: E402

_SECTION_OPEN = '<section class="cyc-grp" id="cc-receipt">'
_TWIN_RE = re.compile(
    r'<span class="l-en">(.*?)</span>\s*<span class="l-zh">(.*?)</span>', re.S)
_REASON_EN = ("the 1-, 3- and 6-month probabilities did not form a rising sequence, "
              "so none is shown")
_REASON_ZH = "1、3、6 个月概率未构成递增序列，故不予显示"


def _data(*records: dict) -> dict:
    return {"meta": {"asOf": "2026-10-17"}, "sectors": list(records), "baskets": []}


def _withheld(rid="ewu", name="🇬🇧 United Kingdom", name_zh="🇬🇧 英国",
              token="non_monotone_cdf") -> dict:
    """Shaped like the committed ewu hazard block: computed, then withheld."""
    return {"id": rid, "name": name, "name_zh": name_zh,
            "now": {"hazard": {"unavailable": True, "unavailable_reason": token}}}


def _passing(rid="ewl", name="🇨🇭 Switzerland", name_zh="🇨🇭 瑞士") -> dict:
    """Shaped like the committed ewl hazard block: PASS cells, so it is shown."""
    cell = {"source": "MODEL", "cell_verdict": "PASS"}
    return {"id": rid, "name": name, "name_zh": name_zh,
            "now": {"hazard": {"direction": "down", "turn_kind": "trough",
                               "1m": dict(cell, p=0.3511),
                               "3m": dict(cell, p=0.4),
                               "6m": dict(cell, p=0.5882)}}}


def _render(hazard: dict) -> str:
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=False)
    try:
        from engine import i18n
        env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    except Exception:  # noqa: BLE001 — mirror the builder's English-only fallback
        env.globals.update(td=lambda en: en, tr=lambda en: en, t=lambda en, zh="": en)
    return env.get_template("country_cycles.html.j2").render(
        projection_receipt={}, hazard_availability=hazard)


def _section(html: str) -> str:
    start = html.index(_SECTION_OPEN)
    end = html.index("</section>", start) + len("</section>")
    return html[start:end]


def _tol_line(sec: str) -> str:
    marker = '<div class="cyc-tol-line">'
    start = sec.index(marker)
    end = sec.index("</div>", start) + len("</div>")
    return sec[start:end]


def test_withheld_reason_is_worded_not_tokened():
    data = _data(_withheld())
    avail = _hazard_availability(data)
    assert avail["n_withheld"] == 1 and avail["n_available"] == 0
    assert avail["reasons"] == [{"en": _REASON_EN, "zh": _REASON_ZH, "n": 1}]
    html = _render(avail)
    line = _tol_line(_section(html))
    assert _REASON_EN in line
    assert _REASON_ZH in line
    assert "non_monotone_cdf" not in html


def test_counts_available_vs_withheld():
    data = _data(_passing(),
                 _passing(rid="ewn", name="🇳🇱 Netherlands", name_zh="🇳🇱 荷兰"),
                 _passing(rid="ews", name="🇸🇬 Singapore", name_zh="🇸🇬 新加坡"),
                 _withheld(),
                 _withheld(rid="tur", name="🇹🇷 Turkey", name_zh="🇹🇷 土耳其"))
    avail = _hazard_availability(data)
    assert (avail["n_available"], avail["n_withheld"], avail["n_total"]) == (3, 2, 5)
    line = _tol_line(_render(avail))
    assert "available for 3 of 5 markets" in line
    assert "withheld for 2" in line
    assert "5 个市场中 3 个提供经校准的转折概率" in line
    assert "2 个未提供" in line


def test_pass_cell_records_are_not_listed_as_withheld():
    data = _data(_passing())
    avail = _hazard_availability(data)
    assert [rec["id"] for rec in avail["available"]] == ["ewl"]
    assert avail["withheld"] == [] and avail["n_available"] == 1
    line = _tol_line(_render(avail))
    assert "available for 1 of 1 markets" in line
    assert "(🇨🇭 Switzerland)" in line
    assert "🇨🇭 瑞士" in line
    assert "ewl" not in [rec["id"] for rec in avail["withheld"]]


def test_unknown_reason_token_renders_no_clause():
    data = _data(_withheld(token="weird_token"))
    avail = _hazard_availability(data)
    assert avail["n_withheld"] == 1 and avail["reasons"] == []
    html = _render(avail)
    line = _tol_line(_section(html))
    assert "weird_token" not in html
    assert _REASON_EN not in line
    assert "withheld for 1" in line


def test_no_hazard_block_renders_nothing():
    data = _data({"id": "nohaz", "name": "No hazard", "now": {"phase": "Peak", "pos": 40}},
                 {"id": "nonow", "name": "No now dict"})
    assert _hazard_availability(data) == {}
    html = _render(_hazard_availability(data))
    assert "cc-receipt" not in html
    assert "cyc-tol-line" not in html


def test_zh_span_present_and_distinct():
    data = _data(_passing(), _withheld())
    line = _tol_line(_render(_hazard_availability(data)))
    twins = _TWIN_RE.findall(line)
    assert len(twins) >= 3
    assert line.count('class="l-en"') == len(twins)
    assert line.count('class="l-zh"') == len(twins)
    for en, zh in twins:
        assert en != zh, f"l-zh span copies the English text: {en!r}"


def test_display_only_framing_is_kept():
    data = _data(_passing(), _withheld())
    line = _tol_line(_render(_hazard_availability(data)))
    assert "never a signal" in line
    assert "绝非信号" in line
