"""Connected SOURCE proposals; no authoritative acceptance or clock issuer exists.

Only the existing synthetic preparation and advisory composer call this pure
contract. External references remain claims: matching bytes cannot authenticate
an issuer, supersession history, an accepted freeze, or a label's availability.
PENDING/MATURE are deliberately unreachable without a qualified existing verifier.
No labels enter candidate inputs, no values are evaluated, and no record is written.
"""
import hashlib
from . import bridge, contracts

PROPOSAL_SCHEMA = "research_codegen.freeze_evidence_proposal.v1"
REFERENCE_SCHEMA = "research_codegen.freeze_evidence_reference.v1"
LABEL_SCHEMA = "research_codegen.label_readiness_declaration.v1"
# Existing evaluator: entry is trigger+1, then 25 future returns through trigger+26.
# The reference exit consumes 21 returns through trigger+22, never the MAE boundary.
LABEL_DEPENDENCIES = (("mae25", 26), ("reference_exit21", 22))
_SCOPE = "FIXED_NINE_SECTOR_MAE25_EXIT21"
_FLAGS = dict(generation_enabled=False, execution_enabled=False, evaluation_enabled=False,
              registration_enabled=False, admission_enabled=False, authority_granted=False)


def _require(ok, cause="PROSPECTIVE_SOURCE_CONTRACT_REFUSED"):
    if not ok:
        raise bridge.BridgeRefused(cause)


def _bound(doc):
    raw = bridge._canonical_bytes(doc)
    _require(len(raw) <= contracts.MAX_BYTES)
    return bridge.BoundBytes(raw, hashlib.sha256(raw).hexdigest(), len(raw))


def _digest(doc):
    raw = bridge._canonical_bytes(doc)
    _require(len(raw) <= bridge.MAX_ARTIFACT_BYTES)
    return hashlib.sha256(raw).hexdigest()


def _reference(doc, expected_identity=None):
    bridge._closed(doc, ("schema", "issuer_origin", "receipt_id", "evidence_sha256",
                        "proposal_identity_sha256", "state", "superseded_by"))
    _require(doc["schema"] == REFERENCE_SCHEMA and contracts._opaque_id(doc["issuer_origin"])
             and contracts._opaque_id(doc["receipt_id"]) and contracts._sha(doc["evidence_sha256"])
             and contracts._sha(doc["proposal_identity_sha256"])
             and type(doc["state"]) is str and doc["state"] == "current"
             and doc["superseded_by"] is None, "EXTERNAL_REFERENCE_INVALID_OR_STALE")
    if expected_identity is not None:
        _require(doc["proposal_identity_sha256"] == expected_identity, "EXTERNAL_REFERENCE_SCOPE_MISMATCH")


def _preparation_scope(prepared):
    return dict(identity={key: getattr(prepared.identity, key) for key in bridge._IDENTITY},
        decision_inputs_sha256=_digest([dict(fold_id=t.fold_id, entity_id=t.entity_id,
            decision_id=t.decision_id, calendar_index=t.calendar_index,
            input_sha256=t.input_bytes.sha256, request_sha256=t.request.sha256,
            capture_evidence_sha256=t.capture_evidence.sha256 if t.capture_evidence is not None else None)
            for t in prepared.decisions]), session_dates_sha256=_digest(list(prepared.session_dates)),
        owner_schedules_sha256=_digest([dict(fold_id=g.fold_id, entity_id=g.entity_id,
            decision_ids=list(g.decision_ids)) for g in prepared.schedules]))


