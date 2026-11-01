"""Tests for prospective native Theta snapshot provenance.

Everything here is lane-local and mocked: a fake HTTP session, synthetic CSV
bytes and pinned receipt clocks (never a monkeypatched historical wall clock).
Imports are explicit and unconditional -- a missing API is a failure, not a skip.
"""
import hashlib
import json

import pandas as pd
import pytest

from lib import options_source_receipts as osr
from collectors import thetadata
from scripts import chain_snapshot_poller as csp

ORIGIN = "https://api.thetadata.us"
NOW = "2026-10-19T21:00:00+00:00"
RECEIVED = "2026-10-19T20:00:00+00:00"
SECOND_TS_COL = "second_order_timestamp"
SECOND_UNDER_COL = "second_order_underlying_timestamp"
SECOND_ACQ_COL = "_theta_second_acquisition"
ACQ = osr.ACQUISITION_COLUMN


def _receipt(endpoint, params, *, received_at=RECEIVED, raw=b"synthetic-raw"):
    return osr.theta_acquisition(endpoint, params, raw, origin=ORIGIN, received_at=received_at)


def _wildcards(root="SPY"):
    return {"symbol": root, "expiration": "*", "strike": "*", "format": "csv"}


def _rows():
    return [
        {"root": "SPY", "expiration": "2026-12-18", "strike": 600.0, "right": "C", "delta": 0.52},
        {"root": "SPY", "expiration": "2026-12-18", "strike": 605.0, "right": "P", "delta": -0.47},
    ]


def _snap_frame(receipt, rows=None, *, raw_ts="2026-10-19 15:59:58.123456"):
    df = pd.DataFrame(rows if rows is not None else _rows())
    df["timestamp"] = raw_ts
    df["underlying_timestamp"] = "2026-10-19 15:59:59.000000"
    df[ACQ] = receipt
    return df


class _Response:
    def __init__(self, body):
        self._body = body
        self.status_code = 200
        self.text = body.decode("utf-8", "replace")

    def iter_content(self, chunk_size=65536):
        yield self._body

    def close(self):
        pass


class _Session:
    def __init__(self, body):
        self._response = _Response(body)
        self.calls = []

    def get(self, url, params=None, timeout=None, stream=False, **kw):
        self.calls.append({"url": url, "params": dict(params or {})})
        return self._response


CSV_HEADER = ("symbol,expiration,right,strike,underlying_price,bid,ask,delta,theta,"
              "vega,rho,epsilon,lambda,implied_vol,iv_error,timestamp,underlying_timestamp\n")
CSV_BODY = CSV_HEADER + (
    "SPY,2026-12-18,C,600.0,600.25,5.10,5.40,0.52,-0.031,0.182,0.021,0.053,0.011,0.21,0.004,"
    "2026-10-19 15:59:58.123456,2026-10-19 15:59:59.000000\n"
    "SPY,2026-12-18,P,605.0,600.25,4.20,4.45,-0.47,-0.028,0.191,0.019,0.055,0.010,0.22,0.005,"
    "2026-10-19 15:59:58.123456,2026-10-19 15:59:59.000000\n")


def _csv_session():
    return _Session(CSV_BODY.encode())


def test_snapshot_endpoint_registry_exact():
    assert osr.THETA_SNAPSHOT_ENDPOINTS == {
        "first": "/v3/option/snapshot/greeks/first_order",
        "second": "/v3/option/snapshot/greeks/second_order",
        "oi": "/v3/option/snapshot/open_interest",
    }
    assert osr.THETA_ENDPOINTS == {
        "greeks": "/v3/option/history/greeks/eod",
        "oi": "/v3/option/history/open_interest",
    }


def test_snapshot_receipt_shape_hash_and_routes():
    raw = CSV_BODY.encode()
    receipt = _receipt(osr.THETA_SNAPSHOT_ENDPOINTS["first"], _wildcards(), raw=raw)
    rec = json.loads(receipt)
    assert set(rec) == {"schema", "origin", "endpoint", "parameters", "received_at",
                        "response_sha256", "availability_basis",
                        "historical_first_availability_established", "calculation_provenance"}
    assert rec["response_sha256"] == hashlib.sha256(raw).hexdigest()
    assert rec["availability_basis"] == "collector_observed_known_by"
    assert rec["historical_first_availability_established"] is False
    assert rec["endpoint"] == osr.THETA_SNAPSHOT_ENDPOINTS["first"]
    for kind in ("first", "second", "oi"):
        assert json.loads(_receipt(osr.THETA_SNAPSHOT_ENDPOINTS[kind], _wildcards(), raw=raw))


