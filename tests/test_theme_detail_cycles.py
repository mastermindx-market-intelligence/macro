"""Regional theme-detail cycles and truthful source-bound reading metadata."""
from __future__ import annotations

import copy
import html as html_module
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from jinja2 import Environment, FileSystemLoader

from engine import basket_history, basket_score, leadership_receipt
from scripts import build_theme_detail as builder
from scripts.build_theme_detail import _cycle_from_chart


def test_cycle_from_chart_builds_compact_record():
    idx = pd.bdate_range("2023-01-02", periods=750)
    x = np.arange(len(idx), dtype=float)
    values = 100.0 * np.exp(0.0004 * x + 0.12 * np.sin(x / 45.0))
    chart = {
        "dates": [d.strftime("%Y-%m-%d") for d in idx],
        "baskets": {"gold_miners": values.tolist()},
    }
    rec = _cycle_from_chart(
        chart,
        "gold_miners",
        {"name": "Gold Miners", "name_zh": "黄金矿业"},
    )
    assert rec is not None
    assert len(rec["price"]) > 50
    assert rec["basis"] == "equal_weight_close"
    assert rec["now"]["phase"] in rec["phases"]
    assert rec["xDomain"][1] > rec["today"]


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/regional_basket_ca_asset_mgrs_20261102.json"


@pytest.fixture
def source():
    return json.loads(FIXTURE.read_text())


@pytest.fixture
def render_detail(monkeypatch, tmp_path, source):
    """Run the incumbent builder and template; replace unrelated disk consumers."""
    written = []

    class FrozenClock:
        @staticmethod
        def now(_tz):
            return datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(builder, "datetime", FrozenClock)
    monkeypatch.setattr(builder, "standout_index", lambda region: {})
    monkeypatch.setattr(builder, "member_context_index", lambda region: {})
    monkeypatch.setattr(builder, "_conviction", lambda *args: None)
    monkeypatch.setattr(builder, "_cycle_from_chart", lambda *args: None)
    monkeypatch.setattr(builder, "_theme_research_mount", lambda *args: None)
    monkeypatch.setattr(basket_score, "act_now_stocks", lambda *args: [])
    monkeypatch.setattr(basket_history, "score_series", lambda *args: source["_detail_history"])
    monkeypatch.setattr(basket_history, "change_timeline", lambda *args, **kwargs: source["_detail_timeline"])
    monkeypatch.setattr(leadership_receipt, "build_receipt", lambda *args: None)
    monkeypatch.setattr(builder, "write_page", lambda path, html: written.append((path, html)))
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)

    def render(payload, region="canada"):
        written.clear()
        assert builder.build_detail_pages(payload, tmp_path, env, region) == 1
        path, html = written[0]
        match = re.search(r"const DETAIL = (.*);\n", html)
        assert match, "incumbent page must retain its exact detail payload"
        return path, html, json.loads(match.group(1))

    return render


@pytest.mark.parametrize("theme_feed", [None, {}, {"themes": []}])
def test_missing_theme_feed_preserves_canadian_price_identity(source, render_detail, theme_feed):
    source["theme_intel"] = theme_feed
    path, html, detail = render_detail(source)

    assert path.name == "ca_asset_mgrs.html"
    assert path.parent.name == "basket_canada"
    assert detail["bench_label"] == source["benchmark_label"] == "S&P/TSX"
    assert detail["bench_label_zh"] == source["benchmark_label_zh"]
    assert detail["as_of"] == source["as_of"] == "2026-11-02"
    assert detail["as_of"] != source["baskets"][0]["created"]
    assert detail["theme"].get("score") is None
    assert "Generated" in html and "2026-11-03 12:00 UTC" in html


def test_empty_optional_labels_use_the_retained_price_payload(source, render_detail):
    source["theme_intel"] = {"as_of": "", "bench_label": None, "bench_label_zh": ""}
    _, _, detail = render_detail(source)
    assert (detail["bench_label"], detail["bench_label_zh"], detail["as_of"]) == (
        source["benchmark_label"], source["benchmark_label_zh"], source["as_of"],
    )


def test_unavailable_source_metadata_never_borrows_us_or_roster_creation(source, render_detail):
    source["theme_intel"] = {}
    for key in ("as_of", "benchmark_label", "benchmark_label_zh"):
        source.pop(key)
    _, _, detail = render_detail(source)
    assert detail["bench_label"] == detail["bench_label_zh"] == "—"
    assert detail["as_of"] is None
    assert detail["basket"]["created"] == "2021-06-14", "roster history must remain intact"


