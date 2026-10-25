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


@pytest.mark.parametrize('root', ['SPY', 'QQQ'])
def test_opted_in_writer_receipt_survives_backfill_and_daily_year_merge(tmp_path, monkeypatch, root):
    from datetime import date
    from collectors import thetadata as td
    from scripts import backfill_thetadata_eod as backfill, topup_thetadata_day as daily

    monkeypatch.setenv('THETADATA_DATED_GREEKS_V1_ROOTS', 'SPY,QQQ')
    day = date(2026, 10, 22)
    captured = '2026-10-23T10:00:00Z'
    raw = b'synthetic complete Greek CSV response'
    receipt = theta_acquisition(THETA_ENDPOINTS['greeks'], dict(symbol=root,
        expiration='*', start_date=20261022, end_date=20261022, right='both',
        format='csv', version='1'), raw, origin='http://theta-test:25503', received_at=captured)
    fresh = pd.DataFrame([dict(root=root, expiration=pd.Timestamp('2026-10-30'),
        strike=100.0, right='C', date=pd.Timestamp(day), gamma=0.1,
        **{ACQUISITION_COLUMN: receipt})])
    monkeypatch.setattr(td, 'bulk_eod', lambda *a, **kw: pd.DataFrame())
    monkeypatch.setattr(td, 'bulk_open_interest', lambda *a, **kw: pd.DataFrame())
    def greeks(r, exp, start, end, **kwargs):
        assert r == root and (exp, start, end) == (0, day, day)
        assert kwargs == {'order': 3, 'version': '1'}
        return fresh.copy()
    monkeypatch.setattr(td, 'bulk_greeks', greeks)
    monkeypatch.setattr(backfill, '_store_dir', lambda: tmp_path / 'backfill')
    assert backfill._pull_root_year(root, 2026, day, day)
    written = pd.read_parquet(backfill._parquet_path('greeks', root, 2026))
    assert written[ACQUISITION_COLUMN].tolist() == [receipt]
    assert native_acquisitions(written, root, str(day), 'greeks', now=captured)[0]['response_sha256'] == hashlib.sha256(raw).hexdigest()

    # Existing unversioned days remain unversioned; only the actually captured
    # new day receives a receipt when daily maintenance appends to the year.
    store = tmp_path / 'daily'
    old = fresh.drop(columns=[ACQUISITION_COLUMN]).copy()
    old['date'] = pd.Timestamp('2026-10-21')
    daily._merge_day(store, 'greeks', root, date(2026, 10, 21), old)
    assert daily._ensure_one_cell(store, 'greeks', root, day, lambda: written) == 'complete'
    year = pd.read_parquet(store / 'greeks' / root / '2026.parquet')
    previous = year[year.date.eq(pd.Timestamp('2026-10-21'))]
    current = year[year.date.eq(pd.Timestamp(day))]
    assert previous[ACQUISITION_COLUMN].isna().all()
    assert native_acquisitions(previous, root, '2026-10-21', 'greeks', now=captured) is None
    assert current[ACQUISITION_COLUMN].tolist() == [receipt]
    assert native_acquisitions(current, root, str(day), 'greeks', now=captured)

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


def test_second_order_source_evidence_is_bound_without_changing_history_only_digest():
    g, oi, _ = book()
    original = exposure_input_digest(g, oi, ASOF, 'SPY')
    frame = g.copy(); frame['_theta_second_acquisition'] = 'synthetic-second-response'
    with_second = exposure_input_digest(frame, oi, ASOF, 'SPY')
    assert with_second != original
    frame['second_order_underlying_price'] = 101
    assert exposure_input_digest(frame, oi, ASOF, 'SPY') != with_second
    frame.drop(columns=['_theta_second_acquisition', 'second_order_underlying_price'], inplace=True)
    assert exposure_input_digest(frame, oi, ASOF, 'SPY') == original


def test_snapshot_capture_cannot_satisfy_the_dated_history_numerical_reader():
    from lib.options_source_receipts import THETA_SNAPSHOT_ENDPOINTS, native_snapshot_acquisitions
    g, _, _ = book()
    frame = g.copy()
    frame[ACQUISITION_COLUMN] = theta_acquisition(THETA_SNAPSHOT_ENDPOINTS['second'],
        dict(symbol='SPY', expiration='*', strike='*', format='csv', version='latest'),
        b'synthetic-snapshot', origin='http://theta-test:25503', received_at=RECEIVED)
    assert native_snapshot_acquisitions(frame, 'SPY', 'second', now=RECEIVED)
    assert native_acquisitions(frame, 'SPY', ASOF, 'greeks', now=RECEIVED) is None


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


