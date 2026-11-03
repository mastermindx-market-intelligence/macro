"""Offline source-continuity tests. No DB, network, real data path or sends."""
from __future__ import annotations

import copy
import json
from datetime import date, datetime, timedelta, timezone

import pytest

from engine import rotation_events as owner
from lib.us_cash_calendar import last_session_on_or_before


def clock(day="2026-10-22", hour=22, minute=0):
    return datetime.fromisoformat(day).replace(hour=hour, minute=minute, tzinfo=timezone.utc)


def packet(day="2026-10-22", n=2.0, d=-1.0):
    end = date.fromisoformat(day)
    start = last_session_on_or_before(last_session_on_or_before(end-timedelta(days=1))-timedelta(days=1))
    row = {"schema":"ratio_lens.short_horizon.v1", "pair_id":"xlp_vs_smh", "num":"XLP", "den":"SMH",
           "context_group":"defensive_sector", "requested_as_of":day, "value_as_of":day,
           "eligible_2s":True, "horizons":{"2s":{
               "eligible":True, "sessions":2, "start":start.isoformat(), "end":day,
               "numerator_return_pct":n, "denominator_return_pct":d,
               "ratio_return_pct":((1+n/100)/(1+d/100)-1)*100}}}
    return {"schema":"rotation_early_context/v1", "definition_id":"rotation_early_context/1",
            "display_only":True, "as_of":day, "pairs":[row], "state":"MIXED_ROTATION"}


def advance(previous=None, ctx=None, now=None):
    return owner.advance_early_observation_history(previous, packet() if ctx is None else ctx,
                                                   observed_at=now or clock())


def seed(n=-1.0, d=1.0, day="2026-10-21"):
    return advance(ctx=packet(day,n,d), now=clock(day))["state"]


def record(tmp_path, monkeypatch, ctx=None, now=None):
    monkeypatch.setenv("COLLECT_LANE","nightly")
    root=tmp_path/"rotation_events"; root.mkdir(exist_ok=True)
    state=root/"state.json"
    if not state.exists(): state.write_text(json.dumps({"active":{"legacy":{"id":"legacy"}},"lockout":{}}))
    return owner.record_early_observation_history({"early_context":packet() if ctx is None else ctx},
                                                 tmp_path, observed_at=now or clock())


def test_first_observation_is_recorded_but_never_a_notification():
    out=advance()
    assert len(out["records"])==1
    assert out["records"][0]["kind"] is None
    assert "notification" not in out["records"][0]
    assert out["state"]["pairs"]["XLP/SMH"]["available"] is True


def test_same_measurement_is_idempotent_and_does_not_mutate_input():
    p=seed(); c=packet(); before=copy.deepcopy((p,c))
    out=advance(p,c); rerun=advance(out["state"],c,clock(minute=30))
    assert rerun["records"]==[]
    assert (p,c)==before


def test_positive_divergence_is_observed_not_sized_or_predicted():
    out=advance(seed())
    notice=out["records"][0]["notification"]
    assert notice["kind"]=="observed_change"
    assert notice["authority"]=="notification_only"
    assert notice["category"]=="sector_rotation_relative"
    assert notice["values"]["numerator_return_pct"]==2.0
    assert notice["source_as_of"]==notice["event_as_of"]=="2026-10-22"
    assert notice["previous_observation_id"].startswith("rotobs_")
    assert "confidence" not in notice and "allocation" not in notice
    assert datetime.fromisoformat(notice["not_after"])-datetime.fromisoformat(notice["observed_at"])==timedelta(hours=24)


def test_unchanged_direction_new_session_records_without_daily_spam():
    out=advance(seed(1,-2),packet(n=2,d=-1))
    assert len(out["records"])==1 and out["records"][0]["kind"] is None


def test_relative_reversal_and_absolute_failure_are_distinct_measured_cases():
    for n,d in [(-2,1),(-1,-3)]:
        out=advance(seed(2,-1),packet(n=n,d=d))
        r=out["records"][0]
        assert r["kind"]=="reversal"
        assert r["values"]["numerator_return_pct"]<0
    assert advance(seed(2,-1),packet(n=-1,d=-3))["records"][0]["values"]["ratio_return_pct"]>0


def test_baseline_revision_does_not_invent_a_previous_alert():
    first=advance()
    later=advance(first["state"],packet(n=3),clock(minute=10))
    assert later["records"][0]["kind"] is None
    assert later["records"][0]["previous_observation_id"]==first["records"][0]["observation_id"]


