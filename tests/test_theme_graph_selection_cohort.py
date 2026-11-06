"""Synthetic receipt witnesses; these are not US/CN natural-event acceptance."""
import copy
import json
import importlib.util
import os
from pathlib import Path
import jsonschema
import pytest

from engine.theme_graph.selection_cohort import (
    FLAGS, compose_selection_cohort, content_sha256, validate_selection_cohort,
)

EFFECTIVE = "2026-10-03T08:00:00Z"
KNOWN = "2026-10-03T12:00:00Z"
OLD = "2026-10-02T08:00:00Z"
FUTURE = "2026-10-04T08:00:00Z"
SHA = "a" * 64


def selection(n=3):
    rows = [{"selection_id": f"owner-row-{i}", "original_identity": {"ticker": f"SEC{i}"},
             "original_reasons": {"en": f"Owner reason {i}", "zh": f"原始理由{i}"},
             "source_row": {"ticker": f"SEC{i}", "display_rank": i + 1, "owner_score": 20 - i}}
            for i in range(n)]
    return dict(owner="fixture-selection-owner", source_schema="fixture.owner/v1",
                source_ref="fixture://immutable-generation", source_sha256=SHA,
                generation_id="owner-generation-1", cohort_scope="complete-finalized-fixture",
                effective_at=EFFECTIVE, selected_at="2026-10-03T12:01:00Z", known_at=KNOWN,
                n_selected=n, rows=rows, rows_sha256=content_sha256(rows),
                ordered_identity_sha256=content_sha256([r["original_identity"] for r in rows]),
                ordered_reasons_sha256=content_sha256([r["original_reasons"] for r in rows]))


def receipt(schema="fixture.owner_read/v1"):
    return dict(status="OK", qualification="EXACT_PIT_QUERY", owner_schema=schema,
                receipt_ref="fixture://owner/receipt", receipt_sha256=SHA,
                generation_id="fixture-generation", effective_at=EFFECTIVE, known_at=KNOWN,
                available_at=OLD, valid_until=None)


def member(i, node="ltheme:ths:battery", canonical=None):
    return dict(member_node_id=f"co:fixture:{i}", node_id=node, kind="local_theme",
                source_family="ths", native_id=node.split(":", 2)[2], node_kind="local_theme", canonical_node_ids=canonical,
                canonical_nodes=[{"node_id": x, "kind": "theme", "receipt_ref": "fixture://canonical/" + x, "receipt_sha256": SHA} for x in canonical or []],
                evidence_ref=f"fixture://membership/{i}/{node}", evidence_sha256=SHA,
                effective_from=OLD, effective_until=None, known_from=OLD,
                rights_status="ALLOWED", rights_receipt_ref="fixture://rights/allowed")


