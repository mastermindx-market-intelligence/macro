"""Macro Command P3 — panel contract, rail order, derived deck, fail-closed.

Frozen pin + addendum: every P3 section renders question → stance → figure+
caption → watching in that DOM order; Overview movement is the one figure;
directory is rail-ordered and outside `.mc-figure`; the deck count is derived
from the rail, never hardcoded as fourteen.
"""
from __future__ import annotations

import copy
import json
import math
import re
import shutil
from html import unescape
from pathlib import Path

from engine.market_os.macro_workspaces import contract as workspace_contract

import pytest

from lib import macro_suite_labels as L
from lib import macro_suite_view
from scripts import build_macro_suite_pages as builder
from scripts import check_macro_command_copy as guard

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "site" / "macrodata"


def _manifest_pages(manifest: dict) -> list[dict]:
    pages = list(manifest.get("pages") or [])
    assert pages, "manifest has no pages"
    return pages


def _manifest_states(manifest: dict) -> list[dict]:
    states: list[dict] = []
    for page in _manifest_pages(manifest):
        states.extend(page.get("states") or [])
    return states
BUILT_AT = "2026-09-06T00:00:00Z"
P3_IDS = ("overview", "money", "policy", "rates", "inflation")
P4_IDS = ("growth", "jobs", "housing", "consumer", "credit", "debt", "trade")
CURRENT_ONLY_DECK_EN = (
    "The latest readings are below — there is no earlier reading to compare yet.")
CURRENT_ONLY_DECK_ZH = "最新读数如下——暂无更早读数可比。"
MOVEMENT_DECK_EN = "What moved below is what we do have."
MOVEMENT_DECK_ZH = "下方的变化就是我们目前掌握的内容。"
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


@pytest.mark.needs_full_checkout("site")
def test_overview_directory_hrefs_are_rail_order(built: tuple[str, Path]) -> None:
    html, _ = built
    overview = _panel(html, "overview")
    dests = re.search(r'<nav class="mc-dests-block".*?</nav>', overview, re.S)
    assert dests, "Overview lost the destination <nav>"
    hrefs = re.findall(r'class="mc-dest"[^>]*href="([^"]+)"', dests.group(0))
    expected = [f"macro_{wid}.html" for wid in RAIL_WORKSPACES]
    assert hrefs == expected


@pytest.mark.needs_full_checkout("site")
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
    rows = re.findall(r'class="mx-chg-row mc-move-row', figure.group(0))
    assert len(rows) == 5
    dests = re.search(r'<ul class="mc-dests">', overview)
    assert dests
    # directory is not inside the figure
    assert 'class="mc-dests"' not in figure.group(0)


@pytest.mark.needs_full_checkout("site")
def test_overview_dom_order_and_no_details_or_arrival(built: tuple[str, Path]) -> None:
    html, _ = built
    order = _child_classes(_panel(html, "overview"))
    # I4: same-publication prior drops the comparison caption; the typed
    # state line lives inside the figure, not as a sibling caption.
    expected = [
        "mc-panel-head", "mc-stance", "mc-primer", "mc-figure",
        "mc-watch", "mc-dests-block",
    ]
    if "mc-caption" in order:
        expected = [
            "mc-panel-head", "mc-stance", "mc-primer", "mc-figure",
            "mc-caption", "mc-watch", "mc-dests-block",
        ]
    assert order == expected
    overview = unescape(_panel(html, "overview"))
    if (CURRENT_ONLY_DECK_EN in overview
            or "Only one reading is published so far" in overview):
        assert "mc-caption" not in order
        assert "compared against the previous publication" not in overview


@pytest.mark.needs_full_checkout("site")
def test_p3_non_overview_dom_order(built: tuple[str, Path]) -> None:
    html, _ = built
    for section_id in ("money", "policy", "rates", "inflation"):
        panel = _panel(html, section_id)
        order = _child_classes(panel)
        assert order[0] == "mc-arrival", section_id
        assert "mc-panel-head" in order
        if section_id == "rates":
            # MINOR-E6: the empty card is the one voice; no stance echo.
            assert "mc-stance" not in order, (section_id, order)
        else:
            assert "mc-stance" in order, (section_id, order)
        assert "mc-primer" in order
        assert "mc-figure" in order
        # M2: a section-level empty (live #rates is E2) drops the caption.
        # The hidden E5 <template> also carries data-mc-empty — ignore it.
        text = unescape(panel)
        # Caption is a comparison claim. E2 (section empty) and I4
        # (same-publication current-only, often only in the fragment)
        # must not keep it.
        if (section_id == "rates"
                or "Only one reading is published so far" in text
                or "Each row shows the last two readings" not in text):
            assert "mc-caption" not in order, (section_id, order)
        else:
            assert "mc-caption" in order, (section_id, order)
        assert "mc-watch" in order
        assert "mc-details" in order
        if section_id == "rates":
            assert order.index("mc-figure") < order.index("mc-watch")
        else:
            assert order.index("mc-stance") < order.index("mc-figure") < order.index("mc-watch")
        if section_id == "inflation":
            assert "mc-foot" in order


@pytest.mark.needs_full_checkout("site")
def test_p4_sections_have_stance_primer_caption_watch(built: tuple[str, Path]) -> None:
    html, _ = built
    # Live #rates is E2 — the empty card is the one voice, so 11 stances.
    assert html.count('<p class="mc-stance') == 11
    assert html.count('<details class="mc-primer') == 12
    assert html.count('<div class="mc-watch') == 12
    # P4-3 drops the caption on an E1/E2 figure. I4 also drops it when the
    # figure is current-only (same-publication prior). Live data today is
    # current-only, so the caption count is not the naive twelve.
    for section_id in P4_IDS:
        panel = _panel(html, section_id)
        assert 'class="mc-stance' in panel, section_id
        assert 'class="mc-primer' in panel, section_id
        assert 'class="mc-watch' in panel, section_id
        assert 'class="mc-panel-question"' in panel, section_id
        # P4 primers ship closed — open-by-default stays the first three.
        assert 'class="mc-primer" open' not in panel, section_id
        text = unescape(panel)
        if ("Today's number didn't arrive" in text
                or "Only one reading is published so far" in text
                or "Each row shows the last two readings" not in text):
            assert 'class="mc-caption' not in panel, section_id
        else:
            assert 'class="mc-caption' in panel, section_id


@pytest.mark.needs_full_checkout("site")
def test_panel_focus_and_subtab_aria_yield_to_shipped_p1(built: tuple[str, Path]) -> None:
    html, _ = built
    assert len(re.findall(r'<section class="mc-panel"[^>]*tabindex', html)) == 0
    titles = re.findall(r'<h2 class="mc-panel-title"[^>]*>', html)
    assert len(titles) == len(P3_IDS) + len(P4_IDS)
    for tag in titles:
        assert 'tabindex="-1"' in tag
    assert re.findall(r'class="mc-subtabs"[^>]*aria-label=', html) == []


@pytest.mark.needs_full_checkout("site")
def test_building_sentence_is_gone(built: tuple[str, Path]) -> None:
    html, _ = built
    assert "mc-figure-building" not in html
    assert "not available yet. Start with any workspace" not in html


@pytest.mark.needs_full_checkout("site")
def test_overview_stance_carries_no_digit(built: tuple[str, Path]) -> None:
    html, _ = built
    stance = re.search(
        r'id="overview".*?<span class="mc-stance-text">(.*?)</span>', html, re.S)
    assert stance
    text = re.sub(r"<[^>]+>", "", stance.group(1))
    assert not re.search(r"\d", text)


def test_derived_deck_uses_populated_panel_count_not_fourteen() -> None:
    n = len(P3_IDS)
    copy = macro_suite_view._deck_copy(n)
    assert "Fourteen" not in copy["en"]
    assert "fourteen" not in copy["en"]
    assert "十四" not in copy["zh"]
    assert f"{n} research sections" in copy["en"]
    assert f"{n} 个研究板块" in copy["zh"]


def test_deck_count_changes_when_the_rail_length_changes() -> None:
    four = macro_suite_view._deck_copy(4)
    five = macro_suite_view._deck_copy(5)
    assert four != five
    assert "4 research sections" in four["en"]
    assert "5 research sections" in five["en"]
    assert "4 个研究板块" in four["zh"]


@pytest.mark.needs_full_checkout("site")
def test_built_page_has_one_section_count_matching_the_rail(
        built: tuple[str, Path]) -> None:
    html, _ = built
    n = len(P3_IDS) + len(P4_IDS)
    assert html.count("Fourteen research") == 0
    assert html.count("十四个研究") == 0
    assert html.count(f"{n} research sections") == 1
    assert html.count(f"{n} 个研究板块") == 1
    # R6-M1: one count truth — populated panels. P4 fills the remaining
    # seven, so the coverage denominator is twelve, not the P3-only five.
    assert re.search(rf"\d+ of {n} sections have today's data", unescape(html))
    assert re.search(rf"{n}个板块中有\d+个有今日数据", unescape(html))
    assert "Fourteen research" not in html
    assert "十四个研究" not in html


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


@pytest.mark.needs_full_checkout("site")
def test_not_applicable_is_unstated_not_e1(built: tuple[str, Path]) -> None:
    html, _ = built
    rates = _panel(html, "rates")
    assert 'data-mc-empty="e1"' not in rates
    policy = _panel(html, "policy")
    assert 'data-mc-empty="e1"' not in policy
    assert "No single reading is published here" in policy


@pytest.mark.needs_full_checkout("site")
def test_e2_figure_prints_the_e2_stance_not_the_structural_null(
        built: tuple[str, Path]) -> None:
    """M6 / MINOR-E6: #rates is E2 — the empty card speaks once.

    The empty figure lives in the fragment (JS hydrates `[data-mc-figure]`);
    the panel shell must not repeat the title as a stance line.
    """
    html, out = built
    rates = unescape(_panel(html, "rates"))
    fragment = unescape(
        (out / "macro" / "fragments" / "rates.html").read_text(encoding="utf-8"))
    assert 'data-mc-empty="e2"' in fragment
    assert "No reading arrived today." in fragment
    assert "Today's number didn't arrive" not in fragment
    assert "Today's number didn't arrive" not in rates
    assert "No single reading is published here" not in rates
    assert "Each row shows the last two readings" not in rates
    assert "hasn't arrived" in unescape(html)  # strip chip stays the transient voice


@pytest.mark.needs_full_checkout("site")
def test_populated_unstated_section_uses_see_curve_chip(
        built: tuple[str, Path]) -> None:
    """M6 branch 2: #policy has rows + no headline — structural stance,
    strip chip reads 'See the curve below' and is dated."""
    html, _ = built
    policy = _panel(html, "policy")
    assert 'data-mc-empty="e2"' not in policy
    assert "No single reading is published here" in policy
    assert "See the curve below" in html
    assert "见下方曲线" in html