def produce_freeze_proposal(run, prepared):
    """Produce an immutable proposal before transport; never accepted-freeze evidence."""
    generation = bridge._bound(run.expected_generation)
    base = dict(schema=PROPOSAL_SCHEMA, **_preparation_scope(prepared),
        trial_family=generation["family"], history_anchor_sha256=generation["history_anchor_sha256"],
        expected_generation_sha256=run.expected_generation.sha256,
        scope="SYNTHETIC_ENGINEERING_ONLY", study_scope=_SCOPE,
        declared_freeze_at_utc=run.declared_freeze_at_utc)
    if run.declared_freeze_at_utc is not None:
        bridge._timestamp(run.declared_freeze_at_utc)
    identity_sha = _bound(base).sha256
    _require(type(run.freeze_evidence_references) is tuple and len(run.freeze_evidence_references) <= 16)
    refs, seen_ids, seen_evidence = [], set(), set()
    for raw in run.freeze_evidence_references:
        ref = bridge._bound(raw)
        _reference(ref, identity_sha)
        _require(ref["receipt_id"] not in seen_ids and ref["evidence_sha256"] not in seen_evidence,
                 "EXTERNAL_REFERENCE_REPLAYED")
        seen_ids.add(ref["receipt_id"]); seen_evidence.add(ref["evidence_sha256"])
        refs.append(ref)
    return _bound(dict(base=base, proposal_identity_sha256=identity_sha, external_references=refs))


def verify_freeze_proposal(proposal, *, prepared=None):
    """Pure closed verification; UNQUALIFIED is the strongest available result."""
    doc = bridge._bound(proposal)
    bridge._closed(doc, ("base", "proposal_identity_sha256", "external_references"))
    base = doc["base"]
    bridge._closed(base, ("schema", "identity", "trial_family", "history_anchor_sha256",
        "expected_generation_sha256", "decision_inputs_sha256", "session_dates_sha256",
        "owner_schedules_sha256", "scope", "study_scope", "declared_freeze_at_utc"))
    bridge._closed(base["identity"], bridge._IDENTITY)
    _require(base["schema"] == PROPOSAL_SCHEMA and base["scope"] == "SYNTHETIC_ENGINEERING_ONLY"
             and base["study_scope"] == _SCOPE and contracts._family(base["trial_family"])
             and all(contracts._sha(base[k]) for k in ("history_anchor_sha256", "expected_generation_sha256",
                 "decision_inputs_sha256", "session_dates_sha256", "owner_schedules_sha256"))
             and all(contracts._sha(v) if k.endswith("sha256") else contracts._opaque_id(v)
                     for k, v in base["identity"].items())
             and doc["proposal_identity_sha256"] == _bound(base).sha256)
    if prepared is not None:
        _require(all(base[key] == value for key, value in _preparation_scope(prepared).items()),
                 "PROPOSAL_PREPARATION_MISMATCH")
    if base["declared_freeze_at_utc"] is not None:
        bridge._timestamp(base["declared_freeze_at_utc"])
    refs = doc["external_references"]
    _require(type(refs) is list and len(refs) <= 16)
    seen = set()
    for ref in refs:
        _reference(ref, doc["proposal_identity_sha256"])
        key = (ref["receipt_id"], ref["evidence_sha256"])
        _require(all(key[0] != old[0] and key[1] != old[1] for old in seen), "EXTERNAL_REFERENCE_REPLAYED")
        seen.add(key)
    missing = ["QUALIFIED_ACCEPTANCE_ISSUER_UNAVAILABLE"]
    if not refs: missing.append("ACCEPTANCE_EVIDENCE_ABSENT")
    if base["declared_freeze_at_utc"] is None: missing.append("DECLARED_FREEZE_TIME_ABSENT")
    return dict(status="UNQUALIFIED", proposal_sha256=proposal.sha256,
                missing_evidence=missing, **_FLAGS)


