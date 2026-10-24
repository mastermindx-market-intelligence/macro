"""Opt-in NDX/NDXP family: never cross-join AM/PM contract identities."""
from __future__ import annotations

import math

import pandas as pd
import pytest

from engine.index_options_family import (
    FamilySourceUnavailable, build_ndx_family_gex, qualify_ndx_family,
)


ASOF = "2026-10-23"
EXP = "2026-11-20"
SPOT = 20000.0


def _row(root: str, *, gamma=0.004, oi=100, right="C", date=ASOF,
         expiration=EXP, strike=20000, spot=SPOT, iv=0.25):
    greek = {
        "date": date, "expiration": expiration, "strike": strike, "right": right,
        "gamma": gamma, "underlying_price": spot, "implied_vol": iv,
        "delta": 0.5, "vanna": 0.0, "charm": 0.0,
    }
    open_interest = {
        "date": date, "expiration": expiration, "strike": strike,
        "right": right, "open_interest": oi,
    }
    return pd.DataFrame([greek]), pd.DataFrame([open_interest])


def _both(**kw):
    return {"NDX": _row("NDX"), "NDXP": _row("NDXP", gamma=0.010, oi=5, **kw)}


def test_identical_visible_strike_expiry_side_remain_distinct_am_pm_contracts():
    raw = _both()
    qualified = qualify_ndx_family(raw, ASOF)
    assert qualified.root_contract_counts == {"NDX": 1, "NDXP": 1}
    assert qualified.shared_strike_expiry_side_keys == 1
    assert list(qualified.greeks["contract_root"]) == ["NDX", "NDXP"]
    assert not any("contract_root" in frame.columns for pair in raw.values() for frame in pair)
    result = build_ndx_family_gex(raw, ASOF)
    assert result["root"] == "NDX"
    # One ROOT-AWARE join, not the four matches of a root-blind Cartesian product.
    # The formula matches the incumbent engine/exposure_math dealer_exposures.
    expected = (0.004 * 100 + 0.010 * 5) * 100 * SPOT**2 * 0.01 / 1e9
    assert result["net_gex_bn"] == pytest.approx(expected, abs=0.0001)
    assert result["coverage"]["n_contracts"] == 2
    metadata = result["family_source"]
    assert metadata["source_roots"] == ["NDX", "NDXP"]
    assert metadata["historical_first_available_at"] is None
    assert metadata["redistribution_grant"] is None
    assert metadata["complete_chain_receipt"] is False
    assert metadata["state"] == "OFFLINE_SOURCE_QUALIFIED_NOT_PUBLISHABLE"


def test_distinct_expiries_are_not_deleted_to_force_overlap():
    raw = {"NDX": _row("NDX", expiration="2026-11-20"),
           "NDXP": _row("NDXP", expiration="2026-10-23", gamma=0.001)}
    result = build_ndx_family_gex(raw, ASOF)
    assert result["coverage"]["n_contracts"] == 2
    assert result["family_source"]["shared_strike_expiry_side_keys"] == 0
    assert {x["exp"] for x in result["by_expiry"]} == {"2026-10-23", "2026-11-20"}


@pytest.mark.parametrize("root", ["NDX", "NDXP"])
@pytest.mark.parametrize("part", [0, 1])
def test_no_source_leg_means_no_family_output(root, part):
    raw = _both()
    bad = list(raw[root])
    bad[part] = pd.DataFrame()
    raw[root] = tuple(bad)
    with pytest.raises(FamilySourceUnavailable, match="absent"):
        build_ndx_family_gex(raw, ASOF)


def test_unqualified_missing_family_root_refuses():
    with pytest.raises(FamilySourceUnavailable, match="BOTH"):
        qualify_ndx_family({"NDX": _row("NDX")}, ASOF)


@pytest.mark.parametrize("part,field,value,match", [
    (0, "gamma", None, "unknown gamma"),
    (0, "gamma", float("nan"), "unknown gamma"),
    (0, "gamma", -1, "unknown gamma"),
    (0, "underlying_price", None, "spot missing"),
    (0, "underlying_price", 24000, "spot bases differ"),
    (0, "implied_vol", 0.0001, "degenerate IV"),
    (0, "strike", 0, "invalid strike"),
    (0, "right", "bad", "unrecognized option side"),
    (0, "date", "2026-10-22", "cross-session"),
    (0, "expiration", "2026-10-22", "expired option"),
    (1, "open_interest", None, "unknown open_interest"),
    (1, "open_interest", -4, "unknown open_interest"),
    (1, "date", "2026-10-22", "cross-session"),
])
def test_bad_or_missing_family_observations_fail_closed(part, field, value, match):
    raw = _both()
    frame = raw["NDXP"][part].copy()
    frame.loc[0, field] = value
    values = list(raw["NDXP"])
    values[part] = frame
    raw["NDXP"] = tuple(values)
    with pytest.raises(FamilySourceUnavailable, match=match):
        qualify_ndx_family(raw, ASOF)


def test_missing_contract_side_cannot_be_treated_as_zero():
    raw = _both()
    greek, oi = raw["NDXP"]
    greek.loc[0, "right"] = "P"
    raw["NDXP"] = (greek, oi)
    with pytest.raises(FamilySourceUnavailable, match="contract mismatch"):
        qualify_ndx_family(raw, ASOF)


def test_duplicates_and_cross_root_source_identity_refuse():
    raw = _both()
    g, oi = raw["NDXP"]
    raw["NDXP"] = (pd.concat([g, g], ignore_index=True), oi)
    with pytest.raises(FamilySourceUnavailable, match="duplicate"):
        qualify_ndx_family(raw, ASOF)
    raw = _both()
    g, oi = raw["NDXP"]
    g["contract_root"] = "NDX"
    raw["NDXP"] = (g, oi)
    with pytest.raises(FamilySourceUnavailable, match="foreign contract identity"):
        qualify_ndx_family(raw, ASOF)


def test_observed_zero_oi_is_not_null_and_does_not_inflate_exposure():
    raw = {"NDX": _row("NDX"), "NDXP": _row("NDXP", gamma=0.0, oi=0)}
    qualified = qualify_ndx_family(raw, ASOF)
    assert qualified.root_contract_counts == {"NDX": 1, "NDXP": 1}
    result = build_ndx_family_gex(raw, ASOF)
    assert result["family_source"]["root_contract_counts"]["NDXP"] == 1
    assert result["coverage"]["n_contracts"] == 1
    assert math.isfinite(result["net_gex_bn"])


def test_missing_quote_does_not_go_to_bs_or_zero():
    raw = _both()
    greek, oi = raw["NDXP"]
    greek.loc[0, "gamma"] = float("nan")
    raw["NDXP"] = (greek, oi)
    with pytest.raises(FamilySourceUnavailable, match="unknown gamma"):
        build_ndx_family_gex(raw, ASOF)
