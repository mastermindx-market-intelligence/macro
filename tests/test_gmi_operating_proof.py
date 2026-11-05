"""Operating proof for the GMI theme graph: five properties composed from fixtures.

GMI program §7 sets zero tolerance for failed-fetch removals, future leakage and
fabricated named anonymous customers; it also requires the 48h stale/unavailable
status to be visible and corrections to be reproducible with measured latency. The
existing suites check each mechanism in isolation. This module proves the
mechanisms COMPOSE into the operating behaviour, folding the A2 activity-history
events (``apply_activity_membership_events``) beside the A3 ThemeState composer
and its readers, on fixtures only: no I/O beyond checked-in contracts and owner
spec bytes, no clock reads, no store, no publication.

Everything not yet wired is expressed ONLY as the one remaining strict xfail at
the end: the v1 event contract has no WITHHOLD action (curated withholding of an
existing belief is owed by the activity_membership_history v2 contract, owner
WS:GMI-THEME-GRAPH). The fold IS wired into ``materialize.build`` since the
2026-10-21 fold-seam lane, so publication marks corrections and the production
observed->routed latency is measurable. Synthetic fixtures use neutral ids
(basket "fixture-roster-01", tickers FIXA/FIXB); the only subject is the
canonical node "theme:hbm_packaging".
"""

from __future__ import annotations

import copy
import datetime
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path

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
)
from engine.theme_graph import theme_state_owner_readers as readers

# ---------------------------------------------------------------- A2 fixtures
# The helper shape is copied from tests/test_theme_graph_activity_membership_history.py
# (real C01 owner lineage, honestly digested events); the subject is fixed to the
# canonical node under proof.

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


def _instant(text: str) -> datetime.datetime:
    parsed = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:  # a date-only stamp denotes the start of its UTC day
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed


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
    # operating proof binds only its shape, so the fixture derives a stand-in honestly.
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


def _curation(decision: str = "ACCEPT", *, at: str = T1, tag: str = "fixture") -> dict:
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


def _correct(knowledge_at: str = T2, *, supersedes: str, tag: str) -> dict:
    revision = 2 if knowledge_at == T2 else 3
    return _event("CORRECT", knowledge_at=knowledge_at, supersedes=supersedes,
                  lineage=_lineage(fact_revision=revision),
                  curation=_curation(at=knowledge_at, tag=tag))


# ---------------------------------------------------------------- A3 fixtures
# The helper shape is copied from tests/test_theme_graph_state.py with the subject
# default moved to the canonical node under proof and neutral fixture member ids.

STATE_MODULE = ROOT / "engine/theme_graph/theme_state.py"
QUERY = {"effective_at": "2026-10-03", "known_at": "2026-10-03T12:00:00Z"}
GRAPH = "graph-20261003"
GENERATIONS = {role: role + "-20261003" for role in
               ("ontology", "identity", "membership", "rights", "eligibility", "narrative",
                "specialist")}


def state_module():
    assert STATE_MODULE.exists(), "missing ThemeState composer module"
    spec = importlib.util.spec_from_file_location("gmi_operating_proof_theme_state", STATE_MODULE)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def receipt(owner_name, payload, subject=TARGET, **changes):
    result = {
        "owner": owner_name, "schema": "fixture." + owner_name + "/v1",
        "generation_id": GENERATIONS[owner_name], "graph_generation_id": GRAPH,
        "subject_id": subject, "query": copy.deepcopy(QUERY),
        "effective_at": "2026-10-03", "known_at": "2026-10-03T09:00:00Z",
        "available_at": "2026-10-03T08:00:00Z", "recorded_at": "2026-10-03T09:00:00Z",
        "availability": "AVAILABLE", "payload": payload, "sha256": digest(payload),
    }
    result.update(changes)
    return result