def _assess_label(label, name, dependency, proposal_identity):
    bridge._closed(label, ("label_id", "dependency_end_session", "declared_expected_maturity_at_utc",
        "source_id", "source_revision_sha256", "basis", "vintage", "observation_id",
        "known_by_at_utc", "received_at_utc", "receipt_sha256", "clock_basis", "clock_evidence_reference"))
    _require(label["label_id"] == name and label["dependency_end_session"] == dependency,
             "LABEL_DEPENDENCY_MISMATCH")
    _require(label["basis"] == "total_return", "LABEL_BASIS_MISMATCH")
    missing = []
    for field in ("source_id", "vintage", "observation_id"):
        if label[field] is None: missing.append(field.upper() + "_ABSENT")
        else: _require(contracts._opaque_id(label[field]), "LABEL_SOURCE_IDENTITY_INVALID")
    revision = label["source_revision_sha256"]
    if revision is None: missing.append("SOURCE_REVISION_ABSENT")
    else: _require(contracts._sha(revision), "LABEL_SOURCE_IDENTITY_INVALID")
    expected = label["declared_expected_maturity_at_utc"]
    if expected is None: missing.append("EXPECTED_MATURITY_UNKNOWN")
    else:
        expected_time = bridge._timestamp(expected)
        _require(expected_time.date().isoformat() >= dependency, "MATURITY_PRECEDES_DEPENDENCY")
    known, received = label["known_by_at_utc"], label["received_at_utc"]
    if known is not None:
        known_time = bridge._timestamp(known)
        _require(known_time.date().isoformat() >= dependency, "LABEL_KNOWN_BEFORE_DEPENDENCY")
        _require(expected is None or known_time >= bridge._timestamp(expected), "LABEL_KNOWN_BEFORE_DEPENDENCY")
    if received is not None:
        _require(known is not None and bridge._timestamp(received) >= bridge._timestamp(known),
                 "LABEL_RECEIPT_CHRONOLOGY_CONFLICT")
    receipt = label["receipt_sha256"]
    if receipt is not None: _require(contracts._sha(receipt), "LABEL_RECEIPT_INVALID")
    # No asserted known-by time without its actual bound receipt identity.
    if known is None: missing.append("LABEL_AVAILABILITY_UNOBSERVED")
    _require((known is None and received is None and receipt is None)
             or (known is not None and received is not None and receipt is not None), "LABEL_RECEIPT_INCOMPLETE")
    if label["clock_basis"] is None: missing.append("CLOCK_BASIS_ABSENT")
    else: _require(type(label["clock_basis"]) is str and label["clock_basis"] in
                   ("LOCAL_CLOCK_UNATTESTED", "SOURCE_SESSION_REFERENCE"), "CLOCK_BASIS_INVALID")
    clock = label["clock_evidence_reference"]
    if clock is not None: _reference(clock, proposal_identity)
    else: missing.append("CLOCK_EVIDENCE_ABSENT")
    # Origin/clock strings above are references, never a qualified verifier.
    causes = missing + ["QUALIFIED_CLOCK_VERIFIER_UNAVAILABLE", "ACCEPTED_FREEZE_UNAVAILABLE"]
    return ("UNKNOWN" if missing else "UNQUALIFIED"), causes


