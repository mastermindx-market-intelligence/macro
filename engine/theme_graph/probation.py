"""The probation queue — proposals waiting on a curated ratification act (W3A §4).

NOTHING IN HERE IS PRODUCTION VOCABULARY. A proposal is a machine saying "these two
things look related" or "this key may have been renamed"; the graph build ignores every
row whose ``status`` is not ``ratified``, and W3A ratifies nothing. That is the whole
point: G0.13 forbids promoting a string or overlap statistic into an edge, so the
statistic lands here with its evidence and a human decides later — or never.

The file is APPEND-ONLY JSONL and rows are keep-FIRST on ``proposal_id``, which is a
deterministic hash of the proposal's SUBJECT. Re-running a proposer therefore re-proposes
nothing: the same finding on the same subject is the same row, and a curator's decision
on it is never overwritten by a later run that happened to see the same overlap again.

Ratification is a CURATED act. This module deliberately ships no ``ratify()``: the way a
row becomes ratified is a human editing it (or a delegated curation session doing so
under its own receipt), and a helper that flipped the field would be the exact
auto-promotion path the queue exists to prevent.
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

log = logging.getLogger(__name__)

#: What a proposal can ask for. ``identity_continuity`` (a suspected ticker rename) and
#: ``key_rename`` (a suspected source-key rename) come from the refresh path; the rest
#: from the coverage-gap and overlap diagnostics.
PROPOSAL_KINDS: frozenset[str] = frozenset({
    "new_theme", "merge", "split", "mapping", "key_rename", "identity_continuity",
})

PROPOSED_BY: frozenset[str] = frozenset({
    "coverage_gap", "overlap_stats", "refresh_identity", "llm_proposed",
})

STATUSES: frozenset[str] = frozenset({"proposed", "ratified", "rejected"})

ROW_FIELDS: tuple[str, ...] = (
    "proposal_id", "kind", "subject", "evidence", "evidence_refs", "proposed_by",
    "created", "status", "ratified_by", "adjudicated_at", "note", "adjudication_note",
)


def utc_now_stamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z")


def _parse_stamp(value: object, field: str) -> datetime:
    """Compare decision clocks in UTC, including legacy unzoned/date-only rows."""
    text = str(value or "").strip()
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        stamp = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc)


def proposal_id(kind: str, subject: dict) -> str:
    """Deterministic id from (kind, subject). The same finding is the same row."""
    payload = json.dumps({"kind": str(kind), "subject": subject},
                         ensure_ascii=False, sort_keys=True, default=str)
    return "prop:" + hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def make_proposal(*, kind: str, subject: dict, evidence: dict | None = None,
                  evidence_refs: list[str] | None = None, proposed_by: str,
                  created: str | None = None, note: str | None = None) -> dict:
    """A well-formed, UNRATIFIED proposal row. Refuses an unknown kind or proposer."""
    if kind not in PROPOSAL_KINDS:
        raise ValueError(f"unknown proposal kind {kind!r}; known: {sorted(PROPOSAL_KINDS)}")
    if proposed_by not in PROPOSED_BY:
        raise ValueError(
            f"unknown proposer {proposed_by!r}; known: {sorted(PROPOSED_BY)} — a "
            f"proposal whose origin is not named cannot be audited later")
    return {
        "proposal_id": proposal_id(kind, subject),
        "kind": kind,
        "subject": dict(subject),
        "evidence": dict(evidence or {}),
        "evidence_refs": list(evidence_refs or []),
        "proposed_by": proposed_by,
        "created": created or utc_now_stamp(),
        # Written as PROPOSED, always. A proposer cannot mint a ratified row.
        "status": "proposed",
        "ratified_by": None,
        "adjudicated_at": None,
        "note": note,
        "adjudication_note": None,
    }


def validate(row: dict) -> list[str]:
    """Structural problems with one row, empty when it is well-formed."""
    out: list[str] = []
    for field in ("proposal_id", "kind", "proposed_by", "created", "status"):
        if not str(row.get(field) or "").strip():
            out.append(f"missing {field}")
    if row.get("kind") and row["kind"] not in PROPOSAL_KINDS:
        out.append(f"kind {row['kind']!r} outside {sorted(PROPOSAL_KINDS)}")
    if row.get("proposed_by") and row["proposed_by"] not in PROPOSED_BY:
        out.append(
            f"proposed_by {row['proposed_by']!r} outside {sorted(PROPOSED_BY)}"
        )
    status = str(row.get("status") or "")
    if status and status not in STATUSES:
        out.append(f"status {status!r} outside {sorted(STATUSES)}")
    ratified_by = str(row.get("ratified_by") or "").strip()
    adjudicated_at = str(row.get("adjudicated_at") or "").strip()
    if status == "ratified" and not ratified_by:
        out.append("status=ratified with no ratified_by — ratification names its author")
    if status != "ratified" and ratified_by:
        out.append("ratified_by set on a row that is not ratified")
    if status in {"ratified", "rejected"} and not adjudicated_at:
        out.append(f"status={status} with no adjudicated_at — decisions name their clock")
    if status == "proposed" and adjudicated_at:
        out.append("adjudicated_at set on a row that is still proposed")

    decision_note = row.get("adjudication_note")
    if decision_note is not None and not isinstance(decision_note, str):
        out.append("adjudication_note must be text or null")
    if status == "proposed" and decision_note is not None:
        out.append("adjudication_note set on a row that is still proposed")

    created_clock = None
    if str(row.get("created") or "").strip():
        try:
            created_clock = _parse_stamp(row.get("created"), "created")
        except ValueError as exc:
            out.append(str(exc))
    adjudicated_clock = None
    if adjudicated_at:
        try:
            adjudicated_clock = _parse_stamp(adjudicated_at, "adjudicated_at")
        except ValueError as exc:
            out.append(str(exc))
    if (
        created_clock is not None
        and adjudicated_clock is not None
        and adjudicated_clock < created_clock
    ):
        out.append("adjudicated_at predates created")
    return out


@lru_cache(maxsize=1)
def _contract_validator():
    """Use the existing proposal schema; this is not a second curation contract."""
    import jsonschema
    path = Path(__file__).resolve().parents[2] / "contracts/theme_graph/probation_proposal.v1.schema.json"
    return jsonschema.Draft202012Validator(json.loads(path.read_text(encoding="utf-8")))


def require_valid_rows(rows: list[dict]) -> None:
    """Fail closed before selection, so damaged objects cannot look like absence.

    Syntax-only strict reading and the legacy forgiving default remain unchanged.
    This guard is for complete research-consumer snapshots, not queue mutation.
    """
    import jsonschema
    seen: set[str] = set()
    for position, row in enumerate(rows, start=1):
        try:
            _contract_validator().validate(row)
            json.dumps(row, allow_nan=False)
        except (jsonschema.ValidationError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid probation proposal at row {position}") from exc
        errors = validate(row)
        if errors:
            raise ValueError(f"invalid probation proposal at row {position}: {errors}")
        if row["proposal_id"] != proposal_id(row["kind"], row["subject"]):
            raise ValueError(f"probation proposal identity payload mismatch at row {position}")
        if row["proposal_id"] in seen:
            raise ValueError(f"duplicate probation proposal identity at row {position}")
        seen.add(row["proposal_id"])


def _unique_proposal_object(pairs):
    """Reject ambiguous keys at every object depth in strict JSONL reads."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_proposals(path: Path, *, strict: bool = False) -> list[dict]:
    """Read rows oldest first, retaining the legacy forgiving default.

    Strict consumers distinguish a missing file from an empty queue and refuse
    malformed, duplicate-key or non-object rows rather than silently dropping them.
    Proposal contract validation remains with the existing owner/consumer.
    """
    if not strict and not path.exists():
        return []
    out: list[dict] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line, object_pairs_hook=_unique_proposal_object if strict else None)
        except Exception as exc:  # noqa: BLE001 — preserve the legacy forgiving reader
            if strict:
                raise ValueError(f"{path.name} line {lineno}: {exc}") from exc
            log.warning("theme_graph.probation: %s line %d unparseable — skipped",
                        path.name, lineno)
            continue
        if isinstance(row, dict):
            out.append(row)
        elif strict:
            raise ValueError(f"{path.name} line {lineno}: proposal row must be a JSON object")
    return out


