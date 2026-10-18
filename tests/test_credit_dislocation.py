"""Synthetic acceptance for descriptive CCW dislocations; no network or market claims."""
from datetime import date
import json

import pandas as pd
import pytest

from engine.credit_dislocation import (
    AUTHORITY, compile_snapshot, identifier, load_snapshot, write_snapshot,
)
from lib.nyse_calendar import sessions_between

END = date(2026, 10, 16)


def cusip(n):
    value = f"{n:08d}"
    total = sum(sum(map(int, str(int(c) * (1 + i % 2)))) for i, c in enumerate(value))
    return value + str((10 - total % 10) % 10)


def fixture():
    days = sessions_between(date(2026, 8, 3), END)
    issuers = [f"TEST{i}" for i in range(6)]
    rows, bonds, stocks = [], [], {}
    reg = {"themes": {"synthetic": {"issuers": {}}}}
    for i, issuer in enumerate(issuers):
        reg["themes"]["synthetic"]["issuers"][issuer] = {"equity_ticker": issuer, "tier": "IG"}
        for j, day in enumerate(days):
            rows.append({"as_of": day.isoformat(), "issuer": issuer,
                         "d1_g_spread_bp_matched": 5.0 if i == 0 else 1.0,
                         "matched_n": 3, "g_spread_bp_pw": 100 + j,
                         "wam_yrs": 5.0})
        bonds.append({"as_of": END.isoformat(), "isin": cusip(i + 1), "issuer": issuer,
                      "name": f"Synthetic {issuer} bullet", "maturity": "2031-10-16",
                      "coupon": 5.0, "price_clean": 99.0, "par": 1000.0,
                      "g_spread_bp": 120.0, "near_par_call_flag": False})
        stocks[issuer] = pd.Series(100.0, index=pd.to_datetime(days))
    return pd.DataFrame(rows), pd.DataFrame(bonds), reg, stocks


def compile_data(data=None, as_of=END):
    return compile_snapshot(*(data or fixture()), as_of=as_of)


def first(result):
    return result["issuers"][0]


@pytest.mark.parametrize("value,kind,valid", [
    ("US0378331005", "isin", True), ("037833100", "cusip", True),
    ("594918104", "cusip", True), ("US0378331006", "isin", False),
    ("037833101", "cusip", False), ("not-an-id", "unknown", False),
    ("", "unknown", False), (None, "unknown", False),
])
def test_identifier(value, kind, valid):
    result = identifier(value)
    assert result["kind"] == kind
    assert result["checksum_valid"] is valid
    assert bool(result["key"]) is valid


def test_correct_relative_comparison_and_authority():
    result = compile_data()
    row = first(result)
    assert row["change_5"]["value_bp"] == 25.0
    assert row["peer_change_5_bp"] == 5.0
    assert row["relative_change_5_bp"] == 20.0
    assert len(row["peer_issuers"]) == 5
    assert row["issuer"] not in row["peer_issuers"]
    assert row["equity_5"]["value_pct"] == 0
    assert row["state"] == "credit_widening_equity_steadier"
    assert result["authority"] == AUTHORITY
    assert not any(result["authority"].values())
    assert result["point_in_time_qualified"] is False
    assert result["parameters"]["thresholds_validated"] is False
    assert result["cds"]["status"] == "unavailable"


def test_missing_session_does_not_become_five_observations():
    history, panel, reg, stocks = fixture()
    drop_day = sorted(history.as_of.unique())[-3]
    history = history[~((history.issuer == "TEST0") & (history.as_of == drop_day))]
    row = first(compile_data((history, panel, reg, stocks)))
    assert row["change_5"]["value_bp"] is None
    assert row["state"] == "insufficient_evidence"


def test_no_matched_bond_is_not_zero_change():
    data = list(fixture())
    data[0].loc[(data[0].issuer == "TEST0") & (data[0].as_of == END.isoformat()), "matched_n"] = 0
    assert first(compile_data(tuple(data)))["change_5"]["value_bp"] is None


def test_coarse_peers_not_enough():
    history, panel, reg, stocks = fixture()
    history = history[history.issuer.isin(["TEST0", "TEST1", "TEST2"])]
    row = first(compile_data((history, panel, reg, stocks)))
    assert row["relative_change_5_bp"] is None
    assert row["state"] == "insufficient_evidence"


