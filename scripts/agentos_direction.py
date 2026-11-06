"""Pure-stdlib Macro owner contract for AgentOS direction acceptance.

Closed-value contract: every failure raises :class:`DirectionError` carrying one
of the closed codes in ``VALID_CODES``.  ``str(exc)`` and ``exc.code`` are that
same closed code alone; rejected input data is never echoed.  Every returned
mapping is detached (freshly constructed) from caller input.

Canonical source paths are derived here, never accepted from callers:

* workstream direction record: ``agentos/workstreams/WS-<WS-KEY>.md``
* decision record:            ``agentos/decisions/DEC-<DEC-KEY>.md``

``<WS-KEY>``/``<DEC-KEY>`` are the UPPER-KEBAB keys after the ``WS:``/``DEC:``
reference prefixes.  Source references are captured facts only: they carry no
authentication, authority or admission meaning, and the owning parent performs
the real owner validation and source capture.
"""

from __future__ import annotations

import datetime
import json
import re

__all__ = [
    "DirectionError",
    "VALID_CODES",
    "validate_declaration",
    "project_direction",
    "WS_PATH_TEMPLATE",
    "DEC_PATH_TEMPLATE",
    "OUTPUT_BUDGET_BYTES",
]

SCHEMA = "agentos.direction_acceptance.v1"
ACCEPTED_STATE = "ACCEPTED"
REPOSITORY = "mastermindx-market-intelligence/macro"

VALID_CODES = frozenset(
    {
        "INVALID_DIRECTION",
        "INVALID_SOURCE",
        "LINEAGE_CONFLICT",
        "LINEAGE_INCOMPLETE",
        "NOT_DECLARED",
        "CONTENT_OVER_BUDGET",
    }
)

WS_PATH_TEMPLATE = "agentos/workstreams/WS-{key}.md"
DEC_PATH_TEMPLATE = "agentos/decisions/DEC-{key}.md"

OUTPUT_BUDGET_BYTES = 64 * 1024
MAX_DECISION_ENTRIES = 128
DEFAULT_MAX_REVISIONS = 8
MAX_REVISIONS_LIMIT = 8

ANSWER_LIMIT = 4096
RATIONALE_LIMIT = 4096
DECIDED_BY_LIMIT = 256

_DATE_PRECISION = "DAY"

_KEBAB_RE = re.compile(r"[A-Z0-9]+(?:-[A-Z0-9]+)*")
_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_HEX_RE = re.compile(r"[0-9a-f]+")

_DECLARATION_KEYS = frozenset({"schema", "state", "work_ref", "predecessor"})
_SOURCE_KEYS = frozenset({"repository", "commit", "path", "content_sha256"})
_ENTRY_KEYS = frozenset({"record", "source"})

_MISSING = object()


class DirectionError(ValueError):
    """Closed-code failure; ``str(exc)`` is the code itself, nothing else."""

    def __init__(self, code):
        if code not in VALID_CODES:
            code = "INVALID_DIRECTION"
        self.code = code
        super().__init__(code)

    def __str__(self):
        return self.code


def _fail(code):
    raise DirectionError(code)


def _is_ws_ref(value):
    if type(value) is not str or not value.startswith("WS:"):
        return False
    key = value[3:]
    return 2 <= len(key) <= 64 and _KEBAB_RE.fullmatch(key) is not None


def _is_dec_ref(value):
    if type(value) is not str or not value.startswith("DEC:"):
        return False
    key = value[4:]
    return 2 <= len(key) <= 128 and _KEBAB_RE.fullmatch(key) is not None


def _bounded_text(value, limit):
    if type(value) is not str or not value.strip():
        return None
    try:
        if len(value.encode("utf-8")) > limit:
            return None
    except UnicodeError:
        return None
    return value


def _canonical_day(value):
    if type(value) is datetime.date:
        return value.isoformat()
    if type(value) is str and _DATE_RE.fullmatch(value) is not None:
        try:
            parsed = datetime.date.fromisoformat(value)
        except ValueError:
            return None
        if parsed.isoformat() == value:
            return value
    return None


