"""B-F06-4 research screener — research_priority_only, never a ranker."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import pytest

from engine.research_screener import (
    CATALYST_WINDOW_TRADING_DAYS,
    EXPOSURE_NULL_EN,
    EXPOSURE_NULL_ZH,
    THEME_NULL_EN,
    THEME_NULL_ZH,
    _assert_no_forbidden_keys,
    compile_research_screener,
    sort_rows,
    trading_days_between,
)

REPO = Path(__file__).resolve().parents[1]
ENGINE_PATH = REPO / "engine" / "research_screener.py"
BUILDER_PATH = REPO / "scripts" / "build_research_screener.py"
TEMPLATE_PATH = REPO / "templates" / "research_screener.html.j2"
CSS_PATH = REPO / "templates" / "research_screener.css"
THEME_CSS_PATH = REPO / "templates" / "theme.css"
NAVLINKS_PATH = REPO / "templates" / "_navlinks.html.j2"
SITE_NAV_PATH = REPO / "templates" / "_site_nav.html.j2"

_SUPPORT_PARTIALS = (
    "_site_nav.html.j2",
    "_navlinks.html.j2",
    "_seo_head.html.j2",
)

_FORBIDDEN = (
    "score",
    "rank",
    "top",
    "best",
    "conviction",
    "排名",
    "评分",
    "得分",
    "最佳",
    "确信",
    "falsifier",
    "refuted",
    "证伪",
)

_FORBIDDEN_KEY = re.compile(
    r"\b(scor(e|es|ed|ing)|rank(s|ed|ing)?|top|best|conviction(s)?)\b",
    re.I,
)
_WORD = re.compile(
    r"\b(scor(e|es|ed|ing)|rank(s|ed|ing)?|top|best|conviction(s)?)\b",
    re.I,
)
_ON_DATE = re.compile(r"\bon\s+\d{4}-\d{2}-\d{2}\b")
_CJK_END = re.compile(r"[。！？]")


def _state(
    listing_key: str,
    ticker: str,
    *,
    name: str | None = None,
    window_start: str | None = None,
    window_end: str | None = None,
) -> dict:
    catalyst: dict
    if window_start:
        catalyst = {
            "next_observables": [{
                "kind": "ESTIMATED_WINDOW",
                "window_start": window_start,
                "window_end": window_end or window_start,
                "authoritative": False,
            }],
            "deadlines": [],
            "coverage_state": "PARTIAL",
        }
    else:
        catalyst = {"next_observables": [], "deadlines": [], "coverage_state": "UNAVAILABLE"}
    rec = {
        "schema": "security_state.v1",
        "listing_key": listing_key,
        "ticker_display": ticker,
        "legs": {
            "catalyst": catalyst,
            "personal_impact": {
                "state": "NO_USER_CONTEXT",
                "coverage_state": "NOT_APPLICABLE",
            },
        },
        "authority": {
            "can_rank": False,
            "can_gate": False,
            "can_size": False,
        },
    }
    if name:
        rec["name"] = name
    return rec


def _valuation(ticker: str, *, price: float, per_share: float, growth: float = 3, margin: float = 0, multiple: float = 18) -> dict:
    return {
        "schema": "valuation_scenario.v1",
        "ticker": ticker,
        "price": {"value": price, "unit": "USD"},
        "scenarios": [{
            "key": "base",
            "assumptions": {
                "sales_growth_pct": growth,
                "margin_delta_pp": margin,
                "earnings_multiple": multiple,
            },
            "per_share": per_share,
            "computable": True,
            "missing": [],
        }],
        "any_computable": True,
    }


def _walk_keys(obj, acc: list[str]) -> None:
    if isinstance(obj, dict):
        acc.extend(obj.keys())
        for value in obj.values():
            _walk_keys(value, acc)
    elif isinstance(obj, list):
        for item in obj:
            _walk_keys(item, acc)


def _visible_copy(html: str) -> str:
    html = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
    html = re.sub(r"<style\b[^>]*>.*?</style>", " ", html, flags=re.I | re.S)
    html = re.sub(r"<[^>]+>", " ", html)
    return html


def test_trading_days_between_skips_weekends():
    # Friday 2026-09-04 to Monday 2026-09-07 is one trading day.
    assert trading_days_between(date(2026, 9, 4), date(2026, 9, 7)) == 1
    assert CATALYST_WINDOW_TRADING_DAYS == 30


def test_no_ranker_guard_on_view_model():
    payload = compile_research_screener(
        [
            _state("US-XNAS-MSFT", "MSFT", name="Microsoft", window_start="2026-09-15"),
            _state("US-XNAS-AAPL", "AAPL", name="Apple", window_start="2026-09-12"),
        ],
        [_valuation("AAPL", price=180, per_share=220)],
        as_of=date(2026, 9, 1),
    )
    keys: list[str] = []
    _walk_keys(payload, keys)
    for key in keys:
        assert not _FORBIDDEN_KEY.search(key), f"forbidden key {key!r}"
    blob = json.dumps(payload, ensure_ascii=False)
    for word in ("score", "rank", "best", "conviction"):
        assert word not in blob.lower()
    assert payload["tier"] == "research_priority_only"
    assert payload["order"] == "name"
    assert payload["orderings"] == ["name", "next_catalyst_date"]


def test_alphabetical_default_order():
    payload = compile_research_screener(
        [
            _state("US-XNAS-MSFT", "MSFT", name="Microsoft"),
            _state("US-XNAS-AAPL", "AAPL", name="Apple"),
            _state("US-XNAS-TSLA", "TSLA", name="Tesla"),
        ],
        as_of=date(2026, 9, 1),
    )
    names = [row["name"] for row in payload["rows"]]
    assert names == ["Apple", "Microsoft", "Tesla"]


def test_catalyst_window_keeps_30_trading_days_and_drops_the_rest():
    as_of = date(2026, 9, 1)
    inside = _state("US-XNAS-AAPL", "AAPL", name="Apple", window_start="2026-09-12")
    far = _state("US-XNAS-MSFT", "MSFT", name="Microsoft", window_start="2027-03-01")
    past = _state("US-XNAS-TSLA", "TSLA", name="Tesla", window_start="2026-08-01")
    payload = compile_research_screener([inside, far, past], as_of=as_of)
    by_name = {row["name"]: row for row in payload["rows"]}
    assert by_name["Apple"]["catalyst"] is not None
    assert by_name["Apple"]["catalyst"]["window_start"] == "2026-09-12"
    assert by_name["Apple"]["catalyst"]["window_end"] == "2026-09-12"
    assert by_name["Apple"]["catalyst"]["kind"] == "estimated_window"
    assert "date" not in by_name["Apple"]["catalyst"]
    assert by_name["Apple"]["catalyst"]["owner"]["en"]
    assert by_name["Microsoft"]["catalyst"] is None
    assert by_name["Tesla"]["catalyst"] is None
    assert trading_days_between(as_of, date(2026, 9, 12)) <= CATALYST_WINDOW_TRADING_DAYS
    assert trading_days_between(as_of, date(2027, 3, 1)) > CATALYST_WINDOW_TRADING_DAYS


def test_per_lens_null_when_owner_is_missing():
    payload = compile_research_screener(
        [_state("US-XNAS-AAPL", "AAPL", name="Apple")],
        as_of=date(2026, 9, 1),
    )
    lenses = {item["lens"]: item for item in payload["nulls"]}
    assert lenses["theme"]["en"] == THEME_NULL_EN
    assert lenses["theme"]["zh"] == THEME_NULL_ZH
    assert lenses["exposure"]["en"] == EXPOSURE_NULL_EN
    assert lenses["exposure"]["zh"] == EXPOSURE_NULL_ZH
    row = payload["rows"][0]
    assert row["theme"] is None
    assert row["exposure"] is None
    assert row["valuation_posture"] is None


def test_valuation_posture_is_owner_attributed():
    payload = compile_research_screener(
        [_state("US-XNAS-AAPL", "AAPL", name="Apple")],
        [_valuation("AAPL", price=180, per_share=220)],
        as_of=date(2026, 9, 1),
    )
    posture = payload["rows"][0]["valuation_posture"]
    assert posture is not None
    assert "inexpensive" in posture["label"]["en"].lower()
    assert "披露" in posture["label"]["zh"]
    assert posture["owner"]["en"]
    assert "。" in posture["assumptions_text"]["zh"] or "，" in posture["assumptions_text"]["zh"]


def test_en_zh_copy_uses_cjk_punctuation():
    payload = compile_research_screener(
        [_state("US-XNAS-AAPL", "AAPL", name="Apple", window_start="2026-09-12")],
        [_valuation("AAPL", price=180, per_share=220)],
        as_of=date(2026, 9, 1),
    )
    zh_blobs = [
        payload["nulls"][0]["zh"],
        payload["nulls"][1]["zh"],
        payload["rows"][0]["why"]["zh"],
        payload["rows"][0]["valuation_posture"]["label"]["zh"],
        payload["rows"][0]["valuation_posture"]["assumptions_text"]["zh"],
    ]
    for text in zh_blobs:
        assert not any(ch in text for ch in ".!?;"), text
        assert _CJK_END.search(text) or "，" in text, text


def test_glance_why_en_is_plain_sentences():
    """MAJOR-1: glance-tier EN why is sentences, not jammed clauses."""
    payload = compile_research_screener(
        [_state("US-XNAS-AAPL", "AAPL", name="Apple", window_start="2026-09-12")],
        [_valuation("AAPL", price=180, per_share=220)],
        as_of=date(2026, 9, 1),
    )
    row = payload["rows"][0]
    label_en = row["valuation_posture"]["label"]["en"]
    assumptions_en = row["valuation_posture"]["assumptions_text"]["en"]
    why_en = row["why"]["en"]
    assert label_en.endswith((".", "!", "?")), label_en
    assert assumptions_en.endswith((".", "!", "?")), assumptions_en
    assert "earnings Sales" not in why_en, why_en
    assert f"{label_en} {assumptions_en}" in why_en, why_en
    assert re.search(r"[.!?]\s+[A-Z]", why_en), why_en


def test_template_zh_as_of_uses_cjk_terminator():
    """MAJOR-2: rendered ZH as-of copy terminates with CJK punctuation."""
    pytest.importorskip("jinja2")
    from jinja2 import Environment, FileSystemLoader

    templates = TEMPLATE_PATH.parent
    env = Environment(loader=FileSystemLoader(str(templates)), autoescape=True)
    payload = compile_research_screener(
        [_state("US-XNAS-AAPL", "AAPL", name="Apple")],
        as_of=date(2026, 9, 1),
    )
    html = env.get_template(TEMPLATE_PATH.name).render(
        payload=payload,
        as_of=payload["as_of"],
    )
    zh_spans = re.findall(r'<span class="l-zh">(.*?)</span>', html)
    asof_zh = [span for span in zh_spans if "数据截至" in span]
    assert asof_zh, html
    for text in asof_zh:
        assert "数据截至" in text
        assert text.rstrip().endswith("。"), text
        assert not re.search(r"数据截至[^。]*\.", text), text
    source = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "数据截至" in source
    # A shared ASCII period after {{ as_of }} would terminate ZH with '.'.
    assert not re.search(r"\{\{\s*as_of\s*\}\}\.", source)


def test_receipt_theme_copy_matches_chip_null():
    source = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert source.count(THEME_NULL_EN) >= 2
    assert "Theme is not available yet." not in source


def test_owner_en_uses_house_panel_names_not_slug_case():
    payload = compile_research_screener(
        [_state("US-XNAS-AAPL", "AAPL", name="Apple", window_start="2026-09-12")],
        [_valuation("AAPL", price=180, per_share=220)],
        as_of=date(2026, 9, 1),
    )
    blob = json.dumps(payload, ensure_ascii=False)
    assert "security-state" not in blob
    assert "valuation-under-assumptions" not in blob
    owner_en = payload["rows"][0]["valuation_posture"]["owner"]["en"]
    assert owner_en == "Valuation under different assumptions"
    assert "Valuation under different assumptions" in payload["rows"][0]["why"]["en"]
    source = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "security-state" not in source
    assert "valuation-under-assumptions" not in source


def test_why_names_the_owner():
    payload = compile_research_screener(
        [_state("US-XNAS-AAPL", "AAPL", name="Apple", window_start="2026-09-12")],
        [_valuation("AAPL", price=180, per_share=220)],
        as_of=date(2026, 9, 1),
    )
    why = payload["rows"][0]["why"]
    assert "Catalyst window panel" in why["en"]
    assert "Valuation under different assumptions" in why["en"]
    assert "催化窗口面板" in why["zh"]
    assert "估值" in why["zh"]


def test_catalyst_date_order_is_the_only_alternative():
    rows = compile_research_screener(
        [
            _state("US-XNAS-MSFT", "MSFT", name="Microsoft", window_start="2026-09-10"),
            _state("US-XNAS-AAPL", "AAPL", name="Apple", window_start="2026-09-20"),
            _state("US-XNAS-TSLA", "TSLA", name="Tesla"),
        ],
        as_of=date(2026, 9, 1),
    )["rows"]
    by_date = sort_rows(rows, "next_catalyst_date")
    assert [row["name"] for row in by_date] == ["Microsoft", "Apple", "Tesla"]


def test_template_has_no_ranker_copy_and_uses_shared_nav():
    source = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert '{% include "_site_nav.html.j2" %}' in source
    assert "_navlinks.html.j2" not in source
    visible = _visible_copy(source)
    assert not _WORD.search(visible)
    for token in ("排名", "评分", "得分", "最佳", "确信", "证伪"):
        assert token not in source
    assert THEME_NULL_EN in source
    assert THEME_NULL_ZH in source
    assert EXPOSURE_NULL_EN in source
    assert EXPOSURE_NULL_ZH in source
    assert "disabled" in source
    assert "page-research-screener" in source


def test_template_renders_via_shared_nav(tmp_path: Path):
    pytest.importorskip("jinja2")
    from jinja2 import Environment, FileSystemLoader

    from engine.research_screener import compile_research_screener as compile_vm

    templates = tmp_path / "templates"
    templates.mkdir()
    templates.joinpath("research_screener.html.j2").write_bytes(TEMPLATE_PATH.read_bytes())
    for name in _SUPPORT_PARTIALS:
        templates.joinpath(name).write_bytes((REPO / "templates" / name).read_bytes())
    env = Environment(loader=FileSystemLoader(str(templates)), autoescape=True)

    def t(en, zh=""):
        return f'<span class="l-en">{en}</span><span class="l-zh">{zh or en}</span>'

    env.globals["t"] = t
    payload = compile_vm(
        [
            _state("US-XNAS-AAPL", "AAPL", name="Apple", window_start="2026-09-12"),
            _state("US-XNAS-MSFT", "MSFT", name="Microsoft"),
        ],
        as_of=date(2026, 9, 1),
    )
    html = env.get_template("research_screener.html.j2").render(
        payload=payload,
        as_of=payload["as_of"],
    )
    assert 'class="site-nav"' in html
    assert "Apple" in html
    assert "Microsoft" in html
    assert THEME_NULL_EN in html or "Theme lens isn&#39;t available yet" in html
    navlinks = NAVLINKS_PATH.read_text(encoding="utf-8")
    # Shared nav family: the rendered page carries the shared chrome, and this
    # packet must not rewrite the 29-suite pin.
    assert SITE_NAV_PATH.read_text(encoding="utf-8").count("_navlinks.html.j2") == 1
    assert navlinks  # untouched pin: file still present and non-empty


def test_builder_and_engine_paths_exist():
    assert ENGINE_PATH.is_file()
    assert BUILDER_PATH.is_file()
    assert TEMPLATE_PATH.is_file()


def test_builder_renders_json_and_html(tmp_path: Path):
    pytest.importorskip("jinja2")

    root = tmp_path
    (root / "templates").mkdir()
    (root / "templates" / "research_screener.html.j2").write_bytes(TEMPLATE_PATH.read_bytes())
    for name in _SUPPORT_PARTIALS:
        (root / "templates" / name).write_bytes((REPO / "templates" / name).read_bytes())
    stockdata = root / "site" / "stockdata"
    stockdata.mkdir(parents=True)
    aapl = _state("US-XNAS-AAPL", "AAPL", name="Apple", window_start="2026-09-12")
    rec = {
        "ticker": "AAPL",
        "name": "Apple",
        "asof": "2026-09-01",
        "security_state": aapl,
        "valuation_scenario": {"v1": _valuation("AAPL", price=180, per_share=220)},
    }
    (stockdata / "AAPL.json").write_text(json.dumps(rec), encoding="utf-8")
    # write_page wants a real repo-shaped site; patch via building into tmp root
    # that also holds a stub lib.pages by invoking the pure helpers.
    from scripts.build_research_screener import build_payload, render_html

    payload = build_payload(root)
    html = render_html(root, payload)
    assert payload["rows"][0]["listing_key"] == "US-XNAS-AAPL"
    assert "Apple" in html
    assert 'class="site-nav"' in html


def test_window_only_catalyst_never_emits_a_date_or_on_date_copy():
    """H1: an estimated window is a window, never an announced date."""
    payload = compile_research_screener(
        [_state("US-XNAS-AAPL", "AAPL", name="Apple", window_start="2026-09-12")],
        as_of=date(2026, 9, 1),
    )
    catalyst = payload["rows"][0]["catalyst"]
    assert catalyst is not None
    assert "date" not in catalyst
    keys: list[str] = []
    _walk_keys(catalyst, keys)
    assert "date" not in keys
    assert catalyst["kind"] == "estimated_window"
    assert catalyst["window_start"] == "2026-09-12"
    assert catalyst["window_end"] == "2026-09-12"
    assert catalyst["event_name"]["en"] == "Estimated window"
    assert catalyst["event_name"]["zh"] == "预计窗口"
    assert catalyst["tag"]["en"] == "Estimated window — not an announced date"
    assert catalyst["tag"]["zh"] == "预计窗口 — 并非官方公布日期"
    why_en = payload["rows"][0]["why"]["en"]
    assert not _ON_DATE.search(why_en), why_en
    assert "on 2026-09-12" not in why_en
    assert "Estimated window September 12" in why_en, why_en
    assert "Estimated window — not an announced date" in why_en, why_en
    assert "Catalyst window panel" in why_en, why_en
    assert "预计窗口 — 并非官方公布日期" in payload["rows"][0]["why"]["zh"]
    assert "催化窗口面板" in payload["rows"][0]["why"]["zh"]
    glance = payload["rows"][0]["why_glance"]["en"]
    assert glance.endswith((".", "!", "?")), glance
    assert "Sales up" not in glance, glance
    assert "From Valuation" not in glance, glance
    assert "Catalyst window panel" in glance, glance


def test_catalyst_window_label_carries_the_range():
    """H1: WHEN renders as a range when window_start != window_end."""
    payload = compile_research_screener(
        [_state("US-XNAS-MSFT", "MSFT", name="Microsoft", window_start="2026-09-22", window_end="2026-09-29")],
        as_of=date(2026, 9, 1),
    )
    catalyst = payload["rows"][0]["catalyst"]
    assert catalyst is not None
    assert "September 22 – September 29" in catalyst["window_label"]["en"], catalyst
    assert "9 月 22 日 – 9 月 29 日" in catalyst["window_label"]["zh"], catalyst


def test_glance_why_is_owner_attributed():
    """H3 MAJOR-1: glance tier names the owner of the fact, not just the fact."""
    catalyst_only = compile_research_screener(
        [_state("US-XNAS-AAPL", "AAPL", name="Apple", window_start="2026-09-12")],
        as_of=date(2026, 9, 1),
    )["rows"][0]
    assert "Catalyst window panel" in catalyst_only["why_glance"]["en"]
    assert "催化窗口面板" in catalyst_only["why_glance"]["zh"]

    valuation_only = compile_research_screener(
        [_state("US-XNAS-MSFT", "MSFT", name="Microsoft")],
        [_valuation("MSFT", price=410, per_share=360)],
        as_of=date(2026, 9, 1),
    )["rows"][0]
    assert "Valuation under different assumptions" in valuation_only["why_glance"]["en"]
    assert "不同假设下的估值面板" in valuation_only["why_glance"]["zh"]


def test_engine_carries_sibling_matching_estimated_window_copy():
    """The engine owns the sibling-matching event label and tag copy."""
    source = ENGINE_PATH.read_text(encoding="utf-8")
    assert '"Estimated window"' in source
    assert '"预计窗口"' in source
    assert '"Estimated window — not an announced date"' in source
    assert '"预计窗口 — 并非官方公布日期"' in source


def test_forbidden_key_guard_covers_inflections():
    """H4.1: score/rank inflections and hyphen-split tokens are forbidden."""
    for key in (
        "score",
        "scores",
        "scored",
        "scoring",
        "rank",
        "ranks",
        "ranked",
        "ranking",
        "top",
        "best",
        "conviction",
        "convictions",
        "foo-scoring",
        "ranked_value",
    ):
        with pytest.raises(ValueError, match="forbids key"):
            _assert_no_forbidden_keys({key: 1})
    source = ENGINE_PATH.read_text(encoding="utf-8")
    assert r"scor(e|es|ed|ing)" in source
    assert r"rank(s|ed|ing)?" in source
    test_source = Path(__file__).read_text(encoding="utf-8")
    assert r"scor(e|es|ed|ing)" in test_source


def test_template_has_no_skydeck_payload_or_en_only_title():
    source = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "window.__skyDeck" not in source
    assert "id=\"rs-payload\"" not in source
    assert "application/json" not in source
    assert "title=" not in source
    # The sibling-matching label lives in engine/research_screener.py, not the
    # template — the template renders {{ row.catalyst.event_name.* }}.
    assert "about 30 trading days" in source
    assert "大约 30 个交易日" in source
    assert "research_screener.css" in source


def test_template_aria_labels_are_plain_bilingual_strings():
    """MAJOR-1: aria-label is a plain bilingual string, never t() macro output."""
    source = TEMPLATE_PATH.read_text(encoding="utf-8")
    # MAJOR-1: plain bilingual strings (no t() macro, no markup inside aria-label)
    assert 'aria-label="Lenses · 视角"' in source, source
    assert 'aria-label="Order · 排列方式"' in source, source
    assert 'aria-describedby="rs-theme-hint"' in source
    assert 'id="rs-theme-hint"' in source
    assert "Theme lens isn&#39;t available yet" in source or "Theme lens isn't available yet" in source
    assert "主题视角尚未提供。" in source


def test_no_markup_inside_any_aria_attribute():
    """MAJOR-1: aria-label must be a plain bilingual string, never t() macro output with markup."""
    source = TEMPLATE_PATH.read_text(encoding="utf-8")
    # Find every aria-label value
    import re
    for m in re.finditer(r'aria-label="([^"]*)"', source):
        val = m.group(1)
        assert "<" not in val, f"aria-label contains markup: {val!r}"
        assert ">" not in val, f"aria-label contains markup: {val!r}"


def test_receipt_li_text_has_no_duplicate_event_name():
    """MAJOR-2: receipt row renders window_label only (no duplicated event_name prefix)."""
    pytest.importorskip("jinja2")
    from jinja2 import Environment, FileSystemLoader

    def t(en, zh=""):
        return f'<span class="l-en">{en}</span><span class="l-zh">{zh or en}</span>'

    templates = TEMPLATE_PATH.parent
    env = Environment(loader=FileSystemLoader(str(templates)), autoescape=True)
    env.globals["t"] = t
    payload = compile_research_screener(
        [_state("US-XNAS-AAPL", "AAPL", name="Apple", window_start="2026-09-12")],
        [_valuation("AAPL", price=180, per_share=220)],
        as_of=date(2026, 9, 1),
    )
    html = env.get_template(TEMPLATE_PATH.name).render(payload=payload, as_of=payload["as_of"])
    # Extract text inside each <li> of the receipt
    li_texts = re.findall(r"<li>(.*?)</li>", html, re.DOTALL)
    catalyst_lis = [t for t in li_texts if "Estimated window" in t or "预计窗口" in t]
    assert catalyst_lis, f"no catalyst receipt li found in: {li_texts}"
    for li in catalyst_lis:
        # Must not have "Estimated window Estimated window" (duplicate event_name + window_label)
        assert "Estimated window Estimated window" not in li, f"duplicate event_name in receipt li: {li}"
        assert "预计窗口预计窗口" not in li, f"duplicate event_name in receipt li: {li}"


def test_why_cell_wraps_instead_of_clipping():
    css = CSS_PATH.read_text(encoding="utf-8")
    assert "text-overflow: ellipsis" not in css
    assert "white-space: nowrap" not in css
    assert "-webkit-line-clamp: 2" in css
    assert "-webkit-box-orient: vertical" in css
    theme = THEME_CSS_PATH.read_text(encoding="utf-8")
    assert "page-research-screener" not in theme
    assert ".rs-" not in theme
    assert "--rs-" not in theme


def test_help_popover_carries_full_why_not_title():
    source = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert 'class="help"' in source
    assert 'class="tip"' in source
    assert "row.why.en" in source
    assert "title=" not in source


def test_help_trigger_role_is_button():
    """Minor 2: the focusable help trigger uses role="button", matching sibling pages."""
    source = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert 'role="button"' in source, "help trigger should use role=button"


def test_en_margin_pluralisation():
    """Minor 4: EN margin copy pluralises correctly (1 point vs N points)."""
    from engine.research_screener import _assumptions_text
    # 1 point → singular
    one_pt = _assumptions_text({"sales_growth_pct": 0, "margin_delta_pp": 1, "earnings_multiple": 20})
    assert "1 point" in one_pt["en"], f"got: {one_pt['en']}"
    assert "1 points" not in one_pt["en"]
    # 2 points → plural
    two_pt = _assumptions_text({"sales_growth_pct": 0, "margin_delta_pp": 2, "earnings_multiple": 20})
    assert "2 points" in two_pt["en"], f"got: {two_pt['en']}"
    # ZH unchanged
    assert "1 个百分点" in one_pt["zh"]
    assert "2 个百分点" in two_pt["zh"]


_STAMP_RE = re.compile(r'(theme|research_screener)\.css\?v=[0-9a-f]{8}')
# Whitehouse banner tag the post-build injector adds to shipped pages (see
# scripts/inject_wh_banner.py; same shape as scripts/build_free_content.py).
_WHB_TAG_RE = re.compile(r"[ \t]*<script[^>]*\bdata-whb\b[^>]*></script>\n?")


def test_committed_page_uses_stamped_stylesheet_helper():
    """H2: page CSS is linked through the lib/pages content stamp, not a bare href."""
    html = (REPO / "site" / "research_screener.html").read_text(encoding="utf-8")
    assert re.search(r'research_screener\.css\?v=[0-9a-f]{8}', html), html[html.find("research_screener.css") - 20:html.find("research_screener.css") + 60] if "research_screener.css" in html else "missing css link"
    assert re.search(r'theme\.css\?v=[0-9a-f]{8}', html)


def test_fresh_bake_matches_committed_site_html():
    """H4.7: baking the committed payload reproduces site/research_screener.html."""
    from scripts.build_research_screener import bake_html

    payload = json.loads((REPO / "site" / "research_screener.json").read_text(encoding="utf-8"))
    baked = bake_html(REPO, payload)
    committed = (REPO / "site" / "research_screener.html").read_text(encoding="utf-8")
    # The nightly's post-build injector (scripts/inject_wh_banner.py) appends
    # one `<script defer data-whb …>` tag to the committed page AFTER the bake;
    # bake_html does not emit it (scripts/build_free_content.py strips the same
    # tag before comparing). Compare the bake, not the injection.
    assert _WHB_TAG_RE.sub("", baked) == _WHB_TAG_RE.sub("", committed)
    assert _STAMP_RE.search(baked)






# ---------------------------------------------------------------------------
# B-F06-4 Exposure-integrity regressions — executable template-script tests.
#
# The exposure behavior lives in the page's INLINE script, so these tests
# execute the real thing: the inline <script> block is extracted from
# templates/research_screener.html.j2 and run under Node's vm against a
# minimal DOM shim (embedded below as _EXPOSURE_HARNESS_JS). Node stdlib
# only; each scenario prints one JSON observation line which the assertions
# below read. Visible state is asserted (hidden flags, data-state, hold
# marks, reader call counts) rather than implementation text. No network, no
# real account, no browser required; skips honestly when node is absent.

_EXPOSURE_HARNESS_JS = r"""'use strict';
/* Exposure-integrity harness for templates/research_screener.html.j2.
   Node stdlib only (vm/fs/path). Extracts the page's inline screener script,
   runs it against a minimal DOM shim, and prints one JSON observation line
   per scenario. Python asserts on the observations. */