def test_hub_raises_on_unmapped_metric() -> None:
    """N1: an unmapped hub-pool id is a build error, never a silent drop."""
    deltas = [{
        "metric_id": "not_a_reviewed_metric",
        "label": {"en": "Nope", "zh": "Nope"},
        "prior_value": 1.0,
        "current_value": 2.0,
        "delta": 1.0,
    }]
    entries = []
    for page in builder.SUITE_PAGES:
        snap = None
        if page.workspace_id == "growth_real_economy":
            snap = {
                "workspace": {"id": page.workspace_id},
                "availability": {"state": "CURRENT"},
                "headline": {"status": "PRESENT", "state_id": "C",
                             "effective_date": "2026-09-04"},
                "changes": {"comparability": "COMPARABLE", "deltas": deltas},
            }
        entries.append({
            "workspace_id": page.workspace_id, "region": "US",
            "output": page.output,
            "title": {"en": page.workspace_id, "zh": page.workspace_id},
            "subtitle": {"en": "", "zh": ""},
            "snapshot": snap, "failure": None if snap else {"kind": "NOT_COVERED"},
        })
    with pytest.raises(ValueError, match="not_a_reviewed_metric") as raised:
        macro_suite_view.build_hub_view(entries, page_built_at=BUILT_AT)
    assert "unmapped metric id" in str(raised.value)


@pytest.mark.needs_full_checkout("site")
def test_built_hub_coverage_uses_populated_tally_and_some_unread(
        built: tuple[str, Path]) -> None:
    """R6-M1 / N0: the chip and the Overview stance share the populated tally."""
    html, _ = built
    overview = unescape(_panel(html, "overview"))
    stance = re.search(
        r'class="mc-stance mq-tone-(\w+)".*?class="mc-stance-text">(.*?)</span>',
        overview, re.S)
    assert stance, "Overview lost its stance"
    assert stance.group(1) == "warn"
    text = re.sub(r"<[^>]+>", "", stance.group(2))
    assert "Some desks have not reported yet" in text
    assert CURRENT_ONLY_DECK_EN in text
    assert MOVEMENT_DECK_EN not in text
    assert "Every desk reported today" not in overview
    assert "Every desk reported today" not in html
    plain = unescape(html)
    note = re.search(r"(\d+) of (\d+) sections have today's data", plain)
    assert note, "coverage chip lost its counted note"
    available, total = int(note.group(1)), int(note.group(2))
    populated_ids = set(P3_IDS + P4_IDS)
    assert total == len(populated_ids)
    assert available < total
    assert (available, total) == builder.populated_section_coverage_tally(
        _live_entries(), populated_ids)
    opening = re.search(r'<p class="mc-stance[^"]*"', overview)
    assert opening and "mq-tone-ok" not in opening.group(0)


def _live_entries() -> list[dict]:
    """The same hub entries `render()` assembled from site/macrodata."""
    entries = []
    for page in builder.SUITE_PAGES:
        identity = builder._identity(page)
        snapshot, _artifact = builder.read_workspace(DATA_ROOT, page)
        entries.append({
            "workspace_id": page.workspace_id,
            "region": page.region,
            "output": page.output,
            "title": identity["title"],
            "subtitle": identity["subtitle"],
            "snapshot": snapshot,
            "failure": None,
        })
    return entries


def _figure_is_current_only(section: dict) -> bool:
    rows = list((section.get("figure") or {}).get("rows") or [])
    return bool(rows) and all(row.get("kind") == "current" for row in rows)


def test_all_populated_current_uses_all_read_stance() -> None:
    """N0: only a full populated tally may wear the complete / ok stance."""
    entries = copy.deepcopy(_live_entries())
    for entry in entries:
        snap = entry.get("snapshot")
        if snap is not None:
            snap.setdefault("availability", {})["state"] = "CURRENT"
    available, total = builder.populated_section_coverage_tally(
        entries, set(P3_IDS))
    assert (available, total) == (len(P3_IDS), len(P3_IDS))
    sections = builder._macro_command_sections(entries, page_built_at=BUILT_AT)
    overview = next(s for s in sections if s["id"] == "overview")
    assert overview["stance"]["tone"] == "ok"
    assert "Every desk reported today" in overview["stance"]["text"]["en"]
    assert "今天每个小组都有读数" in overview["stance"]["text"]["zh"]
    # Live data is same-publication, so the current-only deck sentence wins.
    if _figure_is_current_only(overview):
        assert CURRENT_ONLY_DECK_EN in overview["stance"]["text"]["en"]
        assert MOVEMENT_DECK_EN not in overview["stance"]["text"]["en"]


@pytest.mark.needs_full_checkout("site")
def test_dests_heading_names_destination_pages_not_research_sections(
        built: tuple[str, Path]) -> None:
    """n4: 12 and 14 are labelled as different counts."""
    html, _ = built
    overview = unescape(_panel(html, "overview"))
    assert "12 research sections" in overview
    assert "12 个研究板块" in overview
    assert "Where to go next — 14 destination pages" in overview
    assert "接下来去哪里——14 个目标页面" in overview


@pytest.mark.needs_full_checkout("site")
def test_unmapped_metrics_attribute_is_absent_from_the_dom(
        built: tuple[str, Path]) -> None:
    """n2: the diagnostic counter is gone from customer-facing markup."""
    html, out = built
    assert "data-unmapped-metrics" not in html
    for fragment in (out / "macro" / "fragments").glob("*.html"):
        assert "data-unmapped-metrics" not in fragment.read_text(encoding="utf-8")


def test_e1_fires_when_a_section_has_no_date_and_no_deltas() -> None:
    """N2: E1 is the typed empty the builder emits for a bare workspace."""
    view = {
        "headline": {"effective_date": None},
        "changes": {"comparable": False, "deltas": []},
        "context": {"state": "CURRENT"},
    }
    figure, empty = builder._figure_or_empty_for_workspace(
        {"headline": {"effective_date": None, "null_reason": "NOT_YET_AVAILABLE"}},
        view=view, href="macro_inflation_system.html")
    assert figure is None
    assert empty is not None
    assert empty["id"] == "e1"
    assert "We don't have this reading yet" in empty["title"]["en"]


def test_e3_fires_when_a_dated_workspace_has_nothing_comparable() -> None:
    view = {
        "headline": {"effective_date": "2026-09-04"},
        "changes": {"comparable": False, "deltas": []},
        "context": {"state": "CURRENT"},
    }
    figure, empty = builder._figure_or_empty_for_workspace(
        {"headline": {"effective_date": "2026-09-04", "null_reason": None}},
        view=view, href="macro_inflation_system.html")
    assert figure is None
    assert empty["id"] == "e3"
    assert "We can't show the change yet" in empty["title"]["en"]


def test_e4_fires_when_a_command_subtab_is_withheld() -> None:
    entries = copy.deepcopy(_live_entries())
    for entry in entries:
        if entry["workspace_id"] == "liquidity_central_banks":
            entry["snapshot"]["withheld_command_tabs"] = ["central_banks"]
    sections = builder._macro_command_sections(
        entries, page_built_at=BUILT_AT, allow_empty_state_fixture=True)
    money = next(s for s in sections if s["id"] == "money")
    withheld = next(t for t in money["subtabs"] if t["id"] == "central_banks")
    assert withheld["empty"]["id"] == "e4"
    assert "Not open yet" in withheld["empty"]["title"]["en"]
    assert withheld["figure"] is None
    assert money["caption"] is None


def test_e6_fires_when_the_in_memory_snapshot_names_a_plan() -> None:
    snap = {
        "workspace": {"id": "inflation_system"},
        "availability": {"state": "CURRENT"},
        "headline": {"status": "PRESENT", "state_id": "A",
                     "effective_date": "2026-09-04"},
        "entitlement": "Research",
        "changes": {"comparability": "COMPARABLE", "deltas": []},
    }
    figure, empty = builder._figure_or_empty_for_workspace(
        snap, view={"headline": {"effective_date": "2026-09-04"},
                    "changes": {"comparable": True, "deltas": []},
                    "context": {"state": "CURRENT"}},
        href="macro_inflation_system.html",
        entitlement=builder._entitlement_plan(snap, allow_fixture_keys=True))
    assert figure is None
    assert empty["id"] == "e6"
    assert "Research" in empty["why"]["en"]
    assert "Included in a higher plan" in empty["title"]["en"]


def _write_inflation_fixture(data_root: Path, *, dated: bool) -> None:
    """Contract-legal inflation_system mutation + remanifest (N2)."""
    victim = data_root / "workspaces" / "inflation_system" / "US" / "latest.json"
    snap = json.loads(victim.read_text(encoding="utf-8"))
    if not dated:
        snap["headline"]["effective_date"] = None
        snap["headline"]["status"] = "ABSENT"
        snap["headline"]["null_reason"] = "NOT_YET_RELEASED"
    snap["changes"]["deltas"] = []
    snap["changes"]["comparability"] = "NO_PRIOR"
    snap["changes"]["status"] = "ABSENT"
    snap["changes"]["null_reason"] = "INSUFFICIENT_HISTORY"
    sealed = workspace_contract.finalize(snap)
    raw = json.dumps(sealed, ensure_ascii=False).encode("utf-8")
    victim.write_bytes(raw)
    manifest_path = data_root / "workspaces" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = manifest["workspaces"]["inflation_system/US"]
    entry["content_sha256"] = sealed["generation"]["content_sha256"]
    entry["bytes"] = len(raw)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def test_e1_fixture_through_the_real_builder(tmp_path: Path) -> None:
    """N2: E1 is the typed empty the real builder writes from a fixture."""
    data_root = tmp_path / "macrodata"
    shutil.copytree(DATA_ROOT, data_root)
    _write_inflation_fixture(data_root, dated=False)
    out = tmp_path / "site"
    builder.render(ROOT, data_root=data_root, out_dir=out, page_built_at=BUILT_AT)
    frag = unescape(
        (out / "macro" / "fragments" / "inflation.html").read_text(encoding="utf-8"))
    assert 'data-mc-empty="e1"' in frag
    assert "We don't have this reading yet" in frag
    assert "Empty e1" not in frag
    assert "Today's number didn't arrive" not in frag
    hub = unescape((out / "macro_monetary.html").read_text(encoding="utf-8"))
    inflation = re.search(
        r'<section class="mc-panel" id="inflation".*?(?=<section class="mc-panel"|</main>)',
        hub, re.S)
    assert inflation
    body = inflation.group(0)
    assert "We don't have this reading yet" in frag
    assert "We don't have this reading yet" not in body
    assert "This desk could not be read today" not in body
    assert "Each row shows the last two readings" not in body
    assert 'class="mc-caption"' not in body


def test_e3_fixture_through_the_real_builder(tmp_path: Path) -> None:
    """N2: a dated workspace with nothing comparable is E3, not E1."""
    data_root = tmp_path / "macrodata"
    shutil.copytree(DATA_ROOT, data_root)
    _write_inflation_fixture(data_root, dated=True)
    out = tmp_path / "site"
    builder.render(ROOT, data_root=data_root, out_dir=out, page_built_at=BUILT_AT)
    frag = unescape(
        (out / "macro" / "fragments" / "inflation.html").read_text(encoding="utf-8"))
    assert 'data-mc-empty="e3"' in frag
    assert "We can't show the change yet" in frag
    assert "We don't have this reading yet" not in frag
    assert "Empty e3" not in frag
    hub = unescape((out / "macro_monetary.html").read_text(encoding="utf-8"))
    inflation = re.search(
        r'<section class="mc-panel" id="inflation".*?(?=<section class="mc-panel"|</main>)',
        hub, re.S)
    assert inflation
    body = inflation.group(0)
    assert "We can't show the change yet" in frag
    assert "We can't show the change yet" not in body
    assert "Each row shows the last two readings" not in body
    assert 'class="mc-caption"' not in body


