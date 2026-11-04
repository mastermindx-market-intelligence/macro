"""Prepare exact source edit recipes; never publish, authorize, or adopt a plan.

The incumbent publisher supplies its already-captured canonical owner and
immutable snapshots. It must independently verify the distinct ADOPT_PLAN grant,
Git membership/CAS, and original-operation evidence. These functions return
PREVIEW_ONLY data, not permissions or proof that any effect happened.
"""
from __future__ import annotations

import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import re

MACRO = "mastermindx-market-intelligence/macro"
_CODES = frozenset({"INVALID_REQUEST", "INVALID_SNAPSHOT", "SOURCE_BYTES_MISMATCH",
    "WORK_REF_MISMATCH", "STALE_PREDECESSOR", "STALE_PROPOSAL", "STALE_SOURCE",
    "TARGET_CONFLICT", "CANDIDATE_NOT_VERIFIED", "OPERATION_CONFLICT",
    "CONTENT_OVER_BUDGET", "UNSUPPORTED_CANDIDATE"})


class PlanAdoptionError(ValueError):
    def __init__(self, code):
        self.code = code if code in _CODES else "INVALID_SNAPSHOT"
        super().__init__(self.code)


def _fail(code):
    raise PlanAdoptionError(code)


def _closed(value, keys, code):
    if type(value) is not dict or set(value) != set(keys):
        _fail(code)


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def _hex(value, size, code):
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{" + str(size) + "}", value) is None:
        _fail(code)


def _identity(value, maximum, code):
    if type(value) is not str or not value.strip() or len(value) > maximum or any(c in value for c in "\x00\r\n"):
        _fail(code)
    value.encode("utf-8")


class _Record:
    def __init__(self, raw):
        self.raw = raw
    def read_text(self, *, encoding):
        if encoding != "utf-8":
            _fail("INVALID_SNAPSHOT")
        return self.raw.decode("utf-8")


def _body(raw):
    match = re.fullmatch(rb"---(?:\r\n|\n)(.*?)(?:\r\n|\n)---[ \t]*(?:\r\n|\n)?(.*)", raw, re.DOTALL)
    if match is None:
        _fail("INVALID_SNAPSHOT")
    return match.group(2)


def _edit(path, raw, expected):
    return {"path": path, "mode": "100644", "expected_sha256": expected,
            "content_utf8": raw.decode("utf-8"), "content_sha256": _hash(raw)}


def _capture(value, contract, *, path=None, commit=None, macro=False):
    _closed(value, {"source", "raw_bytes"}, "INVALID_SNAPSHOT")
    try:
        ref = contract.bind_source_ref(value["source"], value["raw_bytes"])
    except ValueError:
        _fail("SOURCE_BYTES_MISMATCH")
    if (path is not None and ref["path"] != path) or (commit is not None and ref["commit"] != commit):
        _fail("INVALID_SNAPSHOT")
    if macro and ref["repository"] != MACRO:
        _fail("UNSUPPORTED_CANDIDATE")
    return ref, value["raw_bytes"]


def _target(value, path, commit, contract):
    if type(value) is not dict or value.get("path") != path:
        _fail("INVALID_SNAPSHOT")
    if value.get("state") == "ABSENT":
        _closed(value, {"path", "state"}, "INVALID_SNAPSHOT")
        return None
    _closed(value, {"path", "state", "capture"}, "INVALID_SNAPSHOT")
    if value["state"] != "CAPTURED":
        _fail("INVALID_SNAPSHOT")
    return _capture(value["capture"], contract, path=path, commit=commit, macro=True)


def _actor(value):
    _closed(value, {"principal_id", "decided_by", "decided_at", "decision_rationale"}, "INVALID_REQUEST")
    for name in ("principal_id", "decided_by"):
        _identity(value[name], 256, "INVALID_REQUEST")
    if type(value["decided_at"]) is not str or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value["decided_at"]) is None:
        _fail("INVALID_REQUEST")
    try:
        date.fromisoformat(value["decided_at"])
    except ValueError:
        _fail("INVALID_REQUEST")
    if type(value["decision_rationale"]) is not str or not value["decision_rationale"].strip() or len(value["decision_rationale"]) > 4096:
        _fail("INVALID_REQUEST")
    value["decision_rationale"].encode("utf-8")
    return copy.deepcopy(value)