const fs = require('fs');
const path = require('path');
const vm = require('vm');

// ---------------------------------------------------------------- errors ---
const ERRORS = [];
process.on('unhandledRejection', (e) => {
  ERRORS.push('unhandledRejection: ' + String((e && e.message) || e));
});

// ------------------------------------------------------------------- DOM ---
class El {
  constructor(tag, attrs) {
    this.tagName = String(tag).toUpperCase();
    this.attrs = Object.assign({}, attrs || {});
    this.children = [];
    this.parent = null;
    this.hidden = false;
    this.disabled = false;
    this.leaf = null;
    this.style = {};
    this.listeners = {};
    this.classSet = new Set(
      String((attrs && attrs['class']) || '').split(/\s+/).filter(Boolean)
    );
  }
  get className() { return Array.from(this.classSet).join(' '); }
  get textContent() {
    if (this.leaf !== null) return this.leaf;
    return this.children.map((c) => c.textContent).join('');
  }
  set textContent(v) { this.children = []; this.leaf = String(v); }
  get classList() {
    const self = this;
    return {
      toggle(name, force) {
        const on = force === undefined ? !self.classSet.has(name) : !!force;
        if (on) self.classSet.add(name); else self.classSet.delete(name);
        return on;
      },
      add(n) { self.classSet.add(n); },
      remove(n) { self.classSet.delete(n); },
      contains(n) { return self.classSet.has(n); },
    };
  }
  setAttribute(k, v) {
    if (k === 'class') {
      this.classSet = new Set(String(v).split(/\s+/).filter(Boolean));
    }
    this.attrs[k] = String(v);
  }
  getAttribute(k) {
    return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null;
  }
  appendChild(child) {
    if (child.parent) child.parent.removeChild(child);
    child.parent = this;
    this.children.push(child);
    return child;
  }
  removeChild(child) {
    const i = this.children.indexOf(child);
    if (i >= 0) this.children.splice(i, 1);
    child.parent = null;
    return child;
  }
  matchesSelector(sel) {
    const tokens = String(sel).match(/(?:\[[^\]]+\])|(?:\.[\w-]+)|(?:[A-Za-z][\w-]*)/g) || [];
    for (const tok of tokens) {
      if (tok[0] === '.') {
        if (!this.classSet.has(tok.slice(1))) return false;
      } else if (tok[0] === '[') {
        const m = tok.slice(1, -1).match(/^([A-Za-z_][\w-]*)(?:="([^"]*)")?$/);
        if (!m) return false;
        if (!(m[1] in this.attrs)) return false;
        if (m[2] !== undefined && this.attrs[m[1]] !== m[2]) return false;
      } else if (this.tagName !== tok.toUpperCase()) {
        return false;
      }
    }
    return true;
  }
  walk(visit) {
    visit(this);
    this.children.forEach((c) => c.walk(visit));
  }
  querySelector(sel) {
    let found = null;
    this.walk((el) => { if (!found && el.matchesSelector(sel)) found = el; });
    return found;
  }
  querySelectorAll(sel) {
    const out = [];
    this.walk((el) => { if (el.matchesSelector(sel)) out.push(el); });
    return out;
  }
  addEventListener(type, fn) { (this.listeners[type] = this.listeners[type] || []).push(fn); }
  dispatch(type) {
    const arr = (this.listeners[type] || []).slice();
    arr.forEach((fn) => {
      try { fn({ type, preventDefault() {}, target: this }); }
      catch (e) { ERRORS.push(String((e && e.message) || e)); }
    });
    return arr.length;
  }
  click() { return this.disabled ? 0 : this.dispatch('click'); }
}