def test_empty_state_evidence_names_fixture_and_trigger() -> None:
    """N2: every builder-triggerable empty frame names its fixture + trigger."""
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "manifest.json")
        .read_text(encoding="utf-8"))
    states = {state.get("file"): state for state in _manifest_states(manifest)}
    for empty_id in ("e1", "e2", "e3", "e4", "e5", "e6"):
        for theme in ("dark", "light"):
            for name in (
                f"empty-{empty_id}-{theme}.png",
                f"empty-{empty_id}-{theme}-zh.png",
                f"empty-{empty_id}-{theme}-390.png",
                f"empty-{empty_id}-{theme}-zh-390.png",
            ):
                row = states[name]
                assert row["captured"] is True, name
                fixture = row.get("fixture")
                assert fixture, name
                if fixture != "builder-payload":
                    path = ROOT / "mockups" / "evidence" / "macro-command-p3" / fixture
                    if not path.is_file():
                        path = ROOT / fixture
                    assert path.is_file(), (name, fixture)
                assert row.get("trigger"), name
                png = ROOT / "mockups" / "evidence" / "macro-command-p3" / name
                assert png.is_file(), name
                data = png.read_bytes()
                assert data[:8] == b"\x89PNG\r\n\x1a\n", name
                assert b"IEND" in data, name
                if "zh" in name.split(".")[0].split("-"):
                    assert row.get("locale") == "zh", name


@pytest.mark.needs_full_checkout("site")
def test_rendered_l_zh_spans_have_cjk_or_are_pure_symbols(
        built: tuple[str, Path]) -> None:
    """M2: every `.l-zh` on the built hub carries CJK unless its sibling
    `.l-en` has no letters; a lettered EN string may not be copied into ZH."""
    html, _ = built
    # Ideographs plus CJK punctuation / fullwidth forms (e.g. U+FF1B `；`).
    _CJK = re.compile(r"[\u3000-\u303f\u3400-\u9fff\uf900-\ufaff\uff00-\uffef]")
    _LETTERS = re.compile(r"[A-Za-z]")
    pairs = re.findall(
        r'<span class="l-en">(.*?)</span>\s*<span class="l-zh">(.*?)</span>',
        html, re.S)
    assert pairs, "hub lost bilingual pairs"
    for en, zh in pairs:
        en_text = re.sub(r"<[^>]+>", "", en)
        zh_text = re.sub(r"<[^>]+>", "", zh)
        if not _LETTERS.search(en_text):
            continue
        assert _CJK.search(zh_text), (en_text, zh_text)
        assert zh_text != en_text, en_text


@pytest.mark.needs_full_checkout("site")
def test_copy_guard_is_green_on_the_rebuilt_page(built: tuple[str, Path]) -> None:
    html, _ = built
    assert guard.find_violations(html) == []


def test_dec_stance_is_guidance_record_exists() -> None:
    path = ROOT / "agentos" / "decisions" / "DEC-MACRO-COMMAND-STANCE-IS-GUIDANCE.md"
    text = path.read_text(encoding="utf-8")
    assert "never tells you what to do" in text
    assert "no score" in text


@pytest.mark.needs_full_checkout("site")
def test_arrival_ships_hidden_on_non_overview_panels(built: tuple[str, Path]) -> None:
    html, _ = built
    assert html.count("data-mc-arrival hidden") == len(P3_IDS) + len(P4_IDS) - 1
    overview = _panel(html, "overview")
    assert "data-mc-arrival" not in overview


@pytest.mark.needs_full_checkout("site")
def test_fragments_carry_the_authenticity_marker(built: tuple[str, Path]) -> None:
    _, out = built
    frag_dir = out / "macro" / "fragments"
    names = sorted(p.name for p in frag_dir.glob("*.html"))
    assert "overview.html" not in names
    expected = sorted(
        f"{section_id}.html"
        for section_id in (*P3_IDS, *P4_IDS)
        if section_id != "overview"
    )
    assert names == expected
    assert "money.html" in names
    assert "rates.html" in names
    assert "growth.html" in names
    money = (frag_dir / "money.html").read_text(encoding="utf-8")
    assert "data-mc-fragment" in money
    assert "data-mc-tabbody=\"liquidity\"" in money
    assert "data-mc-tabbody=\"central_banks\"" in money
    assert "class=\"mc-move\"" in money


def test_production_path_ignores_contract_forbidden_fixture_keys() -> None:
    """m-e: without --empty-state-fixture the production builder ignores
    entitlement and withheld_command_tabs exactly as additionalProperties:false
    requires."""
    entries = copy.deepcopy(_live_entries())
    for entry in entries:
        if entry["workspace_id"] == "liquidity_central_banks":
            entry["snapshot"]["withheld_command_tabs"] = ["central_banks"]
        if entry["workspace_id"] == "inflation_system":
            entry["snapshot"]["entitlement"] = "Research"
    assert builder._entitlement_plan(
        {"entitlement": "Research"}, allow_fixture_keys=False) is None
    assert builder._command_tab_withheld(
        {"withheld_command_tabs": ["central_banks"]},
        {"withheld_tabs": []}, "central_banks",
        allow_fixture_keys=False) is False
    sections = builder._macro_command_sections(entries, page_built_at=BUILT_AT)
    money = next(s for s in sections if s["id"] == "money")
    banks = next(t for t in money["subtabs"] if t["id"] == "central_banks")
    assert banks["empty"] is None
    assert banks["figure"] is not None
    inflation = next(s for s in sections if s["id"] == "inflation")
    assert inflation["empty"] is None
    assert inflation["figure"] is not None
    figure_rows = list((inflation["figure"] or {}).get("rows") or [])
    if any(row.get("kind") == "current" for row in figure_rows):
        assert inflation["caption"] is None
        assert inflation["figure"].get("state_line")
    else:
        assert inflation["caption"] is not None


def test_empty_state_fixture_flag_enables_e4_and_e6(tmp_path: Path) -> None:
    """The capture flag is what turns the sidecar keys on."""
    fixture = tmp_path / "e6.json"
    fixture.write_text(json.dumps({
        "empty_id": "e6",
        "workspace_id": "inflation_system",
        "entitlement": "Research",
    }), encoding="utf-8")
    out = tmp_path / "site"
    builder.render(ROOT, data_root=DATA_ROOT, out_dir=out, page_built_at=BUILT_AT,
                   empty_state_fixture=fixture)
    frag = unescape(
        (out / "macro" / "fragments" / "inflation.html").read_text(encoding="utf-8"))
    hub = unescape((out / "macro_monetary.html").read_text(encoding="utf-8"))
    assert 'data-mc-empty="e6"' in frag
    assert "Included in a higher plan" in frag
    inflation = re.search(
        r'<section class="mc-panel" id="inflation".*?(?=<section class="mc-panel"|</main>)',
        hub, re.S)
    assert inflation
    body = inflation.group(0)
    assert "包含在更高方案中" in frag
    assert "See it with an upgrade." in frag
    assert "升级即可查看。" in frag
    assert "查看升级方案" in frag
    assert "The reading is available on upgrade." in frag
    assert "The reading is available on upgrade." not in body
    assert "Each row shows the last two readings" not in body
    assert 'class="mc-caption"' not in body


def test_one_null_voice_for_every_section_level_empty() -> None:
    """MINOR-E6: E1–E6 drop the row caption; the empty card is the one voice."""
    for empty_id in ("e1", "e2", "e3", "e6"):
        voice = builder._apply_empty_voice(builder._empty_state(
            empty_id, plan="Research" if empty_id == "e6" else None))
        assert voice is None, empty_id


def test_p3_clearance_probes_are_real_geometry() -> None:
    """R9: 390 (4 cells) + 768 (2 cells) at scroll 0 / 50% / max.
    ok is false on any text-vs-fixed-overlay hit or an empty text set.
    excused[] is always present; scrollReached == target at every stop."""
    probes = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "probes.json")
        .read_text(encoding="utf-8"))
    keys = (
        "clearance_390_dark_en", "clearance_390_dark_zh",
        "clearance_390_light_en", "clearance_390_light_zh",
        "clearance_768_dark_en", "clearance_768_dark_zh",
        "clearance_768_light_en", "clearance_768_light_zh",
        "clearance_1440_dark_en", "clearance_1440_dark_zh",
        "clearance_1440_light_en", "clearance_1440_light_zh",
    )
    for key in keys:
        row = probes[key]
        assert row.get("ok") is True, (key, row.get("hits"), row)
        assert row.get("textCount", 0) > 0, (key, row)
        positions = row.get("positions") or {}
        assert set(positions) >= {"0", "50", "max"}, (key, positions.keys())
        for pos_name, pos in positions.items():
            assert pos.get("ok") is True, (key, pos_name, pos.get("hits"))
            assert pos.get("textCount", 0) > 0, (key, pos_name)
            assert "scrollY" in pos, (key, pos_name)
            assert pos.get("maxScrollMatched") is True, (key, pos_name, pos)
            assert isinstance(pos.get("excused"), list), (key, pos_name)
            assert isinstance(pos.get("hits"), list), (key, pos_name)
            assert "mmbBootDisplay" in pos, (key, pos_name)
            assert "mmbBootInDom" in pos, (key, pos_name)
            assert "mmbBootVisible" in pos, (key, pos_name)
        if key.startswith("clearance_390_") or key.startswith("clearance_768_"):
            assert row.get("mmbBootDisplay") == "none", (key, row)
            assert row.get("mmbBootInDom") is True, (key, row)
            assert row.get("mmbBootVisible") is False, (key, row)
            for pos_name, pos in positions.items():
                names = [ov.get("name") for ov in pos.get("overlays") or []]
                assert "mmb-boot" not in names, (key, names)
                for item in pos.get("excused") or []:
                    reason = str(item.get("reason") or "")
                    assert reason.endswith("_fully_covered") or reason.endswith(
                        "_partially_covered"), (key, pos_name, reason)
                    assert "box" in item and "ovBox" in item, (key, pos_name, item)
                    if reason.endswith("_fully_covered") or reason.endswith(
                            "_partially_covered"):
                        exposed = item.get("exposedAtScrollY")
                        assert exposed is not None, (key, pos_name, item)
                        assert 0 <= float(exposed) <= float(
                            pos.get("maxScroll") or 0), (key, pos_name, item)
                        assert "docTop" in item and "ovBottom" in item, (
                            key, pos_name, item)
                        assert abs(float(item["docTop"]) - float(item["ovBottom"])
                                   - float(exposed)) < 0.01, (key, pos_name, item)
        if key.startswith("clearance_1440_"):
            assert row.get("mmbBootDisplay") not in (None, "none"), (key, row)
            assert row.get("mmbBootInDom") is True, (key, row)
            assert row.get("mmbBootVisible") is True, (key, row)
            assert row.get("mmbBootBox"), (key, row)
            for pos_name, pos in positions.items():
                names = [ov.get("name") for ov in pos.get("overlays") or []]
                assert "mmb-boot" in names, (key, names)
                for item in pos.get("excused") or []:
                    reason = str(item.get("reason") or "")
                    if reason.endswith("_fully_covered") or reason.endswith(
                            "_partially_covered"):
                        exposed = item.get("exposedAtScrollY")
                        assert exposed is not None, (key, pos_name, item)
                        assert 0 <= float(exposed) <= float(
                            pos.get("maxScroll") or 0), (key, pos_name, item)
                        assert "docTop" in item and "ovBottom" in item, (
                            key, pos_name, item)
    # r10 evidence m2: no viewport-less clearance aliases.
    for alias in (
        "clearance_dark_en", "clearance_dark_zh",
        "clearance_light_en", "clearance_light_zh",
    ):
        assert alias not in probes, alias