def ratified(rows: list[dict]) -> list[dict]:
    """The rows a build may act on. Everything else is a suggestion, not a fact."""
    return [r for r in rows if str(r.get("status")) == "ratified"
            and str(r.get("ratified_by") or "").strip()
            and str(r.get("adjudicated_at") or "").strip()]


def append_proposals(rows: list[dict], path: Path) -> tuple[int, int]:
    """Append new rows keep-FIRST on ``proposal_id``. Returns ``(appended, skipped)``.

    Never rewrites the file: existing bytes stay exactly as they are, so a curator's
    edits to earlier rows survive every later proposer run.
    """
    bad = [(r.get("proposal_id"), errs) for r in rows if (errs := validate(r))]
    if bad:
        raise ValueError(f"refusing to append malformed proposals: {bad[:3]}")
    known = {str(r.get("proposal_id")) for r in read_proposals(path)}
    fresh = [r for r in rows if str(r.get("proposal_id")) not in known]
    skipped = len(rows) - len(fresh)
    if not fresh:
        return 0, skipped
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in fresh:
            fh.write(json.dumps({k: row.get(k) for k in ROW_FIELDS},
                                ensure_ascii=False, sort_keys=True) + "\n")
    return len(fresh), skipped


# Explicit lifecycle events use a SEPARATE version-selected input. Legacy v1
# proposals, ids, schema and default readers above remain unchanged.
_RELATION_EVENT_SEAL = object()


