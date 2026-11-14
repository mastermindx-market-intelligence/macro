"""Composer tests for the US inflation_system workspace (F01 R2 packet).

RED-first: each degraded condition must produce the correct TYPED state and
never a zero / neutral / calm default. Also covers quadrant classification,
disclosed hysteresis, the 1M vector, digest determinism, zh-label integrity,
and a real-owner-artifact build -- same shape as
tests/test_macro_workspace_liquidity_regime.py.

    python3 -m pytest tests/test_macro_workspace_inflation.py -x -q
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.market_os.macro_workspaces import contract, inflation  # noqa: E402
from engine.inflation_intelligence import write_inflation_intelligence  # noqa: E402
from engine.market_os.macro_workspaces.build import build_all  # noqa: E402
from scripts.build_macro_suite_pages import SUITE_PAGES, read_workspace  # noqa: E402

from lib import macro_suite_labels, macro_suite_view  # noqa: E402

BUILT_AT = "2026-09-04T00:00:00Z"
REAL_ARTIFACT = ROOT / "data" / "release_forecast" / "inflation_intelligence.json"


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #
def _entry(*, available=True, freshness_status="current_with_publication_lag",
           observation_period="2026-07", **numeric) -> dict:
    return {
        "available": available,
        "freshness_status": freshness_status,
        "observation_period": observation_period,
        "observation_age_months": 2,
        **numeric,
    }


def _base_intel() -> dict:
    """A healthy baseline: disinflationary impulse (x<50), narrow/transitory
    persistence (y<50) -> quadrant C. flexible_ann3 > sticky_ann3 so the
    proxy mix reads flexible_led (no contradiction in the baseline)."""
    return {
        "schema": "inflation_intelligence.v1",
        "asof": "2026-09-01",
        "display_only": True,
        "authority": False,
        "released_state": {
            "available": True,
            "headline": _entry(mom_pct=0.05, yoy_pct=0.5, annualized_3m_pct=0.0,
                               annualized_6m_pct=1.0, acceleration_3m_minus_6m_pp=-1.0),
            "core": _entry(mom_pct=0.02, yoy_pct=0.0, annualized_3m_pct=0.0,
                          annualized_6m_pct=1.0, acceleration_3m_minus_6m_pp=-1.0),
            "underlying_proxies": {
                "sticky": _entry(monthly_pct=0.1, annualized_3m_pct=1.0, annualized_6m_pct=1.5,
                                 acceleration_3m_minus_6m_pp=-0.5),
                "flexible": _entry(monthly_pct=0.3, annualized_3m_pct=3.0, annualized_6m_pct=2.0,
                                   acceleration_3m_minus_6m_pp=1.0),
            },
        },
        "next_release_forecast": {
            "available": True,
            "period": "2026-08",
            "release_date": "2026-09-11",
            "core": {
                "available": True, "period": "2026-08", "release_date": "2026-09-11",
                "forecast_asof": "2026-09-01T07:02:44Z",
                "release_radar_projection": {"point": 0.2636, "confidence": 0.0627,
                                             "p10": 0.0962, "p25": 0.183, "p75": 0.3402, "p90": 0.4137},
            },
            "headline": {
                "available": True, "period": "2026-08", "release_date": "2026-09-11",
                "forecast_asof": "2026-09-01T07:02:44Z",
                "release_radar_projection": {"point": 0.4018, "confidence": 0.3026,
                                             "p10": 0.1791, "p25": 0.2901, "p75": 0.53, "p90": 0.6374},
            },
        },
        "current_month_proxy_pressure": {
            "available": True,
            "period": "2026-09",
            "pressure_direction": None,
            "core_model_pressure": {"available": False, "release_radar_projection": None, "period": None},
            "headline_model_pressure": {"available": False, "release_radar_projection": None, "period": None},
            "underlying_proxy_mix": {"read": "flexible_led"},
        },
    }


def _compose(intel: dict, **kw) -> dict:
    return inflation.compose(intel, built_at=BUILT_AT, **kw)


def _required(snapshot: dict, cid: str) -> dict:
    return next(c for c in snapshot["availability"]["required"] if c["component_id"] == cid)


def _axis(snapshot: dict, wire_axis_id: str) -> dict:
    return next(a for a in snapshot["axes"]["items"] if a["axis_id"] == wire_axis_id)


def _component(axis: dict, cid: str) -> dict:
    return next(c for c in axis["components"] if c["component_id"] == cid)


# --------------------------------------------------------------------------- #
# healthy baseline
# --------------------------------------------------------------------------- #
def test_baseline_classifies_disinflating_narrow_quadrant_C() -> None:
    snap = _compose(_base_intel())
    assert snap["headline"]["status"] == "PRESENT"
    x = snap["headline"]["quadrant"]["x"]
    y = snap["headline"]["quadrant"]["y"]
    assert x < 50 and y < 50
    assert snap["headline"]["state_id"] == "C"
    assert snap["headline"]["state_label"]["en"].startswith("Disinflating, narrow")
    # CPI structurally lags its reference month -- the healthy state is
    # LATE_WITHIN_TOLERANCE, never CURRENT (see inflation._owner_freshness).
    assert snap["availability"]["state"] == "LATE_WITHIN_TOLERANCE"
    for cid in ("core_cpi_annualized_3m", "headline_cpi_annualized_3m",
               "sticky_flexible_spread", "core_acceleration_3m_minus_6m"):
        r = _required(snap, cid)
        assert r["freshness"] == "LATE_WITHIN_TOLERANCE"
        assert r["status"] == "PRESENT"


def test_never_emits_current_freshness_for_cpi_sourced_state() -> None:
    """Inflation-specific clock law: CPI/PCE structurally lag, so this
    workspace's healthy floor is LATE_WITHIN_TOLERANCE, unlike liquidity's
    daily data which legitimately reaches CURRENT."""
    snap = _compose(_base_intel())
    assert snap["availability"]["state"] != "CURRENT"
    for m in snap["metrics"]["items"]:
        if m["metric_id"] in ("headline_cpi_yoy_pct", "core_cpi_yoy_pct"):
            assert m["freshness"] != "CURRENT"


# --------------------------------------------------------------------------- #
# typed degraded states (never zero / neutral / calm)
# --------------------------------------------------------------------------- #
def test_missing_required_source_is_typed_source_failed() -> None:
    reg = _base_intel()
    reg["released_state"]["core"] = {"available": False, "freshness_status": "unknown"}
    snap = _compose(reg)
    r = _required(snap, "core_cpi_annualized_3m")
    assert r["freshness"] == "SOURCE_FAILED"
    assert r["status"] == "ABSENT"
    assert r["null_reason"] == "SOURCE_FAILED"
    assert "core_cpi_annualized_3m" in snap["availability"]["degraded"]
    assert snap["availability"]["state"] == "SOURCE_FAILED"  # conservative worst


def test_stale_required_source_is_typed_stale_not_healthy() -> None:
    reg = _base_intel()
    reg["released_state"]["core"]["freshness_status"] = "stale"
    snap = _compose(reg)
    r = _required(snap, "core_cpi_annualized_3m")
    assert r["freshness"] == "STALE_SOURCE"
    assert snap["availability"]["state"] == "STALE_SOURCE"
    assert snap["availability"]["state"] != "LATE_WITHIN_TOLERANCE"


def _reader_view(intel=None, *, freshness_override=None, keep_ids=None):
    """Present a composed inflation snapshot the way the page does."""
    snap = _compose(_base_intel() if intel is None else intel)
    required = snap["availability"]["required"]
    if freshness_override:
        for row in required:
            token = freshness_override.get(row["component_id"])
            if token is not None:
                row["freshness"] = token
    if keep_ids is not None:
        by_id = {row["component_id"]: row for row in required}
        snap["availability"]["required"] = [by_id[cid] for cid in keep_ids]
    return macro_suite_view.build_view(
        snap,
        page_built_at=BUILT_AT,
        artifact={
            "path": "fixture",
            "manifest_path": "fixture",
            "sha256": "fixture",
            "bytes": 1,
            "min_client_contract": "1",
        },
    )


def _diag_titled(view, en_title: str) -> list[dict]:
    return [item for item in view["diagnostics"] if item["title"]["en"] == en_title]


def _diag_copy(view) -> tuple[str, str]:
    en = "\n".join(
        item["title"]["en"] + "\n" + item["body"]["en"] for item in view["diagnostics"])
    zh = "\n".join(
        item["title"]["zh"] + "\n" + item["body"]["zh"] for item in view["diagnostics"])
    return en, zh


def _joined_labels(rows: list[dict]) -> tuple[str, str]:
    return (
        ", ".join(row["label"]["en"] for row in rows),
        "、".join(row["label"]["zh"] for row in rows),
    )


def test_late_within_tolerance_is_named_late_not_degraded() -> None:
    view = _reader_view()
    rows = view["context"]["required"]
    assert rows
    assert {row["freshness_state"] for row in rows} == {"LATE_WITHIN_TOLERANCE"}
    names_en, names_zh = _joined_labels(rows)
    late = _diag_titled(view, "Required source late, within tolerance")
    assert len(late) == 1
    assert late[0]["tone"] == "warn"
    assert late[0]["title"]["zh"] == "必需数据源延迟，仍在容差内"
    assert late[0]["body"]["en"] == f"Late within tolerance: {names_en}."
    assert late[0]["body"]["zh"] == f"延迟但仍在容差内：{names_zh}。"
    en, zh = _diag_copy(view)
    assert "Required source not current" not in en
    assert "Degraded required components" not in en
    assert "必需数据源并非最新" not in zh
    assert "降级的必需分项" not in zh


def test_stale_and_late_required_sources_are_named_on_separate_lines() -> None:
    stale_id = "core_cpi_annualized_3m"
    late_id = "headline_cpi_annualized_3m"
    view = _reader_view(
        freshness_override={stale_id: "STALE_SOURCE"},
        keep_ids=(stale_id, late_id),
    )
    by_id = {row["component_id"]: row for row in view["context"]["required"]}
    assert set(by_id) == {stale_id, late_id}
    assert by_id[stale_id]["freshness_state"] == "STALE_SOURCE"
    assert by_id[late_id]["freshness_state"] == "LATE_WITHIN_TOLERANCE"
    stale_en, stale_zh = _joined_labels([by_id[stale_id]])
    late_en, late_zh = _joined_labels([by_id[late_id]])
    degraded = _diag_titled(view, "Required source not current")
    late = _diag_titled(view, "Required source late, within tolerance")
    assert len(degraded) == 1
    assert len(late) == 1
    assert degraded[0]["tone"] == "warn"
    assert late[0]["tone"] == "warn"
    assert degraded[0]["title"]["zh"] == "必需数据源并非最新"
    assert late[0]["title"]["zh"] == "必需数据源延迟，仍在容差内"
    assert degraded[0]["body"]["en"] == f"Degraded required components: {stale_en}."
    assert degraded[0]["body"]["zh"] == f"降级的必需分项：{stale_zh}。"
    assert late[0]["body"]["en"] == f"Late within tolerance: {late_en}."
    assert late[0]["body"]["zh"] == f"延迟但仍在容差内：{late_zh}。"
    assert late_en not in degraded[0]["body"]["en"]
    assert stale_en not in late[0]["body"]["en"]
    assert late_zh not in degraded[0]["body"]["zh"]
    assert stale_zh not in late[0]["body"]["zh"]


def test_only_stale_required_sources_keep_the_degraded_wording() -> None:
    reg = _base_intel()
    reg["released_state"]["core"]["freshness_status"] = "stale"
    reg["released_state"]["headline"]["freshness_status"] = "stale"
    for leg in ("sticky", "flexible"):
        reg["released_state"]["underlying_proxies"][leg]["freshness_status"] = "stale"
    view = _reader_view(reg)
    rows = view["context"]["required"]
    assert rows
    assert {row["freshness_state"] for row in rows} == {"STALE_SOURCE"}
    names_en, names_zh = _joined_labels(rows)
    degraded = _diag_titled(view, "Required source not current")
    assert len(degraded) == 1
    assert degraded[0]["tone"] == "warn"
    assert degraded[0]["title"]["zh"] == "必需数据源并非最新"
    assert degraded[0]["body"]["en"] == f"Degraded required components: {names_en}."
    assert degraded[0]["body"]["zh"] == f"降级的必需分项：{names_zh}。"
    en, zh = _diag_copy(view)
    assert "Required source late, within tolerance" not in en
    assert "Late within tolerance" not in en
    assert "必需数据源延迟，仍在容差内" not in zh
    assert "延迟但仍在容差内" not in zh


def test_axis_below_coverage_floor_refuses_no_neutral_default() -> None:
    reg = _base_intel()
    # knock out core AND headline -> only the (already-unavailable) nowcast
    # leg remains -> 0 of 4 present, below min_components -> refuse
    reg["released_state"]["core"] = {"available": False, "freshness_status": "unknown"}
    reg["released_state"]["headline"] = {"available": False, "freshness_status": "unknown"}
    snap = _compose(reg)
    axis = _axis(snap, "inflation_impulse")
    assert axis["value"] is None
    assert axis["value_status"] == "ABSENT"
    assert axis["null_reason"] == "COMPUTATION_REFUSED"
    assert snap["headline"]["state_id"] is None
    assert snap["headline"]["status"] == "ABSENT"
    assert snap["headline"]["quadrant"]["x"] is None


def test_current_month_nowcast_unavailable_is_typed_not_yet_released() -> None:
    """The in-progress-month nowcast is an OPTIONAL (non-required) leg: its
    typed absence must still be disclosed on the component, but must not by
    itself force the whole page's availability.state down."""
    snap = _compose(_base_intel())  # baseline already has no radar entry for 2026-09
    axis = _axis(snap, "inflation_impulse")
    comp = _component(axis, "current_month_core_nowcast_annualized")
    assert comp["freshness"] == "NOT_YET_RELEASED"
    assert comp["coverage_state"] == "ABSENT"
    assert comp["null_reason"] == "NOT_YET_RELEASED"
    # not in the required set -> does not gate the overall state
    assert snap["availability"]["state"] == "LATE_WITHIN_TOLERANCE"
    m = next(i for i in snap["metrics"]["items"] if i["metric_id"] == "current_month_pressure_direction")
    assert m["status"] == "ABSENT"
    assert m["null_reason"] == "NOT_YET_RELEASED"


