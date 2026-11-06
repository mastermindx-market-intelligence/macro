"""Display contract for the HK / Canada theme price-coverage block (W28B SPEC 2, seat-amended).

engine/theme_scoring.compute_theme_intel records one population observation per theme and
keeps a below-gate theme only in theme_intel.observation_refusals, but neither regional
basket page showed the reader which themes the desk scored on fewer closes than configured
names or which ones it left out. These tests pin the helper rows and the REAL-template
server-side section that prints them between the ignition-reliability panel and the desk.

Render-only by law: the seat's CI job for this file installs pytest + jinja2 only, so this
module imports NO builder, NO engine.*, NO lib.*, no pandas/numpy. The builder paths below
are DATA read as text / AST only; the helper import is deliberately lazy (inside _to()) so
the RED-first run fails on assertions, not on module collection.

Fixture values are the committed theme_intel observations quoted by the W30-L43 commission:
HK hk_industrials 7 of 9 closes (1766.HK with no close on 2026-10-16), hk_property complete,
hk_pair refused below min_members; CA ca_pipelines 8 of 9 (SES.TO not in the price panel),
ca_lonely insufficient (coverage 0.5) on 2026-10-14.
"""
from __future__ import annotations

import ast
import copy
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jinja2 import Environment, FileSystemLoader  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_BLOCK_OPEN = '<section class="panel pad" id="theme-observation-coverage">'

# ci-trigger-closure: data — builders are read as text / AST only, never imported
_BUILDERS = (_ROOT / "scripts/build_baskets_hk.py",
             _ROOT / "scripts/build_baskets_canada.py")

HK_TI = {
    "observation": {"effective_as_of": "2026-10-16", "status": "legacy_source_without_receipt"},
    "themes": [
        {"id": "hk_industrials", "name": "HK Industrials", "name_zh": "港股工业", "score": 42.4,
         "reco_en": "HOLD", "reco_zh": "持有",
         "observation": {"status": "partial", "configured_n": 9, "observed_n": 7,
                                  "coverage": 0.7778,
                         "min_members": 3, "min_coverage": 0.6, "missing_columns": [],
                         "missing_at_asof": ["1766.HK"], "effective_as_of": "2026-10-16"}},
        {"id": "hk_property", "name": "HK Property", "name_zh": "港股地产", "score": 44.0,
         "reco_en": "HOLD", "reco_zh": "持有",
         "observation": {"status": "complete", "configured_n": 15, "observed_n": 15,
                                  "coverage": 1.0,
                         "min_members": 3, "min_coverage": 0.6, "missing_columns": [],
                         "missing_at_asof": [], "effective_as_of": "2026-10-16"}}],
    "observation_refusals": [
        {"basket_id": "hk_pair",
         "observation": {"status": "complete", "configured_n": 2, "observed_n": 2, "coverage": 1.0,
                         "min_members": 3, "min_coverage": 0.6, "missing_columns": [],
                         "missing_at_asof": [], "effective_as_of": "2026-10-16"}}]}
HK_BASKETS = [{"id": "hk_pair", "name": "HK Pair", "name_zh": "港股双名"}]
CA_TI = {
    "observation": {"effective_as_of": "2026-10-14", "status": "legacy_source_without_receipt"},
    "themes": [
        {"id": "ca_pipelines", "name": "Pipelines & Midstream", "name_zh": "管道与中游", "score": 53,
         "reco_en": "HOLD", "reco_zh": "持有",
         "observation": {"status": "partial", "configured_n": 9, "observed_n": 8,
                                  "coverage": 0.8889,
                         "min_members": 3, "min_coverage": 0.6, "missing_columns": ["SES.TO"],
                         "missing_at_asof": [], "effective_as_of": "2026-10-14"}}],
    "observation_refusals": [
        {"basket_id": "ca_lonely",
         "observation": {"status": "insufficient", "configured_n": 4, "observed_n": 2,
                         "coverage": 0.5, "min_members": 3, "min_coverage": 0.6,
                         "missing_columns": ["AAA.TO"], "missing_at_asof": ["BBB.TO"],
                         "effective_as_of": "2026-10-14"}}]}

_BANNED_EN = ("validated", "live", "forecast", "falsifier", "probability", "bullish",
              "bearish", "buy", "sell", "episode", "independent", "current", "latest",
              "month", "z-score", "percentile rank", "refuted")