class AcceptedRelationEvent:
    """Immutable validated receipt; authentication belongs to the trusted owner reader."""
    __slots__ = ("_json", "_seal", "_authority_json", "_owner_reader")

    def __init__(self, receipt: dict, *, authority_receipt=None, owner_reader=None, _seal=None):
        if _seal is not _RELATION_EVENT_SEAL:
            raise ValueError("relation event requires probation owner admission")
        object.__setattr__(self, "_json", json.dumps(receipt, sort_keys=True, allow_nan=False))
        object.__setattr__(self, "_seal", _seal)
        object.__setattr__(self, "_authority_json", json.dumps(authority_receipt, sort_keys=True, allow_nan=False))
        object.__setattr__(self, "_owner_reader", owner_reader)

    @property
    def authority_receipt(self) -> dict:
        return json.loads(self._authority_json)

    def __setattr__(self, name, value):
        raise AttributeError("accepted relation receipt is immutable")

    @property
    def receipt(self) -> dict:
        return json.loads(self._json)


class RelationEventRefusal(ValueError):
    """Version/action/source/clock/rights input cannot authorize a lifecycle act."""


def relation_event_digest(row: dict) -> str:
    payload = {key: value for key, value in row.items()
               if key not in {"event_id", "event_sha256"}}
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def relation_source_receipt(source_path: Path) -> dict:
    """Read the actual incumbent curated source; strings labelled accepted do not bind."""
    import yaml

    raw = source_path.read_bytes()
    doc = yaml.safe_load(raw)
    if not isinstance(doc, dict) or not isinstance(doc.get("themes"), list):
        raise RelationEventRefusal("curated source is unavailable/malformed")
    version = doc.get("date") or doc.get("updated")
    if not isinstance(version, str) or len(version) != 10:
        raise RelationEventRefusal("curated source version unavailable")
    try:
        datetime.strptime(version, "%Y-%m-%d")
    except ValueError as exc:
        raise RelationEventRefusal("invalid curated source version") from exc
    sha = hashlib.sha256(raw).hexdigest()
    return {"source_ref": "config/theme_crosswalk.yml", "version": version,
            "sha256": sha, "revision": f"crosswalk:{version}:{sha}"}


def _relation_clock(value: str) -> datetime:
    # This contract requires actual zoned instants; never use the v1 permissive
    # date/unzoned parser to fabricate midnight knowledge for an event.
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise RelationEventRefusal("relation clock must be zoned")
    return stamp.astimezone(timezone.utc)