# This static synthetic receipt was produced through the frozen actual owner reader.
# Tests below may mutate it as explicit structural counterexamples, never natural evidence.
STATE_FIXTURE = json.loads(r''' {"effective_at":"2026-10-03T08:00:00Z","generation_id":"3baa0fb2fbef91428a7dc561d5c66828","known_at":"2026-10-03T12:00:00Z","reason_codes":[],"schema":"gmi.theme_state_read/v1","state_generated_at":"2026-10-03T12:00:00Z","state_sha256":"3baa0fb2fbef91428a7dc561d5c668286bcbf643eb1d8ff26fd07c7017360aac","status":"DESCRIPTIVE","subject":{"aggregation":{"reason_codes":[],"receipt":null,"status":"NOT_APPLICABLE"},"availability":"AVAILABLE","eligibility":{"policy_revision":null,"reason_codes":["D2E_UNSEALED"],"status":"NOT_QUALIFIED"},"kind":"local_theme","mapping":{"state":"UNMAPPED","theme_node_ids":[]},"name_en":"Power grid","name_zh":"电网","native_id":"battery","node_id":"ltheme:ths:battery","observations":{"breadth":{"conflicts":[],"coverage":{"basis":"CURRENT_MEMBERSHIP_NOT_PIT","declared":2,"observed":1},"freshness":"FRESH","freshness_policy":{"max_age_hours":30,"owner_policy_revision":"state-default-30h"},"null_reason":null,"owner":"specialist","presence":"POSITIVE","schema":"specialist.native/v1","source_receipts":[{"availability":"AVAILABLE","available_at":"2026-10-03T08:00:00Z","effective_at":"2026-10-03T08:00:00Z","generation_id":"specialist-20261003","graph_generation_id":"graph-20261003","known_at":"2026-10-03T09:00:00Z","owner":"specialist","payload":7,"query":{"effective_at":"2026-10-03T08:00:00Z","known_at":"2026-10-03T12:00:00Z"},"recorded_at":"2026-10-03T09:00:00Z","schema":"fixture.specialist/v1","sha256":"7902699be42c8a8e46fbbb4501726517e86b22c56a189f7625a6da49081b2451","subject_id":"ltheme:ths:battery"}],"units":"percentage_points","value":7,"window":"5_closed_sessions"}},"owner_receipts":{"eligibility":{"availability":"AVAILABLE","available_at":"2026-10-03T08:00:00Z","effective_at":"2026-10-03","generation_id":"eligibility-20261003","graph_generation_id":"graph-20261003","known_at":"2026-10-03T09:00:00Z","owner":"eligibility","payload":{"policy_revision":null,"reason_codes":["D2E_UNSEALED"],"status":"NOT_QUALIFIED"},"query":{"effective_at":"2026-10-03T08:00:00Z","known_at":"2026-10-03T12:00:00Z"},"recorded_at":"2026-10-03T09:00:00Z","schema":"fixture.eligibility/v1","sha256":"558416202a533f168f06ce9274b45bae69669df9aaddb7757d27a5a898f88446","subject_id":"ltheme:ths:battery"},"identity":{"availability":"AVAILABLE","available_at":"2026-10-03T08:00:00Z","effective_at":"2026-10-03","generation_id":"identity-20261003","graph_generation_id":"graph-20261003","known_at":"2026-10-03T09:00:00Z","owner":"identity","payload":{"issuer_ids":["issuer:HUBB"],"status":"RESOLVED"},"query":{"effective_at":"2026-10-03T08:00:00Z","known_at":"2026-10-03T12:00:00Z"},"recorded_at":"2026-10-03T09:00:00Z","schema":"fixture.identity/v1","sha256":"0983daaee5af12f0f45c316ab53a13bdbe80e1263e10ac2409a0f040b5954f1e","subject_id":"ltheme:ths:battery"},"membership":{"availability":"AVAILABLE","available_at":"2026-10-03T08:00:00Z","effective_at":"2026-10-03","generation_id":"membership-20261003","graph_generation_id":"graph-20261003","known_at":"2026-10-03T09:00:00Z","owner":"membership","payload":{"basis":"qualified_owner_query","declared_count":1,"eligible_count":1,"era":"OBSERVED","members":[{"issuer_id":"issuer:HUBB","security_id":"security:HUBB","ticker":"HUBB"}],"observed_count":1,"status":"AVAILABLE"},"query":{"effective_at":"2026-10-03T08:00:00Z","known_at":"2026-10-03T12:00:00Z"},"recorded_at":"2026-10-03T09:00:00Z","schema":"fixture.membership/v1","sha256":"b5d396c55f0c6a1a2ac1093d686927ab4817941e2eb1bf28ce9b5cda6d7831ce","subject_id":"ltheme:ths:battery"},"ontology":{"availability":"AVAILABLE","available_at":"2026-10-03T08:00:00Z","effective_at":"2026-10-03","generation_id":"ontology-20261003","graph_generation_id":"graph-20261003","known_at":"2026-10-03T09:00:00Z","owner":"ontology","payload":{"canonical_mapping":{"state":"UNMAPPED","theme_node_ids":[]}},"query":{"effective_at":"2026-10-03T08:00:00Z","known_at":"2026-10-03T12:00:00Z"},"recorded_at":"2026-10-03T09:00:00Z","schema":"fixture.ontology/v1","sha256":"1476d9e978b2dc1948dfe36cf2b32b79e0d4621486a025139f51fbfd1e39a29d","subject_id":"ltheme:ths:battery"},"rights":{"availability":"AVAILABLE","available_at":"2026-10-03T08:00:00Z","effective_at":"2026-10-03","generation_id":"rights-20261003","graph_generation_id":"graph-20261003","known_at":"2026-10-03T09:00:00Z","owner":"rights","payload":{"allowed":true,"purpose":"research_internal","revision":"rights-r1"},"query":{"effective_at":"2026-10-03T08:00:00Z","known_at":"2026-10-03T12:00:00Z"},"recorded_at":"2026-10-03T09:00:00Z","schema":"fixture.rights/v1","sha256":"577b80c186e3c3d5ad5e5792a0fde9b4b9269a6cc175247c5f6c69b4294bcc81","subject_id":"ltheme:ths:battery"}},"reason_codes":[],"source_family":"ths"},"subject_id":"ltheme:ths:battery"}''')


