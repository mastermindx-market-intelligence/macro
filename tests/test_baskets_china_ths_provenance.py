"""Membership provenance + sleeve chip on the 同花顺 basket browser (W28G SPEC 1/SPEC 3).

The lite page must print which membership file it computes from and how the
weekly re-scrapes went (server-side line, id="mem-prov"), and paint the chip
the builder already attaches (data["sleeve_chip"] -> render kwarg, server-side,
id="sleeve-chip-lite"). Both blocks render only when ``lite`` is true and both
absent cases are byte-identical to the seed template.

Tests import only the stdlib, jinja2 and scripts._ths_provenance (the helper is
imported INSIDE each helper test so the template tests are not collection
errors while the module is absent) — never a scripts/build_*.py builder,
engine.*, lib.*, pandas or numpy. Fixtures are the committed shapes (inline
dicts under tmp_path; no data/, no site/, no network).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_ROOT = Path(__file__).resolve().parent.parent

# The committed membership header (data/baskets_china_ths/membership.json).
_MEM = {"version": "2026-06-30", "curated": "2026-06-30",
        "snapshots": ["2026-06-30"], "baskets": {}}

# The committed chip shape (engine/risk_radar_intl.py cn_sleeve_chip()).
_CHIP = {"sleeve_factor": 0.62, "radar_state": "risk-off",
         "radar_as_of": "2026-10-16",
         "dominant_driver_en": "Breadth breakdown (all-boats)",
         "dominant_driver_zh": "广度普跌（普跌）",
         "label_en": "Sleeve ×0.62 — CN drawdown radar: risk-off",
         "label_zh": "仓位 ×0.62 — CN回撤雷达：risk-off",
         "passport": {"note": "Validated forward-drawdown composite; "
                              "sizes the sleeve, never vetoes names."}}

# The provenance of the committed receipts for the fixture rows below.
_PROV1 = {"observed": "2026-06-30",
          "newest_scrape": {"date": "2026-10-17", "complete": False,
                            "concepts_attempted": 375, "concepts_fetched": 0},
          "last_complete_scrape": "2026-10-03"}


def _rows1() -> list:
    return [
        {"date": "2026-10-03", "complete": True, "concepts_attempted": 375,
         "concepts_fetched": 375, "promoted": True, "members_total": 16878,
         "truncated": ["概念A", "概念B"]},
        {"date": "2026-10-10", "complete": False, "concepts_attempted": 375,
         "concepts_fetched": 120},
        {"date": "2026-10-17", "complete": False, "concepts_attempted": 375,
         "concepts_fetched": 0, "truncated": ["概念A"]},
    ]


def _receipts(tmp_path, rows) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    for row in rows:
        (tmp_path / f"scrape_{row['date']}.json").write_text(
            json.dumps(row, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def _render(**extra) -> str:
    """Render the real template with the builder's minimal context (lite)."""
    env = Environment(loader=FileSystemLoader(str(_ROOT / "templates")),
                      autoescape=True)
    ctx = dict(baskets_json="{}", chart_json="{}", basket_base="",
               bench_en="CSI 300", bench_zh="沪深300",
               generated_utc="2026-10-20 05:30 UTC", lite=True)
    ctx.update(extra)
    return env.get_template("baskets_china_factorwatch.html.j2").render(**ctx)


def _between(html: str, start: str, end: str) -> str:
    i = html.index(start)
    return html[i + len(start):html.index(end, i)]


def _prov(html: str) -> str:
    start = '<p class="tagline" id="mem-prov">'
    i = html.index(start)
    j = html.index("</p>", i)
    return html[i:j + len("</p>")]


def _chip(html: str) -> str:
    start = '<div class="semis-chip" id="sleeve-chip-lite">'
    i = html.index(start)
    j = html.index("</div>", i)
    return html[i:j + len("</div>")]


def _txt(s: str, drop: str) -> str:
    s = re.sub(rf'<span class="{drop}">.*?</span>', "", s, flags=re.S)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s).strip()


def _en(s: str) -> str:
    return _txt(s, "l-zh")


def _zh(s: str) -> str:
    return _txt(s, "l-en")


# ---------------------------------------------------------------- helper 1-7