def test_next_release_projection_metric_is_typed_simulated_not_an_observation() -> None:
    snap = _compose(_base_intel())
    m = next(i for i in snap["metrics"]["items"] if i["metric_id"] == "next_cpi_core_release_projection_mom_pct")
    assert m["status"] == "PRESENT"
    assert m["freshness"] == "SIMULATED"
    assert m["released_at"] is None
    assert m["value"] == pytest.approx(0.2636)


# --------------------------------------------------------------------------- #
# contradiction: sticky-led breadth vs a disinflationary headline
# --------------------------------------------------------------------------- #
def test_sticky_led_but_headline_disinflationary_is_typed_disagreement() -> None:
    reg = _base_intel()
    reg["current_month_proxy_pressure"]["underlying_proxy_mix"]["read"] = "sticky_led"
    snap = _compose(reg)  # baseline x stays < 50 (disinflationary)
    c = snap["availability"]["contradiction"]
    assert c["present"] is True
    assert c["kind"] == "sticky_led_but_headline_disinflationary"
    assert any("contradiction" in r for r in snap["availability"]["reasons"])
    assert any(i["implication_id"] == "sticky_led_headline_disinflation_contradiction"
               for i in snap["implications"]["items"])
    axis = _axis(snap, "persistence_breadth")
    assert axis["value_status"] == "DISAGREEMENT"
    assert axis["value"] is not None
    assert snap["headline"]["quadrant"]["y_status"] == "DISAGREEMENT"
    for cid in ("sticky_flexible_spread", "sticky_acceleration_3m_minus_6m"):
        comp = _component(axis, cid)
        assert comp["coverage_state"] == "DISAGREEMENT"
    # x axis is untouched -- the contradiction only implicates y-side components
    assert _axis(snap, "inflation_impulse")["value_status"] != "DISAGREEMENT"
    assert snap["headline"]["quadrant"]["x_status"] != "DISAGREEMENT"