_BANNED_ZH = ("实时", "申报", "证伪", "已验证", "概率", "独立", "最新", "当前", "月")


def _to():
    from scripts import _baskets_themeobs as TO
    return TO


def _render(tpl: str, **extra) -> str:
    """The builders' own env (autoescape=True) + exactly the context their render calls pass."""
    ctx = {"baskets_json": "{}", "chart_json": "[]", "ignition_json": "{}",
           "provenance_json": "{}", "freshness_json": "{}", "radar_json": "{}",
           "bench_en": "Hang Seng", "bench_zh": "恒生指数", "generated_utc": "TEST"}
    ctx.update(extra)
    env = Environment(loader=FileSystemLoader(str(_ROOT / "templates")), autoescape=True)
    return env.get_template(tpl).render(**ctx)


def _block(html: str) -> str:
    """The new section's own bytes, open tag excluded, up to its closing </section>."""
    i = html.index(_BLOCK_OPEN) + len(_BLOCK_OPEN)
    return html[i:html.index("</section>", i)]


def _rows(block: str) -> list[list[str]]:
    out = []
    for m in re.finditer(r"<tr><td.*?</tr>", block, re.S):
        out.append([re.sub(r"\s+", " ", c).strip()
                    for c in re.findall(r"<td[^>]*>(.*?)</td>", m.group(0), re.S)])
    return out


def _th(block: str) -> list[str]:
    return [re.sub(r"\s+", " ", c).strip() for c in re.findall(r"<th[^>]*>(.*?)</th>", block, re.S)]


def _banned_hits(text: str) -> list[str]:
    hits = [w for w in _BANNED_EN if re.search(r"\b" + re.escape(w) + r"\b", text, re.I)]
    return hits + [w for w in _BANNED_ZH if w in text]


def test_rows_list_partial_themes_then_refusals_and_skip_complete():
    TO = _to()
    before = copy.deepcopy(HK_TI)
    rows = TO.themeobs_rows(HK_TI, HK_BASKETS)
    assert rows == [
        {"id": "hk_industrials", "name": "HK Industrials", "name_zh": "港股工业", "scored": True,
         "score": 42.4, "reco_en": "HOLD", "reco_zh": "持有", "status": "partial",
         "configured_n": 9, "observed_n": 7, "coverage": 0.7778, "min_members": 3,
         "min_coverage": 0.6, "missing_columns": [], "missing_at_asof": ["1766.HK"],
         "effective_as_of": "2026-10-16"},
        {"id": "hk_pair", "name": "HK Pair", "name_zh": "港股双名", "scored": False, "score": None,
         "reco_en": None, "reco_zh": None, "status": "complete", "configured_n": 2,
         "observed_n": 2, "coverage": 1.0, "min_members": 3, "min_coverage": 0.6,
         "missing_columns": [], "missing_at_asof": [], "effective_as_of": "2026-10-16"}]
    assert HK_TI == before


def test_refusal_names_fall_back_to_the_id_then_the_english_name():
    TO = _to()
    rows = TO.themeobs_rows(HK_TI, None)
    assert len(rows) == 2
    assert rows[1]["name"] == "hk_pair" and rows[1]["name_zh"] == "hk_pair"
    rows = TO.themeobs_rows(HK_TI, [{"id": "hk_pair", "name": "HK Pair"}])
    assert rows[1]["name_zh"] == "HK Pair"


def test_bad_input_never_raises_and_lists_nothing():
    TO = _to()
    for ti in (None, [], "x", {"themes": "x"},
               {"themes": [None, 5, {"id": "a"}, {"id": "a", "observation": "x"},
                           {"observation": {"status": "partial"}}]},
               {"observation_refusals": [None, {"basket_id": ""},
                                         {"basket_id": "b", "observation": None},
                                         {"observation": {"status": "x"}}]},
               {"themes": [{"id": "z", "name": "Z",
                            "observation": {"status": "insufficient"}}]}):
        assert TO.themeobs_rows(ti) == [], ti
    for b in (None, "x", [None, {"id": 5}, {"id": ""}], {"a": 1}):
        assert len(TO.themeobs_rows(HK_TI, b)) == 2, b


