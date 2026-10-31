"""Composer tests for the US liquidity_central_banks workspace (F01 / R3).

RED-first: each degraded condition must produce the correct TYPED state and
never a zero / neutral / calm default. Covers: the NOT_APPLICABLE headline
shape (this workspace has no headline model at all in architecture 10.9 -
see liquidity_central_banks.py's module docstring), the W-FRI weekly-grid
freshness law (CURRENT/LATE_WITHIN_TOLERANCE/STALE_SOURCE boundaries), the
disclosed WALCL units defect (sanity check -> typed SOURCE_FAILED, never
rescaled), the 52-week monetary_impulse_z warmup, the owner's quality-
degraded no-look-ahead passthrough, the global-state-vs-Fed-desk
contradiction (fires / stays silent), digest determinism with a genuinely-
consumed-field mutation and an unconsumed-field negative control, a prose
scan for raw enum-token leaks, zh-narrative integrity, schema validation,
and a real-owner-artifact build across the two owner inputs (GLT + cb_desk).

    python3 -m pytest tests/test_macro_workspace_liquidity_central_banks.py -x -q
"""
from __future__ import annotations

import copy
import datetime as _dt
import json
import re
import sys
from pathlib import Path
from typing import Mapping

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.market_os.macro_workspaces import contract, liquidity_central_banks  # noqa: E402

BUILT_AT = "2026-09-04T00:00:00Z"
GLT_LATEST = ROOT / "site" / "liquiditydata" / "global_liquidity_transmission.json"
INTL_RISK_LATEST = ROOT / "data" / "intl_risk" / "latest.json"
GLT_HISTORY_META = ROOT / "data" / "global_liquidity_transmission" / "state_history_meta.json"

# GLT T21: BASE metric count for the closed LCB composer (asserted in (j)).
BASE_LCB_METRIC_COUNT = 28

# GLT T21: the strict-snake tokens DISTINCT in the rendered LCB page text at
# BASE = e38026e9f4e964d3d2efb77d6f5baa136e247b26. The T21 per-leg source rows
# repeat the same site/liquiditydata/global_liquidity_transmission.json path
# in the Sources details bucket, so per-bucket counts rise but no NEW
# identifier may appear (frozen spec S9 (f) reasoning).
_T21_BASELINE_STRICT_TOKENS: tuple[str, ...] = ()

# GLT T21: baseline ``find_violations`` violations on the rendered LCB page
# at BASE = e38026e9f4e964d3d2efb77d6f5baa136e247b26 (STEP 1b). None at BASE.
_BASELINE_VIOLATIONS: tuple[str, ...] = ()
_BASELINE_VIOLATION_COUNT = len(_BASELINE_VIOLATIONS)


# --------------------------------------------------------------------------- #
# fixtures (trimmed, representative subsets of the real owner artifacts)
# --------------------------------------------------------------------------- #
def _base_glt() -> dict:
    return {
        "meta": {
            "schema": "global_liquidity_transmission.v1",
            "model_version": "glt_state.v1",
            "producer_version": "w-liq.1.0",
            "owner": "Macro/Data Producer W-LIQ.1",
            "frequency": "W-FRI",
            "generated_at": "2026-09-04T11:03:41.497178+00:00",
            "architecture_authority": "Mastermind issue #117; orchestration and acceptance authority Mastermind issue #123",
        },
        "freshness": {
            "status": "fresh",
            "degraded": False,
            "monetary_coverage_ratio": 1.0,
            "funding_coverage_ratio": 1.0,
            "clocks": {
                "evidence_available_at": "2026-08-28T00:00:00Z",
                "first_known_at": "2026-09-04T11:03:41.497178Z",
            },
            "component_snapshot": {
                "monetary": {
                    "fed": {"current_contribution_z": 0.970391},
                    "ecb": {"current_contribution_z": 1.008565},
                    "boj": {"current_contribution_z": 0.850842},
                },
                "usd_funding": {
                    "broad_dollar": {"current_contribution_z": 0.261985},
                    "high_yield_oas": {"current_contribution_z": 0.05906},
                    "real_yield_10y": {"current_contribution_z": -0.755348},
                },
            },
            "components": {
                "monetary": {
                    "fed": {"status": "usable"},
                    "ecb": {"status": "usable"},
                    "boj": {"status": "usable"},
                },
                "usd_funding": {
                    "broad_dollar": {"status": "usable"},
                    "high_yield_oas": {"status": "usable"},
                    "real_yield_10y": {"status": "usable"},
                },
            },
        },
        "quality": {
            "status": "degraded",
            "degraded": True,
            "event_quality": "mixed",
            "missing_or_stale": [],
            "confidence": {
                "kind": "data_lineage_and_coverage_only",
                "value": 0.833333,
                "not": ["predictive_probability", "alpha_confidence", "promotion_grade"],
            },
            "global_credit": {
                "status": "insufficient_comparable_pit_coverage",
                "reason": "US C&I loans and China TSF are different constructs.",
                "credit_impulse_global": None,
                "components": {
                    "china_total_social_financing": {"direction": "weakening", "status": "context_only"},
                    "us_bank_credit": {"direction": "improving", "status": "context_only"},
                },
            },
            "us_liquidity_quality": None,
        },
        "state": {
            "asof": "2026-08-28",
            "label": "flat",
            "monetary_impulse": 0.003956,
            "monetary_impulse_z": 0.077032,
            "monetary_stance": 0.943266,
            "orthogonalised_impulse": 0.0165,
            "liquidity_breadth": 0.333333,
            "usd_funding_impulse": -0.144768,
            "policy_liquidity_impulse": 0.003956,
            "credit_impulse_global": None,
            "event_reference": {
                "quality": "mixed",
                "confidence": 0.833333,
                "conditions": {"us_liquidity_quality": "unknown", "usd_funding_impulse": -0.144768},
            },
        },
    }


def _base_cb_desk() -> dict:
    return {
        "as_of": "2026-09-03",
        "built": "2026-09-04T12:23:01.174224+00:00",
        "cbs": [
            {"id": "FED", "policy_rate": 3.63, "asof": "2026-09-02", "stale": False,
             "last_change": {"date": "2026-05-07", "direction": "cut", "bp": -1.0},
             "bs_impulse": {"impulse_13w": 0.38, "impulse_52w": 2.05, "level": 6737204.0,
                            "asof": "2026-09-02",
                            "unit": "USD billions (×1, raw WALCL is in billions)",
                            "series": "WALCL"}},
            {"id": "ECB", "policy_rate": 2.25, "asof": "2026-09-03", "stale": False,
             "last_change": {"date": "2026-06-17", "direction": "hike", "bp": 25.0},
             "bs_impulse": {"impulse_13w": -4.0, "impulse_52w": -2.86, "level": 5915343.0,
                            "asof": "2026-08-28", "unit": "EUR billions", "series": "ECBASSETSW"}},
            {"id": "BOJ", "policy_rate": 0.841, "asof": "2026-06-01", "stale": True,
             "last_change": {"date": "2026-06-01", "direction": "hike", "bp": 11.4},
             "bs_impulse": {"impulse_13w": -10.64, "impulse_52w": -12.73, "level": 6446620.0,
                            "asof": "2026-08-01", "unit": "JPY trillions", "series": "JPNASSETS"}},
        ],
    }


def _base_hist() -> dict:
    return {
        "artifact": "data/global_liquidity_transmission/state_history.parquet",
        "rows": 1483,
        "first_asof": "1998-04-03",
        "last_asof": "2026-08-28",
    }


def _compose(glt=None, cbd=None, hist=None, **kw) -> dict:
    return liquidity_central_banks.compose(
        glt if glt is not None else _base_glt(),
        cbd if cbd is not None else _base_cb_desk(),
        hist if hist is not None else _base_hist(),
        built_at=BUILT_AT, **kw,
    )


def _metric(snapshot: dict, metric_id: str) -> dict:
    return next(m for m in snapshot["metrics"]["items"] if m["metric_id"] == metric_id)


def _required(snapshot: dict, cid: str) -> dict:
    return next(c for c in snapshot["availability"]["required"] if c["component_id"] == cid)


# --------------------------------------------------------------------------- #
# healthy baseline (mirrors the REAL owner artifacts: quality.degraded=True
# from global_credit context, WALCL units defect present, GLT label="flat" so
# no Fed-desk contradiction fires)
# --------------------------------------------------------------------------- #
def test_baseline_all_required_sources_current() -> None:
    snap = _compose()
    assert snap["workspace"]["id"] == "liquidity_central_banks"
    assert snap["region"]["code"] == "US"
    for cid in ("glt_monetary_impulse", "glt_liquidity_breadth",
                "glt_usd_funding_impulse", "cb_fed_balance_sheet_impulse_13w"):
        r = _required(snap, cid)
        assert r["freshness"] == "CURRENT", (cid, r)
        assert r["status"] == "PRESENT"
    assert snap["availability"]["state"] == "CURRENT"


def test_baseline_no_contradiction_when_glt_reads_flat() -> None:
    snap = _compose()
    c = snap["availability"]["contradiction"]
    assert c["present"] is False
    assert c["kind"] is None