function makeStorage() {
  const m = new Map();
  return {
    getItem: (k) => (m.has(String(k)) ? m.get(String(k)) : null),
    setItem: (k, v) => { m.set(String(k), String(v)); },
    removeItem: (k) => { m.delete(String(k)); },
    key: (i) => (Array.from(m.keys())[i] !== undefined ? Array.from(m.keys())[i] : null),
    get length() { return m.size; },
  };
}

class CustomEventShim {
  constructor(type, opts) { this.type = type; Object.assign(this, opts || {}); }
}

function makeDocument(readyState) {
  const html = new El('html');
  const body = new El('body', { class: 'page-research-screener' });
  html.appendChild(body);
  const doc = {
    readyState: readyState || 'complete',
    documentElement: html,
    body,
    listeners: {},
    getElementById(id) {
      let found = null;
      body.walk((el) => { if (!found && el.attrs.id === id) found = el; });
      return found;
    },
    querySelector(sel) { return body.querySelector(sel); },
    querySelectorAll(sel) { return body.querySelectorAll(sel); },
    addEventListener(type, fn) { (this.listeners[type] = this.listeners[type] || []).push(fn); },
    dispatchEvent(ev) {
      const arr = (this.listeners[ev.type] || []).slice();
      arr.forEach((fn) => {
        try { fn(ev); } catch (e) { ERRORS.push(String((e && e.message) || e)); }
      });
      return arr.length;
    },
    createElement(tag) { return new El(tag); },
  };
  return doc;
}

