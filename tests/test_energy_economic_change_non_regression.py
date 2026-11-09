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
    "divergence_board",
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


def _shape_projection(value: dict[str, Any], fields: tuple[str, ...]) -> dict[str, str]:
    """Concrete JSON shape of every SHAPE field: null/bool/number/string/array/object, or "missing"."""
    shapes: dict[str, str] = {}
    for field in fields:
        live = value.get(field, _MISSING)
        shapes[field] = "missing" if live is _MISSING else _json_type_name(live)
    return shapes


def _shape_mismatches(
    live_shapes: dict[str, str], baseline_shapes: dict[str, str], fields: tuple[str, ...]
) -> list[str]:
    """Nullable law (R-ENE-08 repair-2): a field whose live shape equals its baseline shape is
    unchanged; a field in NULLABLE_SHAPE_FIELDS additionally tolerates a live ``null`` and a
    baseline ``null`` (the nightly may omit the block, and a dead reader may come back).
    Every other difference is a shape change."""
    mismatches: list[str] = []
    for field in fields:
        live = live_shapes.get(field, "missing")
        base = baseline_shapes.get(field, "missing")
        if live == base:
            continue
        if field in NULLABLE_SHAPE_FIELDS and "null" in (live, base):
            continue
        mismatches.append(f"{field}: live {live!r} vs baseline {base!r}")
    return mismatches


def _projected_section(
    value: dict[str, Any],
    frozen_fields: tuple[str, ...],
    shape_fields: tuple[str, ...],
) -> dict[str, Any]:
    projected = {
        "frozen": _frozen_projection(value, frozen_fields),
        "shape": _shape_projection(json.loads(json.dumps(value)), shape_fields),
    }
    return json.loads(json.dumps(projected))


def _nuclear_theme_state() -> dict[str, Any]:
    document = json.loads(THEME_STATE_PATH.read_text(encoding="utf-8"))
    theme = next(
        theme for theme in document["themes"] if theme.get("theme_id") == "nuclear_power"
    )
    return _projected_section(theme, THEME_STATE_FROZEN, THEME_STATE_SHAPE)


def _nuclear_theme_tracker() -> dict[str, Any]:
    builder = _load_state_builder()
    context = builder.compose(REPO_ROOT)
    theme = next(
        theme for theme in context["themes"] if theme.get("theme_id") == "nuclear_power"
    )
    return _projected_section(theme, THEME_TRACKER_FROZEN, THEME_TRACKER_SHAPE)


def _read_baseline() -> dict[str, Any]:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def _assert_projected_section_unchanged(
    live_section: dict[str, Any],
    baseline: dict[str, Any],
    section_name: str,
    shape_fields: tuple[str, ...],
) -> None:
    """Frozen fields exact; shape fields compatible under the nullable law."""
    expected = baseline[section_name]
    assert live_section["frozen"] == expected["frozen"]
    mismatches = _shape_mismatches(live_section["shape"], expected["shape"], shape_fields)
    assert not mismatches, f"{section_name} shape changed: " + "; ".join(mismatches)


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