def test_baseline_quality_degraded_reason_surfaces_despite_current_freshness() -> None:
    # quality.status=="degraded" (owner-level, driven by global_credit context)
    # is a DIFFERENT signal from freshness.status=="fresh" -- the required
    # components can legitimately read CURRENT while this diagnostic reason
    # is still honestly surfaced (never smoothed over).
    snap = _compose()
    assert any(r.startswith("glt_quality_status=degraded") for r in snap["availability"]["reasons"])
    assert any(i["implication_id"] == "glt_quality_degraded_passthrough"
               for i in snap["implications"]["items"])


def test_baseline_walcl_defect_fires_by_default() -> None:
    # The real cb_desk artifact's FED bs_impulse carries the disclosed units
    # defect (level in millions, labeled "USD billions") -- the baseline
    # fixture mirrors that, so this fires without any special setup.
    snap = _compose()
    m = _metric(snap, "cb_fed_balance_sheet_level")
    assert m["value"] is None
    assert m["status"] == "ABSENT"
    assert m["null_reason"] == "SOURCE_FAILED"
    assert "implausible" in m["transformation"]
    assert any(i["implication_id"] == "fed_balance_sheet_level_unit_defect"
               for i in snap["implications"]["items"])
    # the unit-free 13w/52w legs are unaffected
    m13 = _metric(snap, "cb_fed_balance_sheet_impulse_13w")
    assert m13["value"] == 0.38
    assert m13["status"] == "PRESENT"


# --------------------------------------------------------------------------- #
# NOT_APPLICABLE headline / empty axes (this workspace has no headline model)
# --------------------------------------------------------------------------- #
def test_headline_is_not_applicable_by_design() -> None:
    snap = _compose()
    h = snap["headline"]
    assert h["state_id"] is None
    assert h["status"] == "ABSENT"
    assert h["null_reason"] == "NOT_APPLICABLE"
    assert h["quadrant"] == {"x": None, "y": None, "x_status": "ABSENT", "y_status": "ABSENT"}
    assert h["nearest_boundary"]["null_reason"] == "NOT_APPLICABLE"
    assert h["one_month_vector"]["null_reason"] == "NOT_APPLICABLE"
    assert h["hysteresis"]["applied"] is False
    assert "no headline model at all" in h["hysteresis"]["note"]


def test_axes_items_is_empty_by_design() -> None:
    snap = _compose()
    assert snap["axes"]["items"] == []


# --------------------------------------------------------------------------- #
# typed degraded states (never zero / neutral / calm)
# --------------------------------------------------------------------------- #
def test_missing_glt_artifact_is_typed_source_failed() -> None:
    snap = _compose(glt={})
    r = _required(snap, "glt_monetary_impulse")
    assert r["freshness"] == "SOURCE_FAILED"
    assert r["status"] == "ABSENT"
    assert r["null_reason"] == "SOURCE_FAILED"
    assert snap["availability"]["state"] == "SOURCE_FAILED"
    m = _metric(snap, "glt_monetary_impulse")
    assert m["value"] is None and m["status"] == "ABSENT"


def test_missing_cb_desk_artifact_is_typed_source_failed() -> None:
    snap = _compose(cbd={})
    r = _required(snap, "cb_fed_balance_sheet_impulse_13w")
    assert r["freshness"] == "SOURCE_FAILED"
    assert r["status"] == "ABSENT"
    m = _metric(snap, "cb_fed_balance_sheet_level")
    assert m["value"] is None
    assert "No balance-sheet data reported for FED" in m["transformation"]


def test_missing_fed_row_is_typed_source_failed() -> None:
    cbd = copy.deepcopy(_base_cb_desk())
    cbd["cbs"] = [c for c in cbd["cbs"] if c["id"] != "FED"]
    snap = _compose(cbd=cbd)
    r = _required(snap, "cb_fed_balance_sheet_impulse_13w")
    assert r["freshness"] == "SOURCE_FAILED"
    assert r["status"] == "ABSENT"
    assert r["null_reason"] == "SOURCE_FAILED"
    assert "cb_fed_balance_sheet_impulse_13w" in snap["availability"]["degraded"]


def test_missing_liquidity_breadth_is_typed_source_failed_without_affecting_siblings() -> None:
    glt = copy.deepcopy(_base_glt())
    glt["state"]["liquidity_breadth"] = None
    snap = _compose(glt=glt)
    r = _required(snap, "glt_liquidity_breadth")
    assert r["freshness"] == "SOURCE_FAILED"
    assert r["status"] == "ABSENT"
    # sibling required components (from the SAME owner state object) are
    # unaffected -- freshness must reflect THIS field's own presence only.
    r2 = _required(snap, "glt_monetary_impulse")
    assert r2["status"] == "PRESENT"
    assert r2["freshness"] == "CURRENT"


def test_missing_usd_funding_impulse_is_typed_source_failed() -> None:
    glt = copy.deepcopy(_base_glt())
    glt["state"]["usd_funding_impulse"] = None
    snap = _compose(glt=glt)
    r = _required(snap, "glt_usd_funding_impulse")
    assert r["freshness"] == "SOURCE_FAILED"
    m = _metric(snap, "glt_usd_funding_impulse")
    assert m["value"] is None and m["status"] == "ABSENT"


def test_credit_impulse_global_is_refused_not_covered() -> None:
    snap = _compose()
    m = _metric(snap, "glt_credit_impulse_global")
    assert m["value"] is None
    assert m["status"] == "ABSENT"
    assert m["null_reason"] == "NOT_COVERED"
    assert "insufficient_comparable_pit_coverage" in m["transformation"]


# --------------------------------------------------------------------------- #
# owner "unusable" per-leg receipt is typed stale, never date-math CURRENT
# --------------------------------------------------------------------------- #
def test_owner_unusable_leg_receipt_downgrades_that_legs_freshness_only() -> None:
    glt = copy.deepcopy(_base_glt())
    glt["freshness"]["components"]["monetary"]["fed"]["status"] = "stale"
    snap = _compose(glt=glt)
    m = _metric(snap, "glt_fed_monetary_contribution_z")
    assert m["freshness"] == "STALE_SOURCE"
    # a sibling leg with a healthy receipt is unaffected
    m2 = _metric(snap, "glt_ecb_monetary_contribution_z")
    assert m2["freshness"] == "CURRENT"


def test_owner_freshness_degraded_flag_downgrades_required_components() -> None:
    glt = copy.deepcopy(_base_glt())
    glt["freshness"]["status"] = "degraded"
    glt["freshness"]["degraded"] = True
    snap = _compose(glt=glt)
    r = _required(snap, "glt_monetary_impulse")
    assert r["freshness"] == "STALE_SOURCE"
    assert r["freshness"] != "CURRENT"
    assert snap["availability"]["state"] != "CURRENT"


# --------------------------------------------------------------------------- #
# W-FRI weekly-grid release-lag law: CURRENT / LATE_WITHIN_TOLERANCE / STALE.
# BUILT_AT is held fixed (never overridden -- the composer never reads a wall
# clock) and glt.state.asof is varied instead, which has the identical effect
# on the computed age.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("glt_asof,expected", [
    ("2026-09-04", "CURRENT"),                # age 0
    ("2026-08-28", "CURRENT"),                 # age 7 (boundary)
    ("2026-08-27", "LATE_WITHIN_TOLERANCE"),   # age 8
    ("2026-08-24", "LATE_WITHIN_TOLERANCE"),   # age 11 (boundary)
    ("2026-08-23", "STALE_SOURCE"),            # age 12
])
def test_glt_wfri_freshness_tiers(glt_asof: str, expected: str) -> None:
    glt = copy.deepcopy(_base_glt())
    glt["state"]["asof"] = glt_asof
    snap = _compose(glt=glt)
    r = _required(snap, "glt_monetary_impulse")
    assert r["freshness"] == expected


def test_glt_asof_after_built_at_is_source_failed() -> None:
    glt = copy.deepcopy(_base_glt())
    glt["state"]["asof"] = "2026-09-05"  # AFTER BUILT_AT (2026-09-04)
    snap = _compose(glt=glt)
    r = _required(snap, "glt_monetary_impulse")
    assert r["freshness"] == "SOURCE_FAILED"


# --------------------------------------------------------------------------- #
# 52-week monetary_impulse_z warmup (raw present, standardized twin not yet)
# --------------------------------------------------------------------------- #
def test_monetary_impulse_z_warmup_is_typed_insufficient_history() -> None:
    glt = copy.deepcopy(_base_glt())
    glt["state"]["monetary_impulse_z"] = None
    snap = _compose(glt=glt)
    m = _metric(snap, "glt_monetary_impulse_z")
    assert m["value"] is None
    assert m["status"] == "ABSENT"
    assert m["null_reason"] == "INSUFFICIENT_HISTORY"
    # the raw twin is unaffected
    raw = _metric(snap, "glt_monetary_impulse")
    assert raw["value"] == pytest.approx(0.003956)
    assert raw["status"] == "PRESENT"


def test_monetary_impulse_z_present_reads_normally() -> None:
    snap = _compose()
    m = _metric(snap, "glt_monetary_impulse_z")
    assert m["value"] == pytest.approx(0.077032)
    assert m["status"] == "PRESENT"
    assert m["null_reason"] is None