def state(node, status="DESCRIPTIVE"):
    result = copy.deepcopy(STATE_FIXTURE)
    result.update(subject_id=node, status=status)
    subject = result["subject"]
    subject.update(node_id=node, native_id=node.split(":", 2)[2])
    for owner in subject["owner_receipts"].values():
        if owner is not None: owner["subject_id"] = node
    for observation in subject["observations"].values():
        for owner in observation["source_receipts"]: owner["subject_id"] = node
    if status == "QUALIFIED":
        subject["eligibility"].update(status="QUALIFIED", policy_revision="fixture-d2e-r1", reason_codes=[])
    return result


def inputs(n=3):
    ids, memberships = {}, {}
    source = selection(n)
    for i in range(n):
        sid = f"owner-row-{i}"
        binding = dict(selection_id=sid, original_identity_sha256=content_sha256(source["rows"][i]["original_identity"]), selection_sha256=content_sha256(source))
        ids[sid] = dict(**receipt("fixture.pit_identity/v1"), **binding, security_id=f"SEC:fixture:{i}",
                        graph_node_ids=[f"co:fixture:{i}"], historical_identity_claim=True)
        memberships[sid] = dict(**receipt("fixture.pit_membership/v1"), **binding,
                                identity_receipt_ref=ids[sid]["receipt_ref"], identity_receipt_sha256=ids[sid]["receipt_sha256"], security_id=f"SEC:fixture:{i}",
                                complete=True, memberships=[member(i)])
    return dict(identity_reads=ids, membership_reads=memberships,
                state_reads={"ltheme:ths:battery": state("ltheme:ths:battery")})


def test_positive_preserves_whole_source_order_reasons_and_all_authority():
    source, kw = selection(), inputs()
    before = copy.deepcopy((source, kw))
    result = compose_selection_cohort(source, **kw)
    assert result["source_selection"] == source
    assert [r["source"] for r in result["selected"]] == source["rows"]
    assert [r["security_id"] for r in result["selected"]] == [f"SEC:fixture:{i}" for i in range(3)]
    assert (source, kw) == before
    assert result["coverage"]["n_selected"] == 3
    assert result["concepts"][0]["n_selected_in_concept"] == 3
    assert result["concepts"][0]["fraction_of_selected"] == 1
    assert result["concepts"][0]["state"]["status"] == "DESCRIPTIVE"
    assert all(result[f] is False for f in FLAGS)
    assert result["availability"] == {"status": "OK", "overlap": "OBSERVED_SHARED_CONCEPTS"}
    assert result["consequence_link"]["status"] == "UNREGISTERED"
    validate_selection_cohort(result)


def test_per_concept_dedup_overlapping_fractions_and_unmapped_local():
    kw = inputs()
    kw["membership_reads"]["owner-row-0"]["memberships"] += [member(0), member(0, "ltheme:ths:recycling")]
    kw["membership_reads"]["owner-row-1"]["memberships"] += [member(1, "ltheme:ths:recycling")]
    kw["state_reads"]["ltheme:ths:recycling"] = state("ltheme:ths:recycling")
    result = compose_selection_cohort(selection(), **kw)
    assert [c["n_selected_in_concept"] for c in result["concepts"]] == [3, 2]
    assert sum(c["fraction_of_selected"] for c in result["concepts"]) > 1
    assert result["coverage"]["multi_theme"] == ["owner-row-0", "owner-row-1"]
    assert result["coverage"]["unmapped_local"] == [f"owner-row-{i}" for i in range(3)]
    assert len(result["concepts"][0]["evidence"]) == 3


def test_empty_selection_and_confirmed_empty_memberships_are_distinct():
    empty = compose_selection_cohort(selection(0), **inputs(0))
    assert empty["availability"]["status"] == "EMPTY_SELECTION"
    assert empty["concepts"] == [] and empty["coverage"]["n_selected"] == 0
    kw = inputs()
    for r in kw["membership_reads"].values():
        r["memberships"] = []
    result = compose_selection_cohort(selection(), **kw)
    assert result["availability"] == {"status": "OK", "overlap": "NO_MEANINGFUL_OVERLAP"}
    assert len(result["coverage"]["no_recorded_membership"]) == 3