def test_revision_of_notifiable_observation_is_linked_correction():
    first=advance(seed())
    later=advance(first["state"],packet(n=3),clock(minute=10))
    assert later["records"][0]["kind"]=="correction"
    assert later["records"][0]["notification"]["previous_observation_id"]==first["records"][0]["observation_id"]


def test_data_withdrawal_uses_null_values_not_old_positive_returns():
    out=advance(seed(2,-1),{})
    notice=out["records"][0]["notification"]
    assert notice["kind"]=="data_withdrawal" and notice["values"] is None
    assert notice["source_as_of"]=="2026-10-21" and notice["event_as_of"]=="2026-10-22"
    assert advance(out["state"],{},clock(minute=30))["records"]==[]
    later=advance(out["state"],{},clock("2026-10-23"))
    assert all(r["kind"] is None for r in later["records"])


def test_restoration_seeds_continuity_instead_of_claiming_a_market_turn():
    withdrawn=advance(seed(2,-1),{})
    restored=advance(withdrawn["state"],packet(),clock(minute=10))
    assert restored["records"][0]["available"] is True
    assert restored["records"][0]["kind"] is None


def test_unobserved_multi_session_gap_is_not_a_new_pivot_alert():
    out=advance(seed(day="2026-10-19"))
    assert out["records"][0]["kind"] is None


def test_weekend_is_contiguous_using_existing_calendar():
    out=advance(seed(day="2026-10-23"),packet("2026-10-26"),clock("2026-10-26"))
    assert out["records"][0]["kind"]=="observed_change"


def test_half_day_settlement_and_holiday_follow_existing_calendar():
    prior=seed(day="2026-11-25")
    before=advance(prior,packet("2026-11-27"),clock("2026-11-27",18,30))
    after=advance(prior,packet("2026-11-27"),clock("2026-11-27",19,0))
    assert before["status"]=="future_source"
    assert after["records"][0]["kind"]=="observed_change"


def test_future_source_and_older_observation_clock_never_roll_history_back():
    prior=seed()
    future=advance(prior,packet("2026-10-23"))
    assert future["status"]=="future_source" and future["state"]==prior
    older=advance(prior,packet("2026-10-20"),clock("2026-10-20"))
    assert older["status"]=="out_of_order" and older["records"]==[]


@pytest.mark.parametrize("bad",[None,True,False,"2",float("nan"),float("inf"),10**1000])
@pytest.mark.parametrize("field",["numerator_return_pct","denominator_return_pct","ratio_return_pct"])
def test_malformed_numeric_evidence_withdraws_without_coercion(bad,field):
    ctx=packet();ctx["pairs"][0]["horizons"]["2s"][field]=bad
    out=advance(seed(2,-1),ctx)
    assert out["records"][0]["kind"]=="data_withdrawal"
    assert out["records"][0]["values"] is None


@pytest.mark.parametrize("mutation",[
    {"eligible_2s":None},{"eligible_2s":"true"},{"schema":"unknown"},
    {"requested_as_of":"2026-10-21"},{"value_as_of":"2026-10-21"},
    {"num":"<script>"},{"num":"SMH"},{"pair_id":""},
])
def test_bad_row_cannot_become_a_measured_change(mutation):
    ctx=packet();ctx["pairs"][0].update(mutation)
    assert advance(seed(2,-1),ctx)["records"][0]["kind"]=="data_withdrawal"


@pytest.mark.parametrize("mutation",[
    {"eligible":False},{"sessions":True},{"sessions":"2"},{"sessions":1},
    {"start":"2026-02-30"},{"start":"2026-10-19"},{"end":"2026-10-21"},
    {"numerator_return_pct":-100},{"denominator_return_pct":-100},{"ratio_return_pct":100},
])
def test_window_identity_and_relative_wealth_are_validated(mutation):
    ctx=packet();ctx["pairs"][0]["horizons"]["2s"].update(mutation)
    assert advance(seed(2,-1),ctx)["records"][0]["kind"]=="data_withdrawal"


def test_duplicate_aliases_abstain_without_double_counting():
    ctx=packet();ctx["pairs"].append(copy.deepcopy(ctx["pairs"][0]))
    out=advance(seed(2,-1),ctx)
    assert len(out["records"])==1 and out["records"][0]["kind"]=="data_withdrawal"


def test_non_defensive_rows_never_create_sector_notifications():
    ctx=packet();ctx["pairs"][0]["context_group"]="retailer_context"
    assert advance(ctx=ctx)["records"]==[]


