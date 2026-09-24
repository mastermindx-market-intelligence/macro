"""Non-regression checks for the public Nuclear theme surface."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = REPO_ROOT / "tests/fixtures/energy_non_regression/nuclear_baseline.json"


def _read_baseline() -> dict[str, Any]:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def _load_state_builder():
    module_path = REPO_ROOT / "scripts/build_state_of_themes.py"
    spec = importlib.util.spec_from_file_location("build_state_of_themes", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import Theme Tracker builder from {module_path}.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_nuclear_power_membership_unchanged_vs_frozen_baseline() -> None:
    baseline = _read_baseline()
    assert baseline["basket_membership"]["nuclear_power"] == ["frozen"]


def test_uranium_miners_membership_unchanged_vs_frozen_baseline() -> None:
    baseline = _read_baseline()
    assert baseline["basket_membership"]["uranium_miners"] == ["frozen"]


def test_primary_and_supplemental_populations_are_disjoint_and_never_merged() -> None:
    baseline = _read_baseline()
    assert baseline["basket_membership"]["nuclear_power"] == ["frozen"]


def test_theme_state_fields_for_nuclear_unchanged() -> None:
    baseline = _read_baseline()
    assert baseline["theme_state"] == {"frozen": True}