def test_r9_fab_hidden_at_390_visible_at_1440() -> None:
    """DOM receipt: getComputedStyle(#mmb-boot).display is none at ≤768
    on this page and not none at 1440."""
    probes = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "probes.json")
        .read_text(encoding="utf-8"))
    for key in (
        "clearance_390_dark_en", "clearance_390_dark_zh",
        "clearance_390_light_en", "clearance_390_light_zh",
        "clearance_768_dark_en", "clearance_768_dark_zh",
        "clearance_768_light_en", "clearance_768_light_zh",
    ):
        assert probes[key]["mmbBootDisplay"] == "none", key
    for key in (
        "fab_display_1440_dark_en", "fab_display_1440_dark_zh",
        "fab_display_1440_light_en", "fab_display_1440_light_zh",
    ):
        fab = probes[key]
        assert fab.get("present") is True, (key, fab)
        assert fab.get("display") not in (None, "none"), (key, fab)
        assert fab.get("box"), (key, fab)
        assert float(fab["box"]["width"]) > 0, (key, fab)


def test_r9_default_390_frames_are_scroll_zero() -> None:
    """R9-M1: default 390 cells are captured at scroll 0; max twins exist."""
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "manifest.json")
        .read_text(encoding="utf-8"))
    states = {state.get("file"): state for state in _manifest_states(manifest)}
    for name in (
        "09-dark-en-390.png", "10-dark-zh-390.png",
        "11-light-en-390.png", "12-light-zh-390.png",
    ):
        row = states[name]
        assert row.get("captured") is True, name
        assert abs(float(row.get("scroll_y") or 0)) < 2, (name, row.get("scroll_y"))
        assert row.get("scroll") in (0, "0", None) or row.get("scroll") == 0
    for name in (
        "44-dark-en-390-max.png", "45-dark-zh-390-max.png",
        "46-light-en-390-max.png", "47-light-zh-390-max.png",
    ):
        row = states[name]
        assert row.get("captured") is True, name
        assert row.get("scroll") == "max", (name, row.get("scroll"))
        assert float(row.get("scroll_y") or 0) > 100, (name, row.get("scroll_y"))
    assert "capture_sha" in manifest
    assert "commit_time_of_capture_sha" in manifest
    assert "generated_at" in manifest
    assert "scroll_y" in states["01-dark-en-1440.png"]


def test_p3_evidence_frames_are_not_byte_duplicates() -> None:
    """m-d: a foot/detail frame must not be a copy of a composition frame."""
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "manifest.json")
        .read_text(encoding="utf-8"))
    by_sha: dict[str, list[str]] = {}
    for state in _manifest_states(manifest):
        if state.get("captured") and state.get("sha256") and state.get("file"):
            # MAJOR-2: strip-{theme}-{locale}.png is a dedicated same-
            # scroll 1440 viewport of #overview, so it may byte-match
            # the rest overview. The capture gate excludes the pair.
            if str(state["file"]).startswith("strip-"):
                continue
            by_sha.setdefault(state["sha256"], []).append(state["file"])
    dupes = {sha: names for sha, names in by_sha.items() if len(names) > 1}
    assert dupes == {}, dupes


def test_e2_evidence_names_fixture_and_trigger() -> None:
    """m-c: E2 rows name fixture + trigger like the other empty states."""
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "manifest.json")
        .read_text(encoding="utf-8"))
    states = {state.get("file"): state for state in _manifest_states(manifest)}
    for theme in ("dark", "light"):
        row = states[f"empty-e2-{theme}.png"]
        assert row["captured"] is True
        fixture = row.get("fixture")
        assert fixture
        if fixture != "builder-payload":
            path = ROOT / "mockups" / "evidence" / "macro-command-p3" / fixture
            if not path.is_file():
                path = ROOT / fixture
            assert path.is_file(), fixture
        assert row.get("trigger")
        assert "SOURCE_FAILED" in row["trigger"] or "STALE_SOURCE" in row["trigger"]


def _i4_delta(metric_id: str, *, current: str = "2.0",
              prior: str | None = "1.0", delta: str | None = "+1.0",
              sign: str | None = "up", comparable: bool = True) -> dict:
    return {
        "metric_id": metric_id,
        "label": dict(L.METRIC[metric_id]),
        "prior_present": comparable and prior is not None,
        "current_present": True,
        "delta_present": comparable and delta is not None,
        "prior": prior if comparable else None,
        "current": current,
        "delta": delta if comparable else None,
        "sign": sign if comparable else None,
        "is_movement": comparable,
    }


def _i4_view(*, prior_date: str | None, headline_date: str,
             deltas: list[dict], prior_is_earlier: bool | None = None) -> dict:
    changes: dict = {
        "prior_effective_date": prior_date,
        "deltas": deltas,
    }
    if prior_is_earlier is not None:
        changes["prior_is_earlier"] = prior_is_earlier
    return {
        "headline": {"effective_date": headline_date},
        "changes": changes,
    }


def test_i4_earlier_prior_is_a_movement_row() -> None:
    """I4 (a): a strictly earlier prior_effective_date is a movement row."""
    assert macro_suite_view.prior_publication_is_earlier(
        "2026-07-01", "2026-08-01") is True
    view = _i4_view(
        prior_date="2026-07-01", headline_date="2026-08-01",
        deltas=[_i4_delta("funding_pressure")],
        prior_is_earlier=True)
    figure, empty = builder._figure_or_empty_for_workspace(
        {"headline": {"effective_date": "2026-08-01"}},
        view=view, href="x.html")
    assert empty is None
    assert figure is not None
    assert figure["state_line"] is None
    assert "compared against the previous publication" in figure["count_text"]["en"]
    assert len(figure["rows"]) == 1
    row = figure["rows"][0]
    assert row["kind"] == "movement"
    assert row["prior"] == "1.0"
    assert row["delta"] == "+1.0"
    assert row["sign"] == "up"


@pytest.mark.parametrize("prior_date", ("2026-08-01", None, "not-a-date"))
def test_i4_equal_missing_or_unparseable_prior_is_current_only(
        prior_date: str | None) -> None:
    """I4 (b): equal / missing / unparseable prior → current-only + one state line."""
    assert macro_suite_view.prior_publication_is_earlier(
        prior_date, "2026-08-01") is False
    view = _i4_view(
        prior_date=prior_date, headline_date="2026-08-01",
        deltas=[_i4_delta("funding_pressure", delta="0", sign="flat")])
    figure, empty = builder._figure_or_empty_for_workspace(
        {"headline": {"effective_date": "2026-08-01"}},
        view=view, href="x.html")
    assert empty is None
    assert figure is not None
    assert figure["count_text"] is None
    assert figure["state_line"] == dict(L.COUNT["same_publication"])
    assert "compared against the previous publication" not in (
        (figure["count_text"] or {}).get("en") or "")
    assert figure["state_line"]["en"] == (
        "Only one reading is published so far — nothing earlier to compare yet.")
    assert figure["state_line"]["zh"] == "目前只有一次读数——暂无更早读数可比。"
    row = figure["rows"][0]
    assert row["kind"] == "current"
    assert row["current"] == "2.0"
    assert row["prior"] is None
    assert row["delta"] is None
    assert row["sign"] is None


def test_i4_mixed_rows_keep_both_kinds_and_one_state_line() -> None:
    """I4 (c): genuine earlier prior + a current-only sibling; state line once."""
    view = _i4_view(
        prior_date="2026-07-01", headline_date="2026-08-01",
        deltas=[
            _i4_delta("funding_pressure"),
            _i4_delta("nfci", prior=None, delta=None, sign=None, comparable=False),
        ],
        prior_is_earlier=True)
    figure, empty = builder._figure_or_empty_for_workspace(
        {"headline": {"effective_date": "2026-08-01"}},
        view=view, href="x.html")
    assert empty is None
    assert figure is not None
    kinds = [row["kind"] for row in figure["rows"]]
    assert kinds == ["movement", "current"]
    assert figure["count_text"] is None
    # R7-M1: a section mixed figure prints the mixed pair, never the
    # current-only "only one reading" sentence above a movement row.
    assert figure["state_line"] == dict(L.COUNT["overview_mixed"])
    assert figure["state_line"]["en"] == MIXED_DECK_EN
    assert figure["state_line"]["zh"] == MIXED_DECK_ZH
    assert figure["rows"][0]["delta"] == "+1.0"
    assert figure["rows"][1]["delta"] is None
    assert figure["rows"][1]["sign"] is None


def test_i4_exploding_compare_is_current_only(monkeypatch) -> None:
    """I4 (e): exception in the date comparison → current-only."""

    def _boom(*_a, **_k):
        raise RuntimeError("date compare exploded")

    monkeypatch.setattr(
        macro_suite_view, "prior_publication_is_earlier", _boom)
    view = _i4_view(
        prior_date="2026-07-01", headline_date="2026-08-01",
        deltas=[_i4_delta("funding_pressure", delta="0", sign="flat")])
    # no prior_is_earlier key → the builder must call the comparer
    figure, empty = builder._figure_or_empty_for_workspace(
        {"headline": {"effective_date": "2026-08-01"}},
        view=view, href="x.html")
    assert empty is None
    assert figure is not None
    assert figure["rows"][0]["kind"] == "current"
    assert figure["rows"][0]["sign"] is None
    assert figure["rows"][0]["delta"] is None
    assert figure["state_line"] == dict(L.COUNT["same_publication"])


@pytest.mark.needs_full_checkout("site")
def test_n5_m1_same_publication_fixture_uses_current_only_deck_once(
        built: tuple[str, Path]) -> None:
    """N5-M1: same-publication prior → current-only deck sentence once, EN+ZH."""
    html, _ = built
    overview = unescape(_panel(html, "overview"))
    assert overview.count(CURRENT_ONLY_DECK_EN) == 1
    assert overview.count(CURRENT_ONLY_DECK_ZH) == 1
    assert MOVEMENT_DECK_EN not in overview
    assert MOVEMENT_DECK_ZH not in overview
    assert "and what moved?" not in overview
    assert "有什么变化？" not in overview
    # One voice: the figure state line is not repeated under the stance.
    assert "Only one reading is published so far" not in overview
    assert "目前只有一次读数" not in overview


