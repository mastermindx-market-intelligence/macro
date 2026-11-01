"""Membership vintage on the China narrative radar (W30-L36 SPEC 2).

The page's `as_of` is the last close date (engine/china_narrative_radar.py),
while basket membership comes from data/baskets_china_ths/membership.json whose
top-level "version" is the newest THS snapshot date. These tests pin the pure
helper `membership_as_of()` plus the sub-line and footer that print both dates.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from engine.narrative_radar_fields import membership_as_of

_ROOT = Path(__file__).resolve().parent.parent
_AS_OF = "2026-10-16"
_VINTAGE = "2026-06-30"
_ABSENT = object()
_MEMBERS = [{"ticker": "002639.SZ", "name_zh": "雪人集团", "ret_63d": 33.39}]
_BASKET = {
    "id": "ice", "name": "Ice & Snow Industry", "name_zh": "冰雪产业",
    "category": "Consumer", "category_zh": "消费", "ret_63d": 41.2, "rank_63d": 1,
    "above_200d": False, "global_ai": None, "top_members": _MEMBERS,
    "state": {"score": 42.0, "label": "Recovering", "label_zh": "修复回升",
              "dist_200d_pct": -0.0, "drawdown_pct": -10.9},
}


def _render(mv=_ABSENT) -> str:
    data = {"as_of": _AS_OF, "provenance": {}, "baskets": [dict(_BASKET)]}
    if mv is not _ABSENT:
        data["membership_as_of"] = mv
    env = Environment(loader=FileSystemLoader(str(_ROOT / "templates")), autoescape=True)
    return env.get_template("china_narrative_radar.html.j2").render(
        data=data, data_json=json.dumps(data, ensure_ascii=False),
        generated_utc="TEST", C={})


def _between(html: str, start: str, end: str) -> str:
    i = html.index(start)
    return html[i + len(start):html.index(end, i)]


def _sub(html: str) -> str:
    return _between(html, '<span class="sub">', '</div>\n  <div class="headline-strip">')


def _foot(html: str) -> str:
    return _between(html, '<div class="foot">', '</div>\n</div>')


def _en_view(seg: str) -> str:
    return re.sub(r'<span class="l-zh">.*?</span>', '', seg, flags=re.DOTALL)


def _zh_view(seg: str) -> str:
    return re.sub(r'<span class="l-en[^"]*">.*?</span>', '', seg, flags=re.DOTALL)


def _single_fragment(absent: str, present: str) -> str:
    """Prove present == absent with exactly ONE contiguous fragment inserted."""
    i = 0
    while i < len(absent) and i < len(present) and absent[i] == present[i]:
        i += 1
    j = 0
    while (j < len(absent) - i and j < len(present) - i
           and absent[len(absent) - 1 - j] == present[len(present) - 1 - j]):
        j += 1
    assert i + j == len(absent), "present is not absent plus one contiguous fragment"
    frag = present[i:len(present) - j]
    assert frag, "present equals absent: nothing was inserted"
    return frag


def test_membership_as_of_returns_the_version_verbatim():
    assert membership_as_of({"version": "2026-06-30", "baskets": {}}) == "2026-06-30"
    for raw in (None, {}, {"version": None}, {"version": "  "}, {"version": 5},
                {"version": []}, []):
        assert membership_as_of(raw) is None, raw


def test_sub_line_prints_both_dates():
    sub = _sub(_render(_VINTAGE))
    i_close = sub.index(_AS_OF)
    assert "membership snapshot" in sub and "成分快照" in sub
    assert sub.index(_VINTAGE) > i_close


def test_footer_names_the_snapshot_and_the_close_date():
    foot = _foot(_render(_VINTAGE))
    assert "THS snapshot dated" in foot and "同花顺快照" in foot
    assert _VINTAGE in foot
    assert "closes run to" in foot and "收盘价截至" in foot
    assert foot.index("Built") > max(foot.index("THS snapshot dated"),
                                     foot.index("closes run to"), foot.index(_VINTAGE))


def test_absent_vintage_adds_nothing():
    absent = _render()
    assert absent == _render(None)
    for html in (absent, _render(None)):
        for seg in (_sub(html), _foot(html)):
            for token in ("membership snapshot", "成分快照", "THS snapshot dated",
                          "同花顺快照", "None"):
                assert token not in seg
    for html in (absent,):
        assert not re.search(r"\n[ \t]*\n", _sub(html))
        assert not re.search(r"\n[ \t]*\n", _foot(html))
    present = _render(_VINTAGE)
    _single_fragment(_sub(absent), _sub(present))
    _single_fragment(_foot(absent), _foot(present))


def test_inserted_fragments_claim_no_recency():
    absent = _render()
    present = _render(_VINTAGE)
    frags = (_single_fragment(_sub(absent), _sub(present)),
             _single_fragment(_foot(absent), _foot(present)))
    for frag in frags:
        low = frag.lower()
        for token in ("current", "live", "latest", "实时", "最新", "当前"):
            assert token not in low, (token, frag)


def test_en_and_zh_views_each_carry_one_language():
    html = _render(_VINTAGE)
    for seg, en_tok, zh_tok in ((_sub(html), "membership snapshot", "成分快照"),
                                (_foot(html), "THS snapshot dated", "同花顺快照")):
        en, zh = _en_view(seg), _zh_view(seg)
        assert en_tok in en and zh_tok not in en
        assert zh_tok in zh and en_tok not in zh
        assert _AS_OF in en and _VINTAGE in en
        assert _AS_OF in zh and _VINTAGE in zh
