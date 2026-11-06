"""Versioned history contract for native activity memberships (recovery 2026-10-16 §9 step 3).

The fold under test is ``engine.theme_graph.materialize.apply_activity_membership_events``:
a pure, unwired reader of APPEND / CORRECT / REMOVE events. Its lineage is the real C01
owner fact (Micron's planned integration of 24GB 8H HBM3E into the NVIDIA H200 platform),
read from the committed owner spec and qualified by the existing issuer-disclosure owner.

C01 grants no graph-membership use, so the real event can never become belief. Tests that
need a current belief flip ``graph_membership_use`` to GRANTED and say so: they prove the
mechanism, not a grant.
"""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import random
from pathlib import Path

import jsonschema
import pytest

from engine.company_intelligence import issuer_disclosure_owner as owner
from engine.theme_graph import materialize
from engine.theme_graph.materialize import (
    ACTIVITY_HISTORY_EVENT_SCHEMA,
    ACTIVITY_HISTORY_STATE_SCHEMA,
    ActivityHistoryRefusal,
    activity_history_event_digest,
    activity_membership_id,
    apply_activity_membership_events,
    validate_activity_history_event,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/theme_graph/activity_membership_history.v1.schema.json"
SPEC = json.loads((ROOT / owner.SPEC_PATH).read_bytes())
FACT = SPEC["fact"]
EDITION = SPEC["edition"]
CODE_VERSION = "0" * 40
MU_NODE = "co:us:MU"
TARGET = "theme:hbm_packaging"
SPECIES = "planned_product_integration"

T1 = FACT["known_at"]  # 2026-10-11T17:09:10.298093+00:00, read from the owner spec
T2 = "2026-10-14T09:00:00+00:00"
T3 = "2026-10-17T09:00:00+00:00"
CUT_BETWEEN_T1_T2 = "2026-10-12T00:00:00Z"
CUT_BETWEEN_T2_T3 = "2026-10-15T00:00:00Z"
AFTER_ALL = "2026-10-19T00:00:00Z"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False)


def _owner_bindings() -> dict:
    qualified = owner.qualify_records(
        CODE_VERSION, (ROOT / owner.SPEC_PATH).read_bytes(),
        (ROOT / owner.RULING_PATH).read_bytes(), (ROOT / owner.REGISTRY_PATH).read_bytes(),
        SPEC["identities"])
    return dict(qualified.bindings)


OWNER_BINDINGS = _owner_bindings()


def _scope() -> dict:
    return {
        "product": FACT["product"],
        "platform": FACT["platform"],
        "counterparty_issuer_id": FACT["object_id"],
        "segment": {"value": None, "state": "UNDISCLOSED"},
    }


def _lineage(*, fact_revision: int | None = None) -> dict:
    revision = FACT["revision"] if fact_revision is None else fact_revision
    # The A1 admission change (probation.py) owns the real proposal-id derivation; this
    # history contract binds only its shape, so the test derives a stand-in honestly.
    proposal_id = "actprop:" + _sha(_canonical({
        "fact_id": FACT["fact_id"], "fact_revision": revision,
        "source_node_id": MU_NODE, "target_node_id": TARGET}))[:24]
    return {
        "proposal_id": proposal_id,
        "fact_id": FACT["fact_id"],
        "fact_revision": revision,
        "source_sha256": EDITION["source_sha256"],
        "span_text_sha256": FACT["span"]["text_sha256"],
        "owner_bindings": OWNER_BINDINGS,
    }


def _curation(decision: str = "ACCEPT", *, at: str = T1, tag: str = "c01") -> dict:
    return {"curator": "named-curator:gmi-theme-graph", "decision": decision,
            "decided_at": at, "receipt_sha256": _sha("curation-receipt:" + tag)}