def test_distinct_concepts_have_honest_no_overlap():
    kw = inputs()
    for i, r in enumerate(kw["membership_reads"].values()):
        node = f"ltheme:ths:fixture_{i}"
        r["memberships"] = [member(i, node)]
        kw["state_reads"][node] = state(node)
    result = compose_selection_cohort(selection(), **kw)
    assert result["availability"]["overlap"] == "NO_MEANINGFUL_OVERLAP"
    assert result["coverage"]["n_shared_concepts"] == 0


@pytest.mark.parametrize("field,value", [("effective_at", "2026-09-30"), ("known_at", "2026-09-30T08:01:00"),
                                          ("generation_id", ""), ("source_sha256", "bad"),
                                          ("n_selected", 1), ("known_at", FUTURE), ("effective_at", FUTURE)])
def test_unqualified_source_refused(field, value):
    source = selection()
    source[field] = value
    with pytest.raises(ValueError):
        compose_selection_cohort(source, **inputs())


@pytest.mark.parametrize("which", ["rows_sha256", "ordered_identity_sha256", "ordered_reasons_sha256"])
def test_owner_declared_digests_are_checked(which):
    source = selection()
    source[which] = "b" * 64
    with pytest.raises(ValueError, match="mismatch"):
        compose_selection_cohort(source, **inputs())


@pytest.mark.parametrize("field,value,reason", [
    ("historical_identity_claim", False, "IDENTITY_NOT_QUALIFIED_AT_SELECTION"),
    ("qualification", "LATEST_PUBLISHED", "UNQUALIFIED_OWNER_QUERY"),
    ("known_at", FUTURE, "QUERY_CUTOFF_MISMATCH"),
    ("available_at", FUTURE, "LATE_KNOWN_RECEIPT"),
    ("valid_until", OLD, "STALE_RECEIPT"),
    ("effective_at", "2026-09-30", "IMPRECISE_OR_MISSING_OWNER_PROVENANCE"),
])
def test_identity_failures_keep_source_row_and_denominator(field, value, reason):
    kw = inputs()
    kw["identity_reads"]["owner-row-0"][field] = value
    result = compose_selection_cohort(selection(), **kw)
    assert result["coverage"]["missing_identity"] == ["owner-row-0"]
    assert result["selected"][0]["reason_codes"] == [reason]
    assert len(result["selected"]) == result["coverage"]["n_selected"] == 3
    assert result["concepts"][0]["fraction_of_selected"] == pytest.approx(2 / 3)
    assert result["availability"]["status"] == "PARTIAL"


@pytest.mark.parametrize("field,value,bucket,reason", [
    ("effective_from", FUTURE, "missing_membership", "FUTURE_MEMBERSHIP"),
    ("effective_until", EFFECTIVE, "missing_membership", "STALE_MEMBERSHIP"),
    ("known_from", FUTURE, "missing_membership", "LATE_KNOWN_MEMBERSHIP"),
    ("known_from", "2026-09-30", "missing_membership", "IMPRECISE_OR_MISSING_MEMBERSHIP_PROVENANCE"),
    ("member_node_id", "co:other", "missing_membership", "MEMBERSHIP_IDENTITY_MISMATCH"),
    ("rights_status", "UNKNOWN", "missing_rights", "RIGHTS_UNAVAILABLE"),
])
def test_membership_and_rights_cutoff_discriminants(field, value, bucket, reason):
    kw = inputs()
    kw["membership_reads"]["owner-row-0"]["memberships"][0][field] = value
    result = compose_selection_cohort(selection(), **kw)
    assert result["coverage"][bucket] == ["owner-row-0"]
    assert reason in result["selected"][0]["reason_codes"]
    assert result["concepts"][0]["n_selected_in_concept"] == 2


def test_missing_receipts_are_not_empty_membership():
    result = compose_selection_cohort(selection(), identity_reads={}, membership_reads={}, state_reads={})
    assert result["availability"] == {"status": "PARTIAL", "overlap": "UNDETERMINED"}
    assert len(result["coverage"]["missing_identity"]) == 3
    kw = inputs()
    kw["membership_reads"].clear()
    result = compose_selection_cohort(selection(), **kw)
    assert len(result["coverage"]["missing_membership"]) == 3
    assert result["coverage"]["no_recorded_membership"] == []