def _inspect(snapshot, work_ref, owner):
    contract = owner._project_plan_contract()
    _closed(snapshot, {"schema", "repository", "commit", "workstream", "decisions", "proposal", "base",
                       "candidate_target", "decision_target"}, "INVALID_SNAPSHOT")
    if snapshot["schema"] != "agentos.plan_adoption_snapshot.v1" or snapshot["repository"] != MACRO:
        _fail("INVALID_SNAPSHOT")
    _hex(snapshot["commit"], 40, "INVALID_SNAPSHOT")
    ws_path = "agentos/workstreams/WS-" + work_ref[3:] + ".md"
    ws_ref, ws_raw = _capture(snapshot["workstream"], contract, path=ws_path, commit=snapshot["commit"], macro=True)
    ws, _ = owner.parse_record(_Record(ws_raw))
    if ws.get("key") != work_ref[3:]:
        _fail("WORK_REF_MISMATCH")
    if any(p.hard for p in owner.check_workstream(ws, Path(ws_path), None)):
        _fail("INVALID_SNAPSHOT")
    if type(snapshot["decisions"]) is not list or len(snapshot["decisions"]) > 128:
        _fail("INVALID_SNAPSHOT")
    records = []
    captured_decisions = {}
    total = len(ws_raw)
    for value in snapshot["decisions"]:
        ref, raw = _capture(value, contract, commit=snapshot["commit"], macro=True)
        rec, _ = owner.parse_record(_Record(raw))
        path = "agentos/decisions/DEC-" + str(rec.get("key")) + ".md"
        if ref["path"] != path or rec.get("key") in captured_decisions:
            _fail("INVALID_SNAPSHOT")
        if "project_plan_adoption" in rec and any(p.hard for p in owner.check_decision(rec, Path(path))):
            _fail("INVALID_SNAPSHOT")
        records.append(rec)
        captured_decisions[rec.get("key")] = (ref, raw, rec)
        total += len(raw)
    try:
        current = owner.select_project_plan_adoption(records, work_ref=work_ref)
    except ValueError:
        _fail("STALE_PREDECESSOR")
    proposal_ref, proposal_raw = _capture(snapshot["proposal"], contract, macro=True)
    associations = ws.get("artifacts") or []
    if (type(associations) is not list
            or proposal_ref["path"] not in associations and "macro:" + proposal_ref["path"] not in associations):
        _fail("STALE_PROPOSAL")
    try:
        header, candidate = owner.parse_project_plan_proposal(proposal_raw, work_ref=work_ref)
    except ValueError:
        _fail("STALE_PROPOSAL")
    base_ref, base_raw = _capture(snapshot["base"], contract)
    if header["base_source"] != base_ref:
        _fail("STALE_SOURCE")
    total += len(proposal_raw) + len(base_raw)
    if total > 2 * 1024 * 1024:
        _fail("CONTENT_OVER_BUDGET")
    try:
        contract.require_proposal_base(header, current)
    except ValueError:
        _fail("STALE_PREDECESSOR")
    try:
        candidate_record, _ = owner.parse_record(_Record(candidate))
    except (ValueError, TypeError, SystemExit):
        _fail("UNSUPPORTED_CANDIDATE")
    if candidate_record.get("key") != work_ref[3:]:
        _fail("WORK_REF_MISMATCH")
    if any(p.hard for p in owner.check_workstream(candidate_record, Path(ws_path), None)):
        _fail("UNSUPPORTED_CANDIDATE")
    changed = sorted(key for key in set(ws) | set(candidate_record) if ws.get(key) != candidate_record.get(key))
    return {"contract": contract, "ws_path": ws_path, "ws_ref": ws_ref, "ws_raw": ws_raw,
            "ws": ws, "current": current, "records": captured_decisions,
            "proposal_ref": proposal_ref, "proposal_raw": proposal_raw, "header": header,
            "candidate": candidate, "base_ref": base_ref, "base_raw": base_raw,
            "preview": {"changed_frontmatter_fields": changed,
                        "record_body_changed": _body(ws_raw) != _body(candidate),
                        "qualification_required": "VERIFIED_ADOPT_PLAN_GRANT_FOR_EXACT_RECIPE"}}


