"""The JODI quality badge on templates/spr.html.j2 must speak Chinese in its zh slot.

The producer already ships ASSESS_WORD_ZH (engine/strategic_reserves.py); these tests
pin the wire: the builder passes the dict, and the badge's t() second argument uses it,
so an zh reader is not handed the English word inside the l-zh span. Rendered from
inline fixtures shaped like the committed record; no site/ or data/ read, no network.
"""
from __future__ import annotations

import inspect
import re
import sys
from pathlib import Path

from jinja2 import Environment

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import strategic_reserves as sr     # noqa: E402
from scripts import build_spr                   # noqa: E402

REPO = Path(__file__).resolve().parent.parent
TEMPLATE = (REPO / "templates/spr.html.j2").read_text(encoding="utf-8")
MACROS = "".join(TEMPLATE.splitlines(True)[:8])


def _badge_source():
    """The badge markup, sliced from the template as it is committed."""
    start = TEMPLATE.index("{% if c.jodi_total_mb is not none %}")
    tag = re.compile(r"\{%-?\s*if c\.jodi_assess\s*%}")
    end = re.compile(r"\{%-?\s*endif\s*%}")
    badge = start + tag.search(TEMPLATE[start:]).start()
    return TEMPLATE[start:badge + end.search(TEMPLATE[badge:]).end()] + "{% endif %}"


def _row(jodi_assess):
    return {"iso": "US", "name": "United States", "name_zh": "美国", "flag": "",
            "jodi_total_mb": 568.7, "jodi_assess": jodi_assess,
            "jodi_as_of": "2026-07", "jodi_mom_mb": -12.9}


def _render(row, stub=True):
    src = _badge_source()
    ctx = {"c": row, "assess_word": sr.ASSESS_WORD, "assess_word_zh": sr.ASSESS_WORD_ZH}
    if stub:
        ctx["t"] = lambda en, zh="": "%s|%s" % (en, zh)
    else:
        src = MACROS + src
    return Environment(autoescape=True).from_string(src).render(**ctx)


def test_builder_passes_the_zh_assess_dictionary_to_the_template():
    assert "assess_word_zh=sr.ASSESS_WORD_ZH" in inspect.getsource(build_spr.main)


def test_reported_badge_renders_its_zh_word_from_a_committed_shaped_record():
    out = _render(_row(1))
    assert "qbadge q1" in out
    assert "reported|官方报送" in out


def test_estimate_badge_renders_its_zh_word():
    out = _render(_row(3))
    assert "qbadge q3" in out
    assert "estimate|估算" in out


def test_zh_slot_is_never_a_copy_of_the_english_word():
    for code, en in ((1, "reported"), (3, "estimate")):
        out = _render(_row(code))
        assert "%s|%s" % (en, en) not in out
        zh = out.split("%s|" % en)[1].split("<")[0]
        assert zh and zh != en


def test_unmapped_and_missing_codes_render_no_badge():
    assert "qbadge" not in _render(_row(None))
    out = _render(_row(9), stub=False)
    assert "None" not in out
    assert "qbadge" in out


def test_only_codes_the_page_actually_shows_are_asserted():
    forbidden = (sr.ASSESS_WORD[2], sr.ASSESS_WORD_ZH[2])   # code 2 stays off the page
    hits = [ln for ln in Path(__file__).read_text(encoding="utf-8").splitlines()
            if "assert" in ln and any(word in ln for word in forbidden)]
    assert hits == []


def _hero_h2():
    for ln in TEMPLATE.splitlines():
        if "<h2>" in ln and "United States SPR" in ln:
            return ln
    raise AssertionError("hero h2 missing")


def _live_if():
    a = TEMPLATE.index("{% if c.live %}")
    b = TEMPLATE.index("{% endif %}", a)
    return TEMPLATE[a:b + len("{% endif %}")]


def test_spr_template_text_drops_live_wording():
    assert "t('live'" not in TEMPLATE
    assert "(EIA, live)" not in TEMPLATE
    assert "Report (live)" not in TEMPLATE
    assert "实时" not in TEMPLATE


def test_hero_h2_dates_the_eia_weekly_figure():
    src = _hero_h2()
    tfn = lambda en, zh="": "%s|%s" % (en, zh)
    env = Environment(autoescape=True)
    out = env.from_string(src).render(as_of="Oct 23, 2026", t=tfn)
    assert "as of" in out
    assert "截至" in out
    assert "Oct 23, 2026" in out
    assert "live" not in out
    assert "实时" not in out
    out2 = env.from_string(src).render(as_of="Sep 04, 2026", t=tfn)
    assert "Sep 04, 2026" in out2


def test_us_row_badge_says_weekly():
    src = _live_if()
    tfn = lambda en, zh="": "%s|%s" % (en, zh)
    env = Environment(autoescape=True)
    on = env.from_string(src).render(c={"live": True}, t=tfn)
    assert "weekly" in on
    assert "每周" in on
    assert "live" not in on
    assert "实时" not in on
    off = env.from_string(src).render(c={"live": False}, t=tfn)
    assert "weekly" not in off
    assert "每周" not in off


def test_import_cover_label_names_52_week_mean():
    i = TEMPLATE.index("SPR ÷")
    label = TEMPLATE[i:i + 90]
    assert "52-week" in label
    assert "52周" in label