@pytest.mark.parametrize("change", ["missing", "future", "subject", "unavailable", "extra"])
def test_state_owner_receipt_cutoff_and_closed_interface(change):
    kw = inputs()
    r = kw["state_reads"]["ltheme:ths:battery"]
    if change == "missing": kw["state_reads"].clear()
    elif change == "future": r["known_at"] = FUTURE
    elif change == "subject": r["subject"]["node_id"] = "ltheme:ths:other"
    elif change == "unavailable": r.update(status="UNAVAILABLE", subject=None)
    else: r["score"] = 1
    result = compose_selection_cohort(selection(), **kw)
    assert len(result["coverage"]["missing_state"]) == 3
    assert result["concepts"][0]["state"] is None
    assert result["concepts"][0]["n_selected_in_concept"] == 3


def test_content_addressed_correction_retains_immutable_selection_and_prior():
    source, kw = selection(), inputs()
    first = compose_selection_cohort(source, **kw)
    snapshot = copy.deepcopy(first)
    kw["state_reads"]["ltheme:ths:battery"]["subject"]["observations"]["breadth"]["value"] = 8
    kw["state_reads"]["ltheme:ths:battery"]["state_sha256"] = "c" * 64
    kw["state_reads"]["ltheme:ths:battery"]["generation_id"] = "c" * 32
    second = compose_selection_cohort(source, **kw, previous_explanation=first)
    assert first == snapshot
    assert second["version"] == {"number": 2, "corrects": first["explanation_id"], "basis": "AS_KNOWN_AT_SELECTION"}
    assert second["explanation_id"] != first["explanation_id"]
    assert second["selection_sha256"] == first["selection_sha256"]
    assert second["selected"] == first["selected"]
    assert compose_selection_cohort(source, **kw, previous_explanation=first) == second
    changed = selection()
    changed["generation_id"] = "other-generation"
    with pytest.raises(ValueError, match="same immutable"):
        compose_selection_cohort(changed, **kw, previous_explanation=first)


def test_later_known_correction_cannot_enter_original_cutoff():
    kw = inputs()
    first = compose_selection_cohort(selection(), **kw)
    kw["membership_reads"]["owner-row-0"]["memberships"][0]["known_from"] = FUTURE
    corrected = compose_selection_cohort(selection(), **kw, previous_explanation=first)
    assert corrected["coverage"]["missing_membership"] == ["owner-row-0"]
    assert corrected["concepts"][0]["n_selected_in_concept"] == 2


def test_neutral_owner_link_never_registers_or_assigns_direction():
    result = compose_selection_cohort(selection(), **inputs(), consequence_reference={"owner": "Evaluation OS/QLedger", "episode_ref": "fixture://ql/episode"})
    assert result["consequence_link"] == {"owner": "Evaluation OS/QLedger", "status": "OWNER_REFERENCE_SUPPLIED", "episode_ref": "fixture://ql/episode"}
    with pytest.raises(ValueError):
        compose_selection_cohort(selection(), **inputs(), consequence_reference={"owner": "new-ledger", "episode_ref": "x"})


def test_authority_fields_and_new_ranking_fields_fail_contract():
    result = compose_selection_cohort(selection(), **inputs())
    for flag in FLAGS:
        mutated = copy.deepcopy(result)
        mutated[flag] = True
        with pytest.raises(jsonschema.ValidationError): validate_selection_cohort(mutated)
    for key in ("score", "rank", "priority"):
        mutated = copy.deepcopy(result)
        mutated[key] = 1
        with pytest.raises(jsonschema.ValidationError): validate_selection_cohort(mutated)
    mutated = copy.deepcopy(result)
    mutated["selected"].reverse()
    with pytest.raises(ValueError, match="order or reasons"):
        validate_selection_cohort(mutated)