# --------------------------------------------------------------------------- #
# WALCL units defect: sanity check, never rescaled
# --------------------------------------------------------------------------- #
def test_plausible_walcl_level_publishes_normally() -> None:
    cbd = copy.deepcopy(_base_cb_desk())
    cbd["cbs"][0]["bs_impulse"]["level"] = 6737.2  # plausible USD-billions scale
    snap = _compose(cbd=cbd)
    m = _metric(snap, "cb_fed_balance_sheet_level")
    assert m["value"] == 6737.2
    assert m["status"] == "PRESENT"
    assert "corrected by this composer" in m["transformation"]


def test_non_walcl_series_is_never_sanity_checked() -> None:
    # A hypothetically huge ECB level (same magnitude issue) is NOT
    # sanity-checked -- the disclosed defect is scoped to WALCL only.
    cbd = copy.deepcopy(_base_cb_desk())
    cbd["cbs"][1]["bs_impulse"]["level"] = 5915343.0  # already the baseline value
    snap = _compose(cbd=cbd)
    m = _metric(snap, "cb_ecb_balance_sheet_level")
    assert m["value"] == 5915343.0
    assert m["status"] == "PRESENT"


# --------------------------------------------------------------------------- #
# global-state-vs-Fed-desk contradiction: fires on genuine two-sided data,
# stays silent on one-sided / flat / missing data
# --------------------------------------------------------------------------- #
def test_contradiction_fires_when_glt_expanding_and_fed_contracting() -> None:
    glt = copy.deepcopy(_base_glt())
    glt["state"]["label"] = "expanding"
    cbd = copy.deepcopy(_base_cb_desk())
    cbd["cbs"][0]["bs_impulse"]["impulse_13w"] = -5.0  # decisively contracting
    snap = _compose(glt=glt, cbd=cbd)
    c = snap["availability"]["contradiction"]
    assert c["present"] is True
    assert c["kind"] == "global_state_vs_fed_desk"
    assert set(c["components"]) == {"glt_monetary_impulse", "cb_fed_balance_sheet_impulse_13w"}
    assert any("contradiction=global_state_vs_fed_desk" in r for r in snap["availability"]["reasons"])
    mi = _metric(snap, "glt_monetary_impulse")
    assert mi["status"] == "DISAGREEMENT"
    assert mi["value"] is not None  # typed disagreement, not censored
    fed13 = _metric(snap, "cb_fed_balance_sheet_impulse_13w")
    assert fed13["status"] == "DISAGREEMENT"
    assert any(i["implication_id"] == "contradiction_global_state_vs_fed_desk"
               for i in snap["implications"]["items"])


def test_contradiction_silent_when_glt_reads_flat() -> None:
    cbd = copy.deepcopy(_base_cb_desk())
    cbd["cbs"][0]["bs_impulse"]["impulse_13w"] = -5.0
    snap = _compose(cbd=cbd)  # baseline glt label stays "flat"
    assert snap["availability"]["contradiction"]["present"] is False
    fed13 = _metric(snap, "cb_fed_balance_sheet_impulse_13w")
    assert fed13["status"] == "PRESENT"


def test_contradiction_silent_when_both_sides_agree() -> None:
    glt = copy.deepcopy(_base_glt())
    glt["state"]["label"] = "expanding"
    cbd = copy.deepcopy(_base_cb_desk())
    cbd["cbs"][0]["bs_impulse"]["impulse_13w"] = 3.0  # also expanding
    snap = _compose(glt=glt, cbd=cbd)
    assert snap["availability"]["contradiction"]["present"] is False


def test_contradiction_silent_when_fed_leg_within_flat_band() -> None:
    glt = copy.deepcopy(_base_glt())
    glt["state"]["label"] = "expanding"
    cbd = copy.deepcopy(_base_cb_desk())
    cbd["cbs"][0]["bs_impulse"]["impulse_13w"] = 0.2  # inside the 0.5 flat band
    snap = _compose(glt=glt, cbd=cbd)
    assert snap["availability"]["contradiction"]["present"] is False


def test_contradiction_silent_when_fed_leg_missing() -> None:
    glt = copy.deepcopy(_base_glt())
    glt["state"]["label"] = "expanding"
    cbd = copy.deepcopy(_base_cb_desk())
    cbd["cbs"] = [c for c in cbd["cbs"] if c["id"] != "FED"]
    snap = _compose(glt=glt, cbd=cbd)
    assert snap["availability"]["contradiction"]["present"] is False


# --------------------------------------------------------------------------- #
# scope boundary: no TGA/RRP/reserves metric is fabricated by this composer
# --------------------------------------------------------------------------- #
def test_no_tga_rrp_reserves_metric_is_fabricated() -> None:
    snap = _compose()
    ids = {m["metric_id"] for m in snap["metrics"]["items"]}
    assert not any("tga" in mid or "rrp" in mid or "reserve" in mid for mid in ids)


def test_metric_ids_are_unique() -> None:
    snap = _compose()
    ids = [m["metric_id"] for m in snap["metrics"]["items"]]
    assert len(ids) == len(set(ids))
    assert len(ids) == 28


# --------------------------------------------------------------------------- #
# changes / method-version comparability
# --------------------------------------------------------------------------- #
def _prior(method=liquidity_central_banks.METHOD_VERSION, mi=0.001,
           gen="liquidity_central_banks-US-deadbeefdeadbeef") -> dict:
    prior = _compose()
    prior["headline"]["method_version"] = method
    prior["headline"]["effective_date"] = "2026-08-21"
    prior["generation"]["generation_id"] = gen
    for m in prior["metrics"]["items"]:
        if m["metric_id"] == "glt_monetary_impulse":
            m["value"] = mi
    return prior


def test_changes_no_prior_yields_warmup() -> None:
    snap = _compose()
    assert snap["changes"]["comparability"] == "NO_PRIOR"
    assert snap["changes"]["null_reason"] == "WARMUP"


def test_changes_method_mismatch_refuses_numeric_comparison() -> None:
    snap = _compose(prior_snapshot=_prior(method="liquidity_central_banks.compose.v0"))
    assert snap["changes"]["comparability"] == "METHOD_CHANGED"
    assert snap["changes"]["deltas"] == []
    assert snap["changes"]["null_reason"] == "COMPUTATION_REFUSED"


def test_changes_comparable_prior_produces_deltas() -> None:
    snap = _compose(prior_snapshot=_prior(mi=0.001))
    assert snap["changes"]["comparability"] == "COMPARABLE"
    ids = {d["metric_id"] for d in snap["changes"]["deltas"]}
    assert ids == set(liquidity_central_banks._TRACKED_CHANGE_METRICS)
    mi_delta = next(d for d in snap["changes"]["deltas"] if d["metric_id"] == "glt_monetary_impulse")
    assert mi_delta["prior_value"] == 0.001
    assert mi_delta["current_value"] == pytest.approx(0.003956)
    assert mi_delta["delta"] == pytest.approx(0.002956, abs=1e-6)


# --------------------------------------------------------------------------- #
# corrections / supersession honesty
# --------------------------------------------------------------------------- #
def test_corrections_none_for_first_print() -> None:
    snap = _compose()
    assert snap["corrections"]["correction_state"] == "none"
    assert snap["corrections"]["predecessor_generation_id"] is None


def test_corrections_superseded_when_same_period_value_changes() -> None:
    glt = _base_glt()
    prior_snap = contract.finalize(liquidity_central_banks.compose(
        glt, _base_cb_desk(), _base_hist(), built_at=BUILT_AT))
    glt2 = copy.deepcopy(glt)
    glt2["state"]["monetary_impulse"] = 0.05  # same asof, revised value
    snap2 = liquidity_central_banks.compose(
        glt2, _base_cb_desk(), _base_hist(), built_at=BUILT_AT, prior_snapshot=prior_snap)
    assert snap2["corrections"]["correction_state"] == "superseded"
    assert snap2["corrections"]["changed_fingerprints"]
    assert snap2["corrections"]["predecessor_generation_id"] == prior_snap["generation"]["generation_id"]


def test_corrections_none_when_reference_period_advances() -> None:
    glt = _base_glt()
    prior_snap = contract.finalize(liquidity_central_banks.compose(
        glt, _base_cb_desk(), _base_hist(), built_at=BUILT_AT))
    glt2 = copy.deepcopy(glt)
    glt2["state"]["asof"] = "2026-09-04"  # new observation, not a revision
    glt2["state"]["monetary_impulse"] = 0.05
    snap2 = liquidity_central_banks.compose(
        glt2, _base_cb_desk(), _base_hist(), built_at=BUILT_AT, prior_snapshot=prior_snap)
    assert snap2["corrections"]["correction_state"] == "none"


# --------------------------------------------------------------------------- #
# digest determinism (contract.py's content_digest excludes generation/build
# provenance; identical owner input -> identical digest). Includes a
# genuinely-consumed-field mutation AND an unconsumed-field negative control.
# --------------------------------------------------------------------------- #
def test_digest_is_deterministic_across_identical_input() -> None:
    snap1 = contract.finalize(_compose())
    snap2 = contract.finalize(_compose())
    assert snap1["generation"]["content_sha256"] == snap2["generation"]["content_sha256"]
    assert snap1["generation"]["generation_id"] == snap2["generation"]["generation_id"]


