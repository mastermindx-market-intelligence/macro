"""Macro Command P3 — panel contract, rail order, derived deck, fail-closed.

Frozen pin + addendum: every P3 section renders question → stance → figure+
caption → watching in that DOM order; Overview movement is the one figure;
directory is rail-ordered and outside `.mc-figure`; the deck count is derived
from the rail, never hardcoded as fourteen.
"""
from __future__ import annotations

import copy
import json
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
    rows = re.findall(r'class="mx-chg-row mc-move-row', figure.group(0))
    assert len(rows) == 5
    dests = re.search(r'<ul class="mc-dests">', overview)
    assert dests
    # directory is not inside the figure
    assert 'class="mc-dests"' not in figure.group(0)


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


def test_p3_non_overview_dom_order(built: tuple[str, Path]) -> None:
    html, _ = built
    for section_id in ("money", "policy", "rates", "inflation"):
        panel = _panel(html, section_id)
        order = _child_classes(panel)
        assert order[0] == "mc-arrival", section_id
        assert "mc-panel-head" in order
        assert "mc-stance" in order
        assert "mc-primer" in order
        assert "mc-figure" in order
        # M2: a section-level empty (live #rates is E2) drops the caption.
        # The hidden E5 <template> also carries data-mc-empty — ignore it.
        text = unescape(panel)
        # Caption is a comparison claim. E2 (section empty) and I4
        # (same-publication current-only, often only in the fragment)
        # must not keep it.
        if ("Today's number didn't arrive" in text
                or "Only one reading is published so far" in text
                or "Each row shows the last two readings" not in text):
            assert "mc-caption" not in order, (section_id, order)
        else:
            assert "mc-caption" in order, (section_id, order)
        assert "mc-watch" in order
        assert "mc-details" in order
        assert order.index("mc-stance") < order.index("mc-figure") < order.index("mc-watch")
        if section_id == "inflation":
            assert "mc-foot" in order


def test_p4_sections_are_not_rendered_as_empty_shells(
        built: tuple[str, Path]) -> None:
    """N5-M2: P3 ships only populated panels — no offer-only P4 shells."""
    html, _ = built
    for section_id in P4_IDS:
        assert f'id="{section_id}"' not in html, section_id
        assert f'data-mc-panel="{section_id}"' not in html, section_id
        assert f'data-mc-section="{section_id}"' not in html, section_id


def test_panel_focus_and_subtab_aria_yield_to_shipped_p1(built: tuple[str, Path]) -> None:
    html, _ = built
    assert len(re.findall(r'<section class="mc-panel"[^>]*tabindex', html)) == 0
    titles = re.findall(r'<h2 class="mc-panel-title"[^>]*>', html)
    assert len(titles) == len(P3_IDS)
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


def test_built_page_has_one_section_count_matching_the_rail(
        built: tuple[str, Path]) -> None:
    html, _ = built
    n = len(P3_IDS)
    assert html.count("Fourteen research") == 0
    assert html.count("十四个研究") == 0
    assert html.count(f"{n} research sections") == 1
    assert html.count(f"{n} 个研究板块") == 1
    # Coverage chip still owns the 12-section completeness integer (C10).
    assert "of 12 sections" in html
    assert "12 个板块中" in html


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
    policy = _panel(html, "policy")
    assert 'data-mc-empty="e1"' not in policy
    assert "No single reading is published here" in policy


def test_e2_figure_prints_the_e2_stance_not_the_structural_null(
        built: tuple[str, Path]) -> None:
    """M6 branch 1: #rates is E2 today — stance matches the empty title.

    The empty figure lives in the fragment (JS hydrates `[data-mc-figure]`);
    the stance is in the panel shell.
    """
    html, out = built
    rates = unescape(_panel(html, "rates"))
    fragment = (out / "macro" / "fragments" / "rates.html").read_text(encoding="utf-8")
    assert 'data-mc-empty="e2"' in fragment
    assert "Today's number didn't arrive" in rates
    assert "No single reading is published here" not in rates
    assert "Each row shows the last two readings" not in rates
    assert "hasn't arrived" in unescape(html)  # strip chip stays the transient voice


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


def test_built_hub_9_of_12_uses_some_unread_stance(built: tuple[str, Path]) -> None:
    """N0: today's 9/12 chip and the Overview stance are one completeness."""
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
    assert available < total
    assert (available, total) == macro_suite_view.section_coverage_tally(_live_entries())
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