def test_duplicate_source_or_canonical_identity_and_conflicting_concept_refused():
    source = selection()
    source["rows"][1]["selection_id"] = source["rows"][0]["selection_id"]
    with pytest.raises(ValueError, match="duplicate"):
        compose_selection_cohort(source, **inputs())
    kw = inputs()
    kw["identity_reads"]["owner-row-1"]["security_id"] = "SEC:fixture:0"
    with pytest.raises(ValueError, match="canonical security"):
        compose_selection_cohort(selection(), **kw)
    kw = inputs()
    m = kw["membership_reads"]["owner-row-1"]["memberships"][0]
    m["canonical_node_ids"] = ["theme:battery"]
    m["canonical_nodes"] = [{"node_id": "theme:battery", "kind": "theme", "receipt_ref": "fixture://canonical", "receipt_sha256": SHA}]
    with pytest.raises(ValueError, match="conflicting"):
        compose_selection_cohort(selection(), **kw)


@pytest.mark.parametrize("change", ["denominator", "fraction", "selected_set", "state_cutoff", "link", "version"])
def test_rehashed_payload_cannot_change_cohort_invariants(change):
    result = compose_selection_cohort(selection(), **inputs())
    if change == "denominator": result["coverage"]["n_selected"] = 2
    elif change == "fraction": result["concepts"][0]["fraction_of_selected"] = 0.5
    elif change == "selected_set": result["concepts"][0]["selected_ids"].reverse()
    elif change == "state_cutoff": result["concepts"][0]["state"]["known_at"] = FUTURE
    elif change == "link": result["consequence_link"]["episode_ref"] = "invented"
    else: result["version"]["number"] = 2
    result["explanation_id"] = "sha256:" + content_sha256({k: v for k, v in result.items() if k != "explanation_id"})
    with pytest.raises(ValueError):
        validate_selection_cohort(result)


def rehash(result):
    result["explanation_id"] = "sha256:" + content_sha256({k: v for k, v in result.items() if k != "explanation_id"})
    return result


@pytest.mark.parametrize("case", ["identity", "membership", "state", "multi_theme", "unmapped", "empty", "state_reason", "evidence"])
def test_review_r1_coverage_and_availability_cannot_be_relabelled(case):
    kw = inputs()
    if case == "identity": kw["identity_reads"].clear()
    if case == "membership": kw["membership_reads"].clear()
    if case == "state": kw["state_reads"].clear()
    if case == "multi_theme":
        for i, r in enumerate(kw["membership_reads"].values()): r["memberships"].append(member(i, "ltheme:ths:recycling"))
        kw["state_reads"]["ltheme:ths:recycling"] = state("ltheme:ths:recycling")
    if case == "empty":
        for r in kw["membership_reads"].values(): r["memberships"] = []
    result = compose_selection_cohort(selection(), **kw)
    if case in ("identity", "membership", "state"):
        result["coverage"]["missing_" + case] = []
        result["availability"] = {"status": "OK", "overlap": "NO_MEANINGFUL_OVERLAP"}
    elif case == "multi_theme": result["coverage"]["multi_theme"] = []
    elif case == "unmapped": result["coverage"]["unmapped_local"] = []
    elif case == "empty": result["coverage"]["no_recorded_membership"] = []
    elif case == "state_reason": result["concepts"][0]["state_reason"] = "MISSING_STATE"
    else: result["concepts"][0]["evidence"] = []
    with pytest.raises((ValueError, jsonschema.ValidationError)):
        validate_selection_cohort(rehash(result))


def test_review_r2_impossible_qualified_state_is_missing_state():
    kw = inputs()
    kw["state_reads"]["ltheme:ths:battery"]["status"] = "QUALIFIED"
    result = compose_selection_cohort(selection(), **kw)
    assert result["coverage"]["missing_state"] == [f"owner-row-{i}" for i in range(3)]
    assert result["concepts"][0]["state"] is None


@pytest.mark.parametrize("refs", [["co:cn:wrong-kind", "ltheme:ths:battery"], ["theme:battery", "theme:battery"]])
def test_review_r3_wrong_or_duplicate_canonical_species_is_not_a_mapping(refs):
    kw = inputs()
    for r in kw["membership_reads"].values(): r["memberships"][0]["canonical_node_ids"] = refs
    result = compose_selection_cohort(selection(), **kw)
    assert result["concepts"] == []
    assert result["coverage"]["missing_membership"] == [f"owner-row-{i}" for i in range(3)]