def test_digest_unaffected_by_code_version() -> None:
    snap1 = contract.finalize(_compose(code_version="abc123"))
    snap2 = contract.finalize(_compose(code_version="def456"))
    assert snap1["generation"]["content_sha256"] == snap2["generation"]["content_sha256"]


def test_digest_changes_when_consumed_glt_field_changes() -> None:
    snap1 = contract.finalize(_compose())
    glt2 = copy.deepcopy(_base_glt())
    glt2["state"]["monetary_impulse"] = 0.5  # genuinely consumed
    snap2 = contract.finalize(_compose(glt=glt2))
    assert snap1["generation"]["content_sha256"] != snap2["generation"]["content_sha256"]


def test_digest_changes_when_consumed_cb_desk_field_changes() -> None:
    snap1 = contract.finalize(_compose())
    cbd2 = copy.deepcopy(_base_cb_desk())
    cbd2["cbs"][0]["bs_impulse"]["impulse_13w"] = 9.9  # genuinely consumed
    snap2 = contract.finalize(_compose(cbd=cbd2))
    assert snap1["generation"]["content_sha256"] != snap2["generation"]["content_sha256"]


def test_digest_unaffected_by_unconsumed_glt_field() -> None:
    snap1 = contract.finalize(_compose())
    glt3 = copy.deepcopy(_base_glt())
    glt3["meta"]["architecture_authority"] = "some unrelated string this composer never reads"
    snap3 = contract.finalize(_compose(glt=glt3))
    assert snap1["generation"]["content_sha256"] == snap3["generation"]["content_sha256"]


def test_digest_unaffected_by_unconsumed_cb_desk_field() -> None:
    snap1 = contract.finalize(_compose())
    cbd3 = copy.deepcopy(_base_cb_desk())
    cbd3["cbs"][0]["last_change"]["bp"] = -999.0  # never read by this composer
    snap3 = contract.finalize(_compose(cbd=cbd3))
    assert snap1["generation"]["content_sha256"] == snap3["generation"]["content_sha256"]


def test_digest_unaffected_by_unconsumed_history_meta_row_count() -> None:
    snap1 = contract.finalize(_compose())
    hist3 = copy.deepcopy(_base_hist())
    hist3["rows"] = 999999  # not read by this composer (only last_asof is)
    snap3 = contract.finalize(_compose(hist=hist3))
    assert snap1["generation"]["content_sha256"] == snap3["generation"]["content_sha256"]


# --------------------------------------------------------------------------- #
# schema validation
# --------------------------------------------------------------------------- #
def test_baseline_snapshot_validates_against_the_closed_contract() -> None:
    snap = contract.finalize(_compose())
    contract.validate(snap)  # raises ContractError on any violation
    assert snap["authority"]["can_size"] is False
    assert snap["authority"]["can_execute"] is False
    assert snap["authority"]["can_originate_signal"] is False


def test_degraded_snapshots_still_validate() -> None:
    glt = copy.deepcopy(_base_glt())
    glt["state"]["label"] = "expanding"
    glt["state"]["monetary_impulse_z"] = None
    glt["freshness"]["status"] = "degraded"
    glt["freshness"]["degraded"] = True
    cbd = copy.deepcopy(_base_cb_desk())
    cbd["cbs"][0]["bs_impulse"]["impulse_13w"] = -5.0
    cbd["cbs"] = [cbd["cbs"][0]]  # only FED reports
    snap = contract.finalize(liquidity_central_banks.compose(
        glt, cbd, _base_hist(), built_at=BUILT_AT))
    contract.validate(snap)


def test_snapshot_with_all_owner_inputs_missing_still_validates() -> None:
    snap = contract.finalize(liquidity_central_banks.compose({}, {}, {}, built_at=BUILT_AT))
    contract.validate(snap)
    assert snap["availability"]["state"] == "SOURCE_FAILED"


# --------------------------------------------------------------------------- #
# disclosure prose: reader language only -- never a raw closed-vocabulary
# enum token (PRESENT/SOURCE_FAILED/etc.) inside a human-readable field.
# --------------------------------------------------------------------------- #
_RAW_ENUM_TOKENS = frozenset({
    "CURRENT", "LATE_WITHIN_TOLERANCE", "STALE_SOURCE", "NOT_YET_RELEASED",
    "SOURCE_FAILED", "RIGHTS_BLOCKED", "NOT_COVERED", "HISTORICAL_AS_KNOWN", "SIMULATED",
    "UNKNOWN", "NOT_APPLICABLE", "INSUFFICIENT_HISTORY", "WARMUP",
    "REVISION_PENDING_REBUILD", "DISAGREEMENT", "COMPUTATION_REFUSED", "OUT_OF_REGION",
    "PRESENT", "PARTIAL", "ABSENT",
})
_PROSE_KEYS = ("en", "zh", "note", "transformation")


def _find_raw_token_leaks(node, path: str = "$") -> list[tuple[str, str, str]]:
    leaks: list[tuple[str, str, str]] = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k in _PROSE_KEYS and isinstance(v, str):
                for tok in _RAW_ENUM_TOKENS:
                    if tok in v:
                        leaks.append((f"{path}.{k}", tok, v))
            leaks.extend(_find_raw_token_leaks(v, f"{path}.{k}"))
    elif isinstance(node, list):
        for idx, v in enumerate(node):
            leaks.extend(_find_raw_token_leaks(v, f"{path}[{idx}]"))
    return leaks


def test_prose_fields_contain_no_raw_enum_tokens() -> None:
    # exercise every disclosure branch at once: contradiction fired, quality
    # degraded, WALCL defect fired, 52w warmup.
    glt = copy.deepcopy(_base_glt())
    glt["state"]["label"] = "expanding"
    glt["state"]["monetary_impulse_z"] = None
    cbd = copy.deepcopy(_base_cb_desk())
    cbd["cbs"][0]["bs_impulse"]["impulse_13w"] = -5.0
    snap = _compose(glt=glt, cbd=cbd)
    leaks = _find_raw_token_leaks(snap)
    assert leaks == [], f"raw enum tokens leaked into prose field(s): {leaks}"


# --------------------------------------------------------------------------- #
# zh-label integrity: composer-authored English phrasing must never leak into
# the composer-authored zh sibling
# --------------------------------------------------------------------------- #
_COMPOSER_ENGLISH_PHRASES = (
    "the owner's own", "This composer", "Rather than guess", "measures data lineage",
    "does not agree with", "cosmetic bucket reuse", "a promotion grade",
)


def _find_english_leaks(node, path: str = "$") -> list[tuple[str, str, str]]:
    leaks: list[tuple[str, str, str]] = []
    if isinstance(node, dict):
        zh = node.get("zh")
        if "en" in node and isinstance(zh, str):
            for phrase in _COMPOSER_ENGLISH_PHRASES:
                if phrase in zh:
                    leaks.append((path, phrase, zh))
        for k, v in node.items():
            leaks.extend(_find_english_leaks(v, f"{path}.{k}"))
    elif isinstance(node, list):
        for idx, v in enumerate(node):
            leaks.extend(_find_english_leaks(v, f"{path}[{idx}]"))
    return leaks


def test_zh_narrative_never_embeds_composer_english_phrasing() -> None:
    glt = copy.deepcopy(_base_glt())
    glt["state"]["label"] = "expanding"
    cbd = copy.deepcopy(_base_cb_desk())
    cbd["cbs"][0]["bs_impulse"]["impulse_13w"] = -5.0
    snap = _compose(glt=glt, cbd=cbd)
    leaks = _find_english_leaks(snap)
    assert leaks == [], f"English phrasing leaked into zh field(s): {leaks}"


def test_zh_narrative_present_wherever_english_is_composer_authored() -> None:
    snap = _compose()
    for impl in snap["implications"]["items"]:
        assert impl["text"]["en"], impl
        assert impl["text"]["zh"], impl
    assert snap["workspace"]["title"]["zh"]
    assert snap["headline"]["subtitle"]["zh"]


# --------------------------------------------------------------------------- #
# real owner artifacts (site/liquiditydata + data/intl_risk#cb_desk +
# data/global_liquidity_transmission/state_history_meta.json) -- skipped
# where an artifact is absent, never fabricated.
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(
    not (GLT_LATEST.exists() and INTL_RISK_LATEST.exists()),
    reason="one or more real owner artifacts are absent")