// -------------------------------------------------------------- fixtures ---
const ROWS = [
  { key: 'US-XNAS-AAPL', ticker: 'AAPL', name: 'Apple', catalystDate: '2026-09-12', hasCatalyst: true },
  { key: 'US-XNAS-MSFT', ticker: 'MSFT', name: 'Microsoft', catalystDate: '', hasCatalyst: false },
  { key: 'US-XNAS-TSLA', ticker: 'TSLA', name: 'Tesla', catalystDate: '2026-09-20', hasCatalyst: true },
];

function buildPage(doc) {
  const main = new El('main', { class: 'rs', id: 'rs-main' });
  doc.body.appendChild(main);
  const chips = new El('div', { class: 'rs-chips', role: 'group' });
  [['theme', true], ['catalyst', false], ['exposure', false], ['valuation', false]].forEach((pair) => {
    const b = new El('button', {
      type: 'button',
      class: 'rs-chip' + (pair[1] ? ' is-disabled' : ''),
      'data-lens': pair[0],
      'aria-pressed': 'false',
    });
    if (pair[1]) { b.disabled = true; b.setAttribute('disabled', ''); b.setAttribute('aria-disabled', 'true'); }
    chips.appendChild(b);
  });
  main.appendChild(chips);
  const orderWrap = new El('div', { class: 'rs-order', role: 'group' });
  [['name', true], ['next_catalyst_date', false]].forEach((pair) => {
    orderWrap.appendChild(new El('button', {
      type: 'button',
      class: 'rs-order-btn' + (pair[1] ? ' is-on' : ''),
      'data-order': pair[0],
      'aria-pressed': pair[1] ? 'true' : 'false',
    }));
  });
  main.appendChild(orderWrap);
  main.appendChild(new El('p', { class: 'rs-theme-null', id: 'rs-theme-hint', 'data-rs-theme-null': '' }));

  const notice = new El('p', { class: 'rs-exposure-null', 'data-rs-exposure-null': '', 'data-state': 'signedout' });
  notice.hidden = true;
  const en = new El('span', { class: 'l-en' });
  en.textContent = 'Sign in to see which of these you hold.';
  const zh = new El('span', { class: 'l-zh' });
  zh.textContent = '登录后即可看到你持有其中哪些。';
  const link = new El('a', { class: 'rs-portfolio-link', 'data-rs-portfolio-link': '', href: 'watchlist.html' });
  link.hidden = true;
  const len = new El('span', { class: 'l-en' });
  len.textContent = 'Open Portfolio';
  const lzh = new El('span', { class: 'l-zh' });
  lzh.textContent = '打开投资组合';
  link.appendChild(len);
  link.appendChild(lzh);
  notice.appendChild(en);
  notice.appendChild(zh);
  notice.appendChild(link);
  main.appendChild(notice);

  const empty = new El('p', { class: 'rs-empty', 'data-rs-empty': '' });
  empty.hidden = true;
  main.appendChild(empty);

  const list = new El('ol', { class: 'rs-list', 'data-rs-list': '' });
  main.appendChild(list);
  ROWS.forEach((r) => {
    const li = new El('li', {
      class: 'rs-row',
      'data-listing-key': r.key,
      'data-ticker': r.ticker,
      'data-name': r.name,
      'data-catalyst-date': r.catalystDate,
      'data-has-catalyst': r.hasCatalyst ? '1' : '0',
      'data-has-valuation': '0',
      'data-has-exposure': '0',
    });
    const hold = new El('li', { class: 'rs-hold-line', 'data-rs-hold': '' });
    hold.hidden = true;
    li.appendChild(hold);
    list.appendChild(li);
  });
  return { notice, empty, list, link };
}

function makeAuth(opts) {
  opts = opts || {};
  const subs = [];
  const auth = {
    hasSession: () => !!opts.session,
    onChange: (fn) => { subs.push(fn); },
    open() {},
  };
  auth.__fire = () => { subs.slice().forEach((fn) => fn({ id: opts.uid || null })); };
  return auth;
}