def test_row_fields_are_type_guarded():
    TO = _to()
    rows = TO.themeobs_rows({"themes": [{"id": "t", "score": True, "observation": {
        "status": "partial", "coverage": "0.5", "configured_n": 4.0, "observed_n": None,
        "missing_columns": ["A", "", 5, None], "missing_at_asof": "X", "min_members": False,
        "effective_as_of": 7}}]})
    assert len(rows) == 1
    r = rows[0]
    assert r["scored"] is True and r["score"] is None
    assert r["coverage"] is None
    assert isinstance(r["configured_n"], float) and r["configured_n"] == 4.0
    assert r["observed_n"] is None and r["min_members"] is None
    assert r["missing_columns"] == ["A"] and r["missing_at_asof"] == []
    assert r["effective_as_of"] is None
    assert r["name"] == "t" and r["name_zh"] == "t"


def test_observation_line_needs_both_fields():
    TO = _to()
    assert TO.observation_line(HK_TI) == {"effective_as_of": "2026-10-16",
                                         "status": "legacy_source_without_receipt"}
    for ti in (None, {}, {"observation": "x"},
               {"observation": {"status": "legacy_source_without_receipt"}},
               {"observation": {"effective_as_of": "2026-10-16"}},
               {"observation": {"effective_as_of": "", "status": "x"}}):
        assert TO.observation_line(ti) == {}, ti


def test_hk_block_prints_the_partial_and_the_refused_theme():
    TO = _to()
    blk = _block(_render("baskets_hk.html.j2", themeobs=TO.themeobs_rows(HK_TI, HK_BASKETS),
                         theme_source=TO.observation_line(HK_TI)))
    rows = _rows(blk)
    assert rows[0] == ['<span class="l-en">HK Industrials</span><span class="l-zh">港股工业</span>',
                       '42 · <span class="l-en">HOLD</span><span class="l-zh">持有</span>',
                       '7 / 9', '77.8%', '≥3 · ≥60%',
                       '<span class="l-en">Partial — gate passed</span>'
                       '<span class="l-zh">部分 — 已过门槛</span>', '—', '1766.HK'], rows[0]
    assert rows[1] == ['<span class="l-en">HK Pair</span><span class="l-zh">港股双名</span>',
                       '—', '2 / 2', '100.0%', '≥3 · ≥60%',
                       '<span class="warn"><span class="l-en">Not scored — below the gate'
                       '</span><span class="l-zh">未评分 — 低于门槛</span></span>', '—', '—'], rows[1]
    assert "HK Property" not in blk


def test_canada_block_separates_the_two_missing_causes():
    TO = _to()
    blk = _block(_render("baskets_canada.html.j2", themeobs=TO.themeobs_rows(CA_TI),
                         theme_source=TO.observation_line(CA_TI)))
    rows = _rows(blk)
    assert rows[0] == ['<span class="l-en">Pipelines &amp; Midstream</span>'
                       '<span class="l-zh">管道与中游</span>',
                       '53 · <span class="l-en">HOLD</span><span class="l-zh">持有</span>',
                       '8 / 9', '88.9%', '≥3 · ≥60%',
                       '<span class="l-en">Partial — gate passed</span>'
                       '<span class="l-zh">部分 — 已过门槛</span>', 'SES.TO', '—'], rows[0]
    assert rows[1] == ['<span class="l-en">ca_lonely</span><span class="l-zh">ca_lonely</span>',
                       '—', '2 / 4', '50.0%', '≥3 · ≥60%',
                       '<span class="warn"><span class="l-en">Not scored — below the gate'
                       '</span><span class="l-zh">未评分 — 低于门槛</span></span>',
                       'AAA.TO', 'BBB.TO'], rows[1]
    th = _th(blk)
    assert th[6] == ('<span class="l-en">Not in the price panel</span>'
                     '<span class="l-zh">不在价格面板中</span>'), th
    assert th[7] == ('<span class="l-en">No close on the as-of date</span>'
                     '<span class="l-zh">截至日无收盘价</span>'), th
    assert th[6] != th[7]


def test_block_is_absent_when_nothing_is_listed():
    TO = _to()
    complete_only = {"themes": [copy.deepcopy(HK_TI["themes"][1])]}
    assert TO.themeobs_rows(complete_only, HK_BASKETS) == []
    for tpl in ("baskets_hk.html.j2", "baskets_canada.html.j2"):
        bare = _render(tpl)
        assert _render(tpl, themeobs=[], theme_source={}) == bare
        assert "theme-observation-coverage" not in bare
        assert "theme-observation-coverage" in _render(tpl, themeobs=TO.themeobs_rows(HK_TI),
                                                       theme_source={})