def _observation(completeness: str = "COMPLETE_AUTHORITATIVE", *, exhaustive: bool = True,
                 present: bool = False, at: str = T2) -> dict:
    return {"completeness": completeness, "roster_exhaustive": exhaustive,
            "subject_present": present, "observed_at": at,
            "source_sha256": _sha("roster:" + completeness + at)}


def _event(action: str, *, knowledge_at: str, use: str = "GRANTED", curation="default",
           observation=None, supersedes=None, source: str = MU_NODE, target: str = TARGET,
           species: str = SPECIES, role: str = "component_supplier", lineage=None,
           membership_id: str | None = None) -> dict:
    """An honestly digested event; ``membership_id`` overrides only for tamper tests."""
    if curation == "default":
        curation = _curation(at=knowledge_at) if action in {"APPEND", "CORRECT"} else None
    scope = _scope()
    event = {
        "schema": ACTIVITY_HISTORY_EVENT_SCHEMA,
        "action": action,
        "membership_id": membership_id or activity_membership_id(
            source_node_id=source, target_node_id=target, species=species, scope=scope),
        "species": species,
        "endpoints": {"source_node_id": source, "target_node_id": target,
                      "direction": "SOURCE_TO_TARGET"},
        "scope": scope,
        "role": role,
        "lifecycle": "planned",
        "evidence_lineage": lineage or _lineage(),
        "use_qualification": {"graph_membership_use": use},
        "curation": curation,
        "observation": observation,
        "supersedes_event_sha256": supersedes,
        "clocks": {"knowledge_at": knowledge_at,
                   "effective_at": {"value": None, "state": "UNDISCLOSED"},
                   "recorded_at": knowledge_at},
    }
    digest = activity_history_event_digest(event)
    return {"event_id": "actevt:" + digest[:24], "event_sha256": digest, **event}


def _append(**kw) -> dict:
    return _event("APPEND", knowledge_at=T1, **kw)


def test_real_c01_lineage_append_stays_refused_while_graph_membership_use_is_not_granted():
    event = _append(use="NOT_GRANTED")
    lineage = event["evidence_lineage"]
    assert lineage["fact_id"] == FACT["fact_id"]
    assert lineage["fact_revision"] == FACT["revision"] == 1
    assert lineage["source_sha256"] == EDITION["source_sha256"]
    assert lineage["source_sha256"].startswith("a7efabf9")
    assert lineage["span_text_sha256"] == FACT["span"]["text_sha256"]
    assert set(lineage["owner_bindings"]) == {"spec", "purpose", "adoption"}
    assert event["scope"]["counterparty_issuer_id"] == FACT["object_id"] == "ISS:US-XNAS-NVDA"
    assert FACT["subject_id"] == "ISS:US-XNAS-MU" and FACT["lifecycle"] == "planned"

    state = apply_activity_membership_events([event], knowledge_cutoff=AFTER_ALL)

    assert state["schema"] == ACTIVITY_HISTORY_STATE_SCHEMA
    assert state["current"] == [] and state["history"] == [] and state["retained"] == []
    assert [row["reason"] for row in state["refused"]] == ["GRAPH_MEMBERSHIP_USE_NOT_GRANTED"]
    assert state["refused"][0]["event_sha256"] == event["event_sha256"]
    assert state["authority"] == {"may_materialize_edges": False, "may_publish": False,
                                  "may_rank": False}


def test_granted_and_accepted_append_becomes_current_belief():
    # SYNTHETIC mechanism proof: C01 grants no graph-membership use (see the test above).
    event = _append(use="GRANTED")
    state = apply_activity_membership_events([event], knowledge_cutoff=AFTER_ALL)
    assert state["refused"] == [] and state["history"] == []
    (belief,) = state["current"]
    assert belief["membership_id"] == event["membership_id"]
    assert belief["event_sha256"] == event["event_sha256"]
    assert belief["endpoints"] == {"source_node_id": MU_NODE, "target_node_id": TARGET,
                                   "direction": "SOURCE_TO_TARGET"}
    assert belief["species"] == SPECIES and belief["role"] == "component_supplier"
    assert belief["lifecycle"] == "planned"
    assert belief["evidence_lineage"] == event["evidence_lineage"]
    assert belief["curation"]["decision"] == "ACCEPT"
    assert (belief["knowledge_from"], belief["knowledge_to"]) == (T1, None)

    rejected = _append(use="GRANTED", curation=_curation("REJECT"))
    state = apply_activity_membership_events([rejected], knowledge_cutoff=AFTER_ALL)
    assert state["current"] == []
    assert [row["reason"] for row in state["refused"]] == ["APPEND_NOT_ACCEPTED"]


