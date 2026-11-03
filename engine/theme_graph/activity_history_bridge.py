"""Curated activity proposal -> activity-history APPEND event bridge (GMI M1 step 2).

Two owners exist and this module only joins them:

* ``engine.theme_graph.probation`` keeps the append-only activity proposal ledger
  (``data/theme_graph/probation/activity_proposals.jsonl``): PROPOSED rows plus the
  terminal RATIFIED/REJECTED rows a NAMED curator wrote, with the receipt BYTES
  hashed into ``curation.receipt_sha256``.
* ``engine.theme_graph.materialize`` folds ``gmi.activity_membership_history_event/v1``
  events into belief (``apply_activity_membership_events``) and refuses every event
  whose ``use_qualification`` does not carry ``graph_membership_use: GRANTED``.

``graph_membership_use`` is granted ONLY by a Chairman ruling REVISION file — a
``company_intelligence.source_purpose_ruling/v1`` record whose ``revises_ruling_sha256``
binds the ORIGINAL source-purpose ruling and whose ``graph_membership_use_grant``
names this exact proposal. No such revision exists on the base tree (an
EXACT_HUMAN_GATE), so until one is dropped at the default glob

    research/theme_graph/*/*GRAPH_MEMBERSHIP_USE_RULING*.json

a RATIFIED proposal stays in its honest state: the bridge writes NO event, records a
HELD bridge receipt with reason ``GRAPH_MEMBERSHIP_USE_NOT_GRANTED``, and proves in
memory that the fold itself refuses the would-be event with that same reason. The
positive path exists only behind a fixture grant (``ruling_id`` prefixed ``FIXTURE``)
reachable solely through ``allow_fixture=True`` — a test door the CLI never opens.
Dropping the real ruling revision plus the seat's curation receipt into the repo must
flip the proposal to an APPEND event the fold accepts as CURRENT belief with NO code
change; every default below (paths, glob, receipt-file name) is designed for that.

This is a bridge for the owners above. It is NOT a new producer, rights resolver,
selection store or ThemeState owner: it decides nothing about rights, imports no
``engine.company_intelligence`` module, never writes a ruling or a curation receipt,
and never touches the proposal ledger.

One decision per ``proposal_id``, sorted: outcome SKIPPED / HELD / APPEND / REFUSED.
A HELD decision carries the would-be event it evaluated — that is the event the fold
refused — for audit only; ``apply_plan`` appends ONLY ``APPEND`` events, so a HELD
event is never written to the events file, and the HELD bridge receipt records
``event_id``/``event_sha256`` as null because nothing was emitted.
"""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import timezone
from functools import lru_cache
from pathlib import Path

from engine.theme_graph import materialize, probation

ROOT = Path(__file__).resolve().parents[2]

BRIDGE_RECEIPT_SCHEMA = "gmi.activity_history_bridge_receipt/v1"
CURATION_RECEIPT_CONTRACT = "contracts/theme_graph/activity_curation_receipt.v1.schema.json"
DEFAULT_RECEIPTS_DIR = "research/theme_graph/activity_curation_receipts"
DEFAULT_EVENTS_PATH = "data/theme_graph/probation/activity_history_events.jsonl"
DEFAULT_BRIDGE_RECEIPTS_PATH = (
    "data/theme_graph/probation/activity_history_bridge_receipts.jsonl")
DEFAULT_USE_RULING_GLOB = "research/theme_graph/*/*GRAPH_MEMBERSHIP_USE_RULING*.json"

