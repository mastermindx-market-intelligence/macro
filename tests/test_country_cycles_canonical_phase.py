"""CC-4 — canonical (ontology) phase + position on country_cycles.html (SPEC CC-4).

now.phase_v2 / now.pos_v2 are the model's canonical read; the cards paint the wheel
phase. The builder maps phase tokens through _PHASE_LABEL_COPY (a copy of the shipped
table at templates/sector_cycles.js:123-126) and rounds positions like the drawer's
JS Math.round (int(v + 0.5), NOT Python round). Synthetic fixtures only; the template
is rendered through an Environment mirroring scripts/build_country_cycles.py:133-141.
"""
from __future__ import annotations

import copy
import inspect
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jinja2 import Environment, FileSystemLoader  # noqa: E402

from scripts.build_country_cycles import (_canonical_phase, _fx_contribution,  # noqa: E402
                                          main)


def _env():
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=False)
    try:
        from engine import i18n
        env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    except Exception:  # noqa: BLE001 — mirror the builder's degrade path
        env.globals.update(td=lambda en: en, tr=lambda en: en, t=lambda en, zh="": en)
    return env


def _render(cd):
    return _env().get_template("country_cycles.html.j2").render(canonical_phase=cd)


def _section(html):
    i = html.index('id="cc-canon"')
    return html[i:html.index("</section>", i)]


def _norm(seg):
    return " ".join(seg.split())


_SPAN = re.compile(r'<span class="l-(en|zh)">(.*?)</span>', re.S)


def _assert_twins_differ(section):
    pairs = _SPAN.findall(section)
    en = [_norm(t) for k, t in pairs if k == "en"]
    zh = [_norm(t) for k, t in pairs if k == "zh"]
    assert en and len(en) == len(zh)
    for a, b in zip(en, zh):
        assert a != b, (a, b)


def _now_rec(rid="ewu", name="United Kingdom", name_zh="英国", phase="Trough",
             pos=1.8, phase_v2="Downturn", pos_v2=93.64):
    return {"id": rid, "name": name, "name_zh": name_zh,
            "now": {"phase": phase, "pos": pos,
                    "phase_v2": phase_v2, "pos_v2": pos_v2}}


def _fx_rec(rid, pair, r63, r252):
    return {"id": rid, "name": "Sweden", "name_zh": "瑞典",
            "fx": {"pair": pair, "quote": "ccy_per_usd",
                   "leg_return_63d": r63, "leg_return_252d": r252}}


def _model(*recs):
    return {"sectors": list(recs), "baskets": []}


def test_canonical_pair_renders_for_the_committed_ewu_record():
    # committed ewu.now: Trough 1.8 vs Downturn 93.64
    data = _model(_now_rec())
    cd = _canonical_phase(data)
    row = cd["rows"][0]
    assert (row["canon_en"], row["canon_zh"]) == ("Rolling over", "回落")
    assert row["pos_v2"] == 94 and row["differs"] is True
    assert (row["wheel_en"], row["wheel_zh"]) == ("Bottoming", "筑底")
    assert row["pos"] == 2
    sec = _norm(_section(_render(cd)))
    assert "Rolling over" in sec and "回落" in sec and "94/100" in sec
    assert "card shows Bottoming" in sec and "卡片显示 筑底" in sec and " · 2/100" in sec
    fv = sec[sec.index('<div class="fv">'):sec.index('<span class="fv-sub">')]
    assert "Bottoming" not in fv                      # the wheel word is only in fv-sub
    assert data["sectors"][0]["now"]["pos_v2"] == 93.64   # model untouched


def test_agreeing_records_still_render_the_pair():
    # committed ewd: Downturn 64.4 / Downturn 98.75 — agrees, so no "card shows"
    cd = _canonical_phase(_model(_now_rec("ewd", "Sweden", "瑞典", "Downturn",
                                          64.4, "Downturn", 98.75)))
    assert cd["rows"][0]["differs"] is False
    sec = _norm(_section(_render(cd)))
    assert "99/100" in sec and "Rolling over" in sec
    assert "回落" in sec and "card shows" not in sec


def test_null_phase_v2_renders_nothing():
    cd = _canonical_phase(_model(_now_rec(phase_v2=None)))
    assert cd == {}
    assert 'id="cc-canon"' not in _render(cd)


def test_unknown_phase_token_renders_nothing():
    cd = _canonical_phase(_model(_now_rec(phase_v2="SixthPhase")))
    assert cd == {}
    html = _render(cd)
    assert 'id="cc-canon"' not in html and "SixthPhase" not in html


def test_half_position_rounds_up_like_the_drawer():
    # committed eza pos_v2 38.5 — the drawer's Math.round gives 39, Python round gives 38
    cd = _canonical_phase(_model(_now_rec("eza", "South Africa", "南非", "Trough",
                                          11.9, "Downturn", 38.5)))
    assert cd["rows"][0]["pos_v2"] == 39
    sec = _norm(_section(_render(cd)))
    assert "39/100" in sec and "38/100" not in sec


def test_counts_disagreements():
    data = _model(_now_rec(),                                   # ewu: differs
                  _now_rec("ewj", "Japan", "日本", "Trough", 18.3, "Downturn", 99.29),
                  _now_rec("ewd", "Sweden", "瑞典", "Downturn", 64.4, "Downturn", 98.75))
    cd = _canonical_phase(data)
    assert cd["n_rows"] == 3 and cd["n_differ"] == 2
    sec = _norm(_section(_render(cd)))
    assert "2 of 3 markets" in sec and "3 个市场中 2 个" in sec


def test_second_read_framing_and_zh_twins():
    cd = _canonical_phase(_model(_now_rec()))
    sec = _section(_render(cd))
    norm = _norm(sec)
    assert ("it is a second read, not a correction." in norm)
    assert "并非更正" in norm and "规范化读数" in norm
    _assert_twins_differ(sec)


def test_builder_helpers_read_only_the_model():
    srcs = [inspect.getsource(_fx_contribution), inspect.getsource(_canonical_phase)]
    for src in srcs:
        for forbidden in ("open(", "read_text", "json.load", "Path("):
            assert forbidden not in src
    data = _model(_now_rec(), _fx_rec("ewd", "USDSEK", 4.0, 4.5))
    dup = copy.deepcopy(data)
    assert _fx_contribution(dup) == _fx_contribution(data)
    assert _canonical_phase(dup) == _canonical_phase(data)
    assert dup == data                                    # neither helper mutates
    msrc = inspect.getsource(main)
    assert "fx_contribution=_fx_contribution(data)" in msrc
    assert "canonical_phase=_canonical_phase(data)" in msrc
