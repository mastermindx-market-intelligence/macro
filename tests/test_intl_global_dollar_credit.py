"""INTL-GS-W3B (IM16): dollar-regime and EM credit transmission contract tests.

Qualified-or-abstain four-clock change receipts built on the incumbent GLT
alignment, the closed abstain vocabulary, point-in-time stability, and the
per-jurisdiction assessments that never upgrade a jurisdiction claim from a
global or regional context input. Synthetic series only unless a real
committed parquet is named; no test ever fetches data.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
import random
import statistics
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

import engine.intl_global_dollar_credit as dc
from engine.global_liquidity_transmission import load_producer_config
from engine.intl_global_observation import ABSTAIN_REASONS as OBS_ABSTAIN_REASONS
from engine.intl_global_observation import check_clocks
from engine.intl_global_universe import load_rights_matrix, load_universe

MODULE_SOURCE_PATH = Path(dc.__file__)

#: Test-only rights row (never written to any config); mirrors an
#: EMISSION_OK row shape: id + rights_class + decision_ref.
RIGHTS_ROW_OK = {
    "id": "fixture.emission_ok",
    "rights_class": "derived_display_ok",
    "decision_ref": "fixture",
}

EM_OAS_SOURCE_IDS = (
    "em_corporate_oas",
    "em_asia_corporate_oas",
    "em_latam_corporate_oas",
    "em_emea_corporate_oas",
)


# --------------------------------------------------------------------------
# synthetic fixtures


def _daily_walk(seed: int, periods: int = 780, start: str = "2023-01-02") -> pd.Series:
    rng = random.Random(seed)
    idx = pd.bdate_range(start, periods=periods)
    value = 100.0
    vals = []
    for _ in range(periods):
        value *= 1.0 + rng.gauss(0.0, 0.004)
        vals.append(value)
    return pd.Series(vals, index=idx, name="fixture")


def _daily_rising(periods: int = 780, start: str = "2023-01-02") -> pd.Series:
    """Deterministically rising series: any 13-week window has a positive change."""
    idx = pd.bdate_range(start, periods=periods)
    vals = [
        100.0 * (1.0006 ** i) * (1.0 + 0.0004 * ((i % 21) - 10) / 10.0)
        for i in range(periods)
    ]
    return pd.Series(vals, index=idx, name="fixture")


def _daily_flat_tail(periods: int = 780, start: str = "2023-01-02") -> pd.Series:
    """Rising walk that freezes for the last ~26 weeks: change at t is exactly 0
    while earlier changes are non-zero (so the prior std stays positive)."""
    idx = pd.bdate_range(start, periods=periods)
    vals = []
    for i in range(periods):
        if i < periods - 130:
            vals.append(100.0 * (1.0006 ** i))
        else:
            vals.append(100.0 * (1.0006 ** (periods - 131)))
    return pd.Series(vals, index=idx, name="fixture")


def _friday_on_or_after(ts) -> pd.Timestamp:
    ts = pd.Timestamp(ts)
    return ts + pd.Timedelta(days=(4 - ts.dayofweek) % 7)


def _as_of_for(raw: pd.Series) -> pd.Timestamp:
    """A Friday at/after the last observation, close enough that the last grid
    point is fresh (age well under every stale_after bound in the GLT config)."""
    return _friday_on_or_after(raw.index[-1])


_DEFAULT = object()


def _receipt(raw, *, source_id="broad_dollar", rights_row=RIGHTS_ROW_OK,
             evidence_ref="fixture:synthetic", as_of=None, ingested_at=_DEFAULT,
             computed_at=_DEFAULT, producer_cfg=None):
    if as_of is None:
        as_of = _as_of_for(raw) if raw is not None and len(raw) else "2026-12-31"
    if ingested_at is _DEFAULT:
        ingested_at = "2026-12-31T23:00:00"
    if computed_at is _DEFAULT:
        computed_at = "2026-12-31T23:30:00"
    return dc.series_change_receipt(
        raw, source_id=source_id, as_of=as_of, ingested_at=ingested_at,
        computed_at=computed_at, rights_row=rights_row,
        evidence_ref=evidence_ref, producer_cfg=producer_cfg)


def _expected_weekly_log(raw: pd.Series, as_of, change_periods=13,
                         transform="log_change"):
    """Independent hand computation of the aligned weekly values.

    The GLT alignment carries, at each Friday grid point, the last observation
    whose reference date plus release_lag_bdays (1 business day) lands on or
    before that Friday — for continuous business-daily data, Thursday's close.
    ``transform="level_change"`` returns plain first differences (percentage
    points) instead of 100 x log differences.
    """
    grid = pd.date_range(raw.index.min(), as_of, freq="W-FRI")
    vals = []
    for friday in grid:
        eligible = raw.index[raw.index <= friday - pd.offsets.BDay(1)]
        vals.append(float(raw.loc[eligible[-1]]) if len(eligible) else None)

    def _change(later, earlier):
        if transform == "log_change":
            return 100.0 * (math.log(later) - math.log(earlier))
        return later - earlier

    changes = [
        None if (i < change_periods or vals[i] is None
                 or vals[i - change_periods] is None)
        else _change(vals[i], vals[i - change_periods])
        for i in range(len(vals))
    ]
    prior = [c for c in changes[:-1] if c is not None]
    return {
        "grid": grid,
        "vals": vals,
        "changes": changes,
        "prior": prior,
        "level": vals[-1],
        "change": changes[-1],
        "z": ((changes[-1] - statistics.mean(prior)) / statistics.stdev(prior))
        if changes[-1] is not None and len(prior) >= 2 else None,
    }


# --------------------------------------------------------------------------
# 1. SOURCES closed vocabulary


def test_sources_closed_and_unadmitted():
    assert list(dc.SOURCES) == [
        "broad_dollar", "us_real_yield_10y", "em_corporate_oas",
        "em_asia_corporate_oas", "em_latam_corporate_oas",
        "em_emea_corporate_oas",
    ]
    matrix_ids = {row["id"] for row in load_rights_matrix()["rows"]}
    expected_series = {
        "broad_dollar": "DTWEXBGS",
        "us_real_yield_10y": "DFII10",
        "em_corporate_oas": "BAMLEMCBPIOAS",
        "em_asia_corporate_oas": "BAMLEMRACRPIASIAOAS",
        "em_latam_corporate_oas": "BAMLEMRLCRPILAOAS",
        "em_emea_corporate_oas": "BAMLEMRECRPIEMEAOAS",
    }
    expected_columns = {"broad_dollar": "broad_dollar", "us_real_yield_10y": "us10y_real"}
    for source_id, meta in dc.SOURCES.items():
        assert meta["rights_ref"] is None
        assert meta["series_id"] == expected_series[source_id]
        assert meta["store"] == "fred"
        assert meta["key"] == expected_series[source_id]
        assert meta["column"] == expected_columns.get(source_id)
        assert not any(
            token in rid for rid in matrix_ids
            for token in ("DTWEXBGS", "DFII10", "BAMLEM")
        ), "no rights-matrix row may name a FRED dollar/real-yield/BAMLEM series"
    for source_id in EM_OAS_SOURCE_IDS:
        population = dc.SOURCES[source_id]["population"]
        assert "corporate" in population
        assert "not sovereigns" in population
        assert dc.SOURCES[source_id]["licence_note"]
    assert dc.SOVEREIGN_SPREAD_SOURCES == {}
    assert dc.CONTRACT_VERSION == "intl-global-dollar-credit-v1"
    assert dc.CLAIM_LEVELS == ("global_context", "regional_system", "jurisdiction")
    assert dc.SOURCES["broad_dollar"]["claim_level"] == "global_context"
    assert dc.SOURCES["us_real_yield_10y"]["claim_level"] == "global_context"
    for source_id in EM_OAS_SOURCE_IDS:
        assert dc.SOURCES[source_id]["claim_level"] == "regional_system"
    expected_reasons = frozenset(OBS_ABSTAIN_REASONS) | {
        "no_admitted_source", "insufficient_history", "stale_input",
        "proxy_population_mismatch", "funding_observation_unavailable",
        "capability_not_qualified"}
    assert dc.ABSTAIN_REASONS == expected_reasons
    assert set(dc.DIRECTION_TOKENS) == set(dc.SOURCES)
    assert dc.DIRECTION_TOKENS["broad_dollar"] == ("dollar_stronger", "dollar_weaker")
    assert dc.DIRECTION_TOKENS["us_real_yield_10y"] == ("real_yield_higher", "real_yield_lower")
    for source_id in EM_OAS_SOURCE_IDS:
        assert dc.DIRECTION_TOKENS[source_id] == ("spread_wider", "spread_narrower")
    assert dc.BANNED_TOKENS == (
        "safe", "stable", "stability", "resilient", "crisis", "low_risk",
        "high_risk", "fragile")


# --------------------------------------------------------------------------
# 2. alignment spec equals the GLT config; direction_multiplier never applied


def test_source_spec_equals_glt_config():
    cfg = load_producer_config()
    assert cfg["min_history_periods"] == 52
    assert cfg["frequency"] == "W-FRI"
    for source_id, component in (
            ("broad_dollar", "broad_dollar"),
            ("us_real_yield_10y", "real_yield_10y")):
        spec = dc.source_spec(source_id, cfg)
        assert spec == cfg["usd_funding_components"][component]
        spec["release_lag_bdays"] = 999  # deep copy: never the config itself
        assert cfg["usd_funding_components"][component]["release_lag_bdays"] != 999
        assert dc.source_spec(source_id, cfg) == cfg["usd_funding_components"][component]
    hy = cfg["usd_funding_components"]["high_yield_oas"]
    for source_id in EM_OAS_SOURCE_IDS:
        series_id = dc.SOURCES[source_id]["series_id"]
        spec = dc.source_spec(source_id, cfg)
        expected = copy.deepcopy(hy)
        expected.update(
            {"store": "fred", "key": series_id, "column": None,
             "source_id": series_id})
        assert spec == expected
        for field in ("frequency", "period_anchor", "release_lag_bdays",
                      "stale_after_calendar_days", "change_transform",
                      "change_periods"):
            assert spec[field] == hy[field]
    assert dc.source_spec("broad_dollar") == dc.source_spec("broad_dollar", cfg)
    with pytest.raises(Exception):
        dc.source_spec("not_a_source")


def test_no_direction_multiplier_and_call_time_config_reads():
    source = MODULE_SOURCE_PATH.read_text()
    assert "W-FRI" not in source, "grid frequency must be read from the GLT config"
    assert "= 52" not in source, "min history must be read from the GLT config"

    rising = _daily_rising()
    receipt = _receipt(rising)
    assert receipt["state"] == "qualified"
    assert receipt["value"]["change"] > 0  # GLT direction_multiplier -1 never applied
    assert receipt["value"]["direction"] == "dollar_stronger"

    cfg = load_producer_config()
    stricter = copy.deepcopy(cfg)
    stricter["min_history_periods"] = 10_000
    abstain = _receipt(rising, producer_cfg=stricter)
    assert abstain["state"] == "abstain"
    assert abstain["abstain_reasons"] == ["insufficient_history"]
    assert abstain["value"] is None

    daily_grid = copy.deepcopy(cfg)
    daily_grid["frequency"] = "D"
    weekly = _receipt(rising)
    daily = _receipt(rising, producer_cfg=daily_grid)
    assert weekly["state"] == "qualified" and daily["state"] == "qualified"
    assert (daily["value"]["prior_history_periods"]
            > weekly["value"]["prior_history_periods"]), \
        "frequency must be read from the producer config at call time"


# --------------------------------------------------------------------------
# 3. qualified synthetic case against a hand computation


def test_qualified_hand_computation():
    raw = _daily_walk(20261021)
    as_of = _as_of_for(raw)
    ingested, computed = "2026-12-31T23:00:00", "2026-12-31T23:30:00"
    receipt = dc.series_change_receipt(
        raw, source_id="broad_dollar", as_of=as_of, ingested_at=ingested,
        computed_at=computed, rights_row=RIGHTS_ROW_OK,
        evidence_ref="fixture:synthetic")
    assert receipt["state"] == "qualified"
    assert receipt["abstain_reasons"] == []
    expected = _expected_weekly_log(raw, as_of)
    value = receipt["value"]
    assert value["level"] == pytest.approx(expected["level"], abs=1e-9)
    assert value["change"] == pytest.approx(expected["change"], abs=1e-9)
    assert value["change_unit"] == "log_pct"
    assert value["change_periods"] == 13
    assert value["z_prior"] == pytest.approx(expected["z"], abs=1e-9)
    assert value["prior_history_periods"] == len(expected["prior"])
    assert value["direction"] in ("dollar_stronger", "dollar_weaker")
    assert (value["direction"] == "dollar_stronger") == (value["change"] > 0)

    assert set(receipt) == {
        "contract_version", "receipt_id", "source_id", "series_id",
        "claim_level", "population", "orientation", "unit", "state",
        "abstain_reasons", "value", "clocks", "alignment", "rights",
        "evidence_ref", "interpretation_limits"}
    assert receipt["rights"] == {
        "rights_ref": "fixture.emission_ok",
        "rights_class": "derived_display_ok",
        "decision_ref": "fixture"}
    cfg = load_producer_config()
    assert receipt["alignment"] == {
        "frequency": "daily_business",
        "release_lag_bdays": 1,
        "stale_after_calendar_days": 10,
        "change_transform": "log_change",
        "min_history_periods": 52}
    assert receipt["alignment"]["frequency"] == cfg["usd_funding_components"]["broad_dollar"]["frequency"]

    clocks = receipt["clocks"]
    obs = datetime.fromisoformat(clocks["observation"]["at"])
    pub = datetime.fromisoformat(clocks["source_publication"]["at"])
    ing = datetime.fromisoformat(clocks["ingestion"]["at"])
    cmp_ = datetime.fromisoformat(clocks["computation"]["at"])
    assert obs <= pub <= ing <= cmp_
    assert clocks["source_publication"]["basis"] == "modeled_release_lag"
    assert check_clocks(clocks) is None

    # exact zero change keeps its own token; falling moves pick the negative one
    flat = _receipt(_daily_flat_tail())
    assert flat["state"] == "qualified"
    assert flat["value"]["change"] == 0.0
    assert flat["value"]["direction"] == "unchanged"


def test_direction_tokens_by_source():
    for source_id, series in (("broad_dollar", _daily_rising()),
                              ("us_real_yield_10y", _daily_rising()),
                              ("em_corporate_oas", _daily_rising())):
        receipt = _receipt(series, source_id=source_id)
        assert receipt["state"] == "qualified", (source_id, receipt["abstain_reasons"])
        assert receipt["value"]["change"] > 0
    assert _receipt(_daily_rising())["value"]["direction"] == "dollar_stronger"
    assert _receipt(_daily_rising(), source_id="us_real_yield_10y")["value"]["direction"] == "real_yield_higher"
    assert _receipt(_daily_rising(), source_id="em_corporate_oas")["value"]["direction"] == "spread_wider"
    # a falling series picks the negative token of every family
    falling = _daily_rising().iloc[::-1]
    falling.index = _daily_rising().index  # same bday index, reversed values
    receipt = _receipt(falling, source_id="em_asia_corporate_oas")
    assert receipt["value"]["change"] < 0
    assert receipt["value"]["direction"] == "spread_narrower"


def test_level_change_sources_use_percentage_points():
    """us_real_yield_10y and every EM corporate OAS source inherit the GLT
    level_change transform: value.diff(13) in percentage points, never a log
    change; only broad_dollar is log_pct."""
    assert dc.source_spec("us_real_yield_10y")["change_transform"] == "level_change"
    for source_id in EM_OAS_SOURCE_IDS:
        assert dc.source_spec(source_id)["change_transform"] == "level_change"

    for source_id in ("us_real_yield_10y", "em_corporate_oas"):
        raw = _daily_walk(271828 + len(source_id))
        as_of = _as_of_for(raw)
        receipt = _receipt(raw, source_id=source_id)
        assert receipt["state"] == "qualified", receipt["abstain_reasons"]
        expected = _expected_weekly_log(raw, as_of, transform="level_change")
        value = receipt["value"]
        assert value["change_unit"] == "percentage_points"
        assert value["change"] == pytest.approx(expected["change"], abs=1e-9)
        assert value["z_prior"] == pytest.approx(expected["z"], abs=1e-9)
        assert value["prior_history_periods"] == len(expected["prior"])
        assert receipt["alignment"]["change_transform"] == "level_change"

    broad = _receipt(_daily_walk(20261021))
    assert broad["state"] == "qualified"
    assert broad["value"]["change_unit"] == "log_pct"


# --------------------------------------------------------------------------
# 4. rights variants


@pytest.mark.parametrize("rights_row", [
    None,
    {"id": "fixture.unresolved", "rights_class": "unresolved", "decision_ref": "x"},
    {"id": "fixture.internal", "rights_class": "internal_only", "decision_ref": "x"},
    {"id": "fixture.blank", "rights_class": "derived_display_ok", "decision_ref": "  "},
])
def test_rights_variants_abstain(rights_row):
    receipt = _receipt(_daily_walk(7), rights_row=rights_row)
    assert receipt["state"] == "abstain"
    assert receipt["abstain_reasons"] == ["rights_unconfirmed"]
    assert receipt["value"] is None


# --------------------------------------------------------------------------
# 5. data-state variants


def test_stale_input():
    raw = _daily_walk(11)
    as_of = raw.index[-1] + pd.Timedelta(days=45)  # >> stale_after_calendar_days
    as_of = _friday_on_or_after(as_of)
    receipt = _receipt(raw, as_of=as_of)
    assert receipt["state"] == "abstain"
    assert receipt["abstain_reasons"] == ["stale_input"]
    assert receipt["value"] is None
    assert receipt["clocks"]["observation"]["at"] is not None


def test_insufficient_history():
    short = _daily_walk(13, periods=60)  # ~12 weekly changes only
    receipt = _receipt(short)
    assert receipt["state"] == "abstain"
    assert receipt["abstain_reasons"] == ["insufficient_history"]
    assert receipt["value"] is None


def test_value_unavailable_none_and_empty():
    for raw in (None, pd.Series(dtype=float)):
        receipt = _receipt(raw)
        assert receipt["state"] == "abstain"
        assert receipt["abstain_reasons"] == ["clock_missing", "value_unavailable"]
        assert receipt["value"] is None
        assert receipt["clocks"]["observation"]["at"] is None
        assert receipt["clocks"]["source_publication"]["at"] is None


# --------------------------------------------------------------------------
# 6. point-in-time stability


def test_point_in_time_production_receipts():
    raw = _daily_walk(20261021)
    as_of = _as_of_for(raw) - pd.Timedelta(weeks=30)  # a Friday well inside
    frames = {("fred", "DTWEXBGS"): raw.to_frame("broad_dollar")}

    def read(group, key):
        return frames.get((group, key))

    kwargs = dict(as_of=as_of, ingested_at="2026-12-31T23:00:00",
                  computed_at="2026-12-31T23:30:00",
                  rights_rows={"broad_dollar": RIGHTS_ROW_OK})
    before = dc.production_receipts(read=read, **kwargs)
    assert before["broad_dollar"]["state"] == "qualified"

    rng = random.Random(99)
    tail_index = pd.bdate_range(raw.index[-1] + pd.Timedelta(days=1), periods=20)
    tail = raw.iloc[-1] * (1.0 + pd.Series([rng.gauss(0, 0.01) for _ in range(20)]).cumsum())
    tail.index = tail_index
    appended = raw.to_frame("broad_dollar")
    frames[("fred", "DTWEXBGS")] = pd.concat([appended, tail.to_frame("broad_dollar")])

    after = dc.production_receipts(read=read, **kwargs)
    assert after == before, "rows dated after as_of must not change any receipt field"


# --------------------------------------------------------------------------
# 7. clock variants


def test_clock_missing_and_order_violation():
    raw = _daily_walk(3)
    missing = _receipt(raw, ingested_at=None)
    assert missing["state"] == "abstain"
    assert missing["abstain_reasons"] == ["clock_missing"]
    reordered = _receipt(raw, ingested_at="2026-12-31T23:00:00",
                         computed_at="2026-12-30T23:30:00")
    assert reordered["state"] == "abstain"
    assert reordered["abstain_reasons"] == ["clock_order_violation"]


def test_receipt_id_ignores_ingestion_and_computation_clocks():
    """receipt_id hashes only the frozen identity fields; the ingestion and
    computation clocks never enter it (they may move freely after the fact
    without minting a new id)."""
    raw = _daily_walk(4242)
    a = _receipt(raw, ingested_at="2026-12-31T23:00:00",
                 computed_at="2026-12-31T23:30:00")
    b = _receipt(raw, ingested_at="2027-01-05T10:00:00",
                 computed_at="2027-01-05T11:00:00")
    assert a["state"] == "qualified" and b["state"] == "qualified"
    assert a["clocks"]["ingestion"]["at"] != b["clocks"]["ingestion"]["at"]
    assert a["clocks"]["computation"]["at"] != b["clocks"]["computation"]["at"]
    assert a["receipt_id"] == b["receipt_id"], \
        "receipt_id must not depend on ingested_at or computed_at"

    # independent recomputation of the id from the frozen identity: the
    # observation clock is the reference date carried at the last Friday,
    # i.e. the last observation at least one business day before it.
    as_of = _as_of_for(raw)
    grid = pd.date_range(raw.index.min(), as_of, freq="W-FRI")
    eligible = raw.index[raw.index <= grid[-1] - pd.offsets.BDay(1)]
    identity = {
        "contract_version": "intl-global-dollar-credit-v1",
        "source_id": "broad_dollar",
        "series_id": "DTWEXBGS",
        "as_of": pd.Timestamp(as_of).strftime("%Y-%m-%d"),
        "observation_at": eligible[-1].strftime("%Y-%m-%d"),
        "evidence_ref": "fixture:synthetic",
    }
    assert identity["observation_at"] == a["clocks"]["observation"]["at"]
    expected_id = "dc:sha256:" + hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":"))
        .encode("utf-8")).hexdigest()
    assert a["receipt_id"] == expected_id

    # positive control: evidence_ref is inside the hashed identity
    c = _receipt(raw, evidence_ref="fixture:other")
    assert c["state"] == "qualified"
    assert c["receipt_id"] != a["receipt_id"]


# --------------------------------------------------------------------------
# 8. real repo data (committed parquets; full CI checkout sees them)


def test_production_receipts_real_store():
    frame = pd.read_parquet("data/fred/DTWEXBGS.parquet")
    as_of = frame.index.max()
    receipts = dc.production_receipts(
        as_of=as_of, ingested_at="2026-12-31T23:00:00",
        computed_at="2026-12-31T23:30:00")
    assert list(receipts) == list(dc.SOURCES)
    for source_id, receipt in receipts.items():
        assert receipt["state"] == "abstain"
        assert "rights_unconfirmed" in receipt["abstain_reasons"]
        assert receipt["rights"] == {"rights_ref": None, "rights_class": None,
                                     "decision_ref": None}
        path = Path("data/fred") / f"{dc.SOURCES[source_id]['series_id']}.parquet"
        if not path.exists():
            assert "value_unavailable" in receipt["abstain_reasons"]
        else:
            assert receipt["abstain_reasons"] == ["rights_unconfirmed"], source_id
            assert receipt["evidence_ref"].startswith(
                f"fred/{dc.SOURCES[source_id]['key']}:sha256:")


def test_real_dollar_series_qualified_with_fixture_row():
    frame = pd.read_parquet("data/fred/DTWEXBGS.parquet")
    as_of = frame.index.max()
    receipts = dc.production_receipts(
        as_of=as_of, ingested_at="2026-12-31T23:00:00",
        computed_at="2026-12-31T23:30:00",
        rights_rows={"broad_dollar": RIGHTS_ROW_OK})
    receipt = receipts["broad_dollar"]
    assert receipt["state"] == "qualified", receipt["abstain_reasons"]
    assert receipt["value"]["change_periods"] == 13
    assert receipt["value"]["direction"] in ("dollar_stronger", "dollar_weaker", "unchanged")
    assert receipt["receipt_id"].startswith("dc:sha256:")


# --------------------------------------------------------------------------
# 9. jurisdiction assessments on the frozen universe


def test_jurisdiction_assessments_universe():
    universe = load_universe()
    out = dc.jurisdiction_assessments(universe)
    assert set(out) == {"contract_version", "claims"}
    assert out["contract_version"] == dc.CONTRACT_VERSION
    claims = out["claims"]
    assert set(claims) == {"dollar_funding", "em_credit_sovereign"}

    ids = sorted(universe["jurisdictions"])
    assert len(ids) == 63
    for claim, capability in dc.ASSESSMENT_CLAIMS.items():
        block = claims[claim]
        assert block["capability"] == capability
        assert sorted(block["jurisdictions"]) == ids
        for assessment in block["jurisdictions"].values():
            assert assessment["state"] == "abstain"
            assert assessment["value"] is None
            assert assessment["claim_level"] == "jurisdiction"
            assert assessment["claim"] == claim
            assert assessment["capability"] == capability
            assert assessment["global_context_ref"] is None
            assert assessment["regional_context_refs"] == []
        assert block["counts_by_state"] == {"abstain": 63}
        assert sum(block["counts_by_reason"].values()) == 63

    funding = claims["dollar_funding"]
    assert funding["counts_by_reason"] == {"no_admitted_source": 63}

    credit = claims["em_credit_sovereign"]
    expected_no_source = sorted(
        jid for jid in ids
        if universe["jurisdictions"][jid]["capabilities"]["local_rates_credit"]["state"] == "unavailable")
    expected_partial = sorted(set(ids) - set(expected_no_source))
    assert expected_partial == ["AU", "GB", "IN", "JP", "KR"]
    assert credit["counts_by_reason"] == {
        "no_admitted_source": 58, "capability_not_qualified": 5}
    assert len(expected_no_source) == 58 and len(expected_partial) == 5
    for jid in expected_partial:
        entry = universe["jurisdictions"][jid]["capabilities"]["local_rates_credit"]
        assessment = credit["jurisdictions"][jid]
        assert assessment["abstain_reasons"] == ["capability_not_qualified"]
        assert assessment["capability_state"] == entry["state"]
        assert assessment["capability_reason"] == entry["reason"] == "fred_10y_only_no_curve_or_credit"
    for jid in expected_no_source:
        assert credit["jurisdictions"][jid]["abstain_reasons"] == ["no_admitted_source"]


# --------------------------------------------------------------------------
# 10. dollar-risk counterexample: spot FX never changes a funding assessment


def test_fx_observation_never_upgrades_funding():
    out = dc.jurisdiction_assessments(
        load_universe(),
        fx_observations={"KR": {"fx_pct": 0.0}, "IN": {"fx_pct": -15.0}})
    funding = out["claims"]["dollar_funding"]["jurisdictions"]
    kr, ind = funding["KR"], funding["IN"]
    assert kr["abstain_reasons"] == ["funding_observation_unavailable", "no_admitted_source"]
    assert ind["abstain_reasons"] == ["funding_observation_unavailable", "no_admitted_source"]
    assert kr["state"] == "abstain" and ind["state"] == "abstain"
    kr_copy = dict(kr, jurisdiction="KR")
    in_copy = dict(ind, jurisdiction="KR")
    assert kr_copy == in_copy, "a flat peg and a -15% move must assess identically"
    # the em_credit claim is untouched by FX observations
    credit = out["claims"]["em_credit_sovereign"]["jurisdictions"]
    assert credit["KR"]["abstain_reasons"] == ["capability_not_qualified"]
    assert credit["IN"]["abstain_reasons"] == ["capability_not_qualified"]


# --------------------------------------------------------------------------
# 11. context receipts never upgrade a jurisdiction assessment


def _qualified_receipts_for_all_sources():
    receipts = {}
    rising = _daily_rising()
    for source_id in dc.SOURCES:
        receipts[source_id] = _receipt(rising, source_id=source_id)
        assert receipts[source_id]["state"] == "qualified", source_id
    return receipts


def test_context_receipts_never_upgrade():
    qualified = _qualified_receipts_for_all_sources()
    out = dc.jurisdiction_assessments(
        load_universe(),
        broad_dollar=qualified["broad_dollar"],
        em_credit_receipts={sid: qualified[sid] for sid in EM_OAS_SOURCE_IDS})
    em_ids = [qualified[sid]["receipt_id"] for sid in EM_OAS_SOURCE_IDS]
    for claim in out["claims"]:
        for jid, assessment in out["claims"][claim]["jurisdictions"].items():
            assert assessment["state"] == "abstain"
            assert assessment["value"] is None
            assert assessment["global_context_ref"] == qualified["broad_dollar"]["receipt_id"]
            if claim == "em_credit_sovereign":
                assert "proxy_population_mismatch" in assessment["abstain_reasons"]
                assert assessment["regional_context_refs"] == sorted(em_ids)
            else:
                assert "proxy_population_mismatch" not in assessment["abstain_reasons"]
                assert assessment["regional_context_refs"] == []
    funding = out["claims"]["dollar_funding"]
    assert funding["counts_by_reason"] == {"no_admitted_source": 63}
    credit = out["claims"]["em_credit_sovereign"]
    assert credit["counts_by_reason"] == {
        "no_admitted_source": 58,
        "capability_not_qualified": 5,
        "proxy_population_mismatch": 63}


# --------------------------------------------------------------------------
# 12. a qualified capability still abstains (no jurisdiction measure in v1)


def test_qualified_capability_still_abstains():
    universe = copy.deepcopy(load_universe())
    universe["jurisdictions"]["BR"]["capabilities"]["dollar_funding_external"] = {
        "state": "qualified", "reason": "fixture_qualified_probe",
        "evidence_ref": "fixture", "rights_ref": None}
    out = dc.jurisdiction_assessments(universe)
    assessment = out["claims"]["dollar_funding"]["jurisdictions"]["BR"]
    assert assessment["abstain_reasons"] == ["value_unavailable"]
    assert assessment["state"] == "abstain"
    assert assessment["value"] is None
    assert out["claims"]["dollar_funding"]["counts_by_reason"] == {
        "no_admitted_source": 62, "value_unavailable": 1}


# --------------------------------------------------------------------------
# 13. closed vocabulary, invariance, no contagion import


def _banned_hits(text: str):
    hits = []
    for token in dc.BANNED_TOKENS:
        if __import__("re").search(
                rf"(?<![A-Za-z0-9_]){token}(?![A-Za-z0-9_])", text):
            hits.append(token)
    return hits


def test_closed_vocabulary_and_invariance():
    universe = load_universe()
    universe_before = copy.deepcopy(universe)
    qualified = _qualified_receipts_for_all_sources()
    abstain = dc.production_receipts(
        as_of="2026-12-31", ingested_at="2026-12-31T23:00:00",
        computed_at="2026-12-31T23:30:00")
    assessments = dc.jurisdiction_assessments(
        universe, fx_observations={"KR": {"fx_pct": 0.0}},
        broad_dollar=qualified["broad_dollar"],
        em_credit_receipts={"em_corporate_oas": qualified["em_corporate_oas"]})

    payloads = list(qualified.values()) + list(abstain.values()) + [assessments]
    for payload in payloads:
        for reason in _reasons_of(payload):
            assert reason in dc.ABSTAIN_REASONS, reason
        assert not _banned_hits(json.dumps(payload, default=str)), \
            f"banned token in output: {_banned_hits(json.dumps(payload, default=str))}"

    assert universe == universe_before, "inputs must not be mutated"

    config_hashes = {
        path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
        for path in ("config/intl_global_universe_v1.json",
                     "config/intl_source_rights_matrix_v1.json")}
    dc.jurisdiction_assessments(load_universe())
    dc.production_receipts(as_of="2026-12-31", ingested_at="2026-12-31T23:00:00",
                           computed_at="2026-12-31T23:30:00")
    for path, digest in config_hashes.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest


def _reasons_of(payload):
    if isinstance(payload, dict):
        if "abstain_reasons" in payload and isinstance(payload["abstain_reasons"], list):
            yield from payload["abstain_reasons"]
        for value in payload.values():
            yield from _reasons_of(value)
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            yield from _reasons_of(item)


def test_no_contagion_import_anywhere():
    import engine.intl_global_acceptance_matrix as am
    for module in (dc, am):
        tree = ast.parse(Path(module.__file__).read_text())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            for name in names:
                assert not name.startswith("engine.contagion"), \
                    f"{module.__name__} must never import the frozen contagion stack"
