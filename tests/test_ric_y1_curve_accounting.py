import hashlib
import json
from unittest import mock

import numpy as np
import pandas as pd
import pytest

from engine.yield_momentum import build_curve_accounting, build_yield_momentum

_GOLDEN_MOMENTUM_SHA = (
    "9fab2a90c00c5eb2d67c7efc3afe18848f428b57344f5f547a32fe8a3c2bc361"
)

_FROZEN_TOP_KEYS = frozenset(
    {
        "schema",
        "calculation_version",
        "basis_schema",
        "cutoff",
        "asof",
        "status",
        "reason",
        "display_only",
        "authority",
        "can_score",
        "can_size",
        "can_trade",
        "law",
        "observations",
        "comparisons",
        "accounting_views",
        "views_are_alternatives_never_summed",
    }
)


def _frame(n=300):
    idx = pd.bdate_range("2025-08-01", periods=n)
    i = np.arange(n, dtype=float)
    return pd.DataFrame(
        {
            "us10y": 4.00 + 0.01 * i,
            "us10y_real": 1.80 + 0.004 * i,
            "term_premium_10y": 0.50 + 0.002 * i,
        },
        index=idx,
    )


def _numeric_leaves(obj, path=""):
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        yield path, obj
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            child = f"{path}.{k}" if path else k
            yield from _numeric_leaves(v, child)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _numeric_leaves(v, f"{path}[{i}]")


def test_y1_momentum_payload_bytes_unchanged():
    payload = build_yield_momentum(_frame())
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    assert digest == _GOLDEN_MOMENTUM_SHA


def test_y1_kw_is_never_relabelled_acm():
    p = build_curve_accounting(_frame())
    acm = p["observations"]["term_premium_acm_10y"]
    kw = p["observations"]["term_premium_kw_10y"]
    assert acm["value"] is None
    assert acm["value_state"] == "missing"
    assert acm["model_id"] == "acm_not_admitted"
    assert acm["source"] is None
    assert acm["target"] == "term_premium_acm"
    assert "kw" in kw["model_id"]
    assert "acm" not in kw["model_id"]
    assert kw["target"] == "term_premium_kw"
    assert kw["evidence_class"] == "estimated_decomposition"
    assert kw["curve_convention"] == "zero"
    assert "model_vintage_unknown" in kw["limitations"]
    assert "model_fit_unknown" in kw["limitations"]
    cmp_ = p["comparisons"]["term_premium_kw_vs_acm"]
    assert cmp_["status"] == "unavailable"
    assert cmp_["reason"] == "operand_missing:right"
    assert cmp_["difference"] is None

    frame2 = _frame().copy()
    frame2["acm_term_premium_10y"] = 9.99
    p2 = build_curve_accounting(frame2)
    acm2 = p2["observations"]["term_premium_acm_10y"]
    assert acm2 == acm
    for path, val in _numeric_leaves(p2):
        assert abs(val - 9.99) > 1e-9


def test_y1_compensation_is_the_b0_transform():
    p = build_curve_accounting(_frame())
    cmp_ = p["comparisons"]["inflation_compensation"]
    assert cmp_["status"] == "comparable_after_transformation"
    assert cmp_["rule_id"] == "inflation_compensation.v1"
    assert cmp_["transform"] == "nominal_minus_real"
    assert cmp_["unit"] == "bp"
    nom = p["observations"]["nominal_10y"]["value"]
    real = p["observations"]["real_10y"]["value"]
    assert abs(cmp_["difference"] - (nom - real) * 100) < 1e-9
    assert "indexation lag" in cmp_["limitations"]


def test_y1_par_and_zero_are_never_subtracted():
    p = build_curve_accounting(_frame())
    assert not any("expected_short" in k for k in p["observations"])
    cmp_ = p["comparisons"]["nominal_par_vs_kw_zero"]
    assert cmp_["status"] == "not_comparable"
    assert cmp_["reason"] == "basis_mismatch:curve_convention"
    assert cmp_["difference"] is None
    nom = p["observations"]["nominal_10y"]["value"]
    kw = p["observations"]["term_premium_kw_10y"]["value"]
    for path, val in _numeric_leaves(p):
        assert abs(val - (nom - kw)) > 1e-6
        assert abs(val - (nom - kw) * 100) > 1e-6


def test_y1_only_admitted_numbers_appear():
    p = build_curve_accounting(_frame())
    for path, val in _numeric_leaves(p):
        if path.endswith(".value"):
            assert path.startswith("observations.")
            continue
        if path == "comparisons.inflation_compensation.difference":
            continue
        pytest.fail(f"unexpected numeric leaf {path}={val}")


def test_y1_views_are_never_summed():
    p = build_curve_accounting(_frame())
    assert frozenset(p.keys()) == _FROZEN_TOP_KEYS
    assert p["views_are_alternatives_never_summed"] is True
    views = p["accounting_views"]
    assert [v["view_id"] for v in views] == [
        "expected_short_plus_term_premium",
        "real_plus_inflation_compensation",
    ]
    assert list(_numeric_leaves(views)) == []
    kw = p["observations"]["term_premium_kw_10y"]["value"]
    real = p["observations"]["real_10y"]["value"]
    comp = p["comparisons"]["inflation_compensation"]["difference"]
    forbidden = (kw + real, kw + comp / 100, real + comp / 100 + kw)
    for path, val in _numeric_leaves(p):
        for target in forbidden:
            assert abs(val - target) > 1e-6