def test_twelve_of_twelve_uses_all_read_stance() -> None:
    """N0: only a full section tally may wear the complete / ok stance."""
    entries = copy.deepcopy(_live_entries())
    for entry in entries:
        snap = entry.get("snapshot")
        if snap is not None:
            snap.setdefault("availability", {})["state"] = "CURRENT"
    available, total = macro_suite_view.section_coverage_tally(entries)
    assert (available, total) == (12, 12)
    sections = builder._macro_command_sections(entries, page_built_at=BUILT_AT)
    overview = next(s for s in sections if s["id"] == "overview")
    assert overview["stance"]["tone"] == "ok"
    assert "Every desk reported today" in overview["stance"]["text"]["en"]
    assert "今天每个小组都有读数" in overview["stance"]["text"]["zh"]
    # Live data is same-publication, so the current-only deck sentence wins.
    if _figure_is_current_only(overview):
        assert CURRENT_ONLY_DECK_EN in overview["stance"]["text"]["en"]
        assert MOVEMENT_DECK_EN not in overview["stance"]["text"]["en"]


def test_dests_heading_names_destination_pages_not_research_sections(
        built: tuple[str, Path]) -> None:
    """n4: 12 and 14 are labelled as different counts."""
    html, _ = built
    overview = unescape(_panel(html, "overview"))
    assert "5 research sections" in overview
    assert "5 个研究板块" in overview
    assert "Where to go next — 14 destination pages" in overview
    assert "接下来去哪里——14 个目标页面" in overview


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
    assert "We don't have this reading yet" in body
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
    assert "We can't show the change yet" in body
    assert "Each row shows the last two readings" not in body
    assert 'class="mc-caption"' not in body


def test_empty_state_evidence_names_fixture_and_trigger() -> None:
    """N2: every builder-triggerable empty frame names its fixture + trigger."""
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "manifest.json")
        .read_text(encoding="utf-8"))
    states = {state.get("file"): state for state in manifest["pages"][0]["states"]}
    for empty_id in ("e1", "e2", "e3", "e4", "e6"):
        for theme in ("dark", "light"):
            name = f"empty-{empty_id}-{theme}.png"
            row = states[name]
            assert row["captured"] is True, name
            assert row.get("fixture"), name
            assert (ROOT / row["fixture"]).is_file(), row["fixture"]
            assert row.get("trigger"), name
            png = ROOT / "mockups" / "evidence" / "macro-command-p3" / name
            assert png.is_file(), name
            data = png.read_bytes()
            assert data[:8] == b"\x89PNG\r\n\x1a\n", name
            assert b"IEND" in data, name
            assert len(data) > 20000, (name, len(data))
    e5 = next(s for s in manifest["pages"][0]["states"]
              if s.get("force_state") == "e5")
    assert e5["captured"] is False
    assert "not builder-triggerable" in e5["reason"]


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


def test_copy_guard_is_green_on_the_rebuilt_page(built: tuple[str, Path]) -> None:
    html, _ = built
    assert guard.find_violations(html) == []


def test_dec_stance_is_guidance_record_exists() -> None:
    path = ROOT / "agentos" / "decisions" / "DEC-MACRO-COMMAND-STANCE-IS-GUIDANCE.md"
    text = path.read_text(encoding="utf-8")
    assert "never tells you what to do" in text
    assert "no score" in text


def test_arrival_ships_hidden_on_non_overview_panels(built: tuple[str, Path]) -> None:
    html, _ = built
    assert html.count("data-mc-arrival hidden") == len(P3_IDS) - 1
    overview = _panel(html, "overview")
    assert "data-mc-arrival" not in overview


def test_fragments_carry_the_authenticity_marker(built: tuple[str, Path]) -> None:
    _, out = built
    frag_dir = out / "macro" / "fragments"
    names = sorted(p.name for p in frag_dir.glob("*.html"))
    assert "overview.html" not in names
    assert names == ["inflation.html", "money.html", "policy.html", "rates.html"]
    assert "money.html" in names
    assert "rates.html" in names
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
    inflation = re.search(
        r'<section class="mc-panel" id="inflation".*?(?=<section class="mc-panel"|</main>)',
        hub, re.S)
    assert inflation
    body = inflation.group(0)
    assert "Included in a higher plan" in body
    assert "Each row shows the last two readings" not in body
    assert 'class="mc-caption"' not in body