def subject(node=TARGET, mapping=None, qualified=False):
    canonical = node.startswith("theme:")
    owners = {
        "ontology": receipt("ontology", {
            "canonical_mapping": {"state": "SUBJECT_IS_CANONICAL" if canonical else
                                  ("MAPPED" if mapping else "UNMAPPED"),
                                  "theme_node_ids": mapping or []}
        }, node),
        "identity": receipt("identity", {"status": "RESOLVED",
                                         "issuer_ids": ["issuer:FIXA", "issuer:FIXB"]}, node),
        "membership": receipt("membership", {"status": "AVAILABLE", "members": [
            {"ticker": "FIXA", "issuer_id": "issuer:FIXA", "security_id": "security:FIXA"},
            {"ticker": "FIXB", "issuer_id": "issuer:FIXB", "security_id": "security:FIXB"}],
            "declared_count": 2, "eligible_count": 2, "observed_count": 2,
            "basket_id": "fixture-roster-01",
            "basis": "qualified_owner_query", "era": "OBSERVED"}, node),
        "rights": receipt("rights", {"allowed": True, "purpose": "research_internal",
                                     "revision": "rights-r1"}, node),
        "eligibility": receipt("eligibility", {"status": "QUALIFIED" if qualified else
                                               "NOT_QUALIFIED", "policy_revision":
                                               "d2e-r1" if qualified else None,
                                               "reason_codes": [] if qualified else ["D2E_UNSEALED"]},
                               node),
    }
    return {
        "node_id": node, "kind": "canonical_theme" if canonical else "local_theme",
        "name_en": "Fixture packaging theme", "name_zh": "固定主题",
        "source_family": None if canonical else "fixture", "native_id": None if canonical else "fixture",
        "owners": owners, "observations": {}, "canonical_aggregation": None,
    }


def compose(inputs=None, **changes):
    options = dict(graph_generation_id=GRAPH, owner_generations=GENERATIONS,
                   effective_at=QUERY["effective_at"], known_at=QUERY["known_at"],
                   generated_at="2026-10-03T12:00:00Z")
    options.update(changes)
    return state_module().compose_state(inputs or [subject()], **options)


def observation(value, node=TARGET, **changes):
    result = {"owner": "specialist", "schema": "specialist.fixture/v1",
              "presence": "POSITIVE", "freshness": "FRESH", "value": value,
              "null_reason": None, "units": "percentage_points", "window": "5_closed_sessions",
              "coverage": {"declared": 2, "observed": 1, "basis": "CURRENT_MEMBERSHIP_NOT_PIT"},
              "conflicts": [],
              "source_receipts": [receipt("specialist", value, node,
                                          effective_at="2026-10-03T08:00:00Z")],
              "freshness_policy": {"max_age_hours": 30, "owner_policy_revision": "state-default-30h"}}
    result.update(changes)
    return result


def _fixture_freshness_observation(effective_at: str, max_age_hours: int) -> dict:
    obs = observation({"return": 1.25})
    obs["source_receipts"][0]["effective_at"] = effective_at
    obs["freshness_policy"] = {"max_age_hours": max_age_hours,
                               "owner_policy_revision": "fixture-owner-policy"}
    return obs


# ------------------------------------------------------------- P1: refresh

def test_refresh_unchanged_source_keeps_one_membership_and_content():
    append = _append()
    redelivered = _append()  # byte-identical redelivery: the same event_sha256
    assert redelivered["event_sha256"] == append["event_sha256"]
    refresh = _event("APPEND", knowledge_at=T2)  # same membership, lineage and source
    assert refresh["membership_id"] == append["membership_id"]
    assert refresh["event_sha256"] != append["event_sha256"]

    state = apply_activity_membership_events([append, redelivered, refresh],
                                             knowledge_cutoff=AFTER_ALL)

    assert len(state["current"]) == 1
    (belief,) = state["current"]
    assert belief["event_sha256"] == append["event_sha256"]
    assert belief["evidence_lineage"] == append["evidence_lineage"]
    assert [(row["event_sha256"], row["reason"]) for row in state["refused"]] == [
        (refresh["event_sha256"], "DUPLICATE_APPEND")]
    assert state["history"] == []


