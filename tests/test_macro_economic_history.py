"""Real collector-fixture -> publication -> manifest reader -> native view proof."""
from __future__ import annotations

import copy
import datetime as dt
import json

import pandas as pd
import pytest

from engine.market_os.macro_workspaces import build, contract, liquidity_regime
from engine.market_os.macro_workspaces.history import (
    MAX_POINTS, SOURCES, attach_workspace_history, load_economic_histories, project_source,
)
from lib.macro_suite_view import build_view
from scripts.build_macro_suite_pages import SUITE_PAGES, SnapshotRefused, read_workspace

BUILT = "2026-11-14T12:00:00Z"


def test_component_rows_preserve_gaps_units_and_source_clocks():
    projection = project_source(SOURCES["WALCL"], [
        ("2026-11-12", 6000000), ("2026-10-29", 6100000), ("2026-11-05", None),
    ], built_at=BUILT)
    assert projection["entry"]["points"] == [
        {"t": "2026-10-29", "v": 6100.0}, {"t": "2026-11-05", "v": None},
        {"t": "2026-11-12", "v": 6000.0},
    ]
    assert projection["entry"]["source_ref"] == projection["source"]["source_id"]
    assert projection["entry"]["basis"] == "latest_revised_observation_history"
    assert projection["source"]["released_at"] is None
    assert projection["source"]["first_known_at"] is None
    assert projection["source"]["collected_at"] is None


@pytest.mark.parametrize("rows", [
    [("2026-11-12", float("inf"))], [("2026-11-12", float("nan"))],
    [("2026-11-12", True)], [("2026-11-12", "3.5")],
    [("2026-02-30", 2)], [("2026-11-15", 2)],
    [("2026-11-12", 2), ("2026-11-12", 3)],
])
def test_invalid_observations_fail_closed(rows):
    with pytest.raises(ValueError):
        project_source(SOURCES["CPIAUCSL"], rows, built_at=BUILT)


def test_tail_bound_is_real_observations_not_downsampling():
    first = dt.date(2020, 1, 1)
    rows = [((first + dt.timedelta(days=i)).isoformat(), i) for i in range(1000)]
    result = project_source(SOURCES["EFFR"], rows, built_at=BUILT)["entry"]
    assert len(result["points"]) == MAX_POINTS
    assert result["points"][0]["v"] == 1000 - MAX_POINTS
    assert result["points"][-1]["v"] == 999
    assert result["freshness"] == "STALE_SOURCE"


def test_batch_reads_once_and_preserves_missing_siblings():
    seen = []
    def reader(path, column):
        seen.append(path)
        return [("2026-11-12", 10)] if path.stem == "INDPRO" else None
    batch = load_economic_histories(fred_dir="fixtures/fred", treasury_dir="fixtures/treasury", built_at=BUILT, reader=reader)
    assert len(seen) == len(set(seen)) == len(SOURCES)
    assert batch["business_activity"]["series"]["status"] == "PARTIAL"
    assert batch["growth_real_economy"]["series"]["status"] == "PARTIAL"
    assert batch["labor_markets"]["series"]["status"] == "ABSENT"
    assert batch["business_activity"]["series"]["items"][0]["points"][0]["v"] == 10


def test_attachment_preserves_current_state_and_deterministic_digest():
    body = liquidity_regime.compose({}, built_at=BUILT)
    original = copy.deepcopy(body)
    batch = load_economic_histories(fred_dir="unused", treasury_dir="unused", built_at=BUILT,
                                    reader=lambda p, c: [("2026-11-12", 20)])
    attached = attach_workspace_history(body, batch["liquidity_regime"])
    assert body == original
    for key in ["headline", "axes", "metrics", "availability", "authority", "changes"]:
        assert attached[key] == original[key]
    sealed = contract.finalize(attached)
    contract.validate(sealed)
    shifted = copy.deepcopy(attached)
    shifted["generation"]["built_at"] = "2026-11-14T13:00:00Z"
    assert contract.content_digest(shifted) == sealed["generation"]["content_sha256"]
    with pytest.raises(ValueError, match="existing series owner"):
        attach_workspace_history(attached, batch["liquidity_regime"])


