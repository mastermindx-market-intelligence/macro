from __future__ import annotations

import hashlib
import json
from copy import deepcopy

import pandas as pd
import pytest

from engine.intl_inputs import (
    countries,
    qualify_return_records,
    source_snapshot,
    _qualification_typed_digest,
)
from engine.intl_performance_records import build_return_records
from engine.intl_workspace_overview import build_overview


POLICY_ID = "intl-observed-endpoints-completed-session-v1"
SOURCE_REFERENCE = "synthetic-first-party-source"
SERIES_IDS = []
for country in countries().values():
    for series_id in (country["index"], country["fx"]):
        if series_id not in SERIES_IDS:
            SERIES_IDS.append(series_id)


def _frame() -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=253, freq="D", tz="Asia/Tokyo")
    return pd.DataFrame(
        {series_id: [100.0 + offset for offset in range(253)]
         for series_id in ("^N225", "USDJPY=X")},
        index=index,
    )


def _snapshot(frame=None) -> dict:
    frame = frame if frame is not None else _frame()
    return source_snapshot(
        frame,
        source_reference=SOURCE_REFERENCE,
        adjustment_bases={series_id: "synthetic-adjusted-close" for series_id in SERIES_IDS},
    )


def _evidence(snapshot, *, latest=None, evaluated="2024-09-09T00:00:00+09:00",
              basis_state="accepted", calendar_ref="synthetic-jp-calendar"):
    latest = latest if latest is not None else "2024-09-09T00:00:00+09:00"
    return [
        {
            "source_reference": SOURCE_REFERENCE,
            "content_sha256": snapshot["content_sha256"],
            "series_id": series_id,
            "adjustment_basis": "synthetic-adjusted-close",
            "basis_state": basis_state,
            "evaluated_at": evaluated,
            "latest_completed_observation": latest,
            "calendar_ref": calendar_ref,
            "owner_ref": "synthetic-owner",
            "decision_ref": "synthetic-owner-decision",
        }
        for series_id in ("^N225", "USDJPY=X")
    ]


def _decisions(records, snapshot, currency_basis="local", *, metadata="allowed",
               value="allowed"):
    leg = "local" if currency_basis == "local" else "usd"
    return [
        {
            "source_reference": SOURCE_REFERENCE,
            "content_sha256": snapshot["content_sha256"],
            "market_id": record["market_id"],
            "index_id": record["index_id"],
            "fx_id": record["fx_id"],
            "horizon": record["horizon"],
            "currency_basis": currency_basis,
            "return_basis": record["return_basis"],
            "leg": leg,
            "owner_ref": "synthetic-disclosure-owner",
            "policy_ref": "synthetic-disclosure-policy",
            "decision_ref": "synthetic-disclosure-decision",
            "metadata": metadata,
            "value": value,
        }
        for record in records["records"]
    ]


def _evaluate(**overrides):
    latest = overrides.pop("latest", None)
    evaluated = overrides.pop("evaluated", None)
    basis_state = overrides.pop("basis_state", None)
    calendar_ref = overrides.pop("calendar_ref", None)
    frame = overrides.pop("frame", None)
    records = build_return_records(
        frame if frame is not None else _frame(),
        market_ids=overrides.pop("market_ids", ["JP"]),
        source_reference=overrides.pop("source_reference", SOURCE_REFERENCE),
    )
    snapshot = overrides.pop("snapshot", None) or _snapshot(frame)
    evidence_options = {}
    if latest is not None:
        evidence_options["latest"] = latest
    if evaluated is not None:
        evidence_options["evaluated"] = evaluated
    if basis_state is not None:
        evidence_options["basis_state"] = basis_state
    if calendar_ref is not None:
        evidence_options["calendar_ref"] = calendar_ref
    evidence = overrides.pop("source_evidence", None) or _evidence(snapshot, **evidence_options)
    basis_for_decisions = overrides.get("currency_basis", "local")
    decisions = overrides.pop("disclosure_decisions", None) or _decisions(
        records, snapshot, basis_for_decisions
    )
    return qualify_return_records(
        records,
        snapshot=snapshot,
        source_evidence=evidence,
        disclosure_decisions=decisions,
        policy_id=overrides.pop("policy_id", POLICY_ID),
        currency_basis=overrides.pop("currency_basis", basis_for_decisions),
        **overrides,
    )