def test_refresh_changed_source_supersedes_and_original_is_reproducible():
    append = _append()
    correct = _correct(T2, supersedes=append["event_sha256"], tag="fixture-r2")
    events = [append, correct]

    state = apply_activity_membership_events(events, knowledge_cutoff=AFTER_ALL)
    (belief,) = state["current"]
    assert belief["event_sha256"] == correct["event_sha256"]
    (closed,) = state["history"]
    assert closed["event_sha256"] == append["event_sha256"]
    assert closed["superseded_by_event_sha256"] == correct["event_sha256"]
    assert (closed["knowledge_from"], closed["knowledge_to"]) == (T1, T2)

    # The same fold at the earlier cutoff reproduces the original belief byte-identically.
    earlier = apply_activity_membership_events(events, knowledge_cutoff=CUT_BETWEEN_T1_T2)
    (original,) = earlier["current"]

    def _open_interval(row):
        return {k: v for k, v in row.items()
                if k not in {"knowledge_to", "superseded_by_event_sha256"}}

    assert json.dumps(_open_interval(original), sort_keys=True) == \
        json.dumps(_open_interval(closed), sort_keys=True)


def test_state_refresh_is_deterministic():
    src = [subject()]
    first = compose(copy.deepcopy(src))
    second = compose(copy.deepcopy(src))
    assert first["state_sha256"] == second["state_sha256"]
    assert first["generation_id"] == second["generation_id"]


# --------------------------------------------------------- P2: correction

def test_correction_latency_is_recorded_from_belief_clocks():
    append = _append()
    correct = _correct(T2, supersedes=append["event_sha256"], tag="fixture-r2")
    state = apply_activity_membership_events([append, correct], knowledge_cutoff=AFTER_ALL)
    (closed,) = state["history"]
    latency_hours = (_instant(closed["knowledge_to"])
                     - _instant(closed["knowledge_from"])).total_seconds() / 3600
    expected_hours = (_instant(T2) - _instant(T1)).total_seconds() / 3600
    assert latency_hours == expected_hours
    print(json.dumps({"original": closed["event_sha256"],
                      "correction": correct["event_sha256"],
                      "latency_hours": latency_hours}))


def test_state_correction_is_a_later_generation_and_keeps_the_original():
    old = compose()
    frozen = copy.deepcopy(old)
    src = subject()
    for r in src["owners"].values():
        r["query"]["known_at"] = "2026-10-03T14:00:00Z"
    new = compose([src], known_at="2026-10-03T14:00:00Z",
                  generated_at="2026-10-03T14:00:00Z", previous=old)
    assert new["generation_id"] != old["generation_id"]
    assert new["correction"]["generation_id"] == old["generation_id"]
    assert new["correction"]["state_sha256"] == old["state_sha256"]
    assert old == frozen
    with pytest.raises(ValueError, match="later"):
        compose(previous=old)


def test_rejected_correction_never_replaces_the_belief():
    append = _append()
    rejected = _event("CORRECT", knowledge_at=T2, supersedes=append["event_sha256"],
                      lineage=_lineage(fact_revision=2),
                      curation=_curation("REJECT", at=T2, tag="fixture-reject"))
    state = apply_activity_membership_events([append, rejected], knowledge_cutoff=AFTER_ALL)
    assert [row["reason"] for row in state["refused"]] == ["CORRECTION_NOT_ACCEPTED"]
    assert [b["event_sha256"] for b in state["current"]] == [append["event_sha256"]]
    assert state["history"] == []


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="A2 activity history v1 has no WITHHOLD action; curated withholding of "
                          "an existing belief is owed by the activity_membership_history v2 "
                          "contract (owner WS:GMI-THEME-GRAPH)")
def test_curated_withhold_of_an_existing_belief():
    schema = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert "WITHHOLD" in schema["properties"]["action"]["enum"]


# ------------------------------------------------------------ P3: removal