def test_provenance_reads_the_committed_shapes(tmp_path) -> None:
    from scripts._ths_provenance import membership_provenance
    result = membership_provenance(_MEM, _receipts(tmp_path, _rows1()))
    assert result == _PROV1
    blob = json.dumps(result)
    for key in ("truncated", "members_total", "promoted"):
        assert key not in blob, f"receipt noise leaked: {key}"


def test_provenance_fail_open_on_bad_membership(tmp_path) -> None:
    from scripts._ths_provenance import membership_provenance
    for bad in (None, [], {}, {"version": ""}, {"version": "  "},
                {"version": 20260630}):
        assert membership_provenance(bad, tmp_path) is None


def test_provenance_keeps_the_date_without_receipts(tmp_path) -> None:
    from scripts._ths_provenance import membership_provenance
    want = {"observed": "2026-06-30", "newest_scrape": None,
            "last_complete_scrape": None}
    assert membership_provenance(_MEM, tmp_path / "missing") == want
    assert membership_provenance(_MEM, None) == want
    (tmp_path / "empty").mkdir()
    assert membership_provenance(_MEM, tmp_path / "empty") == want
    loose = {"version": " 2026-06-30 "}
    assert membership_provenance(loose, tmp_path / "missing") == want


def test_provenance_skips_unreadable_receipts(tmp_path) -> None:
    from scripts._ths_provenance import membership_provenance
    d = _receipts(tmp_path, _rows1())
    (d / "scrape_2026-10-24.json").write_text("{not json", encoding="utf-8")
    (d / "scrape_2026-10-25.json").write_text("[1, 2]", encoding="utf-8")
    (d / "scrape_2026-10-31.json").write_text(
        json.dumps({"date": 20261031, "complete": True}), encoding="utf-8")
    result = membership_provenance(_MEM, d)
    assert result["newest_scrape"]["date"] == "2026-10-17"
    assert result["last_complete_scrape"] == "2026-10-03"


def test_provenance_complete_must_be_true(tmp_path) -> None:
    from scripts._ths_provenance import membership_provenance
    rows = [{"date": "2026-10-03", "complete": True},
            {"date": "2026-10-17", "complete": "true"},
            {"date": "2026-10-24", "complete": 1}]
    result = membership_provenance(_MEM, _receipts(tmp_path, rows))
    assert result["newest_scrape"]["date"] == "2026-10-24"
    assert result["newest_scrape"]["complete"] is False
    assert result["last_complete_scrape"] == "2026-10-03"


def test_provenance_counts_reject_bools_and_strings(tmp_path) -> None:
    from scripts._ths_provenance import membership_provenance
    rows = [{"date": "2026-10-17", "complete": False,
             "concepts_fetched": True, "concepts_attempted": "375"}]
    result = membership_provenance(_MEM, _receipts(tmp_path, rows))
    assert result["newest_scrape"]["concepts_fetched"] is None
    assert result["newest_scrape"]["concepts_attempted"] is None


def test_provenance_last_complete_is_the_newest_complete(tmp_path) -> None:
    from scripts._ths_provenance import membership_provenance
    rows = [{"date": "2026-09-26", "complete": True},
            {"date": "2026-10-03", "complete": True},
            {"date": "2026-10-17", "complete": False}]
    result = membership_provenance(_MEM, _receipts(tmp_path, rows))
    assert result["last_complete_scrape"] == "2026-10-03"
    incomplete = [{"date": "2026-10-17", "complete": False},
                  {"date": "2026-10-10", "complete": False}]
    result = membership_provenance(_MEM, _receipts(tmp_path / "inc", incomplete))
    assert result["last_complete_scrape"] is None


# ----------------------------------------------------------- template 8-18

def test_prov_line_renders_the_committed_case(tmp_path) -> None:
    from scripts._ths_provenance import membership_provenance
    prov = membership_provenance(_MEM, _receipts(tmp_path, _rows1()))
    assert prov == _PROV1
    h = _render(membership_provenance=prov)
    assert _en(_prov(h)) == (
        "Membership file dated 2026-06-30 · newest Tonghuashun re-scrape "
        "2026-10-17: incomplete (0/375 boards) · last complete re-scrape "
        "2026-10-03")
    assert _zh(_prov(h)) == (
        "成分文件日期 2026-06-30 · 最近一次同花顺重抓 2026-10-17: 未完成 "
        "(0/375 个板块) · 上次完整重抓 2026-10-03")