def _require_relation_rights(row: dict) -> None:
    from engine.theme_graph import rights

    prior = row["prior_relation"]
    for node in [prior["src"], prior["dst"], row["new_destination"]]:
        if node is None:
            continue
        family = (rights.family_for_source_ref(row["source_receipt"]["source_ref"])
                  if node.startswith("theme:") else rights.family_for_node_id(node))
        if family is None:
            raise RelationEventRefusal("relation endpoint rights family unavailable")
        rights.rights_class(family)
        if rights.licensing_for_family(family)[0] is not True:
            raise RelationEventRefusal("relation internal use refused")
    rights.rights_class("mastermind_curated")
    if rights.licensing_for_family("mastermind_curated")[0] is not True:
        raise RelationEventRefusal("curation internal use refused")


_HEX64 = re.compile(r"^[a-f0-9]{64}$")


class RelationActionOwnerReader:
    """Narrow read-only resolver over the probation owner's own append-only relation-event ledger. Resolves an explicit ratified row by event_sha256; never writes; never infers."""

    OWNER = "theme_graph.probation"
    SCHEMA = "gmi.probation_owner_action_read/v1"

    def __init__(self, ledger_path):
        self._ledger_path = Path(ledger_path)

    def _refusal(self, status: str, reason: str) -> dict:
        return {"schema": self.SCHEMA, "owner": self.OWNER, "status": status,
                "receipt_ref": None, "reason": reason}

    def _parse_cutoff(self, knowledge_cutoff):
        if knowledge_cutoff is None:
            return None
        try:
            if isinstance(knowledge_cutoff, str):
                return _relation_clock(knowledge_cutoff)
            if isinstance(knowledge_cutoff, datetime):
                if knowledge_cutoff.tzinfo is None:
                    return None
                return knowledge_cutoff.astimezone(timezone.utc)
        except (RelationEventRefusal, ValueError, TypeError):
            return None
        return None

    def _not_ratified(self, field: str) -> dict:
        return self._refusal("UNAVAILABLE",
                             f"relation action not ratified by the curator path: {field}")

    def read_relation_action(self, *, event_sha256, knowledge_cutoff) -> dict:
        if not isinstance(event_sha256, str) or not _HEX64.match(event_sha256):
            return self._refusal("UNAVAILABLE", "malformed resolver request")
        cutoff = self._parse_cutoff(knowledge_cutoff)
        if cutoff is None:
            return self._refusal("UNAVAILABLE", "malformed resolver request")

        if not self._ledger_path.exists():
            return self._refusal("UNAVAILABLE", "owner ledger absent")

        matches: list[dict] = []
        try:
            lines = self._ledger_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return self._refusal("UNAVAILABLE", "owner ledger absent")

        for line in lines:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                return self._refusal("STALE", "owner ledger line unreadable")
            if not isinstance(row, dict):
                return self._refusal("STALE", "owner ledger line unreadable")
            if row.get("event_sha256") == event_sha256:
                matches.append(row)

        if not matches:
            return self._refusal("UNAVAILABLE", "no accepted relation action for event")
        if len(matches) > 1:
            return self._refusal("STALE", "duplicate ledger rows for event")

        row = matches[0]
        if relation_event_digest(row) != event_sha256:
            return self._refusal("STALE", "receipt digest mismatch")
        if row.get("event_id") != "relation-event:" + event_sha256:
            return self._refusal("STALE", "receipt identity mismatch")

        if row.get("schema") != "gmi.probation_relation_event/v2":
            return self._not_ratified("schema")
        if row.get("status") != "ratified":
            return self._not_ratified("status")
        ratified_by = row.get("ratified_by")
        if not isinstance(ratified_by, str) or not ratified_by.strip():
            return self._not_ratified("ratified_by")
        for clock_field in ("adjudicated_at", "known_at", "created_at"):
            try:
                _relation_clock(row[clock_field])
            except (KeyError, RelationEventRefusal, TypeError):
                return self._not_ratified(clock_field)
        if row.get("action") not in {"RELATION_WITHDRAW", "DESTINATION_CHANGE"}:
            return self._not_ratified("action")
        caps = row.get("authority_caps")
        if not isinstance(caps, dict):
            return self._not_ratified("authority_caps")
        for cap_key in ("may_rank", "may_size", "may_gate", "may_escalate"):
            if caps.get(cap_key) is not False:
                return self._not_ratified("authority_caps")
        evidence_refs = row.get("evidence_refs")
        if (not isinstance(evidence_refs, list) or not evidence_refs
                or not all(isinstance(ref, str) and ref for ref in evidence_refs)):
            return self._not_ratified("evidence_refs")

        try:
            created = _relation_clock(row["created_at"])
            adjudicated = _relation_clock(row["adjudicated_at"])
            known = _relation_clock(row["known_at"])
        except (RelationEventRefusal, TypeError):
            return self._not_ratified("clock")

        if created > adjudicated or adjudicated > known:
            return self._refusal("STALE", "receipt chronology violated")
        if known > cutoff:
            return self._refusal("UNAVAILABLE", "relation action not yet knowable at cutoff")

        accepted = {
            "schema": self.SCHEMA,
            "owner": self.OWNER,
            "status": "ACCEPTED",
            "receipt_ref": "data/theme_graph/probation/relation_events.v2.jsonl#"
            + row["event_id"],
            "reason": None,
            "event_sha256": event_sha256,
            "action": row["action"],
            "prior_relation": row["prior_relation"],
            "new_destination": row.get("new_destination"),
            "source_receipt": row["source_receipt"],
            "ratified_by": row["ratified_by"],
            "evidence_refs": list(row["evidence_refs"]),
            "accepted_at": row["adjudicated_at"],
            "known_at": row["known_at"],
            "valid_from": row["adjudicated_at"],
            "valid_to": None,
        }
        return copy.deepcopy(accepted)


