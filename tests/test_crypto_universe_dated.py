"""Dated universe membership: coverage denominator, cohort boundary, PIT refusal."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from engine.crypto_universe import (
    DUPLICATE_ID_RULE,
    UniverseUnavailable,
    breadth_read,
    load_universe,
    load_universe_snapshot,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "crypto_universe"
MIXED = "snapshot_2026-10-10_mixed.json"
CLEAN = "snapshot_2026-10-10_clean.json"
PRIOR = "snapshot_2025-06-01.json"


def _stage(tmp_path: Path, *names: str) -> Path:
    for name in names:
        (tmp_path / name).write_bytes((FIXTURES / name).read_bytes())
    return tmp_path


def _document(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_mixed_snapshot_keeps_exact_identity_and_declared_denominator(tmp_path):
    document = _document(MIXED)
    snap = load_universe_snapshot(50, root=_stage(tmp_path, MIXED))
    assert snap["view"] == "current-roster"
    assert snap["date"] == "2026-10-10"
    assert snap["as_of"] == "2026-10-10"
    assert snap["source"] == "CoinGecko"
    assert snap["page_coverage"] == document["pages"]
    assert snap["coverage"]["observed"] == 40
    assert snap["coverage"]["expected"] == 50
    assert snap["coverage"]["missing_pages"] == ["21-30"]
    assert snap["coverage"]["label"] == "40/50"
    assert snap["coverage"]["complete"] is False
    assert len(snap["rows"]) == 40
    assert snap["requested"] == 50
    assert {row["rank"] for row in snap["rows"]} & set(range(21, 31)) == set()
    # The Market Board still cuts a first page of 20 from the remainder.
    # The missing page stays a hole between those slices.
    assert [row["rank"] for row in snap["rows"][:20]] == list(range(1, 21))
    assert [row["rank"] for row in snap["rows"][20:]] == list(range(31, 51))


def test_clean_snapshot_is_complete_only_when_every_declared_page_is_present(tmp_path):
    snap = load_universe_snapshot(50, root=_stage(tmp_path, CLEAN))
    assert snap["coverage"]["label"] == "50/50"
    assert snap["coverage"]["missing_pages"] == []
    assert snap["coverage"]["complete"] is True
    assert [row["rank"] for row in snap["rows"]] == list(range(1, 51))
    assert snap["view"] == "current-roster"


def test_old_rows_do_not_reenter_a_newer_snapshot_as_current(tmp_path):
    root = _stage(tmp_path, MIXED, PRIOR)
    current = load_universe_snapshot(50, root=root)
    ids = {row["id"] for row in current["rows"]}
    assert current["date"] == "2026-10-10"
    assert "matic-network" not in ids
    assert "ftx-token" not in ids
    assert "polygon-ecosystem-token" in ids
    stale = [item for item in current["excluded"] if item["reason"] == "STALE_OBSERVATION"]
    assert {item["id"] for item in stale} >= {"matic-network", "ftx-token", "bitcoin"}
    prior = load_universe_snapshot(50, root=root, as_of="2025-06-01")
    prior_ids = {row["id"] for row in prior["rows"]}
    assert prior["view"] == "point-in-time"
    assert prior["date"] == "2025-06-01"
    assert "matic-network" in prior_ids
    assert "ftx-token" in prior_ids
    assert "polygon-ecosystem-token" not in prior_ids
    assert "wrapped-steth" not in prior_ids
    dot_now = next(row for row in current["rows"] if row["id"] == "polkadot")
    dot_then = next(row for row in prior["rows"] if row["id"] == "polkadot")
    assert dot_now["rank"] == 17 and dot_now["rank_prev"] == 19
    assert dot_then["rank"] == 19
    wrapped = next(row for row in current["rows"] if row["id"] == "wrapped-bitcoin")
    bitcoin = next(row for row in current["rows"] if row["id"] == "bitcoin")
    assert wrapped["id"] != bitcoin["id"]
    assert wrapped["rank"] != bitcoin["rank"]
    assert "renamed_from" not in wrapped
    assert load_universe(50, root=root)
    assert "matic-network" not in {row["id"] for row in load_universe(50, root=root)}


def test_duplicate_ids_collapse_by_the_stated_rule(tmp_path):
    snap = load_universe_snapshot(50, root=_stage(tmp_path, MIXED))
    assert snap["duplicate_rule"] == DUPLICATE_ID_RULE
    assert "lowest rank" in snap["duplicate_rule"]
    assert "DUPLICATE_ID" in snap["duplicate_rule"]
    bitcoin = [row for row in snap["rows"] if row["id"] == "bitcoin"]
    assert len(bitcoin) == 1
    assert bitcoin[0]["price"] == 100.0
    reasons = [item["reason"] for item in snap["excluded"] if item.get("id") == "bitcoin"]
    assert reasons.count("DUPLICATE_ID") == 1
    assert "STALE_OBSERVATION" in reasons
    absent = [item for item in snap["excluded"] if item["reason"] == "PAGE_ABSENT"]
    assert [item["id"] for item in absent] == ["quant-network"]
    assert "quant-network" not in {row["id"] for row in snap["rows"]}


def test_current_roster_is_labeled_and_missing_pit_membership_is_unavailable(tmp_path):
    root = _stage(tmp_path, MIXED, PRIOR)
    current = load_universe_snapshot(50, root=root)
    assert current["view"] == "current-roster"
    assert current["status"] == "current-roster"
    same_day = load_universe_snapshot(50, root=root, as_of="2026-10-10")
    assert same_day["view"] == "point-in-time"
    assert [row["id"] for row in same_day["rows"]] == [row["id"] for row in current["rows"]]
    refused = load_universe_snapshot(50, root=root, as_of="2024-03-15")
    assert isinstance(refused, UniverseUnavailable)
    assert refused["status"] == "unavailable"
    assert refused["reason"] == "HISTORICAL_MEMBERSHIP_UNAVAILABLE"
    assert refused["rows"] == []
    assert refused["view"] == "point-in-time"
    assert {row["id"] for row in current["rows"]}
    assert {row["id"] for row in refused["rows"]} != {row["id"] for row in current["rows"]}


def test_two_documents_for_one_date_are_not_unioned_into_a_complete_top_50(tmp_path):
    refused = load_universe_snapshot(50, root=_stage(tmp_path, MIXED, CLEAN))
    assert isinstance(refused, UniverseUnavailable)
    assert refused["reason"] == "DUPLICATE_SNAPSHOT_DATE"
    assert refused["rows"] == []
    assert refused["coverage"] is None


def test_numerical_rank_carries_no_recommendation(tmp_path):
    document = _document(MIXED)
    assert any(row.get("recommendation") == "overweight" for row in document["rows"])
    snap = load_universe_snapshot(50, root=_stage(tmp_path, MIXED))
    eth = next(row for row in snap["rows"] if row["id"] == "ethereum")
    assert isinstance(eth["rank"], int)
    assert eth["rank"] == 2
    for row in snap["rows"]:
        assert isinstance(row["rank"], int)
        assert "recommendation" not in row
        assert "allocation" not in row
        assert "score" not in row
        assert "signal" not in row
        assert isinstance(row["symbol"], str) and isinstance(row["name"], str)
        assert row["symbol"] != row["name"] or row["symbol"] in {"XRP", "BNB", "USDT", "USDC", "TRX"}


def test_breadth_partial_coverage_reports_the_denominator_it_used(tmp_path):
    snap = load_universe_snapshot(50, root=_stage(tmp_path, MIXED))
    result = breadth_read(snap["rows"])
    assert result["available"] is True
    assert result["denominator"] == 15
    assert result["eligible"] == 15
    assert result["positive"] == 9
    assert result["value"] == round(100 * result["positive"] / result["denominator"])
    assert result["value"] == 60
    assert result["coverage"]["label"] == "40/50"
    assert result["coverage"]["missing_pages"] == ["21-30"]
    assert result["denominator"] != result["coverage"]["expected"]
    decoy = [dict(row, coverage_expected=50) for row in snap["rows"]]
    decoy_result = breadth_read(decoy)
    assert decoy_result["denominator"] == 15
    assert decoy_result["value"] == 60
    assert "coverage" not in decoy_result


def test_parquet_pit_for_an_unrecorded_date_does_not_return_the_current_roster(tmp_path):
    dates = pd.date_range("2026-09-26", periods=2, freq="D")
    frame = pd.DataFrame(
        {
            "source": ["CoinGecko", "CoinGecko"],
            "coin_id": ["bitcoin", "bitcoin"],
            "symbol": ["BTC", "BTC"],
            "name": ["Bitcoin", "Bitcoin"],
            "market_cap_rank": [1, 1],
            "current_price": [10.0, 11.0],
            "market_cap": [1_000_000, 1_000_000],
            "total_volume": [100_000, 100_000],
            "change_24h_pct": [1.0, 1.0],
            "change_7d_pct": [4.0, 4.0],
            "change_30d_pct": [12.0, 12.0],
        },
        index=dates,
    )
    frame.to_parquet(tmp_path / "market_btc.parquet")
    current = load_universe_snapshot(50, root=tmp_path)
    assert current["view"] == "current-roster"
    assert current["as_of"] == "2026-09-27"
    assert [row["symbol"] for row in current["rows"]] == ["BTC"]
    assert current["coverage"]["complete"] is False
    same = load_universe_snapshot(50, root=tmp_path, as_of="2026-09-27")
    assert same["view"] == "point-in-time"
    assert [row["symbol"] for row in same["rows"]] == ["BTC"]
    refused = load_universe_snapshot(50, root=tmp_path, as_of="2026-09-26")
    assert isinstance(refused, UniverseUnavailable)
    assert refused["rows"] == []
    assert [row["symbol"] for row in refused["rows"]] != ["BTC"]