def _by_horus(receipts):
    return {receipt["binding"]["horizon"]: receipt for receipt in receipts}


def test_zero_return_qualifies_with_real_owners_and_overview():
    frame = _frame()
    frame.iloc[-1, 0] = frame.iloc[-22, 0]
    frame.iloc[-1, 1] = frame.iloc[-22, 1]
    result = _evaluate(frame=frame)
    one_month = _by_horus(result["qualifications"])["1m"]
    assert one_month["quality"] == "qualified"
    assert one_month["binding"]["value"] == 0.0
    overview = build_overview(
        build_return_records(frame, market_ids=["JP"], source_reference=SOURCE_REFERENCE),
        roster=[{"market_id": "JP", "name_en": countries()["JP"]["name"],
                 "name_zh": countries()["JP"]["name_zh"]}],
        context={"horizon": "1m", "currency_basis": "local", "return_basis": "price",
                 "source_reference": SOURCE_REFERENCE},
        qualifications=result["qualifications"],
    )
    assert overview["ranking_status"] == "available"
    assert overview["rows"][0]["metric"]["value"] == 0.0


def test_absent_fx_qualifies_local_but_not_usd_or_contribution():
    frame = _frame().drop(columns=["USDJPY=X"])
    local = _evaluate(frame=frame, currency_basis="local")
    usd = _evaluate(frame=frame, currency_basis="usd_unhedged")
    assert _by_horus(local["qualifications"])["1m"]["quality"] == "qualified"
    assert all(receipt["quality"] == "missing" for receipt in usd["qualifications"])


def test_usd_requires_positive_price_fx_and_identical_paired_endpoints():
    frame = _frame()
    frame.iloc[-22, 0] = -1.0
    result = _evaluate(frame=frame, currency_basis="usd_unhedged")
    assert all(receipt["quality"] == "missing" for receipt in result["qualifications"])

    frame = _frame()
    records = build_return_records(frame, market_ids=["JP"], source_reference=SOURCE_REFERENCE)
    snapshot = _snapshot(frame)
    evidence = _evidence(snapshot)
    decisions = _decisions(records, snapshot, "usd_unhedged")
    records["records"][0]["usd"]["window"]["endpoint_observations"]["fx_start"] = "2024-08-18T00:00:00+09:00"
    result = qualify_return_records(
        records, snapshot=snapshot, source_evidence=evidence,
        disclosure_decisions=decisions, policy_id=POLICY_ID,
        currency_basis="usd_unhedged",
    )
    assert _by_horus(result["qualifications"])["1m"]["quality"] == "unsupported"


def test_missing_disclosure_is_identity_only_and_no_shared_context():
    records = build_return_records(_frame(), market_ids=["JP"], source_reference=SOURCE_REFERENCE)
    snapshot = _snapshot()
    result = qualify_return_records(
        records, snapshot=snapshot, source_evidence=_evidence(snapshot),
        disclosure_decisions=[], policy_id=POLICY_ID, currency_basis="local",
    )
    assert result["qualifications"] == []
    assert result["diagnostics"] == [
        {"code": "qualification_unknown", "market_id": "JP", "horizon": horizon,
         "leg": leg, "currency_basis": "local"}
        for horizon in ("1m", "3m", "6m", "12m", "ytd")
        for leg in ("local", "usd", "fx_contribution")
    ]


def test_denied_metadata_is_slot_only_and_value_denied_nulls_value():
    records = build_return_records(_frame(), market_ids=["JP"], source_reference=SOURCE_REFERENCE)
    snapshot = _snapshot()
    metadata_denied = qualify_return_records(
        records, snapshot=snapshot, source_evidence=_evidence(snapshot),
        disclosure_decisions=_decisions(records, snapshot, metadata="denied"),
        policy_id=POLICY_ID, currency_basis="local",
    )
    overview = build_overview(
        records,
        roster=[{"market_id": "JP", "name_en": countries()["JP"]["name"],
                 "name_zh": countries()["JP"]["name_zh"]}],
        context={"horizon": "1m", "currency_basis": "local", "return_basis": "price",
                 "source_reference": SOURCE_REFERENCE},
        qualifications=metadata_denied["qualifications"],
    )
    assert overview["rows"][0] == {"slot": 0, "quality": "denied", "reason": "metadata_denied"}

    value_denied = qualify_return_records(
        records, snapshot=snapshot, source_evidence=_evidence(snapshot),
        disclosure_decisions=_decisions(records, snapshot, value="denied"),
        policy_id=POLICY_ID, currency_basis="local",
    )
    receipt = _by_horus(value_denied["qualifications"])["1m"]
    assert receipt["quality"] == "denied" and receipt["reason"] == "value_denied"