def assess_label_readiness(run, prepared, *, local_observations=()):
    """Conserve both original label dependencies per decision, without scoring."""
    _require(type(run.label_readiness) is tuple and len(run.label_readiness) <= 4096
             and run.session_dates == prepared.session_dates)
    positions = {}
    for position in run.positions:
        _require(type(position) is bridge.SchedulePosition and type(position.calendar_index) is int
                 and position.calendar_index >= 0 and position.calendar_index not in positions,
                 "FORMATION_IDENTITY_INVALID")
        positions[position.calendar_index] = position
    freeze_after_issue = False
    if run.declared_freeze_at_utc is not None:
        declared = bridge._timestamp(run.declared_freeze_at_utc)
        for raw in local_observations:
            if raw is not None:
                observation = bridge._bound(raw)
                if declared > bridge._timestamp(observation["issued_at_utc"]):
                    freeze_after_issue = True
    supplied, invalid = {}, False
    for raw in run.label_readiness:
        doc = bridge._bound(raw)
        bridge._closed(doc, ("schema", "fold_id", "entity_id", "decision_id", "input_sha256", "labels"))
        _require(doc["schema"] == LABEL_SCHEMA)
        key = (doc["fold_id"], doc["entity_id"], doc["decision_id"])
        _require(all(contracts._opaque_id(k) for k in key) and key not in supplied)
        supplied[key] = doc
    wanted = {(t.fold_id, t.entity_id, t.decision_id) for t in prepared.decisions}
    invalid = bool(set(supplied) - wanted)
    proposal = bridge._bound(prepared.freeze_proposal)
    labels = []
    for task in prepared.decisions:
        key = (task.fold_id, task.entity_id, task.decision_id)
        declaration = supplied.get(key)
        for name, offset in LABEL_DEPENDENCIES:
            state, causes = "UNKNOWN", ["LABEL_DECLARATION_ABSENT"]
            try:
                _require(not freeze_after_issue, "DECLARED_FREEZE_AFTER_TRANSPORT_ISSUE")
                _require(not invalid, "UNEXPECTED_DECISION_DECLARATION")
                _require(type(task.calendar_index) is int and task.calendar_index >= 0
                         and task.calendar_index in positions, "DECISION_FORMATION_IDENTITY_INVALID")
                position = positions[task.calendar_index]
                _require(position.trigger_date in run.session_dates, "DECISION_FORMATION_IDENTITY_INVALID")
                trigger = run.session_dates.index(position.trigger_date)
                _require(trigger + offset < len(run.session_dates), "LABEL_HORIZON_INCOMPLETE")
                if declaration is not None:
                    _require(declaration["input_sha256"] == task.input_bytes.sha256, "LABEL_INPUT_MISMATCH")
                    items = declaration["labels"]
                    _require(type(items) is list and len(items) == 2
                             and all(type(r) is dict for r in items)
                             and [r.get("label_id") for r in items] == [n for n, _ in LABEL_DEPENDENCIES],
                             "LABEL_SET_MISMATCH")
                    label = items[0 if name == "mae25" else 1]
                    state, causes = _assess_label(label, name, run.session_dates[trigger + offset],
                                                proposal["proposal_identity_sha256"])
            except ValueError as exc:
                state = "REFUSED"
                # Closed codes only: never project caller text or raw labels.
                code = str(exc)
                causes = [code if code in _REFUSAL_CODES else "LABEL_DECLARATION_INVALID"]
            labels.append(dict(decision_sha256=hashlib.sha256(bridge._canonical_bytes(key)).hexdigest(),
                               label_id=name, state=state, missing_evidence=causes))
    expected_decisions = [hashlib.sha256(bridge._canonical_bytes(
        (t.fold_id, t.entity_id, t.decision_id))).hexdigest() for t in prepared.decisions]
    freeze = verify_freeze_proposal(prepared.freeze_proposal, prepared=prepared)
    return dict(schema="research_codegen.prospective_readiness.v1", scope="SYNTHETIC_ENGINEERING_ONLY",
        proposal_sha256=prepared.freeze_proposal.sha256, freeze_status=freeze["status"],
        status="REFUSED" if any(r["state"] == "REFUSED" for r in labels) else "UNQUALIFIED",
        driver_proposal_binding="UNAVAILABLE",
        expected_decision_sha256s=expected_decisions,
        decision_coverage_sha256=_digest(expected_decisions),
        missing_evidence=freeze["missing_evidence"], labels=labels,
        unknown_count=sum(r["state"] == "UNKNOWN" for r in labels),
        unqualified_count=sum(r["state"] == "UNQUALIFIED" for r in labels),
        refused_count=sum(r["state"] == "REFUSED" for r in labels),
        pending_count=0, mature_count=0, **_FLAGS)


_REFUSAL_CODES = frozenset({"LABEL_DEPENDENCY_MISMATCH", "LABEL_BASIS_MISMATCH",
    "LABEL_SOURCE_IDENTITY_INVALID", "MATURITY_PRECEDES_DEPENDENCY", "LABEL_KNOWN_BEFORE_DEPENDENCY",
    "LABEL_RECEIPT_CHRONOLOGY_CONFLICT", "LABEL_RECEIPT_INVALID", "LABEL_RECEIPT_INCOMPLETE",
    "EXTERNAL_REFERENCE_INVALID_OR_STALE", "EXTERNAL_REFERENCE_SCOPE_MISMATCH",
    "UNEXPECTED_DECISION_DECLARATION", "LABEL_HORIZON_INCOMPLETE", "LABEL_INPUT_MISMATCH", "LABEL_SET_MISMATCH",
    "CLOCK_BASIS_INVALID", "DECLARED_FREEZE_AFTER_TRANSPORT_ISSUE", "DECISION_FORMATION_IDENTITY_INVALID"})


