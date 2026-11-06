"""Outcome-bound tests for the shadow-only GMI successor; no store/provider writes."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "engine/theme_graph/theme_state.py"
QUERY = {"effective_at": "2026-10-03", "known_at": "2026-10-03T12:00:00Z"}
GRAPH = "graph-20261003"
GENERATIONS = {role: role + "-20261003" for role in
               ("ontology", "identity", "membership", "rights", "eligibility", "narrative", "specialist")}


def module():
    assert MODULE.exists(), "missing successor module: the old shape adapter cannot meet this contract"
    spec = importlib.util.spec_from_file_location("bounded_theme_state", MODULE)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def receipt(owner, payload, subject="ltheme:finviz:power_grid", **changes):
    result = {
        "owner": owner, "schema": "fixture." + owner + "/v1",
        "generation_id": GENERATIONS[owner], "graph_generation_id": GRAPH,
        "subject_id": subject, "query": copy.deepcopy(QUERY),
        "effective_at": "2026-10-03", "known_at": "2026-10-03T09:00:00Z",
        "available_at": "2026-10-03T08:00:00Z", "recorded_at": "2026-10-03T09:00:00Z",
        "availability": "AVAILABLE", "payload": payload, "sha256": digest(payload),
    }
    result.update(changes)
    return result


def subject(node="ltheme:finviz:power_grid", mapping=None, qualified=False):
    canonical = node.startswith("theme:")
    owners = {
        "ontology": receipt("ontology", {
            "canonical_mapping": {"state": "SUBJECT_IS_CANONICAL" if canonical else
                                  ("MAPPED" if mapping else "UNMAPPED"),
                                  "theme_node_ids": mapping or []}
        }, node),
        "identity": receipt("identity", {"status": "RESOLVED", "issuer_ids": ["issuer:HUBB"]}, node),
        "membership": receipt("membership", {"status": "AVAILABLE", "members": [
            {"ticker": "HUBB", "issuer_id": "issuer:HUBB", "security_id": "security:HUBB"}],
            "declared_count": 1, "eligible_count": 1, "observed_count": 1,
            "basis": "qualified_owner_query", "era": "OBSERVED"}, node),
        "rights": receipt("rights", {"allowed": True, "purpose": "research_internal",
                                    "revision": "rights-r1"}, node),
        "eligibility": receipt("eligibility", {"status": "QUALIFIED" if qualified else
                                               "NOT_QUALIFIED", "policy_revision":
                                               "d2e-r1" if qualified else None,
                                               "reason_codes": [] if qualified else ["D2E_UNSEALED"]}, node),
    }
    return {
        "node_id": node, "kind": "canonical_theme" if canonical else "local_theme",
        "name_en": "Power grid", "name_zh": "电网",
        "source_family": None if canonical else "finviz", "native_id": None if canonical else "power_grid",
        "owners": owners, "observations": {}, "canonical_aggregation": None,
    }


def compose(inputs=None, **changes):
    options = dict(graph_generation_id=GRAPH, owner_generations=GENERATIONS,
                   effective_at=QUERY["effective_at"], known_at=QUERY["known_at"],
                   generated_at="2026-10-03T12:00:00Z")
    options.update(changes)
    return module().compose_state(inputs or [subject()], **options)


def observation(value, node="ltheme:finviz:power_grid", **changes):
    result = {"owner": "specialist", "schema": "specialist.native/v1",
              "presence": "POSITIVE", "freshness": "FRESH", "value": value,
              "null_reason": None, "units": "percentage_points", "window": "5_closed_sessions",
              "coverage": {"declared": 2, "observed": 1, "basis": "CURRENT_MEMBERSHIP_NOT_PIT"},
              "conflicts": [], "source_receipts": [receipt("specialist", value, node, effective_at="2026-10-03T08:00:00Z")],
              "freshness_policy": {"max_age_hours": 30, "owner_policy_revision": "state-default-30h"}}
    result.update(changes)
    return result


def test_unmapped_local_is_descriptively_usable_but_not_qualified():
    state = compose()
    local = state["subjects"][0]
    assert local["availability"] == "AVAILABLE"
    assert local["mapping"]["state"] == "UNMAPPED"
    assert local["mapping"]["theme_node_ids"] == []
    assert local["eligibility"]["status"] == "NOT_QUALIFIED"
    assert state["schema"] == "theme_state/v1" and state["mode"] == "shadow"
    assert not any(v for k, v in state["authority"].items() if k.startswith("may_"))


def test_mapped_local_and_canonical_coexist_without_implicit_aggregation():
    local = subject(mapping=["theme:electrification"])
    canonical = subject("theme:electrification")
    state = compose([local, canonical])
    assert {s["node_id"] for s in state["subjects"]} == {local["node_id"], canonical["node_id"]}
    can = next(s for s in state["subjects"] if s["kind"] == "canonical_theme")
    assert can["aggregation"] == {"status": "UNAVAILABLE", "receipt": None,
                                  "reason_codes": ["CANONICAL_AGGREGATION_UNSUPPLIED"]}


def test_specialist_facts_nulls_conflicts_units_and_order_are_preserved():
    src = subject()
    value = {"acceleration": None, "null_reason": "SHORT_HISTORY", "return": 1.25,
             "members": ["HUBB", "IBP"], "entry_ready": True}
    obs = observation(value, conflicts=[{"owner": "other_native", "value": -1.0,
                                        "reason": "DIFFERENT_WINDOW"}])
    src["observations"]["closed_session_leadership"] = obs
    before = copy.deepcopy(src)
    out = compose([src])["subjects"][0]["observations"]["closed_session_leadership"]
    assert out == obs
    assert src == before


@pytest.mark.parametrize("role,field,bad", [
    ("membership", "graph_generation_id", "other-graph"),
    ("identity", "generation_id", "other-identity"),
    ("ontology", "subject_id", "ltheme:finviz:housing"),
    ("rights", "sha256", "0" * 64),
])
def test_owner_generation_identity_or_digest_substitution_refuses(role, field, bad):
    src = subject()
    src["owners"][role][field] = bad
    with pytest.raises(ValueError):
        compose([src])


@pytest.mark.parametrize("clock,value,reason", [
    ("known_at", "2026-10-03", "KNOWLEDGE_TIME_UNPROVEN"),
    ("available_at", "2026-10-04T09:00:00Z", "SOURCE_AFTER_CUTOFF"),
    ("recorded_at", "2026-10-04T09:00:00Z", "SOURCE_AFTER_CUTOFF"),
])
def test_historical_cutoff_refuses_unproved_same_day_and_later_receipts(clock, value, reason):
    src = subject()
    src["owners"]["membership"][clock] = value
    if clock == "available_at":
        src["owners"]["membership"]["known_at"] = value
        src["owners"]["membership"]["recorded_at"] = value
    result = compose([src])["subjects"][0]
    assert result["availability"] == "UNAVAILABLE"
    assert reason in result["reason_codes"]


def test_date_precision_prior_day_is_honest_and_supported():
    src = subject()
    for field in ("known_at", "available_at", "recorded_at"):
        src["owners"]["membership"][field] = "2026-10-02"
    assert compose([src])["subjects"][0]["availability"] == "AVAILABLE"


def test_query_receipt_cannot_substitute_latest_for_requested_history():
    src = subject()
    src["owners"]["membership"]["query"]["known_at"] = "2026-10-04T12:00:00Z"
    with pytest.raises(ValueError, match="query"):
        compose([src])


@pytest.mark.parametrize("allowed,purpose", [(False, "research_internal"), (True, "public_display")])
def test_rights_owner_refusal_and_wrong_use_are_not_membership_absence(allowed, purpose):
    src = subject()
    r = src["owners"]["rights"]
    r["payload"].update(allowed=allowed, purpose=purpose)
    r["sha256"] = digest(r["payload"])
    out = compose([src])["subjects"][0]
    assert out["availability"] == "UNAVAILABLE"
    assert "RIGHTS_NOT_ADMITTED" in out["reason_codes"]


def test_measurement_candidate_and_unsealed_policy_never_mean_qualified():
    src = subject()
    r = src["owners"]["eligibility"]
    r["payload"] = {"status": "measurement_candidate", "policy_revision": None, "reason_codes": []}
    r["sha256"] = digest(r["payload"])
    assert compose([src])["subjects"][0]["eligibility"]["status"] == "NOT_QUALIFIED"


@pytest.mark.parametrize("ticker,basket", [("HUBB", "power_grid"), ("ABNB", "travel"), ("IBP", "housing")])
def test_real_shaped_numeric_legs_and_recommended_rows_produce_only_subset_overlap(ticker, basket):
    ne = receipt("narrative", {"schema": "narrative_emergence.v1", "narratives": [
        {"signature": "cluster1", "legs": {"tighten": .8, "momentum": .3},
         "recommended": [{"ticker": ticker}, {"ticker": "OTHER"}]}]})
    mb = receipt("membership", {"basket_id": basket, "members": [{"ticker": ticker}]})
    obs = module().adapt_recommended_overlap(ne, mb, basket_id=basket, **QUERY)
    assert obs["presence"] == "POSITIVE"
    assert obs["value"] == {"has_overlap": True, "matched_tickers": [ticker],
                            "narrative_signatures": ["cluster1"],
                            "coverage_basis": "top_5_entry_quality_subset"}
    assert ne["payload"]["narratives"][0]["legs"] == {"tighten": .8, "momentum": .3}


@pytest.mark.parametrize("availability,payload,presence,reason", [
    ("VALID_EMPTY", {"narratives": []}, "VALID_EMPTY", None),
    ("UNAVAILABLE", None, "UNAVAILABLE", "OWNER_UNAVAILABLE"),
    ("AVAILABLE", {"narratives": []}, "UNAVAILABLE", "EMPTY_NOT_ADMITTED"),
    ("AVAILABLE", {"narratives": [{"legs": [], "recommended": "bad"}]}, "INVALID", "MALFORMED_NARRATIVE"),
])
def test_valid_empty_unavailable_and_malformed_are_distinct(availability, payload, presence, reason):
    ne = receipt("narrative", payload, availability=availability)
    mb = receipt("membership", {"basket_id": "power_grid", "members": [{"ticker": "HUBB"}]})
    obs = module().adapt_recommended_overlap(ne, mb, basket_id="power_grid", **QUERY)
    assert obs["presence"] == presence and obs["null_reason"] == reason
    if presence in {"UNAVAILABLE", "INVALID"}:
        assert obs["value"] is None


@pytest.mark.parametrize("stamp,freshness", [("2026-09-20", "STALE"), ("2099-01-01", "FUTURE")])
def test_fresh_build_does_not_refresh_old_or_future_observation(stamp, freshness):
    ne = receipt("narrative", {"narratives": [{"signature": "x", "legs": {"tighten": .2},
                                             "recommended": [{"ticker": "HUBB"}]}]}, effective_at=stamp)
    mb = receipt("membership", {"basket_id": "power_grid", "members": [{"ticker": "HUBB"}]})
    obs = module().adapt_recommended_overlap(ne, mb, basket_id="power_grid", **QUERY)
    assert obs["freshness"] == freshness
    if freshness == "FUTURE":
        assert obs["value"] is None


def test_membership_adapter_requires_owner_resolved_members_not_tickers_fallback():
    ne = receipt("narrative", {"narratives": [{"signature": "x", "legs": {"tighten": .2},
                                             "recommended": [{"ticker": "HUBB"}]}]})
    mb = receipt("membership", {"basket_id": "power_grid", "tickers": ["HUBB"]})
    result = module().adapt_recommended_overlap(ne, mb, basket_id="power_grid", **QUERY)
    assert result["presence"] == "INVALID" and result["null_reason"] == "MALFORMED_MEMBERSHIP"


def test_state_digest_authority_and_unknown_keys_are_fail_closed():
    state = compose()
    for mutate in (
        lambda s: s["subjects"][0].update(name_en="substituted"),
        lambda s: s["authority"].update(may_rank=True),
        lambda s: s.update(universal_score=99),
    ):
        broken = copy.deepcopy(state)
        mutate(broken)
        with pytest.raises(ValueError):
            module().validate_state(broken)


def test_reader_is_exact_generation_and_does_not_supply_later_knowledge():
    state = compose()
    reader = module().read_theme_state
    found = reader(state, "ltheme:finviz:power_grid", **QUERY,
                   expected_generation_id=state["generation_id"])
    assert found["status"] == "DESCRIPTIVE" and found["subject"]["node_id"] == found["subject_id"]
    assert found["state_sha256"] == state["state_sha256"]
    early = reader(state, found["subject_id"], effective_at=QUERY["effective_at"],
                   known_at="2026-10-03T08:30:00Z")
    assert early["status"] == "UNAVAILABLE" and early["subject"] is None
    wrong = reader(state, found["subject_id"], **QUERY, expected_generation_id="0" * 32)
    assert wrong["status"] == "UNAVAILABLE" and "GENERATION_MISMATCH" in wrong["reason_codes"]


def test_correction_creates_later_generation_without_rewriting_previous():
    old = compose()
    frozen = copy.deepcopy(old)
    src = subject()
    for r in src["owners"].values():
        r["query"]["known_at"] = "2026-10-03T14:00:00Z"
    new = compose([src], known_at="2026-10-03T14:00:00Z", generated_at="2026-10-03T14:00:00Z", previous=old)
    assert new["generation_id"] != old["generation_id"]
    assert new["correction"]["generation_id"] == old["generation_id"]
    assert new["correction"]["state_sha256"] == old["state_sha256"]
    assert old == frozen
    with pytest.raises(ValueError, match="later"):
        compose(previous=old)


def test_explicit_canonical_aggregation_receipt_required_and_never_invents_mean():
    src = subject("theme:electrification")
    src["canonical_aggregation"] = receipt("specialist", {
        "method": "owner_declared_union", "member_subject_ids": ["ltheme:finviz:power_grid"],
        "value": None, "null_reason": "ECONOMIC_MAGNITUDE_UNSUPPORTED"}, src["node_id"])
    state = compose([src])
    result = state["subjects"][0]
    assert result["aggregation"]["status"] == "SUPPLIED"
    assert result["aggregation"]["receipt"] == src["canonical_aggregation"]
    assert "score" not in result and "mean" not in result


def test_legacy_projection_is_from_same_generation_and_preserves_original_meaning():
    src = subject("theme:electrification")
    raw = {"theme_id": "electrification", "name_en": "Electrification", "name_zh": "电气化",
           "foresight": {"score": 12, "entry_ready": True}, "narrative": None,
           "basket_ids": ["power_grid"], "subsector_rotation": {"rollup_quadrant": None}}
    src["observations"]["legacy_context"] = observation(raw, src["node_id"], units=None, window=None)
    state = compose([src])
    legacy = module().legacy_projection(state)
    assert legacy["themes"] == [raw]
    assert legacy["lineage"]["generation_id"] == state["generation_id"]
    assert legacy["lineage"]["historical_reclassification"] is False
    assert not legacy["authority"]["may_publish"]


def test_deterministic_input_order_and_duplicate_subject_refusal():
    a, b = subject(), subject("ltheme:ths:power_grid")
    b["source_family"], b["native_id"] = "ths", "power_grid"
    assert compose([a, b]) == compose([b, a])
    with pytest.raises(ValueError, match="duplicate"):
        compose([a, a])


def test_contract_schema_is_closed_and_compiler_is_not_a_writer():
    state = compose()
    schema_path = MODULE.parents[2] / "contracts/theme_graph/theme_state.v1.schema.json"
    import jsonschema
    schema = json.loads(schema_path.read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(state, schema)
    source = MODULE.read_text()
    for forbidden in ("write_text(", "write_bytes(", "read_parquet(", "to_parquet(", "requests.", "datetime.now(", "read_edges("):
        assert forbidden not in source

def test_date_only_source_age_interval_cannot_be_called_fresh():
    ne = receipt("narrative", {"narratives": [{"signature": "x", "legs": {"tighten": .2},
                                             "recommended": [{"ticker": "HUBB"}]}]}, effective_at="2026-10-02")
    mb = receipt("membership", {"basket_id": "power_grid", "members": [{"ticker": "HUBB"}]})
    obs = module().adapt_recommended_overlap(ne, mb, basket_id="power_grid", **QUERY)
    assert obs["presence"] == "POSITIVE" and obs["freshness"] == "UNKNOWN"


def test_forged_fresh_status_is_rederived_from_source_facts_not_build_time():
    src = subject()
    value = {"return": 1.25}
    obs = observation(value)
    obs["source_receipts"][0]["effective_at"] = "2026-09-20"
    src["observations"]["leadership"] = obs
    out = compose([src])["subjects"][0]["observations"]["leadership"]
    assert out["value"] == value and out["freshness"] == "STALE"


def test_unavailable_canonical_aggregation_retains_rejected_receipt_and_reasons():
    src = subject("theme:electrification")
    src["canonical_aggregation"] = receipt("specialist", {"method": "owner_declared_union"},
                                          src["node_id"], known_at="2026-10-04T09:00:00Z",
                                          recorded_at="2026-10-04T09:00:00Z")
    out = compose([src])["subjects"][0]["aggregation"]
    assert out["status"] == "UNAVAILABLE" and out["receipt"] == src["canonical_aggregation"]
    assert "SOURCE_AFTER_CUTOFF" in out["reason_codes"]


@pytest.mark.parametrize("replace_from,replace_to,case", [
    ('if graph_generation_id is not None and receipt["graph_generation_id"] != graph_generation_id:',
     'if False:', "graph"),
    ('if canonical_sha256(receipt["payload"]) != receipt["sha256"]:',
     'if False:', "digest"),
    ('return stamp.date() < end.date()', 'return stamp.date() <= end.date()', "same_day"),
    ('"may_rank": False', '"may_rank": True', "authority"),
    ('if not _proven_by(artifact["known_at"], known_at):\n        reasons.append("STATE_AFTER_CUTOFF")\n    if not _proven_by(artifact["generated_at"], known_at):\n        reasons.append("STATE_NOT_YET_EMITTED")',
     'if False:\n        reasons.append("STATE_AFTER_CUTOFF")', "cutoff"),
])
def test_meaningful_source_mutants_are_killed(monkeypatch, replace_from, replace_to, case):
    import types
    source = MODULE.read_text()
    assert replace_from in source
    mutant = types.ModuleType("theme_state_mutant")
    mutant.__file__ = str(MODULE)
    exec(compile(source.replace(replace_from, replace_to, 1), str(MODULE), "exec"), mutant.__dict__)
    monkeypatch.setattr(__import__(__name__, fromlist=["module"]), "module", lambda: mutant)
    with pytest.raises((AssertionError, ValueError, pytest.fail.Exception)):
        if case == "graph":
            test_owner_generation_identity_or_digest_substitution_refuses("membership", "graph_generation_id", "other-graph")
        elif case == "digest":
            test_owner_generation_identity_or_digest_substitution_refuses("rights", "sha256", "0" * 64)
        elif case == "same_day":
            test_historical_cutoff_refuses_unproved_same_day_and_later_receipts("known_at", "2026-10-03", "KNOWLEDGE_TIME_UNPROVEN")
        elif case == "authority":
            test_unmapped_local_is_descriptively_usable_but_not_qualified()
        else:
            test_reader_is_exact_generation_and_does_not_supply_later_knowledge()

@pytest.mark.parametrize("role,payload,reason", [
    ("ontology", [], "ONTOLOGY_INPUT_INVALID"),
    ("identity", [], "IDENTITY_NOT_RESOLVED"),
    ("membership", {"status": "AVAILABLE", "members": [], "declared_count": 0,
                    "eligible_count": 1, "observed_count": 0}, "MEMBERSHIP_INPUT_INVALID"),
])
def test_malformed_required_owner_payload_is_not_an_unmapped_or_empty_success(role, payload, reason):
    src = subject()
    src["owners"][role]["payload"] = payload
    src["owners"][role]["sha256"] = digest(payload)
    out = compose([src])["subjects"][0]
    assert out["availability"] == "UNAVAILABLE" and reason in out["reason_codes"]


def test_null_native_observation_requires_explicit_presence_and_reason():
    src = subject()
    obs = observation(None)
    obs["source_receipts"][0]["payload"] = {"magnitude": None, "reason": "UNSUPPORTED"}
    obs["source_receipts"][0]["sha256"] = digest(obs["source_receipts"][0]["payload"])
    src["observations"]["economic_share"] = obs
    with pytest.raises(ValueError, match="typed"):
        compose([src])

@pytest.mark.parametrize("legs", [{"tighten": {"tickers": ["HUBB"]}}, {"tighten": True}, {"tighten": 2}, []])
def test_malformed_numeric_narrative_legs_are_not_a_positive_observation(legs):
    ne = receipt("narrative", {"narratives": [{"signature": "x", "legs": legs,
                                             "recommended": [{"ticker": "HUBB"}]}]})
    mb = receipt("membership", {"basket_id": "power_grid", "members": [{"ticker": "HUBB"}]})
    obs = module().adapt_recommended_overlap(ne, mb, basket_id="power_grid", **QUERY)
    assert obs["presence"] == "INVALID" and obs["null_reason"] == "MALFORMED_NARRATIVE"


def test_closed_read_receipt_schema_qualifies_both_usable_and_unavailable():
    import jsonschema
    schema = json.loads((MODULE.parents[2] / "contracts/theme_graph/theme_state.v1.schema.json").read_text())
    read_schema = {"$ref": "#/$defs/read_receipt", "$defs": schema["$defs"]}
    state = compose()
    good = module().read_theme_state(state, state["subjects"][0]["node_id"], **QUERY)
    missing = module().read_theme_state(state, "ltheme:finviz:unknown", **QUERY)
    for receipt_value in (good, missing):
        jsonschema.validate(receipt_value, read_schema)
    good["status"] = "UNAVAILABLE"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(good, read_schema)


def test_state_age_is_not_transport_cache_age():
    state = compose()
    old = module().read_theme_state(state, state["subjects"][0]["node_id"],
                                   effective_at=QUERY["effective_at"], known_at="2026-10-05T12:00:00Z")
    assert old["status"] == "UNAVAILABLE" and "STATE_STALE" in old["reason_codes"]


def test_unavailable_observation_receipt_cannot_assert_a_positive_value():
    src = subject()
    obs = observation({"return": 1.25})
    obs["source_receipts"][0] = receipt("specialist", None, availability="UNAVAILABLE",
                                          effective_at="2026-10-03T08:00:00Z")
    src["observations"]["leadership"] = obs
    out = compose([src])["subjects"][0]["observations"]["leadership"]
    assert out["presence"] == "UNAVAILABLE" and out["value"] is None
    assert out["null_reason"] == "OWNER_UNAVAILABLE"
    assert out["source_receipts"] == obs["source_receipts"]


@pytest.mark.parametrize("budget", [float("inf"), float("nan")])
def test_nonfinite_freshness_budget_is_not_an_owner_policy(budget):
    ne = receipt("narrative", {"narratives": []}, availability="VALID_EMPTY")
    mb = receipt("membership", {"basket_id": "power_grid", "members": []}, availability="VALID_EMPTY")
    with pytest.raises(ValueError, match="finite"):
        module().adapt_recommended_overlap(ne, mb, basket_id="power_grid", max_age_hours=budget, **QUERY)


@pytest.mark.parametrize("status,eligibility,availability", [
    ("QUALIFIED", "NOT_QUALIFIED", "AVAILABLE"),
    ("DESCRIPTIVE", "QUALIFIED", "AVAILABLE"),
    ("QUALIFIED", "QUALIFIED", "UNAVAILABLE"),
])
def test_read_wire_cannot_contradict_owner_eligibility_or_availability(status, eligibility, availability):
    import jsonschema
    schema = json.loads((MODULE.parents[2] / "contracts/theme_graph/theme_state.v1.schema.json").read_text())
    state = compose([subject(qualified=True)])
    result = module().read_theme_state(state, state["subjects"][0]["node_id"], **QUERY)
    result["status"] = status
    result["subject"]["eligibility"]["status"] = eligibility
    result["subject"]["availability"] = availability
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(result, {"$ref": "#/$defs/read_receipt", "$defs": schema["$defs"]})


def test_reader_exposes_exact_precise_generation_clock_for_downstream_audit():
    import jsonschema
    state = compose()
    result = module().read_theme_state(state, state["subjects"][0]["node_id"], **QUERY)
    assert result["state_generated_at"] == state["generated_at"]
    assert set(result) == {"schema", "status", "reason_codes", "subject_id", "generation_id",
                           "state_sha256", "state_generated_at", "effective_at", "known_at", "subject"}
    early = module().read_theme_state(state, result["subject_id"], effective_at=QUERY["effective_at"],
                                     known_at="2026-10-03T10:00:00Z")
    assert early["status"] == "UNAVAILABLE" and early["state_generated_at"] == state["generated_at"]
    assert "STATE_NOT_YET_EMITTED" in early["reason_codes"]
    schema = json.loads((MODULE.parents[2] / "contracts/theme_graph/theme_state.v1.schema.json").read_text())
    result["state_generated_at"] = None
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(result, {"$ref": "#/$defs/read_receipt", "$defs": schema["$defs"]})


def test_build_date_cannot_claim_a_precise_generation_emission_clock():
    with pytest.raises(ValueError, match="precise"):
        compose(generated_at="2026-10-04")


@pytest.mark.parametrize("change", ["native_id", "mapped_empty"])
def test_review_exact_native_identity_and_mapping_witnesses(change):
    src = subject()
    if change == "native_id":
        src["native_id"] = "wrong"
    else:
        r = src["owners"]["ontology"]
        r["payload"]["canonical_mapping"] = {"state": "MAPPED", "theme_node_ids": []}
        r["sha256"] = digest(r["payload"])
    with pytest.raises(ValueError):
        compose([src])


def test_review_date_only_impossible_chronology_witness():
    src = subject()
    r = src["owners"]["membership"]
    r.update(available_at="2026-10-02", known_at="2026-10-01", recorded_at="2026-10-02")
    with pytest.raises(ValueError, match="chronology"):
        compose([src])


def test_review_observed_coverage_cannot_exceed_declared_witness():
    src = subject()
    src["observations"]["leadership"] = observation({"return": 1.25},
        coverage={"declared": 1, "observed": 99, "basis": "owner_population"})
    with pytest.raises(ValueError, match="coverage"):
        compose([src])


def test_review_empty_membership_requires_owner_admission_witness():
    ne = receipt("narrative", {"narratives": [{"signature": "x", "legs": {"tighten": .2},
                                             "recommended": [{"ticker": "HUBB"}]}]})
    mb = receipt("membership", {"basket_id": "power_grid", "members": []})
    obs = module().adapt_recommended_overlap(ne, mb, basket_id="power_grid", **QUERY)
    assert obs["presence"] == "UNAVAILABLE" and obs["value"] is None
    assert obs["null_reason"] == "MEMBERSHIP_EMPTY_NOT_ADMITTED"


def test_review_legacy_duplicate_identity_witness():
    inputs = [subject("theme:electrification"), subject("theme:solar")]
    for src in inputs:
        src["observations"]["legacy_context"] = observation({"theme_id": "electrification"}, src["node_id"])
    with pytest.raises(ValueError):
        module().legacy_projection(compose(inputs))


def test_review_rehashed_correction_reference_identity_witness():
    old = compose()
    src = subject()
    for r in src["owners"].values():
        r["query"]["known_at"] = "2026-10-03T14:00:00Z"
    new = compose([src], known_at="2026-10-03T14:00:00Z", generated_at="2026-10-03T14:00:00Z", previous=old)
    new["correction"]["generation_id"] = "0" * 32
    new["state_sha256"] = digest({k: v for k, v in new.items() if k not in {"state_sha256", "generation_id"}})
    new["generation_id"] = new["state_sha256"][:32]
    with pytest.raises(ValueError, match="correction"):
        module().validate_state(new)


def test_review_previous_emitted_after_correction_witness():
    old = compose(generated_at="2026-10-05T12:00:00Z")
    src = subject()
    for r in src["owners"].values():
        r["query"]["known_at"] = "2026-10-03T14:00:00Z"
    with pytest.raises(ValueError, match="emission"):
        compose([src], known_at="2026-10-03T14:00:00Z", generated_at="2026-10-03T14:00:00Z", previous=old)


@pytest.mark.parametrize("available,known,recorded,accepted", [
    ("2026-10-01", "2026-10-02", "2026-10-02", True),
    ("2026-10-01", "2026-10-01T12:00:00Z", "2026-10-01T12:00:00Z", True),
    ("2026-10-01T12:00:00Z", "2026-10-01", "2026-10-02", True),
    ("2026-10-02", "2026-10-01T23:59:59Z", "2026-10-02", False),
    ("2026-10-02T00:00:00Z", "2026-10-01", "2026-10-02", False),
    ("2026-10-01", "2026-10-02", "2026-10-01", False),
])
def test_precision_bounds_preserve_lawful_mixed_clocks_and_reject_definite_order(available, known, recorded, accepted):
    src = subject()
    src["owners"]["membership"].update(available_at=available, known_at=known, recorded_at=recorded)
    if accepted:
        assert compose([src])["subjects"][0]["availability"] == "AVAILABLE"
    else:
        with pytest.raises(ValueError, match="chronology"):
            compose([src])


def test_incumbent_ths_numeric_native_code_remains_exact():
    src = subject("ltheme:ths:885555")
    src.update(source_family="ths", native_id="885555")
    result = compose([src])["subjects"][0]
    assert result["node_id"] == "ltheme:ths:885555" and result["native_id"] == "885555"
    assert result["mapping"]["state"] == "UNMAPPED" and result["availability"] == "AVAILABLE"


@pytest.mark.parametrize("destinations", [["theme:solar", "theme:solar"], ["theme:"], ["basket:us:solar"]])
def test_mapping_destinations_cannot_duplicate_or_leave_canonical_namespace(destinations):
    with pytest.raises(ValueError):
        compose([subject(mapping=destinations)])


@pytest.mark.parametrize("admission,members,eligible,observed,expected", [
    ("AVAILABLE", [], 0, 0, "UNAVAILABLE"),
    ("VALID_EMPTY", [], 0, 0, "AVAILABLE"),
    ("VALID_EMPTY", [{"ticker": "HUBB"}], 1, 1, "UNAVAILABLE"),
])
def test_membership_owner_admission_consistency_preserves_receipt(admission, members, eligible, observed, expected):
    src = subject()
    r = src["owners"]["membership"]
    r["availability"] = admission
    r["payload"].update(status=admission, members=members, eligible_count=eligible, observed_count=observed)
    r["sha256"] = digest(r["payload"])
    out = compose([src])["subjects"][0]
    assert out["availability"] == expected
    assert out["owner_receipts"]["membership"] == r


def test_admitted_empty_membership_remains_lawful_distinct_overlap():
    ne = receipt("narrative", {"narratives": [{"signature": "x", "legs": {"tighten": .2},
                                             "recommended": [{"ticker": "HUBB"}]}]})
    mb = receipt("membership", {"basket_id": "power_grid", "members": []}, availability="VALID_EMPTY")
    obs = module().adapt_recommended_overlap(ne, mb, basket_id="power_grid", **QUERY)
    assert obs["presence"] == "VALID_EMPTY" and obs["value"]["has_overlap"] is False
    assert obs["coverage"]["declared"] == obs["coverage"]["observed"] == 0


def test_single_legacy_identity_cannot_name_another_canonical_subject():
    src = subject("theme:solar")
    src["observations"]["legacy_context"] = observation({"theme_id": "electrification"}, src["node_id"])
    with pytest.raises(ValueError, match="crosswalk equivalence"):
        module().legacy_projection(compose([src]))


def test_standalone_correction_rejects_rehashed_later_prior_emission():
    old = compose()
    src = subject()
    for r in src["owners"].values():
        r["query"]["known_at"] = "2026-10-03T14:00:00Z"
    new = compose([src], known_at="2026-10-03T14:00:00Z", generated_at="2026-10-03T14:00:00Z", previous=old)
    assert new["correction"]["generated_at"] == old["generated_at"]
    new["correction"]["generated_at"] = "2026-10-05T12:00:00Z"
    new["state_sha256"] = digest({k: v for k, v in new.items() if k not in {"state_sha256", "generation_id"}})
    new["generation_id"] = new["state_sha256"][:32]
    with pytest.raises(ValueError, match="emission"):
        module().validate_state(new)


def test_late_reconstruction_correction_is_lawful_when_emission_order_is_real():
    old = compose(generated_at="2026-10-05T12:00:00Z")
    frozen = copy.deepcopy(old)
    src = subject()
    for r in src["owners"].values():
        r["query"]["known_at"] = "2026-10-03T14:00:00Z"
    new = compose([src], known_at="2026-10-03T14:00:00Z", generated_at="2026-10-05T14:00:00Z", previous=old)
    assert new["correction"]["generated_at"] == old["generated_at"] and old == frozen
    refused = module().read_theme_state(new, src["node_id"], effective_at=QUERY["effective_at"], known_at="2026-10-03T14:00:00Z")
    assert refused["status"] == "UNAVAILABLE" and "STATE_NOT_YET_EMITTED" in refused["reason_codes"]