_SOURCE_PURPOSE_RULING_SCHEMA = "company_intelligence.source_purpose_ruling/v1"
_FIXTURE_RULING_PREFIX = "FIXTURE"
_DECISION_TO_CURATION = {"RATIFIED": "ACCEPT", "REJECTED": "REJECT"}
# The five use fields a grant must carry EXACTLY; its subject/target/species/scope/
# proposal_ids fields are checked against the evidence by USE_RULING_GRANT_MISMATCH.
_GRANT_REQUIRED = {
    "purpose": "graph_membership_use",
    "graph_membership_use": "GRANTED",
    "internal": True,
    "display": False,
    "redistribution": False,
}
_BRIDGE_RECEIPT_KEYS = frozenset({
    "schema", "proposal_id", "proposal_sha256", "outcome", "reason_code",
    "graph_membership_use", "event_id", "event_sha256", "curation_receipt_sha256",
    "use_ruling_path", "use_ruling_sha256", "ruling_refusals", "recorded_at",
})
class BridgeRefusal(Exception):
    """A typed bridge refusal; ``code`` is stable and is what callers branch on."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


def proposal_sha256(row: dict) -> str:
    """sha256 of the proposal row's canonical JSON (probation's own canonical form)."""
    return hashlib.sha256(probation._activity_canonical(row).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Curation receipt (contract A)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _curation_receipt_validator():
    import jsonschema

    schema = json.loads((ROOT / CURATION_RECEIPT_CONTRACT).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


def curation_receipt_path(receipts_dir, proposal_id: str) -> Path:
    """The receipt-file convention: ``<receipts-dir>/<proposal_id with ':' -> '_'>.json``."""
    return Path(receipts_dir) / (proposal_id.replace(":", "_") + ".json")


def read_curation_receipt_bytes(receipts_dir, proposal_id: str) -> bytes:
    """The seat's receipt bytes at the convention path; b"" when the file is absent."""
    path = curation_receipt_path(receipts_dir, proposal_id)
    if not path.exists():
        return b""
    return path.read_bytes()