def _candidate_recipe(request, snapshot, actor, owner):
    _closed(request, {"schema", "request_id", "work_ref", "expected_commit", "expected_adoption",
                      "proposal_source", "base_source", "candidate_sha256"}, "INVALID_REQUEST")
    if request["schema"] != "agentos.plan_adoption_request.v1" or type(request["request_id"]) is not str or re.fullmatch(r"mmos-project-adopt-[0-9a-f]{40}", request["request_id"]) is None:
        _fail("INVALID_REQUEST")
    if type(request["work_ref"]) is not str or re.fullmatch(r"WS:[A-Z0-9]+(?:-[A-Z0-9]+)*", request["work_ref"]) is None or not 2 <= len(request["work_ref"][3:]) <= 64:
        _fail("WORK_REF_MISMATCH")
    _hex(request["expected_commit"], 40, "INVALID_REQUEST")
    _hex(request["candidate_sha256"], 64, "INVALID_REQUEST")
    if request["expected_adoption"] is not None and (type(request["expected_adoption"]) is not str or re.fullmatch(r"DEC:[A-Z0-9]+(?:-[A-Z0-9]+)*", request["expected_adoption"]) is None):
        _fail("INVALID_REQUEST")
    try:
        contract = owner._project_plan_contract()
        contract.validate_source_ref(request["proposal_source"])
        contract.validate_source_ref(request["base_source"])
    except (ValueError, TypeError):
        _fail("INVALID_REQUEST")
    actor = _actor(actor)
    inspected = _inspect(snapshot, request["work_ref"], owner)
    if request["expected_commit"] != snapshot["commit"]:
        _fail("STALE_SOURCE")
    current = inspected["current"]
    predecessor = current["decision_ref"] if current else None
    if request["expected_adoption"] != predecessor:
        _fail("STALE_PREDECESSOR")
    if request["proposal_source"] != inspected["proposal_ref"] or request["candidate_sha256"] != inspected["header"]["candidate_sha256"]:
        _fail("STALE_PROPOSAL")
    if request["base_source"] != inspected["base_ref"]:
        _fail("STALE_SOURCE")
    proposal_path = inspected["proposal_ref"]["path"]
    if proposal_path.lower().startswith(("agentos/", ".git/")):
        _fail("UNSUPPORTED_CANDIDATE")
    candidate_path = proposal_path[:-3] + ".candidate-" + request["candidate_sha256"][:20] + ".md"
    if len(candidate_path) > 512 or any(len(part.encode("utf-8")) > 255 for part in candidate_path.split("/")):
        _fail("UNSUPPORTED_CANDIDATE")
    decision_key = "PLAN-ADOPTION-" + request["request_id"][-40:].upper()
    decision_path = "agentos/decisions/DEC-" + decision_key + ".md"
    target = _target(snapshot["candidate_target"], candidate_path, snapshot["commit"], inspected["contract"])
    if target and target[1] != inspected["candidate"]:
        _fail("TARGET_CONFLICT")
    if _target(snapshot["decision_target"], decision_path, snapshot["commit"], inspected["contract"]) is not None:
        _fail("TARGET_CONFLICT")
    current_source = None if current is None else inspected["records"][predecessor[4:]][0]
    basis = {"workstream": inspected["ws_ref"], "current_decision": current_source,
             "proposal": inspected["proposal_ref"], "base": inspected["base_ref"],
             "candidate_target": {"path": candidate_path, "source": target[0] if target else None},
             "decision_target": {"path": decision_path, "state": "ABSENT"}}
    fingerprint = _hash(_canonical({"request": request, "actor": actor, "basis": basis}))
    result = {"schema": "agentos.plan_adoption_recipe.v1", "status": "PREVIEW_ONLY", "phase": "CANDIDATE",
              "request_id": request["request_id"], "request_sha256": fingerprint,
              "work_ref": request["work_ref"], "principal_id": actor["principal_id"],
              "expected_commit": snapshot["commit"], "candidate_path": candidate_path,
              "candidate_sha256": request["candidate_sha256"], "decision_ref": "DEC:" + decision_key,
              "proposal_source": inspected["proposal_ref"], "base_source": inspected["base_ref"],
              "expected_adoption": predecessor, "requires_publication": target is None,
              "candidate_source": target[0] if target else None,
              "edits": [_edit(candidate_path, inspected["candidate"], None)] if target is None else [],
              "preview": inspected["preview"]}
    return result, inspected, actor


def compile_candidate_recipe(*, request, snapshot, actor, owner):
    try:
        return copy.deepcopy(_candidate_recipe(request, snapshot, actor, owner)[0])
    except PlanAdoptionError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, UnicodeError, RecursionError, OverflowError, SystemExit):
        _fail("INVALID_SNAPSHOT")