def test_receipt_parameters_explicit_vs_omitted_version():
    rec = json.loads(_receipt(osr.THETA_SNAPSHOT_ENDPOINTS["second"],
                              dict(_wildcards(), version="1")))
    assert rec["parameters"]["version"] == "1"
    rec_default = json.loads(_receipt(osr.THETA_SNAPSHOT_ENDPOINTS["second"], _wildcards()))
    assert rec_default["parameters"] == _wildcards()
    assert "version" not in rec_default["parameters"]
    hist = json.loads(_receipt(osr.THETA_ENDPOINTS["greeks"],
                               {"symbol": "SPY", "start_date": "2026-10-16",
                                "end_date": "2026-10-17"}, raw=b"legacy"))
    assert hist["endpoint"] == "/v3/option/history/greeks/eod"


def test_receipt_refuses_unknown_parameter_and_unknown_path():
    with pytest.raises(ValueError):
        _receipt(osr.THETA_SNAPSHOT_ENDPOINTS["first"], dict(_wildcards(), greek_model="bsm"))
    with pytest.raises(ValueError):
        _receipt("/v3/option/snapshot/greeks/third_order", _wildcards())


def test_get_csv_attaches_snapshot_receipt_and_native_accepts():
    session = _csv_session()
    df = thetadata._get_csv(session, osr.THETA_SNAPSHOT_ENDPOINTS["first"], _wildcards())
    assert df is not None and len(df) == 2
    sent = session.calls[0]["params"]
    assert sent == {"symbol": "SPY", "expiration": "*", "strike": "*", "format": "csv"}
    assert ACQ in df.columns and df[ACQ].nunique() == 1
    rec = json.loads(df[ACQ].iloc[0])
    assert rec["endpoint"] == osr.THETA_SNAPSHOT_ENDPOINTS["first"]
    assert rec["response_sha256"] == hashlib.sha256(CSV_BODY.encode()).hexdigest()
    assert "version" not in rec["parameters"]
    out = osr.native_snapshot_acquisitions(df.rename(columns={"symbol": "root"}), "SPY", "first")
    assert isinstance(out, list) and len(out) == 1
    assert out[0]["response_sha256"] == rec["response_sha256"]


def test_get_csv_preserves_legacy_rows_when_provenance_fails():
    session = _csv_session()
    df = thetadata._get_csv(session, osr.THETA_SNAPSHOT_ENDPOINTS["oi"],
                            dict(_wildcards(), greek_model="vendor"))
    assert df is not None and len(df) == 2
    assert ACQ not in df.columns


def test_native_requires_receipt_on_every_row():
    ok = _receipt(osr.THETA_SNAPSHOT_ENDPOINTS["first"], _wildcards())
    partial = _snap_frame(ok)
    partial.loc[1, ACQ] = float("nan")
    assert osr.native_snapshot_acquisitions(partial, "SPY", "first", now=NOW) is None
    bare = _snap_frame(ok).drop(columns=[ACQ])
    assert osr.native_snapshot_acquisitions(bare, "SPY", "first", now=NOW) is None


def test_native_refuses_wrong_endpoint_root_or_future_clock():
    hist = _snap_frame(_receipt(osr.THETA_ENDPOINTS["greeks"],
                                {"symbol": "SPY", "start_date": "2026-10-16",
                                 "end_date": "2026-10-17"}))
    assert osr.native_snapshot_acquisitions(hist, "SPY", "first", now=NOW) is None
    other_root = _snap_frame(_receipt(osr.THETA_SNAPSHOT_ENDPOINTS["first"],
                                      _wildcards(root="QQQ")))
    assert osr.native_snapshot_acquisitions(other_root, "SPY", "first", now=NOW) is None
    future = _snap_frame(_receipt(osr.THETA_SNAPSHOT_ENDPOINTS["first"], _wildcards(),
                                  received_at="2026-10-19T23:00:00+00:00"))
    assert osr.native_snapshot_acquisitions(future, "SPY", "first", now=NOW) is None


def test_native_refuses_selection_inconsistent_with_rows():
    mixed = _snap_frame(_receipt(osr.THETA_SNAPSHOT_ENDPOINTS["second"], _wildcards()),
                        rows=[_rows()[0],
                              {"root": "SPY", "expiration": "2027-01-15",
                               "strike": 605.0, "right": "P", "delta": -0.47}])
    assert osr.native_snapshot_acquisitions(mixed, "SPY", "second", now=NOW) is not None
    pinned = _snap_frame(_receipt(osr.THETA_SNAPSHOT_ENDPOINTS["second"],
                                  dict(_wildcards(), expiration="2026-12-18")))
    assert osr.native_snapshot_acquisitions(pinned, "SPY", "second", now=NOW) is not None
    wrong = _snap_frame(_receipt(osr.THETA_SNAPSHOT_ENDPOINTS["second"],
                                 dict(_wildcards(), expiration="2027-01-15")))
    assert osr.native_snapshot_acquisitions(wrong, "SPY", "second", now=NOW) is None