def test_no_contradiction_when_sticky_led_but_headline_already_inflationary() -> None:
    reg = _base_intel()
    reg["current_month_proxy_pressure"]["underlying_proxy_mix"]["read"] = "sticky_led"
    # push x above the boundary -> the "calm headline" premise no longer holds
    for key in ("annualized_3m_pct", "yoy_pct"):
        reg["released_state"]["core"][key] = 6.0
        reg["released_state"]["headline"][key] = 6.0
    snap = _compose(reg)
    assert snap["availability"]["contradiction"]["present"] is False


# --------------------------------------------------------------------------- #
# changes / method-version comparability / 1M vector
# --------------------------------------------------------------------------- #
def _prior(state_id="C", method=inflation.METHOD_VERSION, x=20.0, y=25.0) -> dict:
    return {
        "generation": {"generation_id": "inflation_system-US-deadbeefdeadbeef"},
        "headline": {
            "state_id": state_id, "method_version": method,
            "effective_date": "2026-08-01",
            "quadrant": {"x": x, "y": y},
        },
    }


def test_no_prior_yields_warmup() -> None:
    snap = _compose(_base_intel())
    assert snap["changes"]["comparability"] == "NO_PRIOR"
    assert snap["changes"]["null_reason"] == "WARMUP"
    assert snap["headline"]["one_month_vector"]["status"] == "ABSENT"
    assert snap["headline"]["one_month_vector"]["null_reason"] == "WARMUP"


