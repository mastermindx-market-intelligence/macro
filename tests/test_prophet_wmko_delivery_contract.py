"""Real producer/HTTP regressions for source-bound WM/KO coverage and timing."""
from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from engine import prophet_early_observations as observations
from engine import us_turn_watch as tw
from scripts.build_turn_watch import write_candidate_episode_input
from tests.test_prophet_early_observations import seed

REPO = Path(tw.__file__).resolve().parents[1]


def publish(tmp_path, *, version=1, session="2026-10-16", tickers=("AMZN",),
            change_contract=None, change_row=None):
    source, spine, rows, artifact = seed(tmp_path, tickers, session=session)
    manifest = json.loads((REPO / f"config/us_turn_watch_universe.v{version}.json").read_text())
    artifact["selection_era"] = manifest["selection_era"]
    proof = {key: manifest[key] for key in
             ("universe_id", "selection_era", "population_count", "tickers_sha256")}
    proof.update(schema="us_turn_watch.source_contract.v1", pass_=True)
    proof["pass"] = proof.pop("pass_")
    proof.update(selected_count=manifest["population_count"], universe_limit=None,
                 missing_store_count=0, missing_store=[], modal_session=session,
                 expected_completed_session=session, freshness_ok=True)
    artifact["coverage"]["source_contract"] = proof
    if change_contract:
        change_contract(artifact)
    if change_row:
        change_row(rows[0])
    write_candidate_episode_input(artifact, rows, tmp_path / "data")
    tw.write_artifact(artifact, tmp_path / "site")
    config = tmp_path / "config"
    config.mkdir(exist_ok=True)
    (config / f"us_turn_watch_universe.v{version}.json").write_text(json.dumps(manifest))
    return source, spine, manifest


def projection(tmp_path, **kwargs):
    source, spine, manifest = publish(tmp_path, **kwargs)
    return observations.load_observations(
        source, spine=spine, reference_session=kwargs.get("session", "2026-10-16"),
        public_artifact_path=tmp_path / "site/turn_watch/turn_watch.json",
        active_universe=manifest,
    )


@pytest.mark.parametrize("ticker,state,count", [
    ("WM", "NOT_IN_UNIVERSE", 0),
    ("KO", "IN_UNIVERSE_NO_RECORDED_TRIGGER", 0),
    ("AMZN", "VERIFIED_SOURCE_PARTITION", 1),
])
def test_subject_explanation_never_fabricates_observations(tmp_path, ticker, state, count):
    page = observations.query_observations(projection(tmp_path), ticker=ticker)
    assert page["subject_coverage"]["ticker"] == ticker
    assert page["subject_coverage"]["state"] == state
    assert page["counts"] == {"source": 1, "matched": count, "returned": count}
    assert len(page["rows"]) == count
    assert not any(key.startswith("_") for key in page)
    json.dumps(page, allow_nan=False)
    assert all(value is False for value in page["authority"].values())


def test_security_filter_does_not_create_a_negative_ticker_observation(tmp_path):
    page = observations.query_observations(
        projection(tmp_path), ticker="AMZN", security_id="SEC:US-XNAS-KO")
    assert page["rows"] == []
    assert page["counts"]["matched"] == 0
    # The ticker has a real source event; the different security filter cannot erase that fact.
    assert page["subject_coverage"]["state"] == "VERIFIED_SOURCE_PARTITION"


def test_verified_coverage_binds_the_existing_public_contract(tmp_path):
    page = observations.query_observations(projection(tmp_path), ticker="WM")
    universe = page["universe_coverage"]
    assert universe["state"] == "VERIFIED_SOURCE_PARTITION"
    assert universe["source_session"] == "2026-10-16"
    assert page["coverage"]["source_artifact_receipt"] == "sha256:" + universe["published_proof_sha256"]