@pytest.mark.parametrize("partial", [False, True])
def test_review_r4_rehashed_duplicate_security_with_empty_or_partial_membership(partial):
    kw = inputs()
    for r in kw["membership_reads"].values(): r["memberships"] = []
    if partial: kw["membership_reads"].pop("owner-row-2")
    result = compose_selection_cohort(selection(), **kw)
    result["selected"][1]["security_id"] = result["selected"][0]["security_id"]
    with pytest.raises(ValueError): validate_selection_cohort(rehash(result))


@pytest.mark.parametrize("adapter,field,value", [
    ("identity_reads", "selection_id", "owner-row-1"),
    ("identity_reads", "original_identity_sha256", "f" * 64),
    ("identity_reads", "unknown_authority", True),
    ("membership_reads", "selection_id", "owner-row-1"),
    ("membership_reads", "original_identity_sha256", "f" * 64),
    ("membership_reads", "unknown_authority", True),
])
def test_review_r5_conflicting_or_open_adapter_is_a_typed_gap(adapter, field, value):
    kw = inputs()
    kw[adapter]["owner-row-0"][field] = value
    result = compose_selection_cohort(selection(), **kw)
    key = "missing_identity" if adapter == "identity_reads" else "missing_membership"
    assert result["coverage"][key] == ["owner-row-0"]


def test_shared_issuer_graph_node_preserves_distinct_selected_securities():
    kw = inputs()
    for sid in kw["identity_reads"]:
        kw["identity_reads"][sid]["graph_node_ids"] = ["co:fixture:shared_issuer"]
        kw["membership_reads"][sid]["memberships"][0]["member_node_id"] = "co:fixture:shared_issuer"
    result = compose_selection_cohort(selection(), **kw)
    assert result["coverage"]["n_identity_qualified"] == 3
    assert result["concepts"][0]["n_selected_in_concept"] == 3
    assert len(set(result["concepts"][0]["security_ids"])) == 3
    assert len({e["member_node_id"] for e in result["concepts"][0]["evidence"]}) == 1


@pytest.mark.parametrize("change", ["future_emission", "missing_emission", "date_emission", "generation", "availability", "subject_extra", "eligibility"])
def test_full_owner_state_contract_emission_generation_and_subject_gate(change):
    kw = inputs()
    r = kw["state_reads"]["ltheme:ths:battery"]
    if change == "future_emission": r["state_generated_at"] = FUTURE
    elif change == "missing_emission": del r["state_generated_at"]
    elif change == "date_emission": r["state_generated_at"] = "2026-10-03"
    elif change == "generation": r["generation_id"] = "b" * 32
    elif change == "availability": r["subject"]["availability"] = "UNAVAILABLE"
    elif change == "subject_extra": r["subject"]["score"] = 1
    else: r["subject"]["eligibility"]["status"] = "QUALIFIED"
    result = compose_selection_cohort(selection(), **kw)
    assert result["coverage"]["missing_state"] == [f"owner-row-{i}" for i in range(3)]


def test_canonical_destinations_require_existing_theme_species_receipts():
    kw = inputs()
    for r in kw["membership_reads"].values():
        m = r["memberships"][0]
        m["canonical_node_ids"] = ["theme:battery", "theme:electrification"]
        m["canonical_nodes"] = [{"node_id": x, "kind": "theme", "receipt_ref": "fixture://existing/" + x, "receipt_sha256": SHA} for x in m["canonical_node_ids"]]
    result = compose_selection_cohort(selection(), **kw)
    assert result["coverage"]["unmapped_local"] == []
    assert result["concepts"][0]["canonical_node_ids"] == ["theme:battery", "theme:electrification"]
    kw["membership_reads"]["owner-row-0"]["memberships"][0]["canonical_nodes"] = []
    result = compose_selection_cohort(selection(), **kw)
    assert result["coverage"]["missing_membership"] == ["owner-row-0"]