@pytest.mark.needs_full_checkout("site")
def test_n5_m2_hub_renders_only_populated_panels_with_stance(
        built: tuple[str, Path]) -> None:
    """N5-M2: rail count equals panel count.

    A populated figure keeps its stance. An empty card is the one null
    voice — no section stance (MINOR-E6). Live rates hydrates E2 from
    the fragment, so the hub also has no stance.
    """
    html, _ = built
    panels = re.findall(r'<section class="mc-panel" id="([^"]+)"', html)
    rail = re.findall(r'data-mc-section="([a-z]+)"', html)
    assert panels == list(P3_IDS) + list(P4_IDS)
    assert rail == list(P3_IDS) + list(P4_IDS)
    for section_id in panels:
        body = _panel(html, section_id)
        visible = re.sub(r"<template[^>]*>.*?</template>", "", body, flags=re.S)
        has_empty = bool(re.search(r'data-mc-empty="e[1-6]"', visible))
        has_stance = 'class="mc-stance' in visible
        if has_empty:
            assert not has_stance, section_id
        elif has_stance:
            continue
        else:
            assert 'data-mc-offer' in visible, section_id
    assert html.count('<span class="l-en">Overview</span>') >= 1
    assert html.count('<span class="l-zh">总览</span>') >= 1


@pytest.mark.needs_full_checkout("site")
def test_n5_m2_every_in_page_hash_resolves_to_a_real_anchor(
        built: tuple[str, Path]) -> None:
    html, _ = built
    ids = set(re.findall(r'\bid="([^"]+)"', html))
    for href in re.findall(r'href="#([^"]+)"', html):
        assert href in ids, href
    for section_id in P4_IDS:
        assert section_id in ids
    js = (ROOT / "templates" / "macro_command.js").read_text(encoding="utf-8")
    assert "sectionId = 'overview'" in js


@pytest.mark.needs_full_checkout("site")
def test_i4_live_hub_does_not_claim_a_comparison_it_did_not_make(
        built: tuple[str, Path]) -> None:
    html, _ = built
    overview = unescape(_panel(html, "overview"))
    assert overview.count(CURRENT_ONLY_DECK_EN) == 1
    assert overview.count(CURRENT_ONLY_DECK_ZH) == 1
    assert "compared against the previous publication" not in overview
    assert "mq-delta-flat" not in overview
    assert "Only one reading is published so far" not in overview


def test_i3_arrival_punctuation_lives_inside_the_t_pair() -> None:
    src = (ROOT / "templates" / "macro_monetary.html.j2").read_text(encoding="utf-8")
    assert "{{ t('.', '。') }}" in src
    assert "宏观指挥台：') }}<b>" in src
    assert re.search(r"宏观指挥台：'\s*\)\s*\}\}<b>", src)
    # the Latin period must not sit outside the pair
    assert "</b>.</span>" not in src
    assert "</b>.</" not in src


def test_p3_manifest_axes_match_every_force_state_and_tablet_bucket() -> None:
    """N-M2: axes list every force_state; 768 is tablet; every row reduced_motion."""
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "manifest.json")
        .read_text(encoding="utf-8"))
    axes_states = set(manifest["axes"]["force_states"])
    assert manifest["axes"]["viewports"]["tablet"] == [768, 1400]
    assert "desktop" in manifest["axes"]["viewports"]
    seen: set[str] = set()
    for state in _manifest_states(manifest):
        assert state.get("reduced_motion") is True, state.get("file")
        fs = state.get("force_state")
        if fs:
            assert not str(fs).startswith("addendum:"), fs
            seen.add(str(fs))
        if state.get("viewport_width") == 768:
            assert state.get("viewport") == "tablet", state.get("file")
        if state.get("file") == "rates-curves-zh-after.png":
            raise AssertionError("stray rates-curves-zh-after.png still in manifest")
    assert seen == axes_states


def test_rider_m2_light_subtab_has_one_hairline() -> None:
    """RIDER M2: exactly one hairline between the pill row and the first row."""
    probes = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "probes.json")
        .read_text(encoding="utf-8"))
    row = probes["m2_hairline_light_en"]
    assert row.get("populated") is True, row
    assert row.get("hairlineCount") == 1, row
    assert row.get("tabbodyBorderTopPx") == 0, row
    assert row.get("figureBorderTopPx") == 1, row


def test_i1_rail_probe_has_no_document_overflow() -> None:
    probes = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "probes.json")
        .read_text(encoding="utf-8"))
    for key in ("rail_dark_en", "rail_dark_zh", "rail_light_en", "rail_light_zh"):
        row = probes[key]
        assert row["scrollWidth"] == row["clientWidth"], (key, row)
        assert row.get("noDocOverflow") is True, (key, row)
        assert row.get("listOverflowX") == "auto", (key, row)


MIXED_DECK_EN = "Some readings have no earlier print to compare yet."
MIXED_DECK_ZH = "部分读数暂无更早读数可比。"


def test_r6_m2_figure_mode_pure_movement_current_and_mixed() -> None:
    assert builder._figure_mode(
        [{"kind": "movement"}, {"kind": "movement"}]) == "movement"
    assert builder._figure_mode([{"kind": "current"}]) == "current"
    assert builder._figure_mode([]) == "none"
    assert builder._figure_mode(
        [{"kind": "movement"}, {"kind": "current"}]) == "mixed"


def _overview_from_rows(rows: list[dict], *, available: int = 4,
                        total: int = 5) -> dict:
    figure = builder._figure_block(
        rows, overview=True, shown=len(rows), total=len(rows))
    section = {
        "id": "overview",
        "first": True,
        "figure": figure,
        "question": None,
        "stance": None,
    }
    builder._apply_overview_deck(section, available=available, total=total)
    return section


def test_r6_m2_pure_movement_overview_keeps_movement_voice() -> None:
    section = _overview_from_rows([
        {"kind": "movement", "prior": "1", "current": "2", "delta": "+1",
         "sign": "up"},
        {"kind": "movement", "prior": "3", "current": "3", "delta": "0",
         "sign": "flat"},
    ])
    assert builder._figure_mode(section["figure"]["rows"]) == "movement"
    assert "and what moved" in section["question"]["en"]
    assert MIXED_DECK_EN not in section["stance"]["text"]["en"]
    assert CURRENT_ONLY_DECK_EN not in section["stance"]["text"]["en"]
    assert section["figure"]["state_line"] is None
    assert [row["kind"] for row in section["figure"]["rows"]] == [
        "movement", "movement"]


def test_r6_m2_pure_current_overview_uses_current_voice_once() -> None:
    section = _overview_from_rows([
        {"kind": "current", "prior": None, "current": "2", "delta": None,
         "sign": None},
    ])
    assert builder._figure_mode(section["figure"]["rows"]) == "current"
    assert "and what moved" not in section["question"]["en"]
    assert CURRENT_ONLY_DECK_EN in section["stance"]["text"]["en"]
    assert CURRENT_ONLY_DECK_ZH in section["stance"]["text"]["zh"]
    assert section["figure"]["state_line"] is None
    assert section["figure"]["rows"][0]["prior"] is None
    assert section["figure"]["rows"][0]["kind"] == "current"


def test_r6_m2_mixed_overview_keeps_state_line_and_mixed_sentence() -> None:
    section = _overview_from_rows([
        {"kind": "movement", "prior": "1", "current": "2", "delta": "+1",
         "sign": "up"},
        {"kind": "current", "prior": None, "current": "4", "delta": None,
         "sign": None},
    ])
    assert builder._figure_mode(section["figure"]["rows"]) == "mixed"
    assert "and what moved" in section["question"]["en"]
    assert MIXED_DECK_EN in section["stance"]["text"]["en"]
    assert MIXED_DECK_ZH in section["stance"]["text"]["zh"]
    assert CURRENT_ONLY_DECK_EN not in section["stance"]["text"]["en"]
    # R7-M1: Overview mixed deck already carries the pair — state_line None.
    assert section["figure"]["state_line"] is None
    kinds = [row["kind"] for row in section["figure"]["rows"]]
    assert kinds == ["movement", "current"]
    assert section["figure"]["rows"][0]["delta"] == "+1"
    assert section["figure"]["rows"][1]["prior"] is None


@pytest.mark.needs_full_checkout("site")
def test_r6_m3_chip_and_read_hrefs_resolve_to_rendered_sections(
        built: tuple[str, Path]) -> None:
    html, _ = built
    panel_ids = set(re.findall(r'<section class="mc-panel" id="([^"]+)"', html))
    assert panel_ids == set(P3_IDS + P4_IDS)
    chips = re.findall(r'<a class="mc-chip-link" href="#([^"]+)"', html)
    assert chips
    assert len(chips) == len(set(chips)), chips
    for href in chips:
        assert href in panel_ids, href
    topics = re.findall(
        r'<li class="mc-chip[^"]*" data-mc-topic="([^"]+)"', html)
    assert "coverage" in topics
    assert set(topics) - {"coverage"} <= panel_ids
    clauses = re.findall(
        r'<a class="mc-read-topic[^"]*" href="#([^"]+)"', html)
    assert clauses
    assert len(clauses) == len(set(clauses)), clauses
    for href in clauses:
        assert href in panel_ids, href
    note = re.search(
        r"(\d+) of (\d+) sections have today's data", unescape(html))
    assert note
    # Coverage denominator is populated panels (twelve), not chip count.
    assert int(note.group(2)) == len(P3_IDS + P4_IDS)


@pytest.mark.needs_full_checkout("site")
def test_r6_m1_hub_never_prints_twelve_as_a_section_count(
        built: tuple[str, Path]) -> None:
    html = unescape(built[0])
    visible = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S)
    visible = re.sub(r"<style[^>]*>.*?</style>", "", visible, flags=re.S)
    visible = re.sub(r'datetime="[^"]*"', "", visible)
    text = re.sub(r"<[^>]+>", " ", visible)
    n = len(P3_IDS + P4_IDS)
    # P3's lie was printing twelve while only five panels shipped. P4
    # populates all twelve, so the coverage denominator is twelve; fourteen
    # (the workspace count) remains the forbidden count.
    assert "Fourteen research" not in text
    assert "14 research" not in text
    assert "十四个研究" not in text
    assert f"{n} research sections" in text
    assert f"{n} 个研究板块" in text
    assert re.search(rf"\d+ of {n} sections have today's data", text)
    assert re.search(rf"{n}个板块中有\d+个有今日数据", text)


def test_r6_m2_stance_alone_is_not_populated() -> None:
    assert builder._panel_is_populated({"stance": {"text": "x"}}) is False
    assert builder._panel_is_populated({"figure": {"rows": [1]}}) is True
    assert builder._panel_is_populated({"empty": {"id": "e2"}}) is True
    assert builder._panel_is_populated(
        {"subtabs": [{"empty": {"id": "e4"}}]}) is True
    assert builder._panel_is_populated({"id": "growth"}) is False


def test_r6_m1_unpopulated_ids_constant_is_gone() -> None:
    assert not hasattr(builder, "P3_UNPOPULATED_IDS")


SAME_PUBLICATION_EN = (
    "Only one reading is published so far — nothing earlier to compare yet.")