def test_normalize_preserves_raw_clocks_or_leaves_them_unknown():
    ok = _receipt(osr.THETA_SNAPSHOT_ENDPOINTS["first"], _wildcards())
    raw = _snap_frame(ok)
    out = thetadata._normalize_snapshot_df(raw.copy(), keep_cols=["delta"], label="test")
    assert list(out["timestamp"]) == list(raw["timestamp"])
    assert list(out["underlying_timestamp"]) == list(raw["underlying_timestamp"])
    assert pd.api.types.is_datetime64_any_dtype(out["snapshot_ts"])
    assert (out["snapshot_ts"] == pd.to_datetime(list(raw["timestamp"]))).all()
    assert ACQ in out.columns and out[ACQ].nunique() == 1
    assert (out["root"] == "SPY").all()
    unknown = thetadata._normalize_snapshot_df(
        _snap_frame(ok).drop(columns=["timestamp"]).copy(), keep_cols=["delta"], label="test")
    assert unknown["snapshot_ts"].isna().all()
    assert list(unknown["underlying_timestamp"]) == ["2026-10-19 15:59:59.000000"] * 2


def test_snapshot_greeks_forwards_only_explicit_version_and_refuses_bad(monkeypatch):
    captured = {}

    def fake_get_csv(session, path, params, **kw):
        captured["path"] = path
        captured["params"] = dict(params)
        return pd.DataFrame()

    monkeypatch.setattr(thetadata, "_get_csv", fake_get_csv)
    thetadata.snapshot_greeks("spy", order="first", version="1")
    assert captured["path"] == thetadata.SNAPSHOT_FIRST_ORDER_ENDPOINT
    assert captured["params"] == {"symbol": "SPY", "expiration": "*", "strike": "*", "version": "1"}
    thetadata.snapshot_greeks("SPY")
    assert captured["params"] == {"symbol": "SPY", "expiration": "*", "strike": "*"}
    thetadata.snapshot_greeks("SPY", order="second")
    assert captured["path"] == "/v3/option/snapshot/greeks/second_order"
    with pytest.raises(ValueError):
        thetadata.snapshot_greeks("SPY", order="third")

    def forbidden(session, path, params, **kw):
        raise AssertionError("GET attempted despite invalid version")

    monkeypatch.setattr(thetadata, "_get_csv", forbidden)
    for bad in (0, 2, -1, "2"):
        with pytest.raises(ValueError):
            thetadata.snapshot_greeks("SPY", version=bad)


def _order_frames(match=True):
    ts = "2026-10-19 15:59:58.123456"
    second_ts = ts if match else "2026-10-19 15:59:59.654321"
    first = pd.DataFrame({
        "root": ["SPY", "SPY"],
        "expiration": pd.to_datetime(["2026-12-18"] * 2),
        "strike": [600.0, 605.0],
        "right": ["C", "P"],
        "snapshot_ts": pd.to_datetime([ts, ts]),
        "bid": [5.10, 4.20],
        "delta": [0.52, -0.47],
        "timestamp": [ts, ts],
        "underlying_timestamp": ["2026-10-19 15:59:59.000000"] * 2,
        ACQ: [_receipt(osr.THETA_SNAPSHOT_ENDPOINTS["first"], _wildcards())] * 2,
    })
    second = pd.DataFrame({
        "root": ["SPY", "SPY"],
        "expiration": pd.to_datetime(["2026-12-18"] * 2),
        "strike": [600.0, 605.0],
        "right": ["C", "P"],
        "snapshot_ts": pd.to_datetime([second_ts] * 2),
        "gamma": [0.021, 0.019],
        "vanna": [0.003, 0.004],
        "timestamp": [second_ts] * 2,
        "underlying_timestamp": ["2026-10-19 15:59:59.000000"] * 2,
        ACQ: [_receipt(osr.THETA_SNAPSHOT_ENDPOINTS["second"], _wildcards())] * 2,
    })
    return first, second


def test_join_orders_keeps_first_evidence_and_attaches_secondary():
    first, second = _order_frames(match=True)
    out = csp.join_orders(first, second)
    assert len(out) == 2
    assert list(out["gamma"]) == [0.021, 0.019]
    assert list(out[SECOND_ACQ_COL]) == list(second[ACQ])
    assert list(out[SECOND_TS_COL]) == list(second["timestamp"])
    assert list(out[SECOND_UNDER_COL]) == list(second["underlying_timestamp"])
    assert list(out[ACQ]) == list(first[ACQ])
    assert list(out["timestamp"]) == list(first["timestamp"])
    assert list(out["delta"]) == list(first["delta"])