def test_real_parquet_publication_manifest_and_view_keep_null_points(tmp_path):
    fred = tmp_path / "fred"
    fred.mkdir()
    pd.DataFrame({"headline_cpi": [300.0, float("nan"), 301.5]},
                 index=pd.to_datetime(["2026-08-01", "2026-09-01", "2026-10-01"])).to_parquet(fred / "CPIAUCSL.parquet")
    regime = tmp_path / "regime.json"
    regime.write_text("{}", encoding="utf-8")
    out = tmp_path / "macrodata"
    build.build_all(regime_latest_path=regime, fred_dir=fred, treasury_dir=tmp_path / "treasury",
                    out_root=out, built_at=BUILT)
    page = next(page for page in SUITE_PAGES if page.workspace_id == "inflation_system")
    snapshot, artifact = read_workspace(out, page)
    contract.validate(snapshot)
    view = build_view(snapshot, page_built_at=BUILT, artifact=artifact)
    entry = view["series"]["entries"][0]
    assert entry["points"] == [
        {"t": "2026-08-01", "v": 300.0}, {"t": "2026-09-01", "v": None},
        {"t": "2026-10-01", "v": 301.5},
    ]
    assert entry["count"] == 2 and view["series"]["absent"] is False
    assert entry["unit_token"] == "cpi_index"
    assert "reference dates" in entry["basis"]["en"]
    assert entry["source_ref"] in {row["source_id"] for row in view["evidence"]["sources"]}
    assert artifact["sha256"] == snapshot["generation"]["content_sha256"]
    # The reader, not the client chart, detects tampering with the published body.
    body_path = out / "workspaces" / "inflation_system" / "US" / "latest.json"
    tampered = json.loads(body_path.read_text())
    tampered["series"]["items"][0]["points"][0]["v"] = 0
    body_path.write_text(json.dumps(tampered))
    with pytest.raises(SnapshotRefused):
        read_workspace(out, page)


def test_unreadable_existing_history_aborts_before_publication(tmp_path):
    fred = tmp_path / "fred"
    fred.mkdir()
    (fred / "CPIAUCSL.parquet").write_text("corrupted collector file")
    regime = tmp_path / "regime.json"
    regime.write_text("{}")
    out = tmp_path / "macrodata"
    from pyarrow import ArrowInvalid
    with pytest.raises(ArrowInvalid):
        build.build_all(regime_latest_path=regime, fred_dir=fred, treasury_dir=tmp_path / "treasury",
                        out_root=out, built_at=BUILT)
    assert not (out / "workspaces" / "manifest.json").exists()


def test_gdpnow_quarter_reference_does_not_claim_update_freshness():
    result = project_source(SOURCES["GDPNOW"], [("2026-10-01", 3.481)], built_at=BUILT)
    assert result["entry"]["freshness"] == "CURRENT"
    assert result["source"]["collected_at"] is None
    assert result["source"]["released_at"] is None
    assert "source-update freshness" in result["source"]["transform"]
    assert "Federal Reserve Bank of Atlanta" in result["source"]["provider"]
    assert result["source"]["owner_ref"] == "https://fred.stlouisfed.org/series/GDPNOW"
    assert result["entry"]["unit"] == "percent_saar"


def test_history_age_and_attribution_are_visible_in_series_and_evidence():
    body = liquidity_regime.compose({}, built_at=BUILT)
    batch = load_economic_histories(fred_dir="unused", treasury_dir="unused", built_at=BUILT,
                                    reader=lambda p, c: [("2026-11-12", 20)])
    sealed = contract.finalize(attach_workspace_history(body, batch["liquidity_regime"]))
    view = build_view(sealed, page_built_at=BUILT, artifact={})
    row = view["series"]["entries"][0]
    source = next(row for row in view["evidence"]["sources"] if row["source_id"] == "history:fred:WALCL")
    assert "Reference period" in row["freshness"]["en"]
    assert "Reference period" in source["freshness"]["en"]
    assert "attribution" in source["rights"]["en"]


def test_curve_comparison_dates_belong_to_the_exact_values_and_skip_nulls():
    from lib.macro_suite_view import _curve_hero

    snapshot = {"availability": {"state": "CURRENT"}, "series": {"items": [
        {"series_id": "us10y", "points": [
            {"t": "2026-07-01", "v": 4.0},
            {"t": "2026-08-20", "v": 4.1},
            {"t": "2026-09-07", "v": 4.2},
            {"t": "2026-09-08", "v": None},
            {"t": "2026-09-09", "v": 4.3},
        ]},
        {"series_id": "us2y", "points": [{"t": "2026-09-09", "v": 4.4}]},
    ]}}
    rows = {row["tenor"]: row for row in _curve_hero(snapshot)["tenors"]}
    assert (rows["10y"]["prior_close"], rows["10y"]["prior_close_as_of"]) == (4.2, "2026-09-07")
    assert (rows["10y"]["prior_month"], rows["10y"]["prior_month_as_of"]) == (4.0, "2026-07-01")
    for tenor in ("2y", "30y"):
        for window in ("prior_close", "prior_month"):
            assert rows[tenor][window] is None and rows[tenor][f"{window}_as_of"] is None