def test_builds_and_validates_from_real_owner_artifacts() -> None:
    glt = json.loads(GLT_LATEST.read_text(encoding="utf-8"))
    intl_risk = json.loads(INTL_RISK_LATEST.read_text(encoding="utf-8"))
    cbd = intl_risk.get("cb_desk") or {}
    hist = json.loads(GLT_HISTORY_META.read_text(encoding="utf-8")) if GLT_HISTORY_META.exists() else {}

    snap = contract.finalize(liquidity_central_banks.compose(glt, cbd, hist, built_at=BUILT_AT))
    contract.validate(snap)
    assert snap["headline"]["state_id"] is None
    assert snap["axes"]["items"] == []
    assert snap["authority"]["can_size"] is False
    assert snap["authority"]["can_execute"] is False
    # FED/ECB/BoJ are the architecture-named trio and should be present in
    # any live cb_desk pull (a real-data smoke check, not a fixture claim).
    ids = {m["metric_id"] for m in snap["metrics"]["items"]}
    assert {"cb_fed_balance_sheet_impulse_13w", "cb_ecb_balance_sheet_impulse_13w",
            "cb_boj_balance_sheet_impulse_13w"} <= ids
    # this composer never fabricates a global-credit scalar
    credit = next(m for m in snap["metrics"]["items"] if m["metric_id"] == "glt_credit_impulse_global")
    if credit["value"] is None:
        assert credit["null_reason"] in ("NOT_COVERED", "SOURCE_FAILED", "UNKNOWN")


# =========================================================================== #
# GLT T21 — measured GLT explanation in the Liquidity & Central Banks workspace
# (per-leg release receipts, four distinct clocks, USD translation rows that
# are never fresh money). All ten tests (a)-(j) below use the closed composer
# above + the closed snapshot contract + the view layer's ``normalized`` /
# ``fx_translation`` fields, and a private render helper that mirrors the
# macro_command_copy_law pattern into tmp_path only (never site/).
# =========================================================================== #

# --------------------------------------------------------------------------- #
# T21 fixtures — deep-copied from the BASE fixtures above, with the receipts
# and producer-scale cb_desk the frozen spec S8 requires. ``_glt_with_receipts``
# carries per-leg release receipts in ``freshness.components.<group>.<leg>``
# plus the model_spec.fx dict on ECB / BoJ. ``_producer_cb_desk`` uses the
# producer's published unit strings (USD / EUR / JPY billions) at the
# producer's scale (the fixture-level ``USD billions (×1, raw WALCL is in
# billions)`` and ``JPY trillions`` strings are recorded as a GAP, not
# edited here).
# --------------------------------------------------------------------------- #
def _glt_with_receipts() -> dict:
    base = copy.deepcopy(_base_glt())
    base["meta"]["generated_at"] = "2026-10-16T18:16:51.754201+00:00"
    base["state"]["asof"] = "2026-10-09"
    fr = base["freshness"]
    fr["clocks"] = {
        "evidence_available_at": "2026-10-09T00:00:00Z",
        "evidence_available_at_contributions": {
            "monetary": "2026-10-08T00:00:00Z",
            "usd_funding": "2026-10-09T00:00:00Z",
            "us_liquidity_quality": None,
        },
        "first_known_at": "2026-10-16T18:16:51.754201Z",
        "latest_component_observed_at": "2026-10-07T00:00:00Z",
        "monetary_release_at": "2026-10-08T00:00:00Z",
        "release_at": "2026-10-09T00:00:00Z",
        "state_asof": "2026-10-09T00:00:00Z",
    }
    # per-leg receipts and current_contribution_z (with model_spec.fx where
    # applicable). The composer reads these keys verbatim via _get().
    monetary_components = {
        "fed": {"status": "usable", "reference_date": "2026-10-07",
                "available_date": "2026-10-08", "source_id": "WALCL",
                "provider": "Board of Governors of the Federal Reserve System"},
        "ecb": {"status": "usable", "reference_date": "2026-10-02",
                "available_date": "2026-10-06", "source_id": "ECBASSETSW",
                "provider": "European Central Bank via FRED"},
        "boj": {"status": "usable", "reference_date": "2026-09-30",
                "available_date": "2026-10-02", "source_id": "JPNASSETS",
                "provider": "Bank of Japan via FRED"},
    }
    monetary_snapshot = {
        "fed": {"current_contribution_z": 0.968795,
                "model_spec": {"key": "WALCL", "fx": None}},
        "ecb": {"current_contribution_z": 0.953589,
                "model_spec": {"key": "ECBASSETSW",
                               "fx": {"column": "close", "invert": False,
                                      "key": "EURUSD=X", "store": "yahoo"}}},
        "boj": {"current_contribution_z": 0.830764,
                "model_spec": {"key": "JPNASSETS",
                               "fx": {"column": "close", "invert": True,
                                      "key": "USDJPY=X", "store": "yahoo"}}},
    }
    funding_components = {
        "broad_dollar": {"status": "usable", "reference_date": "2026-10-08",
                         "available_date": "2026-10-09", "source_id": "DTWEXBGS",
                         "provider": "Board of Governors of the Federal Reserve System via FRED"},
        "high_yield_oas": {"status": "usable", "reference_date": "2026-10-08",
                            "available_date": "2026-10-09", "source_id": "BAMLH0A0HYM2",
                            "provider": "ICE BofA via FRED and the repo append-only archive"},
        "real_yield_10y": {"status": "usable", "reference_date": "2026-10-08",
                           "available_date": "2026-10-09", "source_id": "DFII10",
                           "provider": "Board of Governors of the Federal Reserve System via FRED"},
    }
    funding_snapshot = {
        "broad_dollar": {"current_contribution_z": -0.119342,
                         "model_spec": {"key": "DTWEXBGS", "fx": None}},
        "high_yield_oas": {"current_contribution_z": -0.305917,
                           "model_spec": {"key": "BAMLH0A0HYM2", "fx": None}},
        "real_yield_10y": {"current_contribution_z": -1.508251,
                           "model_spec": {"key": "DFII10", "fx": None}},
    }
    fr["components"]["monetary"] = monetary_components
    fr["components"]["usd_funding"] = funding_components
    fr["component_snapshot"]["monetary"] = monetary_snapshot
    fr["component_snapshot"]["usd_funding"] = funding_snapshot
    return base


def _producer_cb_desk() -> dict:
    base = copy.deepcopy(_base_cb_desk())
    # Producer engine/cb_desk.py normalizes FED/ECB into ``USD`` / ``EUR``
    # billions at source; BoJ into ``JPY`` billions. The fixture's
    # ``USD billions (×1, raw WALCL is in billions)`` and ``JPY trillions``
    # strings are recorded as a GAP (fixture-only).
    base["cbs"][0]["bs_impulse"]["unit"] = "USD billions"
    base["cbs"][0]["bs_impulse"]["level"] = 6737.2  # rescaled to producer's
                                                   # unit (plausible at
                                                   # USD-billions scale; the
                                                   # implausibility guard at
                                                   # ~L600-620 refuses a raw
                                                   # level of 6,737,204 under
                                                   # a "billions" label).
    base["cbs"][1]["bs_impulse"]["unit"] = "EUR billions"
    base["cbs"][2]["bs_impulse"]["unit"] = "JPY billions"
    return base


def _t21_render_html(snapshot: dict, tmp_path) -> str:
    """Replicates tests/test_macro_command_copy_law.py::_render_workspace_html
    into tmp_path only — never reads or writes site/. Used by (f) and (g)."""
    from lib import macro_suite_view
    from scripts import build_macro_suite_pages as builder
    page = next(item for item in builder.SUITE_PAGES
                if item.workspace_id == "liquidity_central_banks")
    artifact = {
        "path": "macrodata/workspaces/liquidity_central_banks/US/latest.json",
        "manifest_path": "macrodata/workspaces/manifest.json",
        "sha256": "fixture",
        "bytes": 1,
        "min_client_contract": builder.MIN_CLIENT_CONTRACT,
    }
    view = macro_suite_view.build_view(
        snapshot, page_built_at=BUILT_AT, artifact=artifact,
        layout=builder._layout_for("liquidity_central_banks"))
    out = Path(tmp_path) / "macro_liquidity_central_banks.html"
    out.write_text(builder.render_page(
        builder._environment(ROOT), page, view), encoding="utf-8")
    return out.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# (a) C12: Sept-4 sample cannot certify today's freshness, no glt_* row or
# glt_leg_* source reads CURRENT. With built_at 2026-10-17 the only
# freshness math against the Sept-4 ``state.asof`` is a 43-day age, well
# past the W-FRI grace window.
# --------------------------------------------------------------------------- #
def test_t21_c12_sept4_sample_cannot_certify_current(tmp_path) -> None:
    snap = liquidity_central_banks.compose(
        _base_glt(), _base_cb_desk(), _base_hist(),
        built_at="2026-10-17T00:00:00Z")
    for mid, m in [(mid, m) for mid, m in zip(
            [x["metric_id"] for x in snap["metrics"]["items"]],
            snap["metrics"]["items"]) if mid.startswith("glt_")]:
        if m["value"] is not None:
            # the spec lets the rank be >= STALE_SOURCE for valued rows.
            severity = {
                "CURRENT": 0, "LATE_WITHIN_TOLERANCE": 1,
                "STALE_SOURCE": 2, "SOURCE_FAILED": 3,
            }.get(m["freshness"], -1)
            assert severity >= 2, (mid, m["freshness"])
    src = snap["sources"]["items"]
    leg_sources = [s for s in src if s["source_id"].startswith("glt_leg_")]
    assert leg_sources == [], leg_sources  # _base_glt has no receipts
    # present the snapshot; no glt_* view row should read "Current" / "当前有效".
    from lib import macro_suite_view
    from scripts import build_macro_suite_pages as builder
    view = macro_suite_view.build_view(
        snap, page_built_at="2026-10-17T00:00:00Z",
        artifact={"path": "x", "manifest_path": "y", "sha256": "s",
                  "bytes": 1, "min_client_contract": builder.MIN_CLIENT_CONTRACT},
        layout=builder._layout_for("liquidity_central_banks"))
    for m in view["metrics"]:
        if not m["metric_id"].startswith("glt_"):
            continue
        freshness = m.get("freshness") or {}
        assert (freshness.get("en") or "") != "Current", m["metric_id"]
        assert (freshness.get("zh") or "") != "当前有效", m["metric_id"]
        assert m.get("freshness_tone") != "ok", m["metric_id"]


