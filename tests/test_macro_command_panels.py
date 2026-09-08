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
        panel = _panel(html, section_id)
        order = _child_classes(panel)
        assert order[0] == "mc-arrival", section_id
        assert "mc-panel-head" in order
        assert "mc-stance" in order
        assert "mc-primer" in order
        assert "mc-figure" in order
        # m1: an E2 figure has no rows, so the "each row shows…" caption is dropped.
        if ('data-mc-empty="e2"' in panel
                or "Today's number didn't arrive" in unescape(panel)):
            assert "mc-caption" not in order
        else:
            assert "mc-caption" in order, (section_id, order)
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
    assert "fourteen" not in copy["en"]
    assert "十四" not in copy["zh"]
    assert f"{n} research sections" in copy["en"]
    assert f"{n} 个研究板块" in copy["zh"]


def test_deck_count_changes_when_the_rail_length_changes() -> None:
    eleven = macro_suite_view._deck_copy(11)
    twelve = macro_suite_view._deck_copy(12)
    assert eleven != twelve
    assert "11 research sections" in eleven["en"]
    assert "12 research sections" in twelve["en"]
    assert "11 个研究板块" in eleven["zh"]


def test_built_page_has_one_section_count_matching_the_rail(
        built: tuple[str, Path]) -> None:
    html, _ = built
    n = len(builder.SECTIONS)
    assert html.count("Fourteen research") == 0
    assert html.count("十四个研究") == 0
    assert html.count(f"{n} research sections") == 1
    assert html.count(f"{n} 个研究板块") == 1
    assert f"of {n} sections" in html
    assert f"{n} 个板块中" in html


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


def test_dests_heading_names_destination_pages_not_research_sections(
        built: tuple[str, Path]) -> None:
    """n4: 12 and 14 are labelled as different counts."""
    html, _ = built
    overview = unescape(_panel(html, "overview"))
    assert "12 research sections" in overview
    assert "12 个研究板块" in overview
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
    sections = builder._macro_command_sections(entries, page_built_at=BUILT_AT)
    money = next(s for s in sections if s["id"] == "money")
    withheld = next(t for t in money["subtabs"] if t["id"] == "central_banks")
    assert withheld["empty"]["id"] == "e4"
    assert "Not open yet" in withheld["empty"]["title"]["en"]
    assert withheld["figure"] is None


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
        entitlement=builder._entitlement_plan(snap))
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


def test_empty_state_evidence_names_fixture_and_trigger() -> None:
    """N2: every builder-triggerable empty frame names its fixture + trigger."""
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p3" / "manifest.json")
        .read_text(encoding="utf-8"))
    states = {state.get("file"): state for state in manifest["pages"][0]["states"]}
    for empty_id in ("e1", "e3", "e4", "e6"):
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
              if s.get("force_state") == "addendum:empty-e5-dark.png")
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