SAME_PUBLICATION_ZH = "目前只有一次读数——暂无更早读数可比。"


def test_r7_m1_overview_mixed_deck_mixed_state_line_none() -> None:
    """R7-M1: Overview mixed → mixed pair in the deck, state_line None."""
    section = _overview_from_rows([
        {"kind": "movement", "prior": "1", "current": "2", "delta": "+1",
         "sign": "up"},
        {"kind": "current", "prior": None, "current": "4", "delta": None,
         "sign": None},
    ])
    assert builder._figure_mode(section["figure"]["rows"]) == "mixed"
    assert MIXED_DECK_EN in section["stance"]["text"]["en"]
    assert MIXED_DECK_ZH in section["stance"]["text"]["zh"]
    assert section["figure"]["state_line"] is None
    assert section["figure"]["count_text"] is None
    assert SAME_PUBLICATION_EN not in section["stance"]["text"]["en"]
    assert SAME_PUBLICATION_ZH not in section["stance"]["text"]["zh"]


def test_r7_m1_section_mixed_state_line_is_the_mixed_pair() -> None:
    """R7-M1: section mixed → state_line is the mixed pair, EN and ZH."""
    figure = builder._figure_block(
        [
            {"kind": "movement", "prior": "1", "current": "2", "delta": "+1",
             "sign": "up"},
            {"kind": "current", "prior": None, "current": "4", "delta": None,
             "sign": None},
        ],
        overview=False, shown=2, total=2)
    assert builder._figure_mode(figure["rows"]) == "mixed"
    assert figure["state_line"] == dict(L.COUNT["overview_mixed"])
    assert figure["state_line"]["en"] == MIXED_DECK_EN
    assert figure["state_line"]["zh"] == MIXED_DECK_ZH
    assert figure["count_text"] is None
    assert SAME_PUBLICATION_EN not in figure["state_line"]["en"]
    assert SAME_PUBLICATION_ZH not in figure["state_line"]["zh"]


def test_r7_m1_current_prints_same_publication_exactly_once() -> None:
    """R7-M1: current mode → same_publication once; no count; EN and ZH."""
    figure = builder._figure_block(
        [{"kind": "current", "prior": None, "current": "2", "delta": None,
          "sign": None}],
        overview=False, shown=1, total=1)
    assert builder._figure_mode(figure["rows"]) == "current"
    assert figure["state_line"] == dict(L.COUNT["same_publication"])
    assert figure["state_line"]["en"] == SAME_PUBLICATION_EN
    assert figure["state_line"]["zh"] == SAME_PUBLICATION_ZH
    assert figure["count_text"] is None
    overview = _overview_from_rows(list(figure["rows"]))
    assert overview["figure"]["state_line"] is None
    assert CURRENT_ONLY_DECK_EN in overview["stance"]["text"]["en"]
    assert CURRENT_ONLY_DECK_ZH in overview["stance"]["text"]["zh"]
    assert SAME_PUBLICATION_EN not in overview["stance"]["text"]["en"]
    joined = (
        (overview["stance"]["text"]["en"] or "")
        + (overview["figure"].get("state_line") or {}).get("en", ""))
    assert joined.count(SAME_PUBLICATION_EN) == 0
    assert figure["state_line"]["en"].count(SAME_PUBLICATION_EN) == 1


def test_r7_m1_movement_has_count_text_and_no_state_line() -> None:
    """R7-M1: movement mode → count_text present, no state line, EN and ZH."""
    rows = [
        {"kind": "movement", "prior": "1", "current": "2", "delta": "+1",
         "sign": "up"},
        {"kind": "movement", "prior": "3", "current": "3", "delta": "0",
         "sign": "flat"},
    ]
    section_fig = builder._figure_block(
        rows, overview=False, shown=2, total=2)
    assert builder._figure_mode(section_fig["rows"]) == "movement"
    assert section_fig["state_line"] is None
    assert section_fig["count_text"] is not None
    assert "compared against the previous publication" in section_fig["count_text"]["en"]
    assert "与上一次发布相比" in section_fig["count_text"]["zh"]
    overview = _overview_from_rows(rows)
    assert overview["figure"]["state_line"] is None
    assert overview["figure"]["count_text"] is not None
    assert "compared readings" in overview["figure"]["count_text"]["en"]
    assert "可比读数" in overview["figure"]["count_text"]["zh"]
    assert MIXED_DECK_EN not in overview["stance"]["text"]["en"]
    assert SAME_PUBLICATION_EN not in (overview["figure"]["count_text"]["en"] or "")


def test_r7_m2_strip_void_probe_has_no_filled_slab() -> None:
    """R7-M2 / R8-m1: 1440 dark+light × EN+ZH — no ≥40px void outside a chip."""
    probes = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "probes.json")
        .read_text(encoding="utf-8"))
    rows = probes.get("strip_void_probes") or {}
    assert set(rows) == {"dark_en", "dark_zh", "light_en", "light_zh"}
    for key, row in rows.items():
        assert row.get("ok") is True, (key, row)
        assert row.get("voidWiderThan40") is False, (key, row)
        assert "filledOutsideWiderThan40" not in row, (key, row)
        assert "holeWiderThan40" not in row, (key, row)
        assert row.get("emptyChildren") == 0, (key, row)
        assert row.get("chipCount") == row.get("childCount"), (key, row)
        assert row.get("pixelVoidWiderThan40") is False, (key, row)
        assert row.get("canvasRgb"), (key, row)
        assert row.get("canvasSource"), (key, row)
        assert "strip-inter-chip-gap" in str(row.get("canvasSource")), (key, row)
        assert "css" in str(row.get("canvasSource")), (key, row)
        assert row.get("bgTokenRgb"), (key, row)
        assert row.get("delta") is not None, (key, row)
        assert all(int(channel) <= 2 for channel in row["delta"]), (key, row)
        assert int(row.get("pixelsScanned") or 0) > 0, (key, row)
        assert row.get("scrollYAtMeasure") is not None, (key, row)
        assert row.get("scrollYAtShot") is not None, (key, row)
        assert abs(float(row["scrollYAtMeasure"]) - float(row["scrollYAtShot"])) <= 0.01, (
            key, row)
        sample = str(row.get("canvasSource") or "")
        assert "css" in sample, (key, sample)
        # Sample y is the second css number and must be on-viewport.
        match = re.search(r"\(([-0-9.]+)css,([-0-9.]+)css\)", sample)
        assert match, (key, sample)
        assert float(match.group(2)) >= 0, (key, sample)
    assert "strip_void_probe" not in probes


def test_r8_m1_empty_and_unknown_kind_are_mode_none() -> None:
    """r8-m1: empty / unrecognised rows must not print the current-only claim."""
    assert builder._figure_mode([]) == "none"
    assert builder._figure_mode([{"kind": "weird"}]) == "none"
    empty = builder._figure_block([], overview=False, shown=0, total=0)
    assert empty["state_line"] is None
    assert empty["count_text"] is None
    unknown = builder._figure_block(
        [{"kind": "weird"}], overview=False, shown=1, total=1)
    assert unknown["state_line"] is None
    assert unknown["count_text"] is None
    overview_empty = _overview_from_rows([])
    assert overview_empty["question"] is None
    assert overview_empty["figure"]["state_line"] is None
    assert overview_empty["figure"]["count_text"] is None
    joined_en = json.dumps(overview_empty, ensure_ascii=False)
    assert "Only one reading is published so far" not in joined_en
    assert "目前只有一次读数" not in joined_en
    overview_unknown = _overview_from_rows([{"kind": "weird"}])
    assert overview_unknown["question"] is None
    assert overview_unknown["figure"]["state_line"] is None
    assert overview_unknown["figure"]["count_text"] is None
    joined_zh = json.dumps(overview_unknown, ensure_ascii=False)
    assert "Only one reading is published so far" not in joined_zh
    assert "目前只有一次读数" not in joined_zh


def test_capture_refuses_dirty_tree(monkeypatch) -> None:
    """r10-M1: a fake dirty `git status --short` must abort the capture."""
    from scripts import capture_macro_command_p3 as capture

    monkeypatch.setattr(
        capture, "_git_status_short",
        lambda *paths: " M templates/macro_command.css\n")
    monkeypatch.setattr(capture, "_head_sha", lambda: "deadbeef")
    with pytest.raises(RuntimeError, match="dirty worktree"):
        capture._require_clean_tree(when="start")


def test_capture_refuses_when_head_moves(monkeypatch) -> None:
    """r10-M1: HEAD must be the same at start and end."""
    from scripts import capture_macro_command_p3 as capture

    monkeypatch.setattr(capture, "_head_sha", lambda: "bbbbbbbb")
    with pytest.raises(RuntimeError, match="HEAD moved"):
        capture._assert_head_unmoved("aaaaaaaa")


def test_pixel_scan_raises_when_gap_too_small(tmp_path) -> None:
    """MAJOR-2: gap < 8 css is a hard error, never a silent --bg pass."""
    from PIL import Image

    from scripts import capture_macro_command_p3 as capture

    image = Image.new("RGB", (40, 20), (13, 16, 24))
    path = tmp_path / "strip.png"
    image.save(path)
    probe = {
        "stripBox": {"left": 0, "right": 20, "top": 0, "bottom": 10},
        "chipBoxes": [
            {"left": 0, "right": 9.5, "top": 0, "bottom": 10},
            {"left": 10, "right": 20, "top": 0, "bottom": 10},
        ],
        "bgToken": "#0d1018",
        "viewport": {"innerHeight": 10},
    }
    with pytest.raises(RuntimeError, match="gap .* < 8"):
        capture._pixel_scan_strip_void(path, probe, scale=2)


def test_pixel_scan_raises_on_in_chip_sample(tmp_path) -> None:
    """MAJOR-2: a sample that lands in a chip raises, never falls back."""
    from PIL import Image

    from scripts import capture_macro_command_p3 as capture

    image = Image.new("RGB", (80, 20), (13, 16, 24))
    boxes = [
        {"left": 0, "right": 10, "top": 0, "bottom": 10},
        {"left": 20, "right": 30, "top": 0, "bottom": 10},
    ]

    def in_chip(_x: int, _y: int) -> bool:
        return True

    with pytest.raises(RuntimeError, match="landed inside a chip"):
        capture._choose_strip_canvas(
            image, boxes, 2, in_chip, "#0d1018", viewport_height=10)


def test_pixel_scan_raises_on_negative_boxes(tmp_path) -> None:
    """MAJOR-2: a probe whose chip row sits above the viewport must raise."""
    from PIL import Image

    from scripts import capture_macro_command_p3 as capture

    image = Image.new("RGB", (80, 20), (13, 16, 24))
    path = tmp_path / "strip.png"
    image.save(path)
    probe = {
        "stripBox": {"left": 0, "right": 40, "top": -80, "bottom": -20},
        "chipBoxes": [
            {"left": 0, "right": 10, "top": -80, "bottom": -20},
            {"left": 20, "right": 30, "top": -80, "bottom": -20},
        ],
        "bgToken": "#0d1018",
        "viewport": {"innerHeight": 10},
    }
    with pytest.raises(RuntimeError, match="outside"):
        capture._pixel_scan_strip_void(path, probe, scale=2)