def test_ordinary_qqq_terms_are_explicit_rule_interpretation_not_raw_defaults():
    from lib.options_source_receipts import ordinary_etf_terms, ordinary_spy_terms
    obs=reference();c=obs['contract'];c.update(ticker='O:QQQ261023C00100000',underlying_ticker='QQQ')
    obs['path']='/v3/reference/options/contracts/'+c['ticker']
    term=massive_reference_terms(obs,'QQQ','SEC:US-XNAS-QQQ')
    assert 'multiplier' not in term and 'additional_underlyings' not in term
    before=deepcopy(term)
    out=ordinary_etf_terms(term,root='QQQ')
    assert term==before and out['currency']=='USD' and out['multiplier']==100
    assert out['deliverable']=='100_underlying_shares'
    assert out['term_interpretation']['policy']=='occ_standard_qqq_etf/v1'
    assert out['term_interpretation']['additional_underlyings_field_present'] is False
    assert 'additional_underlyings' not in out and 'correction' not in out
    assert 'economic_expiry_at' not in out and 'model_ref' not in out
    assert ordinary_spy_terms(term)==term


@pytest.mark.parametrize('change',[
    {'root':'SPY'}, {'shares_per_contract':10}, {'exercise_style':'european'},
    {'additional_underlyings':[{'type':'cash','amount':1}]}, {'terms_ref':'https://untrusted.example/contracts'},
])
def test_ordinary_qqq_terms_withhold_adjusted_unknown_or_foreign_terms(change):
    from lib.options_source_receipts import ordinary_etf_terms
    term=dict(root='QQQ',shares_per_contract=100,exercise_style='american',
        terms_ref='https://api.polygon.io/v3/reference/options/contracts#sha256='+'a'*64)
    term.update(change)
    assert ordinary_etf_terms(term,root='QQQ')==term


def test_qqq_terms_policy_cannot_be_selected_by_an_absent_policy():
    from lib.options_source_receipts import ordinary_etf_terms
    obs=reference();c=obs['contract'];c.update(ticker='O:QQQ261023C00100000',underlying_ticker='QQQ')
    obs['path']='/v3/reference/options/contracts/'+c['ticker']
    ctx=dict(root='QQQ',security_id='SEC:US-XNAS-QQQ',contract_terms=[],
             contract_reference_observations=[obs],input_sha256=exposure_input_digest(pd.DataFrame(),pd.DataFrame(),ASOF,'QQQ'))
    out=compose_native_exposure_context(pd.DataFrame(),pd.DataFrame(),ASOF,'QQQ',context=ctx)
    assert 'multiplier' not in out['contract_terms'][0]
    ctx['term_policy']='occ_standard_qqq_etf/v1'
    out=compose_native_exposure_context(pd.DataFrame(),pd.DataFrame(),ASOF,'QQQ',context=ctx)
    assert out['contract_terms'][0]['multiplier']==100
    assert ordinary_etf_terms(out['contract_terms'][0],root='QQQ')['multiplier']==100


@pytest.mark.parametrize("root",["SPY","QQQ"])
@pytest.mark.parametrize("field,value",[("currency","EUR"),("multiplier",50),("deliverable","cash"),("currency",None)])
def test_ordinary_terms_never_overwrite_contradicting_explicit_economics(root,field,value):
    from lib.options_source_receipts import ordinary_etf_terms
    term=dict(root=root,shares_per_contract=100,exercise_style="american",
        terms_ref="https://api.massive.com/v3/reference/options/contracts#sha256="+"a"*64)
    term[field]=value
    assert ordinary_etf_terms(term,root=root)==term


@pytest.mark.parametrize("ref",[
    "https://api.massive.com/v3/reference/options/contracts-mirror.example/t#sha256="+"a"*64,
    "https://api.massive.com/v3/reference/options/contracts/other/O:QQQ261023C00100000#sha256="+"a"*64,
    "https://api.massive.com:443/v3/reference/options/contracts#sha256="+"a"*64,
    "https://api.massive.com/v3/reference/options/contracts?unverified=true#sha256="+"a"*64,
    "https://api.massive.com/v3/reference/options/contracts#sha256=invalid",
    "https://[malformed",
    "https://api.massive.com/v3/reference/options/contracts/#sha256="+"a"*64,
])
def test_ordinary_terms_require_exact_mapped_reference_endpoint(ref):
    from lib.options_source_receipts import ordinary_etf_terms
    term=dict(root="QQQ",shares_per_contract=100,exercise_style="american",terms_ref=ref)
    assert ordinary_etf_terms(term,root="QQQ")==term


def test_history_oi_rejects_a_greek_algorithm_version_in_actual_parameters():
    params=dict(symbol="SPY",expiration="*",start_date=20261015,end_date=20261015,format="csv",version="2")
    with pytest.raises(ValueError,match="parameters"):
        theta_acquisition(THETA_ENDPOINTS["oi"],params,b"synthetic",origin="http://theta-test:25503",received_at=RECEIVED)
    _,oi,_=book();oi=attach(oi,"oi")
    rec=json.loads(oi[ACQUISITION_COLUMN].iloc[0]);rec["parameters"]["version"]="2"
    oi[ACQUISITION_COLUMN]=json.dumps(rec)
    assert native_acquisitions(oi,"SPY",ASOF,"oi",now=RECEIVED) is None