def test_strict_history_clock_and_schema():
    with pytest.raises(ValueError): advance(previous={"schema":"another"})
    with pytest.raises(ValueError): advance(previous={"schema":"rotation_early_observation_history/v1","pairs":{},"last_observed_at":"not-time"})
    with pytest.raises(ValueError): owner.advance_early_observation_history({},packet(),observed_at=datetime(2026,10,22))


def test_off_lane_performs_no_filesystem_creation(tmp_path,monkeypatch):
    monkeypatch.delenv("COLLECT_LANE",raising=False)
    out=owner.record_early_observation_history({"early_context":packet()},tmp_path,observed_at=clock())
    assert out["status"]=="off_lane" and not list(tmp_path.iterdir())


def test_receipts_use_existing_ledger_state_and_keep_legacy_data(tmp_path,monkeypatch):
    first=record(tmp_path,monkeypatch)
    second=record(tmp_path,monkeypatch,now=clock(minute=10))
    root=tmp_path/"rotation_events"
    rows=[json.loads(s) for s in (root/"events.jsonl").read_text().splitlines()]
    assert len(rows)==1 and rows[0]["kind"] is None
    assert second["records"]==[]
    state=json.loads((root/"state.json").read_text())
    assert state["active"]["legacy"]["id"]=="legacy"
    assert state["early_observations"]["pairs"]["XLP/SMH"]["observation_id"]==first["records"][0]["observation_id"]
    assert sorted(p.name for p in root.iterdir())==["events.jsonl","state.json"]


def test_append_then_checkpoint_crash_reuses_original_receipt_clock(tmp_path,monkeypatch):
    root=tmp_path/"rotation_events"; root.mkdir()
    (root/"state.json").write_text('{"active":{},"lockout":{}}')
    original=owner.os.replace
    def failed(*args): raise OSError("simulated checkpoint failure")
    monkeypatch.setattr(owner.os,"replace",failed)
    with pytest.raises(OSError): record(tmp_path,monkeypatch)
    assert "early_observations" not in json.loads((root/"state.json").read_text())
    monkeypatch.setattr(owner.os,"replace",original)
    replay=record(tmp_path,monkeypatch,now=clock(minute=15))
    assert replay["records"][0]["observed_at"]==clock().isoformat()
    assert len((root/"events.jsonl").read_text().splitlines())==1
    assert not list(root.glob('.state-*'))


def test_conflicting_or_truncated_canonical_receipt_never_gets_overwritten(tmp_path,monkeypatch):
    root=tmp_path/"rotation_events"; root.mkdir()
    initial='{"active":{},"lockout":{}}';(root/"state.json").write_text(initial)
    record(tmp_path,monkeypatch)
    ledger=root/"events.jsonl";row=json.loads(ledger.read_text())
    row["values"]["numerator_return_pct"]=999
    ledger.write_text(json.dumps(row)+'\n');(root/"state.json").write_text(initial)
    with pytest.raises(ValueError,match="identity conflict"): record(tmp_path,monkeypatch)
    assert (root/"state.json").read_text()==initial
    ledger.write_text('{"event":')
    with pytest.raises(ValueError): record(tmp_path,monkeypatch)
    assert ledger.read_text()=='{"event":'


def test_checkpoint_without_backing_receipt_fails_closed(tmp_path,monkeypatch):
    record(tmp_path,monkeypatch)
    root=tmp_path/"rotation_events";(root/"events.jsonl").write_text('')
    with pytest.raises(ValueError,match="backed by canonical history"):
        record(tmp_path,monkeypatch,packet("2026-10-23"),clock("2026-10-23"))


def test_recovery_with_changed_input_keeps_original_ledger_parent(tmp_path,monkeypatch):
    record(tmp_path,monkeypatch,packet("2026-10-21",-1,1),clock("2026-10-21"))
    root=tmp_path/"rotation_events"; original=owner.os.replace
    def fail(*args): raise OSError("after append, before checkpoint")
    monkeypatch.setattr(owner.os,"replace",fail)
    with pytest.raises(OSError): record(tmp_path,monkeypatch)
    first_change=json.loads((root/"events.jsonl").read_text().splitlines()[-1])
    monkeypatch.setattr(owner.os,"replace",original)
    recovered=record(tmp_path,monkeypatch,packet(n=3),clock(minute=15))
    rows=[json.loads(x) for x in (root/"events.jsonl").read_text().splitlines()]
    assert len(rows)==3
    assert rows[-1]["kind"]=="correction"
    assert rows[-1]["previous_observation_id"]==first_change["observation_id"]
    assert recovered["records"][0]["observed_at"]==clock().isoformat()
    assert rows[-1]["notification"]["previous_observation_id"]==first_change["observation_id"]