def test_existing_theme_source_remains_authoritative_when_present(source, render_detail):
    source["as_of"] = "2026-10-30"
    source["benchmark_label"] = "different price snapshot"
    source["benchmark_label_zh"] = "另一价格快照"
    _, _, detail = render_detail(source)
    theme = source["theme_intel"]
    assert (detail["bench_label"], detail["bench_label_zh"], detail["as_of"]) == (
        theme["bench_label"], theme["bench_label_zh"], theme["as_of"],
    )


def test_degraded_render_preserves_roster_prices_history_and_regional_routes(source, render_detail):
    healthy_source = copy.deepcopy(source)
    _, healthy_html, healthy = render_detail(healthy_source)
    source["theme_intel"] = {}
    _, degraded_html, degraded = render_detail(source)

    assert degraded["basket"] == healthy["basket"]
    assert all(degraded["basket"][key] == value for key, value in source["baskets"][0].items())
    assert degraded["members"] == healthy["members"]
    assert len(degraded["members"]) == 8
    assert degraded["history"] == healthy["history"] == source["_detail_history"]
    assert degraded["timeline"] == healthy["timeline"] == source["_detail_timeline"]
    assert degraded["stock_base"] == healthy["stock_base"] == "../canada_stock.html#"
    assert degraded["back"] == healthy["back"] == "../baskets_canada.html"
    assert degraded["region"] == healthy["region"] == "canada"
    assert 'href="../baskets_canada.html"' in healthy_html
    assert 'href="../baskets_canada.html"' in degraded_html
    assert degraded["theme"].get("score") is None


def _render_javascript(html, tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for the incumbent JavaScript renderer witness")
    page = tmp_path / "basket.html"
    report = tmp_path / "rendered.json"
    page.write_text(html)
    subprocess.run(
        [node, str(ROOT / "tests/fixtures/basket_detail_render_witness.cjs"), str(page), str(report)],
        check=True, capture_output=True, text=True, timeout=12,
    )
    return json.loads(report.read_text())


def _counter_markup(markup, label):
    match = re.search(
        r'<span class="l-en">' + re.escape(label) + r'</span>.*?<div class="v">(.*?)</div>',
        markup, re.S,
    )
    assert match, label
    return match.group(1)


def _counter_pair(markup, label):
    return html_module.unescape(re.sub(r"<[^>]+>", "", _counter_markup(markup, label))).strip()


def test_missing_theme_counts_render_as_unavailable_with_real_members(source, render_detail, tmp_path):
    source["theme_intel"] = {}
    _, html, _ = render_detail(source)
    report = _render_javascript(html, tmp_path)
    for markup in report["cells"].values():
        assert _counter_pair(markup, "new hi / lo") == "—/—"
        assert _counter_pair(markup, "adv / dec today") == "—/—"
        member_links = set(re.findall(r'<a class="tk" href="([^"]+)"', markup))
        assert member_links == {"../canada_stock.html#" + m["symbol"] for m in source["baskets"][0]["members"]}
        for label in ("new hi / lo", "adv / dec today"):
            value_classes = re.findall(r'<span class="([^"]+)">', _counter_markup(markup, label))
            assert value_classes == ["muted", "muted"]
        assert "2021-06-14 close" not in markup
        assert "S&P/TSX" in html_module.unescape(markup)


@pytest.mark.parametrize("counts", [(0, 0), (3, 1)])
def test_observed_counts_preserve_zero_and_nonzero(source, render_detail, tmp_path, counts):
    # Controlled display observations, not a newly computed market reading.
    th = source["theme_intel"]["themes"][0]
    th["adv"], th["dec"] = counts
    th["breadth"] = {"nh": counts[0], "nl": counts[1]}
    _, html, _ = render_detail(source)
    report = _render_javascript(html, tmp_path)
    for markup in report["cells"].values():
        assert _counter_pair(markup, "new hi / lo") == f"{counts[0]}/{counts[1]}"
        assert _counter_pair(markup, "adv / dec today") == f"{counts[0]}/{counts[1]}"


def test_nonfinite_or_boolean_counts_are_not_observations(source, render_detail, tmp_path):
    th = source["theme_intel"]["themes"][0]
    th.update(adv=float("nan"), dec=float("inf"), breadth={"nh": False, "nl": None})
    _, html, _ = render_detail(source)
    for markup in _render_javascript(html, tmp_path)["cells"].values():
        assert _counter_pair(markup, "new hi / lo") == "—/—"
        assert _counter_pair(markup, "adv / dec today") == "—/—"