def test_missing_equity_no_candidate():
    history, panel, reg, _ = fixture()
    row = first(compile_data((history, panel, reg, {})))
    assert row["relative_change_5_bp"] == 20
    assert row["equity_5"]["value_pct"] is None
    assert row["state"] == "insufficient_evidence"


def test_no_equity_forward_fill():
    history, panel, reg, stocks = fixture()
    stocks["TEST0"] = stocks["TEST0"].iloc[:-1]
    assert first(compile_data((history, panel, reg, stocks)))["equity_5"]["value_pct"] is None


def test_extreme_stock_move_needs_corporate_action_review():
    data = fixture()
    data[3]["TEST0"].iloc[-1] = 50
    assert first(compile_data(data))["equity_5"]["reason"] == "corporate_action_or_extreme_move_needs_review"


def test_joint_deterioration_is_not_credit_first():
    data = fixture()
    data[3]["TEST0"].iloc[-1] = 95
    assert first(compile_data(data))["state"] == "joint_deterioration"


def test_stale_never_has_current_candidate():
    result = compile_data(as_of=date(2026, 11, 2))
    assert result["status"] == "stale"
    assert result["source_as_of"] == END.isoformat()
    assert first(result)["state"] == "historical_only"
    assert first(result)["change_5"]["value_bp"] == 25


def test_row_order_does_not_change_output():
    history, panel, reg, stocks = fixture()
    original = compile_data((history, panel, reg, stocks))
    shuffled = compile_data((history.sample(frac=1, random_state=1), panel.sample(frac=1, random_state=2), reg, stocks))
    assert original == shuffled


def test_exact_duplicate_does_not_multiply_bonds():
    history, panel, reg, stocks = fixture()
    repeated = compile_data((history, pd.concat([panel, panel]), reg, stocks))
    assert repeated["coverage"]["identified_bond_rows"] == 6
    assert len(first(repeated)["bonds"]) == 1


def test_conflicting_duplicate_fails_closed():
    history, panel, reg, stocks = fixture()
    extra = history.iloc[[-1]].copy()
    extra["d1_g_spread_bp_matched"] = 999
    with pytest.raises(ValueError, match="conflicting duplicate"):
        compile_data((pd.concat([history, extra]), panel, reg, stocks))


def test_future_extension_does_not_change_frozen_calculation():
    history, panel, reg, stocks = fixture()
    original = compile_data((history, panel, reg, stocks))
    future = history.iloc[[-1]].copy()
    future["as_of"] = "2026-10-19"
    future["d1_g_spread_bp_matched"] = 1000
    assert compile_data((pd.concat([history, future]), panel, reg, stocks)) == original


def test_future_availability_not_admitted():
    history, panel, reg, stocks = fixture()
    history["available_at"] = history["as_of"] + "T20:00:00Z"
    history.loc[(history.issuer == "TEST0") & (history.as_of == END.isoformat()), "available_at"] = "2026-10-19T20:00:00Z"
    row = first(compile_data((history, panel, reg, stocks)))
    assert row["state"] == "insufficient_evidence"


def test_numeric_nan_never_leaks_to_json():
    data = fixture()
    data[1].loc[0, "price_clean"] = float("nan")
    result = compile_data(data)
    assert first(result)["bonds"][0]["price_clean"] is None
    json.dumps(result, allow_nan=False)


def test_required_columns_rejected():
    data = list(fixture())
    data[0] = data[0].drop(columns="matched_n")
    with pytest.raises(ValueError, match="missing columns"):
        compile_data(tuple(data))


def test_missing_sources_explicit(tmp_path):
    result = load_snapshot(tmp_path, as_of=END)
    assert result["status"] == "unavailable"
    assert "missing_inputs" in result["reason"]
    assert not result["issuers"]


def test_atomic_projection_json(tmp_path):
    expected = compile_data()
    path = tmp_path / "credit_dislocation.json"
    write_snapshot(expected, path)
    assert json.loads(path.read_text()) == expected
    assert not list(tmp_path.glob(".credit-dislocation-*"))


