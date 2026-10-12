from __future__ import annotations

import json
from hashlib import sha256

import pytest

from engine.prophet_lab.intelligence_vector import (
    _MAX_REVENUE,
    _REVENUE_UNIT_SCALE,
    _REVENUE_UNITS,
    build_earnings_intelligence_vector,
    validate_intelligence_vector,
)
from engine.us_candidate_episode import episode_id as b1_episode_id
from lib.dataos.identity import IssuerMaster


_ANCHOR = {
    "kind": "turn_watch_reset_low",
    "time": "2026-07-30T20:00:00Z",
    "price": "100.0000",
    "basis": "turn_watch.reset_low",
    "source_receipt": "sha256:" + "b" * 64,
}
_EVENT_ID = "evt_cik0000320193_2026q3_results"
_GENERATION_ID = "peg:" + "a" * 64


def _unit_workspace(*, value: int, unit: str) -> dict:
    return {
        "schema": "event_workspace.v1",
        "event_id": _EVENT_ID,
        "generation_id": "1" * 24,
        "issuer": {
            "company_id": "cik:0000320193",
            "display_name": "Apple Inc.",
        },
        "fiscal_period": {
            "year": 2026,
            "quarter": 3,
            "calendar_end": "2026-06-27",
        },
        "lifecycle": {
            "state": "complete",
            "source_available_at": "2026-07-30T20:00:00Z",
            "observed_at": "2026-07-30T20:03:00Z",
        },
        "generated_at": "2026-07-30T20:04:00Z",
        "facts": [{
            "schema": "event_fact.v1",
            "metric": "revenue",
            "value": value,
            "unit": unit,
            "period": "2026Q3",
            "basis": "reported",
            "source_span": {"document_id": "doc:issuer-release:1"},
        }],
        "deltas": [{
            "schema": "metric_delta.v1",
            "metric": "revenue",
            "current": {
                "value": value,
                "unit": unit,
                "basis": "reported",
            },
            "prior": {"state": "absent", "reason": "not_available"},
            "consensus": {"state": "absent", "reason": "consensus_unlicensed"},
            "basis_match": False,
        }],
        "guidance": [],
        "claims": [],
        "sources": [{
            "kind": "issuer_release",
            "document_id": "doc:issuer-release:1",
            "source_sha256": "c" * 64,
            "receipt_state": "byte_replayed",
        }],
        "warnings": [],
    }


