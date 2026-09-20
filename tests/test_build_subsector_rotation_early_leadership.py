from __future__ import annotations

import pandas as pd

from scripts.build_subsector_rotation import _attach_early_leadership


def _idx() -> pd.DatetimeIndex:
    return pd.bdate_range("2026-01-05", periods=90)


def _tree() -> list[dict]:
    return [{
        "theme": "Semiconductors",
        "subsectors": [
            {"key": "semiscompute", "name": "Compute", "members": ["A", "B", "C"]},
            {"key": "semismemory", "name": "Memory", "members": ["D", "E", "F"]},
        ],
    }]


def _panel(idx: pd.DatetimeIndex) -> pd.DataFrame:
    return pd.DataFrame(100.0, index=idx, columns=list("ABCDEF"))


def test_attach_early_leadership_publishes_json_ready_shadow_receipt() -> None:
    idx = _idx()
    panel = _panel(idx)
    volume = pd.DataFrame(100.0, index=idx, columns=panel.columns)
    payload: dict = {}
    result = _attach_early_leadership(
        payload,
        _tree(),
        source_tree_sha256="source123",
        generated_utc="2026-09-19 23:40",
        plane={
            "closes": panel,
            "bench": pd.Series(100.0, index=idx),
            "observation": {"effective_as_of": idx[-1].strftime("%Y-%m-%d")},
            "theme_price_resolution": {
                "effective_as_of": idx[-1].strftime("%Y-%m-%d"),
                "resolved_n": 6,
                "unresolved_n": 0,
                "chosen_counts": {"primary_breadth": 6, "baskets_extras": 0},
                "source_basis": {
                    "primary_breadth": "closes_cache_UNADJUSTED",
                    "baskets_extras": "tradj",
                },
                "authority": "measurement_only",
            },
        },
        volume_bundle=(volume, {"raw_tip": idx[-1], "tip": idx[-1],
                                "dropped_all_null_tail_rows": []}),
        completed_through=idx[-1].date(),
    )

    assert payload["early_leadership"] is result
    assert result["status"] == "available"
    assert result["membership_revision"]["source_sha256"] == "source123"
    assert result["membership_revision"]["effective_tree_sha256"] != "source123"
    assert result["source_receipts"]["volume"]["n_columns"] == 6
    assert result["clocks"]["observation"] == idx[-1].strftime("%Y-%m-%d")
    assert result["clocks"]["availability_utc"] is None
    assert result["clocks"]["availability_reason"] == "SOURCE_DID_NOT_RECORD"
    assert result["clocks"]["publication_utc"] is None
    assert result["permissions"]["may_rank"] is False
    assert result["permissions"]["may_trade"] is False


def test_attach_early_leadership_degrades_without_blocking_rotation_build() -> None:
    payload: dict = {}
    result = _attach_early_leadership(
        payload,
        _tree(),
        source_tree_sha256="source123",
        generated_utc="2026-09-19 23:40",
        plane={},
        volume_bundle=(pd.DataFrame(), {}),
        completed_through=pd.Timestamp("2026-09-18").date(),
    )

    assert result["status"] == "unavailable"
    assert result["reason_codes"] == ["GROUP_READ_PLANE_UNAVAILABLE"]
    assert result["permissions"]["may_rank"] is False
    assert result["permissions"]["may_trade"] is False


def test_attach_early_leadership_excludes_in_progress_session() -> None:
    idx = _idx()
    panel = _panel(idx)
    panel.loc[idx[-1], ["A", "B", "C"]] = 160.0
    payload: dict = {}
    result = _attach_early_leadership(
        payload,
        _tree(),
        source_tree_sha256="source123",
        generated_utc="2026-09-19 15:00",
        plane={
            "closes": panel,
            "bench": pd.Series(100.0, index=idx),
            "observation": {"effective_as_of": idx[-1].strftime("%Y-%m-%d")},
            "theme_price_resolution": {},
        },
        volume_bundle=(pd.DataFrame(), {}),
        completed_through=idx[-2].date(),
    )

    assert result["asof"] == idx[-2].strftime("%Y-%m-%d")
    assert result["observation"]["excluded_provisional_dates"] == [
        idx[-1].strftime("%Y-%m-%d")
    ]


def test_attach_early_leadership_uses_resolved_thematic_price_plane() -> None:
    idx = _idx()
    broad = pd.DataFrame(100.0, index=idx, columns=["A"])
    thematic = _panel(idx)
    thematic.loc[idx[-1], ["A", "B", "C"]] = 120.0
    result = _attach_early_leadership(
        {}, _tree(), source_tree_sha256="source123",
        generated_utc="2026-09-19 23:40",
        plane={
            "closes": broad,
            "theme_closes": thematic,
            "bench": pd.Series(100.0, index=idx),
            "observation": {"effective_as_of": idx[-1].strftime("%Y-%m-%d")},
            "theme_price_resolution": {"source_basis": {"primary_breadth": "closes_cache_UNADJUSTED"}},
        },
        volume_bundle=(pd.DataFrame(), {}),
        completed_through=idx[-1].date(),
    )
    compute = next(row for row in result["subthemes"] if row["key"] == "semiscompute")
    assert compute["horizons"]["1"]["coverage"]["eligible_n"] == 3
    assert compute["horizons"]["1"]["return_pct"] == 20.0
    assert result["source_receipts"]["group_read_price_plane"] == "theme_closes"