def test_method_version_mismatch_refuses_numeric_comparison() -> None:
    snap = _compose(_base_intel(), prior_snapshot=_prior(method="inflation_system.compose.v0"))
    assert snap["changes"]["comparability"] == "METHOD_CHANGED"
    assert snap["changes"]["deltas"] == []
    assert snap["changes"]["null_reason"] == "COMPUTATION_REFUSED"
    assert snap["headline"]["one_month_vector"]["status"] == "ABSENT"
    assert snap["headline"]["one_month_vector"]["null_reason"] == "COMPUTATION_REFUSED"


def test_comparable_prior_produces_deltas_and_vector() -> None:
    snap = _compose(_base_intel(), prior_snapshot=_prior(x=10.0, y=40.0))
    assert snap["changes"]["comparability"] == "COMPARABLE"
    assert {d["metric_id"] for d in snap["changes"]["deltas"]} == {"inflation_impulse", "persistence_breadth"}
    v = snap["headline"]["one_month_vector"]
    assert v["status"] == "PRESENT"
    assert v["dx"] is not None and v["dy"] is not None


# --------------------------------------------------------------------------- #
# hysteresis (domain-agnostic quadrant math, ported from liquidity_regime)
# --------------------------------------------------------------------------- #
def _raw_impulse(score: float) -> float:
    """Inverse of inflation._pct_to_100(v, center=2.0, scale=4.0)."""
    return inflation.IMPULSE_CENTER_PCT + (score - 50.0) / 50.0 * inflation.IMPULSE_SCALE_PCT


