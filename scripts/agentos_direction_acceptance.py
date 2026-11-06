"""Pure DRAFT_ONLY recipe for the existing fixed Agent OS Git publisher.

The caller supplies its qualified captured source, original operation lookup
and separately authorized ACCEPT_DIRECTION binding. This compiler reads/writes
nothing and cannot prove either permission, publication or a Runtime action.
It emits exactly WS update + new DEC create + optional predecessor DEC update.
An existing original operation produces only a read-only reconciliation recipe.
"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import re
from pathlib import Path

from scripts import agentos
from scripts import agentos_direction as direction

REQUEST_SCHEMA = "agentos.direction_acceptance_request.v1"
RECIPE_SCHEMA = "agentos.direction_acceptance_recipe.v1"
_REQUEST_KEYS = {"schema", "request_id", "expected_commit", "work_ref", "expected_predecessor", "decision"}
_DECISION_KEYS = {"key", "question", "answer", "rationale", "alternatives", "evidence", "confidence",
                  "reversibility"}
_ERRORS = {"INVALID_REQUEST", "INVALID_SOURCE", "INVALID_DIRECTION", "STALE_SOURCE", "STALE_PREDECESSOR",
           "DECISION_EXISTS", "CONFLICT", "CONTENT_OVER_BUDGET"}


class DirectionRecipeError(ValueError):
    def __init__(self, code):
        if code not in _ERRORS:
            raise ValueError("INVALID_REQUEST")
        self.code = code
        super().__init__(code)


def _require(ok, code="INVALID_REQUEST"):
    if not ok:
        raise DirectionRecipeError(code)


def _json(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, RecursionError, UnicodeError):
        raise DirectionRecipeError("INVALID_REQUEST") from None


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _hex(value, size):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{" + str(size) + "}", value) is not None


def _parse(raw, path, checker):
    _require(type(raw) is bytes and len(raw) <= 262144, "INVALID_SOURCE")
    try:
        text = raw.decode("utf-8")
        class Captured:
            def read_text(self, *, encoding):
                if encoding != "utf-8":
                    raise ValueError()
                return text
        record, body = agentos.parse_record(Captured())
        problems = checker(record, Path(path))
        _require(not any(problem.hard for problem in problems), "INVALID_SOURCE")
        return record, body
    except (UnicodeError, ValueError, TypeError, KeyError, RecursionError):
        raise DirectionRecipeError("INVALID_SOURCE") from None


def _source(source, *, path, raw, commit):
    _require(type(raw) is bytes and len(raw) <= 262144, "INVALID_SOURCE")
    _require(type(source) is dict and set(source) == {"repository", "commit", "path", "content_sha256"}, "INVALID_SOURCE")
    _require(source["repository"] == "mastermindx-market-intelligence/macro" and source["path"] == path
             and source["commit"] == commit and _hex(commit, 40)
             and source["content_sha256"] == _sha(raw), "INVALID_SOURCE")


def _render(record, body):
    # The canonical owner owns parsing/rendering. Derived times and permissions
    # are never minted here; only explicit request/retained record facts survive.
    text = "---\n" + agentos.yaml.safe_dump(record, sort_keys=False, allow_unicode=True) + "---\n" + body
    _require(len(text.encode("utf-8")) <= 262144, "CONTENT_OVER_BUDGET")
    return text


def _workstream_problems(record, path):
    # Existing retained references are preserved byte-for-field in postimages.
    # Their existence warnings belong to the qualified source owner, not this
    # pure recipe. The canonical structural checker receives every other field.
    structural = {k: v for k, v in record.items() if k not in {"artifacts", "owns_paths"}}
    return agentos.check_workstream(structural, path, None)


def compile_acceptance(request, *, captured_commit, workstream_bytes, workstream_source,
                       predecessor_bytes=None, predecessor_source=None,
                       new_decision_absent, permission_binding_digest, decision_actor, decision_date,
                       original_operation=None):
    """Produce inert postimages or original-operation READ_ONLY_RECONCILIATION.

    All keyword inputs are publisher-owned facts, never public request fields.
    The real publisher must independently qualify them, require the distinct
    grant before/after, perform one atomic Git CAS, and reconcile its original
    operation on response loss. A digest is a binding fact, never a grant.
    """
    _require(type(request) is dict and set(request) == _REQUEST_KEYS and request["schema"] == REQUEST_SCHEMA)
    _require(type(request["request_id"]) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", request["request_id"]) is not None)
    _require(_hex(request["expected_commit"], 40) and _hex(captured_commit, 40))
    _require(request["expected_commit"] == captured_commit, "STALE_SOURCE")
    _require(_hex(permission_binding_digest, 64))
    _require(type(decision_actor) is str and decision_actor == decision_actor.strip() and bool(decision_actor)
             and len(decision_actor.encode("utf-8")) <= 256 and not any(ord(c) < 32 for c in decision_actor))
    _require(type(decision_date) is str and re.fullmatch(r"\d{4}-\d{2}-\d{2}", decision_date) is not None, "INVALID_DIRECTION")
    try:
        _require(dt.date.fromisoformat(decision_date).isoformat() == decision_date, "INVALID_DIRECTION")
    except ValueError:
        raise DirectionRecipeError("INVALID_DIRECTION") from None
    work_ref = request["work_ref"]
    _require(type(work_ref) is str and work_ref.startswith("WS:") and 2 <= len(work_ref[3:]) <= 64
             and re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", work_ref[3:]) is not None)
    dec = request["decision"]
    _require(type(dec) is dict and set(dec) == _DECISION_KEYS)
    key = dec["key"]
    _require(type(key) is str and 2 <= len(key) <= 128 and re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", key) is not None)
    ref = "DEC:" + key
    declaration = {"schema": "agentos.direction_acceptance.v1", "state": "ACCEPTED", "work_ref": work_ref,
                   "predecessor": request["expected_predecessor"]}
    try:
        direction.validate_declaration(declaration, work_ref=work_ref, decision_ref=ref)
    except (ValueError, TypeError):
        raise DirectionRecipeError("INVALID_DIRECTION") from None
    request_bytes = _json(request)
    _require(len(request_bytes) <= 32768, "CONTENT_OVER_BUDGET")
    # The actual publisher supplies actor, operation clock and permission
    # binding, then retains them on the original operation. Reconciliation
    # reuses those facts, never a fresh clock or a caller's identity label.
    fingerprint = _sha(_json({"request": request, "permission_binding_digest": permission_binding_digest,
                             "decision_actor": decision_actor, "decision_date": decision_date}))
    operation_id = "mmos-direction-accept-" + _sha(request["request_id"].encode("ascii"))[:40]
    common = {"schema": RECIPE_SCHEMA, "request_id": request["request_id"], "request_sha256": fingerprint,
              "operation_id": operation_id, "work_ref": work_ref, "expected_commit": captured_commit,
              "expected_predecessor": request["expected_predecessor"], "permission_binding_digest": permission_binding_digest}
    if original_operation is not None:
        _require(type(original_operation) is dict and set(original_operation) == {"operation_id", "request_id", "request_sha256"}, "CONFLICT")
        _require(original_operation == {"operation_id": operation_id, "request_id": request["request_id"], "request_sha256": fingerprint}, "CONFLICT")
        return dict(common, state="READ_ONLY_RECONCILIATION", postimages=[])
    _require(type(new_decision_absent) is bool and new_decision_absent, "DECISION_EXISTS")
    ws_path = "agentos/workstreams/WS-" + work_ref[3:] + ".md"
    _source(workstream_source, path=ws_path, raw=workstream_bytes, commit=captured_commit)
    ws, ws_body = _parse(workstream_bytes, ws_path, _workstream_problems)
    _require(ws.get("key") == work_ref[3:], "INVALID_SOURCE")
    old_ref = ws.get("accepted_direction")
    _require(old_ref == request["expected_predecessor"], "STALE_PREDECESSOR")
    old_record = old_body = old_path = None
    if old_ref is None:
        _require(predecessor_bytes is None and predecessor_source is None, "INVALID_SOURCE")
    else:
        old_path = "agentos/decisions/DEC-" + old_ref[4:] + ".md"
        _source(predecessor_source, path=old_path, raw=predecessor_bytes, commit=captured_commit)
        old_record, old_body = _parse(predecessor_bytes, old_path, agentos.check_decision)
        try:
            direction.validate_declaration(old_record.get("direction"), work_ref=work_ref, decision_ref=old_ref)
        except (ValueError, TypeError):
            raise DirectionRecipeError("INVALID_DIRECTION") from None
        _require(old_record.get("key") == old_ref[4:] and "superseded_by" not in old_record
                 and type(old_record.get("affects")) is list and work_ref in old_record["affects"], "INVALID_DIRECTION")
    new_record = copy.deepcopy(dec)
    new_record["decided_by"] = decision_actor
    new_record["decided_at"] = decision_date
    new_record["affects"] = [work_ref]
    new_record["direction"] = declaration
    if old_ref is not None:
        new_record["supersedes"] = [old_ref]
    dec_path = "agentos/decisions/DEC-" + key + ".md"
    _require(not any(p.hard for p in agentos.check_decision(new_record, Path(dec_path))), "INVALID_DIRECTION")
    for field, maximum in (("answer",4096),("rationale",4096),("decided_by",256)):
        _require(type(new_record[field]) is str and bool(new_record[field].strip())
                 and len(new_record[field].encode("utf-8")) <= maximum, "INVALID_DIRECTION")
    _require(type(new_record["decided_at"]) is str and re.fullmatch(r"\d{4}-\d{2}-\d{2}", new_record["decided_at"]) is not None, "INVALID_DIRECTION")
    try:
        _require(dt.date.fromisoformat(new_record["decided_at"]).isoformat() == new_record["decided_at"], "INVALID_DIRECTION")
    except ValueError:
        raise DirectionRecipeError("INVALID_DIRECTION") from None
    ws_next = copy.deepcopy(ws)
    ws_next["accepted_direction"] = ref
    indexed = ws_next.get("decisions", [])
    _require(type(indexed) is list and all(type(v) is str for v in indexed), "INVALID_SOURCE")
    if ref not in indexed:
        indexed = [*indexed, ref]
    ws_next["decisions"] = indexed
    _require(not any(p.hard for p in _workstream_problems(ws_next, Path(ws_path))), "INVALID_DIRECTION")

    def postimage(path, before, text):
        return {"path": path, "expected_sha256": None if before is None else _sha(before),
                "content_sha256": _sha(text.encode("utf-8")), "content_utf8": text}
    images = [postimage(ws_path, workstream_bytes, _render(ws_next, ws_body)),
              postimage(dec_path, None, _render(new_record, "\nAccepted Direction record. Publication and Runtime authorization remain separate.\n"))]
    if old_record is not None:
        previous = copy.deepcopy(old_record)
        previous["superseded_by"] = ref
        images.append(postimage(old_path, predecessor_bytes, _render(previous, old_body)))
    result = dict(common, state="DRAFT_ONLY", postimages=images)
    _require(len(_json(result)) <= 1048576, "CONTENT_OVER_BUDGET")
    return result