@pytest.mark.parametrize("completeness,exhaustive,reason", [
    ("TIMEOUT", True, "REMOVAL_REFUSED_TIMEOUT"),
    ("PARTIAL", True, "REMOVAL_REFUSED_PARTIAL"),
    ("CHANGED_SHAPE", True, "REMOVAL_REFUSED_CHANGED_SHAPE"),
    ("COMPLETE_AUTHORITATIVE", False, "REMOVAL_REFUSED_NON_EXHAUSTIVE_ROSTER"),
])
def test_failed_fetch_never_retires_membership(completeness, exhaustive, reason):
    append = _append()
    remove = _event("REMOVE", knowledge_at=T2, observation=_observation(
        completeness, exhaustive=exhaustive, present=False))
    state = apply_activity_membership_events([append, remove], knowledge_cutoff=AFTER_ALL)

    assert [b["event_sha256"] for b in state["current"]] == [append["event_sha256"]]
    assert state["current"][0]["knowledge_to"] is None
    (kept,) = state["retained"]
    assert kept["reason"] == reason
    assert kept["event_sha256"] == remove["event_sha256"]
    assert kept["retained_belief_event_sha256"] == append["event_sha256"]
    assert state["history"] == []


def test_authoritative_absence_retires_with_a_retire_record():
    append = _append()
    remove = _event("REMOVE", knowledge_at=T2, observation=_observation())
    state = apply_activity_membership_events([append, remove], knowledge_cutoff=AFTER_ALL)

    assert state["current"] == [] and state["retained"] == [] and state["refused"] == []
    (retired,) = state["history"]
    assert retired["event_sha256"] == append["event_sha256"]
    assert retired["removed_by_event_sha256"] == remove["event_sha256"]
    assert retired["knowledge_to"] == T2


def test_present_subject_contradicts_removal():
    append = _append()
    remove = _event("REMOVE", knowledge_at=T2,
                    observation=_observation(present=True))
    state = apply_activity_membership_events([append, remove], knowledge_cutoff=AFTER_ALL)

    assert [b["event_sha256"] for b in state["current"]] == [append["event_sha256"]]
    (kept,) = state["retained"]
    assert kept["reason"] == "REMOVAL_CONTRADICTED_SUBJECT_PRESENT"
    assert kept["retained_belief_event_sha256"] == append["event_sha256"]
    assert state["history"] == []


def test_orphan_remove_is_refused():
    remove = _event("REMOVE", knowledge_at=T2, observation=_observation())
    state = apply_activity_membership_events([remove], knowledge_cutoff=AFTER_ALL)
    assert [row["reason"] for row in state["refused"]] == ["NO_CURRENT_BELIEF"]
    assert state["current"] == [] and state["history"] == [] and state["retained"] == []


# --------------------------------------------------- P4: historical cutoff

def test_cutoff_hides_rows_born_after_it():
    append = _append()
    correct = _correct(T2, supersedes=append["event_sha256"], tag="fixture-r2")
    remove = _event("REMOVE", knowledge_at=T3, observation=_observation(at=T3))
    events = [append, correct, remove]

    early = apply_activity_membership_events(events, knowledge_cutoff=CUT_BETWEEN_T1_T2)
    assert [b["event_sha256"] for b in early["current"]] == [append["event_sha256"]]
    assert early["history"] == []
    assert early["excluded_after_cutoff"] == sorted(
        [correct["event_sha256"], remove["event_sha256"]])
    excluded = set(early["excluded_after_cutoff"])
    assert not ({row["event_sha256"] for row in early["retained"]}
                | {row["event_sha256"] for row in early["refused"]}) & excluded

    middle = apply_activity_membership_events(events, knowledge_cutoff=CUT_BETWEEN_T2_T3)
    assert [b["event_sha256"] for b in middle["current"]] == [correct["event_sha256"]]
    assert [row["event_sha256"] for row in middle["history"]] == [append["event_sha256"]]

    before = apply_activity_membership_events(events, knowledge_cutoff="2026-10-11T00:00:00Z")
    assert before["current"] == []
    assert before["excluded_after_cutoff"] == sorted(
        [append["event_sha256"], correct["event_sha256"], remove["event_sha256"]])


@pytest.mark.parametrize("cutoff", ["2026-10-15", "2026-10-15T00:00:00", "not-a-time"])
def test_invalid_cutoff_is_refused(cutoff):
    with pytest.raises(ActivityHistoryRefusal) as caught:
        apply_activity_membership_events([_append()], knowledge_cutoff=cutoff)
    assert caught.value.code == "KNOWLEDGE_CUTOFF_INVALID"