@pytest.mark.parametrize("change", [
    lambda a: a["coverage"].pop("source_contract"),
    lambda a: a["coverage"]["source_contract"].update({"pass": False}),
    lambda a: a["coverage"]["source_contract"].update(tickers_sha256="0" * 64),
    lambda a: a["coverage"]["source_contract"].update(selection_era=tw.SELECTION_ERA_V2),
    lambda a: a["coverage"]["source_contract"].update(selected_count=40, universe_limit=40),
    lambda a: a["coverage"]["source_contract"].update(missing_store_count=1, missing_store=["KO"]),
])
def test_incomplete_or_mismatched_producer_proof_withholds_membership(tmp_path, change):
    page = observations.query_observations(projection(tmp_path, change_contract=change), ticker="WM")
    assert page["rows"] == []
    assert page["subject_coverage"]["state"] == "UNAVAILABLE"
    assert page["universe_coverage"]["state"] == "UNAVAILABLE"
    assert page["counts"] == {"source": 1, "matched": 0, "returned": 0}


def test_missing_public_receipt_cannot_certify_manifest_membership(tmp_path):
    source, spine, manifest = publish(tmp_path)
    result = observations.load_observations(
        source, spine=spine, reference_session="2026-10-16", active_universe=manifest)
    assert result["universe_coverage"]["state"] == "UNAVAILABLE"


def test_prospective_manifest_never_certifies_historical_v1(tmp_path):
    source, spine, _ = publish(tmp_path)
    future = json.loads((REPO / "config/us_turn_watch_universe.v2.json").read_text())
    result = observations.load_observations(
        source, spine=spine, reference_session="2026-10-20", active_universe=future,
        public_artifact_path=tmp_path / "site/turn_watch/turn_watch.json")
    assert result["universe_coverage"]["state"] == "UNAVAILABLE"


def test_wm_no_event_after_activation_is_distinct_from_outside_v1(tmp_path):
    page = observations.query_observations(
        projection(tmp_path, version=2, session="2026-10-19"), ticker="WM")
    assert page["rows"] == []
    assert page["subject_coverage"]["state"] == "IN_UNIVERSE_NO_RECORDED_TRIGGER"


@pytest.mark.parametrize("reference", [date(2026, 10, 16), date(2026, 10, 20)])
def test_real_loader_and_http_response_keep_the_source_era(tmp_path, monkeypatch, reference):
    import app.prophet_observations as route
    publish(tmp_path)
    # A v2 manifest is present, but the retained source is still v1.
    (tmp_path / "config/us_turn_watch_universe.v2.json").write_bytes(
        (REPO / "config/us_turn_watch_universe.v2.json").read_bytes())
    monkeypatch.setattr(route, "_DATA_ROOT", tmp_path / "data")
    monkeypatch.setattr(route, "expected_last_session", lambda: reference)
    app = FastAPI()
    app.include_router(route.router)
    app.dependency_overrides[route.require_site_full_user] = lambda: {"id": "entitled-fixture"}
    with TestClient(app) as client:
        response = client.get("/api/prophet/observations/v1?ticker=WM")
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    page = response.json()
    assert page["universe_coverage"]["selection_era"] == tw.SELECTION_ERA
    assert page["subject_coverage"]["state"] == "NOT_IN_UNIVERSE"
    assert page["rows"] == []
    assert not any(key.startswith("_") for key in page)


@pytest.mark.parametrize("asof,expected", [(None, None), ("2026-10-15", "2026-10-15"),
    ("2026-10-17", None), ("not-a-date", None), ("2026-02-30", None)])
def test_per_stock_clock_never_inherits_document_freshness(tmp_path, asof, expected):
    result = projection(tmp_path, change_row=lambda row: row.update(asof=asof))
    assert result["rows"][0]["source_timing"]["asof"] == expected


@pytest.mark.parametrize("value", [True, False, "93.90", 0, -1])
def test_invalid_price_is_unknown_through_real_loader(tmp_path, value):
    result = projection(tmp_path, change_row=lambda row: row.update(close=value))
    assert result["rows"][0]["source_timing"]["close"] is None


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True, False])
def test_nonfinite_or_boolean_timing_never_reaches_json(value):
    timing = observations._source_timing(
        {"close": value, "reset": {"reset_low": value, "off_reset_low_pct": value},
         "slow_tier": {"bars_to_cross_3d": value}}, "2026-10-16")
    assert timing["close"] is None and timing["reset_low"] is None
    assert timing["off_reset_low_pct"] is None and timing["slow_tier_bars_to_cross_3d"] is None
    json.dumps(timing, allow_nan=False)


