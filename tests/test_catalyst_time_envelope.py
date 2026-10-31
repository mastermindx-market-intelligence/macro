"""Time-envelope tests that distinguish reconstruction from historical availability."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from engine.catalyst_intelligence import assessment_v2 as A2, assessment_v3 as A3
from engine.catalyst_intelligence.peer_context import ContextError, digest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "research/catalyst_intelligence/company_assessment_v2_r5/fixtures"
CUT = "2026-09-28T20:00:08Z"
MATERIALIZED = "2026-09-28T20:00:13Z"
RECEIVED = "2026-09-28T20:00:15Z"
COMPOSED = "2026-09-28T20:00:16Z"


def supplied_v2():
    return json.loads((FIXTURES / "source_revision.request.json").read_text())


def envelope(old):
    if old is None:
        return None
    return {
        "schema": A3.ENVELOPE_SCHEMA, "owner": old["owner"],
        "information_cutoff_at": old["as_of"], "materialized_at": MATERIALIZED,
        "received_at": RECEIVED, "source_ref": old["source_ref"],
        "source_revision": "fixture:r8:" + old["source_ref"],
        "payload_digest": old["payload_digest"], "payload": deepcopy(old["payload"]),
    }


def supplied_v3():
    old = supplied_v2()
    return {
        "schema": A3.INPUT_SCHEMA, "focal": old["focal"],
        "information_cutoff_at": old["decision_at"], "composed_at": COMPOSED,
        "peer_inputs": old["peer_inputs"], "entry": envelope(old["entry"]),
        "news": {
            "fact_log": old["news"]["fact_log"],
            "current_owners": envelope(old["news"]["current_owners"]),
            "comparison": {
                "information_cutoff_at": old["news"]["comparison"]["since_at"],
                "prior_owners": envelope(old["news"]["comparison"]["prior_owners"]),
            },
        },
    }


def test_delayed_materialization_preserves_information_and_owner_bytes():
    req = supplied_v3()
    before = deepcopy(req)
    out = A3.build_stock_assessment_v3(req)
    old = A2.build_stock_assessment_v2(supplied_v2())
    assert req == before
    assert out["information_cutoff_at"] == CUT and out["composed_at"] == COMPOSED
    assert out["news_context"]["current"]["views"] == old["news_context"]["current"]["views"]
    assert out["news_context"]["comparison"]["prior_views"] == old["news_context"]["comparison"]["prior_views"]
    assert out["news_context"]["comparison"]["pairs"] == old["news_context"]["comparison"]["pairs"]
    assert out["peer_context"] == old["peer_context"]
    assert out["entry_context"]["owner_projection"] == old["entry_context"]["owner_projection"]
    meta = out["news_context"]["current"]["source_envelope"]
    assert meta["materialized_at"] == MATERIALIZED and meta["received_at"] == RECEIVED
    assert meta["payload_digest"] == req["news"]["current_owners"]["payload_digest"]
    assert "known_at" not in meta
    assert out["source_admission_established"] is False
    assert out["decision_availability_established"] is False
    assert not any(out["authority"].values())
    assert all(row["value"] is None for row in out["advanced_estimates"].values())


def test_owner_calls_use_each_information_cut_not_artifact_time(monkeypatch):
    calls = []
    real = A3.project_news_theses
    def observe(log, owner, at, **kwargs):
        calls.append((at, kwargs))
        return real(log, owner, at, **kwargs)
    monkeypatch.setattr(A3, "project_news_theses", observe)
    req = supplied_v3()
    A3.build_stock_assessment_v3(req)
    prior = req["news"]["comparison"]["information_cutoff_at"]
    assert [at for at, _ in calls] == [CUT, prior, CUT]
    assert all(at == kwargs["decision_cut"] for at, kwargs in calls)
    assert calls[-1][1]["prior_owners"] == req["news"]["comparison"]["prior_owners"]["payload"]
    assert calls[-1][1]["prior_as_of_utc"] == prior


def test_pre_cut_publication_observed_later_does_not_enter_earlier_view():
    req = supplied_v3()
    before = A3.build_stock_assessment_v3(req)
    records = req["news"]["fact_log"]["records"]
    late = deepcopy(records[0])
    late.update(
        log_seq=max(r["log_seq"] for r in records) + 1,
        fact_id="fact_" + "d" * 24, cluster_id="ev2_" + "d" * 16,
        document_id="doc_synthetic_late_observation",
        observed_at="2026-09-28T20:00:09Z", source_available_at="2026-09-28T20:00:07Z",
    )
    late["fact_key"]["slot"]["horizon_token"] = "FY2030"
    late["provenance"].update(origin_document_id=late["document_id"],
                              origin_claim_id="claim_synthetic_late",
                              root_family_id="root_synthetic_late")
    late["evidence"].update(document_id=late["document_id"], span_id="span_" + "d" * 20)
    late["owner_claim_ids"] = ["claim_synthetic_late"]
    records.append(late)
    after = A3.build_stock_assessment_v3(req)
    semantic = deepcopy(after["news_context"])
    # The owner binds the complete log, including records excluded at this cut.
    # Only that provenance hash may move; visible facts and every semantic field stay fixed.
    for facet, key in (("current", "views"), ("comparison", "prior_views")):
        assert len(semantic[facet][key]) == len(before["news_context"][facet][key])
        for actual, prior in zip(semantic[facet][key], before["news_context"][facet][key]):
            assert actual["log_sha256"] != prior["log_sha256"]
            actual["log_sha256"] = prior["log_sha256"]
    assert semantic == before["news_context"]
    assert after["input_digest"] != before["input_digest"]
    # Demonstrate that this exact late record would enter at the wrong clock.
    wrong = A3.project_news_theses(req["news"]["fact_log"],
                                   req["news"]["current_owners"]["payload"],
                                   COMPOSED, decision_cut=CUT)
    assert late["fact_id"] in {v["original_proposition_fact_id"] for v in wrong}


def test_current_owner_change_does_not_overwrite_independent_prior_owner_state():
    req = supplied_v3()
    before = A3.build_stock_assessment_v3(req)
    current = req["news"]["current_owners"]
    fid = next(iter(current["payload"]["leaf_payloads"]))
    current["payload"]["leaf_payloads"][fid]["incremental"] = 123000000000
    current["payload_digest"] = digest(current["payload"])
    after = A3.build_stock_assessment_v3(req)
    assert after["news_context"]["comparison"]["prior_views"] == before["news_context"]["comparison"]["prior_views"]
    assert after["news_context"]["comparison"]["source_envelopes"]["prior"] == before["news_context"]["comparison"]["source_envelopes"]["prior"]
    assert after["input_digest"] != before["input_digest"]
    assert after["owner_state_qualification"] == A3.QUALIFICATION
    assert after["source_admission_established"] is False


def test_owner_payload_contamination_with_original_digest_refuses():
    req = supplied_v3()
    req["news"]["comparison"]["prior_owners"]["payload"]["leaf_payloads"] = deepcopy(
        req["news"]["current_owners"]["payload"]["leaf_payloads"])
    with pytest.raises(ContextError, match="digest"):
        A3.build_stock_assessment_v3(req)


@pytest.mark.parametrize("field,value", [
    ("information_cutoff_at", "2026-09-28T20:00:08.000001Z"),
    ("materialized_at", "2026-09-28T20:00:07.999999Z"),
    ("received_at", "2026-09-28T20:00:12.999999Z"),
    ("received_at", "2026-09-28T20:00:16.000001Z"),
    ("schema", "unrecognized"),
    ("owner", "foreign"),
    ("source_ref", " "),
    ("source_revision", ""),
    ("payload_digest", "sha256:" + "0" * 64),
    ("payload", []),
])
def test_invalid_source_binding_and_clock_order_refuse(field, value):
    req = supplied_v3()
    req["news"]["current_owners"][field] = value
    with pytest.raises(ContextError):
        A3.build_stock_assessment_v3(req)


@pytest.mark.parametrize("field", ["information_cutoff_at", "materialized_at", "received_at"])
@pytest.mark.parametrize("value", [
    "2026-09-28T20:00Z", "2026-09-28T20:00:08.0000001Z",
    "2026-09-28T20:00:08+00:00", "2026-09-28T24:00:00Z",
])
def test_clock_precision_is_not_silently_normalized(field, value):
    req = supplied_v3()
    req["news"]["current_owners"][field] = value
    with pytest.raises(ContextError):
        A3.build_stock_assessment_v3(req)


def test_composition_cannot_precede_information_cut():
    req = supplied_v3(); req["composed_at"] = "2026-09-28T20:00:07Z"
    with pytest.raises(ContextError, match="composition precedes"):
        A3.build_stock_assessment_v3(req)


def test_owner_evidence_clock_spelling_remains_literal():
    req = supplied_v3()
    req["news"]["current_owners"]["information_cutoff_at"] = CUT[:-1] + ".000Z"
    with pytest.raises(ContextError, match="explicit owner decision_cut"):
        A3.build_stock_assessment_v3(req)


@pytest.mark.parametrize("where", ["request", "envelope"])
def test_caller_cannot_supply_an_admission_flag(where):
    req = supplied_v3()
    target = req if where == "request" else req["news"]["current_owners"]
    target["source_admission_established"] = True
    with pytest.raises(ContextError, match="closed"):
        A3.build_stock_assessment_v3(req)


def test_missing_history_does_not_hide_available_current_facets():
    req = supplied_v3()
    req["news"]["comparison"]["prior_owners"] = None
    out = A3.build_stock_assessment_v3(req)
    assert out["news_context"]["current"]["state"] == "PROJECTED_RESEARCH"
    assert out["news_context"]["comparison"]["reason_code"] == "PRIOR_OWNER_INPUT_NOT_SUPPLIED"
    assert out["news_context"]["comparison"]["prior_views"] is None
    assert out["entry_context"]["state"] == "OWNER_RESEARCH_CONTEXT_ATTACHED"
    assert out["peer_context"]["state"] == "PROJECTED"


def test_missing_current_does_not_promote_history():
    req = supplied_v3(); req["news"]["current_owners"] = None
    out = A3.build_stock_assessment_v3(req)
    assert out["news_context"]["current"]["views"] is None
    assert out["news_context"]["comparison"]["pairs"] is None
    assert out["entry_context"]["state"] == "OWNER_RESEARCH_CONTEXT_ATTACHED"


def test_unrequested_history_does_not_invent_a_comparison(monkeypatch):
    req = supplied_v3(); req["news"]["comparison"] = None
    calls = []
    real = A3.project_news_theses
    def observe(*args, **kwargs):
        calls.append(kwargs)
        return real(*args, **kwargs)
    monkeypatch.setattr(A3, "project_news_theses", observe)
    out = A3.build_stock_assessment_v3(req)
    assert out["news_context"]["comparison"]["state"] == "NOT_REQUESTED"
    assert len(calls) == 1 and "prior_owners" not in calls[0]


def test_bad_prior_stays_a_refusal_when_current_is_missing():
    req = supplied_v3(); req["news"]["current_owners"] = None
    req["news"]["comparison"]["prior_owners"]["payload_digest"] = "bad"
    with pytest.raises(ContextError, match="digest"):
        A3.build_stock_assessment_v3(req)


def test_malformed_fact_log_stays_a_refusal_when_current_is_missing():
    req = supplied_v3(); req["news"]["current_owners"] = None
    req["news"]["fact_log"] = {"schema": "invalid"}
    with pytest.raises(ContextError, match="fact log"):
        A3.build_stock_assessment_v3(req)


def test_delayed_entry_retains_owner_chase_block_and_evaluation_clocks():
    req = supplied_v3()
    entry = A3.build_stock_assessment_v3(req)["entry_context"]
    assert entry["owner_projection"] == req["entry"]["payload"]
    assert entry["owner_projection"]["entry_open"] is False
    assert entry["owner_projection"]["state"] == "RAN_DONT_CHASE"
    assert entry["owner_projection"]["evaluated_at"] == CUT
    assert entry["decision_availability_established"] is False
    assert entry["interpretation"] == "RECONSTRUCTED_CONTEXT_IS_NOT_CURRENT_ENTRY_AVAILABILITY"


def test_older_entry_evaluation_cannot_become_the_new_cut():
    req = supplied_v3()
    req["peer_inputs"] = req["news"] = None
    req["information_cutoff_at"] = "2026-09-28T20:00:09Z"
    req["entry"]["information_cutoff_at"] = req["information_cutoff_at"]
    out = A3.build_stock_assessment_v3(req)
    assert out["entry_context"]["state"] == "DIFFERENT_INFORMATION_CUT"
    assert out["entry_context"]["owner_projection"] is None


def test_peer_knowability_still_uses_information_cut_not_composition_time():
    req = supplied_v3()
    req["peer_inputs"]["observations"][1]["known_at"] = "2026-09-28T20:00:09Z"
    peers = A3.build_stock_assessment_v3(req)["peer_context"]["context"]
    assert peers["coverage"]["observed_peer_issuers"] == 2
    assert {"security_id": "P1", "reason": "PRICE_NOT_KNOWN_AT_DECISION"} in peers["excluded"]


def test_v3_cli_runs_the_real_owner_composition():
    req = supplied_v3()
    result = subprocess.run([sys.executable, "-m", "engine.catalyst_intelligence"],
                            cwd=ROOT, input=json.dumps(req), text=True,
                            capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == A3.build_stock_assessment_v3(req)
