"""A43 corpus guard: the committed responsive/keyboard evidence must prove the row.

Masterplan row A43 condition "EN/ZH desktop/tablet/mobile and keyboard use"
requires "Readable responsive layout, focus restore, no clipping and correct
disabled/unavailable text." The Z1 review graded the row PARTIAL
(``kind: test_gap``): the capture tool recorded the keyboard walk but never the
Escape-close focus restore, and never the disabled/unavailable control text.
This guard reads the committed corpus only (JSON, no browser, <2s) and fails
until every regenerated receipt carries those facts.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "mockups" / "evidence" / "fundamental_forensics_p2"

VIEWPORTS = ("desktop", "tablet", "mobile")
LOCALES = ("en", "zh")
THEMES = ("dark", "light")
# 3 viewports x 2 locales x 2 themes = 12 rest cells per set.
CELL_KEYS = {(v, l, t) for v in VIEWPORTS for l in LOCALES for t in THEMES}
# Per set: the rest state plus one state per forced interaction.
POPULATED_FORCE_STATES = ("source_hover", "lead_open_focus", "drawer_open")
KEYBOARD_FORCE_STATES = ("tab_keys", "drawer_trap")
# keyboard interactions.json = 3 viewports x {tab_keys, drawer_trap} x 2 x 2.
KEYBOARD_RECEIPT_KINDS = ("tab_keys", "drawer_trap")
KEYBOARD_RECEIPT_COUNT = 24

# templates/fundamental_forensics.html.j2:87-90 and :119-122: the two disabled
# desk controls A43 names, with the locale labels their data-label-* carry.
DISABLED_CONTROL_LABELS = {
    "#ff-export-btn": {"en": "Export unavailable", "zh": "导出不可用"},
    "#ff-saved-save": {"en": "Save this view", "zh": "保存当前视图"},
}

pytestmark = pytest.mark.needs_full_checkout("mockups")


def _manifest(set_name: str) -> dict:
    return json.loads((CORPUS / set_name / "manifest.json").read_text(encoding="utf-8"))


def _interactions(set_name: str) -> list[dict]:
    return json.loads((CORPUS / set_name / "interactions.json").read_text(encoding="utf-8"))


def _states(set_name: str) -> list[dict]:
    return _manifest(set_name)["pages"][0]["states"]


def _receipt_cell_key(receipt: dict) -> tuple[str, str, str]:
    return (receipt["viewport"], receipt["locale"], receipt["theme"])


# ---------------------------------------------------------------------------
# coverage: every viewport x locale x theme cell exists and captured
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("set_name", ["populated", "keyboard"])
def test_manifest_covers_every_viewport_locale_theme_cell(set_name: str) -> None:
    states = _states(set_name)
    expected_states = {
        (None, key) for key in CELL_KEYS
    } | {
        (force, key)
        for force in (
            POPULATED_FORCE_STATES if set_name == "populated" else KEYBOARD_FORCE_STATES
        )
        for key in CELL_KEYS
    }
    seen = {(row["force_state"], (row["viewport"], row["locale"], row["theme"])) for row in states}
    assert seen == expected_states
    assert all(row["captured"] for row in states)
    totals = _manifest(set_name)["totals"]
    assert totals["states_attempted"] == totals["states_captured"] == len(expected_states)


def test_keyboard_manifest_is_36_states() -> None:
    assert len(_states("keyboard")) == 36


def test_keyboard_interactions_are_exactly_24_verified_receipts() -> None:
    receipts = _interactions("keyboard")
    assert len(receipts) == KEYBOARD_RECEIPT_COUNT
    seen = {(receipt["interaction"], _receipt_cell_key(receipt)) for receipt in receipts}
    assert seen == {
        (kind, key) for kind in KEYBOARD_RECEIPT_KINDS for key in CELL_KEYS
    }
    tab_keys = [r for r in receipts if r["interaction"] == "tab_keys"]
    assert len(tab_keys) == 12
    assert all(r["verified"] is True for r in tab_keys), [
        r["cell_id"] for r in tab_keys if r["verified"] is not True
    ]


def test_drawer_trap_receipts_prove_escape_close_and_focus_restore() -> None:
    traps = [r for r in _interactions("keyboard") if r["interaction"] == "drawer_trap"]
    assert len(traps) == 12
    for receipt in traps:
        cell = receipt["cell_id"]
        assert receipt["verified"] is True, cell
        facts = receipt["facts"]
        # Enter opened the drawer with keyboard focus on its close button.
        assert facts["opened"]["focus_id"] == "ff-evidence-close", cell
        # Escape closed it and focus went back to the product's restore target
        # (the selected finding's own button, or the CTA fallback) — the fact
        # records which of the two observables held.
        closed = facts["closed"]
        assert closed["open"] is False, cell
        assert closed["focus_restored"] is True, cell
        assert (
            closed["focus_matches_trigger"] or closed["focus_on_finding_button"]
        ), cell


# ---------------------------------------------------------------------------
# disabled/unavailable text on every rest cell and keyboard receipt
# ---------------------------------------------------------------------------


def _assert_disabled_control_entry(entry: dict, locale: str, origin: str) -> None:
    selector = entry["selector"]
    assert selector in DISABLED_CONTROL_LABELS, (origin, selector)
    assert entry["present"] is True, (origin, selector)
    assert entry["disabled"] is True, (origin, selector)
    expected = DISABLED_CONTROL_LABELS[selector][locale]
    assert entry["visible_text"] == expected, (origin, selector, entry["visible_text"])
    assert entry["label_en"] == DISABLED_CONTROL_LABELS[selector]["en"], (origin, selector)
    assert entry["label_zh"] == DISABLED_CONTROL_LABELS[selector]["zh"], (origin, selector)
    assert entry["tip"], (origin, selector)


def test_populated_rest_cells_carry_disabled_controls_receipts() -> None:
    receipts = [
        r for r in _interactions("populated") if r["interaction"] == "disabled_controls"
    ]
    seen = {_receipt_cell_key(r) for r in receipts}
    assert seen == CELL_KEYS
    assert len(receipts) == 12
    for receipt in receipts:
        assert receipt["force_state"] is None, receipt["cell_id"]
        assert receipt["verified"] is True, receipt["cell_id"]
        controls = receipt["facts"]["controls"]
        assert len(controls) == 2, receipt["cell_id"]
        for entry in controls:
            _assert_disabled_control_entry(entry, receipt["locale"], receipt["cell_id"])


def test_keyboard_receipts_probe_the_none_state_controls() -> None:
    receipts = _interactions("keyboard")
    for receipt in receipts:
        controls = receipt["facts"]["disabled_controls"]
        assert len(controls) == 2, receipt["cell_id"]
        for entry in controls:
            _assert_disabled_control_entry(entry, receipt["locale"], receipt["cell_id"])


# ---------------------------------------------------------------------------
# tablet preset + no clipping
# ---------------------------------------------------------------------------


def test_tablet_cells_use_the_capture_tool_tablet_preset() -> None:
    # The preset is read from the capture module, not hard-coded here.
    from scripts.capture_page_evidence import VIEWPORTS

    tablet_width, tablet_height = VIEWPORTS["tablet"]
    for set_name in ("populated", "keyboard"):
        tablet_rows = [row for row in _states(set_name) if row["viewport"] == "tablet"]
        # 4 tablet cells (2 locales x 2 themes), one row per state each.
        states_per_cell = 1 + len(
            POPULATED_FORCE_STATES if set_name == "populated" else KEYBOARD_FORCE_STATES
        )
        assert len(tablet_rows) == 4 * states_per_cell, set_name
        for row in tablet_rows:
            assert row["viewport_width"] == tablet_width, (set_name, row["file"])
            assert row["viewport_height"] == tablet_height, (set_name, row["file"])


@pytest.mark.parametrize("set_name", ["populated", "keyboard"])
def test_no_tablet_clipping_in_the_smell_report(set_name: str) -> None:
    """No overflow on any viewport: smells.json pages[].metrics.by_viewport.<vp>
    reports ``horizontal_overflow`` false and ``elements_wider_than_viewport``
    == 0 for desktop, tablet AND mobile — those two fields are the corpus's
    overflow/clip smell. Tablet is the Z1-named gap; desktop/mobile are pinned
    too so a regenerated corpus cannot clip anywhere (Z1 re-review F3)."""
    smells = json.loads((CORPUS / set_name / "smells.json").read_text(encoding="utf-8"))
    by_viewport = smells["pages"][0]["metrics"]["by_viewport"]
    assert set(by_viewport) >= {"desktop", "tablet", "mobile"}, (set_name, sorted(by_viewport))
    for viewport in ("desktop", "tablet", "mobile"):
        metrics = by_viewport[viewport]
        assert metrics["horizontal_overflow"] is False, (set_name, viewport)
        assert metrics["elements_wider_than_viewport"] == 0, (set_name, viewport)
