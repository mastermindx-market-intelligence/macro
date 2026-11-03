"""FIF A0: the reviewed API unit selects the production dataset mode.

The flip lives in the repo-managed ``app/deploy/macro-api.service`` fragment so
it deploys through update.sh's reviewed-unit install and is rolled back by a
revert. These tests pin the exact line and keep it a lawful mode that the API
selector accepts.
"""
from __future__ import annotations

from pathlib import Path

import app.forensics as forensics_api

ROOT = Path(__file__).resolve().parents[1]
UNIT = ROOT / "app" / "deploy" / "macro-api.service"
MODE_LINE = "Environment=FIF_FINANCIAL_DATASET_MODE=production"


def _unit_lines() -> list[str]:
    return [line.strip() for line in UNIT.read_text(encoding="utf-8").splitlines()]


def test_macro_api_unit_sets_production_dataset_mode_exactly_once() -> None:
    lines = _unit_lines()
    assert lines.count(MODE_LINE) == 1
    service_idx = lines.index("[Service]")
    mode_idx = lines.index(MODE_LINE)
    next_section_idx = next(
        (i for i in range(service_idx + 1, len(lines)) if lines[i].startswith("[")),
        len(lines),
    )
    assert service_idx < mode_idx < next_section_idx
    for line in lines:
        if line.startswith("#") or forensics_api.FIF_FINANCIAL_DATASET_MODE_ENV not in line:
            continue
        assert line == MODE_LINE


def test_unit_mode_value_is_accepted_by_the_api_selector(monkeypatch) -> None:
    value = MODE_LINE.split("=", 2)[2]
    monkeypatch.setenv(forensics_api.FIF_FINANCIAL_DATASET_MODE_ENV, value)
    assert forensics_api._financial_dataset_mode() == "production"


def test_unit_never_points_the_production_store_at_a_local_directory() -> None:
    # The store must resolve from the private research-store family on the
    # host, never from a fixture or scratch directory baked into the unit.
    for line in _unit_lines():
        if line.startswith("#"):
            continue
        assert "FIF_PRODUCTION_DATASET_LOCAL_STORE" not in line
        assert "RESEARCH_LOCAL_STORE" not in line