def _read_owner_action(reader, row: dict, *, emitted_at: str) -> dict:
    """Consume an authenticated incumbent reader capability, never source assertions.

    No such resolver is wired in the normal builder. Injection is a trusted owner
    interface, not data granting itself authority; controlled test implementations
    explicitly stand in for that missing capability and prove no natural acceptance.
    """
    import jsonschema

    if reader is None:
        raise RelationEventRefusal("OWNER_ACTION_AUTHORITY_UNAVAILABLE: incumbent resolver unwired")
    try:
        receipt = reader.read_relation_action(
            event_sha256=row["event_sha256"], knowledge_cutoff=emitted_at)
    except Exception as exc:
        raise RelationEventRefusal("OWNER_ACTION_AUTHORITY_UNAVAILABLE: owner read failed") from exc
    contract = Path(__file__).resolve().parents[2] / (
        "contracts/theme_graph/probation_relation_event.v2.schema.json")
    schema = json.loads(contract.read_text())["$defs"]["owner_action_read"]
    try:
        jsonschema.Draft202012Validator(schema).validate(receipt)
    except jsonschema.ValidationError as exc:
        raise RelationEventRefusal("OWNER_ACTION_AUTHORITY_INVALID: malformed owner receipt") from exc
    status = receipt["status"]
    if status != "ACCEPTED":
        raise RelationEventRefusal("OWNER_ACTION_AUTHORITY_" + status + ": " + receipt["reason"])
    if not receipt["receipt_ref"].strip():
        raise RelationEventRefusal("OWNER_ACTION_AUTHORITY_INVALID: empty owner receipt reference")
    for field in ("event_sha256", "action", "prior_relation", "new_destination",
                  "source_receipt", "ratified_by", "evidence_refs"):
        if receipt[field] != row[field]:
            raise RelationEventRefusal("OWNER_ACTION_AUTHORITY_MISMATCH: " + field)
    accepted = _relation_clock(receipt["accepted_at"])
    known = _relation_clock(receipt["known_at"])
    valid_from = _relation_clock(receipt["valid_from"])
    valid_to = _relation_clock(receipt["valid_to"]) if receipt["valid_to"] is not None else None
    emitted = _relation_clock(emitted_at)
    if (accepted != _relation_clock(row["adjudicated_at"]) or accepted > known
            or known > _relation_clock(row["known_at"]) or known > emitted
            or valid_from > accepted or valid_from > emitted
            or (valid_to is not None and valid_to <= emitted)):
        raise RelationEventRefusal("OWNER_ACTION_AUTHORITY_CLOCK_REFUSAL")
    return receipt


