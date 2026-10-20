"""Synthetic offline source composition: no terms/default/model promotion."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import runpy
from unittest.mock import MagicMock

import pandas as pd
import pytest

from lib.options_source_receipts import (ACQUISITION_COLUMN, THETA_ENDPOINTS,
    theta_acquisition, native_acquisitions, massive_reference_terms)
from engine.options_exposure_projection import (compose_native_exposure_context,
    exposure_input_digest, build_exposure_projection)

ASOF = "2026-10-15"
EXPIRY = "2026-10-23"
RECEIVED = "2026-10-15T20:01:00+00:00"


def book():
    # Reuse the producer's synthetic contract book, not a provider payload.
    return runpy.run_path("tests/test_options_exposure_projection.py")["book"]()


def attach(frame, kind):
    frame = frame.copy()
    frame[ACQUISITION_COLUMN] = theta_acquisition(THETA_ENDPOINTS[kind],
        {"symbol": "SPY", "expiration": "*", "start_date": 20261015,
         "end_date": 20261015, "format": "csv"}, b"synthetic CSV", origin="http://theta-test:25503", received_at=RECEIVED)
    return frame


def reference():
    ticker = "O:SPY261023C00100000"
    c = dict(ticker=ticker, underlying_ticker="SPY", contract_type="call",
        expiration_date=EXPIRY, strike_price=100, exercise_style="american", shares_per_contract=100)
    return dict(schema="options_reference_capability_observation/v1", state="response_observed",
        origin="https://api.polygon.io", path="/v3/reference/options/contracts/" + ticker,
        capability={"http_status": 200, "verdict": "entitled"}, contract=c,
        field_presence={k: True for k in c}, completed_at=RECEIVED, payload_sha256="a" * 64)


def test_large_reference_composition_preserves_existing_evidence_and_duplicate_refusal():
    observations=[];terms=[]
    for strike in range(100,3100):
        obs=reference();ticker=f'O:SPY261023C{strike*1000:08d}'
        obs['contract'].update(ticker=ticker,strike_price=strike)
        obs['path']='/v3/reference/options/contracts/'+ticker
        observations.append(obs)
        term=massive_reference_terms(obs,'SPY','SEC:SPY')
        term['owner_evidence']='retained'
        terms.append(term)
    ctx=dict(security_id='SEC:SPY',contract_terms=terms,contract_reference_observations=observations,
             input_sha256=exposure_input_digest(pd.DataFrame(),pd.DataFrame(),ASOF,'SPY'))
    out=compose_native_exposure_context(pd.DataFrame(),pd.DataFrame(),ASOF,'SPY',context=ctx)
    assert len(out['contract_terms'])==3000
    assert all(t['owner_evidence']=='retained' and t['reference_observation_ref']==t['terms_ref']
               for t in out['contract_terms'])
    assert out['contract_terms'][-1]['strike']==3099
    ctx['contract_terms']=terms+[deepcopy(terms[-1])]
    with pytest.raises(ValueError,match='Ambiguous owner terms'):
        compose_native_exposure_context(pd.DataFrame(),pd.DataFrame(),ASOF,'SPY',context=ctx)


def test_reference_maps_only_observed_fields_without_contract_or_model_defaults():
    obs = reference()
    term = massive_reference_terms(obs, "SPY", "SEC:SPY")
    assert term["exercise_style"] == "american" and term["shares_per_contract"] == 100
    assert term["series_id"] == obs["contract"]["ticker"]
    assert term["available_at"] == RECEIVED
    assert term["availability_basis"] == "collector_observed_known_by"
    for absent in ("additional_underlyings", "correction", "currency", "multiplier",
                   "deliverable", "deliverable_ref", "economic_expiry_at", "model_ref"):
        assert absent not in term
    assert obs == reference()
    obs["contract"]["additional_underlyings"] = [{"type": "currency", "underlying": "USD", "amount": 5}]
    obs["field_presence"]["additional_underlyings"] = True
    obs["contract"]["shares_per_contract"] = 150
    adjusted = massive_reference_terms(obs, "SPY")
    assert adjusted["shares_per_contract"] == 150 and adjusted["additional_underlyings"] == obs["contract"]["additional_underlyings"]
    assert "deliverable" not in adjusted


@pytest.mark.parametrize("mutate", [
    lambda x: x["capability"].update(http_status=403, verdict="not_entitled"),
    lambda x: x["contract"].update(underlying_ticker="QQQ"),
    lambda x: x["contract"].update(strike_price=101),
    lambda x: x["contract"].update(contract_type="put"),
    lambda x: x.update(completed_at="2099-01-01T00:00:00Z"),
    lambda x: x.update(completed_at="2026-10-15T20:01:00"),
    lambda x: x["field_presence"].update(shares_per_contract=False),
    lambda x: x.update(payload_sha256="bad"),
])
def test_reference_refuses_failed_foreign_mismatched_or_unclocked_observations(mutate):
    obs = reference(); mutate(obs)
    with pytest.raises(ValueError):
        massive_reference_terms(obs, "SPY")


def test_complete_native_receipt_is_persisted_in_existing_rows_and_decoded_once(tmp_path, monkeypatch):
    from collectors import thetadata as td
    raw = ("symbol,expiration,strike,right,timestamp,open_interest\n"
           "SPY,2026-10-23,100,CALL,2026-10-15T06:30:00,100\n").encode()
    response = MagicMock(status_code=200)
    response.iter_content = lambda **kw: iter([raw[:30], raw[30:]])
    session = MagicMock(); session.get.return_value = response
    fetched = td._get_csv(session, THETA_ENDPOINTS["oi"],
        {"symbol": "SPY", "expiration": "*", "start_date": 20261015, "end_date": 20261015})
    normalized = td._normalize_oi_df(fetched)
    path = tmp_path / "oi.parquet"; normalized.to_parquet(path, index=False)
    stored = pd.read_parquet(path)
    receipt = json.loads(stored[ACQUISITION_COLUMN].iloc[0])
    assert receipt["response_sha256"] == hashlib.sha256(raw).hexdigest()
    assert receipt["endpoint"] == THETA_ENDPOINTS["oi"]
    assert receipt["parameters"]["format"] == "csv"
    assert "version" not in receipt["parameters"] and "model_ref" not in receipt
    assert datetime.fromisoformat(receipt["received_at"]).tzinfo is not None
    many = pd.concat([stored] * 2000, ignore_index=True)
    from lib import options_source_receipts as module
    loads = module.json.loads; calls = []
    monkeypatch.setattr(module.json, "loads", lambda value: (calls.append(value), loads(value))[1])
    assert len(native_acquisitions(many, "SPY", ASOF, "oi")) == 1
    assert len(calls) == 1


@pytest.mark.parametrize("bad", ["missing", "wrong_root", "wrong_endpoint", "outside_window", "future", "malformed"])
def test_partial_or_mismatched_native_receipts_never_fill_availability(bad):
    g, oi, _ = book(); g = attach(g, "greeks"); oi = attach(oi, "oi")
    if bad == "missing": oi.loc[0, ACQUISITION_COLUMN] = None
    elif bad == "malformed": oi.loc[0, ACQUISITION_COLUMN] = "{broken"
    else:
        rec = json.loads(oi.loc[0, ACQUISITION_COLUMN])
        if bad == "wrong_root": rec["parameters"]["symbol"] = "QQQ"
        if bad == "wrong_endpoint": rec["endpoint"] = THETA_ENDPOINTS["greeks"]
        if bad == "outside_window": rec["parameters"]["start_date"] = 20261016
        if bad == "future": rec["received_at"] = "2099-01-01T00:00:00Z"
        oi.loc[0, ACQUISITION_COLUMN] = json.dumps(rec)
    ctx = {"root": "SPY", "input_sha256": exposure_input_digest(g, oi, ASOF, "SPY")}
    out = compose_native_exposure_context(g, oi, ASOF, "SPY", context=ctx)
    assert out["clocks"]["greeks_available_at"] == RECEIVED
    assert "oi_available_at" not in out["clocks"] and "source_snapshot_ref" not in out


def test_composition_uses_actual_known_by_and_keeps_missing_qualifiers_unknown():
    g, oi, _ = book(); g = attach(g, "greeks"); oi = attach(oi, "oi")
    ctx = dict(root="SPY", security_id="SEC:SPY", input_sha256=exposure_input_digest(g, oi, ASOF, "SPY"),
        contract_reference_observations=[reference()])
    before = deepcopy(ctx)
    out = compose_native_exposure_context(g, oi, ASOF, "SPY", context=ctx)
    assert ctx == before
    assert out["clocks"]["greeks_available_at"] == RECEIVED
    assert out["clocks"]["oi_available_at"] == RECEIVED
    assert out["clocks"]["source_session"] == ASOF
    assert out["source_snapshot_ref"].startswith("capture:sha256:")
    assert "option_observed_at" not in out["clocks"] and "underlying_observed_at" not in out["clocks"]
    assert "greek_provenance" not in out and "rights_decision_ref" not in out
    assert out["contract_terms"][0]["shares_per_contract"] == 100
    p = build_exposure_projection(g, oi, ASOF, "SPY", context=out)
    assert p["metrics"]["gamma"]["qualified"] == 0
    assert p["metrics"]["gamma"]["exclusions"] == {"source_availability_unknown": 2}
    assert compose_native_exposure_context(g, oi, ASOF, "SPY", context=None) is None


def test_late_capture_cannot_move_explicit_historical_cutoff_or_rebind_changed_rows():
    g, oi, ctx = book(); g = attach(g, "greeks"); oi = attach(oi, "oi")
    ctx["input_sha256"] = exposure_input_digest(g, oi, ASOF, "SPY")
    out = compose_native_exposure_context(g, oi, ASOF, "SPY", context=ctx)
    assert out["clocks"]["available_at"] == ctx["clocks"]["available_at"]
    assert build_exposure_projection(g, oi, ASOF, "SPY", context=out)["metrics"]["gamma"]["exclusions"] == {"source_after_availability_cutoff": 2}
    changed = oi.copy(); changed.loc[0, "open_interest"] += 1
    assert compose_native_exposure_context(g, changed, ASOF, "SPY", context=ctx) == ctx


def test_builder_composes_reference_through_existing_context_and_preserves_legacy(monkeypatch):
    from scripts import build_options_hub_nightly as builder
    from engine.options_hub import compute_gex
    from engine.vex_engine import compute_vex
    g, oi, _ = book(); g["vega"] = [.1, .1]
    g = attach(g, "greeks"); oi = attach(oi, "oi")
    ctx = dict(root="SPY", security_id="SEC:SPY", input_sha256=exposure_input_digest(g, oi, ASOF, "SPY"),
        contract_reference_observations=[reference()])
    monkeypatch.setattr(builder, "_load_greeks", lambda *a: g.copy())
    monkeypatch.setattr(builder, "_load_oi_for_date", lambda *a: oi.copy())
    monkeypatch.setattr(builder, "_load_yahoo", lambda *a: None)
    _, out, _ = builder.build_root("SPY", ASOF, None, exposure_context=ctx)
    assert out["exposure_projection"]["clocks"]["oi_available_at"] == RECEIVED
    assert out["exposure_projection"]["metrics"]["gamma"]["qualified"] == 0
    _, default, _ = builder.build_root("SPY", ASOF, None)
    assert default["exposure_projection"]["cells_status"] == "source_unqualified"
    # Two fresh receipts for numerically identical observations are not two contracts.
    repeated_g = pd.concat([g, attach(g.iloc[[0]], "greeks")], ignore_index=True)
    repeated_o = pd.concat([oi, attach(oi.iloc[[0]], "oi")], ignore_index=True)
    rec = json.loads(repeated_g.loc[2, ACQUISITION_COLUMN]); rec["received_at"] = "2026-10-15T20:02:00Z"
    repeated_g.loc[2, ACQUISITION_COLUMN] = json.dumps(rec)
    rec = json.loads(repeated_o.loc[2, ACQUISITION_COLUMN]); rec["received_at"] = "2026-10-15T20:02:00Z"
    repeated_o.loc[2, ACQUISITION_COLUMN] = json.dumps(rec)
    baseline = compute_gex(g, oi, ASOF, "SPY")
    duplicate = compute_gex(repeated_g, repeated_o, ASOF, "SPY")
    assert {k: v for k, v in baseline.items() if k != "exposure_projection"} == {
        k: v for k, v in duplicate.items() if k != "exposure_projection"}
    assert compute_vex(g, oi, ASOF, "SPY") == compute_vex(repeated_g, repeated_o, ASOF, "SPY")
    assert duplicate["exposure_projection"]["population"]["received_rows"] == 3


def test_reference_conflicts_and_late_terms_do_not_rewrite_owner_evidence():
    g, oi, ctx = book()
    # A different economic series identifier may not silently replace the owner.
    ctx["contract_reference_observations"] = [reference()]
    with pytest.raises(ValueError, match="Conflicting reference terms"):
        compose_native_exposure_context(g, oi, ASOF, "SPY", context=ctx)
    ctx["contract_terms"][0]["series_id"] = reference()["contract"]["ticker"]
    out = compose_native_exposure_context(g, oi, ASOF, "SPY", context=ctx)
    assert pd.Timestamp(out["contract_terms"][0]["available_at"]) == pd.Timestamp(RECEIVED)
    assert build_exposure_projection(g, oi, ASOF, "SPY", context=out)["metrics"]["gamma"]["exclusions"] == {"series_terms_availability_unqualified": 1}