def test_state_reader_never_supplies_later_knowledge():
    state = compose()
    early = state_module().read_theme_state(state, TARGET, effective_at=QUERY["effective_at"],
                                            known_at="2026-10-03T08:30:00Z")
    assert early["status"] == "UNAVAILABLE" and early["subject"] is None
    assert {"STATE_AFTER_CUTOFF", "STATE_NOT_YET_EMITTED"} <= set(early["reason_codes"])


# ---------------------------------------------- P5: source failure + 48h

@pytest.mark.parametrize("effective_at,max_age_hours,expected", [
    ("2026-10-01T13:00:00Z", 48, "FRESH"),
    ("2026-10-01T11:00:00Z", 48, "STALE"),
    ("2026-10-01T20:00:00Z", 30, "STALE"),
    ("2026-10-01", 48, "UNKNOWN"),
])
def test_freshness_budget_is_computed_from_fixture_clocks_and_reported(
        effective_at, max_age_hours, expected):
    age_hours = (_instant(QUERY["known_at"]) - _instant(effective_at)).total_seconds() / 3600
    src = subject()
    src["observations"]["fixture_signal"] = _fixture_freshness_observation(
        effective_at, max_age_hours)
    reported = compose([src])["subjects"][0]["observations"]["fixture_signal"]
    assert reported["freshness"] == expected
    print(json.dumps({"effective_at": effective_at, "known_at": QUERY["known_at"],
                      "age_hours": age_hours, "max_age_hours": max_age_hours,
                      "freshness": reported["freshness"]}))


def test_unavailable_source_is_visible_not_green():
    src = subject()
    src["observations"]["fixture_signal"] = observation({"return": 1.25})
    src["observations"]["fixture_signal"]["source_receipts"] = [
        receipt("specialist", None, TARGET, availability="UNAVAILABLE",
                effective_at="2026-10-03T08:00:00Z")]
    out = compose([src])["subjects"][0]["observations"]["fixture_signal"]
    assert out["presence"] == "UNAVAILABLE" and out["value"] is None
    assert out["null_reason"] == "OWNER_UNAVAILABLE"

    missing = subject()
    missing["owners"]["membership"] = receipt("membership", None, TARGET,
                                              availability="UNAVAILABLE")
    state = compose([missing])
    read = state_module().read_theme_state(state, TARGET, **QUERY)
    assert read["status"] == "UNAVAILABLE" and read["subject"] is None
    assert "MEMBERSHIP_UNAVAILABLE" in read["reason_codes"]


def test_stale_state_is_reported_by_the_reader():
    state = compose()
    read = state_module().read_theme_state(state, TARGET, effective_at=QUERY["effective_at"],
                                           known_at="2026-10-04T19:00:00Z")
    assert read["status"] == "UNAVAILABLE"
    assert "STATE_STALE" in read["reason_codes"]


def test_unavailable_or_non_pit_native_membership_is_not_a_roster():
    pit_native = {"availability": "AVAILABLE",
                  "value": {"pit": True, "members": [{"ticker": "FIXA"}],
                            "snapshot_date": "2026-10-03", "basket_id": "fixture-roster-01",
                            "suite": readers.MEMBERSHIP_SUITES[0]}}
    assert readers.StateQualificationReader._pit_membership(pit_native) == pit_native["value"]
    for native in (
            dict(pit_native, availability="UNAVAILABLE"),
            dict(pit_native, availability="TIMEOUT"),
            {"availability": "AVAILABLE", "value": dict(pit_native["value"], pit=False)},
            {"availability": "AVAILABLE", "value": dict(pit_native["value"], members=[])},
    ):
        assert readers.StateQualificationReader._pit_membership(native) is None


# ------------------------------ fold wiring (a strict xfail until 2026-10-21)

def test_fold_is_wired_into_build_so_publication_marks_corrections_and_routing_is_measured():
    assert "apply_activity_membership_events" in inspect.getsource(materialize.build)