def test_receipt_time_and_notification_tampering_fail_closed(tmp_path,monkeypatch):
    record(tmp_path,monkeypatch,packet("2026-10-21",-1,1),clock("2026-10-21"))
    record(tmp_path,monkeypatch)
    ledger=tmp_path/"rotation_events"/"events.jsonl"
    raw=ledger.read_text(); rows=[json.loads(x) for x in raw.splitlines()]
    for field,value in [("observed_at","2026-10-22T22:00:00"),("observed_at","not-a-time"),("not_after","2099-01-01T00:00:00+00:00")]:
        damaged=copy.deepcopy(rows)
        if field=="not_after": damaged[-1]["notification"][field]=value
        else: damaged[-1][field]=value
        ledger.write_text(''.join(json.dumps(x)+'\n' for x in damaged))
        with pytest.raises(ValueError): record(tmp_path,monkeypatch,now=clock(minute=10))
    ledger.write_text(raw)


def test_duplicate_pair_id_across_distinct_instruments_is_not_two_observations():
    ctx=packet();other=copy.deepcopy(ctx["pairs"][0]);other["num"]="XLU";ctx["pairs"].append(other)
    out=advance(ctx=ctx)
    assert out["records"]==[]


@pytest.mark.parametrize("history",[[],"unknown",True,7])
def test_non_mapping_history_never_becomes_a_clean_baseline(history):
    with pytest.raises(ValueError,match="history type"):
        advance(previous=history)


def test_existing_nightly_writer_preserves_observation_checkpoint(tmp_path,monkeypatch):
    record(tmp_path,monkeypatch)
    root=tmp_path/"rotation_events";p=root/"state.json"
    state=json.loads(p.read_text());state["active"]={};p.write_text(json.dumps(state))
    before=copy.deepcopy(state["early_observations"])
    monkeypatch.delenv("COLLECT_LANE",raising=False)
    owner.run_nightly({},tmp_path,generated_utc="2026-10-22 22:00 UTC")
    assert json.loads(p.read_text())["early_observations"]==before


def legacy_closed():
    return {"ts":"2026-10-22 22:00 UTC","event":"closed","pair_id":"xlk:memory->mag7",
            "sector":"xlk","from_leg":"memory","to_leg":"mag7","started":"2026-10-01",
            "closed_asof":"2026-10-22","reason":"conditions_lapsed","day_n":15}


def test_shared_ledger_reader_does_not_promote_observations_to_confirmed_events(tmp_path):
    receipt=advance()["records"][0];closed=legacy_closed()
    ledger=tmp_path/"events.jsonl";ledger.write_text(json.dumps(receipt)+'\n'+json.dumps(closed)+'\n')
    result=owner.read_ledger_history(ledger)
    assert result["status"]=="OK"
    assert [x["row"] for x in result["rows"]]==[closed]
    assert result["coverage"]["excluded_observation_receipts"]==1
    assert result["coverage"]["event_counts"]=={"created":0,"closed":1}
    assert result["coverage"]["selected_rows"]==1
    assert owner.closed_recent(ledger)==[closed]


def test_shared_history_reader_rejects_broken_observation_receipts(tmp_path):
    receipt=advance()["records"][0];receipt["values"]["numerator_return_pct"]=999
    ledger=tmp_path/"events.jsonl";ledger.write_text(json.dumps(receipt)+'\n')
    result=owner.read_ledger_history(ledger)
    assert result["status"]=="INVALID"
    assert result["error"]["code"]=="INVALID_OBSERVATION_RECEIPT"
    assert result["rows"]==[]


def test_only_observations_means_no_confirmed_rows_not_missing_history(tmp_path):
    receipt=advance()["records"][0]
    ledger=tmp_path/"events.jsonl";ledger.write_text(json.dumps(receipt)+'\n')
    result=owner.read_ledger_history(ledger)
    assert result["status"]=="OK"
    assert result["coverage"]["excluded_observation_receipts"]==1
    assert result["coverage"]["selected_rows"]==0


def test_checkpoint_none_is_corruption_not_an_empty_baseline(tmp_path,monkeypatch):
    root=tmp_path/"rotation_events";root.mkdir()
    (root/"state.json").write_text('{"active":{},"early_observations":null}')
    with pytest.raises(ValueError,match="checkpoint type"):
        record(tmp_path,monkeypatch)
    assert not (root/"events.jsonl").exists()