def test_adapter_uses_existing_store_without_source_writes(tmp_path):
    history, panel, reg, stocks = fixture()
    cc = tmp_path / "corp_bonds"
    (cc / "series").mkdir(parents=True)
    (tmp_path / "yahoo").mkdir()
    history.to_parquet(cc / "series/issuer_daily.parquet", index=False)
    panel.to_parquet(cc / "series/bond_panel_latest.parquet", index=False)
    (cc / "issuer_themes.json").write_text(json.dumps(reg))
    for ticker, series in stocks.items():
        series.rename("close").to_frame().to_parquet(tmp_path / "yahoo" / f"{ticker}.parquet")
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = load_snapshot(tmp_path, as_of=END)
    after = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after
    assert first(result)["relative_change_5_bp"] is None
    assert result["pricing_validation"]["status"] == "unqualified"
    assert result["provenance"]["issuers"]["sha256"]


@pytest.mark.parametrize("value", [pd.NA, float("nan"), 594918104, "US037833100５"])
def test_ambiguous_native_identifier_is_not_coerced(value):
    result = identifier(value)
    assert result["key"] is None
    assert result["checksum_valid"] is False

def test_unknown_call_flag_not_promoted_to_false():
    data = fixture()
    data[1]["near_par_call_flag"] = pd.Series([pd.NA] * 6, dtype="boolean")
    assert first(compile_data(data))["bonds"][0]["near_par_call_flag"] is None


def _write_qualified_store(root):
    from engine.corp_credit import bind_validation_inputs
    history, bonds, registry, stocks = fixture()
    cc = root / "corp_bonds"
    (cc / "series").mkdir(parents=True)
    (root / "baskets/ohlcv").mkdir(parents=True)
    history.to_parquet(cc / "series/issuer_daily.parquet", index=False)
    bonds["mv"] = bonds["par"] * 0.99
    bonds["accrued_pct"] = 1.0
    bonds["price_dirty"] = 100.0
    bonds.to_parquet(cc / "series/bond_panel_latest.parquet", index=False)
    (cc / "issuer_themes.json").write_text(json.dumps(registry))
    for ticker, series in stocks.items():
        series.to_frame("close").to_parquet(root / "baskets/ohlcv" / f"{ticker}.parquet")
    val = {"as_of": END.isoformat(), "overall": "PASS", "price_convention": "clean",
           "sample_metadata": {"LQD": {"as_of": END.isoformat()}},
           "criteria": {"b": {"LQD": {"median_bp": 1.0}}}}
    val = bind_validation_inputs(val, root, observation_as_of=END.isoformat(), calculation_convention="clean")
    (cc / "validation.json").write_text(json.dumps(val))
    return cc, val


def test_source_qualification_binds_actual_prices_and_artifact_hashes(tmp_path):
    cc, val = _write_qualified_store(tmp_path)
    before = (cc / "validation.json").read_bytes()
    result = load_snapshot(tmp_path, as_of=END)
    assert result["pricing_validation"]["status"] == "passed"
    assert result["pricing_validation"]["source_binding_verified"] is True
    assert result["coverage"]["paired_comparisons"] == 6
    assert val["input_binding"]["convention_verified_rows"] == 6
    assert (cc / "validation.json").read_bytes() == before


@pytest.mark.parametrize("change", ["absent", "failed", "wrong_day", "wrong_convention",
                                    "changed_panel", "changed_history", "future", "sample_date"])
def test_mismatched_or_missing_pricing_never_emits_derived_comparisons(tmp_path, change):
    cc, val = _write_qualified_store(tmp_path)
    if change == "failed": val["overall"] = "FAIL"
    if change == "wrong_day": val["input_binding"]["observation_as_of"] = "2026-10-15"
    if change == "wrong_convention": val["price_convention"] = "dirty"
    if change == "future": val["as_of"] = "2026-10-19"
    if change == "sample_date": val["sample_metadata"]["LQD"]["as_of"] = "2026-10-15"
    if change in {"changed_panel", "changed_history"}:
        name = "bond_panel_latest" if change == "changed_panel" else "issuer_daily"
        file = cc / "series" / f"{name}.parquet"
        frame = pd.read_parquet(file)
        column = "price_clean" if change == "changed_panel" else "d1_g_spread_bp_matched"
        frame.loc[0, column] += 1
        frame.to_parquet(file, index=False)
    (cc / "validation.json").write_text(json.dumps(val))
    if change == "absent": (cc / "validation.json").unlink()
    result = load_snapshot(tmp_path, as_of=END)
    assert result["pricing_validation"]["status"] == "unqualified"
    assert result["coverage"]["paired_comparisons"] == 0
    assert all(row["state"] == "insufficient_evidence" for row in result["issuers"])
    assert all(row["change_5"]["value_bp"] is None for row in result["issuers"])
    assert all(b["g_spread_bp"] is None for row in result["issuers"] for b in row["bonds"])