def test_native_ko_timing_fields_survive_without_reinterpretation(tmp_path):
    def ko(row):
        row.update(close=93.9, asof="2026-10-16",
                   reset={"reset_low": 85.65, "reset_low_date": "2026-10-02", "off_reset_low_pct": 9.63},
                   slow_tier={"above_200dma": True, "eligible": True, "evaluated": True,
                              "tier": "T2", "bars_to_cross_3d": None, "blocking": []})
    page = observations.query_observations(projection(tmp_path, tickers=("KO",), change_row=ko), ticker="KO")
    timing = page["rows"][0]["source_timing"]
    assert timing["slow_tier_above_200dma"] is True
    assert [timing[k] for k in ("asof", "close", "reset_low", "reset_low_date", "off_reset_low_pct")] == [
        "2026-10-16", 93.9, 85.65, "2026-10-02", 9.63]
    json.dumps(page, allow_nan=False)


@pytest.mark.parametrize("failure", [None, RuntimeError("calendar unavailable")])
def test_unresolved_completed_session_fails_closed(tmp_path, monkeypatch, failure):
    def unavailable(now_utc=None):
        if isinstance(failure, Exception):
            raise failure
        return failure
    monkeypatch.setattr(tw, "_completed_session", unavailable)
    assert tw.active_selection_era(REPO / "data") is None
    assert tw.universe_contract_for_active(REPO / "data") is None


def build_fixture(tmp_path, monkeypatch, *, version, source_session, completed_session):
    import pandas as pd
    from lib import nyse_calendar
    manifest = json.loads((REPO / f"config/us_turn_watch_universe.v{version}.json").read_text())
    names = ["KO"] if version == 1 else ["KO", "WM"]
    manifest.update(tickers=names, population_count=len(names),
                    tickers_sha256=sha256(("\n".join(names) + "\n").encode()).hexdigest())
    manifest["universe_id"] = f'us-turn-watch:{manifest["selection_era"]}:{manifest["tickers_sha256"][:12]}'
    manifest["snapshot"] = {"graded_min_bars_200": len(names), "graded_min_bars_260": len(names)}
    config = tmp_path / "config"
    config.mkdir()
    contract_path = config / f"us_turn_watch_universe.v{version}.json"
    contract_path.write_text(json.dumps(manifest))
    data, site = tmp_path / "data", tmp_path / "site"
    price_dir = data / tw.DECK_STORE
    price_dir.mkdir(parents=True)
    site.mkdir()
    prices = pd.Series(range(100, 500), dtype=float,
                       index=pd.bdate_range(end=source_session, periods=400))
    for name in names + [tw.BENCHMARK]:
        prices.to_frame("close").to_parquet(price_dir / f"{name}.parquet")
    monkeypatch.setattr(nyse_calendar, "expected_last_session",
                        lambda now_utc=None: date.fromisoformat(completed_session))
    return data, site, contract_path


@pytest.mark.parametrize("version,session,era", [
    (1, "2026-10-16", tw.SELECTION_ERA), (2, "2026-10-19", tw.SELECTION_ERA_V2)])
def test_real_producer_and_sidecar_emit_the_same_selected_era(tmp_path, monkeypatch, version, session, era):
    data, site, _ = build_fixture(tmp_path, monkeypatch, version=version,
                                 source_session=session, completed_session=session)
    artifact, rows = tw.compute_deck_with_candidates(data, site)
    assert artifact["selection_era"] == era
    assert artifact["coverage"]["source_contract"]["selection_era"] == era
    assert artifact["coverage"]["source_contract"]["pass"] is True
    sidecar = json.loads(write_candidate_episode_input(artifact, rows, data).read_text())
    assert sidecar["selection_era"] == era
    assert sidecar["source_artifact_sha256"] == "sha256:" + sha256(tw.artifact_bytes(artifact)).hexdigest()