def test_complete_authoritative_empty_observation_removes_and_preserves_history():
    append = _append()
    remove = _event("REMOVE", knowledge_at=T2, observation=_observation())
    state = apply_activity_membership_events([append, remove], knowledge_cutoff=AFTER_ALL)

    assert state["current"] == [] and state["retained"] == [] and state["refused"] == []
    (closed,) = state["history"]
    assert closed["event_sha256"] == append["event_sha256"]
    assert closed["removed_by_event_sha256"] == remove["event_sha256"]
    assert (closed["knowledge_from"], closed["knowledge_to"]) == (T1, T2)
    assert closed["evidence_lineage"] == append["evidence_lineage"]

    # Belief before the removal was known is still readable: nothing was deleted.
    earlier = apply_activity_membership_events([append, remove],
                                               knowledge_cutoff=CUT_BETWEEN_T1_T2)
    assert [b["event_sha256"] for b in earlier["current"]] == [append["event_sha256"]]
    assert earlier["history"] == []

    orphan = apply_activity_membership_events([remove], knowledge_cutoff=AFTER_ALL)
    assert [row["reason"] for row in orphan["refused"]] == ["NO_CURRENT_BELIEF"]


@pytest.mark.parametrize(
    ("completeness", "exhaustive", "present", "reason"),
    [
        ("TIMEOUT", True, False, "REMOVAL_REFUSED_TIMEOUT"),
        ("PARTIAL", True, False, "REMOVAL_REFUSED_PARTIAL"),
        ("CHANGED_SHAPE", True, False, "REMOVAL_REFUSED_CHANGED_SHAPE"),
        ("COMPLETE_AUTHORITATIVE", False, False, "REMOVAL_REFUSED_NON_EXHAUSTIVE_ROSTER"),
        ("COMPLETE_AUTHORITATIVE", True, True, "REMOVAL_CONTRADICTED_SUBJECT_PRESENT"),
    ],
)
def test_timeout_partial_changed_shape_and_non_exhaustive_roster_do_not_remove(
        completeness, exhaustive, present, reason):
    append = _append()
    remove = _event("REMOVE", knowledge_at=T2, observation=_observation(
        completeness, exhaustive=exhaustive, present=present))
    state = apply_activity_membership_events([append, remove], knowledge_cutoff=AFTER_ALL)

    assert [b["event_sha256"] for b in state["current"]] == [append["event_sha256"]]
    assert state["current"][0]["knowledge_to"] is None
    assert state["history"] == [] and state["refused"] == []
    (kept,) = state["retained"]
    assert kept["reason"] == reason
    assert kept["event_sha256"] == remove["event_sha256"]
    assert kept["retained_belief_event_sha256"] == append["event_sha256"]