def test_missing_window_baseline_cannot_admit_a_multi_day_first_delta():
    from lib.nyse_calendar import session_n_back
    history, bonds, registry, stocks = fixture()
    start = session_n_back(END, 5).isoformat()
    history = history[~((history["issuer"] == "TEST0") & (history["as_of"] == start))]
    result = compile_snapshot(history, bonds, registry, stocks, as_of=END)
    assert first(result)["change_5"]["value_bp"] is None
    assert start in first(result)["change_5"]["missing_sessions"]


def test_equity_adapter_prefers_complete_whole_store_without_stitching(tmp_path):
    _write_qualified_store(tmp_path)
    path = tmp_path / "baskets/ohlcv/TEST0.parquet"
    complete = pd.read_parquet(path)
    complete.iloc[:-3].to_parquet(path)
    (tmp_path / "yahoo").mkdir()
    complete.to_parquet(tmp_path / "yahoo/TEST0.parquet")
    result = load_snapshot(tmp_path, as_of=END)
    assert result["provenance"]["equity:TEST0"]["store"] == "yahoo"
    assert first(result)["equity_5"]["value_pct"] == 0


def test_validation_receipt_change_changes_observation_identity(tmp_path):
    cc, val = _write_qualified_store(tmp_path)
    before = load_snapshot(tmp_path, as_of=END)
    val["criteria"]["b"]["LQD"]["median_bp"] = 2.0
    (cc / "validation.json").write_text(json.dumps(val))
    after = load_snapshot(tmp_path, as_of=END)
    assert before["observation_id"] != after["observation_id"]


def test_binding_refuses_a_falsely_declared_calculation_convention(tmp_path):
    from engine.corp_credit import bind_validation_inputs
    _, val = _write_qualified_store(tmp_path)
    with pytest.raises(ValueError, match="declared price convention"):
        bind_validation_inputs(val, tmp_path, observation_as_of=END.isoformat(), calculation_convention="dirty")


def test_validation_sample_selection_keeps_same_day_vintage(tmp_path):
    from engine.corp_credit import _load_validation_samples
    sample = tmp_path / "corp_bonds/validation_sample"
    sample.mkdir(parents=True)
    for day in ["2026-10-15", "2026-10-16"]:
        pd.DataFrame({"as_of": [day], "coupon": [5.0]}).to_parquet(sample / f"LQD_{day}.parquet")
    selected = _load_validation_samples(tmp_path, as_of="2026-10-15")["LQD"]
    assert selected["as_of"].iloc[0] == "2026-10-15"
    assert _load_validation_samples(tmp_path, as_of="2026-10-14")["LQD"] is None


def test_initial_price_probe_reuses_resolved_convention_without_acceptance(monkeypatch, tmp_path):
    import engine.corp_credit as cc
    panel = pd.DataFrame({"as_of": ["2026-10-15"] * 6})
    sample = pd.DataFrame({"as_of": ["2026-10-15"] * 6, "ytm_pct": [5.0] * 6})
    monkeypatch.setattr(cc, "_load_validation_samples", lambda *a, **k: {"LQD": sample})
    monkeypatch.setattr(cc, "_join_panel_to_sample", lambda *a: sample)
    calls = []
    def resolve(joined, day):
        calls.append((day, "ytm_pct_is" in joined))
        return {"verdict": "clean"}
    monkeypatch.setattr(cc, "resolve_price_convention", resolve)
    assert cc.initial_price_convention(panel, tmp_path) == "clean"
    assert calls == [("2026-10-15", True)]
    sample["as_of"] = "2026-10-14"
    assert cc.initial_price_convention(panel, tmp_path) == "dirty"
    assert len(calls) == 1