# --------------------------------------------------------------------------- #
# (b) C12: a re-wrap of _glt_with_receipts() that changes ONLY
# meta.generated_at and freshness.clocks.first_known_at (both later) yields
# the identical freshness token on every glt_* row and glt_leg_* source; and
# rank never improves for built_at later than the reference. C11 day-window
# for the fed leg: asof+0d -> CURRENT, asof+12d -> STALE_SOURCE,
# asof-1d -> SOURCE_FAILED. The window mirrors
# tests/test_global_liquidity_transmission_liveness_v2.py.
# --------------------------------------------------------------------------- #
def test_t21_c12_rewrap_never_improves_freshness_and_c11_day_window(tmp_path) -> None:
    from lib import macro_suite_view
    from scripts import build_macro_suite_pages as builder
    # Use a built_at AFTER the _glt_with_receipts asof (2026-10-09) so the
    # freshness math is well-defined; BUILT_AT (= 2026-09-04) precedes the
    # asof and would yield SOURCE_FAILED on every leg, which is not the
    # reference state the spec is asking about.
    REF_BUILT = "2026-10-17T00:00:00Z"
    base_snap = contract.finalize(
        liquidity_central_banks.compose(
            _glt_with_receipts(), _producer_cb_desk(), _base_hist(),
            built_at=REF_BUILT))
    base_view = macro_suite_view.build_view(
        base_snap, page_built_at=REF_BUILT,
        artifact={"path": "x", "manifest_path": "y", "sha256": "s",
                  "bytes": 1, "min_client_contract": builder.MIN_CLIENT_CONTRACT},
        layout=builder._layout_for("liquidity_central_banks"))
    base_metric_freshness = {
        m["metric_id"]: m["freshness"] for m in base_snap["metrics"]["items"]
        if m["metric_id"].startswith("glt_")}
    base_leg_freshness = {
        s["source_id"]: s["freshness"] for s in base_snap["sources"]["items"]
        if s["source_id"].startswith("glt_leg_")}

    # C12 re-wrap: only the two fields the spec names change.
    rew = _glt_with_receipts()
    rew["meta"]["generated_at"] = "2026-10-17T19:16:51.754201Z"
    rew["freshness"]["clocks"]["first_known_at"] = "2026-10-17T19:16:51.754201Z"
    rew_snap = contract.finalize(
        liquidity_central_banks.compose(
            rew, _producer_cb_desk(), _base_hist(), built_at=REF_BUILT))
    rew_metric_freshness = {
        m["metric_id"]: m["freshness"] for m in rew_snap["metrics"]["items"]
        if m["metric_id"].startswith("glt_")}
    rew_leg_freshness = {
        s["source_id"]: s["freshness"] for s in rew_snap["sources"]["items"]
        if s["source_id"].startswith("glt_leg_")}
    assert rew_metric_freshness == base_metric_freshness, \
        "C12: a re-wrap of meta.generated_at + first_known_at must not change"
    assert rew_leg_freshness == base_leg_freshness, \
        "C12: per-leg source freshness must be invariant under the re-wrap"

    # rank(CURRENT) < LATE_WITHIN_TOLERANCE < STALE_SOURCE < SOURCE_FAILED
    RANK = {"CURRENT": 0, "LATE_WITHIN_TOLERANCE": 1, "STALE_SOURCE": 2,
            "SOURCE_FAILED": 3, "NOT_COVERED": -1, "NOT_YET_RELEASED": -1}
    # for built_at later than the reference built_at the rank never improves.
    later_built = "2026-10-18T00:00:00Z"
    later_snap = contract.finalize(
        liquidity_central_banks.compose(
            _glt_with_receipts(), _producer_cb_desk(), _base_hist(),
            built_at=later_built))
    for m in later_snap["metrics"]["items"]:
        if m["metric_id"].startswith("glt_"):
            new_rank = RANK.get(m["freshness"], -1)
            old_rank = RANK.get(base_metric_freshness[m["metric_id"]], -1)
            if old_rank >= 0 and new_rank >= 0:
                assert new_rank >= old_rank, \
                    (m["metric_id"], base_metric_freshness[m["metric_id"]],
                     m["freshness"])

    # C11 day-window for the fed leg against glt_asof (state.asof).
    asof = "2026-10-09"
    for built_at_delta_days, expected in (
            (0, "CURRENT"), (12, "STALE_SOURCE")):
        year, month, day = (int(asof[:4]), int(asof[5:7]), int(asof[8:10]))
        built_dt = _dt.date(year, month, day) + _dt.timedelta(
            days=built_at_delta_days)
        built_at = built_dt.isoformat() + "T00:00:00Z"
        snap = liquidity_central_banks.compose(
            _glt_with_receipts(), _producer_cb_desk(), _base_hist(),
            built_at=built_at)
        row = next(m for m in snap["metrics"]["items"]
                   if m["metric_id"] == "glt_fed_monetary_contribution_z")
        assert row["freshness"] == expected, \
            (built_at_delta_days, row["freshness"], expected)
    # fed leg at asof-1 day (future-clock) -> SOURCE_FAILED.
    year, month, day = (int(asof[:4]), int(asof[5:7]), int(asof[8:10]))
    future_dt = _dt.date(year, month, day) - _dt.timedelta(days=1)
    snap = liquidity_central_banks.compose(
        _glt_with_receipts(), _producer_cb_desk(), _base_hist(),
        built_at=future_dt.isoformat() + "T00:00:00Z")
    row = next(m for m in snap["metrics"]["items"]
               if m["metric_id"] == "glt_fed_monetary_contribution_z")
    assert row["freshness"] == "SOURCE_FAILED"


# --------------------------------------------------------------------------- #
# (c) Discriminator: normalized rows (glt_monetary_impulse_z,
# glt_orthogonalised_impulse) carry NO currency unit, even when the producer
# injects "USD billions" into a normalized metric. The S7 keyword strings
# also resolve without any refused word (will/expected/projected/forecast/
# outlook / 将 / 预期 / 预测 / 展望 / 预计).
# --------------------------------------------------------------------------- #
_CURRENCY_RE = re.compile(r"(USD|EUR|JPY|\$|\bbn\b|billion)", re.I)
_REFUSED_WORDS = (
    "will", "expected", "projected", "forecast", "outlook",
    "将", "预期", "预测", "展望", "预计",
)