def test_prov_line_complete_newest_hides_last_complete() -> None:
    h = _render(membership_provenance={
        "observed": "2026-06-30",
        "newest_scrape": {"date": "2026-10-03", "complete": True,
                          "concepts_attempted": 375, "concepts_fetched": 375},
        "last_complete_scrape": "2026-10-03"})
    en = _en(_prov(h))
    assert en.endswith("2026-10-03: complete (375/375 boards)"), en
    assert "last complete" not in en


def test_prov_line_without_receipts_or_counts() -> None:
    base = {"observed": "2026-06-30", "newest_scrape": None,
            "last_complete_scrape": None}
    h = _render(membership_provenance=dict(base))
    assert _en(_prov(h)) == "Membership file dated 2026-06-30"
    h = _render(membership_provenance={**base,
                                       "last_complete_scrape": "2026-10-03"})
    assert _en(_prov(h)) == ("Membership file dated 2026-06-30 · last complete "
                             "re-scrape 2026-10-03")
    h = _render(membership_provenance={
        "observed": "2026-06-30", "last_complete_scrape": "2026-10-03",
        "newest_scrape": {"date": "2026-10-17", "complete": False,
                          "concepts_attempted": None, "concepts_fetched": 0}})
    en = _en(_prov(h))
    for tok in ("(", "/", "None", "boards"):
        assert tok not in en, f"count noise leaked {tok!r}: {en}"
    assert en.endswith("· last complete re-scrape 2026-10-03"), en


def test_prov_line_is_escaped() -> None:
    h = _render(membership_provenance={"observed": "<i>x</i>",
                                       "newest_scrape": None,
                                       "last_complete_scrape": None})
    seg = _prov(h)
    assert "&lt;i&gt;x&lt;/i&gt;" in seg
    assert "<i>" not in seg


_CHIP_STATES = [
    ("risk-off", "RISK-OFF — trade smaller", "避险 — 减小仓位"),
    ("elevated", "ELEVATED — trade smaller", "偏高 — 减小仓位"),
    ("caution", "CAUTION — avoid chasing", "谨慎 — 谨慎追高"),
    ("calm", "CALM — normal sizing", "平静 — 正常仓位"),
]


def test_chip_renders_each_state() -> None:
    for state, act_en, act_zh in _CHIP_STATES:
        h = _render(sleeve_chip=dict(_CHIP, radar_state=state))
        assert _en(_chip(h)) == (
            f"Risk backdrop {act_en} sleeve sizing ×0.62 main risk: "
            "Breadth breakdown as of 2026-10-16"), state
        assert _zh(_chip(h)) == (
            f"风险背景 {act_zh} 组合仓位 ×0.62 主要风险：广度普跌 "
            "截至 2026-10-16"), state


def test_chip_never_prints_producer_labels_or_passport() -> None:
    seg = _chip(_render(sleeve_chip=_CHIP))
    for leak in ("Validated", "vetoes", "CN回撤雷达", "None", "style="):
        assert leak not in seg, f"chip leaked {leak!r}"
    assert "risk-off" not in _zh(seg)


def test_chip_formats_factor_and_degrades_driver_and_date() -> None:
    seg = _chip(_render(sleeve_chip=dict(_CHIP, sleeve_factor=1)))
    assert "×1.00" in _en(seg)
    two = _chip(_render(sleeve_chip=dict(
        _CHIP, dominant_driver_en="A (b)", dominant_driver_zh=None)))
    assert "main risk: A" in _en(two)
    assert "主要风险：A" in _zh(two)
    five = _chip(_render(sleeve_chip=dict(_CHIP, dominant_driver_en=5)))
    assert "main risk" not in _en(five)
    assert "主要风险" not in _zh(five)
    absent = {k: v for k, v in _CHIP.items() if k != "dominant_driver_en"}
    seg = _chip(_render(sleeve_chip=absent))
    assert "main risk" not in _en(seg)
    assert "主要风险" not in _zh(seg)
    no_asof = {k: v for k, v in _CHIP.items() if k != "radar_as_of"}
    seg = _chip(_render(sleeve_chip=no_asof))
    assert "as of" not in _en(seg)
    assert "截至" not in _zh(seg)