def test_carry_stale_session_unknown_and_basis_failure_are_distinct():
    frame = _frame().copy()
    frame.iloc[-22, 0] = None
    frame.iloc[-22, 1] = None
    carried = _evaluate(frame=frame)
    carried_receipt = _by_horus(carried["qualifications"])["1m"]
    assert carried_receipt["quality"] == "qualified"

    records = build_return_records(_frame(), market_ids=["JP"], source_reference=SOURCE_REFERENCE)
    frame = _frame().iloc[:-1]
    records = build_return_records(frame, market_ids=["JP"], source_reference=SOURCE_REFERENCE)
    snapshot = _snapshot(frame)
    stale = qualify_return_records(
        records, snapshot=snapshot,
        source_evidence=_evidence(snapshot, latest="2024-09-09T00:00:00+09:00"),
        disclosure_decisions=_decisions(records, snapshot), policy_id=POLICY_ID,
        currency_basis="local",
    )
    assert _by_horus(stale["qualifications"])["1m"]["reason"] == "source_session_missed"

    unknown = _evaluate(calendar_ref="")
    assert _by_horus(unknown["qualifications"])["1m"]["reason"] == "session_unknown"

    failed_basis = _evaluate(basis_state="failed")
    receipt = _by_horus(failed_basis["qualifications"])["1m"]
    assert receipt["quality"] == "unknown" and receipt["reason"] == "adjustment_basis_failed"


def test_future_tip_is_invalid_even_with_fresh_fetch_clock():
    records = build_return_records(_frame(), market_ids=["JP"], source_reference=SOURCE_REFERENCE)
    frame = _frame().iloc[:-1]
    records = build_return_records(frame, market_ids=["JP"], source_reference=SOURCE_REFERENCE)
    snapshot = _snapshot(frame)
    result = qualify_return_records(
        records, snapshot=snapshot,
        source_evidence=_evidence(snapshot, latest="2024-09-09T00:00:00+09:00",
                                  evaluated="2024-12-01T00:00:00+09:00"),
        disclosure_decisions=_decisions(records, snapshot), policy_id=POLICY_ID,
        currency_basis="local",
    )
    receipt = _by_horus(result["qualifications"])["1m"]
    assert receipt["quality"] == "stale" and receipt["reason"] == "source_session_missed"


def test_typed_hash_identity_preserves_numeric_type_and_signed_zero():
    first = _qualification_typed_digest({
        "integer": 2 ** 4096, "float": 2.0, "negative_zero": -0.0,
        "nested": [False, None, "χ"],
    })
    second = _qualification_typed_digest({
        "nested": [False, None, "χ"], "negative_zero": -0.0,
        "float": 2.0, "integer": 2 ** 4096,
    })
    changed_int = _qualification_typed_digest({"integer": 2 ** 4096 + 1})
    changed_zero = _qualification_typed_digest({
        "integer": 2 ** 4096, "float": 2.0, "negative_zero": 0.0,
        "nested": [False, None, "χ"],
    })
    assert first == second and first != changed_int and first != changed_zero