def test_join_orders_degrades_secondary_to_null_preserving_first():
    first_mismatch, second_mismatch = _order_frames(match=False)
    out = csp.join_orders(first_mismatch, second_mismatch)
    assert out["gamma"].isna().all() and out["vanna"].isna().all()
    for col in (SECOND_TS_COL, SECOND_UNDER_COL, SECOND_ACQ_COL):
        assert col in out.columns and out[col].isna().all()
    first_only, _ = _order_frames()
    missing = csp.join_orders(first_only, None)
    for col in tuple(csp.SECOND_ORDER_JOIN_COLS) + (SECOND_TS_COL, SECOND_UNDER_COL,
                                                    SECOND_ACQ_COL):
        assert col in missing.columns and missing[col].isna().all()
    for joined in (out, missing):
        assert list(joined[ACQ]) == list(first_mismatch[ACQ])
        assert list(joined["timestamp"]) == list(first_mismatch["timestamp"])
        assert list(joined["delta"]) == list(first_mismatch["delta"])


def test_vendor_snapshot_quote_flags_unchanged():
    assert thetadata.SNAPSHOT_FIRST_ORDER_QUOTE_LABEL == "vendor_snapshot_bid_ask"
    for flag in ("SNAPSHOT_FIRST_ORDER_IS_NBBO", "SNAPSHOT_FIRST_ORDER_IS_LIVE",
                 "SNAPSHOT_FIRST_ORDER_IS_CURRENT", "SNAPSHOT_FIRST_ORDER_IS_EXECUTABLE",
                 "SNAPSHOT_FIRST_ORDER_HAS_SIZES", "SNAPSHOT_FIRST_ORDER_HAS_VENUES",
                 "SNAPSHOT_FIRST_ORDER_HAS_CONDITIONS"):
        assert getattr(thetadata, flag) is False


@pytest.mark.parametrize("version,tenor", [(None,None),("1","provider_snapshot_fixed_0dte_0.15"),("latest","provider_snapshot_latest_min_1h")])
def test_actual_requested_snapshot_policy_is_separate_from_model_identity(version,tenor):
    params=_wildcards()
    if version is not None: params["version"]=version
    rec=json.loads(_receipt(osr.THETA_SNAPSHOT_ENDPOINTS["first"],params))
    proof=rec["calculation_provenance"]
    assert proof["requested_version"] == version
    assert proof["tenor_policy"] == tenor
    assert proof["serving_build"] is None
    assert proof["methodology_ref"].endswith("option_snapshot_greeks_first_order.html")
    assert "economic_expiry_no_floor" not in json.dumps(proof)
    assert "model_ref" not in proof and "unit" not in proof


@pytest.mark.parametrize("field,value",[("schema","other"),("availability_basis","provider_first_publication"),("historical_first_availability_established",True),("response_sha256","bad"),("calculation_provenance",None)])
def test_snapshot_malformed_or_promoted_proof_refuses(field,value):
    rec=json.loads(_receipt(osr.THETA_SNAPSHOT_ENDPOINTS["first"],_wildcards()))
    rec[field]=value
    assert osr.native_snapshot_acquisitions(_snap_frame(json.dumps(rec)),"SPY","first",now=NOW) is None


def test_snapshot_unknown_null_root_and_duplicate_receipt_key_refuse():
    raw=_receipt(osr.THETA_SNAPSHOT_ENDPOINTS["first"],_wildcards())
    frame=_snap_frame(raw);frame.loc[1,"root"]=None
    assert osr.native_snapshot_acquisitions(frame,"SPY","first",now=NOW) is None
    duplicate=raw[:-1]+',"endpoint":"'+osr.THETA_SNAPSHOT_ENDPOINTS["first"]+'"}'
    assert osr.native_snapshot_acquisitions(_snap_frame(duplicate),"SPY","first",now=NOW) is None


def test_join_cannot_reuse_preexisting_secondary_evidence():
    first,_=_order_frames()
    for col in csp.SECOND_ORDER_SOURCE_COLS.values():first[col]="forged-prior-secondary"
    out=csp.join_orders(first,None)
    assert all(out[col].isna().all() for col in csp.SECOND_ORDER_SOURCE_COLS.values())


def test_snapshot_metadata_byte_cap_refuses_before_json_decode(monkeypatch):
    frame=_snap_frame(" "*16385)
    def forbidden(*args,**kwargs):raise AssertionError("oversized metadata decoded")
    monkeypatch.setattr(osr.json,"loads",forbidden)
    assert osr.native_snapshot_acquisitions(frame,"SPY","first",now=NOW) is None