def test_correction_preserves_prior_belief_and_an_earlier_cutoff_reads_the_original():
    append = _append()
    # SYNTHETIC owner correction: the fact's revision 2 does not exist in C01 today.
    correct = _event("CORRECT", knowledge_at=T2, supersedes=append["event_sha256"],
                     lineage=_lineage(fact_revision=2),
                     curation=_curation(at=T2, tag="c01-r2"))
    state = apply_activity_membership_events([append, correct], knowledge_cutoff=AFTER_ALL)

    (now,) = state["current"]
    assert now["event_sha256"] == correct["event_sha256"]
    assert now["evidence_lineage"]["fact_revision"] == 2
    assert (now["knowledge_from"], now["knowledge_to"]) == (T2, None)
    (prior,) = state["history"]
    assert prior["event_sha256"] == append["event_sha256"]
    assert prior["superseded_by_event_sha256"] == correct["event_sha256"]
    assert (prior["knowledge_from"], prior["knowledge_to"]) == (T1, T2)
    assert prior["evidence_lineage"]["fact_revision"] == 1

    earlier = apply_activity_membership_events([append, correct],
                                               knowledge_cutoff=CUT_BETWEEN_T1_T2)
    (original,) = earlier["current"]
    assert original["event_sha256"] == append["event_sha256"]
    assert original["knowledge_to"] is None and earlier["history"] == []
    assert earlier["excluded_after_cutoff"] == [correct["event_sha256"]]

    stale = _event("CORRECT", knowledge_at=T3, supersedes=append["event_sha256"],
                   lineage=_lineage(fact_revision=3), curation=_curation(at=T3, tag="c01-r3"))
    raced = apply_activity_membership_events([append, correct, stale],
                                             knowledge_cutoff=AFTER_ALL)
    assert [b["event_sha256"] for b in raced["current"]] == [correct["event_sha256"]]
    assert [row["reason"] for row in raced["refused"]] == ["CORRECTION_TARGET_NOT_CURRENT"]


def test_knowledge_cutoff_excludes_later_events_before_selection():
    append = _append()
    late_remove = _event("REMOVE", knowledge_at=T3, observation=_observation(at=T3))
    state = apply_activity_membership_events([append, late_remove],
                                             knowledge_cutoff=CUT_BETWEEN_T2_T3)

    assert [b["event_sha256"] for b in state["current"]] == [append["event_sha256"]]
    assert state["history"] == []
    # Excluded before selection: the late event is never evaluated, so it is neither
    # retained nor refused; it is only listed as excluded.
    assert state["retained"] == [] and state["refused"] == []
    assert state["excluded_after_cutoff"] == [late_remove["event_sha256"]]

    # A cutoff BEFORE the append itself sees no belief at all.
    before = apply_activity_membership_events([append, late_remove],
                                              knowledge_cutoff="2026-10-11T00:00:00Z")
    assert before["current"] == [] and before["refused"] == []
    assert before["excluded_after_cutoff"] == sorted(
        [append["event_sha256"], late_remove["event_sha256"]])

    for bad in ("2026-10-15", "2026-10-15T00:00:00", "not-a-time"):
        with pytest.raises(ActivityHistoryRefusal) as caught:
            apply_activity_membership_events([append], knowledge_cutoff=bad)
        assert caught.value.code == "KNOWLEDGE_CUTOFF_INVALID"


def test_tampered_event_digest_and_membership_id_are_refused():
    event = _append()

    forged_sha = dict(event, event_sha256="0" * 64)
    edited_after_digest = dict(event, role="platform_owner")
    forged_id = dict(event, event_id="actevt:" + "0" * 24)
    for tampered in (forged_sha, edited_after_digest, forged_id):
        with pytest.raises(ActivityHistoryRefusal) as caught:
            validate_activity_history_event(tampered)
        assert caught.value.code == "EVENT_DIGEST_MISMATCH"

    wrong_membership = _append(membership_id="actmem:" + "0" * 24)
    with pytest.raises(ActivityHistoryRefusal) as caught:
        validate_activity_history_event(wrong_membership)
    assert caught.value.code == "MEMBERSHIP_ID_MISMATCH"

    # One invalid event refuses the whole fold; nothing is skipped silently.
    with pytest.raises(ActivityHistoryRefusal) as caught:
        apply_activity_membership_events([event, forged_sha], knowledge_cutoff=AFTER_ALL)
    assert caught.value.code == "EVENT_DIGEST_MISMATCH"


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (MU_NODE, "basket:baskets:x"),
        (MU_NODE, "ltheme:finviz:x"),
        (MU_NODE, "basket:baskets_china_ths:x"),
        ("basket:baskets:x", TARGET),
        (TARGET, MU_NODE),
    ],
)
def test_basket_ltheme_and_vendor_endpoints_are_refused(source, target):
    event = _append(source=source, target=target)
    with pytest.raises(ActivityHistoryRefusal) as caught:
        validate_activity_history_event(event)
    assert caught.value.code == "ENDPOINT_NOT_ADMITTED"
    with pytest.raises(ActivityHistoryRefusal):
        apply_activity_membership_events([event], knowledge_cutoff=AFTER_ALL)