@pytest.mark.parametrize("change", ["identity_receipt", "membership_receipt", "missing_rights", "duplicates_only", "canonical_refs", "evidence_row_binding", "missing_identity_reason"])
def test_review_relational_receipt_and_outcome_corruption(change):
    result = compose_selection_cohort(selection(), **inputs())
    if change == "identity_receipt": result["selected"][0]["identity_receipt"] = None
    elif change == "membership_receipt": result["selected"][0]["membership_receipt"] = None
    elif change == "missing_rights": result["coverage"]["missing_rights"] = ["owner-row-0"]
    elif change == "duplicates_only":
        kw = inputs()
        for r in kw["membership_reads"].values(): r["memberships"] = []
        result = compose_selection_cohort(selection(), **kw)
        result["selected"][0]["membership_receipt"]["observed_count"] = 1
        result["selected"][0]["membership_summary"]["duplicate_evidence_count"] = 1
        result["coverage"]["no_recorded_membership"] = ["owner-row-1", "owner-row-2"]
    elif change == "missing_identity_reason":
        result = compose_selection_cohort(selection(), identity_reads={}, membership_reads={}, state_reads={})
        result["selected"][0]["reason_codes"] = ["OK"]
    elif change == "canonical_refs":
        result["concepts"][0]["canonical_node_ids"] = ["co:wrong", "ltheme:ths:battery"]
    else: result["concepts"][0]["evidence"][0]["security_id"] = "SEC:wrong"
    with pytest.raises((ValueError, jsonschema.ValidationError)):
        validate_selection_cohort(rehash(result))


@pytest.mark.parametrize("emitted_later", [False, True])
def test_actual_owner_reader_integration_is_separate_synthetic_proof(emitted_later):
    root = Path(os.environ.get("GMI_STATE_OWNER_WORKSPACE", Path(__file__).resolve().parents[1]))
    fixture_path = root / "tests/test_theme_graph_state.py"
    if not fixture_path.exists():
        pytest.skip("actual successor owner source not mounted; synthetic adapter tests are not owner integration")
    spec = importlib.util.spec_from_file_location("w3c_actual_owner_fixture", fixture_path)
    fx = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fx)
    fx.QUERY = {"effective_at": EFFECTIVE, "known_at": KNOWN}
    node = "ltheme:ths:battery"
    src = fx.subject(node, qualified=True)
    src.update(source_family="ths", native_id="battery")
    artifact = fx.compose([src], generated_at=FUTURE if emitted_later else KNOWN)
    reader_result = fx.module().read_theme_state(artifact, node, **fx.QUERY, expected_generation_id=artifact["generation_id"])
    owner_schema = json.loads((root / "contracts/theme_graph/theme_state.v1.schema.json").read_text())
    cohort_schema = json.loads((Path(__file__).resolve().parents[1] / "contracts/theme_graph/selection_cohort_read.v1.schema.json").read_text())
    assert cohort_schema["$defs"]["owner_state_read_contract"]["$defs"] == owner_schema["$defs"]
    kw = inputs()
    kw["state_reads"][node] = reader_result
    result = compose_selection_cohort(selection(), **kw)
    if emitted_later:
        assert reader_result["status"] == "UNAVAILABLE"
        assert "STATE_NOT_YET_EMITTED" in reader_result["reason_codes"]
        assert result["coverage"]["missing_state"] == [f"owner-row-{i}" for i in range(3)]
    else:
        assert reader_result["status"] == "QUALIFIED"
        assert result["concepts"][0]["state"] == reader_result
        assert result["coverage"]["missing_state"] == []


@pytest.mark.parametrize("field,value", [("native_id", "wrong"), ("source_family", "finviz"), ("native_id", "battery ")])
def test_state_subject_identity_contradiction_is_typed_missing_state(field, value):
    kw = inputs()
    kw["state_reads"]["ltheme:ths:battery"]["subject"][field] = value
    result = compose_selection_cohort(selection(), **kw)
    assert result["availability"]["status"] == "PARTIAL"
    assert result["coverage"]["missing_state"] == [f"owner-row-{i}" for i in range(3)]
    assert result["concepts"][0]["state"] is None
    assert result["concepts"][0]["state_reason"] == "STATE_SUBJECT_IDENTITY_MISMATCH"
    assert [r["source"] for r in result["selected"]] == selection()["rows"]


@pytest.mark.parametrize("field,value", [("native_id", "wrong"), ("source_family", "finviz"), ("native_id", "battery ")])
def test_wire_schema_cannot_launder_rehashed_state_identity_contradiction(field, value):
    result = compose_selection_cohort(selection(), **inputs())
    result["concepts"][0]["state"]["subject"][field] = value
    schema = json.loads((Path(__file__).resolve().parents[1] / "contracts/theme_graph/selection_cohort_read.v1.schema.json").read_text())
    # JSON Schema cannot concatenate independent strings; semantic validation is required.
    jsonschema.Draft202012Validator(schema).validate(rehash(result))
    with pytest.raises(ValueError):
        validate_selection_cohort(result)