function makeStore(opts) {
  opts = opts || {};
  let calls = 0;
  const readStateFn = opts.readState || (() => ({
    authority: 'cloud', state: 'ready', last_good_at: '2026-10-13T00:00:00Z', warning: null,
  }));
  const store = {
    user: () => (opts.user === undefined ? { id: 'u-1', email: 'u1@example.com' } : opts.user),
    portfolio: {
      list: () => {
        calls += 1;
        if (opts.list) return opts.list();
        return Promise.resolve(opts.items !== undefined ? opts.items : []);
      },
      readState: readStateFn,
    },
  };
  store.__calls = () => calls;
  return store;
}

// -------------------------------------------------------------- sandbox ----
function makeSandbox(opts) {
  opts = opts || {};
  const doc = makeDocument(opts.readyState || 'complete');
  const timers = [];
  const sandbox = {
    document: doc,
    CustomEvent: CustomEventShim,
    localStorage: opts.localStorage || makeStorage(),
    sessionStorage: makeStorage(),
    location: { reload() { sandbox.__reloads = (sandbox.__reloads || 0) + 1; } },
    navigator: { languages: ['en-US'], language: 'en-US' },
    setTimeout(fn) { const t = { fn }; timers.push(t); return t; },
    clearTimeout(t) { const i = timers.indexOf(t); if (i >= 0) timers.splice(i, 1); },
    console: { warn() {}, error() {}, log() {} },
    Promise, Array, Object, String, JSON, Date, Number, Boolean, RegExp, Error, TypeError,
    isNaN,
  };
  const winListeners = {};
  sandbox.addEventListener = (type, fn) => {
    (winListeners[type] = winListeners[type] || []).push(fn);
  };
  sandbox.removeEventListener = (type, fn) => {
    const arr = winListeners[type] || [];
    const i = arr.indexOf(fn);
    if (i >= 0) arr.splice(i, 1);
  };
  sandbox.window = sandbox;
  const ctx = { sandbox, doc, timers, errors: ERRORS };
  return ctx;
}

async function settle(ctx, rounds) {
  const n = rounds || 8;
  for (let i = 0; i < n; i++) {
    await new Promise((r) => setImmediate(r));
    const pending = ctx.timers.splice(0, ctx.timers.length);
    pending.forEach((t) => {
      try { t.fn(); } catch (e) { ERRORS.push(String((e && e.message) || e)); }
    });
  }
}

function extractInlineScript(templateSource) {
  const blocks = [];
  const re = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
  let m;
  while ((m = re.exec(templateSource)) !== null) {
    if (/\bsrc\s*=/.test(m[1])) continue;
    blocks.push(m[2]);
  }
  const main = blocks.find((b) => b.indexOf('data-rs-list') !== -1);
  if (!main) throw new Error('screener inline script not found in template');
  return main;
}

function snapshot(ctx, page, storeRef) {
  const rows = page.list.querySelectorAll('.rs-row');
  return {
    order: rows.map((r) => r.getAttribute('data-ticker')),
    rows: rows.map((r) => {
      const hold = r.querySelector('[data-rs-hold]');
      return {
        ticker: r.getAttribute('data-ticker'),
        hidden: !!r.hidden,
        hasExposure: r.getAttribute('data-has-exposure'),
        holdHidden: hold ? !!hold.hidden : null,
      };
    }),
    emptyHidden: !!page.empty.hidden,
    notice: {
      hidden: !!page.notice.hidden,
      state: page.notice.getAttribute('data-state'),
      en: page.notice.querySelector('.l-en').textContent,
      zh: page.notice.querySelector('.l-zh').textContent,
      linkHidden: !!page.link.hidden,
      linkHref: page.link.getAttribute('href'),
    },
    readerCalls: storeRef ? storeRef.__calls() : null,
    errors: ERRORS.slice(),
  };
}

// ------------------------------------------------------------ scenarios ----
function chip(doc, lens) { return doc.querySelector('.rs-chip[data-lens="' + lens + '"]'); }
function orderBtn(doc, order) { return doc.querySelector('.rs-order-btn[data-order="' + order + '"]'); }