def test_one_context_and_independently_recomputable_trace_hashes():
    result = _evaluate(market_ids=list(countries()))
    context = [item for item in result["diagnostics"] if item["code"] == "evaluation_context"]
    traces = [item for item in result["diagnostics"] if item["code"] == "evaluation_trace"]
    assert len(context) == 1 and len(traces) == len(result["qualifications"])
    assert context[0]["context_sha256"] == _qualification_typed_digest(context[0]["material"])
    for receipt, trace in zip(result["qualifications"], traces):
        expected = "derived-evaluation:sha256:" + _qualification_typed_digest(trace["material"])
        assert receipt["decision_ref"] == trace["decision_ref"] == expected
    serialized = json.dumps(result, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    assert serialized.count('"domain":"intl-inputs-evaluation-context-v1"') == 1


def test_inputs_and_outputs_are_detached_and_nonmutating():
    frame = _frame()
    records = build_return_records(frame, market_ids=["JP"], source_reference=SOURCE_REFERENCE)
    snapshot = _snapshot(frame)
    evidence = _evidence(snapshot)
    decisions = _decisions(records, snapshot)
    originals = deepcopy((records, snapshot, evidence, decisions))
    result = _evaluate(
        snapshot=snapshot, source_evidence=evidence, disclosure_decisions=decisions,
    )
    assert (records, snapshot, evidence, decisions) == originals
    context = result["diagnostics"][0]["material"]
    assert context is not records and context["snapshot"] is not snapshot
    assert result["qualifications"][0]["binding"] is not context["records"]["records"][0]


def test_actual_roster_horizons_and_japanese_primary_identity_are_preserved():
    frame = _frame()
    frame["^KS11"] = [100.0 + offset for offset in range(253)]
    frame["USDKRW=X"] = [100.0 + offset for offset in range(253)]
    result = _evaluate(frame=frame, market_ids=["JP", "KR"])
    identities = [(receipt["binding"]["market_id"], receipt["binding"]["horizon"])
                  for receipt in result["qualifications"]]
    assert identities == [(market, horizon) for market in ("JP", "KR")
                          for horizon in ("1m", "3m", "6m", "12m", "ytd")]
    jp = next(receipt for receipt in result["qualifications"]
              if receipt["binding"]["market_id"] == "JP")
    assert jp["binding"]["index_id"] == "^N225" and jp["binding"]["fx_id"] == "USDJPY=X"
    assert list(countries()) == ["JP", "KR", "TW", "IN", "AU", "GB", "EZ"]


def test_positive_legs_with_unequal_windows_do_not_rank():
    frame = _frame()
    frame["^KS11"] = [101.0 + offset for offset in range(253)]
    frame.iloc[-10, frame.columns.get_loc("^KS11")] = None
    # No KR FX: the actual local-only owner uses its observed local grid.
    records = build_return_records(frame, market_ids=["JP", "KR"], source_reference=SOURCE_REFERENCE)
    snapshot = _snapshot(frame)
    evidence = _evidence(snapshot)
    evidence.append({**deepcopy(evidence[0]), "series_id":"^KS11", "calendar_ref":"synthetic-kr-calendar"})
    result = qualify_return_records(
        records, snapshot=snapshot, source_evidence=evidence,
        disclosure_decisions=_decisions(records, snapshot), policy_id=POLICY_ID,
        currency_basis="local",
    )
    receipts=[r for r in result["qualifications"] if r["binding"]["horizon"]=="1m"]
    assert len(receipts)==2 and all(r["quality"]=="qualified" for r in receipts)
    assert receipts[0]["binding"]["window"]["start"] != receipts[1]["binding"]["window"]["start"]
    overview = build_overview(
        records,
        roster=[{"market_id": code, "name_en": countries()[code]["name"],
                 "name_zh": countries()[code]["name_zh"]} for code in ("JP", "KR")],
        context={"horizon": "1m", "currency_basis": "local", "return_basis": "price",
                 "source_reference": SOURCE_REFERENCE},
        qualifications=result["qualifications"],
    )
    assert overview["ranking_status"] == "unavailable"
    assert overview["ranking_reason"] == "unequal_windows"


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda snapshot: snapshot.update(content_sha256="0" * 64), "snapshot"),
        (lambda snapshot: snapshot["series"].append(deepcopy(snapshot["series"][0])), "snapshot"),
        (lambda snapshot: snapshot["series"][0]["observations"].reverse(), "snapshot"),
        (lambda snapshot: snapshot["series"][0]["observations"][0].update(value=True), "snapshot"),
    ],
)
def test_snapshot_corruption_and_duplicates_fail_closed(mutation, message):
    snapshot = _snapshot()
    mutation(snapshot)
    records = build_return_records(_frame(), market_ids=["JP"], source_reference=SOURCE_REFERENCE)
    with pytest.raises(ValueError, match=message):
        qualify_return_records(
            records, snapshot=snapshot, source_evidence=_evidence(_snapshot()),
            disclosure_decisions=_decisions(records, _snapshot()), policy_id=POLICY_ID,
            currency_basis="local",
        )


