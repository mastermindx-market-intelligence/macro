"""The incumbent builder owns the dormant observation hook; no new schedule/IO."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts import build_rotation_events as builder


@pytest.fixture
def canonical(tmp_path, monkeypatch):
    monkeypatch.setattr(builder.config,"ROOT",tmp_path)
    monkeypatch.setattr(builder.config,"data_dir",lambda:tmp_path/"data")
    monkeypatch.setattr(builder.config,"load",lambda:{"storage":{"site_dir":"site"}})
    monkeypatch.setenv("COLLECT_LANE","nightly")
    monkeypatch.setenv("ROTATION_OBSERVATION_RECORDING_ENABLED","1")
    return tmp_path/"data",tmp_path/"site"


def invoke(paths, **overrides):
    data,site=paths
    args={"data_dir":data,"site":site,"art_dir":None,"explicit_stamp":False}
    args.update(overrides)
    return builder._record_early_observations({"early_context":{}},**args)


def test_default_disabled_does_not_resolve_paths_or_read_anything(monkeypatch,tmp_path):
    monkeypatch.delenv("ROTATION_OBSERVATION_RECORDING_ENABLED",raising=False)
    def fail(): raise AssertionError("disabled path consulted configuration")
    monkeypatch.setattr(builder.config,"data_dir",fail)
    assert invoke((tmp_path/"data",tmp_path/"site"))["status"]=="disabled"
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("value",["true","yes","0",""])
def test_activation_is_exact_and_never_truthy(value,canonical,monkeypatch):
    monkeypatch.setenv("ROTATION_OBSERVATION_RECORDING_ENABLED",value)
    assert invoke(canonical)["status"]=="disabled"


def test_scratch_and_explicit_historical_clock_never_record(canonical,monkeypatch):
    def fail(*a,**kw): raise AssertionError("forbidden history write")
    monkeypatch.setattr(builder.rotation_events,"record_early_observation_history",fail)
    assert invoke(canonical,art_dir=canonical[0])["status"]=="replay_or_scratch"
    assert invoke(canonical,explicit_stamp=True)["status"]=="replay_or_scratch"


def test_nightly_and_canonical_path_constraints(canonical,monkeypatch):
    monkeypatch.setenv("COLLECT_LANE","adhoc")
    assert invoke(canonical)["status"]=="off_lane"
    monkeypatch.setenv("COLLECT_LANE","nightly")
    assert invoke(canonical,data_dir=canonical[0]/"other")["status"]=="noncanonical_path"
    assert invoke(canonical,site=canonical[1]/"preview")["status"]=="noncanonical_path"


def test_observation_clock_is_aware_and_actual_hook_time(canonical,monkeypatch):
    seen=[]
    def record(payload,data_dir,*,observed_at):
        seen.append((payload,data_dir,observed_at))
        return {"status":"recorded","records":[{"id":"example"}]}
    monkeypatch.setattr(builder.rotation_events,"record_early_observation_history",record)
    before=datetime.now(timezone.utc);result=invoke(canonical);after=datetime.now(timezone.utc)
    assert result=={"status":"recorded","receipts":1}
    assert before<=seen[0][2]<=after
    assert seen[0][1]==canonical[0].resolve()


def test_recording_failure_is_not_zero_success(canonical,monkeypatch):
    def fail(*a,**kw): raise OSError("simulated checkpoint failure")
    monkeypatch.setattr(builder.rotation_events,"record_early_observation_history",fail)
    result=invoke(canonical)
    assert result=={"status":"unavailable","receipts":None,"error_class":"OSError"}


def prepare_builder(monkeypatch):
    monkeypatch.setattr(builder.sector_legs,"load_registry",lambda:{})
    monkeypatch.setattr(builder.sector_legs,"sector_closes",lambda registry:{})
    monkeypatch.setattr(builder.sector_fragmentation,"compute",lambda *a,**k:{"n_fragmented":0,"sectors":[]})
    payload={"schema":"rotation_events.v1","as_of":"2026-10-22","active":[],"created_tonight":[],
             "closed_tonight":[],"early_context":{"as_of":"2026-10-22"}}
    monkeypatch.setattr(builder.rotation_events,"run_nightly",lambda *a,**k:dict(payload))
    monkeypatch.setattr(builder.rotation_events,"to_alerts",lambda p:[])
    return payload


def test_actual_builder_calls_observer_only_after_json_publication(canonical,monkeypatch):
    prepare_builder(monkeypatch)
    seen=[]
    def record(payload,data_dir,*,observed_at):
        artifact=canonical[1]/"marketdata"/"rotation_events.json"
        assert artifact.exists()
        assert json.loads(artifact.read_text())["early_context"]==payload["early_context"]
        seen.append(True)
        return {"status":"recorded","records":[]}
    monkeypatch.setattr(builder.rotation_events,"record_early_observation_history",record)
    result=builder.build()
    assert seen==[True]
    assert result["early_observation_recording"]=={"status":"recorded","receipts":0}


def test_actual_builder_explicit_clock_remains_replay_only(canonical,monkeypatch):
    prepare_builder(monkeypatch)
    def fail(*a,**kw): raise AssertionError("historical builder advanced observations")
    monkeypatch.setattr(builder.rotation_events,"record_early_observation_history",fail)
    result=builder.build(generated_utc="2026-10-22 22:00 UTC")
    assert result["early_observation_recording"]["status"]=="replay_or_scratch"
    assert (canonical[1]/"marketdata"/"rotation_events.json").exists()


def test_actual_scratch_builder_keeps_canonical_site_untouched(canonical,monkeypatch,tmp_path):
    prepare_builder(monkeypatch)
    def fail(*a,**kw): raise AssertionError("scratch builder advanced observations")
    monkeypatch.setattr(builder.rotation_events,"record_early_observation_history",fail)
    scratch=tmp_path/"sandbox"
    result=builder.build(art_dir=scratch)
    assert result["early_observation_recording"]["status"]=="replay_or_scratch"
    assert (scratch/"site"/"marketdata"/"rotation_events.json").exists()
    assert not canonical[1].exists()


def test_no_send_or_roster_owner_is_introduced():
    import inspect
    code=inspect.getsource(builder._record_early_observations)
    assert "alert_outbox" not in code
    assert "send_fn" not in code and "_auth_page" not in code
    assert "record_early_observation_history" in code