const SCENARIOS = {
  async closed_only(ctx) {
    const page = buildPage(ctx.doc);
    ctx.sandbox.MDXAuth = makeAuth({ session: true });
    const store = makeStore({ items: [{ ticker: 'AAPL', status: 'closed' }] });
    ctx.sandbox.WatchStore = store;
    runInline(ctx);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx);
    return snapshot(ctx, page, store);
  },

  // Real WatchStore returns resolved null while its shared client initializes.
  async loading_resolved_null(ctx) {
    const page = buildPage(ctx.doc);
    ctx.sandbox.MDXAuth = makeAuth({ session: true });
    const store = makeStore({ items: null,
      readState: () => ({ authority: 'cloud', state: 'loading' }) });
    ctx.sandbox.WatchStore = store;
    runInline(ctx);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx);
    return snapshot(ctx, page, store);
  },

  async missing_read_state(ctx) {
    const page = buildPage(ctx.doc);
    ctx.sandbox.MDXAuth = makeAuth({ session: true });
    const store = makeStore({ items: [] });
    delete store.portfolio.readState;
    ctx.sandbox.WatchStore = store;
    runInline(ctx);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx);
    return snapshot(ctx, page, store);
  },

  // A new readiness/auth event must invalidate even an already-published book.
  async refresh_published(ctx) {
    const page = buildPage(ctx.doc);
    const auth = makeAuth({ session: true });
    ctx.sandbox.MDXAuth = auth;
    let refresh = false, resolveRefresh;
    const store = makeStore({ list: () => refresh
      ? new Promise((resolve) => { resolveRefresh = resolve; })
      : Promise.resolve([{ ticker: 'AAPL' }]) });
    ctx.sandbox.WatchStore = store;
    runInline(ctx);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx);
    const before = snapshot(ctx, page, store);
    refresh = true;
    ctx.doc.dispatchEvent({ type: 'wl-auth' });
    const during = snapshot(ctx, page, store);
    if (resolveRefresh) resolveRefresh([{ ticker: 'TSLA' }]);
    await settle(ctx);
    const after = snapshot(ctx, page, store);
    auth.__fire();
    const authRefresh = snapshot(ctx, page, store);
    if (resolveRefresh) resolveRefresh([]);
    await settle(ctx);
    return { before, during, after, authRefresh, final: snapshot(ctx, page, store) };
  },

  async replaced_store_published(ctx) {
    const page = buildPage(ctx.doc);
    ctx.sandbox.MDXAuth = makeAuth({ session: true });
    const storeA = makeStore({ items: [{ ticker: 'AAPL' }] });
    ctx.sandbox.WatchStore = storeA;
    runInline(ctx);
    await settle(ctx);
    let resolveB;
    const storeB = makeStore({ list: () => new Promise((r) => { resolveB = r; }) });
    ctx.sandbox.WatchStore = storeB;
    chip(ctx.doc, 'exposure').click();
    const during = snapshot(ctx, page, storeB);
    if (resolveB) resolveB([{ ticker: 'MSFT' }]);
    await settle(ctx);
    return { during, after: snapshot(ctx, page, storeB) };
  },

  // Signed out: notice copy, no reader call, rows stay visible.
  async signed_out(ctx) {
    const page = buildPage(ctx.doc);
    ctx.sandbox.MDXAuth = makeAuth({ session: false });
    const store = makeStore({ items: [{ ticker: 'AAPL' }] });
    ctx.sandbox.WatchStore = store;
    runInline(ctx);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx);
    return snapshot(ctx, page, store);
  },

  // Real watchstore.js, no sync host (dormant init), MDXAuth signed in,
  // benign seeded local AAPL book. Reader must never be called.
  async no_host_actual_watchstore(ctx) {
    const page = buildPage(ctx.doc);
    ctx.sandbox.MDXAuth = makeAuth({ session: true, uid: 'u-1' });
    ctx.sandbox.localStorage.setItem('mdash.pf.v1', JSON.stringify({
      v: 1,
      rows: [{ id: 'loc-1', ticker: 'AAPL', shares: 10, entry_price: 1, entry_date: null, notes: null, status: 'open' }],
    }));
    // Exercise the original unsafe reader after the real dormant API exists.
    // Boot-before-later-scripts has a separate scenario; starting the old inline
    // script before WatchStore here would pass merely because no reader exists.
    runSource(ctx, ctx.files.watchstore);
    const store = ctx.sandbox.WatchStore;
    const realList = store.portfolio.list;
    let calls = 0;
    store.portfolio.list = function () { calls += 1; return realList.apply(this, arguments); };
    store.__calls = () => calls;
    runInline(ctx);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx);
    const out = snapshot(ctx, page, store);
    out.watchstorePresent = !!ctx.sandbox.WatchStore && typeof ctx.sandbox.WatchStore.user === 'function';
    out.storeUserIsNull = ctx.sandbox.WatchStore.user() === null;
    return out;
  },

  async missing_store(ctx) {
    const page = buildPage(ctx.doc);
    ctx.sandbox.MDXAuth = makeAuth({ session: true, uid: 'u-1' });
    runInline(ctx);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx);
    return snapshot(ctx, page, null);
  },

  async missing_user(ctx) {
    const page = buildPage(ctx.doc);
    ctx.sandbox.MDXAuth = makeAuth({ session: true, uid: 'u-1' });
    const store = makeStore({ user: null, items: [{ ticker: 'AAPL' }] });
    ctx.sandbox.WatchStore = store;
    runInline(ctx);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx);
    return snapshot(ctx, page, store);
  },

  async missing_api(ctx) {
    const page = buildPage(ctx.doc);
    ctx.sandbox.MDXAuth = makeAuth({ session: true, uid: 'u-1' });
    ctx.sandbox.WatchStore = { user: () => ({ id: 'u-1' }) };
    runInline(ctx);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx);
    return snapshot(ctx, page, null);
  },

  async loading_pending(ctx) {
    const page = buildPage(ctx.doc);
    ctx.sandbox.MDXAuth = makeAuth({ session: true, uid: 'u-1' });
    const store = makeStore({
      list: () => new Promise(() => {}),
      readState: () => ({ authority: 'cloud', state: 'loading', last_good_at: null, warning: null }),
    });
    ctx.sandbox.WatchStore = store;
    runInline(ctx);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx);
    return snapshot(ctx, page, store);
  },

  async error_null(ctx) {
    const page = buildPage(ctx.doc);
    ctx.sandbox.MDXAuth = makeAuth({ session: true, uid: 'u-1' });
    const store = makeStore({
      items: null,
      readState: () => ({ authority: 'cloud', state: 'error', last_good_at: null, warning: 'cloud-unavailable' }),
    });
    ctx.sandbox.WatchStore = store;
    runInline(ctx);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx);
    return snapshot(ctx, page, store);
  },

  async rejection(ctx) {
    const page = buildPage(ctx.doc);
    ctx.sandbox.MDXAuth = makeAuth({ session: true, uid: 'u-1' });
    const store = makeStore({ list: () => Promise.reject(new Error('rls denied')) });
    ctx.sandbox.WatchStore = store;
    runInline(ctx);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx);
    return snapshot(ctx, page, store);
  },

  async sync_throw(ctx) {
    const page = buildPage(ctx.doc);
    ctx.sandbox.MDXAuth = makeAuth({ session: true, uid: 'u-1' });
    const store = makeStore({ list() { throw new Error('boom'); } });
    ctx.sandbox.WatchStore = store;
    runInline(ctx);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx);
    return snapshot(ctx, page, store);
  },

  async malformed_items(ctx) {
    const page = buildPage(ctx.doc);
    ctx.sandbox.MDXAuth = makeAuth({ session: true, uid: 'u-1' });
    const store = makeStore({ items: { length: 2 } });
    ctx.sandbox.WatchStore = store;
    runInline(ctx);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx);
    return snapshot(ctx, page, store);
  },

  async malformed_rows_mixed(ctx) {
    const page = buildPage(ctx.doc);
    ctx.sandbox.MDXAuth = makeAuth({ session: true, uid: 'u-1' });
    const store = makeStore({
      items: [null, 42, {}, { ticker: 'aapl' }, { ticker: 'MSFT', status: 'closed' }, { ticker: '' }],
    });
    ctx.sandbox.WatchStore = store;
    runInline(ctx);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx);
    return snapshot(ctx, page, store);
  },

  async malformed_rows_all(ctx) {
    const page = buildPage(ctx.doc);
    ctx.sandbox.MDXAuth = makeAuth({ session: true, uid: 'u-1' });
    const store = makeStore({ items: [null, 'junk', 5] });
    ctx.sandbox.WatchStore = store;
    runInline(ctx);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx);
    return snapshot(ctx, page, store);
  },

  async malformed_rows_closed(ctx) {
    const page = buildPage(ctx.doc);
    ctx.sandbox.MDXAuth = makeAuth({ session: true });
    const store = makeStore({ items: [{ ticker: 'AAPL', status: 'closed' }, null] });
    ctx.sandbox.WatchStore = store;
    runInline(ctx);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx);
    return snapshot(ctx, page, store);
  },

  async local_ready(ctx) {
    const page = buildPage(ctx.doc);
    ctx.sandbox.MDXAuth = makeAuth({ session: true, uid: 'u-1' });
    const store = makeStore({
      items: [{ ticker: 'AAPL', status: 'open' }],
      readState: () => ({ authority: 'local', state: 'ready', last_good_at: null, warning: null }),
    });
    ctx.sandbox.WatchStore = store;
    runInline(ctx);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx);
    return snapshot(ctx, page, store);
  },

  async degraded_cloud_with_rows(ctx) {
    const page = buildPage(ctx.doc);
    ctx.sandbox.MDXAuth = makeAuth({ session: true, uid: 'u-1' });
    const store = makeStore({
      items: [{ ticker: 'AAPL' }],
      readState: () => ({ authority: 'cloud', state: 'degraded', last_good_at: '2026-10-01T00:00:00Z', warning: 'cloud-unavailable' }),
    });
    ctx.sandbox.WatchStore = store;
    runInline(ctx);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx);
    return snapshot(ctx, page, store);
  },

  async verified_cloud_empty(ctx) {
    const page = buildPage(ctx.doc);
    ctx.sandbox.MDXAuth = makeAuth({ session: true, uid: 'u-1' });
    const store = makeStore({ items: [] });
    ctx.sandbox.WatchStore = store;
    runInline(ctx);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx);
    return snapshot(ctx, page, store);
  },

  async ready_open_closed(ctx) {
    const page = buildPage(ctx.doc);
    ctx.sandbox.MDXAuth = makeAuth({ session: true, uid: 'u-1' });
    const store = makeStore({
      items: [{ ticker: 'aapl' }, { ticker: 'MSFT', status: 'closed' }, { ticker: 'TSLA' }],
    });
    ctx.sandbox.WatchStore = store;
    runInline(ctx);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx);
    return snapshot(ctx, page, store);
  },

  // Account switch while read A pending: read B (new owner) must win; A must
  // never publish. Hold marks must clear at the switch.
  async account_switch_pending(ctx) {
    const page = buildPage(ctx.doc);
    const auth = makeAuth({ session: true, uid: 'u-1' });
    ctx.sandbox.MDXAuth = auth;
    let resolveA;
    const storeA = makeStore({ user: { id: 'u-1' }, list: () => new Promise((res) => { resolveA = res; }) });
    ctx.sandbox.WatchStore = storeA;
    runInline(ctx);
    await settle(ctx, 2);
    const midMarks = snapshot(ctx, page, storeA);

    let resolveB;
    const storeB = makeStore({ user: { id: 'u-2' }, list: () => new Promise((res) => { resolveB = res; }) });
    ctx.sandbox.WatchStore = storeB;
    auth.__fire();
    ctx.doc.dispatchEvent({ type: 'wl-auth' });
    await settle(ctx, 2);
    const midSwitch = snapshot(ctx, page, storeB);

    resolveB([{ ticker: 'TSLA' }]);
    await settle(ctx);
    const afterB = snapshot(ctx, page, storeB);

    resolveA([{ ticker: 'AAPL' }]);
    await settle(ctx);
    const afterALate = snapshot(ctx, page, storeB);

    return { midMarks, midSwitch, afterB, afterALate };
  },

  async signout_during_pending(ctx) {
    const page = buildPage(ctx.doc);
    const auth = makeAuth({ session: true, uid: 'u-1' });
    ctx.sandbox.MDXAuth = auth;
    let resolveA;
    const store = makeStore({ list: () => new Promise((res) => { resolveA = res; }) });
    ctx.sandbox.WatchStore = store;
    runInline(ctx);
    await settle(ctx, 2);
    auth.hasSession = () => false;
    auth.__fire();
    ctx.doc.dispatchEvent({ type: 'wl-auth' });
    await settle(ctx, 2);
    const mid = snapshot(ctx, page, store);
    resolveA([{ ticker: 'AAPL' }]);
    await settle(ctx);
    const after = snapshot(ctx, page, store);
    return { mid, after };
  },

  // Same owner re-fires wl-auth while a read is pending: the fresh read must
  // supersede the old completion.
  async superseded_completion(ctx) {
    const page = buildPage(ctx.doc);
    const auth = makeAuth({ session: true, uid: 'u-1' });
    ctx.sandbox.MDXAuth = auth;
    const resolvers = [];
    const store = makeStore({
      list: () => new Promise((res) => { resolvers.push(res); }),
    });
    ctx.sandbox.WatchStore = store;
    runInline(ctx);
    await settle(ctx, 2);
    ctx.doc.dispatchEvent({ type: 'wl-auth' });
    await settle(ctx, 2);
    resolvers[0]([{ ticker: 'AAPL' }]);
    await settle(ctx);
    const afterOld = snapshot(ctx, page, store);
    resolvers[1]([{ ticker: 'TSLA' }]);
    await settle(ctx);
    const afterNew = snapshot(ctx, page, store);
    return { reads: resolvers.length, afterOld, afterNew };
  },

  async wl_auth_readiness_recovery(ctx) {
    const page = buildPage(ctx.doc);
    ctx.sandbox.MDXAuth = makeAuth({ session: true, uid: 'u-1' });
    let ready = false;
    const store = makeStore({
      items: [],
      readState: () => (ready
        ? { authority: 'cloud', state: 'ready', last_good_at: 't', warning: null }
        : { authority: 'cloud', state: 'loading', last_good_at: null, warning: null }),
    });
    const realList = store.portfolio.list;
    store.portfolio.list = function () {
      return ready ? Promise.resolve([{ ticker: 'MSFT' }]) : realList.call(this);
    };
    ctx.sandbox.WatchStore = store;
    runInline(ctx);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx);
    const before = snapshot(ctx, page, store);
    ready = true;
    ctx.doc.dispatchEvent({ type: 'wl-auth' });
    await settle(ctx);
    const after = snapshot(ctx, page, store);
    return { before, after };
  },

  async boot_before_later_scripts(ctx) {
    const page = buildPage(ctx.doc);
    ctx.doc.readyState = 'loading';
    ctx.sandbox.MDXAuth = makeAuth({ session: true, uid: 'u-1' });
    runInline(ctx);                       // scripts later in the page have NOT run yet
    const store = makeStore({ items: [{ ticker: 'AAPL' }] });
    ctx.sandbox.WatchStore = store;       // the later <script src> defines the store
    const callsAtEval = store.__calls();
    (ctx.doc.listeners['DOMContentLoaded'] || []).slice().forEach((fn) => fn({ type: 'DOMContentLoaded' }));
    await settle(ctx);
    const out = snapshot(ctx, page, store);
    out.callsAtEval = callsAtEval;
    return out;
  },

  async exposure_off_recovery(ctx) {
    const page = buildPage(ctx.doc);
    ctx.sandbox.MDXAuth = makeAuth({ session: true, uid: 'u-1' });
    const store = makeStore({ items: [{ ticker: 'AAPL' }] });
    ctx.sandbox.WatchStore = store;
    runInline(ctx);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx);
    const on = snapshot(ctx, page, store);
    chip(ctx.doc, 'exposure').click();    // off
    await settle(ctx, 2);
    const off = snapshot(ctx, page, store);
    chip(ctx.doc, 'exposure').click();    // on again
    await settle(ctx, 2);
    const onAgain = snapshot(ctx, page, store);
    return { on, off, onAgain };
  },

  async lens_and_order_regression(ctx) {
    const page = buildPage(ctx.doc);
    ctx.sandbox.MDXAuth = makeAuth({ session: true, uid: 'u-1' });
    const store = makeStore({ items: [{ ticker: 'TSLA' }] });
    ctx.sandbox.WatchStore = store;
    runInline(ctx);
    await settle(ctx);
    const base = snapshot(ctx, page, store);
    chip(ctx.doc, 'catalyst').click();
    await settle(ctx, 2);
    const catalystOn = snapshot(ctx, page, store);
    orderBtn(ctx.doc, 'next_catalyst_date').click();
    await settle(ctx, 2);
    const dateOrder = snapshot(ctx, page, store);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx, 2);
    const exposureOn = snapshot(ctx, page, store);
    chip(ctx.doc, 'exposure').click();
    await settle(ctx, 2);
    const exposureOff = snapshot(ctx, page, store);
    return { base, catalystOn, dateOrder, exposureOn, exposureOff };
  },
};