def test_t21_discriminator_normalized_rows_carry_no_currency_unit(tmp_path) -> None:
    from lib import macro_suite_view
    from scripts import build_macro_suite_pages as builder
    snap = contract.finalize(liquidity_central_banks.compose(
        _glt_with_receipts(), _producer_cb_desk(), _base_hist(),
        built_at=BUILT_AT))
    artifact = {"path": "x", "manifest_path": "y", "sha256": "s",
                "bytes": 1, "min_client_contract": builder.MIN_CLIENT_CONTRACT}

    def _view_row(snap_):
        view = macro_suite_view.build_view(
            snap_, page_built_at=BUILT_AT, artifact=artifact,
            layout=builder._layout_for("liquidity_central_banks"))
        return {m["metric_id"]: m for m in view["metrics"]}

    rows = _view_row(snap)
    for mid in ("glt_monetary_impulse_z", "glt_orthogonalised_impulse"):
        row = rows[mid]
        assert row["normalized"] is True, mid
        unit = row.get("unit")
        if unit is not None:
            assert not _CURRENCY_RE.search(unit.get("en") or ""), (mid, unit)
            assert not _CURRENCY_RE.search(unit.get("zh") or ""), (mid, unit)

    # inject "USD billions" into glt_monetary_impulse_z metric (deep copy).
    injected = copy.deepcopy(snap)
    for m in injected["metrics"]["items"]:
        if m["metric_id"] == "glt_monetary_impulse_z":
            m["unit"] = "USD billions"
            break
    rows2 = _view_row(injected)
    row = rows2["glt_monetary_impulse_z"]
    assert row["normalized"] is True
    unit = row.get("unit")
    assert unit is None or not _CURRENCY_RE.search(unit.get("en") or "") \
        and not _CURRENCY_RE.search(unit.get("zh") or ""), unit

    # S7 keyword strings contain no refused word.
    from lib import macro_suite_labels as L
    keys = [
        ("USD billions", "UNIT"), ("EUR billions", "UNIT"),
        ("JPY billions", "UNIT"), ("local currency", "UNIT"),
        ("ratio_0_1", "UNIT"),
        ("fx_translation_not_fresh_money", "BASIS"),
        ("standardized_monetary_contribution", "BASIS"),
        ("standardized_funding_contribution", "BASIS"),
        ("trailing_13w_pct_change", "BASIS"),
        ("trailing_52w_pct_change", "BASIS"),
        ("higher_more_expansionary", "DIRECTION"),
        ("higher_easier_funding", "DIRECTION"),
        ("higher_more_accommodative", "DIRECTION"),
        ("higher_more_coverage", "DIRECTION"),
        ("glt_fed_monetary_contribution_z", "METRIC"),
        ("glt_ecb_monetary_contribution_z", "METRIC"),
        ("glt_boj_monetary_contribution_z", "METRIC"),
        ("glt_broad_dollar_contribution_z", "METRIC"),
        ("glt_high_yield_oas_contribution_z", "METRIC"),
        ("glt_real_yield_10y_contribution_z", "METRIC"),
        ("glt_ecb_usd_translation", "METRIC"),
        ("glt_boj_usd_translation", "METRIC"),
        ("cb_fed_balance_sheet_level", "METRIC"),
        ("cb_ecb_balance_sheet_level", "METRIC"),
        ("cb_boj_balance_sheet_level", "METRIC"),
        ("cb_ecb_balance_sheet_impulse_13w", "METRIC"),
        ("cb_boj_balance_sheet_impulse_13w", "METRIC"),
        ("cb_fed_balance_sheet_impulse_52w", "METRIC"),
        ("cb_ecb_balance_sheet_impulse_52w", "METRIC"),
        ("cb_boj_balance_sheet_impulse_52w", "METRIC"),
        ("glt_monetary_coverage_ratio", "METRIC"),
        ("glt_funding_coverage_ratio", "METRIC"),
    ]
    for key, vocab in keys:
        # The spec S7 strings are the example form; the actual pair may
        # differ slightly because we preserved the T11 byte-identity goldens.
        # In every case, NO refused word may appear.
        pair = L.label(vocab.lower(), key)
        for phrase in (pair.get("en") or "", pair.get("zh") or ""):
            for rw in _REFUSED_WORDS:
                # substring match on word boundaries for EN; literal for ZH
                if re.search(r"\b" + re.escape(rw) + r"\b", phrase, re.I) or rw in phrase:
                    raise AssertionError(
                        f"S7 refused word {rw!r} in {vocab}.{key}: {phrase!r}")


# --------------------------------------------------------------------------- #
# (d) Discriminator: an absent ecb leg renders a typed absence (no digit in
# value/unit text; bilingual absence cell; ABSENT with NOT_COVERED null
# reason when the model_spec.fx is also dropped).
# --------------------------------------------------------------------------- #
def test_t21_discriminator_absent_leg_renders_typed_absence(tmp_path) -> None:
    from lib import macro_suite_view
    from scripts import build_macro_suite_pages as builder
    glt = copy.deepcopy(_glt_with_receipts())
    # Remove the ecb leg's component_snapshot value AND receipt.
    del glt["freshness"]["component_snapshot"]["monetary"]["ecb"]
    del glt["freshness"]["components"]["monetary"]["ecb"]
    snap = contract.finalize(liquidity_central_banks.compose(
        glt, _producer_cb_desk(), _base_hist(), built_at=BUILT_AT))
    row = next(m for m in snap["metrics"]["items"]
               if m["metric_id"] == "glt_ecb_monetary_contribution_z")
    assert row["value"] is None
    assert row["status"] == "ABSENT"
    artifact = {"path": "x", "manifest_path": "y", "sha256": "s",
                "bytes": 1, "min_client_contract": builder.MIN_CLIENT_CONTRACT}
    view = macro_suite_view.build_view(
        snap, page_built_at=BUILT_AT, artifact=artifact,
        layout=builder._layout_for("liquidity_central_banks"))
    view_row = next(m for m in view["metrics"]
                    if m["metric_id"] == "glt_ecb_monetary_contribution_z")
    assert view_row["absence"] is not None
    assert isinstance(view_row["absence"]["label"], Mapping)
    assert (view_row["value"] is None
            or not re.search(r"\d", view_row["value"].get("en", ""))
            and not re.search(r"\d", view_row["value"].get("zh", "")))
    if view_row.get("unit"):
        u_en = view_row["unit"].get("en") or ""
        u_zh = view_row["unit"].get("zh") or ""
        assert not re.search(r"\d", u_en)
        assert not re.search(r"\d", u_zh)


# --------------------------------------------------------------------------- #
# (e) USD translation rows: is_fresh_money False, basis names the pair and
# carries the "Fixing date: not published by the source." EN/ZH text.
# --------------------------------------------------------------------------- #
def test_t21_usd_translation_is_never_fresh_money(tmp_path) -> None:
    from lib import macro_suite_view
    from scripts import build_macro_suite_pages as builder
    snap = contract.finalize(liquidity_central_banks.compose(
        _glt_with_receipts(), _producer_cb_desk(), _base_hist(),
        built_at=BUILT_AT))
    artifact = {"path": "x", "manifest_path": "y", "sha256": "s",
                "bytes": 1, "min_client_contract": builder.MIN_CLIENT_CONTRACT}
    view = macro_suite_view.build_view(
        snap, page_built_at=BUILT_AT, artifact=artifact,
        layout=builder._layout_for("liquidity_central_banks"))
    expectations = {
        "glt_ecb_usd_translation": ("euro–dollar", "欧元兑美元"),
        "glt_boj_usd_translation": ("dollar–yen", "美元兑日元"),
    }
    for mid, (en_pair, zh_pair) in expectations.items():
        row = next(m for m in view["metrics"] if m["metric_id"] == mid)
        fx = row.get("fx_translation") or {}
        assert fx.get("is_fresh_money") is False, mid
        en_basis = (row.get("basis") or {}).get("en") or ""
        zh_basis = (row.get("basis") or {}).get("zh") or ""
        assert en_pair in en_basis, (mid, en_basis)
        assert "Fixing date: not published by the source." in en_basis, mid
        assert zh_pair in zh_basis, (mid, zh_basis)
        assert "定盘日期：数据源未公布" in zh_basis, mid


# --------------------------------------------------------------------------- #
# (f) Rendered page adds no new machine identifier. ``_T21_BASELINE_STRICT_TOKENS``
# and ``_BASELINE_VIOLATION_COUNT`` are recorded at STEP 1b against BASE =
# e38026e9f4e964d3d2efb77d6f5baa136e247b26 (both zero — the committed
# base golden already passes the copy-law guard).
# --------------------------------------------------------------------------- #
def test_t21_rendered_page_adds_no_new_machine_identifier(tmp_path) -> None:
    from scripts import check_macro_command_copy as copy_guard
    from scripts import count_macro_command_machine_text as counter
    snap = contract.finalize(liquidity_central_banks.compose(
        _glt_with_receipts(), _producer_cb_desk(), _base_hist(),
        built_at=BUILT_AT))
    html_path = Path(tmp_path) / "macro_liquidity_central_banks.html"
    html = _t21_render_html(snap, tmp_path)
    html_path.write_text(html, encoding="utf-8")
    violations = copy_guard.find_violations(html)
    if _BASELINE_VIOLATION_COUNT == 0:
        assert violations == [], violations
    else:
        assert set(violations) <= set(_BASELINE_VIOLATIONS), violations
    counts = counter.count_file(html_path)
    assert counts["top"]["strict"] == 0, counts
    # composite-regex count: sum of strict/loose/parquet/ruleid in the top
    # (visible-text) bucket only. The drawer/details buckets hold the
    # repeated site/liquiditydata/global_liquidity_transmission.json path
    # receipts (see (f) reasoning), which are not new identifiers.
    composite = sum(counts["top"].values())
    assert composite == 0, composite
    nodes = copy_guard.visible_text_nodes(html)
    visible_text = "\n".join(n["text"] for n in nodes if n.get("text"))
    tokens = set(counter.STRICT_SNAKE.findall(visible_text))
    assert tokens.issubset(set(_T21_BASELINE_STRICT_TOKENS)), \
        (tokens - set(_T21_BASELINE_STRICT_TOKENS))


# --------------------------------------------------------------------------- #
# (g) Linkage: the rendered html from (f)'s helper carries the metric name in
# the shell's real element shape. The spec names "Fed balance sheet, against
# its own history" / "美联储资产负债表（对比自身历史）"; the LABEL table
# preserves the T11 byte-identity goldens (so the rendered text uses the
# deslug form "Glt fed monetary contribution z" / "美联储货币贡献 z 值").
# We assert the real element with the rendered strings (the PR quotes both).
# --------------------------------------------------------------------------- #
def test_t21_linkage_fed_label_reaches_rendered_element(tmp_path) -> None:
    snap = contract.finalize(liquidity_central_banks.compose(
        _glt_with_receipts(), _producer_cb_desk(), _base_hist(),
        built_at=BUILT_AT))
    html = _t21_render_html(snap, tmp_path)
    # The shell wraps the metric name in <span class="mq-metric-name"> and
    # prints the bilingual label pair inside two ``<span class="l-en">`` /
    # ``<span class="l-zh">`` children. T21 review M3(e): the reviewed S7
    # strings ship ("Fed balance sheet, against its own history" /
    # "美联储资产负债表（对比自身历史）"); the T11 preservation goldens
    # froze BASE's de-slugged fallback, so tests/test_macro_rates_curves_
    # route.py collapses exactly these strings back to BASE text for that
    # comparison only.
    expected_en = "Fed balance sheet, against its own history"
    expected_zh = "美联储资产负债表（对比自身历史）"
    needle = (
        '<span class="mq-metric-name">'
        f'<span class="l-en">{expected_en}</span>'
        f'<span class="l-zh">{expected_zh}</span>'
        '</span>')
    assert needle in html, (expected_en, expected_zh, needle[:200])


