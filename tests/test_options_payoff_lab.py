"""Options payoff lab: frozen catalog over the payoff engine, plus the emit leg.

Synthetic chains only. The store is monkeypatched. This file never reads a
real ThetaData tree and never writes data/ or site/ in the repo.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

import engine.options_payoff_lab as lab
import engine.options_skew as options_skew
import engine.thetadata_store as thetadata_store
import scripts.build_options_payoff_lab as builder

ASOF = "2026-09-01"
EXPIRY = "2026-10-01"
SPOT = 100.0
ROOTS = ("SPY", "QQQ", "IWM", "DIA")

CHAIN_COLUMNS = [
    "root", "expiration", "strike", "right", "date",
    "open", "high", "low", "close", "volume", "count", "bid_eod", "ask_eod",
    "open_interest",
    "implied_vol", "delta", "theta", "vega", "rho",
    "iv_error",
]

# Call delta falls toward 0 as the strike rises. Put delta is negative.
_DELTAS = {
    ("C", 90.0): 0.80,
    ("C", 95.0): 0.65,
    ("C", 100.0): 0.50,
    ("C", 105.0): 0.25,
    ("C", 110.0): 0.10,
    ("P", 90.0): -0.25,
    ("P", 95.0): -0.40,
    ("P", 100.0): -0.50,
    ("P", 105.0): -0.70,
    ("P", 110.0): -0.85,
}
_STRIKES = (90.0, 95.0, 100.0, 105.0, 110.0)

# Same whitelist the payoff engine test uses. entry_price is a quote field.
# The four authority keys are the engine's own disclosure that it does not
# rank, size, or originate a trade. A new key that merely contains those
# words still fails.
_FORBIDDEN = {
    "rank", "score", "rating", "conviction", "recommend", "signal", "size",
    "sizing", "allocation", "weight", "target", "stop", "action", "buy",
    "sell", "best", "top", "preferred", "alert", "entry",
}
_WHITELIST = {"entry_price"}
_AUTHORITY = {
    "entry_authority", "ranking_authority", "sizing_authority", "llm_origination",
}


def _chain_row(root, right, strike, *, iv=0.20, delta=None) -> dict:
    if delta is None:
        delta = _DELTAS[(right, strike)]
    return dict(
        root=root, expiration=EXPIRY, strike=strike, right=right, date=ASOF,
        open=5.0, high=5.5, low=4.5, close=5.0, volume=10.0, count=5,
        bid_eod=4.9, ask_eod=5.1, open_interest=50.0,
        implied_vol=iv, delta=delta, theta=-0.01, vega=0.1, rho=0.05, iv_error=0.0,
    )


def _chain_frame(root, *, iv=0.20, delta_nan=False) -> pd.DataFrame:
    rows = []
    for strike in _STRIKES:
        for right in ("C", "P"):
            delta = float("nan") if delta_nan else _DELTAS[(right, strike)]
            rows.append(_chain_row(root, right, strike, iv=iv, delta=delta))
    return pd.DataFrame(rows, columns=CHAIN_COLUMNS)


def _skew_frame(root) -> pd.DataFrame:
    rows = []
    for strike in _STRIKES:
        for right, is_call in (("C", True), ("P", False)):
            rows.append({
                "underlying": root,
                "expiry": EXPIRY,
                "K": strike,
                "T": 30.0 / 365.0,
                "iv": 0.20,
                "delta": _DELTAS[(right, strike)],
                "is_call": is_call,
                "spot": SPOT,
                "oi": 50.0,
                "volume": 10.0,
                "asof": ASOF,
            })
    return pd.DataFrame(rows)


def _install_store(monkeypatch, chains, frames):
    def fake_chain(date, root, store=None):
        return chains.get(root, pd.DataFrame(columns=CHAIN_COLUMNS))

    def fake_load(asof, store=None, roots=None):
        root = roots[0]
        frame = frames.get(root)
        if frame is None:
            return None, "no_chain_for_date"
        return frame, "ok"

    monkeypatch.setattr(thetadata_store, "chain", fake_chain)
    monkeypatch.setattr(options_skew, "load_chain", fake_load)


def _codes(payload) -> set[str]:
    found = set()

    def walk(value):
        if isinstance(value, dict):
            code = value.get("code")
            if isinstance(code, str) and "reason" in value:
                found.add(code)
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload)
    return found


def _keys(payload) -> set[str]:
    found = set()

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                found.add(str(key).lower())
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload)
    return found


def test_four_roots_build_four_structures_each(monkeypatch):
    chains = {root: _chain_frame(root) for root in ROOTS}
    frames = {root: _skew_frame(root) for root in ROOTS}
    _install_store(monkeypatch, chains, frames)
    payload = lab.build_payoff_lab(ASOF, store="stub")
    assert payload["schema"] == "mastermind.options_payoff_lab/v1"
    assert payload["asof"] == ASOF
    assert payload["source"] == "thetadata"
    assert [row["root"] for row in payload["roots"]] == list(ROOTS)
    assert payload["counts"]["roots_priced"] == 4
    assert payload["counts"]["structures_built"] == 16
    assert payload["counts"]["structures_null"] == 0
    for row in payload["roots"]:
        assert row["spot"] == pytest.approx(SPOT)
        assert row["expiration"] == EXPIRY
        assert row["tenor_days"] == pytest.approx(30.0)
        assert row["states"] == []
        names = [item["name"] for item in row["structures"]]
        assert names == list(lab.CATALOG)
        by_name = {item["name"]: item for item in row["structures"]}
        straddle = by_name["atm_straddle"]
        assert [rule["strike"] for rule in straddle["selection_rule"]] == [100.0, 100.0]
        assert {rule["rule"] for rule in straddle["selection_rule"]} == {"nearest_spot"}
        rr = by_name["rr25"]
        assert [rule["rule"] for rule in rr["selection_rule"]] == ["delta", "delta"]
        assert [rule["strike"] for rule in rr["selection_rule"]] == [105.0, 90.0]
        put_spread = by_name["put_spread_95_90"]
        assert [rule["strike"] for rule in put_spread["selection_rule"]] == [95.0, 90.0]
        call_spread = by_name["call_spread_105_110"]
        assert [rule["strike"] for rule in call_spread["selection_rule"]] == [105.0, 110.0]
        for item in row["structures"]:
            spots = item["expiry_payoff"]["spots"]
            assert len(spots) == 41
            assert spots[0] == pytest.approx(SPOT * 0.80)
            assert spots[-1] == pytest.approx(SPOT * 1.20)
            assert set(item["scenario_grids"]) == {"0", "7", "21"}
            days = [point["days_forward"] for point in item["greeks_drift"]["points"]]
            assert days == [0, 7, 21]
            assert item["summary"]["max_loss"] is not None
            assert item["evidence_recipe"]["authority"]["entry_authority"] == "none"


def test_empty_chain_nulls_that_root_and_leaves_the_others(monkeypatch):
    chains = {root: _chain_frame(root) for root in ROOTS}
    frames = {root: _skew_frame(root) for root in ROOTS}
    chains["IWM"] = pd.DataFrame(columns=CHAIN_COLUMNS)
    frames["IWM"] = None
    _install_store(monkeypatch, chains, frames)
    payload = lab.build_payoff_lab(ASOF, store="stub")
    by_root = {row["root"]: row for row in payload["roots"]}
    assert by_root["IWM"]["structures"] == []
    assert by_root["IWM"]["states"][0]["code"] == "CHAIN_EMPTY"
    assert payload["counts"]["roots_priced"] == 3
    assert payload["counts"]["structures_built"] == 12
    assert payload["counts"]["structures_null"] == 4
    for root in ("SPY", "QQQ", "DIA"):
        assert len(by_root[root]["structures"]) == 4


def test_missing_spot_is_typed_null(monkeypatch):
    chains = {"SPY": _chain_frame("SPY")}
    frames = {"SPY": _skew_frame("SPY").assign(spot=float("nan"))}
    _install_store(monkeypatch, chains, frames)
    payload = lab.build_payoff_lab(ASOF, store="stub", roots=("SPY",))
    assert payload["roots"][0]["states"][0]["code"] == "SPOT_UNAVAILABLE"
    assert payload["roots"][0]["structures"] == []
    assert payload["counts"]["structures_built"] == 0


def test_no_usable_tenor_is_typed_null(monkeypatch):
    chains = {"SPY": _chain_frame("SPY")}
    frame = _skew_frame("SPY")
    frame["T"] = 0.0
    _install_store(monkeypatch, chains, {"SPY": frame})
    payload = lab.build_payoff_lab(ASOF, store="stub", roots=("SPY",))
    assert payload["roots"][0]["states"][0]["code"] == "NO_USABLE_TENOR"
    assert payload["counts"]["roots_priced"] == 0


def test_missing_iv_nulls_only_vol_dependent_outputs(monkeypatch):
    frame = _chain_frame("SPY", iv=float("nan"), delta_nan=True)
    _install_store(monkeypatch, {"SPY": frame}, {"SPY": _skew_frame("SPY")})
    payload = lab.build_payoff_lab(ASOF, store="stub", roots=("SPY",))
    row = payload["roots"][0]
    assert payload["counts"]["structures_built"] == 4
    rr = {item["name"]: item for item in row["structures"]}["rr25"]
    assert [rule["rule"] for rule in rr["selection_rule"]] == ["moneyness", "moneyness"]
    assert [rule["strike"] for rule in rr["selection_rule"]] == [105.0, 95.0]
    for item in row["structures"]:
        assert item["expiry_payoff"]["max_loss"] is not None or item["expiry_payoff"]["max_gain"] is not None
        for grid in item["scenario_grids"].values():
            for pnl_row in grid["pnl"]:
                assert all(cell is None for cell in pnl_row)
        for point in item["greeks_drift"]["points"]:
            assert point["net"]["delta"] is None
        assert "LEG_IV_MISSING" in {state["code"] for state in item["states"]}


def test_artifact_has_no_entry_or_sizing_keys(monkeypatch):
    chains = {root: _chain_frame(root) for root in ROOTS}
    frames = {root: _skew_frame(root) for root in ROOTS}
    _install_store(monkeypatch, chains, frames)
    payload = lab.build_payoff_lab(ASOF, store="stub")
    text = json.dumps(payload)
    keys = _keys(json.loads(text))
    keys -= _WHITELIST
    keys -= _AUTHORITY
    hits = set()
    for name in keys:
        tokens = set(name.split("_")) | {name}
        hits |= tokens & _FORBIDDEN
    assert not hits, hits
    assert "LEG_IV_MISSING" not in _codes(payload)


def test_emit_never_opens_the_store(monkeypatch, tmp_path, capsys):
    def boom(*_args, **_kwargs):
        raise AssertionError("emit opened the store")

    monkeypatch.setattr(thetadata_store, "chain", boom)
    monkeypatch.setattr(thetadata_store, "resolve_thetadata_store", boom)
    monkeypatch.setattr(options_skew, "load_chain", boom)
    data = tmp_path / "data" / "options_payoff_lab"
    data.mkdir(parents=True)
    site = tmp_path / "site"
    payload = {
        "schema": lab.SCHEMA,
        "asof": ASOF,
        "source": "thetadata",
        "roots": [],
        "counts": {"roots_priced": 1, "structures_built": 3, "structures_null": 0},
        "states": [],
    }
    (data / "latest.json").write_text(json.dumps(payload), encoding="utf-8")
    rc = builder.main([
        "--emit",
        "--data-dir", str(data),
        "--site-dir", str(site),
    ])
    assert rc == 0
    out = json.loads((site / "options_payoff_lab" / "latest.json").read_text(encoding="utf-8"))
    assert out["ledger_asof"] == ASOF
    assert out["accrual_state"] == "ledger_only"
    assert out["n"] == 3
    assert "opened the store" not in capsys.readouterr().err


def test_absent_data_file_emits_honest_null(tmp_path):
    data = tmp_path / "missing"
    site = tmp_path / "site"
    rc = builder.main(["--emit", "--data-dir", str(data), "--site-dir", str(site)])
    assert rc == 0
    out = json.loads((site / "options_payoff_lab" / "latest.json").read_text(encoding="utf-8"))
    assert out["accrual_state"] == "absent"
    assert out["n"] == 0
    assert out["ledger_asof"] is None
    assert out["counts"]["structures_built"] == 0
    assert out["states"][0]["code"] == "ABSENT"


def test_unresolved_store_warns_and_does_not_fail(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(thetadata_store, "resolve_thetadata_store", lambda **_kwargs: None)
    data = tmp_path / "data" / "options_payoff_lab"
    rc = builder.main(["--accrue", "--data-dir", str(data)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "::warning title=options-payoff-lab-source::" in captured.out
    assert not (data / "latest.json").exists()


def test_module_imports_tenor_and_spot_from_options_skew():
    text = Path(lab.__file__).read_text(encoding="utf-8")
    assert "import engine.options_skew as options_skew" in text
    assert "options_skew.load_chain" in text
    assert "options_skew._nearest_expiry" in text
    lowered = text.lower()
    for banned in ("d1", "norm.cdf", "normal_cdf", "erf(", "closed form", "black_scholes"):
        assert banned not in lowered