// ---------------------------------------------------------------- runner ---
let TPL_SOURCE = '';
let WATCHSTORE_SOURCE = '';

function runInline(ctx) {
  vm.runInNewContext(TPL_SOURCE, ctx.sandbox, { filename: 'research_screener.inline.js' });
}
function runSource(ctx, src, name) {
  vm.runInNewContext(src, ctx.sandbox, { filename: name || 'watchstore.js' });
}

async function main() {
  const dir = process.argv[2];
  const ids = process.argv.slice(3);
  TPL_SOURCE = fs.readFileSync(path.join(dir, 'research_screener_inline.html.js'), 'utf8');
  const wsPath = path.join(dir, 'watchstore.js');
  WATCHSTORE_SOURCE = fs.existsSync(wsPath) ? fs.readFileSync(wsPath, 'utf8') : '';

  for (const id of ids) {
    ERRORS.length = 0;
    const fn = SCENARIOS[id];
    if (!fn) {
      process.stdout.write(JSON.stringify({ scenario: id, error: 'unknown scenario' }) + '\n');
      continue;
    }
    const ctx = makeSandbox({ readyState: 'complete' });
    ctx.files = { watchstore: WATCHSTORE_SOURCE };
    let out;
    try {
      const res = await fn(ctx);
      out = Object.assign({ scenario: id, errors: ERRORS.slice() }, res);
    } catch (e) {
      out = { scenario: id, harnessError: String((e && e.stack) || e) };
    }
    process.stdout.write(JSON.stringify(out) + '\n');
  }
}

main().catch((e) => { console.error(e); process.exit(1); });"""


def _exposure_node_available() -> bool:
    import shutil

    return shutil.which("node") is not None


def _extract_screener_inline_script(source: str) -> str:
    blocks = []
    for m in re.finditer(r"<script\b([^>]*)>([\s\S]*?)</script>", source):
        if re.search(r"\bsrc\s*=", m.group(1)):
            continue
        blocks.append(m.group(2))
    mains = [b for b in blocks if "data-rs-list" in b]
    assert len(mains) == 1, "expected exactly one inline screener script"
    return mains[0]


def _run_exposure_scenarios(tmp_path: Path, scenario_ids: list[str]) -> dict:
    """Extract + execute the template's inline script under Node, return the
    per-scenario JSON observations."""
    import subprocess

    assert _exposure_node_available() or pytest.skip("node is not installed")
    harness = tmp_path / "research_screener_exposure_harness.js"
    harness.write_text(_EXPOSURE_HARNESS_JS, encoding="utf-8")
    inline = tmp_path / "research_screener_inline.html.js"
    inline.write_text(
        _extract_screener_inline_script(TEMPLATE_PATH.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    watchstore = tmp_path / "watchstore.js"
    ws_src = TEMPLATE_PATH.parent / "watchstore.js"
    if ws_src.is_file():
        watchstore.write_bytes(ws_src.read_bytes())
    else:
        watchstore.write_text("", encoding="utf-8")
    proc = subprocess.run(
        ["node", str(harness), str(tmp_path), *scenario_ids],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, f"harness failed: {proc.stderr[-2000:]}"
    out: dict[str, dict] = {}
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        out[rec["scenario"]] = rec
    missing = [s for s in scenario_ids if s not in out]
    assert not missing, f"harness did not report: {missing}"
    broken = {s: r["harnessError"] for s, r in out.items() if "harnessError" in r}
    assert not broken, f"harness errors: {broken}"
    for rec in out.values():
        assert rec.get("errors") == [], f"uncaught page errors: {rec.get('errors')}"
    return out


def _held(scen: dict) -> list[str]:
    return [r["ticker"] for r in scen["rows"] if r["hasExposure"] == "1"]


def _visible(scen: dict) -> list[str]:
    return [r["ticker"] for r in scen["rows"] if not r["hidden"]]


def test_exposure_notice_variants_and_portfolio_destination():
    """COPY/DOM: same rs-exposure-null container/class, four honest EN/ZH
    states, existing watchlist.html destination, no new CSS or inline styles."""
    source = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert '<p class="rs-exposure-null" data-rs-exposure-null' in source
    # Signed-out keeps the canonical engine copy verbatim.
    assert source.count(EXPOSURE_NULL_EN) >= 2  # static and post-boot copy agree
    assert source.count(EXPOSURE_NULL_ZH) >= 2
    for en, zh in (
        ("Loading your holdings…", "正在读取你的持仓…"),
        (
            "Holdings are unavailable here.",
            "此处暂时无法读取持仓。",
        ),
        (
            "Current holdings could not be verified.",
            "暂时无法确认当前持仓。",
        ),
    ):
        assert en in source, en
        assert zh in source, zh
    assert 'href="watchlist.html"' in source
    assert "<span class=\"l-en\">Open Portfolio</span><span class=\"l-zh\">打开投资组合</span>" in source
    # No new styling mechanism: no inline styles, no style block, canonical CSS.
    assert "style=" not in source
    assert "<style" not in source


def test_exposure_signed_out_shows_notice_and_keeps_rows_visible(tmp_path: Path):
    """Signed out: the notice says so, rows are NOT hidden (never a claimed
    zero), and the reader is never called."""
    (out,) = [_run_exposure_scenarios(tmp_path, ["signed_out"])[k] for k in ["signed_out"]]
    notice = out["notice"]
    assert notice["hidden"] is False
    assert notice["state"] == "signedout"
    assert notice["en"] == EXPOSURE_NULL_EN
    assert notice["zh"] == EXPOSURE_NULL_ZH
    assert notice["linkHidden"] is True
    assert _visible(out) == ["AAPL", "MSFT", "TSLA"]
    assert out["emptyHidden"] is True  # no false "No names match"
    assert out["readerCalls"] == 0


def test_exposure_dormant_watchstore_local_book_is_never_read(tmp_path: Path):
    """The real watchstore.js with NO sync host stays dormant; a signed-in
    MDXAuth session must not read (or display) the anonymous local book."""
    rec = _run_exposure_scenarios(tmp_path, ["no_host_actual_watchstore"])[
        "no_host_actual_watchstore"
    ]
    assert rec["watchstorePresent"] is True
    assert rec["storeUserIsNull"] is True
    assert rec["readerCalls"] == 0
    assert _held(rec) == []
    assert _visible(rec) == ["AAPL", "MSFT", "TSLA"]
    assert rec["notice"]["hidden"] is False
    assert rec["notice"]["state"] == "unavailable"
    assert rec["notice"]["linkHidden"] is False
    assert rec["notice"]["linkHref"] == "watchlist.html"


def test_exposure_missing_store_user_or_api_never_claims_zero(tmp_path: Path):
    """Missing WatchStore, missing owner id, or missing portfolio API: rows
    keep their ordinary visibility, no hold marks, reader untouched."""
    out = _run_exposure_scenarios(
        tmp_path, ["missing_store", "missing_user", "missing_api"]
    )
    for name in ("missing_store", "missing_user", "missing_api"):
        rec = out[name]
        assert rec["notice"]["state"] == "unavailable", name
        assert rec["notice"]["hidden"] is False
        assert _held(rec) == [], name
        assert _visible(rec) == ["AAPL", "MSFT", "TSLA"], name
        assert rec["readerCalls"] in (0, None), name
        assert rec["emptyHidden"] is True, name


def test_exposure_unverified_reads_never_become_no_names_match(tmp_path: Path):
    """Loading, null/error, rejection, synchronous throw, a non-array answer
    and an all-malformed array: every row stays visible, nothing is marked,
    and the honest degraded/loading copy shows instead of the empty state."""
    out = _run_exposure_scenarios(
        tmp_path,
        [
            "loading_pending",
            "error_null",
            "rejection",
            "sync_throw",
            "malformed_items",
            "malformed_rows_all",
        ],
    )
    loading = out["loading_pending"]
    assert loading["notice"]["state"] == "loading"
    assert loading["notice"]["en"] == "Loading your holdings…"
    assert loading["notice"]["zh"] == "正在读取你的持仓…"
    for name in (
        "error_null",
        "rejection",
        "sync_throw",
        "malformed_items",
        "malformed_rows_all",
    ):
        rec = out[name]
        assert rec["notice"]["state"] == "degraded", name
        assert rec["notice"]["hidden"] is False
        assert rec["notice"]["linkHidden"] is False, name  # Open Portfolio link
        assert rec["notice"]["linkHref"] == "watchlist.html"
        assert _held(rec) == [], name
        assert _visible(rec) == ["AAPL", "MSFT", "TSLA"], name
        assert rec["emptyHidden"] is True, name


def test_exposure_ready_read_marks_open_rows_only(tmp_path: Path):
    """A verified cloud-ready read excludes closed lots and filters held names."""
    ready = _run_exposure_scenarios(tmp_path, ["ready_open_closed"])["ready_open_closed"]
    assert _held(ready) == ["AAPL", "TSLA"]
    assert _visible(ready) == ["AAPL", "TSLA"]
    by_ticker = {r["ticker"]: r for r in ready["rows"]}
    assert by_ticker["MSFT"]["hidden"] is True
    assert by_ticker["MSFT"]["holdHidden"] is True
    assert ready["notice"]["hidden"] is True
    assert ready["emptyHidden"] is True


def test_exposure_partial_malformed_book_does_not_claim_completeness(tmp_path: Path):
    """Discarding bad rows would falsely claim the partial book is complete,
    including a known zero when its only valid positions are closed."""
    out = _run_exposure_scenarios(tmp_path, ["malformed_rows_mixed", "malformed_rows_closed"])
    for rec in out.values():
        assert rec["notice"]["state"] == "degraded"
        assert _held(rec) == []
        assert rec["emptyHidden"] is True


def test_exposure_local_and_degraded_answers_are_never_published(tmp_path: Path):
    """An authority:'local' ready answer and a degraded last-good cloud answer
    are both refused: no marks, degraded copy, no false zero."""
    out = _run_exposure_scenarios(
        tmp_path, ["local_ready", "degraded_cloud_with_rows"]
    )
    for name in ("local_ready", "degraded_cloud_with_rows"):
        rec = out[name]
        assert rec["notice"]["state"] == "degraded", name
        assert _held(rec) == [], name
        assert _visible(rec) == ["AAPL", "MSFT", "TSLA"], name
        assert rec["emptyHidden"] is True, name
        assert rec["readerCalls"] >= 1, name  # the read happened, the answer was refused


def test_exposure_verified_cloud_empty_is_the_only_lens_empty(tmp_path: Path):
    """A verified cloud-ready EMPTY answer is the only thing that may produce
    the lens's empty state under Exposure."""
    rec = _run_exposure_scenarios(tmp_path, ["verified_cloud_empty"])[
        "verified_cloud_empty"
    ]
    assert rec["notice"]["hidden"] is True
    assert _visible(rec) == []
    assert rec["emptyHidden"] is False
    assert _held(rec) == []


