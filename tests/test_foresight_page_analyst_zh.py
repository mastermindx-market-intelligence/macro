"""SPEC 5 (W33-LB) — the analyst provenance line gets its zh half.

`engine/foresight_analyst.py` computes `regime_read` AND `regime_read_zh` (both
the computed path and `load_committed_theses`) and the builder passes the whole dict
as `analyst=`. The template printed the English string raw, outside the page's
toggle, so a zh reader skipped the sentence that carries the read's date.

`t()` applies `|safe`, so the house pattern is escape-then-toggle:
`t(x|e, (x_zh or x)|e)`.

Synthetic fixtures only: the strings below are the committed ledger-replay
shape. No store, no builder, no network, no `site/` or `data/` write.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

READ_EN = ("Last saved analyst read \u2014 2026-10-18. No new read was taken for this"
           " rebuild; the break-conditions below are the ones it last set.")
READ_ZH = "上次保存的分析师解读 \u2014 2026-10-18。本次重建未重新解读；以下失效条件为上次设定。"
_MISSING = object()


def _analyst(zh=READ_ZH, en=READ_EN):
    """The exact dict `load_committed_theses()` returns for the committed ledger."""
    out = {"asof": "2026-10-18", "n_theses": 6, "from_ledger": True,
           "regime_read": en, "confidence": "low",
           "disclaimer": "Model-written; the deterministic monitor re-checks it.",
           "theses": [{"theme": "defense_aerospace", "confidence": "low",
                       "kill_criteria": ["The edgar-scarcity surface turns off."],
                       "mechanism": "", "non_obvious": "", "evidence_display": []}]}
    if zh is not _MISSING:
        out["regime_read_zh"] = zh
    return out


def _render(analyst, **over):
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")),
                      autoescape=True)
    ctx = dict(
        cascade={"sizing": None, "demand_pool": None, "dislocation": None},
        themes=[], stage_counts={}, stage_order=[],
        demand_pool=None, dislocation=None,
        track={"foresight": 0, "bottleneck": 0, "glut": 0, "revisions": 0,
               "guidance": 0, "emergence": 0, "subsector": 0, "recent": []},
        grade=None, emergence=None, subsectors=None, convergence=None, power=None,
        analyst=analyst, monitor=None, health=None,
        asof="2026-10-20", generated_utc="2026-10-20 00:00 UTC",
        nav_prefix="", active_section="research", active_page="foresight",
    )
    ctx.update(over)
    return env.get_template("foresight.html.j2").render(**ctx)


def _prov(html):
    """The provenance `<p>` only — never the disclaimer or a thesis row."""
    at = html.index("Last saved analyst read")
    return html[html.rindex("<p>", 0, at):html.index("</p>", at)]


def _spans(prov, cls):
    return re.findall(r'<span class="%s">(.*?)</span>' % cls, prov, re.S)


def test_zh_provenance_renders_from_the_committed_replay_shape():
    prov = _prov(_render(_analyst()))
    zh = _spans(prov, "l-zh")
    assert zh, "the zh half of the provenance line never reaches the page"
    assert "上次保存的分析师解读" in zh[0]
    assert "2026-10-18" in zh[0], "the zh reader never sees the read's date"


def test_both_languages_never_share_one_visible_span():
    prov = _prov(_render(_analyst()))
    assert prov.count('class="l-en"') == 1, prov
    assert prov.count('class="l-zh"') == 1, prov
    assert _spans(prov, "l-en")[0].startswith("Last saved analyst read")


def test_missing_zh_falls_back_to_english():
    for analyst in (_analyst(zh=_MISSING), _analyst(zh="")):
        prov = _prov(_render(analyst))
        assert prov.count("<p>") == 1, "the sentence was dropped or duplicated"
        assert '<span class="l-zh"></span>' not in prov, "an empty zh span shipped"
        assert "Last saved analyst read" in _spans(prov, "l-zh")[0]
    # Constraint 3 is a source requirement as well as a rendered one: the fallback
    # stays explicit, so dropping the guard goes red here rather than silently
    # relying on `t()`'s own falsy-zh branch.
    src = (ROOT / "templates" / "foresight.html.j2").read_text(encoding="utf-8")
    line = next(ln for ln in src.splitlines()
                if "analyst.regime_read_zh" in ln and "analyst.regime_read" in ln)
    assert "analyst.regime_read_zh or analyst.regime_read" in line


def test_ledger_string_is_escaped():
    html = _render(_analyst(en="<b>x</b> & y", zh="<i>z</i> & w"))
    assert "&lt;b&gt;" in html and "&lt;i&gt;" in html
    assert "<b>x</b>" not in html and "<i>z</i>" not in html