def _validate_source(value, *, expected_path):
    if type(value) is not dict or value.keys() != _SOURCE_KEYS:
        _fail("INVALID_SOURCE")
    repository = value["repository"]
    if type(repository) is not str or repository != REPOSITORY:
        _fail("INVALID_SOURCE")
    commit = value["commit"]
    if type(commit) is not str or len(commit) != 40 or _HEX_RE.fullmatch(commit) is None:
        _fail("INVALID_SOURCE")
    path = value["path"]
    if type(path) is not str or path != expected_path:
        _fail("INVALID_SOURCE")
    digest = value["content_sha256"]
    if type(digest) is not str or len(digest) != 64 or _HEX_RE.fullmatch(digest) is None:
        _fail("INVALID_SOURCE")
    return {
        "repository": repository,
        "commit": commit,
        "path": path,
        "content_sha256": digest,
    }


def validate_declaration(value, *, work_ref, decision_ref):
    """Validate one explicit direction acceptance declaration.

    Returns a detached mapping of the closed declaration fields.  Anything else
    raises ``DirectionError("INVALID_DIRECTION")`` without echoing the input.
    """
    if not _is_ws_ref(work_ref):
        _fail("INVALID_DIRECTION")
    if not _is_dec_ref(decision_ref):
        _fail("INVALID_DIRECTION")
    if type(value) is not dict or value.keys() != _DECLARATION_KEYS:
        _fail("INVALID_DIRECTION")
    schema = value["schema"]
    if type(schema) is not str or schema != SCHEMA:
        _fail("INVALID_DIRECTION")
    state = value["state"]
    if type(state) is not str or state != ACCEPTED_STATE:
        _fail("INVALID_DIRECTION")
    declared_ws = value["work_ref"]
    if type(declared_ws) is not str or declared_ws != work_ref:
        _fail("INVALID_DIRECTION")
    predecessor = value["predecessor"]
    if predecessor is not None:
        if not _is_dec_ref(predecessor):
            _fail("INVALID_DIRECTION")
        if predecessor == decision_ref:
            _fail("INVALID_DIRECTION")
    return {
        "schema": schema,
        "state": state,
        "work_ref": declared_ws,
        "predecessor": predecessor,
    }


def _project_row(decision_ref, entry, *, work_ref, expected_commit):
    record = entry["record"]
    key = record.get("key")
    if type(key) is not str or key != decision_ref[4:]:
        _fail("INVALID_DIRECTION")
    declaration = validate_declaration(
        record.get("direction"), work_ref=work_ref, decision_ref=decision_ref
    )
    if "project_plan_adoption" in record:
        _fail("INVALID_DIRECTION")
    affects = record.get("affects")
    if type(affects) is not list:
        _fail("INVALID_DIRECTION")
    if not any(type(item) is str and item == work_ref for item in affects):
        _fail("INVALID_DIRECTION")
    answer = _bounded_text(record.get("answer"), ANSWER_LIMIT)
    rationale = _bounded_text(record.get("rationale"), RATIONALE_LIMIT)
    decided_by = _bounded_text(record.get("decided_by"), DECIDED_BY_LIMIT)
    if answer is None or rationale is None or decided_by is None:
        _fail("INVALID_DIRECTION")
    decided_at = _canonical_day(record.get("decided_at"))
    if decided_at is None:
        _fail("INVALID_DIRECTION")
    source = _validate_source(
        entry["source"], expected_path=DEC_PATH_TEMPLATE.format(key=decision_ref[4:])
    )
    if source["commit"] != expected_commit:
        _fail("INVALID_SOURCE")
    predecessor = declaration["predecessor"]
    supersedes = record.get("supersedes", [])
    if predecessor is None:
        if not (type(supersedes) is list and supersedes == []):
            _fail("LINEAGE_CONFLICT")
    else:
        if type(supersedes) is not list or supersedes != [predecessor]:
            _fail("LINEAGE_CONFLICT")
    row = {
        "decision_ref": decision_ref,
        "answer": answer,
        "rationale": rationale,
        "decided_by": decided_by,
        "decided_at": decided_at,
        "date_precision": _DATE_PRECISION,
        "predecessor": predecessor,
        "source": source,
    }
    return record, predecessor, row