def _raw_spread(score: float, scale: float) -> float:
    """Inverse of inflation._pct_to_100(v, center=0.0, scale=scale)."""
    return (score - 50.0) / 50.0 * scale


def _regime_at(x_target: float, y_target: float) -> dict:
    """Craft owner inputs so every present x-component (and every present
    y-component) standardizes to exactly the same target score -- the
    weighted mean of N equal values is that value regardless of the weight
    split, so this reaches an exact axis score without solving the full
    weighted system by hand."""
    reg = _base_intel()
    core_yoy = _raw_impulse(x_target)
    core_ann3 = _raw_impulse(x_target)
    headline_ann3 = _raw_impulse(x_target)
    core_head_gap = _raw_spread(y_target, inflation.SPREAD_SCALE_COREHEAD_PP)
    headline_yoy = core_yoy - core_head_gap
    sticky_flex_spread = _raw_spread(y_target, inflation.SPREAD_SCALE_STICKY_PP)
    core_accel = _raw_spread(y_target, inflation.SPREAD_SCALE_ACCEL_PP)
    sticky_accel = _raw_spread(y_target, inflation.SPREAD_SCALE_ACCEL_PP)
    sticky_ann3 = 2.0
    flexible_ann3 = sticky_ann3 - sticky_flex_spread
    reg["released_state"]["core"].update(
        annualized_3m_pct=core_ann3, yoy_pct=core_yoy, acceleration_3m_minus_6m_pp=core_accel)
    reg["released_state"]["headline"].update(annualized_3m_pct=headline_ann3, yoy_pct=headline_yoy)
    reg["released_state"]["underlying_proxies"]["sticky"].update(
        annualized_3m_pct=sticky_ann3, acceleration_3m_minus_6m_pp=sticky_accel)
    reg["released_state"]["underlying_proxies"]["flexible"].update(annualized_3m_pct=flexible_ann3)
    reg["current_month_proxy_pressure"]["underlying_proxy_mix"]["read"] = (
        "sticky_led" if sticky_ann3 >= flexible_ann3 else "flexible_led")
    return reg


def test_hysteresis_holds_prior_within_band() -> None:
    # x ~ 47.6 (disinflating, near boundary), y ~ 48 (narrow, near boundary)
    # -> raw C, prior D within band -> hold D
    reg = _regime_at(47.6, 48.0)
    snap = _compose(reg, prior_snapshot=_prior(state_id="D", x=52.0, y=48.0))
    assert abs(snap["headline"]["quadrant"]["x"] - 47.6) < 0.5
    assert snap["headline"]["hysteresis"]["held_prior"] is True
    assert snap["headline"]["state_id"] == "D"


def test_hysteresis_flips_when_both_axes_beyond_band() -> None:
    # x ~ 30, y ~ 30 -> both beyond the 5-pt band -> flip to raw C off prior D
    reg = _regime_at(30.0, 30.0)
    snap = _compose(reg, prior_snapshot=_prior(state_id="D", x=52.0, y=48.0))
    assert snap["headline"]["hysteresis"]["held_prior"] is False
    assert snap["headline"]["state_id"] == "C"


# --------------------------------------------------------------------------- #
# axis_id: native per the widened shared-contract pattern (orchestrator
# ruling); drivers buckets remain the shared schema's two fixed generic keys
# -- see inflation.py module docstring "AXIS IDS" / "DEVIATION NOTE"
# --------------------------------------------------------------------------- #
def test_axis_id_is_native_per_widened_contract() -> None:
    snap = _compose(_base_intel())
    x_axis = _axis(snap, "inflation_impulse")
    y_axis = _axis(snap, "persistence_breadth")
    assert x_axis["axis_id"] == "inflation_impulse"
    assert x_axis["label"]["en"] == "Inflation impulse"
    assert x_axis["direction_semantics"] == "higher_more_inflationary"
    assert y_axis["axis_id"] == "persistence_breadth"
    assert y_axis["label"]["en"] == "Persistence & breadth"
    assert y_axis["direction_semantics"] == "higher_more_persistent_broad"


def test_drivers_bucket_reuse_carries_the_two_axes() -> None:
    snap = _compose(_base_intel())
    rate_side_ids = {d["driver_id"] for d in snap["drivers"]["rate_side"]}
    balance_sheet_ids = {d["driver_id"] for d in snap["drivers"]["balance_sheet"]}
    assert rate_side_ids == {c["component_id"] for c in _axis(snap, "inflation_impulse")["components"]}
    assert balance_sheet_ids == {c["component_id"] for c in _axis(snap, "persistence_breadth")["components"]}


