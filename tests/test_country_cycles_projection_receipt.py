"""CC-1 — the Country Cycles page states which projected turn windows already lapsed.

Synthetic fixtures only: no site/ or data/ read, no network. The page is rendered
through an Environment that mirrors scripts/build_country_cycles.py:133-141
(FileSystemLoader(templates), autoescape=False, the engine.i18n globals with the same
English-only fallback), so every assertion is about the committed template bytes and
the builder's own projection fields — `overdue`, `overdue_frac`, `last_confirmed_t`.
"""
from __future__ import annotations

import copy
import inspect
import re
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.build_country_cycles import (  # noqa: E402
    _hazard_availability,
    _projection_receipt,
)

_SECTION_OPEN = '<section class="cyc-grp" id="cc-receipt">'
_TWIN_RE = re.compile(
    r'<span class="l-en">(.*?)</span>\s*<span class="l-zh">(.*?)</span>', re.S)
_WITHHELD = {"unavailable": True, "unavailable_reason": "non_monotone_cdf"}


def _data(*records: dict) -> dict:
    return {"meta": {"asOf": "2026-10-17"}, "sectors": list(records), "baskets": []}


def _record(rid="ewu", name="🇬🇧 United Kingdom", name_zh="🇬🇧 英国", overdue=True,
            turn="peak", central="2020-09", anchor="2020-03", frac=15.841,
            hazard=None) -> dict:
    """Shaped like the committed ewu row, period_yrs included, so a helper that read
    the FULL-cycle median instead of overdue_frac cannot pass."""
    rec = {"id": rid, "name": name, "name_zh": name_zh,
           "proj": {"nextTurn": turn, "central": central, "low": "2020-06",
                    "high": "2021-05", "overdue": overdue, "overdue_frac": frac,
                    "last_confirmed_t": anchor, "tilt": "mixed",
                    "period_yrs": {"median": 0.83, "lo": 0.39, "hi": 2.3}}}
    if hazard is not None:
        rec["now"] = {"hazard": hazard}
    return rec


def _render(receipt: dict, hazard: dict) -> str:
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=False)
    try:
        from engine import i18n
        env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    except Exception:  # noqa: BLE001 — mirror the builder's English-only fallback
        env.globals.update(td=lambda en: en, tr=lambda en: en, t=lambda en, zh="": en)
    return env.get_template("country_cycles.html.j2").render(
        projection_receipt=receipt, hazard_availability=hazard)


def _section(html: str) -> str:
    start = html.index(_SECTION_OPEN)
    end = html.index("</section>", start) + len("</section>")
    return html[start:end]


def test_lapsed_row_renders_the_committed_ewu_receipt():
    data = _data(_record(hazard=_WITHHELD))
    sec = _section(_render(_projection_receipt(data), _hazard_availability(data)))
    assert "Projected peak window lapsed" in sec
    assert "推演顶部窗口已过期" in sec
    assert "centred 2020-09" in sec
    assert "anchored on the turn confirmed 2020-03" in sec
    assert "15.8× the median half-cycle" in sec
    assert "1 of 1 projected windows have already lapsed" in sec
    assert "0.83" not in sec                      # period_yrs.median never reaches the page


def test_forward_window_is_not_marked_lapsed():
    data = _data(_record(rid="ewt", name="🇹🇭 Thailand", name_zh="🇹🇭 泰国",
                         overdue=False, central="2026-12", anchor="2026-07", frac=0.602))
    receipt = _projection_receipt(data)
    assert receipt["n_lapsed"] == 0 and receipt["lapsed"] == []
    assert receipt["n_total"] == 1
    sec = _section(_render(receipt, _hazard_availability(data)))
    assert "0 of 1 projected windows have already lapsed" in sec
    assert "<details>" not in sec
    assert "cyc-facts" not in sec
    assert "2026-12" not in sec
    assert "the median half-cycle" not in sec