def test_chip_absent_cases_are_byte_identical() -> None:
    cases = [dict(), dict(sleeve_chip=None), dict(sleeve_chip={}),
             dict(sleeve_chip=[]), dict(sleeve_chip="calm"),
             dict(sleeve_chip=3),
             dict(sleeve_chip=dict(_CHIP, radar_state="unknown")),
             dict(sleeve_chip=dict(_CHIP, radar_state=None)),
             dict(sleeve_chip=dict(_CHIP, sleeve_factor=None)),
             dict(sleeve_chip=dict(_CHIP, sleeve_factor="0.62")),
             dict(sleeve_chip=dict(_CHIP, sleeve_factor=True))]
    for ctx in cases:
        html = _render(**ctx)
        assert "sleeve-chip-lite" not in html, ctx
        assert ('<div id="semis-chip"></div>\n    \n  </header>'
                in html), ctx


def test_prov_absent_cases_are_byte_identical() -> None:
    for ctx in (dict(), dict(membership_provenance=None),
                dict(membership_provenance={}),
                dict(membership_provenance={"observed": ""})):
        html = _render(**ctx)
        assert "mem-prov" not in html, ctx
        assert ('</a></p>\n    \n    <div id="semis-chip"></div>'
                in html), ctx


def test_both_blocks_only_on_lite() -> None:
    html = _render(lite=False, membership_provenance=_PROV1,
                   sleeve_chip=_CHIP)
    assert "mem-prov" not in html
    assert "sleeve-chip-lite" not in html
    assert "2026-10-16" not in html


def test_blocks_have_no_whitespace_only_line() -> None:
    h = _render(membership_provenance=_PROV1, sleeve_chip=_CHIP)
    for seg in (_prov(h), _chip(h)):
        assert not re.search(r"\n[ \t]*\n", seg), seg
    assert '</a></p>\n    <p class="tagline" id="mem-prov">' in h
    assert ('<div id="semis-chip"></div>\n    <div class="semis-chip" '
            'id="sleeve-chip-lite">') in h
    assert '</div>\n    \n  </header>' in h


# -------------------------------------------------------------- source 19-21

def test_added_template_lines_add_no_style_or_colour_literal() -> None:
    src = (_ROOT / "templates" / "baskets_china_factorwatch.html.j2").read_text(
        encoding="utf-8")
    i = src.index("{%- if membership_provenance")
    j = src.index("{%- endif %}\n    {# cross-market", i)
    k = src.index("{%- set sc = sleeve_chip")
    m = src.index("\n    {% else %}", k)
    text = src[i:j] + src[k:m]
    for tok in ("style=", "<style", "rgb(", "hsl(", "color-mix",
                "border-left", "|safe", "passport", "label_en", "label_zh"):
        assert tok not in text, f"banned token in the added lines: {tok!r}"
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", text)
    for line in text.splitlines():
        assert len(line) <= 100, line


def test_builder_wires_both_blocks() -> None:
    src = (_ROOT / "scripts" / "build_baskets_china_ths.py").read_text(
        encoding="utf-8")  # ci-trigger-closure: data — builder source read as text, never imported
    assert "from scripts import _ths_provenance as PV" in src
    assert "PV.membership_provenance(" in src
    assert "membership_provenance=mem_prov," in src
    assert 'sleeve_chip=slim_data.get("sleeve_chip"),' in src
    assert "mem_prov = None" in src


def test_added_copy_has_no_banned_word(tmp_path) -> None:
    from scripts._ths_provenance import membership_provenance
    prov = membership_provenance(_MEM, _receipts(tmp_path, _rows1()))
    h = _render(membership_provenance=prov,
                sleeve_chip=dict(_CHIP, radar_state="risk-off"))
    texts = [_en(_prov(h)), _zh(_prov(h)), _en(_chip(h)), _zh(_chip(h))]
    banned = ["实时", "申报", "证伪", "validated", "已验证", "live",
              "forecast", "falsifier", "probability", "概率", "bullish",
              "bearish", "buy", "sell", "episode", "independent", "独立",
              "current", "latest", "最新", "当前", "month", "月",
              "z-score", "percentile rank", "refuted"]
    for text in texts:
        low = text.lower()
        for word in banned:
            if re.search(r"[A-Za-z]", word):
                assert word.lower() not in low, f"banned {word!r} in {text!r}"
            else:
                assert word not in text, f"banned {word!r} in {text!r}"