def test_unadmitted_species_and_missing_curation_or_observation_are_refused():
    cases = [
        (_append(species="company_theme_exposure"), "SPECIES_NOT_ADMITTED"),
        (_append(curation=None), "CURATION_REQUIRED"),
        (_event("CORRECT", knowledge_at=T2, supersedes="a" * 64, curation=None),
         "CURATION_REQUIRED"),
        (_event("CORRECT", knowledge_at=T2, supersedes=None), "SUPERSEDES_REQUIRED"),
        (_event("REMOVE", knowledge_at=T2, observation=None), "OBSERVATION_REQUIRED"),
        (_append(supersedes="a" * 64), "EVENT_SCHEMA_INVALID"),
        (_append(curation=dict(_curation(), curator="   ")), "EVENT_SCHEMA_INVALID"),
        (_append(role="index_constituent"), "EVENT_SCHEMA_INVALID"),
    ]
    for event, code in cases:
        with pytest.raises(ActivityHistoryRefusal) as caught:
            validate_activity_history_event(event)
        assert caught.value.code == code, (event["action"], code, caught.value)


def test_fold_is_deterministic_pure_and_wired_only_into_build():
    other_scope_target = "theme:advanced_packaging"
    events = [
        _append(),
        _event("CORRECT", knowledge_at=T2, supersedes=_append()["event_sha256"],
               lineage=_lineage(fact_revision=2), curation=_curation(at=T2, tag="r2")),
        _event("REMOVE", knowledge_at=T3, observation=_observation("TIMEOUT", at=T3)),
        _event("APPEND", knowledge_at=T2, target=other_scope_target),
        _event("REMOVE", knowledge_at=T3, target=other_scope_target,
               observation=_observation(at=T3)),
        _append(use="NOT_GRANTED", target="theme:hbm_supply"),
    ]
    frozen = copy.deepcopy(events)
    expected = _canonical(apply_activity_membership_events(events, knowledge_cutoff=AFTER_ALL))
    rng = random.Random(20261019)
    for _ in range(12):
        shuffled = list(events)
        rng.shuffle(shuffled)
        got = apply_activity_membership_events(shuffled, knowledge_cutoff=AFTER_ALL)
        assert _canonical(got) == expected
    assert events == frozen  # the fold never mutates its input
    # Duplicate delivery of the same event is idempotent.
    doubled = apply_activity_membership_events(events + events, knowledge_cutoff=AFTER_ALL)
    assert _canonical(doubled) == expected

    state = json.loads(expected)
    assert [b["endpoints"]["target_node_id"] for b in state["current"]] == [TARGET]
    assert {row["reason"] for row in state["retained"]} == {"REMOVAL_REFUSED_TIMEOUT"}
    assert {row["reason"] for row in state["refused"]} == {"GRAPH_MEMBERSHIP_USE_NOT_GRANTED"}
    assert len(state["history"]) == 2  # the corrected original and the removed sibling

    # Wired (2026-10-21 fold-seam lane): build() is the fold's ONLY consumer — the
    # relation-event applier and the diffing path stay fold-free.
    assert "apply_activity_membership_events" in inspect.getsource(materialize.build)
    for unwired in (materialize.apply_relation_events, materialize.changed_edges):
        assert "apply_activity_membership_events" not in inspect.getsource(unwired)
        assert "activity_history" not in inspect.getsource(unwired)


