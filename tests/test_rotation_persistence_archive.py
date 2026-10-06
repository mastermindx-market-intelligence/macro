from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from scripts.research.rotation_persistence.archive import load_basket_archive
from scripts.research.rotation_persistence.contracts import ContractError, strict_json_dumps


def _theme(
    theme_id: str,
    rank: float,
    score: float,
    *,
    label: str = "dominant",
    breadth: float | None = 0.6,
) -> dict:
    return {
        "id": theme_id,
        "rank": rank,
        "score": score,
        "label": label,
        "components": {"breadth": breadth},
    }


def _snapshot(as_of: str, themes: list[dict]) -> str:
    return json.dumps({"as_of": as_of, "themes": themes}, separators=(",", ":"))


def _write_archive(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_parquet(path, index=False)


def _row(as_of: str, themes: list[dict], *, logged_at: str = "2026-09-10T00:00:00Z") -> dict:
    return {
        "asof": as_of,
        "logged_at": logged_at,
        "snapshot_json": _snapshot(as_of, themes),
    }


def test_load_basket_archive_normalizes_valid_session_rows(tmp_path: Path) -> None:
    path = tmp_path / "baskets.parquet"
    themes = [_theme("a", 1, 80), _theme("b", 2, 60, breadth=None)]
    _write_archive(path, [_row("2026-09-08", themes), _row("2026-09-09", themes)])

    frames, receipt = load_basket_archive(path)

    assert list(frames) == [date(2026, 9, 8), date(2026, 9, 9)]
    assert list(frames[date(2026, 9, 8)].index) == ["a", "b"]
    assert frames[date(2026, 9, 8)].loc["a", "rank"] == 1.0
    assert frames[date(2026, 9, 8)].loc["a", "score"] == 80.0
    assert frames[date(2026, 9, 8)].loc["a", "breadth"] == 0.6
    assert pd.isna(frames[date(2026, 9, 8)].loc["b", "breadth"])
    assert receipt.rows_read == 2
    assert receipt.rows_valid == 2
    assert receipt.first_asof == "2026-09-08"
    assert receipt.last_asof == "2026-09-09"
    assert receipt.non_session_rows == ()
    assert receipt.duplicate_asof_rows == ()


def test_load_basket_archive_keeps_first_duplicate_asof(tmp_path: Path) -> None:
    path = tmp_path / "baskets.parquet"
    first = _row("2026-09-08", [_theme("a", 1, 80)], logged_at="2026-09-08T20:00:00Z")
    second = _row("2026-09-08", [_theme("a", 1, 10)], logged_at="2026-09-08T21:00:00Z")
    _write_archive(path, [second, first])

    frames, receipt = load_basket_archive(path)

    assert frames[date(2026, 9, 8)].loc["a", "score"] == 10.0
    assert receipt.rows_valid == 1
    assert receipt.duplicate_asof_rows == ("2026-09-08",)


def test_load_basket_archive_drops_non_session_rows_with_receipt(tmp_path: Path) -> None:
    path = tmp_path / "baskets.parquet"
    _write_archive(
        path,
        [
            _row("2026-09-05", [_theme("a", 1, 80)]),  # Saturday
            _row("2026-09-08", [_theme("a", 1, 70)]),
        ],
    )

    frames, receipt = load_basket_archive(path)

    assert list(frames) == [date(2026, 9, 8)]
    assert receipt.non_session_rows == ("2026-09-05",)


def test_load_basket_archive_rejects_snapshot_date_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "baskets.parquet"
    row = _row("2026-09-08", [_theme("a", 1, 80)])
    row["snapshot_json"] = _snapshot("2026-09-09", [_theme("a", 1, 80)])
    _write_archive(path, [row])

    with pytest.raises(ContractError, match="snapshot as_of"):
        load_basket_archive(path)


def test_load_basket_archive_rejects_duplicate_theme_id(tmp_path: Path) -> None:
    path = tmp_path / "baskets.parquet"
    _write_archive(path, [_row("2026-09-08", [_theme("a", 1, 80), _theme("a", 2, 70)])])

    with pytest.raises(ContractError, match="duplicate theme id"):
        load_basket_archive(path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("rank", 0, "rank"),
        ("rank", float("nan"), "rank"),
        ("score", float("inf"), "score"),
        ("score", True, "score"),
    ],
)
def test_load_basket_archive_rejects_invalid_rank_or_score(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    path = tmp_path / "baskets.parquet"
    theme = _theme("a", 1, 80)
    theme[field] = value
    _write_archive(path, [_row("2026-09-08", [theme])])

    with pytest.raises(ContractError, match=message):
        load_basket_archive(path)


def test_load_basket_archive_binds_exact_source_sha256(tmp_path: Path) -> None:
    path = tmp_path / "baskets.parquet"
    _write_archive(path, [_row("2026-09-08", [_theme("a", 1, 80)])])

    _, receipt = load_basket_archive(path)

    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    assert receipt.source_sha256 == expected
    assert len(receipt.source_sha256) == 64


def test_load_basket_archive_requires_owner_columns(tmp_path: Path) -> None:
    path = tmp_path / "baskets.parquet"
    pd.DataFrame([{"asof": "2026-09-08"}]).to_parquet(path, index=False)

    with pytest.raises(ContractError, match="required columns"):
        load_basket_archive(path)


def test_strict_json_dumps_is_sorted_and_rejects_nonfinite() -> None:
    assert strict_json_dumps({"b": 1, "a": 2}) == '{"a":2,"b":1}'
    with pytest.raises(ValueError):
        strict_json_dumps({"x": float("nan")})