def check_curation_receipt(proposed_row: dict, terminal_row: dict,
                           receipt_bytes: bytes | None) -> dict:
    """Validate the curator receipt bytes against the terminal ledger row.

    Every refusal names WHY: RECEIPT_MISSING (no bytes), RECEIPT_SHA_MISMATCH (the
    bytes do not hash to ``curation.receipt_sha256``), RECEIPT_INVALID (not JSON or
    not a contract-A receipt), RECEIPT_PROPOSAL_MISMATCH (a different subject or a
    different PROPOSED row hash) and RECEIPT_FIELD_MISMATCH (curator, reviewed_at or
    decision disagree with the row). Returns the parsed receipt.
    """
    curation = terminal_row.get("curation") or {}
    if not receipt_bytes:
        raise BridgeRefusal(
            "RECEIPT_MISSING", f"no receipt bytes for {proposed_row.get('proposal_id')!r}")
    digest = hashlib.sha256(receipt_bytes).hexdigest()
    if digest != curation.get("receipt_sha256"):
        raise BridgeRefusal(
            "RECEIPT_SHA_MISMATCH",
            f"receipt hashes to {digest}, the ledger recorded {curation.get('receipt_sha256')}")
    try:
        receipt = json.loads(receipt_bytes.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 — a torn receipt is a refusal, not a crash
        raise BridgeRefusal("RECEIPT_INVALID", f"not JSON: {exc}") from None
    errors = [
        f"{'/'.join(str(p) for p in err.absolute_path) or '<root>'}: {err.message}"
        for err in _curation_receipt_validator().iter_errors(receipt)
    ]
    if errors:
        raise BridgeRefusal("RECEIPT_INVALID", "; ".join(errors[:3]))
    if receipt["proposal_id"] != proposed_row.get("proposal_id"):
        raise BridgeRefusal(
            "RECEIPT_PROPOSAL_MISMATCH", f"receipt names {receipt['proposal_id']!r}")
    if receipt["proposal_sha256"] != proposal_sha256(proposed_row):
        raise BridgeRefusal(
            "RECEIPT_PROPOSAL_MISMATCH", "receipt hashes a different PROPOSED row")
    if receipt["curator"] != curation.get("curator"):
        raise BridgeRefusal("RECEIPT_FIELD_MISMATCH", "curator differs from the ledger row")
    if receipt["reviewed_at"] != curation.get("decided_at"):
        raise BridgeRefusal(
            "RECEIPT_FIELD_MISMATCH", "reviewed_at differs from the ledger decided_at")
    if _DECISION_TO_CURATION.get(receipt["decision"]) != curation.get("decision"):
        raise BridgeRefusal(
            "RECEIPT_FIELD_MISMATCH",
            f"decision {receipt['decision']} disagrees with the ledger {curation.get('decision')}")
    return receipt


# ---------------------------------------------------------------------------
# Graph-membership use qualification (Chairman ruling revision only)
# ---------------------------------------------------------------------------

def _resolve_repo_path(value) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _ruling_refusal(path, code: str, detail: str) -> dict:
    return {"path": None if path is None else str(path), "code": code, "detail": detail}


def _ruling_revision_failure(path: str, ruling: dict, proposed_row: dict, *,
                             allow_fixture: bool) -> dict | None:
    """The first failing check for one ruling file, in the frozen order; None qualifies."""
    evidence = proposed_row.get("evidence") or {}
    if ruling.get("schema") != _SOURCE_PURPOSE_RULING_SCHEMA:
        return _ruling_refusal(path, "USE_RULING_SCHEMA",
                               f"schema is {ruling.get('schema')!r}, "
                               f"not {_SOURCE_PURPOSE_RULING_SCHEMA!r}")
    ruling_id = ruling.get("ruling_id")
    if (isinstance(ruling_id, str) and ruling_id.startswith(_FIXTURE_RULING_PREFIX)
            and not allow_fixture):
        return _ruling_refusal(path, "USE_RULING_FIXTURE",
                               f"ruling_id {ruling_id!r} is a fixture grant; "
                               "only a test may use it")
    # The revision must bind the ORIGINAL ruling by hash, twice over, and carry it.
    purpose = (evidence.get("use_qualification") or {}).get("purpose") or {}
    bindings = (evidence.get("source_evidence") or {}).get("owner_bindings") or {}
    revises_sha = ruling.get("revises_ruling_sha256")
    original_path = _resolve_repo_path(ruling.get("revises_ruling_path"))
    original_bytes = None
    if original_path is not None:
        try:
            original_bytes = original_path.read_bytes()
        except OSError:
            original_bytes = None
    original_sha = None if original_bytes is None else hashlib.sha256(original_bytes).hexdigest()
    if (revises_sha != purpose.get("ruling_binding_sha256")
            or revises_sha != bindings.get("purpose")
            or original_sha != revises_sha):
        return _ruling_refusal(path, "USE_RULING_REVISION_BINDING",
                               "revises_ruling_sha256 does not bind the original ruling "
                               "(evidence purpose binding, owner purpose binding and the "
                               "file's own bytes must all agree)")
    try:
        original = json.loads(original_bytes.decode("utf-8"))
    except Exception:  # noqa: BLE001 — an unreadable original fails the drift check
        original = None
    original_use = original.get("permitted_use") if isinstance(original, dict) else None
    if ruling.get("permitted_use") != original_use:
        return _ruling_refusal(path, "USE_RULING_REVISION_DRIFT",
                               "permitted_use differs from the original ruling's dict; "
                               "the revision must carry it verbatim")
    if (ruling.get("decision_owner") != "Chairman Chris"
            or ruling.get("evidence_kind") != "direct_chairman_source_rights_confirmation"
            or ruling.get("decision") != "covered"):
        return _ruling_refusal(path, "USE_RULING_AUTHORITY",
                               "not a covered direct Chairman source-rights confirmation")
    source = ruling.get("source") or {}
    edition = (evidence.get("source_evidence") or {}).get("edition") or {}
    if (source.get("sha256") != edition.get("source_sha256")
            or source.get("byte_length") != edition.get("byte_length")):
        return _ruling_refusal(path, "USE_RULING_SOURCE_MISMATCH",
                               "ruling source does not name the proposal's evidence edition")
    grant = ruling.get("graph_membership_use_grant")
    if not isinstance(grant, dict) or any(grant.get(k) != v
                                          for k, v in _GRANT_REQUIRED.items()):
        return _ruling_refusal(path, "USE_RULING_PERMITTED_USE",
                               "graph_membership_use_grant is missing or is not exactly "
                               "the granted internal-only graph use")
    endpoints = evidence.get("endpoints") or {}
    scope = evidence.get("scope") or {}
    grant_scope = grant.get("membership_scope") or {}
    proposal_ids = grant.get("proposal_ids")
    if (grant.get("subject_node_id") != endpoints.get("source_node_id")
            or grant.get("target_node_id") != endpoints.get("target_node_id")
            or grant.get("species") != evidence.get("species")
            or grant_scope.get("counterparty_issuer_id") != scope.get("counterparty_issuer_id")
            or grant_scope.get("platform") != scope.get("platform")
            or grant_scope.get("product") != scope.get("product")
            or not isinstance(proposal_ids, list)
            or proposed_row.get("proposal_id") not in proposal_ids):
        return _ruling_refusal(path, "USE_RULING_GRANT_MISMATCH",
                               "grant subject/target/species, membership scope or "
                               "proposal_ids differ from the proposal's evidence")
    recorded = probation._activity_zoned(ruling.get("recorded_at"))
    original_recorded = probation._activity_zoned(
        original.get("recorded_at") if isinstance(original, dict) else None)
    if recorded is None or original_recorded is None or recorded < original_recorded:
        return _ruling_refusal(path, "USE_RULING_CLOCK",
                               "recorded_at is not a zoned instant or does not postdate "
                               "the original ruling")
    return None


def qualify_graph_membership_use(proposed_row: dict, ruling_paths, *,
                                 allow_fixture: bool = False) -> dict:
    """Qualify graph-membership use against Chairman ruling REVISION files.

    NEVER raises for a bad ruling: every failing file is recorded as one refusal and
    the next file is tried. A file qualifies only when every frozen check passes.
    Zero qualifying files -> NOT_GRANTED. More than one -> NOT_GRANTED plus
    USE_RULING_AMBIGUOUS (none is ever picked). Exactly one -> GRANTED. No paths at
    all -> NOT_GRANTED with USE_RULING_ABSENT.
    """
    refusals: list[dict] = []
    qualified: list[tuple[str, dict, str]] = []
    for raw_path in ruling_paths or []:
        path = str(raw_path)
        try:
            raw = Path(path).read_bytes()
            ruling = json.loads(raw.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 — an unreadable ruling is recorded
            refusals.append(_ruling_refusal(path, "USE_RULING_UNREADABLE", str(exc)))
            continue
        if not isinstance(ruling, dict):
            refusals.append(_ruling_refusal(path, "USE_RULING_UNREADABLE",
                                            "ruling is not a JSON object"))
            continue
        failure = _ruling_revision_failure(path, ruling, proposed_row,
                                           allow_fixture=allow_fixture)
        if failure is not None:
            refusals.append(failure)
            continue
        qualified.append((path, ruling, hashlib.sha256(raw).hexdigest()))
    if not ruling_paths:
        refusals.append(_ruling_refusal(None, "USE_RULING_ABSENT",
                                        "no graph-membership-use ruling revision was "
                                        "supplied or found at the default glob"))
    if not qualified:
        granted, pick = "NOT_GRANTED", None
    elif len(qualified) > 1:
        granted, pick = "NOT_GRANTED", None
        refusals.append(_ruling_refusal(None, "USE_RULING_AMBIGUOUS",
                                        f"{len(qualified)} ruling revisions qualify; "
                                        "none is picked"))
    else:
        granted, pick = "GRANTED", qualified[0]
    return {
        "graph_membership_use": granted,
        "ruling_path": None if pick is None else pick[0],
        "ruling_sha256": None if pick is None else pick[2],
        "ruling_recorded_at": None if pick is None else pick[1].get("recorded_at"),
        "refusals": refusals,
    }


# ---------------------------------------------------------------------------
# Event construction
# ---------------------------------------------------------------------------

def effective_at_from_evidence(clock: dict) -> dict:
    """The event's ``effective_at``: a KNOWN date verbatim, a KNOWN instant as its
    UTC calendar date, UNDISCLOSED / NOT_APPLICABLE as (null, state)."""
    state = (clock or {}).get("state")
    value = (clock or {}).get("value")
    if state == "KNOWN":
        if (clock or {}).get("precision") == "date" and isinstance(value, str):
            return {"value": value, "state": "KNOWN"}
        if (clock or {}).get("precision") == "instant":
            parsed = probation._activity_zoned(value)
            if parsed is not None:
                return {"value": parsed.astimezone(timezone.utc).date().isoformat(),
                        "state": "KNOWN"}
        raise BridgeRefusal("EFFECTIVE_CLOCK_UNMAPPABLE", repr(clock))
    if state in {"UNDISCLOSED", "NOT_APPLICABLE"}:
        return {"value": None, "state": state}
    raise BridgeRefusal("EFFECTIVE_CLOCK_UNMAPPABLE", repr(clock))


def build_append_event(proposed_row: dict, terminal_row: dict, use: dict, *,
                       recorded_at: str) -> dict:
    """One closed ``gmi.activity_membership_history_event/v1`` APPEND event.

    ``knowledge_at`` is the later of the curation instant and (when GRANTED) the
    ruling's ``recorded_at``, kept as the ORIGINAL string of the later instant. The
    built event is validated by the materialize owner; any failure is EVENT_INVALID.
    """
    evidence = proposed_row["evidence"]
    curation = terminal_row["curation"]
    recorded = probation._activity_zoned(recorded_at)
    if recorded is None:
        raise BridgeRefusal("RECORDED_AT_INVALID", repr(recorded_at))
    knowledge_at = curation["decided_at"]
    if use.get("graph_membership_use") == "GRANTED":
        ruling_at = probation._activity_zoned(use.get("ruling_recorded_at") or "")
        if ruling_at is None:
            raise BridgeRefusal("USE_RULING_CLOCK",
                                "a GRANTED use carries no zoned ruling_recorded_at")
        if ruling_at > probation._activity_zoned(knowledge_at):
            knowledge_at = use["ruling_recorded_at"]
    source_evidence = evidence["source_evidence"]
    bindings = source_evidence["owner_bindings"]
    endpoints = copy.deepcopy(evidence["endpoints"])
    scope = copy.deepcopy(evidence["scope"])
    event = {
        "schema": materialize.ACTIVITY_HISTORY_EVENT_SCHEMA,
        "action": "APPEND",
        "membership_id": materialize.activity_membership_id(
            source_node_id=endpoints["source_node_id"],
            target_node_id=endpoints["target_node_id"],
            species=evidence["species"], scope=scope),
        "species": evidence["species"],
        "endpoints": endpoints,
        "scope": scope,
        "role": evidence["role"],
        "lifecycle": evidence["lifecycle"],
        "evidence_lineage": {
            "proposal_id": proposed_row["proposal_id"],
            "fact_id": source_evidence["fact_id"],
            "fact_revision": source_evidence["fact_revision"],
            "source_sha256": source_evidence["edition"]["source_sha256"],
            "span_text_sha256": source_evidence["span"]["text_sha256"],
            "owner_bindings": {
                "spec": bindings["spec"],
                "purpose": bindings["purpose"],
                "adoption": bindings["adoption"],
            },
        },
        "use_qualification": {"graph_membership_use": use["graph_membership_use"]},
        "curation": {
            "curator": curation["curator"],
            "decision": curation["decision"],
            "decided_at": curation["decided_at"],
            "receipt_sha256": curation["receipt_sha256"],
        },
        "observation": None,
        "supersedes_event_sha256": None,
        "clocks": {
            "knowledge_at": knowledge_at,
            "effective_at": effective_at_from_evidence(evidence["clocks"]["effective"]),
            "recorded_at": recorded_at,
        },
    }
    event["event_sha256"] = materialize.activity_history_event_digest(event)
    event["event_id"] = "actevt:" + event["event_sha256"][:24]
    try:
        materialize.validate_activity_history_event(event)
    except materialize.ActivityHistoryRefusal as exc:
        raise BridgeRefusal("EVENT_INVALID", str(exc)) from None
    if recorded < probation._activity_zoned(knowledge_at):
        raise BridgeRefusal("RECORDED_BEFORE_KNOWLEDGE",
                            f"recorded_at {recorded_at} precedes knowledge_at {knowledge_at}")
    return event


# ---------------------------------------------------------------------------
# Planning (pure over the ledger rows + events; reads only the receipt files)
# ---------------------------------------------------------------------------

def _fold(events: list[dict], *, knowledge_cutoff: str) -> dict:
    """The materialize owner's fold, one indirection so the verdict is observable."""
    return materialize.apply_activity_membership_events(
        events, knowledge_cutoff=knowledge_cutoff)


def _decision(pid, proposed_row, *, outcome, reason_code=None, use=None, event=None,
              fold_verdict=None) -> dict:
    use = use or {}
    return {
        "proposal_id": pid,
        "proposal_sha256": None if proposed_row is None else proposal_sha256(proposed_row),
        "outcome": outcome,
        "reason_code": reason_code,
        "graph_membership_use": use.get("graph_membership_use"),
        "event": event,
        "use_ruling_path": use.get("ruling_path"),
        "use_ruling_sha256": use.get("ruling_sha256"),
        "ruling_refusals": list(use.get("refusals") or []),
        "fold_verdict": fold_verdict,
    }


def _decide_ratified(pid, proposed, terminal, *, receipts_dir, ruling_paths,
                     recorded_at, existing_events, allow_fixture) -> dict:
    use = qualify_graph_membership_use(proposed, ruling_paths,
                                       allow_fixture=allow_fixture)
    def refused(code, fold_verdict=None):
        return _decision(pid, proposed, outcome="REFUSED", reason_code=code,
                         use=use, event=None, fold_verdict=fold_verdict)

    try:
        event = build_append_event(proposed, terminal, use, recorded_at=recorded_at)
    except BridgeRefusal as exc:
        return refused(exc.code)
    # Idempotency, keyed (proposal_id, graph_membership_use), against the events file.
    for existing in existing_events:
        if not isinstance(existing, dict) or existing.get("action") != "APPEND":
            continue
        lineage = existing.get("evidence_lineage") or {}
        qualified = existing.get("use_qualification") or {}
        if (lineage.get("proposal_id") == pid
                and qualified.get("graph_membership_use") == use["graph_membership_use"]):
            if existing.get("event_sha256") == event["event_sha256"]:
                return _decision(pid, proposed, outcome="SKIPPED",
                                 reason_code="ALREADY_BRIDGED", use=use, event=event)
            return refused("EVENT_KEY_CONFLICT")
    try:
        check_curation_receipt(proposed, terminal,
                               read_curation_receipt_bytes(receipts_dir, pid))
    except BridgeRefusal as exc:
        return _decision(pid, proposed, outcome="REFUSED", reason_code=exc.code,
                         use=use, event=event)
    try:
        fold = _fold(list(existing_events) + [event],
                     knowledge_cutoff=event["clocks"]["knowledge_at"])
    except materialize.ActivityHistoryRefusal as exc:
        return _decision(pid, proposed, outcome="REFUSED", reason_code="FOLD_REFUSED",
                         use=use, event=event, fold_verdict=exc.code)
    believed = [b for b in fold["current"]
                if b["membership_id"] == event["membership_id"]
                and b["event_sha256"] == event["event_sha256"]]
    if believed:
        return _decision(pid, proposed, outcome="APPEND",
                         reason_code="GRAPH_MEMBERSHIP_USE_GRANTED", use=use, event=event)
    rows = [r for r in fold["refused"] if r["event_sha256"] == event["event_sha256"]]
    verdict = rows[0]["reason"] if rows else None
    if use["graph_membership_use"] != "GRANTED":
        if verdict != "GRAPH_MEMBERSHIP_USE_NOT_GRANTED":
            return _decision(pid, proposed, outcome="REFUSED",
                             reason_code="FOLD_VERDICT_UNEXPECTED", use=use, event=event,
                             fold_verdict=verdict)
        return _decision(pid, proposed, outcome="HELD",
                         reason_code="GRAPH_MEMBERSHIP_USE_NOT_GRANTED", use=use,
                         event=event, fold_verdict=verdict)
    return _decision(pid, proposed, outcome="REFUSED", reason_code="FOLD_REFUSED",
                     use=use, event=event, fold_verdict=verdict)


def plan_bridge(ledger_rows: list[dict], *, receipts_dir, ruling_paths, recorded_at: str,
                existing_events: list[dict], allow_fixture: bool = False) -> list[dict]:
    """One bridge decision per ``proposal_id``, sorted by ``proposal_id``.

    Outcomes: SKIPPED (awaiting curation, rejected, already bridged), HELD (ratified
    but graph-membership use not granted — no event), APPEND (granted and the fold
    accepts the event as current belief), REFUSED (a typed code; the caller writes
    nothing for that run). Reads only the curation receipt files under
    ``receipts_dir``; the ledger and the events file are caller-supplied.
    """
    rows_by_pid: dict[str, list[dict]] = {}
    for row in ledger_rows:
        rows_by_pid.setdefault(str(row.get("proposal_id")), []).append(row)
    decisions = []
    for pid in sorted(rows_by_pid):
        rows = rows_by_pid[pid]
        proposed = next((r for r in rows if r.get("status") == "PROPOSED"), None)
        terminals = [r for r in rows if r.get("status") in {"RATIFIED", "REJECTED"}]
        if proposed is None:
            decisions.append(_decision(pid, rows[0], outcome="REFUSED",
                                       reason_code="LEDGER_PROPOSAL_MISSING"))
        elif len(terminals) > 1:
            decisions.append(_decision(pid, proposed, outcome="REFUSED",
                                       reason_code="CURATION_AMBIGUOUS"))
        elif not terminals:
            decisions.append(_decision(pid, proposed, outcome="SKIPPED",
                                       reason_code="AWAITING_CURATION"))
        elif terminals[0].get("status") == "REJECTED":
            decisions.append(_decision(pid, proposed, outcome="SKIPPED",
                                       reason_code="PROPOSAL_REJECTED"))
        else:
            decisions.append(
                _decide_ratified(pid, proposed, terminals[0], receipts_dir=receipts_dir,
                                 ruling_paths=ruling_paths, recorded_at=recorded_at,
                                 existing_events=existing_events,
                                 allow_fixture=allow_fixture))
    return decisions


# ---------------------------------------------------------------------------
# The two explicit I/O surfaces: reading and appending the bridge's own JSONL files
# ---------------------------------------------------------------------------

def _read_jsonl(path, code: str) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    out: list[dict] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception as exc:  # noqa: BLE001 — a torn line is a file refusal
            raise BridgeRefusal(code, f"line {lineno}: {exc}") from None
        if not isinstance(row, dict):
            raise BridgeRefusal(code, f"line {lineno}: not an object")
        out.append(row)
    return out


def read_events(path) -> list[dict]:
    """The activity history events file; missing -> []. Malformed -> EVENTS_FILE_INVALID."""
    return _read_jsonl(path, "EVENTS_FILE_INVALID")


def read_bridge_receipts(path) -> list[dict]:
    """The bridge receipts file; missing -> []. Malformed -> BRIDGE_RECEIPTS_FILE_INVALID."""
    return _read_jsonl(path, "BRIDGE_RECEIPTS_FILE_INVALID")


def _bridge_receipt_row_problems(row: dict) -> list[str]:
    if not isinstance(row, dict) or set(row) != _BRIDGE_RECEIPT_KEYS:
        missing = sorted(_BRIDGE_RECEIPT_KEYS - set(row or {}))
        extra = sorted(set(row or {}) - _BRIDGE_RECEIPT_KEYS)
        return [f"closed key set violated (missing {missing}, unexpected {extra})"]

    def sha_ok(value):
        return isinstance(value, str) and len(value) == 64 and value == value.lower()

    problems = []
    if row["schema"] != BRIDGE_RECEIPT_SCHEMA:
        problems.append(f"schema is {row['schema']!r}")
    if not probation._activity_zoned(row["recorded_at"]):
        problems.append("recorded_at is not a zoned instant")
    if not sha_ok(row["proposal_sha256"]) or not sha_ok(row["curation_receipt_sha256"]):
        problems.append("proposal_sha256 / curation_receipt_sha256 must be sha256 hex")
    if row["outcome"] not in {"SKIPPED", "HELD", "APPEND", "REFUSED"}:
        problems.append(f"outcome {row['outcome']!r}")
    if row["graph_membership_use"] not in {"GRANTED", "NOT_GRANTED", None}:
        problems.append(f"graph_membership_use {row['graph_membership_use']!r}")
    if row["event_id"] is not None and not str(row["event_id"]).startswith("actevt:"):
        problems.append(f"event_id {row['event_id']!r}")
    if row["event_sha256"] is not None and not sha_ok(row["event_sha256"]):
        problems.append("event_sha256 must be sha256 hex or null")
    if row["reason_code"] is not None and not isinstance(row["reason_code"], str):
        problems.append("reason_code must be a string or null")
    if not isinstance(row["ruling_refusals"], list):
        problems.append("ruling_refusals must be a list")
    return problems


def _bridge_receipt_row(decision: dict, *, recorded_at: str) -> dict:
    event = decision.get("event")
    is_append = decision.get("outcome") == "APPEND"
    row = {
        "schema": BRIDGE_RECEIPT_SCHEMA,
        "proposal_id": decision.get("proposal_id"),
        "proposal_sha256": decision.get("proposal_sha256"),
        "outcome": decision.get("outcome"),
        "reason_code": decision.get("reason_code"),
        "graph_membership_use": decision.get("graph_membership_use"),
        "event_id": event.get("event_id") if is_append and event else None,
        "event_sha256": event.get("event_sha256") if is_append and event else None,
        "curation_receipt_sha256": (event["curation"]["receipt_sha256"] if event else None),
        "use_ruling_path": decision.get("use_ruling_path"),
        "use_ruling_sha256": decision.get("use_ruling_sha256"),
        "ruling_refusals": decision.get("ruling_refusals"),
        "recorded_at": recorded_at,
    }
    problems = _bridge_receipt_row_problems(row)
    if problems:
        raise BridgeRefusal("BRIDGE_RECEIPT_INVALID",
                            f"{row.get('proposal_id')}: {problems[0]}")
    return row


def plan_counts(plan: list[dict], *, existing_events: list[dict],
                existing_receipts: list[dict]) -> dict:
    """What the plan WOULD write now: new APPEND events, new receipt rows, skipped."""
    existing_shas = {e.get("event_sha256") for e in existing_events}
    seen = {(r.get("proposal_id"), r.get("graph_membership_use"), r.get("outcome"))
            for r in existing_receipts}
    appended = receipt_rows = skipped = 0
    for decision in plan:
        outcome = decision.get("outcome")
        if outcome == "APPEND":
            event = decision.get("event") or {}
            if event.get("event_sha256") in existing_shas:
                skipped += 1
            else:
                appended += 1
                existing_shas.add(event.get("event_sha256"))
            key = (decision.get("proposal_id"), decision.get("graph_membership_use"), "APPEND")
            if key not in seen:
                receipt_rows += 1
                seen.add(key)
        elif outcome == "HELD":
            key = (decision.get("proposal_id"), decision.get("graph_membership_use"), "HELD")
            if key not in seen:
                receipt_rows += 1
                seen.add(key)
            else:
                skipped += 1
        else:
            skipped += 1
    return {"appended_events": appended, "receipt_rows": receipt_rows, "skipped": skipped}


def _append_jsonl(path: Path, rows: list[dict], *, code: str) -> int:
    """Append rows as canonical JSONL; existing bytes are a prefix, never rewritten."""
    if not rows:
        return 0
    old = path.read_bytes() if path.exists() else b""
    if old and not old.endswith(b"\n"):
        raise BridgeRefusal(code, f"{path} does not end with a newline")
    payload = old + b"".join(
        probation._activity_canonical(row).encode("utf-8") + b"\n" for row in rows)
    assert payload.startswith(old), "an append must never rewrite existing bytes"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return len(rows)


def apply_plan(plan: list[dict], *, events_path, receipts_path, recorded_at: str) -> dict:
    """Write the plan: ONLY APPEND events, plus one bridge receipt row per new
    (proposal_id, graph_membership_use, outcome) key among APPEND/HELD decisions.

    Returns counts {appended_events, receipt_rows, skipped}. REFUSED decisions are
    never handed here by the CLI (it exits 3 first); defensively they write nothing.
    """
    events_path, receipts_path = Path(events_path), Path(receipts_path)
    existing = read_events(events_path)
    receipts = read_bridge_receipts(receipts_path)
    counts = plan_counts(plan, existing_events=existing, existing_receipts=receipts)
    existing_shas = {e.get("event_sha256") for e in existing}
    seen = {(r.get("proposal_id"), r.get("graph_membership_use"), r.get("outcome"))
            for r in receipts}
    new_events: list[dict] = []
    new_receipts: list[dict] = []
    for decision in plan:
        outcome = decision.get("outcome")
        if outcome == "APPEND":
            event = decision.get("event")
            if event is None:
                raise BridgeRefusal("BRIDGE_RECEIPT_INVALID",
                                    "an APPEND decision carries no event")
            if event["event_sha256"] not in existing_shas:
                new_events.append(event)
                existing_shas.add(event["event_sha256"])
        if outcome in {"APPEND", "HELD"}:
            row = _bridge_receipt_row(decision, recorded_at=recorded_at)
            key = (row["proposal_id"], row["graph_membership_use"], row["outcome"])
            if key not in seen:
                new_receipts.append(row)
                seen.add(key)
    appended = _append_jsonl(events_path, new_events, code="EVENTS_FILE_INVALID")
    written = _append_jsonl(receipts_path, new_receipts, code="BRIDGE_RECEIPTS_FILE_INVALID")
    assert appended == counts["appended_events"], "event write must match the count"
    assert written == counts["receipt_rows"], "receipt write must match the count"
    return counts