def _object_nodes(node, path="#"):
    if isinstance(node, dict):
        if node.get("type") == "object":
            yield path, node
        for key, value in node.items():
            yield from _object_nodes(value, f"{path}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _object_nodes(value, f"{path}/{index}")


def test_history_contract_is_closed():
    schema = json.loads(CONTRACT.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    assert schema["properties"]["schema"]["const"] == ACTIVITY_HISTORY_EVENT_SCHEMA
    assert schema["properties"]["species"]["enum"] == [SPECIES, "principal_business_activity"]
    nodes = list(_object_nodes(schema))
    assert len(nodes) >= 10
    open_nodes = [path for path, node in nodes if node.get("additionalProperties") is not False]
    assert open_nodes == []

    validator = jsonschema.Draft202012Validator(schema)
    event = _append()
    assert list(validator.iter_errors(event)) == []
    for extra in (dict(event, extra=1),
                  dict(event, scope=dict(event["scope"], extra=1)),
                  dict(event, clocks=dict(event["clocks"], extra=1)),
                  dict(event, evidence_lineage=dict(
                      event["evidence_lineage"],
                      owner_bindings=dict(event["evidence_lineage"]["owner_bindings"],
                                          extra="a" * 64)))):
        assert list(validator.iter_errors(extra)) != []
        with pytest.raises(ActivityHistoryRefusal) as caught:
            validate_activity_history_event(extra)
        assert caught.value.code == "EVENT_SCHEMA_INVALID"


# ---------------------------------------------------------------------------------------
# 2026-10-21 additive amendment: the second admitted activity species
# principal_business_activity (role operator, lifecycle current, segment-only scope,
# activity: fact ids). The builders below digest through the module's own digest and
# membership-id functions; no digest is ever hand-typed.
# ---------------------------------------------------------------------------------------

ACTIVITY_SPECIES = "principal_business_activity"


def _principal_lineage() -> dict:
    fact_id = "activity:" + _sha("principal-business-activity:" + MU_NODE)
    proposal_id = "actprop:" + _sha(_canonical({
        "fact_id": fact_id, "fact_revision": FACT["revision"],
        "source_node_id": MU_NODE, "target_node_id": TARGET}))[:24]
    return {
        "proposal_id": proposal_id,
        "fact_id": fact_id,
        "fact_revision": FACT["revision"],
        "source_sha256": EDITION["source_sha256"],
        "span_text_sha256": FACT["span"]["text_sha256"],
        "owner_bindings": OWNER_BINDINGS,
    }


def _principal_segment(value="Networking", *, state="KNOWN") -> dict:
    return {"segment": {"value": value, "state": state}}


def _principal_event(*, knowledge_at: str = T1, use: str = "GRANTED", role: str = "operator",
                     lifecycle: str = "current", scope: dict | None = None,
                     species: str = ACTIVITY_SPECIES, lineage=None) -> dict:
    """An honestly digested principal-activity APPEND; overrides only for mix tests."""
    body_scope = _principal_segment() if scope is None else scope
    event = {
        "schema": ACTIVITY_HISTORY_EVENT_SCHEMA,
        "action": "APPEND",
        "membership_id": activity_membership_id(
            source_node_id=MU_NODE, target_node_id=TARGET, species=species, scope=body_scope),
        "species": species,
        "endpoints": {"source_node_id": MU_NODE, "target_node_id": TARGET,
                      "direction": "SOURCE_TO_TARGET"},
        "scope": body_scope,
        "role": role,
        "lifecycle": lifecycle,
        "evidence_lineage": lineage or _principal_lineage(),
        "use_qualification": {"graph_membership_use": use},
        "curation": _curation(at=knowledge_at, tag=ACTIVITY_SPECIES),
        "observation": None,
        "supersedes_event_sha256": None,
        "clocks": {"knowledge_at": knowledge_at,
                   "effective_at": {"value": None, "state": "UNDISCLOSED"},
                   "recorded_at": knowledge_at},
    }
    digest = activity_history_event_digest(event)
    return {"event_id": "actevt:" + digest[:24], "event_sha256": digest, **event}


def _rehashed(event: dict, **overrides) -> dict:
    """A copy of ``event`` with overrides applied and its digest/id honestly recomputed."""
    body = copy.deepcopy(event)
    body.pop("event_id")
    body.pop("event_sha256")
    body.update(overrides)
    body["membership_id"] = activity_membership_id(
        source_node_id=body["endpoints"]["source_node_id"],
        target_node_id=body["endpoints"]["target_node_id"],
        species=body["species"], scope=body["scope"])
    digest = activity_history_event_digest(body)
    return {"event_id": "actevt:" + digest[:24], "event_sha256": digest, **body}


def test_principal_activity_granted_accepted_append_folds_into_current():
    granted = _principal_event(use="GRANTED")
    validate_activity_history_event(granted)  # the amendment admits the shape
    state = apply_activity_membership_events([granted], knowledge_cutoff=AFTER_ALL)
    assert state["refused"] == [] and state["history"] == [] and state["retained"] == []
    (belief,) = state["current"]
    assert belief["species"] == ACTIVITY_SPECIES
    assert belief["role"] == "operator" and belief["lifecycle"] == "current"
    assert belief["scope"] == {"segment": {"value": "Networking", "state": "KNOWN"}}
    assert belief["evidence_lineage"]["fact_id"].startswith("activity:")
    assert (belief["knowledge_from"], belief["knowledge_to"]) == (T1, None)

    # The same principal activity without a granted graph-membership use is refused.
    state = apply_activity_membership_events([_principal_event(use="NOT_GRANTED")],
                                             knowledge_cutoff=AFTER_ALL)
    assert state["current"] == [] and state["history"] == []
    assert [row["reason"] for row in state["refused"]] == ["GRAPH_MEMBERSHIP_USE_NOT_GRANTED"]


def test_principal_segment_value_is_part_of_membership_identity():
    networking = _principal_event()
    automotive = _principal_event(scope=_principal_segment("Automotive"))
    assert networking["membership_id"] != automotive["membership_id"]
    state = apply_activity_membership_events([networking, automotive],
                                             knowledge_cutoff=AFTER_ALL)
    assert state["refused"] == []
    assert sorted(b["membership_id"] for b in state["current"]) == sorted(
        [networking["membership_id"], automotive["membership_id"]])

    # A second, distinct APPEND event for the SAME membership identity is a duplicate.
    dupe = _principal_event(knowledge_at=T2)
    assert dupe["membership_id"] == networking["membership_id"]
    assert dupe["event_sha256"] != networking["event_sha256"]
    state = apply_activity_membership_events([networking, dupe], knowledge_cutoff=AFTER_ALL)
    assert [row["reason"] for row in state["refused"]] == ["DUPLICATE_APPEND"]
    assert [b["membership_id"] for b in state["current"]] == [networking["membership_id"]]


def test_cross_species_mixing_is_refused_in_history_events():
    mixes = [
        _rehashed(_principal_event(), role="component_supplier"),
        _rehashed(_principal_event(), lifecycle="planned"),
        _rehashed(_principal_event(),
                  scope={"product": FACT["product"],
                         "segment": {"value": "Networking", "state": "KNOWN"}}),
        _rehashed(_append(), role="operator"),
    ]
    for mixed in mixes:
        with pytest.raises(ActivityHistoryRefusal) as caught:
            validate_activity_history_event(mixed)
        assert caught.value.code == "EVENT_SCHEMA_INVALID", mixed["event_id"]
        with pytest.raises(ActivityHistoryRefusal):
            apply_activity_membership_events([mixed], knowledge_cutoff=AFTER_ALL)