# --------------------------------------------------------------------------- #
# (h) Labels cover every new token: after reset, composing _glt_with_receipts
# + _producer_cb_desk produces no unknown vocabulary:token pair.
# --------------------------------------------------------------------------- #
def test_t21_labels_cover_every_new_token() -> None:
    from lib import macro_suite_labels as L
    L.reset_unknown_tokens()
    snap = contract.finalize(liquidity_central_banks.compose(
        _glt_with_receipts(), _producer_cb_desk(), _base_hist(),
        built_at=BUILT_AT))
    # present the snapshot through the view layer to drive label lookups.
    from lib import macro_suite_view
    from scripts import build_macro_suite_pages as builder
    macro_suite_view.build_view(
        snap, page_built_at=BUILT_AT,
        artifact={"path": "x", "manifest_path": "y", "sha256": "s",
                  "bytes": 1, "min_client_contract": builder.MIN_CLIENT_CONTRACT},
        layout=builder._layout_for("liquidity_central_banks"))
    unknowns = L.unknown_tokens()
    s7_keys = {
        "USD billions", "EUR billions", "JPY billions", "local currency",
        "ratio_0_1",
        "fx_translation_not_fresh_money",
        "standardized_monetary_contribution",
        "standardized_funding_contribution",
        "trailing_13w_pct_change", "trailing_52w_pct_change",
        "higher_more_expansionary", "higher_easier_funding",
        "higher_more_accommodative", "higher_more_coverage",
        "glt_fed_monetary_contribution_z",
        "glt_ecb_monetary_contribution_z",
        "glt_boj_monetary_contribution_z",
        "glt_broad_dollar_contribution_z",
        "glt_high_yield_oas_contribution_z",
        "glt_real_yield_10y_contribution_z",
        "glt_ecb_usd_translation", "glt_boj_usd_translation",
        "cb_fed_balance_sheet_level",
        "cb_ecb_balance_sheet_level",
        "cb_boj_balance_sheet_level",
        "cb_ecb_balance_sheet_impulse_13w",
        "cb_boj_balance_sheet_impulse_13w",
        "cb_fed_balance_sheet_impulse_52w",
        "cb_ecb_balance_sheet_impulse_52w",
        "cb_boj_balance_sheet_impulse_52w",
        "glt_monetary_coverage_ratio",
        "glt_funding_coverage_ratio",
    }
    leaked = [u for u in unknowns
              if any(u.endswith(":" + k) for k in s7_keys)]
    assert leaked == [], leaked
    glt_cb_metric_tokens = set()
    for m in snap["metrics"]["items"]:
        glt_cb_metric_tokens.add(m["metric_id"])
    leaked_metric = [u for u in unknowns
                     if u.split(":", 1)[-1] in glt_cb_metric_tokens]
    assert leaked_metric == [], leaked_metric


# --------------------------------------------------------------------------- #
# (i) Four clocks on the fed leg row + per-leg source row; the cb_ level row
# keeps its own cb_desk clocks (NOT the GLT receipt values).
# --------------------------------------------------------------------------- #
def test_t21_four_clocks_mapped_from_release_receipt() -> None:
    snap = liquidity_central_banks.compose(
        _glt_with_receipts(), _producer_cb_desk(), _base_hist(),
        built_at=BUILT_AT)
    fed_row = next(m for m in snap["metrics"]["items"]
                   if m["metric_id"] == "glt_fed_monetary_contribution_z")
    assert fed_row["observed_at"] == "2026-10-07"
    assert fed_row["released_at"] == "2026-10-08"
    assert fed_row["available_at"] == "2026-10-08T00:00:00Z"
    assert fed_row["collected_at"] == "2026-10-16T18:16:51.754201Z"
    assert fed_row["reference_period"] == "2026-10-07"
    assert fed_row["calculation_as_of"] == "2026-10-09"
    distinct = {fed_row["observed_at"], fed_row["released_at"],
                fed_row["available_at"], fed_row["collected_at"]}
    assert len(distinct) == 4, distinct

    leg_src = next(s for s in snap["sources"]["items"]
                   if s["source_id"] == "glt_leg_fed")
    assert leg_src["reference_period"] == "2026-10-07"
    assert leg_src["released_at"] == "2026-10-08"
    assert leg_src["first_known_at"] == "2026-10-08T00:00:00Z"
    assert leg_src["collected_at"] == "2026-10-16T18:16:51.754201Z"
    assert leg_src["definition_id"] == "WALCL"
    assert leg_src["provider"] == "Board of Governors of the Federal Reserve System"

    # T21 review M1: EVERY leg source row present carries the SAME freshness
    # token as that leg's composed metric row (copied, never recomputed).
    # The equality is checked under a normal past clock (the frozen spec's
    # canonical example built_at): under the module BUILT_AT the fixture's
    # receipts are a future clock and both freshness paths return
    # SOURCE_FAILED, which would hide a divergence.
    fresh_snap = liquidity_central_banks.compose(
        _glt_with_receipts(), _producer_cb_desk(), _base_hist(),
        built_at="2026-10-17T00:00:00Z")
    metric_fresh = {m["metric_id"]: m["freshness"]
                    for m in fresh_snap["metrics"]["items"]}
    leg_metric_by_leg = {
        "fed": "glt_fed_monetary_contribution_z",
        "ecb": "glt_ecb_monetary_contribution_z",
        "boj": "glt_boj_monetary_contribution_z",
        "broad_dollar": "glt_broad_dollar_contribution_z",
        "high_yield_oas": "glt_high_yield_oas_contribution_z",
        "real_yield_10y": "glt_real_yield_10y_contribution_z",
    }
    leg_sources = [s for s in fresh_snap["sources"]["items"]
                   if s["source_id"].startswith("glt_leg_")]
    assert leg_sources, "fixture must produce glt_leg_* source rows"
    for src in leg_sources:
        leg = src["source_id"][len("glt_leg_"):]
        assert src["freshness"] == metric_fresh[leg_metric_by_leg[leg]], (
            leg, src["freshness"], metric_fresh[leg_metric_by_leg[leg]])

    cb_fed = next(m for m in snap["metrics"]["items"]
                  if m["metric_id"] == "cb_fed_balance_sheet_level")
    assert cb_fed["released_at"] != "2026-10-08"
    assert cb_fed["available_at"] != "2026-10-08T00:00:00Z"
    assert cb_fed["collected_at"] != "2026-10-16T18:16:51.754201Z"


# --------------------------------------------------------------------------- #
# (j) Translation rows: exactly two (no glt_fed_usd_translation); both have
# value None / status ABSENT / null_reason NOT_COVERED / freshness
# NOT_COVERED / unit "USD billions"; source_refs match the spec exactly.
# Composing _base_glt() (no model_spec) yields NO translation rows and the
# existing metric count is unchanged versus BASE (28).
# --------------------------------------------------------------------------- #
def test_t21_translation_rows_only_for_ecb_and_boj() -> None:
    snap = liquidity_central_banks.compose(
        _glt_with_receipts(), _producer_cb_desk(), _base_hist(),
        built_at=BUILT_AT)
    translations = [m for m in snap["metrics"]["items"]
                    if m["metric_id"].endswith("_usd_translation")]
    assert {t["metric_id"] for t in translations} == {
        "glt_ecb_usd_translation", "glt_boj_usd_translation"}
    src_refs = {
        "glt_ecb_usd_translation": ["FRED:ECBASSETSW", "yahoo:EURUSD=X"],
        "glt_boj_usd_translation": ["FRED:JPNASSETS", "yahoo:USDJPY=X"],
    }
    for t in translations:
        assert t["value"] is None
        assert t["status"] == "ABSENT"
        assert t["null_reason"] == "NOT_COVERED"
        assert t["freshness"] == "NOT_COVERED"
        assert t["unit"] == "USD billions"
        assert t["source_refs"] == src_refs[t["metric_id"]]
        # T21 review M2: no reading exists, so no observed date and no
        # reference period (S4: observed_at None).
        assert t["observed_at"] is None and t["reference_period"] is None
    # composing _base_glt() (no model_spec) yields NO translation rows and
    # the metric count is unchanged versus BASE.
    base_snap = liquidity_central_banks.compose(
        _base_glt(), _base_cb_desk(), _base_hist(), built_at=BUILT_AT)
    base_translations = [m for m in base_snap["metrics"]["items"]
                         if m["metric_id"].endswith("_usd_translation")]
    assert base_translations == []
    assert len(base_snap["metrics"]["items"]) == BASE_LCB_METRIC_COUNT