# --------------------------------------------------------------------------- #
# zh narrative must never embed an English quadrant-label phrase
# --------------------------------------------------------------------------- #
_QUADRANT_EN_LABEL_PHRASES = (
    "Disinflating headline", "Accelerating and broad-based",
    "Disinflating, narrow", "Accelerating but narrow",
)


def _find_english_label_leaks(node, path: str = "$") -> list[tuple[str, str, str]]:
    leaks: list[tuple[str, str, str]] = []
    if isinstance(node, dict):
        zh = node.get("zh")
        if "en" in node and isinstance(zh, str):
            for phrase in _QUADRANT_EN_LABEL_PHRASES:
                if phrase in zh:
                    leaks.append((path, phrase, zh))
        for k, v in node.items():
            leaks.extend(_find_english_label_leaks(v, f"{path}.{k}"))
    elif isinstance(node, list):
        for idx, v in enumerate(node):
            leaks.extend(_find_english_label_leaks(v, f"{path}[{idx}]"))
    return leaks


def test_zh_narrative_never_embeds_english_quadrant_label() -> None:
    for x_t, y_t in ((25.0, 30.0), (75.0, 25.0), (25.0, 75.0), (75.0, 75.0)):
        reg = _regime_at(x_t, y_t)
        snap = _compose(reg)
        assert snap["headline"]["state_id"] in ("A", "B", "C", "D")
        leaks = _find_english_label_leaks(snap)
        assert leaks == [], f"English quadrant label leaked into zh field(s): {leaks}"


# --------------------------------------------------------------------------- #
# corrections / supersession honesty
# --------------------------------------------------------------------------- #
def test_corrections_none_for_first_print() -> None:
    snap = _compose(_base_intel())
    assert snap["corrections"]["correction_state"] == "none"
    assert snap["corrections"]["predecessor_generation_id"] is None
    assert snap["corrections"]["changed_fingerprints"] == []


def test_corrections_superseded_when_same_period_source_value_changes() -> None:
    reg = _base_intel()
    prior_snap = contract.finalize(_compose(reg))
    reg2 = copy.deepcopy(reg)
    reg2["released_state"]["core"]["yoy_pct"] = 4.4  # revision, same asof/reference period
    snap2 = _compose(reg2, prior_snapshot=prior_snap)
    assert snap2["corrections"]["correction_state"] == "superseded"
    assert snap2["corrections"]["changed_fingerprints"]
    assert any(fp.startswith("cpi_headline_core:core_cpi_yoy_pct:")
               for fp in snap2["corrections"]["changed_fingerprints"])
    assert snap2["corrections"]["predecessor_generation_id"] == prior_snap["generation"]["generation_id"]


def test_corrections_none_when_reference_period_advances() -> None:
    reg = _base_intel()
    prior_snap = contract.finalize(_compose(reg))
    reg2 = copy.deepcopy(reg)
    reg2["asof"] = "2026-10-01"  # new observation, not a revision
    reg2["released_state"]["core"]["yoy_pct"] = 4.4
    snap2 = _compose(reg2, prior_snapshot=prior_snap)
    assert snap2["corrections"]["correction_state"] == "none"


# --------------------------------------------------------------------------- #
# digest determinism + schema validation
# --------------------------------------------------------------------------- #
def test_identical_owner_input_yields_identical_digest_across_builds() -> None:
    reg = _base_intel()
    snap_a = contract.finalize(_compose(reg, code_version="commit-aaaa"))
    snap_b = contract.finalize(_compose(reg, code_version="commit-bbbb"))
    assert snap_a["generation"]["content_sha256"] == snap_b["generation"]["content_sha256"]
    assert snap_a["generation"]["generation_id"] == snap_b["generation"]["generation_id"]
    contract.validate(snap_a)
    contract.validate(snap_b)


def test_baseline_snapshot_satisfies_the_closed_contract() -> None:
    snap = contract.finalize(_compose(_base_intel()))
    contract.validate(snap)  # raises ContractError on any violation
    ok, reason = contract.check(snap)
    assert ok, reason


# --------------------------------------------------------------------------- #
# real owner artifact
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not REAL_ARTIFACT.exists(), reason="owner artifact data/release_forecast/inflation_intelligence.json absent")
def test_builds_and_validates_from_real_owner_artifact() -> None:
    intel = json.loads(REAL_ARTIFACT.read_text(encoding="utf-8"))
    snap = contract.finalize(inflation.compose(intel, built_at=BUILT_AT))
    contract.validate(snap)  # real-data snapshot satisfies the closed contract
    assert snap["headline"]["state_id"] in ("A", "B", "C", "D", None)
    assert snap["generation"]["calculation_as_of"] == intel.get("asof")
    assert snap["authority"]["can_size"] is False
    assert snap["workspace"]["id"] == "inflation_system"