def read_relation_events(path: Path, *, source_path: Path,
                         emitted_at: str, owner_action_reader=None) -> list[AcceptedRelationEvent]:
    """Strict accepted-event owner read; no writer, ratifier, mixed queue or ledger.

    An absent optional event input means no lifecycle act was supplied; it is not
    a complete relation-population observation and authorizes no withdrawals.
    """
    import jsonschema
    from engine.theme_graph import rights

    if not path.exists():
        return []
    source = relation_source_receipt(source_path)
    emitted = _relation_clock(emitted_at)
    contract = Path(__file__).resolve().parents[2] / (
        "contracts/theme_graph/probation_relation_event.v2.schema.json")
    validator = jsonschema.Draft202012Validator(json.loads(contract.read_text()))
    result = []
    seen = set()
    for row in read_proposals(path, strict=True):
        try:
            validator.validate(row)
            digest = relation_event_digest(row)
            if row["event_sha256"] != digest or row["event_id"] != "relation-event:" + digest:
                raise RelationEventRefusal("relation event digest/identity mismatch")
            if row["event_id"] in seen:
                raise RelationEventRefusal("duplicate relation event")
            seen.add(row["event_id"])
            if row["source_receipt"] != source:
                raise RelationEventRefusal("relation event curation revision mismatch")
            prior = row["prior_relation"]
            expected = f"expresses:{prior['src']}->{prior['dst']}@{prior['valid_from']}"
            if prior["edge_id"] != expected:
                raise RelationEventRefusal("relation identity mismatch")
            datetime.strptime(prior["valid_from"], "%Y-%m-%d")
            created = _relation_clock(row["created_at"])
            known = _relation_clock(row["known_at"])
            adjudicated = _relation_clock(row["adjudicated_at"])
            effective = _relation_clock(row["effective_at"])
            if created > adjudicated or known != adjudicated or known > emitted or effective > emitted:
                raise RelationEventRefusal("relation event chronology/future refusal")
            if source["version"] > known.date().isoformat():
                raise RelationEventRefusal("curation source version not yet known")
            if effective.date().isoformat() <= prior["valid_from"]:
                raise RelationEventRefusal("relation event must advance the prior valid window")
            if row["new_destination"] == prior["dst"]:
                raise RelationEventRefusal("destination change must change destination")
            # Current per-use licensing comes only from the incumbent registry.
            if not row["ratified_by"].strip():
                raise RelationEventRefusal("relation ratifier unavailable")
            _require_relation_rights(row)
        except (jsonschema.ValidationError, ValueError, rights.RightsRefusal) as exc:
            raise RelationEventRefusal(str(exc)) from exc
        authority_receipt = _read_owner_action(owner_action_reader, row, emitted_at=emitted_at)
        result.append(AcceptedRelationEvent(row, authority_receipt=authority_receipt,
                                           owner_reader=owner_action_reader, _seal=_RELATION_EVENT_SEAL))
    return result


def require_daily_relation_event(event: AcceptedRelationEvent, *, belief_time: str,
                                 emitted_at: str) -> dict:
    """Refuse precision the daily graph cannot represent; do not ceil an effect."""
    if not isinstance(event, AcceptedRelationEvent) or event._seal is not _RELATION_EVENT_SEAL:
        raise RelationEventRefusal("unadmitted relation event")
    row = event.receipt
    current_authority = _read_owner_action(event._owner_reader, row, emitted_at=emitted_at)
    if current_authority != event.authority_receipt:
        raise RelationEventRefusal("OWNER_ACTION_AUTHORITY_CHANGED: re-read differs from accepted receipt")
    _require_relation_rights(row)  # revocation is checked at this actual use too
    effective = _relation_clock(row["effective_at"])
    known = _relation_clock(row["known_at"])
    emitted = _relation_clock(emitted_at)
    if effective.time().isoformat() != "00:00:00":
        raise RelationEventRefusal("DAILY_GRAPH_UNREPRESENTABLE: intraday effective clock")
    day = datetime.strptime(belief_time, "%Y-%m-%d").date()
    if known.date() > day or (known.date() == day and known.time().isoformat() != "00:00:00"):
        raise RelationEventRefusal("DAILY_GRAPH_UNREPRESENTABLE: intraday known clock")
    if known > emitted or effective > emitted or effective.date() > day:
        raise RelationEventRefusal("relation event future relative to graph clocks")
    return row
