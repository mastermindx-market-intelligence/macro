"""D03 T43: malformed live source dates must publish the honest warm state.

The design-fixture path intentionally bypasses freshness. These regressions use
the normal data/top_maturation/latest.json path, including build() and main(),
so a date-parser exception cannot leave the previously published board in place.
"""
from __future__ import annotations

import datetime
import json
from html import unescape
from pathlib import Path

import pytest

from scripts import build_winner_health_page as bwh


REPO = Path(__file__).resolve().parent.parent
_REAL_DATE = datetime.date
_TODAY = _REAL_DATE(2026, 11, 4)
INVALID_DATES = (
    "2026-99-01",
    "2026-00-10",
    "2026-02-30",
    "2025-02-29",
    "2100-02-29",
    "2026-01-00",
    "0000-01-01",
)


@pytest.fixture(autouse=True)
def fixed_calendar_day(monkeypatch):
    """Keep calendar-boundary cases deterministic across midnight and hosts."""
    class FixedDate(_REAL_DATE):
        @classmethod
        def today(cls):
            return cls(_TODAY.year, _TODAY.month, _TODAY.day)

    monkeypatch.setattr(datetime, "date", FixedDate)


def _live_artifact(data_dir: Path, payload: object) -> Path:
    path = data_dir / "top_maturation" / "latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _isolated_root(tmp_path: Path, monkeypatch, asof: str) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "templates").symlink_to(REPO / "templates", target_is_directory=True)
    monkeypatch.setattr(bwh, "_data_dir", lambda r: r / "data")
    _live_artifact(root / "data", {"asof": asof})
    # A failed build used to leave this previous board unmodified.
    previous = root / "site" / "winner_health.html"
    previous.parent.mkdir()
    previous.write_text("PREVIOUS_BOARD_MUST_NOT_SURVIVE", encoding="utf-8")
    return root


@pytest.mark.parametrize("asof", INVALID_DATES)
def test_impossible_calendar_dates_are_unusable(asof):
    assert bwh._is_stale({"asof": asof}) is True


@pytest.mark.parametrize("asof", [None, "", "not-a-date", 20261104, [], {}])
def test_malformed_date_shapes_remain_unusable(asof):
    assert bwh._is_stale({"asof": asof}) is True


def test_missing_date_remains_unusable():
    assert bwh._is_stale({}) is True


@pytest.mark.parametrize("age, stale", [(0, False), (1, False), (5, False),
                                        (6, False), (7, True), (30, True)])
def test_existing_six_calendar_day_cutoff_is_unchanged(age, stale):
    asof = (_TODAY - datetime.timedelta(days=age)).isoformat()
    assert bwh._is_stale({"asof": asof}) is stale


def test_timestamp_prefix_keeps_existing_date_semantics():
    assert bwh._is_stale({"asof": "2026-10-29T23:59:59Z"}) is False
    assert bwh._is_stale({"asof": "2026-10-28T23:59:59Z"}) is True


def test_valid_leap_day_is_parsed_then_judged_by_age():
    assert bwh._is_stale({"asof": "2024-02-29"}) is True


@pytest.mark.parametrize("asof", ["2026-99-01", "2026-02-30", "2025-02-29"])
def test_live_loader_returns_warm_context_for_impossible_dates(tmp_path, asof):
    _live_artifact(tmp_path, {"asof": asof})
    assert bwh._load_context(tmp_path) is None


@pytest.mark.parametrize("age, accepted", [(6, True), (7, False)])
def test_live_loader_preserves_freshness_boundary(tmp_path, age, accepted):
    payload = {"asof": (_TODAY - datetime.timedelta(days=age)).isoformat(),
               "source_marker": "unchanged"}
    _live_artifact(tmp_path, payload)
    assert bwh._load_context(tmp_path) == (payload if accepted else None)


@pytest.mark.parametrize("asof", ["2026-99-01", "2026-02-30", "2025-02-29"])
def test_live_build_publishes_warm_page_instead_of_leaving_old_board(
    tmp_path, monkeypatch, asof
):
    root = _isolated_root(tmp_path, monkeypatch, asof)
    out = bwh.build(root)
    assert out == root / "site" / "winner_health.html"
    html = out.read_text(encoding="utf-8")
    assert "Tonight's read has not landed yet" in unescape(html)
    assert "今晚的判读尚未生成" in html
    assert "PREVIOUS_BOARD_MUST_NOT_SURVIVE" not in html
    assert asof not in html


@pytest.mark.parametrize("asof", ["2026-99-01", "2026-02-30", "2025-02-29"])
def test_live_cli_succeeds_when_warm_page_was_written(
    tmp_path, monkeypatch, capsys, asof
):
    root = _isolated_root(tmp_path, monkeypatch, asof)
    assert bwh.main(["--root", str(root)]) == 0
    html = (root / "site" / "winner_health.html").read_text(encoding="utf-8")
    assert "Tonight's read has not landed yet" in unescape(html)
    assert "PREVIOUS_BOARD_MUST_NOT_SURVIVE" not in html
    assert "render failed" not in capsys.readouterr().out


def test_explicit_fixture_still_bypasses_live_freshness_policy(tmp_path):
    payload = {"asof": "2000-01-01", "source_marker": "historical design fixture"}
    path = _live_artifact(tmp_path, payload)
    assert bwh._load_context(tmp_path, fixture=path) == payload