# --------------------------------------------------------------------------- #
# actual owner -> atomic publication -> manifest reader -> consumer view
# --------------------------------------------------------------------------- #
def _published_owner_fixture(tmp_path: Path, *, missing_annual_endpoint: bool = False) -> dict:
    """All inputs are temporary, fixed-date collector shapes; no ambient feeds.

    The real owner calculates the rates. The publisher receives its actual
    artifact path, rather than assuming that a FRED directory invokes the owner.
    Distinct endpoints make headline/core and annual/monthly swaps observable.
    """
    collector = tmp_path / "collector"
    fred = collector / "data" / "fred"
    fred.mkdir(parents=True)
    dates = pd.date_range("2025-08-01", periods=13, freq="MS")
    cohorts = {
        "CPIAUCSL": ("headline_cpi", [100 + 2 * i / 11 for i in range(12)] + [103.02]),
        "CPILFESL": ("core_cpi", [200 + 4 * i / 11 for i in range(12)] + [204.0]),
        "STICKCPIM157SFRBATL": ("sticky_cpi", [0.2] * 13),
        "FLEXCPIM157SFRBATL": ("flex_cpi", [0.1] * 13),
    }
    for sid, (column, values) in cohorts.items():
        frame = pd.DataFrame({column: values}, index=dates)
        if missing_annual_endpoint and sid == "CPIAUCSL":
            # Keep 13 observations, but replace the exact annual endpoint with
            # an older month. A positional 12-row lag would invent a YoY rate.
            earlier = pd.DataFrame({column: [98.0]}, index=pd.DatetimeIndex(["2025-07-01"]))
            frame = pd.concat([earlier, frame.iloc[1:]])
            assert len(frame) == 13 and pd.Timestamp("2025-08-01") not in frame.index
        frame.to_parquet(fred / f"{sid}.parquet")

    radar = collector / "radar.json"
    radar.write_text(json.dumps({"asof": "2026-09-04", "upcoming": []}), encoding="utf-8")
    ledger = collector / "forward.jsonl"
    ledger.write_text("", encoding="utf-8")
    owner, owner_path = write_inflation_intelligence(
        root=collector, as_of="2026-09-04",
        radar_latest_path=radar, forward_ledger_path=ledger,
    )
    owner_bytes = owner_path.read_bytes()
    regime = tmp_path / "regime.json"
    regime.write_text("{}", encoding="utf-8")
    absent = tmp_path / "unrelated-inputs-absent"
    out = tmp_path / "site" / "macrodata"
    receipts = build_all(
        out_root=out, regime_latest_path=regime,
        inflation_intel_path=owner_path,  # The owner-to-publisher handoff under test.
        rates_command_path=absent / "rates.json", intl_risk_path=absent / "risk.json",
        glt_latest_path=absent / "glt.json", glt_history_meta_path=absent / "glt-history.json",
        fred_dir=fred, zori_path=absent / "zori.parquet",
        capital_structure_projection_path=absent / "capital.json",
        treasury_dir=absent / "treasury", treasury_auctions_path=absent / "auctions.json",
        bis_dir=absent / "bis", bonds_latest_path=absent / "bonds.json",
        built_at=BUILT_AT, code_version="synthetic-inflation-owner-publication",
    )
    page = next(page for page in SUITE_PAGES if page.workspace_id == "inflation_system")
    snapshot, artifact = read_workspace(out, page)
    view = macro_suite_view.build_view(snapshot, page_built_at=BUILT_AT, artifact=artifact)
    assert owner_path.read_bytes() == owner_bytes  # Consumer work cannot rewrite its owner.
    return {
        "owner": owner, "owner_path": owner_path, "out": out,
        "receipts": receipts, "snapshot": snapshot, "artifact": artifact, "view": view,
    }