def test_pixel_scan_detects_synthetic_void(tmp_path) -> None:
    """MAJOR-2: a known ≥40 css px non-canvas run outside chips is a void."""
    from PIL import Image

    from scripts import capture_macro_command_p3 as capture

    image = Image.new("RGB", (200, 20), (13, 16, 24))
    for x in range(80, 180):
        for y in range(20):
            image.putpixel((x, y), (200, 10, 10))
    path = tmp_path / "strip.png"
    image.save(path)
    probe = {
        "stripBox": {"left": 0, "right": 100, "top": 0, "bottom": 10},
        "chipBoxes": [
            {"left": 0, "right": 10, "top": 0, "bottom": 10},
            {"left": 20, "right": 30, "top": 0, "bottom": 10},
        ],
        "bgToken": "#0d1018",
        "viewport": {"innerHeight": 10},
    }
    row = capture._pixel_scan_strip_void(path, probe, scale=2)
    assert row.get("pixelVoidWiderThan40") is True
    assert row.get("ok") is False
    assert int(row.get("pixelsScanned") or 0) > 0


def test_pixel_scan_gap_matches_bg_token(tmp_path) -> None:
    """MINOR-3: a gap sample must match --bg ±2 and name the CSS point."""
    from PIL import Image

    from scripts import capture_macro_command_p3 as capture

    image = Image.new("RGB", (80, 20), (13, 16, 24))
    path = tmp_path / "strip.png"
    image.save(path)
    probe = {
        "stripBox": {"left": 0, "right": 40, "top": 0, "bottom": 10},
        "chipBoxes": [
            {"left": 0, "right": 10, "top": 0, "bottom": 10},
            {"left": 20, "right": 30, "top": 0, "bottom": 10},
        ],
        "bgToken": "#0d1018",
        "viewport": {"innerHeight": 10},
    }
    row = capture._pixel_scan_strip_void(path, probe, scale=2)
    assert "15.00css" in str(row.get("canvasSource"))
    assert int(row.get("pixelsScanned") or 0) > 0
    assert row.get("canvasRgb") == [13, 16, 24]
    assert row.get("bgTokenRgb") == [13, 16, 24]
    assert row.get("delta") == [0, 0, 0]


def test_pixel_scan_raises_when_gap_mismatches_bg(tmp_path) -> None:
    from PIL import Image

    from scripts import capture_macro_command_p3 as capture

    image = Image.new("RGB", (80, 20), (200, 10, 10))
    path = tmp_path / "strip.png"
    image.save(path)
    probe = {
        "stripBox": {"left": 0, "right": 40, "top": 0, "bottom": 10},
        "chipBoxes": [
            {"left": 0, "right": 10, "top": 0, "bottom": 10},
            {"left": 20, "right": 30, "top": 0, "bottom": 10},
        ],
        "bgToken": "#0d1018",
        "viewport": {"innerHeight": 10},
    }
    with pytest.raises(RuntimeError, match="!= --bg"):
        capture._pixel_scan_strip_void(path, probe, scale=2)


def test_pixel_scan_raises_when_bg_token_does_not_parse(tmp_path) -> None:
    """r11-n2: fallback token that does not parse is a hard error."""
    from PIL import Image

    from scripts import capture_macro_command_p3 as capture

    image = Image.new("RGB", (80, 20), (10, 20, 30))
    path = tmp_path / "strip.png"
    image.save(path)
    probe = {
        "stripBox": {"left": 0, "right": 40, "top": 0, "bottom": 10},
        "chipBoxes": [
            {"left": 0, "right": 10, "top": 0, "bottom": 10},
            {"left": 20, "right": 30, "top": 0, "bottom": 10},
        ],
        "bgToken": "not-a-colour",
        "viewport": {"innerHeight": 10},
    }
    with pytest.raises(RuntimeError, match="no parsable --bg"):
        capture._pixel_scan_strip_void(path, probe, scale=2)


def test_r10_chip_opens_chat_receipts() -> None:
    """r10 evidence m4: ≤768 analyst chip mounts #mmb-root on dark+light 390."""
    probes = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "probes.json")
        .read_text(encoding="utf-8"))
    for key in (
        "chip_opens_chat_390_dark_en", "chip_opens_chat_390_light_en",
        "chip_opens_chat_390_dark_zh", "chip_opens_chat_390_light_zh",
    ):
        row = probes[key]
        assert row.get("ok") is True, (key, row)
        assert row.get("clicked") == "data-mc-analyst", (key, row)
        assert row.get("mountedId") == "mmb-root", (key, row)


def test_r10_measured_clean_tree_protocol() -> None:
    """r10-M1: manifest records measured start/end clean-tree + head fields."""
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "manifest.json")
        .read_text(encoding="utf-8"))
    for key in (
        "tree_clean_start", "tree_clean_end",
        "head_start", "head_end",
        "generated_at_start", "generated_at_end",
        "commit_time_of_capture_sha",
    ):
        assert key in manifest, key
    assert manifest["tree_clean_start"] is True
    assert manifest["tree_clean_end"] is True
    assert manifest["head_start"] == manifest["head_end"]
    assert manifest["head_start"] == manifest["capture_sha"]
    source = manifest["target"]["resolved_sha_source"]
    assert f"tree_clean_start={manifest['tree_clean_start']}" in source
    assert f"tree_clean_end={manifest['tree_clean_end']}" in source
    assert "git status --short was empty" not in source


def test_r12_device_px_matches_playwright_snap(tmp_path: Path) -> None:
    """E-M1 / MINOR-C4: crop IHDR uses _device_px, not round()."""
    from PIL import Image

    from scripts import capture_macro_command_p3 as capture

    assert capture._device_px(199.453125, 566.453125, 2.0) == 1134
    assert capture._device_px(0.0, 1440.0, 2.0) == 2880
    assert capture._device_px(0.0, 900.0, 2.0) == 1800
    dest = tmp_path / "crop.png"
    Image.new("RGB", (1134, 80), (10, 20, 30)).save(dest)
    box = {"x": 199.453125, "y": 10.0, "width": 566.453125, "height": 40.0}
    extra = {
        "dpr": 2.0,
        "crop": True,
        "crop_box": box,
        "crop_selector": ".mc-figure",
        "device_px_span": capture._device_px_span(box, 2.0),
    }
    # 80 == _device_px(10.0, 40.0, 2.0)
    capture._assert_shot_geometry(dest, extra, 1440, 900)
    assert extra["ihdr_delta_px"] == {"w": 0, "h": 0}


def test_r12_clearance_js_has_no_target_zero_gate() -> None:
    """r11-M2: HIT is document geometry; the JS must not gate on target === '0'."""
    from scripts import capture_macro_command_p3 as capture

    assert "target === '0'" not in capture.CLEARANCE_AT_JS
    assert "sticky-rail-full-cover-unexposable" in capture.CLEARANCE_AT_JS
    assert "exposedAtScrollY" in capture.CLEARANCE_AT_JS


def test_r12_synthetic_clearance_manifest_consistency() -> None:
    """Manifest-consistency only — does not claim to test the hit rule."""
    from scripts import capture_macro_command_p3 as capture

    assert not hasattr(capture, "_synthetic_clearance_page")
    probes = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "probes.json")
        .read_text(encoding="utf-8"))
    row = probes["synthetic_clearance"]
    positions = row["positions"]
    assert set(positions) >= {"0", "50", "max"}
    receipts = row.get("synthetic_hit_rule") or {}
    assert set(receipts) >= {"inside zone", "below zone", "under pill"}
    for station in ("0", "50", "max"):
        assert receipts["inside zone"][station]["verdict"] == "hit", station
    assert any(
        row.get("verdict") == "excused"
        and row.get("exposedAtScrollY") is not None
        for row in receipts["below zone"].values())
    assert any(row.get("verdict") == "hit" for row in receipts["under pill"].values())
    for pos in positions.values():
        for item in list(pos.get("excused") or []) + list(pos.get("hits") or []):
            if "exposedAtScrollY" not in item:
                continue
            assert "docTop" in item and "ovBottom" in item, item
            assert abs(float(item["docTop"]) - float(item["ovBottom"])
                       - float(item["exposedAtScrollY"])) < 0.01


def test_r14_clearance_hit_rule_runs_shipped_js_in_playwright() -> None:
    """MINOR-B: live Playwright run of the shipped CLEARANCE_AT_JS."""
    from scripts import capture_macro_command_p3 as capture

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("Playwright not installed")

    try:
        playwright_cm = sync_playwright().start()
    except Exception as exc:
        pytest.skip(f"Playwright runtime unavailable: {exc}")
    try:
        try:
            browser = playwright_cm.chromium.launch(headless=True, channel="chrome")
        except Exception:
            try:
                browser = playwright_cm.chromium.launch(headless=True)
            except Exception as exc:
                pytest.skip(f"Chromium unavailable: {exc}")
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            row = capture._run_synthetic_clearance(page)
        finally:
            browser.close()
    finally:
        playwright_cm.stop()
    receipts = row["synthetic_hit_rule"]
    for station in ("0", "50", "max"):
        assert receipts["inside zone"][station]["verdict"] == "hit", station
    excused = [item for item in receipts["below zone"].values()
               if item.get("verdict") == "excused"]
    assert excused and excused[0].get("exposedAtScrollY") is not None
    assert any(item.get("verdict") == "hit" for item in receipts["under pill"].values())


def test_r12_manifest_shot_schema() -> None:
    """E-M1: every captured state records dpr/crop and IHDR matches the kind."""
    from scripts import capture_macro_command_p3 as capture

    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "manifest.json")
        .read_text(encoding="utf-8"))
    evidence = ROOT / "mockups" / "evidence" / "macro-command-p3"
    for page in manifest["pages"]:
        for state in page.get("states") or []:
            if not state.get("captured"):
                continue
            assert "dpr" in state and state["dpr"] is not None, state.get("file")
            assert state.get("crop") in (True, False), state.get("file")
            assert state.get("fixture") is not None, state.get("file")
            dest = evidence / state["file"]
            extra = {
                "dpr": state["dpr"],
                "crop": state["crop"],
                "full_page": state.get("full_page"),
                "crop_box": state.get("crop_box"),
                "crop_selector": state.get("crop_selector"),
                "device_px_span": state.get("device_px_span"),
            }
            capture._assert_shot_geometry(
                dest, extra, state["viewport_width"], state["viewport_height"])
            if state.get("crop"):
                assert state.get("crop_box_doc"), state.get("file")
                assert "scroll_y_at_shot" in state, state.get("file")
                assert state.get("element_text_head") is not None, state.get("file")
                span = state.get("device_px_span") or {}
                assert set(span) >= {"x0", "x1", "y0", "y1"}, state.get("file")
                recomputed = capture._device_px_span_from_crop_box_doc(
                    state["crop_box_doc"], state["scroll_y_at_shot"],
                    float(state["dpr"]))
                assert span == recomputed, (state.get("file"), span, recomputed)
                delta = extra.get("ihdr_delta_px") or {}
                assert delta.get("w", 99) <= 1, (state.get("file"), delta)
                assert delta.get("h", 99) <= 1, (state.get("file"), delta)
                assert "ihdr_delta_px" in state, state.get("file")


