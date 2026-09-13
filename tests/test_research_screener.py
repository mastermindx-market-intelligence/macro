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
    compile_research_screener,
    sort_rows,
    trading_days_between,
)

REPO = Path(__file__).resolve().parents[1]
ENGINE_PATH = REPO / "engine" / "research_screener.py"
BUILDER_PATH = REPO / "scripts" / "build_research_screener.py"
TEMPLATE_PATH = REPO / "templates" / "research_screener.html.j2"
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

_FORBIDDEN_KEY = re.compile(r"(score|rank|top|best|conviction)", re.I)
_WORD = re.compile(r"\b(score|rank|top|best|conviction)\b", re.I)
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
    assert by_name["Apple"]["catalyst"]["date"] == "2026-09-12"
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


def test_why_names_the_owner():
    payload = compile_research_screener(
        [_state("US-XNAS-AAPL", "AAPL", name="Apple", window_start="2026-09-12")],
        [_valuation("AAPL", price=180, per_share=220)],
        as_of=date(2026, 9, 1),
    )
    why = payload["rows"][0]["why"]
    assert "security-state catalyst record" in why["en"]
    assert "valuation-under-assumptions" in why["en"]
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
    assert THEME_NULL_EN in html
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