def test_one_null_voice_for_every_section_level_empty() -> None:
    """M2: E1–E6 drop the row caption; section-level empties share the slot title."""
    for empty_id in ("e1", "e2", "e3", "e6"):
        voice = builder._apply_empty_voice(builder._empty_state(
            empty_id, plan="Research" if empty_id == "e6" else None))
        assert voice is not None
        assert voice["tone"] == "neutral"
        assert voice["text"]["en"] == L.EMPTY_STATES[empty_id]["title"]["en"]


def test_p3_clearance_probes_are_real_geometry() -> None:
    """N-B1: four 390 max-scroll measurements. The file records the numbers;
    this test does not move the page. lastBottom <= pillTop, and the scroll
    actually reached equals scrollHeight - innerHeight."""
    probes = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "probes.json")
        .read_text(encoding="utf-8"))
    for key in ("clearance_dark_en", "clearance_dark_zh",
                "clearance_light_en", "clearance_light_zh"):
        row = probes[key]
        assert row.get("lastBottom") is not None, key
        assert row["lastBottom"] > 0, (key, row)
        assert row.get("pillTop") is not None and row["pillTop"] > 0, (key, row)
        assert row.get("pillHeight") is not None and row["pillHeight"] > 0, (key, row)
        assert row.get("clear") is True, (key, row)
        assert row["lastBottom"] <= row["pillTop"], (key, row)
        max_scroll = row["scrollHeight"] - row["innerHeight"]
        assert abs(row["maxScroll"] - max_scroll) < 2, (key, row)
        assert abs(row["scrollReached"] - row["maxScroll"]) < 2, (key, row)
        assert row.get("maxScrollMatched") is True, (key, row)


def test_p3_evidence_frames_are_not_byte_duplicates() -> None:
    """m-d: a foot/detail frame must not be a copy of a composition frame."""
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "manifest.json")
        .read_text(encoding="utf-8"))
    by_sha: dict[str, list[str]] = {}
    for state in manifest["pages"][0]["states"]:
        if state.get("captured") and state.get("sha256") and state.get("file"):
            by_sha.setdefault(state["sha256"], []).append(state["file"])
    dupes = {sha: names for sha, names in by_sha.items() if len(names) > 1}
    assert dupes == {}, dupes


def test_e2_evidence_names_fixture_and_trigger() -> None:
    """m-c: E2 rows name fixture + trigger like the other empty states."""
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "manifest.json")
        .read_text(encoding="utf-8"))
    states = {state.get("file"): state for state in manifest["pages"][0]["states"]}
    for theme in ("dark", "light"):
        row = states[f"empty-e2-{theme}.png"]
        assert row["captured"] is True
        assert row.get("fixture")
        assert (ROOT / row["fixture"]).is_file()
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
    assert figure["state_line"] == dict(L.COUNT["same_publication"])
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


def test_n5_m2_hub_renders_only_populated_panels_with_stance(
        built: tuple[str, Path]) -> None:
    """N5-M2: every section has a stance; rail count equals panel count."""
    html, _ = built
    panels = re.findall(r'<section class="mc-panel" id="([^"]+)"', html)
    rail = re.findall(r'data-mc-section="([a-z]+)"', html)
    assert panels == list(P3_IDS)
    assert rail == list(P3_IDS)
    for section_id in panels:
        body = _panel(html, section_id)
        assert 'class="mc-stance' in body, section_id
    # Destination cards still name the fourteen workspaces; the Growth
    # *panel* is what must be gone (offer-only shells).
    assert html.count('<span class="l-en">Overview</span>') >= 1
    assert html.count('<span class="l-zh">总览</span>') >= 1


def test_n5_m2_unpopulated_hash_resolves_to_overview_anchor(
        built: tuple[str, Path]) -> None:
    html, _ = built
    ids = set(re.findall(r'\bid="([^"]+)"', html))
    for href in re.findall(r'href="#([^"]+)"', html):
        assert href in ids, href
        assert href not in P4_IDS
    js = (ROOT / "templates" / "macro_command.js").read_text(encoding="utf-8")
    assert "sectionId = 'overview'" in js


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
    for state in manifest["pages"][0]["states"]:
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