def compile_adoption_recipe(*, request, initial_snapshot, current_snapshot, actor,
                            candidate_publication, owner):
    try:
        result, original, actor = _candidate_recipe(request, initial_snapshot, actor, owner)
        _closed(candidate_publication, {"schema", "state", "request_id", "request_sha256", "source", "raw_bytes"}, "CANDIDATE_NOT_VERIFIED")
        if (candidate_publication["schema"] != "agentos.plan_candidate_publication.v1"
                or candidate_publication["state"] != "VERIFIED_DEFAULT"):
            _fail("CANDIDATE_NOT_VERIFIED")
        if (candidate_publication["request_id"] != result["request_id"]
                or candidate_publication["request_sha256"] != result["request_sha256"]):
            _fail("OPERATION_CONFLICT")
        candidate_source, candidate_bytes = _capture({"source": candidate_publication["source"],
            "raw_bytes": candidate_publication["raw_bytes"]}, original["contract"], path=result["candidate_path"], macro=True)
        if candidate_bytes != original["candidate"]:
            _fail("CANDIDATE_NOT_VERIFIED")
        current = _inspect(current_snapshot, result["work_ref"], owner)
        if current["current"] != original["current"]:
            _fail("STALE_PREDECESSOR")
        if current["ws_raw"] != original["ws_raw"] or current["base_ref"] != original["base_ref"] or current["base_raw"] != original["base_raw"]:
            _fail("STALE_SOURCE")
        if (current["proposal_raw"] != original["proposal_raw"]
                or any(current["proposal_ref"][k] != original["proposal_ref"][k] for k in ("repository", "path", "content_sha256"))):
            _fail("STALE_PROPOSAL")
        prior = result["expected_adoption"]
        if prior and current["records"][prior[4:]][1] != original["records"][prior[4:]][1]:
            _fail("STALE_PREDECESSOR")
        target = _target(current_snapshot["candidate_target"], result["candidate_path"], current_snapshot["commit"], original["contract"])
        if target is None or target[1] != candidate_bytes:
            _fail("CANDIDATE_NOT_VERIFIED")
        decision_path = "agentos/decisions/" + result["decision_ref"].replace(":", "-", 1) + ".md"
        if _target(current_snapshot["decision_target"], decision_path, current_snapshot["commit"], original["contract"]) is not None:
            _fail("TARGET_CONFLICT")
        metadata = {"schema": "agentos.project_plan_adoption.v1", "work_ref": result["work_ref"],
                    "adopted_source": candidate_source, "predecessor": prior,
                    "proposal_source": original["proposal_ref"], "display_revision": None}
        original["contract"].require_expected_predecessor(metadata, current["current"])
        decision = {"key": result["decision_ref"][4:], "question": "Which exact planning content is adopted for " + result["work_ref"] + "?",
            "answer": "Adopt the exact candidate source referenced in project_plan_adoption.",
            "rationale": actor["decision_rationale"], "alternatives": [{"option": "Retain the prior baseline",
                "why_not": "The explicit ADOPT_PLAN request chose the captured candidate."}],
            "evidence": [json.dumps(ref, sort_keys=True, ensure_ascii=False) for ref in (original["proposal_ref"], original["base_ref"], candidate_source)],
            "affects": [result["work_ref"]], "confidence": "medium", "reversibility": "easy",
            "decided_by": actor["decided_by"], "decided_at": actor["decided_at"], "project_plan_adoption": metadata}
        if prior:
            decision["supersedes"] = [prior]
        new_raw = owner.draft_decision(decision).encode("utf-8")
        parsed, _ = owner.parse_record(_Record(new_raw))
        if any(p.hard for p in owner.check_decision(parsed, Path(decision_path))):
            _fail("INVALID_SNAPSHOT")
        edits = []
        if current["ws_raw"] != candidate_bytes:
            edits.append(_edit(current["ws_path"], candidate_bytes, _hash(current["ws_raw"])))
        edits.append(_edit(decision_path, new_raw, None))
        if prior:
            old_ref, old_raw, old_record = current["records"][prior[4:]]
            post = copy.deepcopy(old_record)
            post["superseded_by"] = result["decision_ref"]
            post_raw = owner._yaml_frontmatter(post).encode("utf-8") + _body(old_raw)
            parsed_old, _ = owner.parse_record(_Record(post_raw))
            if any(p.hard for p in owner.check_decision(parsed_old, Path(old_ref["path"]))):
                _fail("INVALID_SNAPSHOT")
            edits.append(_edit(old_ref["path"], post_raw, _hash(old_raw)))
        result.update({"phase": "ADOPTION_DECISION", "expected_commit": current_snapshot["commit"],
                       "candidate_source": candidate_source, "requires_publication": True, "edits": edits})
        return copy.deepcopy(result)
    except PlanAdoptionError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, UnicodeError, RecursionError, OverflowError, SystemExit):
        _fail("INVALID_SNAPSHOT")