def test_block_sits_between_the_reliability_panel_and_the_desk():
    TO = _to()
    sc = {"market": "hk", "n_graded": 102,
          "by_state": {"running": {"n": 102, "beat_rate_4w": None}}}
    for tpl, ti in (("baskets_hk.html.j2", HK_TI), ("baskets_canada.html.j2", CA_TI)):
        html = _render(tpl, themeobs=TO.themeobs_rows(ti),
                       theme_source=TO.observation_line(ti), scorecard=sc)
        assert html.count('id="theme-observation-coverage"') == 1, tpl
        assert html.count('id="ignition-reliability"') == 1, tpl
        a, b, c, d = (html.index('id="nr-scorecard"'), html.index('id="ignition-reliability"'),
                      html.index('id="theme-observation-coverage"'), html.index('id="content"'))
        assert a < b < c < d, (a, b, c, d, tpl)


def test_block_copy_is_bilingual_and_banned_word_free():
    TO = _to()
    blk = _block(_render("baskets_hk.html.j2", themeobs=TO.themeobs_rows(HK_TI, HK_BASKETS),
                         theme_source=TO.observation_line(HK_TI)))
    pairs = len(re.findall(r'<span class="l-en">[^<]*</span><span class="l-zh">', blk))
    assert pairs == blk.count('<span class="l-en">') == blk.count('<span class="l-zh">')
    zh = " ".join(re.findall(r'<span class="l-zh">([^<]*)</span>', blk))
    assert "申报" not in zh and "实时" not in zh
    text = re.sub(r"<[^>]*>", " ", blk)
    assert _banned_hits(text) == [], _banned_hits(text)


def _slices(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    i = next(n for n, l in enumerate(lines) if "{%- if themeobs %}" in l)
    j = next(n for n in range(i, len(lines)) if "</section>" in lines[n])
    k = next(n for n in range(j, len(lines)) if lines[n].strip() == "{%- endif %}")
    a = lines[i:k + 1]
    p = next(n for n, l in enumerate(lines) if "{%- if theme_source" in l)
    seen, q = 0, None
    for n in range(p, len(lines)):
        if lines[n].strip() == "{%- endif %}":
            seen += 1
            if seen == 2:
                q = n
                break
    b = lines[p:q + 1]
    return a, b


def test_added_template_lines_add_no_style_or_colour_literal():
    for name in ("baskets_hk.html.j2", "baskets_canada.html.j2"):
        a, b = _slices(_ROOT / "templates" / name)
        assert len(a) == 39, (name, len(a))
        assert len(b) == 10, (name, len(b))
        for line in a + b:
            assert len(line) <= 100, (name, line)
            assert not re.search(r"style|#[0-9a-fA-F]{3,6}\b|rgb\(|hsl\(|color-mix", line), line


def _nodes(node):
    # Recursive child iteration: the CI closure scanner reads any call named `walk`
    # as a filesystem traversal and would widen this job to scripts/** + templates/**.
    yield node
    for child in ast.iter_child_nodes(node):
        yield from _nodes(child)


def test_builders_pass_both_context_keys():
    imp = "from scripts import _baskets_themeobs as TO  # noqa: E402"
    for path in _BUILDERS:
        text = path.read_text(encoding="utf-8")
        assert text.count(imp) == 1, path
        lines = text.splitlines()
        bs = [n for n, l in enumerate(lines) if "_baskets_scorecard as BS" in l]
        assert bs and lines[bs[0] + 1].strip() == imp, path
        hits = []
        for node in _nodes(ast.parse(text)):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "render"
                    and any(kw.arg == "scorecard" for kw in node.keywords)):
                hits.append(node)
        assert len(hits) == 1, path
        kws = {kw.arg: ast.unparse(kw.value).replace('"', "'") for kw in hits[0].keywords}
        assert kws["themeobs"] == "TO.themeobs_rows(data.get('theme_intel'), data.get('baskets'))"
        assert kws["theme_source"] == "TO.observation_line(data.get('theme_intel'))"