def test_real_owner_rates_survive_publication_and_reader_with_monthly_dates(tmp_path: Path) -> None:
    result = _published_owner_fixture(tmp_path)
    owner, snap, artifact, view = (result[key] for key in ("owner", "snapshot", "artifact", "view"))
    expected = {
        "headline_cpi_yoy_pct": ("headline", "yoy_pct", "pct_yoy", 3.02),
        "headline_cpi_mom_pct": ("headline", "mom_pct", "pct_mom", 1.0),
        "core_cpi_yoy_pct": ("core", "yoy_pct", "pct_yoy", 2.0),
        "core_cpi_mom_pct": ("core", "mom_pct", "pct_mom", 0.0),
    }
    metrics = {row["metric_id"]: row for row in snap["metrics"]["items"]}
    displayed = {row["metric_id"]: row for row in view["metrics"]}
    for metric_id, (group, field, unit, value) in expected.items():
        upstream, metric, shown = owner["released_state"][group], metrics[metric_id], displayed[metric_id]
        assert upstream[field] == pytest.approx(value)
        assert metric["value"] == upstream[field]
        assert metric["status"] == "PRESENT" and metric["null_reason"] is None
        assert shown["value"] is not None and shown["absence"] is None
        assert float(shown["value"]["en"]) == pytest.approx(value)
        assert float(shown["value"]["zh"]) == pytest.approx(value)
        assert metric["reference_period"] == shown["reference_period"] == "2026-08"
        assert metric["unit"] == unit
        assert metric["basis"] == "seasonally_adjusted_not_original_vintage"
        assert shown["unit"] == macro_suite_labels.label("unit", unit)
        assert shown["basis"] == macro_suite_labels.label("basis", metric["basis"])
        assert shown["freshness"] == macro_suite_labels.label("freshness", "LATE_WITHIN_TOLERANCE")
        assert metric["owner_ref"] == f"engine.inflation_intelligence.released_state.{group}"
        assert metric["definition_id"] == f"released_state.{group}.{field}"
        assert metric["source_refs"] == shown["source_refs"] == [metric["owner_ref"]]
        assert upstream["revision_basis"] == "latest_local_fred_not_original_release_vintage"
        assert metric["freshness"] == "LATE_WITHIN_TOLERANCE"
        for clock in ("released_at", "available_at", "collected_at", "revised_at"):
            assert metric[clock] is None

    assert {row["source_asof"] for row in view["context"]["required"]} == {"2026-08"}
    assert snap["availability"]["state"] == "LATE_WITHIN_TOLERANCE"
    assert snap["generation"]["calculation_as_of"] == owner["asof"] == "2026-09-04"
    source = next(row for row in snap["sources"]["items"] if row["source_id"] == "cpi_headline_core")
    assert source["artifact_ref"] == "data/release_forecast/inflation_intelligence.json"
    for clock in ("released_at", "first_known_at", "collected_at", "revised_at"):
        assert source[clock] is None

    manifest_path = result["out"] / "workspaces" / "manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    assert manifest == result["receipts"]["_manifest"]["manifest"]
    entry = manifest["workspaces"]["inflation_system/US"]
    body_path = result["out"] / entry["path"]
    assert json.loads(body_path.read_bytes()) == snap == result["receipts"]["inflation_system/US"]["snapshot"]
    assert entry["content_sha256"] == artifact["sha256"] == contract.content_digest(snap)
    assert entry["generation_id"] == snap["generation"]["generation_id"]
    assert entry["bytes"] == artifact["bytes"] == len(body_path.read_bytes())
    assert manifest["generated_at"] == BUILT_AT
    assert view["evidence"]["artifact"] == artifact
    assert view["evidence"]["generation"]["content_sha256"] == artifact["sha256"]
    assert owner["display_only"] is True and owner["authority"] is False
    assert set(owner["allowed_actions"]) == {"may_rank", "may_score", "may_size", "may_gate", "may_escalate", "may_trade"}
    assert all(value is False for value in owner["allowed_actions"].values())
    flags = view["evidence"]["authority"]["flags"]
    assert len(flags) == 5 and all(flag["value"] is False for flag in flags)


def test_missing_exact_annual_endpoint_keeps_monthly_rate_and_core_zero(tmp_path: Path) -> None:
    result = _published_owner_fixture(tmp_path, missing_annual_endpoint=True)
    owner = result["owner"]["released_state"]
    metrics = {row["metric_id"]: row for row in result["snapshot"]["metrics"]["items"]}
    displayed = {row["metric_id"]: row for row in result["view"]["metrics"]}
    assert owner["headline"]["available"] is True
    assert owner["headline"]["yoy_pct"] is None
    assert metrics["headline_cpi_yoy_pct"]["value"] is None
    assert metrics["headline_cpi_yoy_pct"]["status"] == "ABSENT"
    assert metrics["headline_cpi_yoy_pct"]["null_reason"] == "SOURCE_FAILED"
    assert displayed["headline_cpi_yoy_pct"]["value"] is None
    assert displayed["headline_cpi_yoy_pct"]["absence"] is not None
    assert displayed["headline_cpi_yoy_pct"]["absence"]["token"] == "SOURCE_FAILED"
    for metric_id, value in (("headline_cpi_mom_pct", 1.0), ("core_cpi_yoy_pct", 2.0), ("core_cpi_mom_pct", 0.0)):
        assert metrics[metric_id]["value"] == pytest.approx(value)
        assert displayed[metric_id]["value"] is not None
        assert float(displayed[metric_id]["value"]["en"]) == pytest.approx(value)
        assert float(displayed[metric_id]["value"]["zh"]) == pytest.approx(value)
        assert displayed[metric_id]["reference_period"] == "2026-08"
