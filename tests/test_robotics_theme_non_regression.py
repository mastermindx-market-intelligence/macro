"""Non-regression freeze for the robotics_automation legacy decision outputs and
public-leak guards.

Operation gmi-robotics-fable-ceo-e2e-20260923-chairman-001 (carrier Macro #7908),
lane R3. Mirrors the accepted Energy pattern
(tests/test_energy_economic_change_non_regression.py on #7895): frozen vs shape
projections per section, a canonical sha256 per section, the Theme Tracker read
through scripts/build_state_of_themes.py::compose(REPO_ROOT), the sparse-checkout
skip guard, and a ``--regenerate-baseline <main-sha>`` CLI.

What this freezes (master packet section 3 items 4-5; RBV-28, RBV-31): the Robotics
research vertical must NEVER change basket membership/weights, ThemeState, the Theme
Tracker lane/stage/recommendation shape, entry fields, member ordering shape or Prophet
presence, and must never leak a full-fidelity research payload through public pages,
public JSON or the tracked evidence parquet. The baseline was taken at main
3c93f8194f6c2cb19dad21c1347d8b3b8474aa31 BEFORE any Robotics product code existed.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = REPO_ROOT / "tests/fixtures/robotics_non_regression/robotics_baseline.json"
MEMBERSHIP_PATH = REPO_ROOT / "data/baskets/membership.json"
THEME_STATE_PATH = REPO_ROOT / "data/neuralweb/theme_state.json"
BASKET_CONFLUENCE_PATH = REPO_ROOT / "site/marketdata/basket_confluence.json"
PROPHET_INDEX_PATH = REPO_ROOT / "site/prophet/index.json"
EVIDENCE_PARQUET_PATH = REPO_ROOT / "data/theme_graph/evidence.parquet"
PUBLIC_PAGE_PATHS = (
    REPO_ROOT / "site/state_of_themes.html",
    REPO_ROOT / "site/basket/robotics_automation.html",
)
PUBLIC_JSON_ROOTS = ("site/marketdata", "site/prophet")
BASKET_ID = "robotics_automation"
BASELINE_SCHEMA = "robotics.theme_non_regression.v1"
FROZEN_AT_MAIN = "3c93f8194f6c2cb19dad21c1347d8b3b8474aa31"

MEMBERSHIP_FIELDS = ("ticker", "added", "removed", "curated_added")
# theme_state: ``foresight`` is split — its DECISION sub-fields are frozen as
# ``foresight_decision``; its nightly-moving ``score`` is a shape field
# (``foresight_score``). Across the month before the freeze the foresight object
# changed 8 times on main, every time score-only (review of R3, blocker 1).
FORESIGHT_DECISION_FIELDS = ("stage", "entry_ready", "tier", "bottleneck_band", "source")
THEME_STATE_FROZEN = (
    "theme_id",
    "name_en",
    "name_zh",
    "basket_ids",
    "foresight_decision",
    "narrative",
)
THEME_STATE_SHAPE = (
    "radar",
    "basket_intel",
    "subsector_rotation",
    "divergence_board",
    "subsector_keys",
    "foresight_score",
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
# basket_confluence: identity + the member SET are frozen; the emitted member ORDER is
# sorted by a nightly return column (ret_20d at the freeze), so it is a shape field —
# its type is pinned, its permutation is not (packet escape hatch, see README).
BASKET_CONFLUENCE_FROZEN = (
    "key",
    "kind",
    "label",
    "label_zh",
    "sector",
    "sector_zh",
    "basket_id",
    "chart_key",
)
BASKET_CONFLUENCE_SHAPE = (
    "entry",
    "regime",
    "class",
    "price_level",
    "n_members",
    "n_priced",
    "n_live",
    "reliability",
    "coverage_pct",
    "has_signals",
    "start",
    "as_of",
    "member_order",
)
PROPHET_TOP_LEVEL_KEYS = (
    "schema",
    "asof",
    "recorded_at",
    "source_asof",
    "source_board_asof",
    "source_delayed",
    "source_unknown",
    "source_basis",
    "plans",
)
PROPHET_ROW_TICKER_FIELD = "asset"
PROPHET_FROZEN = ("member_tickers_present",)
# one artifact outside the scan roots that theme_state.foresight.source names
EXTRA_PUBLIC_JSON = ("site/basketdata/foresight_cascade.json",)

# Payload markers only. Shell markup such as a hidden mount element or an
# /api/themes/v1/research URL is allowed and is deliberately NOT a canary.
PUBLIC_PAGE_CANARIES = (
    "gmirca_",
    "theme_graph.curation_assertion.v1",
    "curation_revision",
    "theme_graph_private/",
    "DOCUMENTED_PRODUCT_INCLUSION",
    "PRODUCT_CAPABILITY",
    "ANNOUNCED_DEVELOPMENT_AGREEMENT",
    "REPORTED_OPERATING_MEASURE",
    "NarGo",
    "K-Series frameless",
)
PUBLIC_JSON_CANARIES = (b"gmirca_", b"curation_assertion")
PARQUET_FORBIDDEN_COLUMN = "curation_assertion"

_NO_SKIP = pytest.mark.skipif(False, reason="required checkout directories are present")


# ---------------------------------------------------------------------------
# projections (verbatim from the Energy pattern where they apply)
# ---------------------------------------------------------------------------

def _json_type_name(value: Any) -> str:
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


def _project(value: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: value.get(field) for field in fields}


def _frozen_projection(value: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return _project(value, fields)


def _shape_projection(value: dict[str, Any], fields: tuple[str, ...]) -> dict[str, str]:
    return {field: _json_type_name(value.get(field)) for field in fields}


def _projected_section(
    value: dict[str, Any],
    frozen_fields: tuple[str, ...],
    shape_fields: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "frozen": _frozen_projection(value, frozen_fields),
        "shape": _shape_projection(value, shape_fields),
    }


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _read_baseline() -> dict[str, Any]:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def _load_state_builder() -> Any:
    module_path = REPO_ROOT / "scripts/build_state_of_themes.py"
    spec = importlib.util.spec_from_file_location("build_state_of_themes", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import Theme Tracker builder from {module_path}.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _needs_checkout(*directories: str) -> bool:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from scripts.worktree_sparse import missing_dirs

    return bool(set(directories) & set(missing_dirs(REPO_ROOT)))


# ---------------------------------------------------------------------------
# section readers
# ---------------------------------------------------------------------------

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


def _member_tickers() -> list[str]:
    return sorted(member["ticker"] for member in _basket_snapshot(BASKET_ID)["members"])


def _robotics_theme_state() -> dict[str, Any]:
    document = json.loads(THEME_STATE_PATH.read_text(encoding="utf-8"))
    theme = next(theme for theme in document["themes"] if theme.get("theme_id") == BASKET_ID)
    foresight = theme.get("foresight") or {}
    view = dict(theme)
    view["foresight_decision"] = (
        {field: foresight.get(field) for field in FORESIGHT_DECISION_FIELDS}
        if isinstance(foresight, dict) else None)
    view["foresight_score"] = foresight.get("score") if isinstance(foresight, dict) else None
    return _projected_section(view, THEME_STATE_FROZEN, THEME_STATE_SHAPE)


def _robotics_theme_tracker() -> dict[str, Any]:
    builder = _load_state_builder()
    context = builder.compose(REPO_ROOT)
    theme = next(theme for theme in context["themes"] if theme.get("theme_id") == BASKET_ID)
    projected = _projected_section(theme, THEME_TRACKER_FROZEN, THEME_TRACKER_SHAPE)
    return json.loads(json.dumps(projected))


def _robotics_basket_confluence() -> dict[str, Any]:
    document = json.loads(BASKET_CONFLUENCE_PATH.read_text(encoding="utf-8"))
    entry = next(row for row in document["baskets"] if row.get("basket_id") == BASKET_ID)
    members = entry.get("members") or []
    view = dict(entry)
    view["member_order"] = [member.get("ticker") for member in members]
    projected = _projected_section(view, BASKET_CONFLUENCE_FROZEN, BASKET_CONFLUENCE_SHAPE)
    # the member SET is a decision output (membership) and is frozen; the ORDER is not
    projected["frozen"]["member_tickers_sorted"] = sorted(view["member_order"])
    return projected


def _robotics_prophet_presence() -> dict[str, Any]:
    document = json.loads(PROPHET_INDEX_PATH.read_text(encoding="utf-8"))
    members = set(_member_tickers())
    rows = [
        row for row in document.get("plans", [])
        if isinstance(row, dict) and str(row.get(PROPHET_ROW_TICKER_FIELD)) in members
    ]
    row_shape: dict[str, str] = {}
    for row in rows:
        for key in sorted(row):
            type_name = _json_type_name(row.get(key))
            row_shape[key] = type_name if key not in row_shape or row_shape[key] == type_name else "mixed"
    present = sorted({str(row.get(PROPHET_ROW_TICKER_FIELD)) for row in rows})
    frozen = {"member_tickers_present": present}
    return {
        "structure_checked": {
            "top_level_keys_present": [key for key in PROPHET_TOP_LEVEL_KEYS if key in document],
            "top_level_keys": sorted(document.keys()),
            "rows_container": "plans",
            "row_ticker_field": PROPHET_ROW_TICKER_FIELD,
        },
        "frozen": {field: frozen[field] for field in PROPHET_FROZEN},
        "shape": {"row_fields": row_shape},
    }


def _public_json_files() -> list[Path]:
    files: list[Path] = []
    for root in PUBLIC_JSON_ROOTS:
        files.extend(sorted((REPO_ROOT / root).rglob("*.json")))
    files.extend(sorted((REPO_ROOT / "site").glob("*.json")))
    files.extend(REPO_ROOT / extra for extra in EXTRA_PUBLIC_JSON if (REPO_ROOT / extra).exists())
    return files


def _public_pages_section() -> dict[str, Any]:
    return {
        "pages": [str(path.relative_to(REPO_ROOT)) for path in PUBLIC_PAGE_PATHS],
        "canaries": list(PUBLIC_PAGE_CANARIES),
        "json_roots": list(PUBLIC_JSON_ROOTS) + ["site/*.json"] + list(EXTRA_PUBLIC_JSON),
        "json_canaries": [token.decode() for token in PUBLIC_JSON_CANARIES],
    }


def _evidence_parquet_section() -> dict[str, Any]:
    return {
        "path": str(EVIDENCE_PARQUET_PATH.relative_to(REPO_ROOT)),
        "forbidden_column": PARQUET_FORBIDDEN_COLUMN,
        "rule": "column absent, or every cell null",
    }


# ---------------------------------------------------------------------------
# tests — one per section, comparing the live projection AND its sha256
# ---------------------------------------------------------------------------

def test_baseline_frozen_at_main_sha_is_pinned() -> None:
    baseline = _read_baseline()
    assert baseline["schema"] == BASELINE_SCHEMA
    assert baseline["frozen_at_main"] == FROZEN_AT_MAIN


@pytest.mark.needs_full_checkout("data") if _needs_checkout("data") else _NO_SKIP
def test_robotics_automation_membership_unchanged_vs_frozen_baseline() -> None:
    baseline = _read_baseline()
    assert _basket_snapshot(BASKET_ID) == baseline["basket_membership"][BASKET_ID]
    assert set(baseline["basket_membership"]) == {BASKET_ID}, "cn_robotics is a different surface"
    assert (
        _canonical_sha256(baseline["basket_membership"])
        == baseline["section_sha256"]["basket_membership"]
    )


def test_frozen_field_lists_exclude_nightly_volatile_fields() -> None:
    nightly_volatile_fields = (
        "radar",
        "basket_intel",
        "subsector_rotation",
        "divergence_board",
        "lane",
        "lane_rank",
        "fav_count",
        "caut_count",
        "present_count",
        "stage_key",
        "stage_sort",
        "falsifier_any_fired",
        "filter_flags",
        "entry",
        "regime",
        "price_level",
        "as_of",
        "member_order",
        "foresight",
        "foresight_score",
        "score",
        "row_fields",
    )
    for field in nightly_volatile_fields:
        assert field not in THEME_STATE_FROZEN
        assert field not in THEME_TRACKER_FROZEN
        assert field not in BASKET_CONFLUENCE_FROZEN
        assert field not in PROPHET_FROZEN
        assert field not in FORESIGHT_DECISION_FIELDS
    assert PROPHET_FROZEN == ("member_tickers_present",)


@pytest.mark.needs_full_checkout("data") if _needs_checkout("data") else _NO_SKIP
def test_theme_state_fields_for_robotics_unchanged() -> None:
    baseline = _read_baseline()
    assert _robotics_theme_state() == baseline["theme_state"]
    assert _canonical_sha256(baseline["theme_state"]) == baseline["section_sha256"]["theme_state"]


@pytest.mark.needs_full_checkout("data", "site") if _needs_checkout("data", "site") else _NO_SKIP
def test_theme_tracker_robotics_entry_unchanged() -> None:
    baseline = _read_baseline()
    assert _robotics_theme_tracker() == baseline["theme_tracker"]
    assert _canonical_sha256(baseline["theme_tracker"]) == baseline["section_sha256"]["theme_tracker"]


@pytest.mark.needs_full_checkout("site") if _needs_checkout("site") else _NO_SKIP
def test_basket_confluence_robotics_entry_unchanged() -> None:
    baseline = _read_baseline()
    assert _robotics_basket_confluence() == baseline["basket_confluence"]
    assert (
        _canonical_sha256(baseline["basket_confluence"])
        == baseline["section_sha256"]["basket_confluence"]
    )


@pytest.mark.needs_full_checkout("data", "site") if _needs_checkout("data", "site") else _NO_SKIP
def test_prophet_presence_of_robotics_members_unchanged() -> None:
    baseline = _read_baseline()
    assert _robotics_prophet_presence() == baseline["prophet_presence"]
    assert (
        _canonical_sha256(baseline["prophet_presence"])
        == baseline["section_sha256"]["prophet_presence"]
    )


@pytest.mark.needs_full_checkout("site") if _needs_checkout("site") else _NO_SKIP
def test_public_pages_carry_no_payload_canaries() -> None:
    baseline = _read_baseline()
    assert baseline["public_pages"] == _public_pages_section()
    assert _canonical_sha256(baseline["public_pages"]) == baseline["section_sha256"]["public_pages"]
    for path in PUBLIC_PAGE_PATHS:
        assert path.exists(), f"Expected committed public page is absent: {path}"
        content = path.read_text(encoding="utf-8")
        for canary in PUBLIC_PAGE_CANARIES:
            assert canary not in content, f"{canary!r} leaked into {path.relative_to(REPO_ROOT)}"
    files = _public_json_files()
    assert files, "no public JSON files found to scan"
    for path in files:
        blob = path.read_bytes()
        for token in PUBLIC_JSON_CANARIES:
            assert token not in blob, f"{token!r} leaked into {path.relative_to(REPO_ROOT)}"


@pytest.mark.needs_full_checkout("data") if _needs_checkout("data") else _NO_SKIP
def test_evidence_parquet_has_no_live_assertion_cells() -> None:
    pandas = pytest.importorskip("pandas")
    baseline = _read_baseline()
    assert baseline["evidence_parquet"] == _evidence_parquet_section()
    assert (
        _canonical_sha256(baseline["evidence_parquet"])
        == baseline["section_sha256"]["evidence_parquet"]
    )
    frame = pandas.read_parquet(EVIDENCE_PARQUET_PATH)
    if PARQUET_FORBIDDEN_COLUMN in frame.columns:
        assert frame[PARQUET_FORBIDDEN_COLUMN].isna().all(), (
            "tracked evidence parquet carries live curation_assertion cells"
        )


# ---------------------------------------------------------------------------
# baseline regeneration
# ---------------------------------------------------------------------------

def _baseline_document(main_sha: str) -> dict[str, Any]:
    sections = {
        "basket_membership": {BASKET_ID: _basket_snapshot(BASKET_ID)},
        "theme_state": _robotics_theme_state(),
        "theme_tracker": _robotics_theme_tracker(),
        "basket_confluence": _robotics_basket_confluence(),
        "prophet_presence": _robotics_prophet_presence(),
        "public_pages": _public_pages_section(),
        "evidence_parquet": _evidence_parquet_section(),
    }
    return {
        "schema": BASELINE_SCHEMA,
        "frozen_at_main": main_sha,
        "owners": {
            "basket_membership": {"artifact": "data/baskets/membership.json"},
            "theme_state": {"artifact": "data/neuralweb/theme_state.json"},
            "theme_tracker": {"reader": "scripts.build_state_of_themes.compose"},
            "basket_confluence": {"artifact": "site/marketdata/basket_confluence.json"},
            "prophet_presence": {"artifact": "site/prophet/index.json"},
            "public_pages": {"artifacts": [str(p.relative_to(REPO_ROOT)) for p in PUBLIC_PAGE_PATHS]},
            "evidence_parquet": {"artifact": "data/theme_graph/evidence.parquet"},
        },
        **sections,
        "section_sha256": {name: _canonical_sha256(value) for name, value in sections.items()},
    }


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "--regenerate-baseline":
        raise SystemExit(
            "usage: python3 tests/test_robotics_theme_non_regression.py --regenerate-baseline <main-sha>"
        )
    document = _baseline_document(sys.argv[2])
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
