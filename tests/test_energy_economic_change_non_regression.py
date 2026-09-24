"""Non-regression checks for the public Nuclear theme surface."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import subprocess
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
THEME_STATE_FROZEN = (
    "theme_id",
    "name_en",
    "name_zh",
    "basket_ids",
    "subsector_keys",
)
THEME_STATE_SHAPE = (
    "radar",
    "basket_intel",
    "foresight",
    "narrative",
    "subsector_rotation",
    "divergence_board",
)
THEME_TRACKER_FROZEN = (
    "theme_id",
    "name_en",
    "name_zh",
)
THEME_TRACKER_SHAPE = (
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
NULLABLE_SHAPE_FIELDS = (
    "radar",
    "basket_intel",
    "narrative",
    "foresight",
    "leadership_context",
    "entry_context",
    "falsifier_label",
    "stage_raw",
    "stage_key",
    "stage_label_en",
    "stage_label_zh",
    "stage_sort",
)
_MISSING = object()
THEME_TRACKER_FIELDS = THEME_TRACKER_FROZEN + THEME_TRACKER_SHAPE
_NO_SKIP = pytest.mark.skipif(False, reason="required checkout directories are present")


PRIVATE_DOSSIER_CANARIES = (
    "economic_change_dossier",
    "economic_change_dossier/v1",
    "Nuclear Value Capture",
    "contingent_within_leu",
    "Westinghouse displayed revenue",
    "PRE_EVENT_TIMESTAMPED_VALUE",
)


def _json_type_name(value: Any) -> str:
    value = json.loads(json.dumps(value))
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _frozen_projection(
    value: dict[str, Any], fields: tuple[str, ...]
) -> dict[str, Any]:
    return _project(value, fields)


def _shape_projection(
    value: dict[str, Any],
    fields: tuple[str, ...],
    baseline_shapes: dict[str, str] | None = None,
) -> dict[str, str]:
    nullable_from_baseline = (
        {
            field
            for field in fields
        if field in NULLABLE_SHAPE_FIELDS
        and baseline_shapes.get(field) == "null"
        }
        if baseline_shapes is not None
        else set()
    )
    shapes: dict[str, str] = {}
    for field in fields:
        if field in nullable_from_baseline:
            continue
        shape = _nullable_json_type_name(
            value.get(field, _MISSING), field, nullable_from_baseline
        )
        if shape is not None:
            shapes[field] = shape
    return shapes


def _nullable_json_type_name(
    value: Any, field_name: str, nullable_from_baseline: set[str]
) -> str | None:
    if value is _MISSING:
        return "missing"
    if value is None:
        return (
            None
            if field_name in NULLABLE_SHAPE_FIELDS or field_name in nullable_from_baseline
            else "null"
        )
    return _json_type_name(value)


def _projected_section(
    value: dict[str, Any],
    frozen_fields: tuple[str, ...],
    shape_fields: tuple[str, ...],
    baseline_shapes: dict[str, str] | None = None,
) -> dict[str, Any]:
    projected = {
        "frozen": _frozen_projection(value, frozen_fields),
        "shape": _shape_projection(value, shape_fields, baseline_shapes),
    }
    return json.loads(json.dumps(projected))


def _nuclear_theme_state() -> dict[str, Any]:
    document = json.loads(THEME_STATE_PATH.read_text(encoding="utf-8"))
    theme = next(
        theme for theme in document["themes"] if theme.get("theme_id") == "nuclear_power"
    )
    baseline = _read_baseline()
    return _projected_section(
        theme,
        THEME_STATE_FROZEN,
        THEME_STATE_SHAPE,
        baseline["theme_state"]["shape"],
    )


def _nuclear_theme_tracker() -> dict[str, Any]:
    builder = _load_state_builder()
    context = builder.compose(REPO_ROOT)
    theme = next(
        theme for theme in context["themes"] if theme.get("theme_id") == "nuclear_power"
    )
    baseline = _read_baseline()
    projected = _projected_section(
        theme,
        THEME_TRACKER_FROZEN,
        THEME_TRACKER_SHAPE,
        baseline["theme_tracker"]["shape"],
    )
    return json.loads(json.dumps(projected))


def _read_baseline() -> dict[str, Any]:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def _assert_section_unchanged(
    live_value: Any, baseline: dict[str, Any], section_name: str
) -> None:
    assert live_value == baseline[section_name]
    assert _canonical_sha256(live_value) == baseline["section_sha256"][section_name]


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


def _git_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _missing_checkout_directories() -> tuple[str, ...]:
    from scripts.worktree_sparse import missing_dirs

    return tuple(missing_dirs(REPO_ROOT))


def _validate_regeneration_preconditions(main_sha: str) -> None:
    head_sha = _git_head()
    if head_sha != main_sha:
        raise SystemExit(
            f"Regeneration requires the requested main SHA to be HEAD; HEAD is {head_sha}."
        )
    missing_directories = _missing_checkout_directories()
    if missing_directories:
        raise SystemExit(
            "Regeneration requires a full checkout; missing directories: "
            + ", ".join(missing_directories)
        )


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


def _basket_membership_section() -> dict[str, Any]:
    return {
        basket_id: _basket_snapshot(basket_id)
        for basket_id in ("nuclear_power", "uranium_miners")
    }


def test_nuclear_power_membership_unchanged_vs_frozen_baseline() -> None:
    baseline = _read_baseline()
    _assert_section_unchanged(_basket_membership_section(), baseline, "basket_membership")


def test_uranium_miners_membership_unchanged_vs_frozen_baseline() -> None:
    baseline = _read_baseline()
    _assert_section_unchanged(_basket_membership_section(), baseline, "basket_membership")


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


def test_frozen_field_lists_exclude_nightly_volatile_fields() -> None:
    nightly_volatile_fields = (
        "radar",
        "basket_intel",
        "lane",
        "lane_rank",
        "fav_count",
        "caut_count",
        "present_count",
        "stage_key",
        "stage_raw",
        "stage_label_en",
        "stage_label_zh",
        "stage_sort",
        "falsifier_label",
        "falsifier_any_fired",
        "filter_flags",
        "leadership_context",
        "entry_context",
    )
    for field in nightly_volatile_fields:
        assert field not in THEME_STATE_FROZEN
        assert field not in THEME_TRACKER_FROZEN


def test_json_type_name_uses_json_shapes() -> None:
    assert _json_type_name(json.loads(json.dumps((1, 2)))) == "array"


def test_nullable_shape_allows_live_null_and_declared_baseline_null() -> None:
    nullable_baseline = {field: None for field in NULLABLE_SHAPE_FIELDS}
    nullable_live = {field: None for field in NULLABLE_SHAPE_FIELDS}
    baseline_shapes = {field: "null" for field in NULLABLE_SHAPE_FIELDS}
    assert (
        _shape_projection(nullable_live, NULLABLE_SHAPE_FIELDS, baseline_shapes) == {}
    )
    assert _shape_projection(nullable_baseline, NULLABLE_SHAPE_FIELDS) == {}

    for field in NULLABLE_SHAPE_FIELDS:
        live_value = {field: {"joined": True}}
        assert _shape_projection(live_value, (field,), baseline_shapes) == {}


def test_non_nullable_shape_rejects_baseline_null() -> None:
    assert _shape_projection({"lane": None}, ("lane",)) == {"lane": "null"}


def test_regeneration_rejects_requested_sha_that_is_not_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(__name__ + "._git_head", lambda: "actual-head")
    with pytest.raises(SystemExit, match="requested main SHA to be HEAD"):
        _validate_regeneration_preconditions("requested-head")


def test_regeneration_rejects_sparse_checkout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(__name__ + "._git_head", lambda: "requested-head")
    monkeypatch.setattr(
        __name__ + "._missing_checkout_directories", lambda: ("data", "site")
    )
    with pytest.raises(SystemExit, match="missing directories: data, site"):
        _validate_regeneration_preconditions("requested-head")


@pytest.mark.needs_full_checkout("data") if _needs_checkout("data") else _NO_SKIP
def test_theme_state_fields_for_nuclear_unchanged() -> None:
    baseline = _read_baseline()
    _assert_section_unchanged(_nuclear_theme_state(), baseline, "theme_state")


@pytest.mark.needs_full_checkout("data", "site") if _needs_checkout("data", "site") else _NO_SKIP
def test_theme_tracker_nuclear_entry_unchanged() -> None:
    baseline = _read_baseline()
    _assert_section_unchanged(_nuclear_theme_tracker(), baseline, "theme_tracker")


@pytest.mark.needs_full_checkout("site") if _needs_checkout("site") else _NO_SKIP
def test_public_nuclear_pages_carry_no_private_dossier_canaries() -> None:
    baseline = _read_baseline()
    assert tuple(baseline["public_pages"]["canaries"]) == PRIVATE_DOSSIER_CANARIES
    for path in PUBLIC_PAGE_PATHS:
        assert path.exists(), f"Expected committed public page is absent: {path}"
        content = path.read_text(encoding="utf-8")
        for canary in PRIVATE_DOSSIER_CANARIES:
            assert canary not in content
    _assert_section_unchanged(baseline["public_pages"], baseline, "public_pages")

def _baseline_document(main_sha: str) -> dict[str, Any]:
    sections = {
        "basket_membership": _basket_membership_section(),
        "theme_state": _nuclear_theme_state(),
        "theme_tracker": _nuclear_theme_tracker(),
        "public_pages": {"canaries": list(PRIVATE_DOSSIER_CANARIES)},
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
    main_sha = sys.argv[2]
    _validate_regeneration_preconditions(main_sha)
    document = _baseline_document(main_sha)
    BASELINE_PATH.write_text(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