def test_source_digest_and_record_identity_mismatch_fail_closed():
    records = build_return_records(_frame(), market_ids=["JP"], source_reference="other-source")
    snapshot = _snapshot()
    with pytest.raises(ValueError, match="snapshot"):
        qualify_return_records(
            records, snapshot=snapshot, source_evidence=_evidence(snapshot),
            disclosure_decisions=_decisions(records, snapshot), policy_id=POLICY_ID,
            currency_basis="local",
        )

    records = build_return_records(_frame(), market_ids=["JP"], source_reference=SOURCE_REFERENCE)
    snapshot["source_reference"] = "other-source"
    with pytest.raises(ValueError, match="snapshot"):
        qualify_return_records(
            records, snapshot=snapshot, source_evidence=_evidence(_snapshot()),
            disclosure_decisions=_decisions(records, _snapshot()), policy_id=POLICY_ID,
            currency_basis="local",
        )


def test_duplicate_evidence_and_decisions_are_rejected():
    records = build_return_records(_frame(), market_ids=["JP"], source_reference=SOURCE_REFERENCE)
    snapshot = _snapshot()
    evidence = _evidence(snapshot)
    evidence.append(deepcopy(evidence[0]))
    with pytest.raises(ValueError, match="source_evidence"):
        qualify_return_records(records, snapshot=snapshot, source_evidence=evidence,
                               disclosure_decisions=_decisions(records, snapshot),
                               policy_id=POLICY_ID, currency_basis="local")
    decisions = _decisions(records, snapshot)
    decisions.append(deepcopy(decisions[0]))
    with pytest.raises(ValueError, match="disclosure"):
        qualify_return_records(records, snapshot=snapshot, source_evidence=_evidence(snapshot),
                               disclosure_decisions=decisions, policy_id=POLICY_ID,
                               currency_basis="local")


