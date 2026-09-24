"""Non-regression checks for the public Nuclear theme surface."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = REPO_ROOT / "tests/fixtures/energy_non_regression/nuclear_baseline.json"
MEMBERSHIP_PATH = REPO_ROOT / "data/baskets/membership.json"
THEME_STATE_PATH = REPO_ROOT / "data/neuralweb/theme_state.json"
PUBLIC_PAGE_PATHS = (
    REPO_ROOT / "site/basket/nuclear_power.html",
    REPO_ROOT / "site/state_of_themes.html",
)
MEMBERSHIP_FIELDS = ("ticker", "added", "removed", "curated_added")
THEME_STATE_FIELDS = (
    "theme_id",
    "name_en",
    "name_zh",
    "foresight",
    "basket_intel",
    "radar",
    "narrative",
    "basket_ids",
)
THEME_TRACKER_FIELDS = (
    "theme_id",
    "name_en",
    "name_zh",
    "lane",
    "lane_rank",
    "stance_en",
    "stance_zh",
    "story_en",
    "story_zh",
    "fav_count",
    "caut_count",
    "present_count",
    "stage_raw",
    "stage_key",
    "stage_label_en",
    "stage_label_zh",
    "stage_sort",
    "falsifier_any_fired",
    "falsifier_label",
    "filter_flags",
    "leadership_context",
    "entry_context",
)
PRIVATE_DOSSIER_CANARIES = (
    "economic_change_dossier",
    "Nuclear Value Capture",
    "realized price",
    "contingent_within_leu",
    "Westinghouse displayed revenue",
    "PRE_EVENT_TIMESTAMPED_VALUE",
)


def _read_baseline() -> dict[str, Any]:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _load_state_builder() -> Any:
    module_path = REPO_ROOT / "scripts/build_state_of_themes.py"
    spec = importlib.util.spec_from_file_location("build_state_of_themes", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import Theme Tracker builder from {module_path}.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _project(value: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: value.get(field) for field in fields}


def _needs_checkout(*directories: str) -> bool:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from scripts.worktree_sparse import missing_dirs

    return bool(set(directories) & set(missing_dirs(REPO_ROOT)))


def _basket_snapshot(basket_id: str) -> dict[str, Any]:
    document = json.loads(MEMBERSHIP_PATH.read_text(encoding="utf-8"))
    basket = document["baskets"][basket_id]
    return {
        "weighting": basket.get("weighting"),
        "weights": basket.get("weights"),
        "members": sorted(
            (
                {field: member.get(field) for field in MEMBERSHIP_FIELDS}
                for member in basket.get("members", [])
            ),
            key=lambda member: member["ticker"],
        ),
    }


def _nuclear_theme_state() -> dict[str, Any]:
    document = json.loads(THEME_STATE_PATH.read_text(encoding="utf-8"))
    theme = next(
        theme for theme in document["themes"] if theme.get("theme_id") == "nuclear_power"
    )
    return _project(theme, THEME_STATE_FIELDS)


def _nuclear_theme_tracker() -> dict[str, Any]:
    builder = _load_state_builder()
    context = builder.compose(REPO_ROOT)
    theme = next(
        theme for theme in context["themes"] if theme.get("theme_id") == "nuclear_power"
    )
    projected = _project(theme, THEME_TRACKER_FIELDS)
    return json.loads(json.dumps(projected))


def test_nuclear_power_membership_unchanged_vs_frozen_baseline() -> None:
    baseline = _read_baseline()
    assert _basket_snapshot("nuclear_power") == baseline["basket_membership"]["nuclear_power"]
    assert (
        _canonical_sha256(baseline["basket_membership"])
        == baseline["section_sha256"]["basket_membership"]
    )


def test_uranium_miners_membership_unchanged_vs_frozen_baseline() -> None:
    baseline = _read_baseline()
    assert (
        _basket_snapshot("uranium_miners") == baseline["basket_membership"]["uranium_miners"]
    )
    assert (
        _canonical_sha256(baseline["basket_membership"])
        == baseline["section_sha256"]["basket_membership"]
    )


def test_primary_and_supplemental_populations_are_disjoint_and_never_merged() -> None:
    primary = _basket_snapshot("nuclear_power")
    supplemental = _basket_snapshot("uranium_miners")
    primary_tickers = {member["ticker"] for member in primary["members"]}
    supplemental_tickers = {member["ticker"] for member in supplemental["members"]}
    assert not primary_tickers & supplemental_tickers
    assert {"BWXT", "SMR", "OKLO"} <= primary_tickers
    assert {"CCJ", "LEU"} <= supplemental_tickers
    assert "LEU" not in primary_tickers
    assert all(ticker not in supplemental_tickers for ticker in ("BWXT", "SMR", "OKLO"))


@pytest.mark.needs_full_checkout("data") if _needs_checkout("data") else pytest.mark.needs_full_checkout()
def test_theme_state_fields_for_nuclear_unchanged() -> None:
    baseline = _read_baseline()
    assert _nuclear_theme_state() == baseline["theme_state"]
    assert _canonical_sha256(baseline["theme_state"]) == baseline["section_sha256"]["theme_state"]


@pytest.mark.needs_full_checkout("data", "site") if _needs_checkout("data", "site") else pytest.mark.needs_full_checkout()
def test_theme_tracker_nuclear_entry_unchanged() -> None:
    baseline = _read_baseline()
    assert _nuclear_theme_tracker() == baseline["theme_tracker"]
    assert _canonical_sha256(baseline["theme_tracker"]) == baseline["section_sha256"]["theme_tracker"]


@pytest.mark.needs_full_checkout("site") if _needs_checkout("site") else pytest.mark.needs_full_checkout()
def test_public_nuclear_pages_carry_no_private_dossier_canaries() -> None:
    baseline = _read_baseline()
    for path in PUBLIC_PAGE_PATHS:
        assert path.exists(), f"Expected committed public page is absent: {path}"
        content = path.read_text(encoding="utf-8")
        for canary in PRIVATE_DOSSIER_CANARIES:
            assert canary not in content
    assert _canonical_sha256(baseline["public_pages"]) == baseline["section_sha256"]["public_pages"]

def _baseline_document(main_sha: str) -> dict[str, Any]:
    sections = {
        "basket_membership": {
            basket_id: _basket_snapshot(basket_id)
            for basket_id in ("nuclear_power", "uranium_miners")
        },
        "theme_state": _nuclear_theme_state(),
        "theme_tracker": _nuclear_theme_tracker(),
        "public_pages": {"canaries": []},
    }
    return {
        "schema": "energy.nuclear_non_regression.v1",
        "frozen_at_main": main_sha,
        "owners": {
            "basket_membership": {"artifact": "data/baskets/membership.json"},
            "theme_state": {"reader": "engine.neuralweb.thematic_state.compose"},
            "theme_tracker": {"reader": "scripts.build_state_of_themes.compose"},
        },
        **sections,
        "section_sha256": {
            name: _canonical_sha256(value) for name, value in sections.items()
        },
    }


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "--regenerate-baseline":
        raise SystemExit("usage: python3 tests/test_energy_economic_change_non_regression.py --regenerate-baseline <main-sha>")
    document = _baseline_document(sys.argv[2])
    BASELINE_PATH.write_text(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