def project_direction(
    *,
    work_ref,
    workstream,
    workstream_source,
    decisions,
    max_revisions=DEFAULT_MAX_REVISIONS,
):
    """Project the explicitly declared direction chain of one workstream.

    The current decision is the explicitly declared ``accepted_direction`` and
    every prior row follows that same explicit predecessor chain.  Dates are
    recorded facts only and never elect or reorder rows.
    """
    if not _is_ws_ref(work_ref):
        _fail("INVALID_DIRECTION")
    if type(max_revisions) is not int or not 1 <= max_revisions <= MAX_REVISIONS_LIMIT:
        _fail("INVALID_DIRECTION")
    if type(workstream) is not dict:
        _fail("INVALID_DIRECTION")
    ws_key = workstream.get("key")
    if type(ws_key) is not str or ws_key != work_ref[3:]:
        _fail("INVALID_DIRECTION")
    if "accepted_direction" not in workstream:
        _fail("NOT_DECLARED")
    accepted = workstream["accepted_direction"]
    if not _is_dec_ref(accepted):
        _fail("INVALID_DIRECTION")
    if type(workstream.get("decisions")) is not list or accepted not in workstream["decisions"]:
        _fail("INVALID_DIRECTION")
    if type(decisions) is not dict:
        _fail("INVALID_DIRECTION")
    if len(decisions) > MAX_DECISION_ENTRIES:
        _fail("INVALID_DIRECTION")
    for ref, entry in decisions.items():
        if not _is_dec_ref(ref):
            _fail("INVALID_DIRECTION")
        if type(entry) is not dict or entry.keys() != _ENTRY_KEYS:
            _fail("INVALID_DIRECTION")
        if type(entry["record"]) is not dict:
            _fail("INVALID_DIRECTION")

    ws_source = _validate_source(
        workstream_source,
        expected_path=WS_PATH_TEMPLATE.format(key=work_ref[3:]),
    )

    seen = set()
    rows = []
    successor_ref = None
    next_ref = accepted
    has_more = False
    total_count = None
    while True:
        if next_ref in seen:
            _fail("LINEAGE_CONFLICT")
        entry = decisions.get(next_ref, _MISSING)
        if entry is _MISSING:
            _fail("LINEAGE_INCOMPLETE")
        record, predecessor, row = _project_row(
            next_ref, entry, work_ref=work_ref, expected_commit=ws_source["commit"]
        )
        if successor_ref is None:
            if "superseded_by" in record:
                _fail("LINEAGE_CONFLICT")
        else:
            superseded_by = record.get("superseded_by")
            if type(superseded_by) is not str or superseded_by != successor_ref:
                _fail("LINEAGE_CONFLICT")
        seen.add(next_ref)
        rows.append(row)
        successor_ref = next_ref
        if len(rows) >= max_revisions:
            if predecessor in seen:
                _fail("LINEAGE_CONFLICT")
            if predecessor is not None:
                has_more = True
                total_count = None
            else:
                has_more = False
                total_count = len(rows)
            break
        if predecessor is None:
            has_more = False
            total_count = len(rows)
            break
        next_ref = predecessor

    payload = {
        "work_ref": work_ref,
        "workstream_source": ws_source,
        "current": rows[0],
        "history": {
            "revisions": rows[1:],
            "has_more": has_more,
            "total_count": total_count,
        },
    }
    serialized = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    if len(serialized) > OUTPUT_BUDGET_BYTES:
        _fail("CONTENT_OVER_BUDGET")
    return payload