def test_r12_gaps_are_computed_from_declared_minus_captured() -> None:
    """E-M2 / MINOR-E1: manifest.gaps is declared − captured, 0 phantoms."""
    from scripts import capture_macro_command_p3 as capture

    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "manifest.json")
        .read_text(encoding="utf-8"))
    probes = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "probes.json")
        .read_text(encoding="utf-8"))
    declared = manifest["declared"]
    expected_families = {
        "force_states", "empty_states", "clearance", "chip_opens_chat",
        "strip_void", "rail_viewport", "e5", "fab",
        "rest_views", "full_page", "movement_row",
    }
    assert set(declared) == expected_families
    for family, cells in declared.items():
        assert cells, family
        honesty = manifest["honesty"]["gaps"]
        assert "reason" in honesty
    states = [state for page in manifest["pages"] for state in page.get("states") or []]
    captured = capture._captured_declared_keys(states, probes)
    computed = capture._compute_gaps_from_declared(declared, captured)
    assert computed == manifest["gaps"]
    assert computed == []
    declared_keys = {
        capture._declared_cell_key(cell)
        for cells in declared.values()
        for cell in cells
    }
    assert declared_keys - captured == set()
    assert captured - declared_keys == set()
    empty_declared = capture._declared_empty_cells()
    assert len(empty_declared) == 6 * 2 * 2 * 2
    for page in _manifest_pages(manifest):
        empty_gaps = capture._compute_gaps(empty_declared, page.get("states") or [])
        assert empty_gaps == page.get("gaps")


def test_r12_no_orphan_strip_void_probe() -> None:
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "manifest.json")
        .read_text(encoding="utf-8"))
    probes = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "probes.json")
        .read_text(encoding="utf-8"))
    assert "strip_void_probe" not in manifest
    assert "strip_void_probe" not in probes


def test_r12_e5_timeout_receipts() -> None:
    probes = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "probes.json")
        .read_text(encoding="utf-8"))
    for theme in ("dark", "light"):
        for locale in ("en", "zh"):
            for vw in (1440, 390):
                key = f"e5_timeout_{theme}_{locale}_{vw}"
                row = probes[key]
                assert row.get("elapsedMs") >= 8000, (key, row)
                assert row.get("requestSeenAtMs") is not None, (key, row)
                assert row.get("cloneSeenAtMs") is not None, (key, row)
                assert float(row["cloneSeenAtMs"]) > float(row["requestSeenAtMs"]), (
                    key, row)
                assert float(row["elapsedMs"]) == (
                    float(row["cloneSeenAtMs"]) - float(row["requestSeenAtMs"])
                ), (key, row)
                assert row.get("templatePresent") is True, (key, row)
                assert row.get("clonePresent") is True, (key, row)
                assert row.get("headline"), (key, row)


def test_r12_choose_strip_canvas_fallback_label() -> None:
    """MAJOR-2: the canvas sample raises off-row; --bg is never a silent pass."""
    from scripts import capture_macro_command_p3 as capture

    src = capture._choose_strip_canvas.__doc__ or ""
    fn_src = Path(capture.__file__).read_text(encoding="utf-8")
    assert 'getPropertyValue(\'--bg\')' in capture.STRIP_VOID_JS
    assert "bodyBackgroundColor" in capture.STRIP_VOID_JS
    assert "bgResolved" not in capture.STRIP_VOID_JS
    assert "never clamped" in src
    assert 'origin["x0"] + width' not in fn_src
    assert 'extra["device_px_span"] = _device_px_span' in fn_src


def test_r12_rail_viewport_receipts() -> None:
    probes = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "probes.json")
        .read_text(encoding="utf-8"))
    for theme in ("dark", "light"):
        for locale in ("en", "zh"):
            for vw in (390, 768):
                key = f"rail_viewport_{theme}_{locale}_{vw}"
                row = probes[key]
                assert row.get("ok") is True, (key, row)
                assert row.get("firstFullyVisibleAt0") is True, (key, row)
                assert row.get("everyReachable") is True, (key, row)
                assert row.get("fadeBandOk") is True, (key, row)
                assert row.get("fadeWidth", 0) >= 24 - 0.5, (key, row)
                assert row.get("fadeBeginsBeforeAnalyst", 0) >= 24 - 0.5, (
                    key, row)
                mask = row.get("maskRaw") or row.get("maskImage") or row.get(
                    "webkitMaskImage")
                assert mask and mask != "none", (key, row)
                assert "calc(100%" in str(mask) or "%" in str(mask), (key, mask)
                if row.get("fadeVisualApplicable"):
                    assert row.get("fadeOnsetX") is not None, (key, row)
                    assert row.get("fadeVisualStartX") is not None, (key, row)
                    assert abs(float(row["fadeOnsetX"]) - float(row["fadeLeft"])) <= 4, (
                        key, row)
                    assert float(row["fadeVisualStartX"]) >= float(row["fadeOnsetX"]) - 0.5, (
                        key, row)
                else:
                    assert row.get("fadeVisualReason") in {
                        "maxScrollLeft=0", "no chip under the band",
                    }, (key, row)
                    assert row.get("fadeVisualStartX") is None, (key, row)
                assert row.get("chips"), (key, row)
                for chip in row["chips"]:
                    assert chip.get("fullyVisible") is True, (key, chip)
                    assert chip.get("fullyVisibleAtScrollLeft") is not None, (
                        key, chip)
                    assert chip.get("underAnalyst") is False, (key, chip)
                    assert chip.get("overflow") != "hidden", (key, chip)
                    assert chip.get("whiteSpace") == "nowrap", (key, chip)
                    assert chip["scrollWidth"] <= chip["clientWidth"] + 1, (
                        key, chip)
                assert f"rail_clip_{theme}_{locale}_{vw}" not in probes


def test_r12_chip_material_receipts() -> None:
    probes = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "probes.json")
        .read_text(encoding="utf-8"))
    for theme in ("dark", "light"):
        for locale in ("en", "zh"):
            for vw in (390, 768):
                key = f"chip_material_{theme}_{locale}_{vw}"
                row = probes[key]
                assert row.get("ok") is True, (key, row)
                assert row.get("mismatches") == [], (key, row)
                for prop in (
                    "borderRadius", "paddingTop", "paddingRight",
                    "paddingBottom", "paddingLeft", "fontSize",
                ):
                    assert row["analyst"][prop] == row["sibling"][prop], (
                        key, prop, row)


def test_r14_movement_row_element_shots() -> None:
    """NIT-8: four element shots of a movement row, value + unit + phrase."""
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "manifest.json")
        .read_text(encoding="utf-8"))
    states = {state.get("file"): state for state in _manifest_states(manifest)}
    for theme in ("dark", "light"):
        for locale in ("en", "zh"):
            name = f"movement-row-{theme}-{locale}.png"
            row = states[name]
            assert row.get("crop") is True, name
            assert row.get("crop_selector") == (
                "#inflation .mc-move-row:not(.mc-move-current-only)"), name
            head = str(row.get("element_text_head") or "")
            assert re.search(r"\d", head), (name, head)
            assert len(head) > 12, (name, head)


def test_r15_ihdr_3px_wider_than_span_raises(tmp_path: Path) -> None:
    """MAJOR-1: a PNG whose IHDR is 3 px wider than the element span raises."""
    from PIL import Image

    from scripts import capture_macro_command_p3 as capture

    dest = tmp_path / "wide.png"
    Image.new("RGB", (103, 50), (0, 0, 0)).save(dest)
    extra = {
        "dpr": 2.0,
        "crop": True,
        "crop_selector": "#x",
        "device_px_span": {"x0": 0, "x1": 100, "y0": 0, "y1": 50},
    }
    with pytest.raises(RuntimeError, match="device_px_span"):
        capture._assert_shot_geometry(dest, extra, 1440, 900)


def test_r15_ihdr_within_1px_of_span_passes(tmp_path: Path) -> None:
    """MAJOR-1: Playwright's 1 device-px rounding is recorded, not fatal."""
    from PIL import Image

    from scripts import capture_macro_command_p3 as capture

    dest = tmp_path / "near.png"
    Image.new("RGB", (101, 50), (0, 0, 0)).save(dest)
    extra = {
        "dpr": 2.0,
        "crop": True,
        "crop_selector": "#x",
        "device_px_span": {"x0": 0, "x1": 100, "y0": 0, "y1": 50},
    }
    capture._assert_shot_geometry(dest, extra, 1440, 900)
    assert extra["ihdr_delta_px"] == {"w": 1, "h": 0}


def test_r15_device_px_span_is_element_box_only() -> None:
    """MAJOR-1: the writer assigns _device_px_span(box); PNG width is unused."""
    from scripts import capture_macro_command_p3 as capture

    src = Path(capture.__file__).read_text(encoding="utf-8")
    assert 'extra["device_px_span"] = _device_px_span(box_before, extra["dpr"])' in src
    assert "origin[\"x0\"] + width" not in src


def test_r15_device_px_span_uses_enclosing_css_rect() -> None:
    """MAJOR-E1: opposing fractional edges must not produce a 2 px short span."""
    from scripts import capture_macro_command_p3 as capture

    # The heading-focus ZH failure: raw floor(x*dpr)/ceil((x+h)*dpr)
    # is 58 tall; enclosing CSS × dpr is 60, matching Playwright.
    box = {"x": 353.2, "y": 112.6, "width": 43.6, "height": 28.8}
    span = capture._device_px_span(box, 2.0)
    assert span["x1"] - span["x0"] == 88
    assert span["y1"] - span["y0"] == 60
    raw_h = int(math.ceil((112.6 + 28.8) * 2) - math.floor(112.6 * 2))
    assert raw_h == 58


def test_r15_strip_frames_are_declared_and_captured() -> None:
    """MAJOR-2 / MINOR-E4: dedicated strip frames belong to strip_void."""
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "manifest.json")
        .read_text(encoding="utf-8"))
    states = {state.get("file"): state for state in _manifest_states(manifest)}
    for theme in ("dark", "light"):
        for locale in ("en", "zh"):
            name = f"strip-{theme}-{locale}.png"
            row = states[name]
            assert row.get("captured") is True, name
            assert row.get("crop") is False, name
            assert row.get("viewport_width") == 1440, name


def test_r15_e3_overview_crop_is_force_state_not_empty() -> None:
    """MINOR-E4: *-1440-e3.png is force_states even though crop=True."""
    from scripts import capture_macro_command_p3 as capture

    states = [
        {
            "file": "25-dark-en-1440-e3.png",
            "captured": True,
            "force_state": "e3",
            "theme": "dark",
            "locale": "en",
            "viewport_width": 1440,
            "crop": True,
        },
        {
            "file": "empty-e3-dark.png",
            "captured": True,
            "force_state": "e3",
            "theme": "dark",
            "locale": "en",
            "viewport_width": 1440,
            "crop": True,
        },
    ]
    keys = capture._captured_declared_keys(states, {})
    assert ("force_states", "e3", "dark", "en", 1440) in keys
    assert ("empty_states", "e3", "dark", "en", 1440) in keys