@pytest.mark.parametrize(
    "timestamp",
    [
        "2024-01-01T00:00:00.000000000+09:00",
        "2024-01-01T00:00:00-08:00",
        "2024-01-01T00:00:00Z",
    ],
)
def test_precise_timestamp_labels_and_offsets_are_retained(timestamp):
    snapshot = _snapshot()
    observation = snapshot["series"][0]["observations"][0]
    observation["timestamp"] = timestamp
    material = [[series["series_id"], series["adjustment_basis"],
                 [[item["timestamp"], None if item["value"] is None else
                   ("i:" + str(item["value"]) if type(item["value"]) is int else
                    "f:" + item["value"].hex())]
                  for item in series["observations"]]]
                for series in snapshot["series"]]
    snapshot["content_sha256"] = hashlib.sha256(
        json.dumps(material, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    result = _evaluate(snapshot=snapshot)
    trace_context = result["diagnostics"][0]["material"]
    assert trace_context["snapshot"]["series"][0]["observations"][0]["timestamp"] == timestamp


@pytest.mark.parametrize(
    "first, second, valid",
    [
        ("2024-01-01T00:00:00+09:00", "2023-12-31T16:00:01Z", True),
        ("2024-01-01T00:00:00+09:00", "2023-12-31T15:00:00Z", False),
        ("2024-01-01T00:00:00.000000001+00:00", "2024-01-01T00:00:00Z", False),
        ("2024-01-01T00:00:00+00:00", "2024-01-01T00:00:00Z", False),
        ("2024-01-01T00:00:00", "2024-01-01T00:00:01", False),
        ("2024-01-01T00:00:00", "2024-01-01T00:00:01Z", False),
    ],
)
def test_nanosecond_offset_and_naive_aware_ordering(first, second, valid):
    snapshot = _snapshot()
    observations = snapshot["series"][0]["observations"][:2]
    observations[0]["timestamp"] = first
    observations[1]["timestamp"] = second
    material = [[series["series_id"], series["adjustment_basis"],
                 [[item["timestamp"], None if item["value"] is None else
                   ("i:" + str(item["value"]) if type(item["value"]) is int else
                    "f:" + item["value"].hex())]
                  for item in series["observations"]]]
                for series in snapshot["series"]]
    snapshot["content_sha256"] = hashlib.sha256(
        json.dumps(material, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    if valid:
        result = _evaluate(snapshot=snapshot)
        assert result["qualifications"]
    else:
        with pytest.raises(ValueError, match="snapshot"):
            _evaluate(snapshot=snapshot)


def test_unknown_policy_explicit_basis_and_malformed_inputs():
    with pytest.raises(ValueError, match="unknown_policy"):
        _evaluate(policy_id="other-policy")
    with pytest.raises(ValueError, match="currency_basis"):
        _evaluate(currency_basis="both")

    records = build_return_records(_frame(), market_ids=["JP"], source_reference=SOURCE_REFERENCE)
    snapshot = _snapshot()
    decisions = _decisions(records, snapshot)
    decisions[0].pop("decision_ref")
    with pytest.raises(ValueError, match="disclosure"):
        qualify_return_records(records, snapshot=snapshot, source_evidence=_evidence(snapshot),
                               disclosure_decisions=decisions, policy_id=POLICY_ID,
                               currency_basis="local")


def test_purity_traps_store_network_and_clock(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("impure call")

    frame = _frame()
    records = build_return_records(frame, market_ids=["JP"], source_reference=SOURCE_REFERENCE)
    snapshot = _snapshot(frame)
    monkeypatch.setattr("lib.store.read", denied)
    import socket
    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr("time.time", denied)
    qualify_return_records(
        records, snapshot=snapshot, source_evidence=_evidence(snapshot),
        disclosure_decisions=_decisions(records, snapshot), policy_id=POLICY_ID,
        currency_basis="local",
    )


def _all_leg_decisions(records,snapshot,basis='local'):
    return [{**d,'leg':leg} for d in _decisions(records,snapshot,basis) for leg in ('local','usd','fx_contribution')]


def _complete_inputs(frame=None,basis='local'):
    frame=_frame() if frame is None else frame
    records=build_return_records(frame,market_ids=['JP'],source_reference=SOURCE_REFERENCE)
    snap=_snapshot(frame)
    return dict(records=records,snapshot=snap,source_evidence=_evidence(snap),
                disclosure_decisions=_all_leg_decisions(records,snap,basis),policy_id=POLICY_ID,currency_basis=basis)


@pytest.mark.parametrize('basis',['local','usd_unhedged'])
def test_all_three_legs_under_single_requested_basis_reach_actual_overview(basis):
    inputs=_complete_inputs(basis=basis);result=qualify_return_records(**inputs)
    assert len(result['qualifications'])==15
    assert len({(r['binding']['market_id'],r['binding']['horizon'],r['binding']['leg']) for r in result['qualifications']})==15
    view=build_overview(inputs['records'],roster=[{'market_id':'JP','name_en':'Japan','name_zh':'日本'}],
                       context={'horizon':'1m','currency_basis':basis,'return_basis':'price','source_reference':SOURCE_REFERENCE},
                       qualifications=result['qualifications'])
    row=view['rows'][0]
    assert all(row[leg]['quality']=='qualified' for leg in ('local','usd','fx_contribution'))
    source=next(r for r in inputs['records']['records'] if r['horizon']=='1m')
    assert all(row[leg]['value']==source[leg]['value'] for leg in ('local','usd','fx_contribution'))
    assert sum(d['code']=='evaluation_context' for d in result['diagnostics'])==1


def test_missing_one_leg_does_not_borrow_its_sibling_decision():
    inputs=_complete_inputs();inputs['disclosure_decisions']=[d for d in inputs['disclosure_decisions'] if not(d['horizon']=='1m' and d['leg']=='fx_contribution')]
    result=qualify_return_records(**inputs)
    assert len(result['qualifications'])==14
    unknown=[d for d in result['diagnostics'] if d['code']=='qualification_unknown']
    assert unknown==[{'code':'qualification_unknown','market_id':'JP','horizon':'1m','leg':'fx_contribution','currency_basis':'local'}]


def test_one_nanosecond_carry_withheld_without_changing_record():
    inputs=_complete_inputs()
    row=next(r for r in inputs['records']['records'] if r['horizon']=='1m')
    row['local']['window']['start']=row['local']['window']['start'].replace('T00:00:00','T00:00:00.000000001')
    before=deepcopy(inputs)
    result=qualify_return_records(**inputs)
    receipt=next(r for r in result['qualifications'] if r['binding']['horizon']=='1m' and r['binding']['leg']=='local')
    assert receipt['quality']=='unsupported' and receipt['reason']=='carry_not_admitted'
    assert inputs==before and receipt['binding']['window']==row['local']['window']


def test_historical_record_end_not_current_merely_because_snapshot_is_current():
    inputs=_complete_inputs()
    older=build_return_records(_frame().iloc[:-1],market_ids=['JP'],source_reference=SOURCE_REFERENCE)
    inputs['records']=older
    result=qualify_return_records(**inputs)
    receipt=next(r for r in result['qualifications'] if r['binding']['horizon']=='1m' and r['binding']['leg']=='local')
    assert receipt['quality']=='unknown' and receipt['reason']=='invalid_source_evidence'


@pytest.mark.parametrize('field,value',[('evaluated_at','2024-09-09T01:00:00'),('latest_completed_observation','2024-09-09T00:00:00'),
    ('evaluated_at','2024-09-09T00:00:00+09:99'),('evaluated_at',None),('latest_completed_observation','nonsense')])
def test_malformed_and_mixed_awareness_source_clocks_withhold(field,value):
    inputs=_complete_inputs()
    for evidence in inputs['source_evidence']:evidence[field]=value
    result=qualify_return_records(**inputs)
    assert all(r['quality']!='qualified' for r in result['qualifications'])
    assert any(r['reason']=='invalid_source_evidence' for r in result['qualifications'])


def test_equivalent_offset_instants_qualify_without_rewriting_labels():
    inputs=_complete_inputs()
    for e in inputs['source_evidence']:
        e['evaluated_at']='2024-09-08T15:00:00Z';e['latest_completed_observation']='2024-09-08T15:00:00Z'
    result=qualify_return_records(**inputs)
    receipt=next(r for r in result['qualifications'] if r['binding']['horizon']=='1m' and r['binding']['leg']=='local')
    assert receipt['quality']=='qualified'
    assert receipt['binding']['window']['end']=='2024-09-09T00:00:00+09:00'


@pytest.mark.parametrize('field,value',[('owner_ref',None),('decision_ref',[]),('calendar_ref',123),('basis_state',[])])
def test_malformed_source_identity_never_qualifies(field,value):
    inputs=_complete_inputs();inputs['source_evidence'][0][field]=value
    with pytest.raises(ValueError,match='source_evidence'):qualify_return_records(**inputs)


@pytest.mark.parametrize('field',['metadata','value'])
def test_unknown_disclosure_remains_unknown(field):
    inputs=_complete_inputs()
    for d in inputs['disclosure_decisions']:d[field]='unknown'
    result=qualify_return_records(**inputs)
    assert all(r['quality'] in ('unknown','missing') for r in result['qualifications'])
    assert all(r['disclosure'][field]=='unknown' for r in result['qualifications'])


def test_large_integer_digest_and_global_limit_are_preserved():
    import sys
    frame=_frame();frame['^KS11']=pd.Series([10**5000]+[None]*252,index=frame.index,dtype=object)
    limit=sys.get_int_max_str_digits();inputs=_complete_inputs(frame)
    result=qualify_return_records(**inputs)
    assert len(result['qualifications'])==15
    assert sys.get_int_max_str_digits()==limit
    assert result['diagnostics'][0]['material']['snapshot']['series'][2]['observations'][0]['value']==10**5000


@pytest.mark.parametrize('mutate',[lambda x:x['records']['records'][0].update(index_id='not-configured'),
    lambda x:x['records']['records'][0].update(requested_observations=True),
    lambda x:x['records']['records'][0]['local'].update(unit='dollars'),
    lambda x:x['records']['records'][0]['local'].update(numerical_status=[]),
    lambda x:x['records']['records'][0]['local'].update(window={}),
    lambda x:x['disclosure_decisions'][0].update(metadata=[]),
    lambda x:x.update(currency_basis=[]),lambda x:x['records']['records'][0].update(fx_quote_orientation='unknown'),
    lambda x:x['records']['records'][0].update(index_label='TOPIX')])
def test_malformed_shapes_refuse_with_valueerror(mutate):
    inputs=_complete_inputs();mutate(inputs)
    with pytest.raises(ValueError):qualify_return_records(**inputs)


def test_cycle_and_custom_container_do_not_execute_or_crash():
    inputs=_complete_inputs();inputs['records']['records'].append(inputs['records'])
    with pytest.raises(ValueError):qualify_return_records(**inputs)
    class Trap(dict):
        def values(self):raise AssertionError('custom code called')
    inputs=_complete_inputs();inputs['records']=Trap(inputs['records'])
    with pytest.raises(ValueError):qualify_return_records(**inputs)


@pytest.mark.parametrize("blank", [" ", "\t", "\r\n", "\u00a0"])
def test_blank_calendar_reference_is_unknown(blank):
    result = _evaluate(calendar_ref=blank)
    receipt = _by_horus(result["qualifications"])["1m"]
    assert receipt["quality"] == "unknown"
    assert receipt["reason"] == "session_unknown"