def test_exposure_auth_transitions_invalidate_pending_reads(tmp_path: Path):
    """Account switch, sign-out and a same-owner readiness re-fire while a
    read is pending: marks clear at once, the old completion never publishes,
    and the new owner's read wins."""
    out = _run_exposure_scenarios(
        tmp_path,
        ["account_switch_pending", "signout_during_pending", "superseded_completion"],
    )
    sw = out["account_switch_pending"]
    assert _held(sw["midMarks"]) == []
    assert all(r["hasExposure"] == "0" for r in sw["midSwitch"]["rows"])  # cleared at switch
    assert _held(sw["afterB"]) == ["TSLA"]  # owner B's read published
    assert _held(sw["afterALate"]) == ["TSLA"]  # owner A's late completion ignored
    so = out["signout_during_pending"]
    assert all(r["hasExposure"] == "0" for r in so["mid"]["rows"])  # cleared at sign-out
    assert _held(so["after"]) == []  # post-signout completion ignored
    assert so["after"]["notice"]["hidden"] is True  # lens off in this scenario
    sup = out["superseded_completion"]
    assert sup["reads"] == 2
    assert _held(sup["afterOld"]) == []  # superseded completion ignored
    assert _held(sup["afterNew"]) == ["TSLA"]


def test_exposure_wl_auth_readiness_recovery(tmp_path: Path):
    """A loading first read (cloud not ready) recovers via the existing
    wl-auth readiness event without any polling."""
    rec = _run_exposure_scenarios(tmp_path, ["wl_auth_readiness_recovery"])[
        "wl_auth_readiness_recovery"
    ]
    assert rec["before"]["notice"]["state"] == "loading"
    assert _held(rec["before"]) == []
    assert _visible(rec["before"]) == ["AAPL", "MSFT", "TSLA"]
    assert rec["after"]["notice"]["hidden"] is True
    assert _held(rec["after"]) == ["MSFT"]
    assert _visible(rec["after"]) == ["MSFT"]
    assert rec["after"]["emptyHidden"] is True


def test_exposure_boot_waits_for_later_page_scripts(tmp_path: Path):
    """While document.readyState === 'loading' the screener must not read:
    scripts later in the page (watchstore.js) land first, and the boot read
    happens once, after them."""
    rec = _run_exposure_scenarios(tmp_path, ["boot_before_later_scripts"])[
        "boot_before_later_scripts"
    ]
    assert rec["callsAtEval"] == 0
    assert rec["readerCalls"] == 1
    assert _held(rec) == ["AAPL"]
    assert rec["notice"]["hidden"] is True


def test_exposure_off_restores_ordinary_research(tmp_path: Path):
    """Switching Exposure off hides the notice and restores ordinary
    visibility; on again reuses the verified answer without re-reading."""
    rec = _run_exposure_scenarios(tmp_path, ["exposure_off_recovery"])[
        "exposure_off_recovery"
    ]
    assert _visible(rec["on"]) == ["AAPL"]
    assert _held(rec["on"]) == ["AAPL"]
    assert _visible(rec["off"]) == ["AAPL", "MSFT", "TSLA"]
    assert rec["off"]["notice"]["hidden"] is True
    assert _visible(rec["onAgain"]) == ["AAPL"]
    assert rec["onAgain"]["readerCalls"] == rec["on"]["readerCalls"]


def test_exposure_preserves_other_lenses_and_order(tmp_path: Path):
    """Catalyst lens, date ordering and their combination with Exposure keep
    the pre-repair semantics."""
    rec = _run_exposure_scenarios(tmp_path, ["lens_and_order_regression"])[
        "lens_and_order_regression"
    ]
    assert _visible(rec["base"]) == ["AAPL", "MSFT", "TSLA"]
    assert rec["base"]["order"] == ["AAPL", "MSFT", "TSLA"]
    assert _visible(rec["catalystOn"]) == ["AAPL", "TSLA"]
    assert rec["dateOrder"]["order"] == ["AAPL", "TSLA", "MSFT"]
    assert _visible(rec["dateOrder"]) == ["AAPL", "TSLA"]
    assert _visible(rec["exposureOn"]) == ["TSLA"]  # catalyst ∧ held
    assert _visible(rec["exposureOff"]) == ["AAPL", "TSLA"]
    assert rec["exposureOff"]["notice"]["hidden"] is True


def test_exposure_closed_only_is_verified_empty(tmp_path: Path):
    rec = _run_exposure_scenarios(tmp_path, ["closed_only"])["closed_only"]
    assert rec["notice"]["hidden"] is True
    assert _visible(rec) == []
    assert _held(rec) == []
    assert rec["emptyHidden"] is False


def test_exposure_resolved_loading_is_not_a_failure(tmp_path: Path):
    rec = _run_exposure_scenarios(tmp_path, ["loading_resolved_null"])["loading_resolved_null"]
    assert rec["notice"]["state"] == "loading"
    assert rec["notice"]["linkHidden"] is True
    assert _held(rec) == []
    assert rec["emptyHidden"] is True


def test_exposure_requires_both_public_read_methods(tmp_path: Path):
    rec = _run_exposure_scenarios(tmp_path, ["missing_read_state"])["missing_read_state"]
    assert rec["notice"]["state"] == "unavailable"
    assert rec["readerCalls"] == 0
    assert _held(rec) == []


def test_exposure_refresh_invalidates_published_holdings(tmp_path: Path):
    rec = _run_exposure_scenarios(tmp_path, ["refresh_published"])["refresh_published"]
    assert _held(rec["before"]) == ["AAPL"]
    assert _held(rec["during"]) == []
    assert rec["during"]["notice"]["state"] == "loading"
    assert _held(rec["after"]) == ["TSLA"]
    assert _held(rec["authRefresh"]) == []
    assert _held(rec["final"]) == []
    assert rec["final"]["emptyHidden"] is False


def test_exposure_cache_belongs_to_the_same_store(tmp_path: Path):
    rec = _run_exposure_scenarios(tmp_path, ["replaced_store_published"])["replaced_store_published"]
    assert _held(rec["during"]) == []
    assert rec["during"]["notice"]["state"] == "loading"
    assert _held(rec["after"]) == ["MSFT"]