def test_y1_single_move_is_not_identified():
    frame = _frame()
    p = build_curve_accounting(frame)
    ym = build_yield_momentum(frame)
    move = p["observations"]["nominal_10y_move_22d"]
    assert move["value"] == 22.0
    assert move["value"] == ym["series"]["10y"]["velocity_bp"]["22d"]
    assert move["reference_start"] == ym["series"]["10y"]["endpoint_dates"]["22d"][0]
    assert move["reference_end"] == ym["series"]["10y"]["endpoint_dates"]["22d"][1]
    assert p["observations"]["real_10y_move_22d"]["value"] == 8.8
    cmp_ = p["comparisons"]["yield_move_attribution"]
    assert cmp_["status"] == "not_identified"
    assert cmp_["reason"] == "underidentified:decomposition"
    assert cmp_["difference"] is None
    assert cmp_["range"] is None
    assert "expected_short=+7.33bp + term_premium=+14.67bp" in cmp_["limitations"]
    assert "expected_short=-7.33bp + term_premium=+29.33bp" in cmp_["limitations"]
    assert frozenset(cmp_.keys()) == frozenset(
        p["comparisons"]["inflation_compensation"].keys()
    )


def test_y1_missing_inputs_are_missing_never_zero():
    frame = _frame().copy()
    frame["us10y_real"] = np.nan
    del frame["term_premium_10y"]
    p = build_curve_accounting(frame)
    assert p["observations"]["term_premium_kw_10y"]["value"] is None
    assert p["observations"]["term_premium_kw_10y"]["value_state"] == "missing"
    assert p["observations"]["real_10y"]["value"] is None
    assert p["observations"]["real_10y"]["value_state"] == "missing"
    assert p["observations"]["nominal_10y"]["value_state"] == "present"
    assert p["comparisons"]["inflation_compensation"]["status"] == "unavailable"
    for path, val in _numeric_leaves(p):
        assert val != 0.0
    assert p["status"] == "available"


def test_y1_stale_input_is_stale_not_present():
    frame = _frame()
    last = frame.index[-1]
    cutoff = last
    stale_start = last - pd.Timedelta(days=40)
    mask = frame.index >= stale_start
    frame.loc[mask, "term_premium_10y"] = np.nan
    p = build_curve_accounting(frame)
    kw = p["observations"]["term_premium_kw_10y"]
    assert kw["value"] is None
    assert kw["value_state"] == "stale"
    assert "stale" in kw["quality"]
    assert "stale_beyond_tolerance_31d" in kw["limitations"]
    assert p["comparisons"]["nominal_par_vs_kw_zero"]["status"] == "unavailable"


def test_y1_cutoff_is_point_in_time():
    c = str(_frame().index[250].date())
    a = build_curve_accounting(_frame(), cutoff=c)
    b_frame = _frame()
    b_frame.iloc[251:] = b_frame.iloc[251:].add(1.0)
    b = build_curve_accounting(b_frame, cutoff=c)
    assert a == b
    assert a["observations"]["nominal_10y"]["value_state"] == "present"
    assert a["observations"]["nominal_10y"]["observation_time"] == c
    assert a["asof"] == c
    for key, obs in a["observations"].items():
        if obs["value_state"] == "present" and obs.get("observation_time"):
            assert obs["observation_time"] <= c
    for key in ("nominal_10y_move_22d", "real_10y_move_22d"):
        ref_end = a["observations"][key].get("reference_end")
        if ref_end is not None:
            assert ref_end <= c


def test_y1_internal_error_degrades_never_raises():
    with mock.patch(
        "engine.rates_command_basis.compare_qualified",
        side_effect=RuntimeError("boom"),
    ):
        p = build_curve_accounting(_frame())
    assert p["status"] == "error"
    assert p["reason"] == "internal_error:RuntimeError"
    assert p["observations"] == {}
    assert p["comparisons"] == {}
    assert p["display_only"] is True
    assert p["authority"] is False
    assert frozenset(p.keys()) == _FROZEN_TOP_KEYS
    json.dumps(p, allow_nan=False)


def test_y1_payload_is_strict_json_and_display_only():
    p = build_curve_accounting(_frame())
    text = json.dumps(p, allow_nan=False)
    assert len(text) < 30000
    assert p["display_only"] is True
    assert p["authority"] is False
    assert p["can_score"] is False
    assert p["can_size"] is False
    assert p["can_trade"] is False

    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                assert k not in ("rank", "score", "recommendation", "allowed_actions"), k
                assert not str(k).startswith("may_"), k
                walk(v)
        elif isinstance(obj, (list, tuple)):
            for v in obj:
                walk(v)

    walk(p)
    assert "validated" not in text.lower()


def test_y1_empty_frame_is_unavailable():
    p = build_curve_accounting(pd.DataFrame())
    assert p["status"] == "unavailable"
    assert p["reason"] == "empty_frame"
    assert p["observations"] == {}
    assert p["comparisons"] == {}
    assert p["cutoff"] is None
    assert frozenset(p.keys()) == _FROZEN_TOP_KEYS
