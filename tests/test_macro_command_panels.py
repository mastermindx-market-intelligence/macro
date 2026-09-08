"""Macro Command P3 — panel contract, rail order, derived deck, fail-closed.

Frozen pin + addendum: every P3 section renders question → stance → figure+
caption → watching in that DOM order; Overview movement is the one figure;
directory is rail-ordered and outside `.mc-figure`; the deck count is derived
from the rail, never hardcoded as fourteen.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from lib import macro_suite_labels as L
from lib import macro_suite_view
from scripts import build_macro_suite_pages as builder
from scripts import check_macro_command_copy as guard

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "site" / "macrodata"
BUILT_AT = "2026-09-06T00:00:00Z"
P3_IDS = ("overview", "money", "policy", "rates", "inflation")
P4_IDS = ("growth", "jobs", "housing", "consumer", "credit", "debt", "trade")
RAIL_WORKSPACES = (
    "liquidity_regime", "liquidity_central_banks", "monetary_policy",
    "rates_curves", "inflation_system", "growth_real_economy",
    "business_activity", "labor_markets", "housing_real_estate",
    "consumer_payments", "financial_conditions", "capital_structure",
    "national_debt_liabilities", "trade_flows",
)


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> tuple[str, Path]:
    out = tmp_path_factory.mktemp("macro_command_panels") / "site"
    pages = builder.render(ROOT, data_root=DATA_ROOT, out_dir=out, page_built_at=BUILT_AT)
    hub = [p for p in pages if p.name == builder.HUB_PAGE.output]
    assert hub, "the builder did not write macro_monetary.html"
    return hub[0].read_text(encoding="utf-8"), out


def _panel(html: str, section_id: str) -> str:
    match = re.search(
        r'<section class="mc-panel" id="' + section_id + r'".*?(?=<section class="mc-panel"|</main>)',
        html, re.S)
    assert match, section_id
    return match.group(0)


def _child_classes(panel: str) -> list[str]:
    """Direct mc-* children of one panel, in document order."""
    body = re.sub(r"<template[^>]*>.*?</template>", "", panel, flags=re.S)
    found: list[str] = []
    depth = 0
    for match in re.finditer(r"</?([a-z0-9]+)([^>]*)>", body, re.I):
        raw = match.group(0)
        tag = match.group(1).lower()
        attrs = match.group(2)
        if raw.startswith("</"):
            depth -= 1
            continue
        if depth == 1:
            cls = re.search(r'class="([^"]+)"', attrs)
            if cls:
                lead = cls.group(1).split()[0]
                if lead.startswith("mc-"):
                    found.append(lead)
        if not raw.endswith("/>") and tag not in {"br", "img", "hr", "input", "meta", "link"}:
            depth += 1
    return found


def test_rail_workspace_order_is_the_fourteen_named_in_delta_13() -> None:
    assert builder.rail_workspace_ids() == RAIL_WORKSPACES
    assert len(set(builder.rail_workspace_ids())) == 14


def test_overview_directory_hrefs_are_rail_order(built: tuple[str, Path]) -> None:
    html, _ = built
    overview = _panel(html, "overview")
    dests = re.search(r'<nav class="mc-dests-block".*?</nav>', overview, re.S)
    assert dests, "Overview lost the destination <nav>"
    hrefs = re.findall(r'class="mc-dest"[^>]*href="([^"]+)"', dests.group(0))
    expected = [f"macro_{wid}.html" for wid in RAIL_WORKSPACES]
    assert hrefs == expected


def test_overview_has_one_figure_of_five_rows_outside_the_directory(
        built: tuple[str, Path]) -> None:
    html, _ = built
    overview = _panel(html, "overview")
    figures = re.findall(r'data-mc-figure', overview)
    assert len(figures) == 1
    figure = re.search(r'<div class="mc-figure"[^>]*>.*?(?=<p class="mc-caption"|<div class="mc-watch")',
                       overview, re.S)
    assert figure, "Overview figure missing"
    assert 'class="mc-move"' in figure.group(0)
    rows = re.findall(r'class="mx-chg-row mc-move-row"', figure.group(0))
    assert len(rows) == 5
    dests = re.search(r'<ul class="mc-dests">', overview)
    assert dests
    # directory is not inside the figure
    assert 'class="mc-dests"' not in figure.group(0)


def test_overview_dom_order_and_no_details_or_arrival(built: tuple[str, Path]) -> None:
    html, _ = built
    order = _child_classes(_panel(html, "overview"))
    assert order == [
        "mc-panel-head", "mc-stance", "mc-primer", "mc-figure",
        "mc-caption", "mc-watch", "mc-dests-block",
    ]


def test_p3_non_overview_dom_order(built: tuple[str, Path]) -> None:
    html, _ = built
    for section_id in ("money", "policy", "rates", "inflation"):
        order = _child_classes(_panel(html, section_id))
        assert order[0] == "mc-arrival", section_id
        assert "mc-panel-head" in order
        assert "mc-stance" in order
        assert "mc-primer" in order
        assert "mc-figure" in order
        assert "mc-caption" in order
        assert "mc-watch" in order
        assert "mc-details" in order
        assert order.index("mc-stance") < order.index("mc-figure") < order.index("mc-watch")
        if section_id == "inflation":
            assert "mc-foot" in order


def test_p4_sections_have_no_stance_primer_caption_watch(built: tuple[str, Path]) -> None:
    html, _ = built
    for section_id in P4_IDS:
        panel = _panel(html, section_id)
        assert 'class="mc-stance' not in panel, section_id
        assert 'class="mc-primer' not in panel, section_id
        assert 'class="mc-caption' not in panel, section_id
        assert 'class="mc-watch' not in panel, section_id


def test_panel_focus_and_subtab_aria_yield_to_shipped_p1(built: tuple[str, Path]) -> None:
    html, _ = built
    assert len(re.findall(r'<section class="mc-panel"[^>]*tabindex', html)) == 0
    titles = re.findall(r'<h2 class="mc-panel-title"[^>]*>', html)
    assert len(titles) == 12
    for tag in titles:
        assert 'tabindex="-1"' in tag
    assert re.findall(r'class="mc-subtabs"[^>]*aria-label=', html) == []


def test_building_sentence_is_gone(built: tuple[str, Path]) -> None:
    html, _ = built
    assert "mc-figure-building" not in html
    assert "not available yet. Start with any workspace" not in html


def test_overview_stance_carries_no_digit(built: tuple[str, Path]) -> None:
    html, _ = built
    stance = re.search(
        r'id="overview".*?<span class="mc-stance-text">(.*?)</span>', html, re.S)
    assert stance
    text = re.sub(r"<[^>]+>", "", stance.group(1))
    assert not re.search(r"\d", text)


def test_derived_deck_uses_rail_section_count_not_fourteen() -> None:
    n = len(builder.SECTIONS)
    assert n == 12
    copy = macro_suite_view._deck_copy(n)
    assert "Fourteen" not in copy["en"]
    assert "十四个研究工作区" not in copy["zh"]
    assert str(n) in copy["zh"]
    assert "Twelve" in copy["en"]


def test_deck_count_changes_when_the_rail_length_changes() -> None:
    eleven = macro_suite_view._deck_copy(11)
    twelve = macro_suite_view._deck_copy(12)
    assert eleven != twelve
    assert "Eleven" in eleven["en"]
    assert "11" in eleven["zh"]


def test_copy_budgets_on_the_reviewed_tables() -> None:
    for section_id, keys in L.STANCES.items():
        for key, pair in keys.items():
            assert len(pair["en"].split()) <= 20, (section_id, key, pair["en"])
            assert len(re.findall(r"[\u4e00-\u9fff]", pair["zh"])) <= 34, (section_id, key)
    for section_id, pair in L.CAPTIONS.items():
        assert len(pair["en"].split()) <= 18, (section_id, pair["en"])
    for section_id, pair in L.PRIMERS.items():
        assert len(pair["en"].split()) <= 45, (section_id, pair["en"])
    for section_id, bullets in L.WATCHING.items():
        assert len(bullets) == 2
        for bullet in bullets:
            assert len(bullet["en"].split()) <= 16, (section_id, bullet["en"])


def test_unknown_stance_key_raises_and_writes_no_page(tmp_path: Path) -> None:
    out = tmp_path / "site"
    out.mkdir()
    # A PRESENT headline with a letter the money table does not carry.
    entries = []
    for page in builder.SUITE_PAGES:
        snap = None
        if page.workspace_id == "liquidity_regime":
            snap = {
                "workspace": {"id": page.workspace_id},
                "headline": {"status": "PRESENT", "state_id": "Z",
                             "effective_date": "2026-09-04"},
                "changes": {"comparability": "COMPARABLE", "deltas": []},
            }
        entries.append({
            "workspace_id": page.workspace_id, "region": "US",
            "output": page.output,
            "title": {"en": page.workspace_id, "zh": page.workspace_id},
            "subtitle": {"en": "", "zh": ""},
            "snapshot": snap, "failure": None if snap else {"kind": "NOT_COVERED"},
        })
    with pytest.raises(builder.MacroCommandBuildError, match="unknown stance key"):
        builder._macro_command_sections(entries, page_built_at=BUILT_AT)
    assert not (out / "macro_monetary.html").exists()


def test_unmapped_metric_on_a_p3_section_raises() -> None:
    deltas = [{
        "metric_id": "not_a_reviewed_metric",
        "label": {"en": "Nope", "zh": "Nope"},
        "prior_present": True, "current_present": True, "delta_present": True,
        "prior": "1", "current": "2", "delta": "+1", "sign": "up",
    }]
    with pytest.raises(builder.MacroCommandBuildError, match="unmapped metric_id"):
        builder._move_rows_from_deltas(deltas, href="x.html", show_source=None)


def test_not_applicable_is_unstated_not_e1(built: tuple[str, Path]) -> None:
    html, _ = built
    rates = _panel(html, "rates")
    assert 'data-mc-empty="e1"' not in rates
    assert "No single reading is published here" in rates
    policy = _panel(html, "policy")
    assert 'data-mc-empty="e1"' not in policy


def test_copy_guard_is_green_on_the_rebuilt_page(built: tuple[str, Path]) -> None:
    html, _ = built
    assert guard.find_violations(html) == []


def test_dec_stance_is_guidance_record_exists() -> None:
    path = ROOT / "agentos" / "decisions" / "DEC-MACRO-COMMAND-STANCE-IS-GUIDANCE.md"
    text = path.read_text(encoding="utf-8")
    assert "never tells you what to do" in text
    assert "no score" in text


def test_arrival_ships_hidden_on_eleven_non_overview_panels(built: tuple[str, Path]) -> None:
    html, _ = built
    assert html.count("data-mc-arrival hidden") == 11
    overview = _panel(html, "overview")
    assert "data-mc-arrival" not in overview


def test_fragments_carry_the_authenticity_marker(built: tuple[str, Path]) -> None:
    _, out = built
    frag_dir = out / "macro" / "fragments"
    names = sorted(p.name for p in frag_dir.glob("*.html"))
    assert "overview.html" not in names
    assert "money.html" in names
    assert "rates.html" in names
    money = (frag_dir / "money.html").read_text(encoding="utf-8")
    assert "data-mc-fragment" in money
    assert "data-mc-tabbody=\"liquidity\"" in money
    assert "data-mc-tabbody=\"central_banks\"" in money
    assert "class=\"mc-move\"" in money
