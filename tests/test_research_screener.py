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
    assert "security state catalyst record" in why["en"]
    assert "Valuation under different assumptions" in why["en"]
    assert "催化事项" in why["zh"]
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
    why_en = payload["rows"][0]["why"]["en"]
    assert not _ON_DATE.search(why_en), why_en
    assert "on 2026-09-12" not in why_en
    assert "opens around September 12" in why_en
    assert "windows, not certainties" in why_en
    assert "窗口，不是定论" in payload["rows"][0]["why"]["zh"]
    glance = payload["rows"][0]["why_glance"]["en"]
    assert glance.endswith((".", "!", "?"))
    assert "Sales up" not in glance
    assert "From Valuation" not in glance


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
    assert "Estimated window" in source
    assert "估计窗口" in source
    assert "about 30 trading days" in source
    assert "大约 30 个交易日" in source
    assert "research_screener.css" in source


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


_STAMP_RE = re.compile(r'(theme|research_screener)\.css\?v=[0-9a-f]{8}')


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
    assert baked == committed
    assert _STAMP_RE.search(baked)