def _is_ancestor_of_origin_main(sha: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", sha, "origin/main"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _missing_checkout_directories() -> tuple[str, ...]:
    from scripts.worktree_sparse import missing_dirs

    return tuple(missing_dirs(REPO_ROOT))


def _validate_regeneration_preconditions(main_sha: str) -> None:
    head_sha = _git_head()
    if head_sha != main_sha:
        raise SystemExit(
            f"Regeneration requires the requested main SHA to be HEAD; HEAD is {head_sha}."
        )
    if not _is_ancestor_of_origin_main(main_sha):
        raise SystemExit(
            f"Regeneration requires a SHA that is an ancestor of origin/main; {main_sha} is not "
            "(a lane merge commit is never the frozen main)."
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


@pytest.mark.needs_full_checkout("data") if _needs_checkout("data") else _NO_SKIP
def test_nuclear_power_membership_unchanged_vs_frozen_baseline() -> None:
    baseline = _read_baseline()
    assert _basket_snapshot("nuclear_power") == baseline["basket_membership"]["nuclear_power"]


@pytest.mark.needs_full_checkout("data") if _needs_checkout("data") else _NO_SKIP
def test_uranium_miners_membership_unchanged_vs_frozen_baseline() -> None:
    baseline = _read_baseline()
    assert _basket_snapshot("uranium_miners") == baseline["basket_membership"]["uranium_miners"]
    assert _basket_membership_section() == baseline["basket_membership"]


@pytest.mark.needs_full_checkout("data") if _needs_checkout("data") else _NO_SKIP
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
        "radar", "basket_intel", "foresight", "narrative", "subsector_rotation", "divergence_board",
        "lane", "lane_rank", "stance_en", "stance_zh", "story_en", "story_zh",
        "fav_count", "caut_count", "present_count",
        "stage_raw", "stage_key", "stage_label_en", "stage_label_zh", "stage_sort",
        "falsifier_any_fired", "falsifier_label", "filter_flags",
        "leadership_context", "entry_context",
    )
    assert len(nightly_volatile_fields) == 25
    for field in nightly_volatile_fields:
        assert field not in THEME_STATE_FROZEN
        assert field not in THEME_TRACKER_FROZEN


def test_json_type_name_uses_json_shapes() -> None:
    assert _json_type_name(json.loads(json.dumps((1, 2)))) == "array"


def test_nullable_shape_law_against_committed_baseline_shapes() -> None:
    baseline = _read_baseline()
    state_shapes = baseline["theme_state"]["shape"]
    tracker_shapes = baseline["theme_tracker"]["shape"]
    # a nullable block the nightly omitted tonight
    assert _shape_mismatches({**state_shapes, "radar": "null"}, state_shapes, THEME_STATE_SHAPE) == []
    assert _shape_mismatches({**state_shapes, "basket_intel": "null"}, state_shapes, THEME_STATE_SHAPE) == []
    assert _shape_mismatches({**state_shapes, "foresight": "null"}, state_shapes, THEME_STATE_SHAPE) == []
    # a dead reader coming back: baseline null, live object
    assert state_shapes["narrative"] == "null"
    assert _shape_mismatches({**state_shapes, "narrative": "object"}, state_shapes, THEME_STATE_SHAPE) == []
    # nuclear first entering the hidden-opportunity state: divergence_board null -> object
    assert state_shapes["divergence_board"] == "null"
    assert _shape_mismatches({**state_shapes, "divergence_board": "object"}, state_shapes, THEME_STATE_SHAPE) == []
    assert tracker_shapes["leadership_context"] == "null"
    assert _shape_mismatches({**tracker_shapes, "leadership_context": "object", "entry_context": "string"}, tracker_shapes, THEME_TRACKER_SHAPE) == []
    # a non-nullable field going null IS a change
    assert _shape_mismatches({**tracker_shapes, "lane": "null"}, tracker_shapes, THEME_TRACKER_SHAPE) == ["lane: live 'null' vs baseline 'string'"]
    assert _shape_mismatches({**tracker_shapes, "stance_en": "null"}, tracker_shapes, THEME_TRACKER_SHAPE) != []
    # a type flip on a nullable field that is not a null IS a change
    assert _shape_mismatches({**state_shapes, "radar": "object"}, state_shapes, THEME_STATE_SHAPE) == ["radar: live 'object' vs baseline 'array'"]
    # the assertion helper reports the same verdicts end to end
    _assert_projected_section_unchanged(
        {"frozen": baseline["theme_state"]["frozen"], "shape": {**state_shapes, "radar": "null", "narrative": "object"}},
        baseline, "theme_state", THEME_STATE_SHAPE,
    )
    with pytest.raises(AssertionError, match="lane: live 'null'"):
        _assert_projected_section_unchanged(
            {"frozen": baseline["theme_tracker"]["frozen"], "shape": {**tracker_shapes, "lane": "null"}},
            baseline, "theme_tracker", THEME_TRACKER_SHAPE,
        )


def test_live_null_in_a_non_nullable_shape_field_is_recorded_as_null() -> None:
    assert _shape_projection({"lane": None}, ("lane",)) == {"lane": "null"}
    assert _shape_projection({}, ("lane",)) == {"lane": "missing"}


def test_baseline_sections_match_their_recorded_sha256() -> None:
    baseline = _read_baseline()
    for section_name, digest in baseline["section_sha256"].items():
        assert _canonical_sha256(baseline[section_name]) == digest, section_name


def test_regeneration_rejects_sha_that_is_not_on_origin_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(__name__ + "._git_head", lambda: "lane-head")
    monkeypatch.setattr(__name__ + "._missing_checkout_directories", lambda: ())
    monkeypatch.setattr(__name__ + "._is_ancestor_of_origin_main", lambda sha: False)
    with pytest.raises(SystemExit, match="ancestor of origin/main"):
        _validate_regeneration_preconditions("lane-head")


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
    monkeypatch.setattr(__name__ + "._is_ancestor_of_origin_main", lambda sha: True)
    monkeypatch.setattr(
        __name__ + "._missing_checkout_directories", lambda: ("data", "site")
    )
    with pytest.raises(SystemExit, match="missing directories: data, site"):
        _validate_regeneration_preconditions("requested-head")


@pytest.mark.needs_full_checkout("data") if _needs_checkout("data") else _NO_SKIP
def test_theme_state_fields_for_nuclear_unchanged() -> None:
    baseline = _read_baseline()
    _assert_projected_section_unchanged(_nuclear_theme_state(), baseline, "theme_state", THEME_STATE_SHAPE)


@pytest.mark.needs_full_checkout("data", "site") if _needs_checkout("data", "site") else _NO_SKIP
def test_theme_tracker_nuclear_entry_unchanged() -> None:
    baseline = _read_baseline()
    _assert_projected_section_unchanged(_nuclear_theme_tracker(), baseline, "theme_tracker", THEME_TRACKER_SHAPE)


@pytest.mark.needs_full_checkout("site") if _needs_checkout("site") else _NO_SKIP
def test_public_nuclear_pages_carry_no_private_dossier_canaries() -> None:
    baseline = _read_baseline()
    assert tuple(baseline["public_pages"]["canaries"]) == PRIVATE_DOSSIER_CANARIES
    for path in PUBLIC_PAGE_PATHS:
        assert path.exists(), f"Expected committed public page is absent: {path}"
        content = path.read_text(encoding="utf-8")
        for canary in PRIVATE_DOSSIER_CANARIES:
            assert canary not in content

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