def validate_public_readiness(value):
    """Closed advisory projection: no raw labels, timestamps, paths or issuer claims."""
    bridge._closed(value, ("schema", "scope", "proposal_sha256", "freeze_status", "status",
        "driver_proposal_binding", "missing_evidence", "expected_decision_sha256s", "decision_coverage_sha256",
        "labels", "unknown_count", "unqualified_count", "refused_count", "pending_count", "mature_count", *_FLAGS))
    _require(type(value["schema"]) is str and value["schema"] == "research_codegen.prospective_readiness.v1"
             and type(value["scope"]) is str and value["scope"] == "SYNTHETIC_ENGINEERING_ONLY"
             and type(value["freeze_status"]) is str and value["freeze_status"] == "UNQUALIFIED"
             and type(value["driver_proposal_binding"]) is str
             and value["driver_proposal_binding"] in ("UNAVAILABLE", "BOUND_SOURCE_ONLY")
             and type(value["status"]) is str and value["status"] in ("UNQUALIFIED", "REFUSED")
             and contracts._sha(value["proposal_sha256"])
             and all(type(value[k]) is bool and value[k] is False for k in _FLAGS))
    permitted = _REFUSAL_CODES | frozenset({"LABEL_DECLARATION_INVALID", "LABEL_DECLARATION_ABSENT",
        "QUALIFIED_ACCEPTANCE_ISSUER_UNAVAILABLE", "ACCEPTANCE_EVIDENCE_ABSENT", "DECLARED_FREEZE_TIME_ABSENT",
        "SOURCE_ID_ABSENT", "VINTAGE_ABSENT", "OBSERVATION_ID_ABSENT", "SOURCE_REVISION_ABSENT", "CLOCK_BASIS_ABSENT",
        "EXPECTED_MATURITY_UNKNOWN", "QUALIFIED_CLOCK_VERIFIER_UNAVAILABLE", "ACCEPTED_FREEZE_UNAVAILABLE",
        "LABEL_AVAILABILITY_UNOBSERVED", "CLOCK_EVIDENCE_ABSENT"})
    def reasons(items):
        _require(type(items) is list and 0 < len(items) <= 16
                 and all(type(c) is str and c in permitted for c in items))
        return list(items)
    expected = value["expected_decision_sha256s"]
    _require(type(expected) is list and len(expected) <= 4096
             and all(contracts._sha(item) for item in expected)
             and len(set(expected)) == len(expected)
             and value["decision_coverage_sha256"] == _digest(expected))
    labels, seen, groups = [], set(), {}
    _require(type(value["labels"]) is list and len(value["labels"]) <= 8192)
    for row in value["labels"]:
        bridge._closed(row, ("decision_sha256", "label_id", "state", "missing_evidence"))
        _require(contracts._sha(row["decision_sha256"]) and type(row["label_id"]) is str
                 and row["label_id"] in ("mae25", "reference_exit21") and type(row["state"]) is str
                 and row["state"] in ("UNKNOWN", "UNQUALIFIED", "REFUSED"))
        key = (row["decision_sha256"], row["label_id"])
        _require(key not in seen); seen.add(key)
        groups.setdefault(key[0], set()).add(key[1])
        labels.append({**row, "missing_evidence": reasons(row["missing_evidence"])})
    for state in ("unknown", "unqualified", "refused", "pending", "mature"):
        count = value[state + "_count"]
        _require(type(count) is int and count == sum(r["state"] == state.upper() for r in labels))
    _require(value["status"] == ("REFUSED" if value["refused_count"] else "UNQUALIFIED"))
    _require([(r["decision_sha256"], r["label_id"]) for r in labels]
             == [(decision, name) for decision in expected for name, _ in LABEL_DEPENDENCIES],
             "LABEL_COVERAGE_MISMATCH")
    return {**value, "expected_decision_sha256s": list(expected),
            "missing_evidence": reasons(value["missing_evidence"]), "labels": labels}