def test_summary_counts_lapsed_vs_total():
    data = _data(_record(),
                 _record(rid="eido", name="🇮🇩 Indonesia", name_zh="🇮🇩 印度尼西亚",
                         turn="trough", central="2018-10", anchor="2018-02", frac=13.652),
                 _record(rid="ewt", name="🇹🇭 Thailand", name_zh="🇹🇭 泰国",
                         overdue=False, central="2026-12", anchor="2026-07", frac=0.602))
    receipt = _projection_receipt(data)
    assert (receipt["n_lapsed"], receipt["n_total"]) == (2, 3)
    sec = _section(_render(receipt, _hazard_availability(data)))
    assert "2 of 3 projected windows have already lapsed" in sec
    assert "3 个推演窗口中已有 2 个过期" in sec


def test_missing_proj_keys_render_nothing():
    data = _data({"id": "bare", "name": "No proj at all"},
                 {"id": "empty", "name": "Empty proj", "proj": {}},
                 {"id": "nullish", "name": "Null verdict",
                  "proj": {"overdue": None, "central": "2020-01", "overdue_frac": 1.0}})
    receipt = _projection_receipt(data)
    assert receipt == {}
    html = _render(receipt, _hazard_availability(data))
    assert "cc-receipt" not in html


def test_lapsed_rows_are_ordered_most_overdue_first():
    data = _data(_record(rid="tur", name="🇹🇷 Turkey",
                         name_zh="🇹🇷 土耳其", frac=10.824),
                 _record(),
                 _record(rid="eido", name="🇮🇩 Indonesia", name_zh="🇮🇩 印度尼西亚",
                         frac=13.652))
    receipt = _projection_receipt(data)
    assert [row["id"] for row in receipt["lapsed"]] == ["ewu", "eido", "tur"]
    sec = _section(_render(receipt, {}))
    places = [sec.index(row["name"]) for row in receipt["lapsed"]]
    assert places == sorted(places)
    tied = _projection_receipt(_data(
        _record(rid="lo", name="Rounds low", name_zh="低", frac=1.999),
        _record(rid="hi", name="Rounds high", name_zh="高", frac=2.04)))
    assert [row["id"] for row in tied["lapsed"]] == ["hi", "lo"]   # RAW frac, not rounded
    noverdict = _projection_receipt(_data(_record(frac=None), _record(rid="abc", frac=2.0)))
    assert [row["id"] for row in noverdict["lapsed"]] == ["abc", "ewu"]


def test_both_languages_present_and_distinct():
    data = _data(_record(hazard=_WITHHELD))
    sec = _section(_render(_projection_receipt(data), _hazard_availability(data)))
    twins = _TWIN_RE.findall(sec)
    assert len(twins) >= 5
    assert sec.count('class="l-en"') == len(twins)
    assert sec.count('class="l-zh"') == len(twins)
    for en, zh in twins:
        assert en != zh, f"l-zh span copies the English text: {en!r}"
    assert "Next" not in sec
    assert "下次" not in sec


def test_builder_helper_reads_only_the_model():
    for fn in (_projection_receipt, _hazard_availability):
        src = inspect.getsource(fn)
        for needle in ("open(", "read_text", "json.load", "Path(", "period_yrs"):
            assert needle not in src, f"{fn.__name__} reaches for {needle!r}"
    data = _data(_record(hazard=_WITHHELD),
                 _record(rid="ewl", name="🇨🇭 Switzerland", name_zh="🇨🇭 瑞士",
                         frac=0.4, hazard={"1m": {"p": 0.3511, "cell_verdict": "PASS"}}))
    scratch = copy.deepcopy(data)
    _projection_receipt(scratch)
    assert scratch == data
    _hazard_availability(scratch)
    assert scratch == data
    from scripts import build_country_cycles as builder
    assert "projection_receipt=_projection_receipt(data)" in inspect.getsource(builder.main)