def _revisions(*, value: int, unit: str) -> list[dict]:
    workspace = _unit_workspace(value=value, unit=unit)
    canonical_workspace = json.dumps(
        workspace, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode()
    return [{
        "generation_id": workspace["generation_id"],
        "source_sha256": workspace["sources"][0]["source_sha256"],
        "source_available_at": workspace["lifecycle"]["source_available_at"],
        "observed_at": workspace["lifecycle"]["observed_at"],
        "lifecycle_state": "complete",
        "form": "8-K",
        "workspace_receipt": {
            "sha256": sha256(canonical_workspace).hexdigest(),
            "bytes": len(canonical_workspace),
        },
        "workspace": workspace,
    }]


def _build_unit_projection(*, value: int, unit: str) -> dict:
    episode = {
        "schema": "prophet.candidate_episode/v1",
        "episode_id": b1_episode_id(
            "SEC:US-XNAS-AAPL", "epoch_0", _ANCHOR, 1,
        ),
        "company_id": "ISS:US:320193",
        "security_id": "SEC:US-XNAS-AAPL",
        "identity_epoch": "epoch_0",
        "state": "CANDIDATE",
        "opened_at": "2026-07-30T20:05:00Z",
        "opened_session": "2026-07-30",
        "structural_anchor": _ANCHOR,
        "expert_events": ["radar:event:content-addressed-1"],
    }
    issuer_master = IssuerMaster.from_records([{
        "security_id": "SEC:US-XNAS-AAPL",
        "issuer_id": "ISS:US:320193",
        "issuer_state": "active",
        "listing_key": "US:XNAS:AAPL",
        "issuer_cik": "0000320193",
    }])
    return build_earnings_intelligence_vector(
        episode=episode,
        episode_generation_id=_GENERATION_ID,
        episode_known_at="2026-07-30T20:05:00Z",
        issuer_master=issuer_master,
        find_event_id=lambda company_id: _EVENT_ID,
        read_revisions=lambda event_id: _revisions(value=value, unit=unit),
    )


def _revenue_observation(payload: dict) -> dict | None:
    return next((
        observation for observation
        in payload["evidence_families"][0]["observations"]
        if observation["native_metric_id"] == "fact:revenue"
    ), None)


def test_revenue_units_normalize_to_identical_usd_values() -> None:
    raw_usd = _build_unit_projection(
        value=109_417_000_000, unit="USD",
    )
    usd_millions = _build_unit_projection(
        value=109_417, unit="usd_millions",
    )
    raw_observation = _revenue_observation(raw_usd)
    producer_observation = _revenue_observation(usd_millions)

    assert raw_observation is not None
    assert producer_observation is not None
    assert raw_observation["value_usd"] == 109_417_000_000
    assert producer_observation["value_usd"] == raw_observation["value_usd"]
    validate_intelligence_vector(raw_usd)
    validate_intelligence_vector(usd_millions)


def test_revenue_observation_preserves_native_value_and_unit() -> None:
    observation = _revenue_observation(_build_unit_projection(
        value=109_417_000_000, unit="USD",
    ))

    assert observation is not None
    assert observation["value"] == 109_417_000_000
    assert observation["units"] == "USD"
    assert set(observation) == {
        "observation_id", "native_metric_id", "value_state", "value", "units",
        "value_usd", "method_class", "method_version", "source_ref_ids",
        "evidence_root_ids", "economic_dependence_group_ids", "quality_flags",
        "absence_reasons", "neutral_definition_ref", "correction_lineage_state",
    }


@pytest.mark.parametrize(
    ("value", "unit"),
    [
        (_MAX_REVENUE + 1, "USD"),
        (_MAX_REVENUE // _REVENUE_UNIT_SCALE["usd_millions"] + 1, "usd_millions"),
    ],
)
def test_revenue_bound_is_applied_to_usd_equivalent(
    value: int, unit: str,
) -> None:
    payload = _build_unit_projection(value=value, unit=unit)

    assert _revenue_observation(payload) is None
    assert payload["evidence_families"][0]["coverage"]["state"] in {
        "COVERED", "PARTIAL", "UNKNOWN", "NOT_COVERED",
    }
    validate_intelligence_vector(payload)


def test_revenue_unit_table_and_admission_set_match() -> None:
    assert set(_REVENUE_UNIT_SCALE) == set(_REVENUE_UNITS)
    assert set(_REVENUE_UNIT_SCALE) == {"USD", "usd_millions"}


@pytest.mark.parametrize("unit", ["eur", "unknown", None])
def test_unknown_revenue_unit_remains_typed_absence(unit: str | None) -> None:
    payload = _build_unit_projection(value=109_417, unit=unit)

    assert _revenue_observation(payload) is None
    assert payload["evidence_families"][0]["coverage"]["state"] == "UNKNOWN"
    validate_intelligence_vector(payload)


def test_current_fact_consistency_still_requires_value_and_unit_match() -> None:
    payload = _build_unit_projection(
        value=109_417_000_000, unit="USD",
    )
    delta = payload["evidence_families"][0]["trajectory"]["dimensions"][0]["value"]

    assert delta["current"] == {
        "value": 109_417_000_000,
        "unit": "USD",
        "basis": "reported",
    }


# Existing D5-to-factual-dossier consumer; no alternate event/clock/source reader.
def _q06_vector(*, value=109417, source_hash=None, opened_at="2026-07-30T20:33:00Z",
                source_clock="2026-07-30T20:30:28Z", return_inputs=False):
    from pathlib import Path
    raw = (Path(__file__).resolve().parents[1] /
           "tests/fixtures/company_intelligence/aapl_fy2026_q3_ex99_1.htm").read_bytes()
    assert sha256(raw).hexdigest() == "070abd6a9cdb7070e546d24ffcbc41c65450d939c6f88f189cb18ec711cf5fdb"
    revision = _revisions(value=value, unit="usd_millions")[0]
    workspace = revision["workspace"]
    workspace["sources"][0]["source_sha256"] = source_hash or sha256(raw).hexdigest()
    workspace["facts"][0]["basis"] = "gaap"
    workspace["deltas"][0]["current"]["basis"] = "gaap"
    workspace["lifecycle"]["source_available_at"] = source_clock
    workspace["lifecycle"]["observed_at"] = "2026-07-30T20:31:00Z"
    workspace["generated_at"] = "2026-07-30T20:32:00Z"
    revision["source_sha256"] = workspace["sources"][0]["source_sha256"]
    revision["source_available_at"] = source_clock
    revision["observed_at"] = workspace["lifecycle"]["observed_at"]
    encoded = json.dumps(workspace, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    revision["workspace_receipt"] = {"sha256":sha256(encoded).hexdigest(), "bytes":len(encoded)}
    episode = {
        "schema":"prophet.candidate_episode/v1",
        "episode_id":b1_episode_id("SEC:US-XNAS-AAPL", "epoch_0", _ANCHOR, 1),
        "company_id":"ISS:US:320193", "security_id":"SEC:US-XNAS-AAPL",
        "identity_epoch":"epoch_0", "state":"CANDIDATE", "opened_at":opened_at,
        "opened_session":"2026-07-30", "structural_anchor":_ANCHOR,
        "expert_events":["radar:event:content-addressed-1"],
    }
    master=IssuerMaster.from_records([{"security_id":"SEC:US-XNAS-AAPL",
        "issuer_id":"ISS:US:320193","issuer_state":"active","listing_key":"US:XNAS:AAPL",
        "issuer_cik":"0000320193"}])
    if return_inputs:
        return episode,master,[revision]
    return build_earnings_intelligence_vector(episode=episode,episode_generation_id=_GENERATION_ID,
        episode_known_at=opened_at,issuer_master=master,find_event_id=lambda _: _EVENT_ID,
        read_revisions=lambda _:[revision])


def _install_q06(root):
    from pathlib import Path
    from engine.prophet_lab.earnings_dossier import Q06_CONTRACT_PATH, Q06_RIGHTS_PATH
    repo=Path(__file__).resolve().parents[1]
    for target,source in [(Q06_CONTRACT_PATH,"tests/fixtures/prophet/q06_source_contract.v0_2.json"),
                          (Q06_RIGHTS_PATH,Q06_RIGHTS_PATH)]:
        path=root/target;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes((repo/source).read_bytes())


def test_earnings_detail_binds_real_source_contract_and_native_d5(tmp_path):
    from copy import deepcopy
    from engine.prophet_lab.earnings_dossier import load_q06_source_field, project_earnings_detail
    _install_q06(tmp_path);field,state=load_q06_source_field(tmp_path)
    v=_q06_vector();before=deepcopy(v);out=project_earnings_detail(v,source_field=field,source_state=state)
    assert out["comparison_state"]=="COMPARABLE_REPORTED_CHANGE_BOUND"
    change=out["dossier"]["reported_changes"][0]
    assert change["current_value"]==109417 and change["prior_value"]==94036
    assert change["change_pct"]==pytest.approx(16.356501765281383)
    assert change["prior_available_at"]=="2026-07-30T20:30:28Z"
    assert change["prior_event_id"]==change["current_event_id"]
    assert change["comparison_origin"]=="SAME_CURRENT_RELEASE_COMPARATIVE_TABLE"
    assert "16.4%" in out["headline"]
    assert out["dossier"]["expectation_surprises"]==[]
    assert all(x is False for x in out["authority"].values())
    assert v==before and out["source_projection_id"]==v["projection_id"]


def test_earnings_detail_missing_contract_preserves_current_observation(tmp_path):
    from engine.prophet_lab.earnings_dossier import load_q06_source_field, project_earnings_detail
    field,state=load_q06_source_field(tmp_path)
    out=project_earnings_detail(_q06_vector(),source_field=field,source_state=state)
    assert out["comparison_state"]=="SOURCE_CONTRACT_NOT_INSTALLED"
    assert out["dossier"]["reported_changes"]==[]
    assert out["current_observations"][0]["value_usd"]==109417000000


@pytest.mark.parametrize("source_hash,value,state", [
    ("d"*64,109417,"SOURCE_FIELD_REVISION_MISMATCH"),
    (None,109418,"SOURCE_FIELD_VALUE_MISMATCH"),
])
def test_earnings_detail_does_not_join_current_number_to_wrong_revision(tmp_path,source_hash,value,state):
    from engine.prophet_lab.earnings_dossier import load_q06_source_field,project_earnings_detail
    _install_q06(tmp_path);field,status=load_q06_source_field(tmp_path)
    out=project_earnings_detail(_q06_vector(source_hash=source_hash,value=value),source_field=field,source_state=status)
    assert out["comparison_state"]==state
    assert out["dossier"]["reported_changes"]==[]


def test_earnings_detail_clock_mismatch_does_not_backdate_field(tmp_path):
    from engine.prophet_lab.earnings_dossier import load_q06_source_field,project_earnings_detail
    _install_q06(tmp_path);field,status=load_q06_source_field(tmp_path)
    out=project_earnings_detail(_q06_vector(source_clock="2026-07-30T20:30:27Z"),source_field=field,source_state=status)
    assert out["comparison_state"]=="SOURCE_FIELD_CLOCK_MISMATCH"
    assert out["dossier"]["reported_changes"]==[]


def test_earnings_detail_early_episode_keeps_d5_absence(tmp_path):
    from engine.prophet_lab.earnings_dossier import load_q06_source_field,project_earnings_detail
    _install_q06(tmp_path);field,status=load_q06_source_field(tmp_path)
    out=project_earnings_detail(_q06_vector(opened_at="2026-07-30T20:05:00Z"),source_field=field,source_state=status)
    assert out["comparison_state"]!="COMPARABLE_REPORTED_CHANGE_BOUND"
    assert not (out["dossier"] or {}).get("reported_changes")


@pytest.mark.parametrize("which,state",[("contract","SOURCE_CONTRACT_CHANGED"),("rights","SOURCE_RIGHTS_CHANGED")])
def test_earnings_detail_rechecks_installed_contract_and_rights(tmp_path,which,state):
    from engine.prophet_lab.earnings_dossier import load_q06_source_field,Q06_CONTRACT_PATH,Q06_RIGHTS_PATH
    _install_q06(tmp_path);path=tmp_path/(Q06_CONTRACT_PATH if which=="contract" else Q06_RIGHTS_PATH)
    path.write_bytes(path.read_bytes()+b"\n")
    field,status=load_q06_source_field(tmp_path)
    assert field is None and status==state


def test_earnings_detail_mutated_internal_contract_cannot_mint_growth(tmp_path):
    from engine.prophet_lab.earnings_dossier import load_q06_source_field,project_earnings_detail
    _install_q06(tmp_path);field,status=load_q06_source_field(tmp_path)
    field["economic_identity"]["prior"]["value"]=1
    out=project_earnings_detail(_q06_vector(),source_field=field,source_state=status)
    assert out["comparison_state"]=="SOURCE_CONTRACT_CHANGED"
    assert out["dossier"]["reported_changes"]==[]


def test_earnings_detail_does_not_mutate_native_source_or_prior_output(tmp_path):
    from engine.prophet_lab.earnings_dossier import load_q06_source_field,project_earnings_detail
    _install_q06(tmp_path);field,status=load_q06_source_field(tmp_path);v=_q06_vector()
    files={str(p):p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    first=project_earnings_detail(v,source_field=field,source_state=status)
    first["current_observations"][0]["value"]=0
    second=project_earnings_detail(v,source_field=field,source_state=status)
    assert second["current_observations"][0]["value"]==109417
    assert files=={str(p):p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


def test_earnings_detail_never_exposes_source_paths_or_raw_contract(tmp_path):
    from engine.prophet_lab.earnings_dossier import load_q06_source_field,project_earnings_detail
    _install_q06(tmp_path);field,status=load_q06_source_field(tmp_path)
    raw=json.dumps(project_earnings_detail(_q06_vector(),source_field=field,source_state=status))
    for forbidden in ["https://",str(tmp_path),"current_span","historical_envelope_identities","research/licenses/"]:
        assert forbidden not in raw



def test_q06_fixture_replays_both_accepted_number_spans():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    contract=json.loads((root/"tests/fixtures/prophet/q06_source_contract.v0_2.json").read_bytes())
    raw=(root/"tests/fixtures/company_intelligence/aapl_fy2026_q3_ex99_1.htm").read_bytes()
    provenance=contract["field_provenance"]
    assert sha256(raw).hexdigest()==provenance["source_document"]["normalized_body_sha256"]
    for side in ["current","prior"]:
        span=provenance[f"{side}_span"]
        text=raw[span["start"]:span["end"]]
        assert sha256(text).hexdigest()==span["text_sha256"]
        assert float(text.decode("utf-8").replace(",",""))==contract["economic_identity"][side]["value"]


def test_new_method_never_claims_an_old_as_run_recommendation(tmp_path):
    from engine.prophet_lab.earnings_dossier import load_q06_source_field,project_earnings_detail
    _install_q06(tmp_path);field,state=load_q06_source_field(tmp_path)
    result=project_earnings_detail(_q06_vector(),source_field=field,source_state=state)
    assert result["is_original_as_run_recommendation"] is False
    assert result["method_scope"]=="RETROSPECTIVE_FACTUAL_RECONSTRUCTION_NO_AS_RUN_PROMOTION"