def test_post_cutoff_build_cannot_publish_stale_v1_prices_under_v2(tmp_path, monkeypatch):
    data, site, _ = build_fixture(tmp_path, monkeypatch, version=2,
                                 source_session="2026-10-16", completed_session="2026-10-19")
    artifact, _ = tw.compute_deck_with_candidates(data, site)
    assert artifact["data_session"] == "2026-10-16"
    assert artifact["coverage"]["source_contract"]["pass"] is False


def test_build_reuses_one_contract_snapshot_even_if_file_changes(tmp_path, monkeypatch):
    data, site, path = build_fixture(tmp_path, monkeypatch, version=2,
                                    source_session="2026-10-19", completed_session="2026-10-19")
    real_cross_section = tw._leader_rs_cross_section
    def replace_after_selection(closes, benchmark):
        path.write_text("{}")
        return real_cross_section(closes, benchmark)
    monkeypatch.setattr(tw, "_leader_rs_cross_section", replace_after_selection)
    artifact, _ = tw.compute_deck_with_candidates(data, site)
    assert artifact["coverage"]["universe"] == 2
    assert artifact["coverage"]["source_contract"]["pass"] is True
    assert artifact["selection_era"] == tw.SELECTION_ERA_V2


def test_explicit_unresolved_selection_never_reloads_a_contract(tmp_path, monkeypatch):
    data, _, _ = build_fixture(tmp_path, monkeypatch, version=2,
                               source_session="2026-10-19", completed_session="2026-10-19")
    def forbidden(*args, **kwargs):
        raise AssertionError("an explicit unresolved contract must not be redispatched")
    monkeypatch.setattr(tw, "universe_contract_for_active", forbidden)
    assert tw.universe(data, selected_contract=None) == []
    status = tw.source_contract_status(data, members=[], closes={}, missing_store=[],
                                       benchmark=None, min_bars=260, selected_contract=None)
    assert status["pass"] is False and status["selection_era"] is None


@pytest.mark.parametrize("ticker", ["wm", "Wm", "WM"])
def test_subject_membership_uses_canonical_ticker_case(tmp_path, ticker):
    page = observations.query_observations(projection(tmp_path), ticker=ticker)
    assert page["subject_coverage"] == {"ticker": "WM", "state": "NOT_IN_UNIVERSE", "reason": None}


def test_legacy_shared_helpers_keep_v1_after_the_new_turn_watch_cutoff(tmp_path, monkeypatch):
    from lib import nyse_calendar
    data, _, _ = build_fixture(tmp_path, monkeypatch, version=1,
                               source_session="2026-10-19", completed_session="2026-10-19")
    assert tw.universe(data) == ["KO"]
    import pandas as pd
    close = pd.Series([1.0], index=pd.to_datetime(["2026-10-19"]))
    manifest = tw.universe_contract(data)
    # The floor in this fixture is one member; the legacy producer retains its own era.
    result = tw.source_contract_status(data, members=["KO"], closes={"KO": close},
                                       missing_store=[], benchmark=close, min_bars=200)
    assert result["selection_era"] == tw.SELECTION_ERA and result["pass"] is True


def test_optional_universe_import_failure_preserves_valid_observations(tmp_path, monkeypatch):
    import builtins
    import app.prophet_observations as route
    publish(tmp_path)
    monkeypatch.setattr(route, "_DATA_ROOT", tmp_path / "data")
    monkeypatch.setattr(route, "expected_last_session", lambda: date(2026, 10, 16))
    original_import = builtins.__import__
    def without_universe(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "engine" and "us_turn_watch" in fromlist:
            raise ModuleNotFoundError("optional universe runtime")
        return original_import(name, globals, locals, fromlist, level)
    monkeypatch.setattr(builtins, "__import__", without_universe)
    result = observations.query_observations(route.read_current_observations(), ticker="AMZN")
    assert result["status"] == "CURRENT_SESSION" and len(result["rows"]) == 1
    assert result["universe_coverage"]["state"] == "UNAVAILABLE"
    json.dumps(result, allow_nan=False)
