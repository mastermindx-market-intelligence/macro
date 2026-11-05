"""WP02 structural research kernel; no real-source admission path.

The public API accepts bounded JSON bytes and two exact frozen policy artifacts.
Synthetic results are deductions from supplied artificial premises, not facts,
issuer identity decisions, source authority, historical completeness or rights.
This module has no store, registry, provider, callback or network integration.
"""
from __future__ import annotations

from collections import Counter, deque
from datetime import date, datetime, timezone
from fractions import Fraction
from hashlib import sha256
import json
import re


POLICY_SHA256 = "d41422d76219b1c5d3a3c9cbb19a1bc3124433031200b09499033bd4dc30d522"
POLICY_LENGTH = 60312
ADOPTION_SHA256 = "645a20a39842d9c5a03b4ff39a37280d1aa02c32ef545c061d0aa959f06e0016"
ADOPTION_LENGTH = 9593
EFFECTIVE_POLICY_SHA256 = "90bec6078348af6e41c9538e12e0443dd37d671c85a7089c64c547f5ce5e7714"
BASE_CONTENT_SHA256 = "6349f2b2c9f8d9257d3853d4906bdfcc9dd6fe706cf053e957f9a4098c133266"
SEED = "GMI-WP02-20261009-v1"
D = date(2026, 9, 30)
K = datetime(2026, 10, 9, tzinfo=timezone.utc)
GROUPS = ("US", "CN_MAINLAND", "HK", "CA", "UK", "JP", "EU")
ACTIVITIES = ("SEMICONDUCTOR_CLOUD", "INDUSTRIALS", "CONSUMER",
              "ENERGY_MATERIALS", "FINANCIALS", "HEALTHCARE")
BANDS = ("L", "M", "S")
STRATA = GROUPS[:4] + ("INT",)
INT_COUNTRIES = GROUPS[4:]
QUOTA = {"L": 2, "M": 1, "S": 1}
EVENT_KINDS = ("ADMISSION", "REMOVAL", "TRANSFER", "CONVERSION",
               "IDENTITY_REPLACEMENT", "PRIMARY_STATUS_CHANGE")
MAX_INPUT = 2 * 1024 * 1024
MAX_OUTPUT = 8 * 1024 * 1024
MAX_RECORDS = 512
MAX_SOURCES = 1024
MAX_SOURCE_BYTES = 256 * 1024
MAX_CLASSES = 8
MAX_ASSERTIONS = 16
MAX_EVENTS = 1024
MAX_ACTIONS = 32
MAX_DEPTH = 24
MAX_TOKENS = 160000
MAX_DERIVED_BITS = 8192
DECIMAL = re.compile(r"[+-]?(?:0|[1-9][0-9]{0,47})(?:\.[0-9]{1,24})?\Z")
HEX = re.compile(r"[0-9a-f]{64}\Z")
UTC_INSTANT = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.([0-9]+))?Z\Z")


class ContractError(ValueError):
    """A fixed, non-source-text error code and JSON coordinate."""
    def __init__(self, code, scope="request"):
        self.code, self.scope = code, scope
        super().__init__(code + " at " + scope)


def _fail(code, scope):
    raise ContractError(code, scope)


def canonical_bytes(value, limit=MAX_OUTPUT):
    """Deterministic JSON; account UTF-8 bytes before joining fragments."""
    fragments, size = [], 0
    encoder = json.JSONEncoder(ensure_ascii=False, sort_keys=True,
                               separators=(",", ":"), allow_nan=False)
    try:
        for fragment in encoder.iterencode(value):
            raw = fragment.encode("utf-8", "strict")
            size += len(raw)
            if size > limit:
                _fail("OUTPUT_BYTE_LIMIT", "output")
            fragments.append(raw)
    except (TypeError, UnicodeError, ValueError) as exc:
        if isinstance(exc, ContractError):
            raise
        _fail("NON_JSON_OUTPUT", "output")
    return b"".join(fragments)


def _binding(raw):
    return {"byte_length": len(raw), "sha256": sha256(raw).hexdigest()}


def _json(raw, limit=MAX_INPUT, scope="request"):
    if type(raw) is not bytes:
        _fail("BYTES_REQUIRED", scope)
    if len(raw) > limit:
        _fail("INPUT_BYTE_LIMIT", scope)
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeError:
        _fail("INVALID_UTF8", scope)
    # A pre-parse depth/token fence prevents an unbounded Python JSON tree.
    depth, tokens, quoted, escaped = 0, 0, False, False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
            tokens += 1
        elif char in "[{":
            depth += 1
            tokens += 1
            if depth > MAX_DEPTH:
                _fail("JSON_DEPTH_LIMIT", scope)
        elif char in "]}":
            depth -= 1
        elif char in ",:":
            tokens += 1
        if tokens > MAX_TOKENS:
            _fail("JSON_NODE_LIMIT", scope)

    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                _fail("DUPLICATE_JSON_KEY", scope)
            try:
                key.encode("utf-8", "strict")
            except UnicodeError:
                _fail("INVALID_UTF8", scope)
            out[key] = value
        return out

    def integer(value):
        if len(value.lstrip("-")) > 12:
            _fail("JSON_INTEGER_LIMIT", scope)
        return int(value)

    def noninteger(_):
        _fail("NON_INTEGER_JSON_NUMBER", scope)

    try:
        parsed = json.loads(text, object_pairs_hook=pairs, parse_int=integer,
                            parse_float=noninteger, parse_constant=noninteger)
        # Reject escaped lone surrogates in values as well as in keys.
        canonical_bytes(parsed, limit)
        return parsed
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        if isinstance(exc, ContractError):
            raise
        _fail("INVALID_JSON", scope)


def _object(value, required, optional=(), scope="request"):
    if type(value) is not dict or not set(required) <= value.keys() or \
            not value.keys() <= set(required) | set(optional):
        _fail("CLOSED_OBJECT_SHAPE", scope)
    return value


def _array(value, maximum, scope):
    if type(value) is not list or len(value) > maximum:
        _fail("ARRAY_SHAPE_OR_LIMIT", scope)
    return value


def _text(value, scope, maximum=256):
    if type(value) is not str:
        _fail("STRING_REQUIRED", scope)
    try:
        raw = value.encode("utf-8", "strict")
    except UnicodeError:
        _fail("INVALID_UTF8", scope)
    if not raw or len(raw) > maximum:
        _fail("STRING_LENGTH", scope)
    return value


def _choice(value, options, scope):
    _text(value, scope)
    if value not in options:
        _fail("ENUM_VALUE", scope)
    return value


def _count(value, scope):
    if type(value) is not int or not 0 <= value <= 10**12 - 1:
        _fail("NONNEGATIVE_INTEGER_REQUIRED", scope)
    return value


def _day(value, scope):
    _text(value, scope, 10)
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        _fail("ISO_DATE_REQUIRED", scope)
    if parsed.isoformat() != value:
        _fail("ISO_DATE_REQUIRED", scope)
    return parsed


def _instant(value, scope):
    _text(value, scope, 40)
    shape = UTC_INSTANT.fullmatch(value)
    if shape is None:
        _fail("EXPLICIT_UTC_BOUND_REQUIRED", scope)
    # datetime truncates finer fractions. Reject them before conversion so a
    # post-K assertion or correction can never be rounded onto the cutoff.
    if shape.group(1) is not None and len(shape.group(1)) > 6:
        _fail("UTC_TIMESTAMP_PRECISION_UNSUPPORTED", scope)
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
        return parsed
    except ValueError as exc:
        if isinstance(exc, ContractError):
            raise
        _fail("EXPLICIT_UTC_BOUND_REQUIRED", scope)


def _unique_strings(values, maximum, scope, options=None):
    result = []
    for value in _array(values, maximum, scope):
        result.append(_text(value, scope) if options is None else
                      _choice(value, options, scope))
    if len(set(result)) != len(result):
        _fail("DUPLICATE_IDENTITY", scope)
    return result


def rational(value, role="positive", *, evidenced_zero=False, scope="numeric"):
    """Bounded decimal strings only; never coerce floats, bools or abs(delta)."""
    if type(value) is not str or not DECIMAL.fullmatch(value):
        _fail("DECIMAL_STRING_REQUIRED", scope)
    number = Fraction(value)
    if role == "positive":
        if number <= 0:
            _fail("STRICTLY_POSITIVE_REQUIRED", scope)
    elif role == "delta":
        if number == 0 and evidenced_zero is not True:
            _fail("ZERO_DELTA_EVIDENCE_REQUIRED", scope)
    else:
        _fail("UNKNOWN_NUMERIC_ROLE", scope)
    return number


def _rational_json(number):
    _bounded_fraction(number, "derived_numeric")
    return {"numerator": str(number.numerator), "denominator": str(number.denominator)}


def _bounded_fraction(number, scope):
    if number.numerator.bit_length() > MAX_DERIVED_BITS or number.denominator.bit_length() > MAX_DERIVED_BITS:
        _fail("EXACT_ARITHMETIC_BUDGET", scope)
    return number


def priority_hash(domain, *fields):
    material = bytearray()
    for value in (domain, SEED, *fields):
        raw = _text(value, "hash_field").encode("utf-8", "strict")
        material.extend(len(raw).to_bytes(8, "big"))
        material.extend(raw)
    return sha256(material).digest()


def _priority(issuer_id):
    return priority_hash("issuer-priority", issuer_id), issuer_id.encode("utf-8")


def bind_policy(policy_bytes, adoption_bytes):
    """Exact known bytes plus exact single override; not signer authentication."""
    for raw, length, digest, scope in (
            (policy_bytes, POLICY_LENGTH, POLICY_SHA256, "policy"),
            (adoption_bytes, ADOPTION_LENGTH, ADOPTION_SHA256, "adoption")):
        if type(raw) is not bytes or len(raw) != length or sha256(raw).hexdigest() != digest:
            _fail("FROZEN_POLICY_BINDING_MISMATCH", scope)
    policy = _json(policy_bytes, POLICY_LENGTH, "policy")
    adoption = _json(adoption_bytes, ADOPTION_LENGTH, "adoption")
    if sha256(canonical_bytes(policy)).hexdigest() != BASE_CONTENT_SHA256:
        _fail("BASE_POLICY_CONTENT_MISMATCH", "policy")
    overrides = adoption["normative_overrides"]
    if len(overrides) != 1 or overrides[0]["pointer"] != "/capitalization/numeric_rule" or \
            policy["capitalization"]["numeric_rule"] != overrides[0]["expected_original"]:
        _fail("ADOPTION_OVERRIDE_MISMATCH", "adoption")
    policy["capitalization"]["numeric_rule"] = overrides[0]["replacement"]
    if sha256(canonical_bytes(policy)).hexdigest() != EFFECTIVE_POLICY_SHA256:
        _fail("EFFECTIVE_POLICY_CONTENT_MISMATCH", "policy")
    return {"policy_raw": _binding(policy_bytes), "adoption_raw": _binding(adoption_bytes),
            "effective_policy_content_sha256": EFFECTIVE_POLICY_SHA256,
            "changed_pointer": "/capitalization/numeric_rule",
            "binding_scope": "EXACT_KNOWN_CONTENT_NOT_AUTHORITY_AUTHENTICATION"}


class _Context:
    def __init__(self, sources):
        self.sources, self.source_receipts, self.holds = {}, [], []
        self.span_checks = 0
        self.assertion_coordinates = {}
        for row in _array(sources, MAX_SOURCES, "sources"):
            _object(row, ("source_id", "content", "sha256", "byte_length"), scope="source")
            sid = _text(row["source_id"], "source.source_id")
            if sid in self.sources:
                _fail("DUPLICATE_SOURCE_ID", "sources")
            if type(row["content"]) is not str:
                _fail("STRING_REQUIRED", "source.content")
            raw = row["content"].encode("utf-8", "strict")
            if len(raw) > MAX_SOURCE_BYTES:
                _fail("SOURCE_BYTE_LIMIT", "source")
            digest = _text(row["sha256"], "source.sha256", 64)
            length = _count(row["byte_length"], "source.byte_length")
            good = HEX.fullmatch(digest) is not None and _binding(raw) == {
                "sha256": digest, "byte_length": length}
            self.sources[sid] = (raw, good)
            self.source_receipts.append({"source_id": sid, "actual_bytes": _binding(raw),
                                         "integrity": "MATCH" if good else "MISMATCH"})
            if not good:
                self.hold("SUPPLIED_BYTE_BINDING_MISMATCH", sid)

    def hold(self, code, scope):
        self.holds.append({"code": code, "scope": scope})

    def raw(self, sid, scope):
        _text(sid, scope)
        item = self.sources.get(sid)
        if item is None or not item[1]:
            _fail("SUPPLIED_SOURCE_UNAVAILABLE_OR_CORRUPT", scope)
        return item[0]

    def evidence(self, binding, expected, scope):
        _object(binding, ("source_id", "start", "end"), scope=scope)
        raw = self.raw(binding["source_id"], scope)
        start, end = _count(binding["start"], scope), _count(binding["end"], scope)
        if not 0 <= start < end <= len(raw) or raw[start:end] != expected.encode("utf-8"):
            _fail("SOURCE_SPAN_VALUE_MISMATCH", scope)
        self.span_checks += 1

    def raw_list(self, sid, expected, scope):
        parsed = _json(self.raw(sid, scope), MAX_SOURCE_BYTES, scope)
        if canonical_bytes(parsed) != canonical_bytes(expected):
            _fail("RAW_TO_PARSED_RECONCILIATION_MISMATCH", scope)


def _membership(value, partition_ids, scope):
    result = {}
    for row in _array(value, MAX_RECORDS, scope):
        _object(row, ("member_id", "record_id", "partition_id", "instrument", "primary_status"), scope=scope)
        mid = _text(row["member_id"], scope)
        _text(row["record_id"], scope)
        _choice(row["partition_id"], partition_ids, scope)
        _choice(row["instrument"], ("ORDINARY", "DEPOSITARY_RECEIPT", "EXCLUDED"), scope)
        _choice(row["primary_status"], ("PRIMARY", "SECONDARY"), scope)
        if mid in result:
            _fail("DUPLICATE_MEMBER_ID", scope)
        result[mid] = row
    return result


def _set_diff(actual, expected):
    return {"missing": sorted(set(expected) - set(actual)),
            "extra": sorted(set(actual) - set(expected)),
            "different_states": sorted(k for k in set(actual) & set(expected)
                                       if actual[k] != expected[k])}


def reconcile_history(history, context):
    """Reconcile supplied artificial sets and reversible full-state transitions."""
    _object(history, ("kind", "target_date", "anchor_date", "anchor_public_upper",
                      "partitions", "declared_partition_ids", "anchor_members", "target_members",
                      "anchor_source_id", "target_source_id", "events_source_id", "events",
                      "coverage_start", "coverage_end", "covered_event_kinds", "declared_event_ids",
                      "expected_anchor_member_ids", "expected_target_member_ids"), scope="history")
    kind = _choice(history["kind"], ("SNAPSHOT", "RECONSTRUCTION", "CURRENT_ONLY"), "history.kind")
    target = _day(history["target_date"], "history.target_date")
    anchor = _day(history["anchor_date"], "history.anchor_date")
    if target != D:
        _fail("FIXED_D_MISMATCH", "history")
    if _instant(history["anchor_public_upper"], "history.anchor_public_upper") > K:
        _fail("POST_CUTOFF_ANCHOR", "history")
    partitions = {}
    for row in _array(history["partitions"], 128, "history.partitions"):
        _object(row, ("partition_id", "jurisdiction"), scope="history.partition")
        pid = _text(row["partition_id"], "history.partition")
        if pid in partitions:
            _fail("DUPLICATE_PARTITION_ID", "history")
        partitions[pid] = _choice(row["jurisdiction"], GROUPS, "history.partition")
    if set(partitions.values()) != set(GROUPS):
        _fail("MODEL_PERIMETER_INCOMPLETE", "history")
    if set(_unique_strings(history["declared_partition_ids"], 128, "history.partitions")) != set(partitions):
        _fail("PARTITION_SET_MISMATCH", "history")
    before = _membership(history["anchor_members"], partitions, "history.anchor_members")
    expected = _membership(history["target_members"], partitions, "history.target_members")
    for field, members in (("expected_anchor_member_ids", before), ("expected_target_member_ids", expected)):
        if set(_unique_strings(history[field], MAX_RECORDS, "history." + field)) != set(members):
            _fail("DECLARED_MEMBER_SET_MISMATCH", "history." + field)
    context.raw_list(history["anchor_source_id"], history["anchor_members"], "history.anchor")
    context.raw_list(history["target_source_id"], history["target_members"], "history.target")
    events = _array(history["events"], MAX_EVENTS, "history.events")
    context.raw_list(history["events_source_id"], events, "history.events")
    start, end = min(anchor, target), max(anchor, target)
    if _day(history["coverage_start"], "history.coverage_start") != start or \
            _day(history["coverage_end"], "history.coverage_end") != end:
        _fail("EVENT_INTERVAL_UNCOVERED", "history")
    if set(_unique_strings(history["covered_event_kinds"], len(EVENT_KINDS),
                           "history.covered_event_kinds", EVENT_KINDS)) != set(EVENT_KINDS):
        _fail("EVENT_KIND_UNCOVERED", "history")
    event_ids, orders, ordered = set(), set(), []
    for event in events:
        _object(event, ("event_id", "effective_date", "sequence", "kind", "public_upper", "before", "after"), scope="history.event")
        eid = _text(event["event_id"], "history.event_id")
        effective = _day(event["effective_date"], "history.event_date")
        sequence = _count(event["sequence"], "history.sequence")
        event_kind = _choice(event["kind"], EVENT_KINDS, "history.event_kind")
        if eid in event_ids or (effective, sequence) in orders:
            _fail("AMBIGUOUS_EVENT_ID_OR_ORDER", "history.events")
        event_ids.add(eid)
        orders.add((effective, sequence))
        if not start < effective <= end or _instant(event["public_upper"], "history.event_public") > K:
            _fail("EVENT_OUTSIDE_INTERVAL_OR_K", eid)
        old = _membership(event["before"], partitions, "history.event.before")
        new = _membership(event["after"], partitions, "history.event.after")
        sizes = (len(old), len(new))
        if sizes != ((0, 1) if event_kind == "ADMISSION" else
                     (1, 0) if event_kind == "REMOVAL" else (1, 1)):
            _fail("EVENT_KIND_STATE_SHAPE_MISMATCH", eid)
        if old == new:
            _fail("NO_CHANGE_MEMBERSHIP_EVENT", eid)
        if sizes == (1, 1):
            old_row, new_row = next(iter(old.values())), next(iter(new.values()))
            changed = {field for field in old_row if old_row[field] != new_row[field]}
            allowed = {"TRANSFER": {"partition_id"}, "CONVERSION": {"instrument"},
                       "IDENTITY_REPLACEMENT": {"member_id", "record_id"},
                       "PRIMARY_STATUS_CHANGE": {"primary_status"}}[event_kind]
            if not changed or not changed <= allowed:
                _fail("EVENT_KIND_CHANGED_FIELDS_MISMATCH", eid)
        ordered.append((effective, sequence, eid, old, new, event_kind))
    if set(_unique_strings(history["declared_event_ids"], MAX_EVENTS, "history.declared_event_ids")) != event_ids:
        _fail("DECLARED_EVENT_SET_MISMATCH", "history")
    if kind == "CURRENT_ONLY":
        _fail("CURRENT_ONLY_SURVIVOR_FRAME", "history")
    if kind == "SNAPSHOT" and (anchor != target or events):
        _fail("SNAPSHOT_COORDINATE_MISMATCH", "history")
    if kind == "RECONSTRUCTION" and anchor == target:
        _fail("RECONSTRUCTION_REQUIRES_DISTINCT_ANCHOR", "history")
    working = dict(before)
    applied = []
    for _, _, eid, old, new, event_kind in sorted(ordered, reverse=anchor > target):
        remove, insert = (new, old) if anchor > target else (old, new)
        if any(working.get(mid) != row for mid, row in remove.items()):
            _fail("EVENT_BEFORE_AFTER_STATE_MISMATCH", eid)
        for mid in remove:
            del working[mid]
        if any(mid in working for mid in insert):
            _fail("EVENT_INSERT_COLLISION", eid)
        working.update(insert)
        applied.append({"event_id": eid, "kind": event_kind,
                        "direction": "REVERSE" if anchor > target else "FORWARD"})
    diff = _set_diff(working, expected)
    if any(diff.values()):
        context.hold("TARGET_MEMBER_SET_MISMATCH", "history")
    receipt = {"state": "MODEL_SET_MATCH" if not any(diff.values()) else "MODEL_SET_MISMATCH",
               "direction": "SNAPSHOT" if kind == "SNAPSHOT" else "REVERSE" if anchor > target else "FORWARD",
               "anchor_supplied_count": len(before), "target_supplied_count": len(expected),
               "reconstructed_model_count": len(working), "set_difference": diff,
               "applied_events": applied,
               "reconstructed_set_content_sha256": sha256(canonical_bytes(
                   [working[k] for k in sorted(working)])).hexdigest(),
               "historical_authority": "FRAME_HISTORY_UNPROVEN"}
    return working, partitions, receipt


def resolve_assertions(bundle, context, *, issuer_id, class_id, component,
                       maximum_age=None, fixed_date=None, require_point=False):
    """Model same-fact comparison; claimed relations never authenticate sources.

    POINT coordinates are measurement dates. PERSISTENT coordinates are valid
    starts; all overlapping states at D compete, irrespective of start recency.
    Only same-publisher, exact-scope corrections/retractions are modeled. A
    transition across different persistent intervals is explicitly unsupported.
    """
    scope = issuer_id + "/" + class_id + "/" + component
    _object(bundle, ("state_kind", "assertions", "relations"), scope=scope)
    state_kind = _choice(bundle["state_kind"], ("POINT", "PERSISTENT"), scope)
    if require_point and state_kind != "POINT":
        _fail("POINT_MEASUREMENT_REQUIRED", scope)
    candidates, eligible, exclusions = {}, {}, []
    for row in _array(bundle["assertions"], MAX_ASSERTIONS, scope):
        _object(row, ("assertion_id", "publisher_id", "coordinate", "valid_to", "public_upper",
                      "value", "unit_basis", "status", "evidence"), scope=scope)
        aid = _text(row["assertion_id"], scope)
        publisher = _text(row["publisher_id"], scope)
        coordinate = _day(row["coordinate"], scope)
        until = None if row["valid_to"] is None else _day(row["valid_to"], scope)
        public = _instant(row["public_upper"], scope)
        basis = _text(row["unit_basis"], scope)
        status = _choice(row["status"], ("ACTUAL", "ESTIMATED"), scope)
        value = rational(row["value"], scope=scope)
        context.evidence(row["evidence"], row["value"], scope)
        if aid in candidates:
            _fail("DUPLICATE_ASSERTION_ID", scope)
        if aid in context.assertion_coordinates:
            _fail("ASSERTION_ID_REUSED_ACROSS_COMPONENTS", scope)
        context.assertion_coordinates[aid] = scope
        if (state_kind == "POINT" and until is not None) or (until is not None and until <= coordinate):
            _fail("ASSERTION_INTERVAL_INVALID", scope)
        item = {"id": aid, "publisher": publisher, "coordinate": coordinate,
                "until": until, "public": public, "value": value, "basis": basis}
        candidates[aid] = item
        reason = ("POST_CUTOFF_SOURCE" if public > K else "ESTIMATE_NOT_MEASUREMENT" if status != "ACTUAL"
                  else "FUTURE_MEASUREMENT" if coordinate > D else
                  "STATE_NOT_APPLICABLE" if until is not None and D >= until else
                  "COMPONENT_TOO_OLD" if state_kind == "POINT" and maximum_age is not None and
                  (D - coordinate).days > maximum_age else
                  "OUTSIDE_FIXED_REFERENCE_DATE" if fixed_date is not None and coordinate != fixed_date else None)
        if reason:
            exclusions.append({"assertion_id": aid, "reason": reason})
        else:
            eligible[aid] = item
    # Pick measurement before publication recency or correction magnitude.
    selected_coordinate = max((a["coordinate"] for a in eligible.values()), default=None) if state_kind == "POINT" else D
    required = {aid: a for aid, a in eligible.items()
                if state_kind == "PERSISTENT" or a["coordinate"] == selected_coordinate}
    for aid in eligible.keys() - required.keys():
        exclusions.append({"assertion_id": aid, "reason": "OLDER_DISTINCT_MEASUREMENT_RETAINED"})
    edges, remove, relations, relation_ids = {}, set(), [], set()
    for link in _array(bundle["relations"], 32, scope):
        _object(link, ("relation_id", "kind", "publisher_id", "new_id", "old_id",
                       "fact_coordinate", "unit_basis", "public_upper", "evidence", "resolution_owner_id"), scope=scope)
        rid = _text(link["relation_id"], scope)
        kind = _choice(link["kind"], ("SUPERSEDES", "RETRACTS", "ALIAS"), scope)
        publisher = _text(link["publisher_id"], scope)
        _text(link["resolution_owner_id"], scope)
        old_id = _text(link["old_id"], scope)
        new_id = link["new_id"]
        if new_id is not None:
            _text(new_id, scope)
        if rid in relation_ids or old_id not in candidates or (new_id is not None and new_id not in candidates):
            _fail("RELATION_ID_OR_REFERENCE_INVALID", scope)
        relation_ids.add(rid)
        if (kind == "RETRACTS") != (new_id is None) or new_id == old_id:
            _fail("RELATION_SHAPE_INVALID", scope)
        old, new = candidates[old_id], candidates.get(new_id)
        fact_coordinate = _day(link["fact_coordinate"], scope)
        if fact_coordinate != old["coordinate"] or link["unit_basis"] != old["basis"]:
            _fail("RELATION_SCOPE_MISMATCH", scope)
        if new is not None and (new["coordinate"], new["until"], new["basis"]) != \
                (old["coordinate"], old["until"], old["basis"]):
            _fail("PERSISTENT_TRANSITION_NOT_IMPLEMENTED" if state_kind == "PERSISTENT" else
                  "RELATION_SCOPE_MISMATCH", scope)
        if kind != "ALIAS" and (publisher != old["publisher"] or
                                (new is not None and publisher != new["publisher"])):
            _fail("CROSS_PUBLISHER_RESOLUTION_NOT_IMPLEMENTED", scope)
        if kind == "ALIAS" and new["value"] != old["value"]:
            _fail("ALIAS_VALUE_MISMATCH", scope)
        public = _instant(link["public_upper"], scope)
        context.evidence(link["evidence"], kind + ":" + (new_id or "") + ":" + old_id, scope)
        usable = public <= K and old_id in eligible and (new is None or new_id in eligible)
        if usable and public < max(old["public"], new["public"] if new is not None else old["public"]):
            _fail("RELATION_PRECEDES_REFERENCED_ASSERTION", scope)
        relations.append({"relation_id": rid, "kind": kind, "new_id": new_id, "old_id": old_id,
                          "state": "UNAUTHENTICATED_MODEL_RELATION" if usable else "OUTSIDE_K_OR_APPLICABILITY",
                          "source_evidence_binding": link["evidence"]})
        if usable and kind == "SUPERSEDES":
            edges.setdefault(new_id, set()).add(old_id)
            if old_id in required:
                remove.add(old_id)
        elif usable and kind == "RETRACTS" and old_id in required:
            remove.add(old_id)
    visiting, visited = set(), set()

    def visit(node):
        if node in visiting:
            _fail("CYCLIC_SUPERSESSION", scope)
        if node in visited:
            return
        visiting.add(node)
        for child in sorted(edges.get(node, ())):
            visit(child)
        visiting.remove(node)
        visited.add(node)

    for node in sorted(edges):
        visit(node)
    active = {aid: a for aid, a in required.items() if aid not in remove}
    values = {a["value"] for a in active.values()}
    bases = {a["basis"] for a in active.values()}
    state = ("CAP_COMPONENT_UNAVAILABLE" if not active else
             "CAP_COMPONENT_BASIS_UNPROVEN" if len(bases) != 1 else
             "CAP_COMPONENT_CONFLICT" if len(values) != 1 else
             "MODEL_RESOLVED_SUPERSESSION" if remove else
             "MODEL_RESOLVED_EQUIVALENT" if len(active) > 1 else "MODEL_RESOLVED_SINGLE")
    value = next(iter(values)) if state.startswith("MODEL_RESOLVED") else None
    # Historical conflicts are retained even if a newer point is self-contained.
    older = {}
    for aid, a in eligible.items():
        if aid not in required:
            older.setdefault((a["coordinate"].isoformat(), a["basis"]), []).append(a)
    older_conflicts = [{"coordinate": key[0], "unit_basis": key[1],
                        "assertion_ids": sorted(a["id"] for a in items)}
                       for key, items in sorted(older.items()) if len({a["value"] for a in items}) > 1]
    receipt = {"scope": {"issuer_id": issuer_id, "class_id": class_id, "component": component},
               "state_kind": state_kind, "state": state,
               "selected_coordinate": selected_coordinate.isoformat() if selected_coordinate else None,
               "all_assertion_ids": sorted(candidates), "active_assertion_ids": sorted(active),
               "supplied_assertions": sorted(bundle["assertions"], key=lambda row: row["assertion_id"]),
               "bundle_content_binding": _binding(canonical_bytes(bundle)),
               "assertion_scope": "COMPLETE_SUPPLIED_BUNDLE_NOT_A_COMPLETE_PUBLIC_SOURCE_CENSUS",
               "exclusions": sorted(exclusions, key=lambda row: (row["assertion_id"], row["reason"])),
               "relations": sorted(relations, key=lambda row: row["relation_id"]),
               "older_conflicts_retained": older_conflicts,
               "active_values": [{"value": _rational_json(v),
                                  "assertion_ids": sorted(aid for aid, a in active.items() if a["value"] == v)}
                                 for v in sorted(values)],
               "modeled_value": _rational_json(value) if value is not None else None,
               "source_semantics_authenticated": False, "independent_evidence_count": None}
    return value, next(iter(bases)) if len(bases) == 1 else None, selected_coordinate, receipt


def _fx_rates(fx, context):
    _object(fx, ("series", "available_dates", "reference_date", "rates"), scope="fx")
    if fx["series"] != "ECB euro foreign exchange reference rates":
        _fail("FX_SERIES_OUTSIDE_POLICY", "fx")
    dates = [_day(s, "fx.available_dates") for s in _unique_strings(fx["available_dates"], 32, "fx.available_dates")]
    reference = _day(fx["reference_date"], "fx.reference_date")
    latest = max((s for s in dates if s <= D), default=None)
    if latest is None or reference != latest or (D - reference).days > 5:
        _fail("FX_COMMON_DATE_UNAVAILABLE", "fx")
    rates, receipts = {}, []
    for row in _array(fx["rates"], 64, "fx.rates"):
        _object(row, ("currency", "bundle"), scope="fx.rate")
        currency = _text(row["currency"], "fx.currency", 3)
        if len(currency) != 3 or not currency.isascii() or not currency.isalpha() or currency != currency.upper():
            _fail("CURRENCY_CODE_REQUIRED", "fx")
        if currency in rates or currency == "EUR":
            _fail("DUPLICATE_OR_EUR_DENOMINATOR_RATE", "fx")
        value, basis, _, receipt = resolve_assertions(row["bundle"], context, issuer_id="ECB_MODEL",
                    class_id=currency, component="FX_REFERENCE_RATE", fixed_date=reference, require_point=True)
        receipts.append(receipt)
        if value is None or basis != "UNITS_" + currency + "_PER_EUR":
            context.hold(receipt["state"] if value is None else "CAP_COMPONENT_BASIS_UNPROVEN", "fx/" + currency)
            rates[currency] = None
            continue
        if any(_day(a["coordinate"], "fx.assertion_date") not in dates for a in row["bundle"]["assertions"]):
            _fail("FX_ASSERTION_DATE_NOT_DECLARED", "fx")
        rates[currency] = value
    if "USD" not in rates:
        context.hold("FX_USD_REFERENCE_MISSING", "fx")
    receipt = {"reference_date": reference.isoformat(), "assertions": receipts,
               "source_date_completeness": "SUPPLIED_MODEL_DATES_ONLY"}
    if "USD" not in rates or any(value is None for value in rates.values()):
        return {}, receipt
    usd = rates["USD"]
    result = {c: _bounded_fraction(usd / value, "fx/" + c) for c, value in rates.items()}
    result["EUR"], result["USD"] = usd, Fraction(1)
    return result, receipt


def _class_cap(row, context, issuer_id, rates):
    _object(row, ("class_id", "kind", "d_basis", "shares", "price", "quote_scale",
                  "quote_scale_evidence", "currency", "counter", "calendar", "actions",
                  "declared_event_ids", "share_bridge_event_ids", "price_bridge_event_ids"), scope="class")
    cid = _text(row["class_id"], "class.class_id")
    scope = issuer_id + "/" + cid
    kind = _choice(row["kind"], ("ORDINARY", "ADR", "UNLISTED_PROXY", "ZERO_OR_CEASED"), scope)
    if kind != "ORDINARY":
        _fail("RICHER_CLASS_RIGHTS_OR_CEASED_FACT_NOT_IMPLEMENTED", scope)
    d_basis = _text(row["d_basis"], scope)
    currency = _text(row["currency"], scope, 3)
    if currency not in rates:
        _fail("FX_UNAVAILABLE", scope)
    _object(row["counter"], ("mic", "security_id"), scope=scope)
    _text(row["counter"]["mic"], scope)
    _text(row["counter"]["security_id"], scope)
    shares, share_basis, share_date, share_receipt = resolve_assertions(
        row["shares"], context, issuer_id=issuer_id, class_id=cid,
        component="ACTUAL_OUTSTANDING_ORDINARY_SHARES", maximum_age=183, require_point=True)
    price, price_basis, price_date, price_receipt = resolve_assertions(
        row["price"], context, issuer_id=issuer_id, class_id=cid,
        component="RAW_OFFICIAL_CLOSE/" + row["counter"]["mic"] + "/" + row["counter"]["security_id"] + "/" + currency,
        maximum_age=10, require_point=True)
    receipt = {"class_id": cid, "shares": share_receipt, "price": price_receipt,
               "modeled_cap_usd": None, "events": []}
    if shares is None or price is None:
        for item in (share_receipt, price_receipt):
            if not item["state"].startswith("MODEL_RESOLVED"):
                context.hold(item["state"], scope)
        return None, receipt
    calendar = [_day(s, scope) for s in _unique_strings(row["calendar"], 11, scope)]
    if any(not 0 <= (D - s).days <= 10 for s in calendar) or price_date not in calendar:
        _fail("SUPPLIED_PRICE_CALENDAR_MISMATCH", scope)
    age_sessions = sum(s > price_date for s in calendar)
    if age_sessions > 5:
        _fail("PRICE_TOO_OLD", scope)
    scale = rational(row["quote_scale"], scope=scope)
    context.evidence(row["quote_scale_evidence"], row["quote_scale"], scope)
    actions, ids, coordinates = [], set(), set()
    for event in _array(row["actions"], MAX_ACTIONS, scope):
        _object(event, ("event_id", "effective_date", "sequence", "kind", "public_upper", "value",
                        "before_basis", "after_basis", "evidence", "zero_evidence"), scope=scope)
        eid = _text(event["event_id"], scope)
        effective = _day(event["effective_date"], scope)
        sequence = _count(event["sequence"], scope)
        action_kind = _choice(event["kind"], ("DELTA", "SPLIT"), scope)
        before_basis = _text(event["before_basis"], scope)
        after_basis = _text(event["after_basis"], scope)
        if eid in ids or (effective, sequence) in coordinates:
            _fail("DUPLICATE_ACTION_OR_AMBIGUOUS_ORDER", scope)
        ids.add(eid)
        coordinates.add((effective, sequence))
        if effective in (share_date, price_date):
            _fail("SAME_DAY_ACTION_ORDER_UNPROVEN", scope)
        if not min(share_date, price_date) < effective <= D:
            _fail("ACTION_OUTSIDE_BRIDGE_INTERVAL", scope)
        if _instant(event["public_upper"], scope) > K:
            _fail("POST_CUTOFF_ACTION", scope)
        if event["value"] is None:
            _fail("MATERIAL_ACTION_QUANTITY_UNAVAILABLE", scope)
        zero_proved = False
        if event["zero_evidence"] is not None:
            context.evidence(event["zero_evidence"], "EXPLICIT_NO_CHANGE:" + eid, scope)
            zero_proved = True
        value = rational(event["value"], "delta" if action_kind == "DELTA" else "positive",
                         evidenced_zero=zero_proved, scope=scope)
        context.evidence(event["evidence"], event["value"], scope)
        if action_kind == "DELTA" and before_basis != after_basis:
            _fail("ADDITIVE_DELTA_UNIT_CHANGE", scope)
        if action_kind == "SPLIT" and before_basis == after_basis:
            _fail("SPLIT_REQUIRES_EXPLICIT_NEW_UNIT_BASIS", scope)
        actions.append((effective, sequence, eid, action_kind, value, before_basis, after_basis))
    if set(_unique_strings(row["declared_event_ids"], MAX_ACTIONS, scope)) != ids:
        _fail("ACTION_INVENTORY_SET_MISMATCH", scope)
    expected_share = {a[2] for a in actions if a[0] > share_date}
    expected_price = {a[2] for a in actions if a[0] > price_date and a[3] == "SPLIT"}
    if set(_unique_strings(row["share_bridge_event_ids"], MAX_ACTIONS, scope)) != expected_share or \
            set(_unique_strings(row["price_bridge_event_ids"], MAX_ACTIONS, scope)) != expected_price:
        _fail("EXPLICIT_BRIDGE_EVENT_SET_MISMATCH", scope)
    for effective, sequence, eid, action_kind, value, before_basis, after_basis in sorted(actions):
        if effective > share_date:
            if share_basis != before_basis:
                _fail("SHARE_ACTION_BASIS_MISMATCH", scope)
            shares = _bounded_fraction(shares + value if action_kind == "DELTA" else shares * value, scope)
            share_basis = after_basis
            if shares <= 0:
                _fail("NONPOSITIVE_RESULTING_CLASS_SHARES", scope)
        if effective > price_date and action_kind == "SPLIT":
            if price_basis != before_basis:
                _fail("STALE_PRICE_SPLIT_BASIS_UNPROVEN", scope)
            price = _bounded_fraction(price / value, scope)
            price_basis = after_basis
        receipt["events"].append({"event_id": eid, "effective_date": effective.isoformat(),
                                   "sequence": sequence, "kind": action_kind, "value": _rational_json(value)})
    if share_basis != d_basis or price_basis != d_basis:
        _fail("D_EQUIVALENT_PRICE_SHARE_BASIS_UNPROVEN", scope)
    value = _bounded_fraction(_bounded_fraction(_bounded_fraction(shares * price, scope) * scale, scope) * rates[currency], scope)
    if value <= 0:
        _fail("NONPOSITIVE_CLASS_CAP", scope)
    receipt.update({"modeled_cap_usd": _rational_json(value), "d_basis": d_basis,
                    "reported_share_age_days": (D - share_date).days,
                    "raw_price_age_days": (D - price_date).days,
                    "supplied_calendar_older_sessions": age_sessions,
                    "modeled_bridged_shares": _rational_json(shares),
                    "modeled_d_equivalent_price": _rational_json(price),
                    "quote_scale": _rational_json(scale), "usd_per_currency": _rational_json(rates[currency]),
                    "unreported_actions_known_absent": False})
    return value, receipt


def _record_caps(records, members, partitions, context, rates):
    by_id, issuers, caps, receipts, excluded = {}, set(), {}, [], []
    for row in _array(records, MAX_RECORDS, "records"):
        _object(row, ("record_id", "issuer_id", "eligibility", "primary_groups", "activity",
                      "exclusion_reason", "exclusion_evidence", "class_ids", "classes"), scope="record")
        rid = _text(row["record_id"], "record.record_id")
        if rid in by_id:
            _fail("DUPLICATE_RECORD_ID", "records")
        by_id[rid] = row
        issuer_id = row["issuer_id"]
        if issuer_id is not None:
            _text(issuer_id, "record.issuer_id")
            if issuer_id in issuers:
                _fail("DUPLICATE_ECONOMIC_ISSUER", "records")
            issuers.add(issuer_id)
    # Source-security lines may share a record, but no D record can disappear.
    member_record_ids = {row["record_id"] for row in members.values()}
    if member_record_ids != set(by_id):
        _fail("MEMBERSHIP_RECORD_SET_MISMATCH", "records")
    for rid in sorted(by_id):
        row = by_id[rid]
        issuer_id = row["issuer_id"]
        eligibility = _choice(row["eligibility"], ("ELIGIBLE", "EXCLUDED", "UNRESOLVED"), rid)
        groups = _unique_strings(row["primary_groups"], len(GROUPS), rid, GROUPS)
        activity = row["activity"]
        if activity is not None:
            _choice(activity, ACTIVITIES, rid)
        class_ids = _unique_strings(row["class_ids"], MAX_CLASSES, rid)
        classes = _array(row["classes"], MAX_CLASSES, rid)
        if eligibility == "EXCLUDED":
            reason = _choice(row["exclusion_reason"], ("INSTRUMENT_OUTSIDE", "ACTIVITY_OUTSIDE", "PRIMARY_OUTSIDE"), rid)
            context.evidence(row["exclusion_evidence"], reason, rid)
            excluded.append({"record_id": rid, "issuer_id": issuer_id, "reason": reason,
                             "semantic_status": "UNAUTHENTICATED_MODEL_EXCLUSION"})
            continue
        if row["exclusion_reason"] is not None or row["exclusion_evidence"] is not None:
            _fail("EXCLUSION_FIELDS_ON_NONEXCLUDED_RECORD", rid)
        if eligibility == "UNRESOLVED" or issuer_id is None or activity is None or not groups:
            context.hold("POTENTIALLY_ELIGIBLE_RECORD_UNRESOLVED", rid)
            receipts.append({"record_id": rid, "issuer_id": issuer_id, "modeled_cap_usd": None,
                             "state": "UNRESOLVED_NOT_DROPPED"})
            continue
        actual_groups = {partitions[m["partition_id"]] for m in members.values()
                         if m["record_id"] == rid and m["primary_status"] == "PRIMARY" and m["instrument"] != "EXCLUDED"}
        if actual_groups != set(groups):
            context.hold("PRIMARY_GROUP_MEMBERSHIP_MISMATCH", rid)
            continue
        country = min(groups, key=lambda g: (priority_hash("primary-jurisdiction", issuer_id, g), g.encode("utf-8")))
        observed_ids = []
        for cls in classes:
            if type(cls) is not dict or "class_id" not in cls:
                _fail("CLASS_SHAPE", rid)
            observed_ids.append(_text(cls["class_id"], rid))
        if not class_ids or len(set(observed_ids)) != len(observed_ids) or set(observed_ids) != set(class_ids):
            context.hold("ECONOMIC_CLASS_SET_INCOMPLETE_OR_DUPLICATE", rid)
            receipts.append({"record_id": rid, "issuer_id": issuer_id, "modeled_cap_usd": None,
                             "state": "CLASS_SET_HELD"})
            continue
        total, class_receipts, failed = Fraction(0), [], False
        for cls in sorted(classes, key=lambda item: item["class_id"]):
            try:
                value, class_receipt = _class_cap(cls, context, issuer_id, rates)
                class_receipts.append(class_receipt)
                if value is None:
                    failed = True
                else:
                    try:
                        total = _bounded_fraction(total + value, rid)
                    except ContractError as exc:
                        context.hold(exc.code, exc.scope)
                        failed = True
            except ContractError as exc:
                context.hold(exc.code, exc.scope)
                class_receipts.append({"class_id": cls["class_id"], "modeled_cap_usd": None,
                                       "state": exc.code})
                failed = True
        receipt = {"record_id": rid, "issuer_id": issuer_id, "assigned_primary_group": country,
                   "all_supplied_primary_groups": sorted(groups), "activity": activity,
                   "classes": class_receipts, "modeled_cap_usd": None,
                   "state": "CAP_FRAME_INCOMPLETE" if failed else "MODEL_RESOLVED_CAP"}
        if failed:
            context.hold("CAP_FRAME_INCOMPLETE", rid)
        else:
            receipt["modeled_cap_usd"] = _rational_json(total)
            caps[issuer_id] = {"issuer_id": issuer_id, "record_id": rid, "country": country,
                               "activity": activity, "cap": total}
        receipts.append(receipt)
    return caps, receipts, excluded


def absolute_band(value):
    if not isinstance(value, Fraction) or value <= 0:
        _fail("POSITIVE_EXACT_CAP_REQUIRED", "absolute_band")
    return ("MICRO" if value < 250000000 else "S_ABS" if value < 2000000000 else
            "M_ABS" if value < 10000000000 else "L_ABS")


def relative_pools(caps):
    """All 42 artificial pools; equal values always move to the higher band."""
    pools, labelled = [], []
    for country in GROUPS:
        for activity in ACTIVITIES:
            members = [r for r in caps.values() if r["country"] == country and r["activity"] == activity]
            members.sort(key=lambda r: (-r["cap"], r["issuer_id"].encode("utf-8")))
            n = len(members)
            k1, k2 = (n + 1) // 2, (3 * n + 3) // 4
            t1, t2 = (members[k1 - 1]["cap"], members[k2 - 1]["cap"]) if n else (None, None)
            counts = {band: 0 for band in BANDS}
            for row in members:
                value = row["cap"]
                band = "L" if value >= t1 else "M" if value >= t2 else "S"
                counts[band] += 1
                labelled.append({"issuer_id": row["issuer_id"], "record_id": row["record_id"],
                                 "country": country, "activity": activity, "band": band,
                                 "cell": activity + "|" + band,
                                 "absolute_band": absolute_band(value),
                                 "modeled_cap_usd": _rational_json(value)})
            pools.append({"country": country, "activity": activity, "modeled_N": n,
                          "k1": k1 if n else None, "k2": k2 if n else None,
                          "t1": _rational_json(t1) if t1 is not None else None,
                          "t2": _rational_json(t2) if t2 is not None else None,
                          "band_counts": counts, "state": "MODEL_POOL_COMPLETE" if n else "MODEL_EMPTY_POOL"})
    return pools, labelled


def _flow_inputs(candidates, country_demand, cell_demand):
    if type(country_demand) is not dict or type(cell_demand) is not dict or \
            not 0 < len(country_demand) <= 7 or not 0 < len(cell_demand) <= 18:
        _fail("FLOW_DEMAND_SHAPE", "flow")
    for vector in (country_demand, cell_demand):
        for key, value in vector.items():
            _text(key, "flow.key")
            _count(value, "flow.demand")
    target = sum(country_demand.values())
    if target != sum(cell_demand.values()) or target > 120:
        _fail("FLOW_DEMAND_TOTAL_MISMATCH_OR_LIMIT", "flow")
    seen = set()
    for row in _array(candidates, MAX_RECORDS, "flow.candidates"):
        if type(row) is not dict or not {"issuer_id", "country", "cell"} <= row.keys():
            _fail("FLOW_CANDIDATE_SHAPE", "flow")
        issuer = _text(row["issuer_id"], "flow.issuer")
        if issuer in seen:
            _fail("DUPLICATE_ECONOMIC_ISSUER", "flow")
        seen.add(issuer)
        if row["country"] not in country_demand or row["cell"] not in cell_demand:
            _fail("FLOW_CANDIDATE_OUTSIDE_DEMANDS", "flow")
    return target


def capacity_flow(candidates, country_demand, cell_demand):
    """Bounded integer maxflow with complete matrix and actual residual mincut.

    This lower-level mathematical helper accepts artificial capacities only; it
    neither reads source receipts nor bypasses diagnose()'s real-source holds.
    """
    target = _flow_inputs(candidates, country_demand, cell_demand)
    countries, cells = sorted(country_demand), sorted(cell_demand)
    matrix = Counter((r["country"], r["cell"]) for r in candidates)
    source, sink = ("source", ""), ("sink", "")
    capacity, residual, adjacency = {}, {}, {}

    def edge(left, right, value):
        capacity[left, right] = value
        residual[left, right], residual[right, left] = value, 0
        adjacency.setdefault(left, []).append(right)
        adjacency.setdefault(right, []).append(left)

    for country in countries:
        edge(source, ("country", country), country_demand[country])
    for country in countries:
        for cell in cells:
            edge(("country", country), ("cell", cell), matrix[country, cell])
    for cell in cells:
        edge(("cell", cell), sink, cell_demand[cell])
    flow = 0
    while flow < target:
        parents, queue = {source: None}, deque([source])
        while queue and sink not in parents:
            left = queue.popleft()
            for right in adjacency[left]:
                if right not in parents and residual[left, right] > 0:
                    parents[right] = left
                    queue.append(right)
        if sink not in parents:
            break
        increment, right = target - flow, sink
        while parents[right] is not None:
            left = parents[right]
            increment = min(increment, residual[left, right])
            right = left
        right = sink
        while parents[right] is not None:
            left = parents[right]
            residual[left, right] -= increment
            residual[right, left] += increment
            right = left
        flow += increment
    reachable, queue = {source}, deque([source])
    while queue:
        left = queue.popleft()
        for right in adjacency[left]:
            if residual[left, right] > 0 and right not in reachable:
                reachable.add(right)
                queue.append(right)
    cut_edges = [{"from": list(left), "to": list(right), "capacity": value}
                 for (left, right), value in sorted(capacity.items())
                 if left in reachable and right not in reachable]
    cut_capacity = sum(edge["capacity"] for edge in cut_edges)
    if cut_capacity != flow:
        _fail("INTERNAL_FLOW_CUT_INCONSISTENCY", "flow")
    return {"target": target, "achieved_flow": flow,
            "country_demands": {c: country_demand[c] for c in countries},
            "cell_demands": {c: cell_demand[c] for c in cells},
            "capacity_matrix": {country: {cell: matrix[country, cell] for cell in cells}
                                for country in countries},
            "allocation": {country: {cell: capacity[("country", country), ("cell", cell)] -
                                       residual[("country", country), ("cell", cell)] for cell in cells}
                           for country in countries},
            "deficient_cut": None if flow == target else {
                "reachable_countries": sorted(n[1] for n in reachable if n[0] == "country"),
                "reachable_cells": sorted(n[1] for n in reachable if n[0] == "cell"),
                "edges": cut_edges, "capacity": cut_capacity, "deficit": target - flow}}


def lexicographic_selection(candidates, country_demand, cell_demand):
    """Exact residual inclusion algorithm, independently testable on tiny sets."""
    target = _flow_inputs(candidates, country_demand, cell_demand)
    initial = capacity_flow(candidates, country_demand, cell_demand)
    if initial["achieved_flow"] != target:
        return {"state": "MODEL_INFEASIBLE", "selected_issuer_ids": None,
                "initial_flow": initial, "trials": []}
    ordered = sorted(candidates, key=lambda row: _priority(row["issuer_id"]))
    country_left, cell_left = dict(country_demand), dict(cell_demand)
    selected, trials = [], []
    for index, row in enumerate(ordered):
        if len(selected) == target:
            trials.extend({"issuer_id": r["issuer_id"], "decision": "NOT_NEEDED_AFTER_QUOTA_COMPLETE"}
                          for r in ordered[index:])
            break
        # Excludes the current row: it cannot satisfy its own trial demand.
        remaining = ordered[index + 1:]
        trial_country, trial_cell = dict(country_left), dict(cell_left)
        trial_country[row["country"]] -= 1
        trial_cell[row["cell"]] -= 1
        if min(trial_country.values()) < 0 or min(trial_cell.values()) < 0:
            trials.append({"issuer_id": row["issuer_id"], "decision": "QUOTA_ALREADY_FULL"})
            continue
        completion = capacity_flow(remaining, trial_country, trial_cell)
        feasible = completion["achieved_flow"] == completion["target"]
        trial = {"issuer_id": row["issuer_id"], "decision": "INCLUDE" if feasible else "EXCLUDE_INFEASIBLE_COMPLETION",
                 "remaining_target": completion["target"], "achieved_flow": completion["achieved_flow"],
                 "current_removed_before_trial": True}
        if feasible:
            selected.append(row["issuer_id"])
            country_left, cell_left = trial_country, trial_cell
        else:
            trial["deficient_completion"] = completion
        trials.append(trial)
    if len(selected) != target or any(country_left.values()) or any(cell_left.values()):
        _fail("INTERNAL_SELECTION_INCONSISTENCY", "selection")
    return {"state": "MODEL_FEASIBLE", "selected_issuer_ids": selected,
            "initial_flow": initial, "trials": trials,
            "final_country_demands": country_left, "final_cell_demands": cell_left}


def select_cohort(labelled):
    selected, deficits, nonint_decisions = [], [], []
    for country in GROUPS[:4]:
        for activity in ACTIVITIES:
            for band in BANDS:
                rows = sorted((row for row in labelled if row["country"] == country and
                               row["activity"] == activity and row["band"] == band),
                              key=lambda row: _priority(row["issuer_id"]))
                quota = QUOTA[band]
                if len(rows) < quota:
                    deficits.append({"country": country, "activity": activity, "band": band,
                                     "available": len(rows), "required": quota, "shortfall": quota - len(rows)})
                selected.extend(row["issuer_id"] for row in rows[:quota])
                nonint_decisions.extend({"issuer_id": row["issuer_id"],
                    "decision": "INCLUDE_IF_FULL_DESIGN_FEASIBLE" if index < quota else "OUTSIDE_FIXED_PRIORITY_QUOTA"}
                    for index, row in enumerate(rows))
    international = lexicographic_selection([r for r in labelled if r["country"] in INT_COUNTRIES],
        {country: 8 for country in INT_COUNTRIES},
        {activity + "|" + band: QUOTA[band] for activity in ACTIVITIES for band in BANDS})
    if deficits or international["state"] != "MODEL_FEASIBLE":
        return {"state": "MODEL_QUOTA_INFEASIBLE", "selected_issuer_ids": None,
                "non_INT_deficits": deficits, "non_INT_decisions": nonint_decisions,
                "INT": international, "quota_audit": None}
    selected.extend(international["selected_issuer_ids"])
    selected.sort(key=_priority)
    lookup = {row["issuer_id"]: row for row in labelled}
    strata = Counter()
    strata_activity = Counter()
    strata_cells = Counter()
    int_countries, size_counts = Counter(), Counter()
    for issuer_id in selected:
        row = lookup[issuer_id]
        stratum = row["country"] if row["country"] in GROUPS[:4] else "INT"
        strata[stratum] += 1
        strata_activity[stratum + "|" + row["activity"]] += 1
        strata_cells[stratum + "|" + row["cell"]] += 1
        size_counts[row["band"]] += 1
        if stratum == "INT":
            int_countries[row["country"]] += 1
    if len(set(selected)) != 120 or len(selected) != 120 or any(strata[s] != 24 for s in STRATA) or \
            any(strata_activity[s + "|" + a] != 4 for s in STRATA for a in ACTIVITIES) or \
            any(strata_cells[s + "|" + a + "|" + b] != QUOTA[b] for s in STRATA for a in ACTIVITIES for b in BANDS) or \
            any(int_countries[c] != 8 for c in INT_COUNTRIES):
        _fail("INTERNAL_120_QUOTA_AUDIT_FAILED", "selection")
    return {"state": "MODEL_120_FEASIBLE", "selected_issuer_ids": selected,
            "non_INT_deficits": [], "non_INT_decisions": nonint_decisions, "INT": international,
            "quota_audit": {"unique_issuers": len(set(selected)), "strata": dict(strata),
                "strata_activity": dict(strata_activity), "strata_activity_size": dict(strata_cells),
                "INT_countries": dict(int_countries), "size_counts": dict(size_counts)}}


COUNT_FIELDS = ("source_declared_total", "exhaustive_total", "raw_record_count", "parsed_record_count",
                "duplicates_resolved_count", "anchor_count", "resulting_d_member_count", "identity_resolved_issuer_count",
                "evidenced_out_of_scope_count", "potentially_eligible_omission_count", "unresolved_potentially_eligible_count") + \
               tuple("event_" + kind for kind in EVENT_KINDS)


def _supplied_counts(value, expected, context):
    _object(value, (), COUNT_FIELDS, scope="counts")
    result = {}
    for field in COUNT_FIELDS:
        if field not in value:
            state, number = "MISSING", None
        elif value[field] is None:
            state, number = "UNKNOWN", None
        elif field == "source_declared_total" and value[field] == "NOT_PUBLISHED":
            state, number = "NOT_PUBLISHED", None
        elif type(value[field]) is int and 0 <= value[field] < 10**12:
            state, number = "SUPPLIED_VALID_COUNT", value[field]
        else:
            state, number = "INVALID_COUNT", None
        result[field] = {"state": state, "supplied_value": number,
                         "source_truth_verified": False}
        if state in ("MISSING", "UNKNOWN", "INVALID_COUNT"):
            context.hold("SUPPLIED_COUNT_" + state, "counts/" + field)
        elif state == "SUPPLIED_VALID_COUNT" and field in expected and number != expected[field]:
            result[field]["reconciliation"] = "MISMATCH"
            result[field]["computed_from_supplied_records"] = expected[field]
            context.hold("SUPPLIED_COUNT_RECONCILIATION_MISMATCH", "counts/" + field)
        elif state == "SUPPLIED_VALID_COUNT" and field in expected:
            result[field]["reconciliation"] = "MATCH_SUPPLIED_RECORDS_ONLY"
    return result


def _claims(value):
    boolean_fields = ("producer_success", "source_authority_verified", "history_proven", "rights_verified")
    string_fields = ("owner_id", "receipt_sha256", "source_path", "actual_F")
    _object(value, (), boolean_fields + string_fields, scope="claims")
    for field in boolean_fields:
        if field in value and type(value[field]) is not bool:
            _fail("CLAIM_BOOLEAN_SHAPE", "claims")
    for field in string_fields:
        if field in value and value[field] is not None:
            _text(value[field], "claims", 2048)
    return {"state": "UNTRUSTED_CLAIMS_HAVE_NO_AUTHORITY_EFFECT",
            "supplied_field_names": sorted(value), "content_binding": _binding(canonical_bytes(value))}


STRESS_LABELS = ("IDENTITY_ALIAS", "ANON_CONCENTRATION", "DUAL_FLOW", "TERMINATION_EXPLICIT",
                 "SUPPLIER_LIST_STALE", "SEGMENT_RECAST", "DIMENSION_CUSTOM", "QUANTITY_DENOMINATOR")


def _stress_cases(cases, context, selected, labelled):
    case_ids, rows = set(), []
    lookup = {r["issuer_id"]: r for r in labelled}
    for row in _array(cases, 128, "stress_cases"):
        _object(row, ("case_id", "stratum", "issuer_id", "document_id", "document_role", "locator", "label",
                      "evidence", "independent_review_id", "before_vendor_outputs"), scope="stress_case")
        case_id = _text(row["case_id"], "stress_case")
        if case_id in case_ids:
            _fail("DUPLICATE_STRESS_CASE_ID", "stress_case")
        case_ids.add(case_id)
        stratum = _choice(row["stratum"], STRATA, "stress_case")
        issuer_id = _text(row["issuer_id"], "stress_case")
        document_id = _text(row["document_id"], "stress_case")
        locator = _text(row["locator"], "stress_case")
        _choice(row["document_role"], ("ANNUAL_2023", "ANNUAL_2024", "ANNUAL_2025", "INTERIM_OR_MATERIAL_EVENT_2026"), "stress_case")
        label = _choice(row["label"], STRESS_LABELS, "stress_case")
        if row["independent_review_id"] is not None:
            _text(row["independent_review_id"], "stress_case")
        if type(row["before_vendor_outputs"]) is not bool:
            _fail("STRESS_CASE_CLAIM_SHAPE", "stress_case")
        context.evidence(row["evidence"], label, "stress_case")
        member = lookup.get(issuer_id)
        actual_stratum = (member["country"] if member and member["country"] in GROUPS[:4] else "INT")
        in_model = selected is not None and issuer_id in selected and actual_stratum == stratum
        rows.append({"case_id": case_id, "issuer_id": issuer_id, "stratum": stratum,
                     "document_id": document_id, "locator": locator, "label": label,
                     "model_membership": "WITHIN_MODELED_COHORT" if in_model else "NOT_BOUND_TO_MODELED_COHORT",
                     "genuine_case_or_independent_review_verified": False})
    rows.sort(key=lambda r: (r["issuer_id"].encode("utf-8"), r["document_id"].encode("utf-8"),
                             r["locator"].encode("utf-8"), r["case_id"].encode("utf-8")))
    counts = Counter(r["stratum"] for r in rows if r["model_membership"] == "WITHIN_MODELED_COHORT")
    return {"supplied_case_count": len(rows), "cases": rows,
            "modeled_within_cohort_counts": {s: counts[s] for s in STRATA},
            "modeled_shortfall_per_stratum": {s: max(0, 6 - counts[s]) for s in STRATA},
            "actual_genuine_case_count": None, "actual_genuine_case_shortfall": None,
            "genuine_case_requirement": "NOT_ESTABLISHED_30_TOTAL_AND_6_PER_STRATUM",
            "independent_review_and_pre_vendor_sequence": "UNVERIFIED",
            "missing_cases_replace_issuers": False}


def _closed_nested_shapes(request):
    """Check all nested key sets even when an earlier semantic gate will hold."""
    assertion_keys = ("assertion_id", "publisher_id", "coordinate", "valid_to", "public_upper", "value", "unit_basis", "status", "evidence")
    relation_keys = ("relation_id", "kind", "publisher_id", "new_id", "old_id", "fact_coordinate", "unit_basis", "public_upper", "evidence", "resolution_owner_id")

    def evidence(value):
        _object(value, ("source_id", "start", "end"), scope="evidence")

    def bundle(value):
        _object(value, ("state_kind", "assertions", "relations"), scope="bundle")
        for row in _array(value["assertions"], MAX_ASSERTIONS, "bundle.assertions"):
            _object(row, assertion_keys, scope="assertion")
            evidence(row["evidence"])
        for row in _array(value["relations"], 32, "bundle.relations"):
            _object(row, relation_keys, scope="relation")
            evidence(row["evidence"])

    for row in _array(request["records"], MAX_RECORDS, "records"):
        _object(row, ("record_id", "issuer_id", "eligibility", "primary_groups", "activity", "exclusion_reason", "exclusion_evidence", "class_ids", "classes"), scope="record")
        if row["exclusion_evidence"] is not None:
            evidence(row["exclusion_evidence"])
        for cls in _array(row["classes"], MAX_CLASSES, "classes"):
            _object(cls, ("class_id", "kind", "d_basis", "shares", "price", "quote_scale", "quote_scale_evidence", "currency", "counter", "calendar", "actions", "declared_event_ids", "share_bridge_event_ids", "price_bridge_event_ids"), scope="class")
            bundle(cls["shares"])
            bundle(cls["price"])
            evidence(cls["quote_scale_evidence"])
            _object(cls["counter"], ("mic", "security_id"), scope="counter")
            for event in _array(cls["actions"], MAX_ACTIONS, "actions"):
                _object(event, ("event_id", "effective_date", "sequence", "kind", "public_upper", "value", "before_basis", "after_basis", "evidence", "zero_evidence"), scope="action")
                evidence(event["evidence"])
                if event["zero_evidence"] is not None:
                    evidence(event["zero_evidence"])
    fx = request["fx"]
    _object(fx, ("series", "available_dates", "reference_date", "rates"), scope="fx")
    for row in _array(fx["rates"], 64, "fx.rates"):
        _object(row, ("currency", "bundle"), scope="fx.rate")
        bundle(row["bundle"])
    history = request["history"]
    _object(history, ("kind", "target_date", "anchor_date", "anchor_public_upper", "partitions", "declared_partition_ids", "anchor_members", "target_members", "anchor_source_id", "target_source_id", "events_source_id", "events", "coverage_start", "coverage_end", "covered_event_kinds", "declared_event_ids", "expected_anchor_member_ids", "expected_target_member_ids"), scope="history")
    member_keys = ("member_id", "record_id", "partition_id", "instrument", "primary_status")
    for field in ("anchor_members", "target_members"):
        for row in _array(history[field], MAX_RECORDS, "history." + field):
            _object(row, member_keys, scope="member")
    for row in _array(history["partitions"], 128, "history.partitions"):
        _object(row, ("partition_id", "jurisdiction"), scope="partition")
    for row in _array(history["events"], MAX_EVENTS, "history.events"):
        _object(row, ("event_id", "effective_date", "sequence", "kind", "public_upper", "before", "after"), scope="membership_event")
        for field in ("before", "after"):
            for state in _array(row[field], MAX_RECORDS, "event." + field):
                _object(state, member_keys, scope="member")
    for row in _array(request["stress_cases"], 128, "stress_cases"):
        _object(row, ("case_id", "stratum", "issuer_id", "document_id", "document_role", "locator", "label", "evidence", "independent_review_id", "before_vendor_outputs"), scope="stress_case")
        evidence(row["evidence"])


DEFERRED_CONTRACTS = (
    "AUTHENTICATED_REAL_SOURCE_ADMISSION_INTERFACE_NOT_SELECTED",
    "REAL_VENUE_TIMEZONE_PARTITION_AND_PUBLICATION_AUTHORITY_NOT_VERIFIED",
    "CANONICAL_ISSUER_PRIMARY_ACTIVITY_AND_PERIMETER_SEMANTICS_NOT_VERIFIED",
    "SOURCE_SEARCH_SCOPE_AND_UNOBSERVED_ACTION_COMPLETENESS_NOT_VERIFIED",
    "MULTICOUNTER_PRIMARY_CHOICE_AND_REAL_EXCHANGE_CALENDARS_NOT_VERIFIED",
    "CROSS_PUBLISHER_RECONCILIATION_AND_PERSISTENT_INTERVAL_TRANSITIONS_NOT_IMPLEMENTED",
    "ADR_UNLISTED_PROXY_AND_ZERO_CEASED_CLASS_SEMANTICS_NOT_IMPLEMENTED",
    "SAME_DAY_ACTION_VERSUS_MEASUREMENT_ORDER_NOT_IMPLEMENTED",
    "GENUINE_DOCUMENT_STRESS_CASES_AND_PRE_VENDOR_SEQUENCE_NOT_VERIFIED",
    "SEGMENT_ROLE_SUPPLEMENT_AND_POST_UNBLINDING_REPLACEMENT_NOT_IMPLEMENTED",
)


def _base_result():
    return {"schema": "research.gmi.wp02.source_diagnostic/v1", "status": "STRUCTURAL_ONLY",
            "readiness": "NOT_READY", "request_mode": "REAL_SOURCE", "model_state": "NOT_RUN",
            "policy_binding": None, "request_binding": None,
            "authority": {"admission": "NOT_ADMITTED", "rank": False, "size": False, "trade": False,
                          "prediction": False, "production": False, "export": False, "training": False,
                          "graph": False, "source_authority_authenticated": False,
                          "source_truth_authenticated": False, "canonical_issuer_identity_verified": False},
            "real_inputs": {"eligible_population_count": None, "per_pool_cardinalities": None,
                            "selected_cohort": None, "quantiles": None, "resolved_capitalizations": None,
                            "actual_F": None, "actual_INT_flow": None},
            "axes": {"receipt_structure_state": "NOT_CHECKED",
                     "retained_byte_integrity_state": "NOT_CHECKED",
                     "source_authority_verification_state": "SOURCE_AUTHORITY_UNVERIFIED",
                     "historical_coverage_verification_state": "FRAME_HISTORY_UNPROVEN",
                     "entitlement_verification_state": "SOURCE_RIGHTS_UNVERIFIED",
                     "derivation_reconciliation_state": "NOT_CHECKED"},
            "holds": [{"code": code, "scope": "real_source"} for code in (
                "SOURCE_AUTHORITY_UNVERIFIED", "SOURCE_RIGHTS_UNVERIFIED", "FRAME_HISTORY_UNPROVEN")],
            "supplied_source_diagnostics": [], "supplied_counts": None, "untrusted_claims": None,
            "supplied_record_checks": None, "synthetic": None, "stress_cases": None,
            "D": D.isoformat(), "K": "2026-10-09T00:00:00Z", "actual_F": None,
            "deferred_contracts": list(DEFERRED_CONTRACTS),
            "limits": {"input_bytes": MAX_INPUT, "output_bytes": MAX_OUTPUT,
                       "records": MAX_RECORDS, "sources": MAX_SOURCES, "source_bytes_each": MAX_SOURCE_BYTES,
                       "classes_each": MAX_CLASSES, "assertions_per_bundle": MAX_ASSERTIONS,
                       "membership_events": MAX_EVENTS, "actions_per_class": MAX_ACTIONS,
                       "JSON_depth": MAX_DEPTH, "JSON_lexical_tokens": MAX_TOKENS,
                       "derived_rational_numerator_or_denominator_bits": MAX_DERIVED_BITS},
            "scope": "SUPPLIED_RECORD_COHERENCE_AND_ARTIFICIAL_MODEL_ONLY_NO_REAL_SOURCE_ADAPTER"}


def _finish(result):
    result["holds"] = [{"code": code, "scope": scope} for code, scope in sorted(
        {(row["code"], row["scope"]) for row in result["holds"]})]
    try:
        canonical_bytes(result)
    except ContractError as exc:
        refused = _base_result()
        refused["policy_binding"] = result["policy_binding"]
        refused["request_binding"] = result["request_binding"]
        refused["request_mode"] = result["request_mode"]
        refused["model_state"] = "OUTPUT_REFUSED"
        refused["axes"]["receipt_structure_state"] = "OUTPUT_BUDGET_REFUSAL"
        refused["holds"].append({"code": exc.code, "scope": "output"})
        return refused
    return result


def diagnose(request_bytes, *, policy_bytes, adoption_bytes):
    """Inspect bounded JSON bytes; synthetic mode cannot promote real authority.

    Missing mode means REAL_SOURCE. Contract failures are explicit structured
    refusals with null real outputs. No caller-provided verdict is trusted.
    """
    result = _base_result()
    context = None
    try:
        result["policy_binding"] = bind_policy(policy_bytes, adoption_bytes)
        request = _json(request_bytes)
        result["request_binding"] = {"raw": _binding(request_bytes),
                                     "canonical_content": _binding(canonical_bytes(request)),
                                     "scope": "INPUT_CONTENT_IDENTITY_NOT_SOURCE_AUTHENTICATION"}
        _object(request, ("schema", "sources", "records", "history", "fx", "counts", "stress_cases", "claims"),
                ("mode",), scope="request")
        if request["schema"] != "research.gmi.wp02.source_diagnostic_request/v1":
            _fail("REQUEST_SCHEMA_MISMATCH", "request")
        mode = _choice(request.get("mode", "REAL_SOURCE"), ("REAL_SOURCE", "SYNTHETIC_MODEL"), "request.mode")
        result["request_mode"] = mode
        _closed_nested_shapes(request)
        result["untrusted_claims"] = _claims(request["claims"])
        context = _Context(request["sources"])
        result["supplied_source_diagnostics"] = sorted(context.source_receipts, key=lambda r: r["source_id"])
        result["axes"]["retained_byte_integrity_state"] = (
            "SUPPLIED_BYTES_MATCH_SELF_DECLARED_BINDINGS" if all(r["integrity"] == "MATCH" for r in context.source_receipts)
            else "SUPPLIED_BYTE_BINDING_MISMATCH")
        members, partitions, history_receipt = {}, {}, None
        try:
            members, partitions, history_receipt = reconcile_history(request["history"], context)
        except ContractError as exc:
            context.hold(exc.code, exc.scope)
        rates, fx_receipt = {}, None
        try:
            rates, fx_receipt = _fx_rates(request["fx"], context)
        except ContractError as exc:
            context.hold(exc.code, exc.scope)
        caps, cap_receipts, exclusions = {}, [], []
        if history_receipt is not None:
            try:
                caps, cap_receipts, exclusions = _record_caps(request["records"], members, partitions, context, rates)
            except ContractError as exc:
                context.hold(exc.code, exc.scope)
        records = request["records"]
        anchor_count = len(request["history"]["anchor_members"])
        event_counts = Counter(row["kind"] for row in request["history"]["events"] if type(row["kind"]) is str)
        expected = {"source_declared_total": anchor_count, "exhaustive_total": anchor_count,
                    "raw_record_count": anchor_count, "parsed_record_count": anchor_count,
                    "anchor_count": anchor_count, "potentially_eligible_omission_count": 0}
        if history_receipt is not None:
            expected.update({"resulting_d_member_count": len(members),
                "duplicates_resolved_count": len(members) - len({r["record_id"] for r in members.values()}),
                "identity_resolved_issuer_count": len({r["issuer_id"] for r in records if type(r["issuer_id"]) is str}),
                "evidenced_out_of_scope_count": sum(r["eligibility"] == "EXCLUDED" for r in records),
                "unresolved_potentially_eligible_count": sum(r["eligibility"] != "EXCLUDED" and
                    (r["eligibility"] == "UNRESOLVED" or r["issuer_id"] is None or r["activity"] is None or not r["primary_groups"])
                    for r in records)})
        expected.update({"event_" + kind: event_counts[kind] for kind in EVENT_KINDS})
        result["supplied_counts"] = _supplied_counts(request["counts"], expected, context)
        pools, labelled, selection = None, [], None
        if mode == "SYNTHETIC_MODEL" and not context.holds:
            pools, labelled = relative_pools(caps)
            selection = select_cohort(labelled)
            if selection["state"] != "MODEL_120_FEASIBLE":
                context.hold("MODEL_QUOTA_INFEASIBLE", "synthetic.selection")
        selected = selection["selected_issuer_ids"] if selection else None
        result["stress_cases"] = _stress_cases(request["stress_cases"], context, selected, labelled)
        result["supplied_record_checks"] = {
            "input_record_count": len(records), "input_source_count": len(request["sources"]),
            "numeric_spans_reconciled": context.span_checks,
            "history_set_reconciliation": history_receipt["state"] if history_receipt else "NOT_RECONCILED",
            "real_source_semantics_derived": False}
        result["axes"]["receipt_structure_state"] = "CLOSED_SHAPES_CHECKED" if not context.holds else "CHECKED_WITH_TYPED_HOLDS"
        result["axes"]["derivation_reconciliation_state"] = "SUPPLIED_RECORD_MODEL_RECONCILED" if not context.holds else "SUPPLIED_RECORD_DERIVATION_HELD"
        if mode == "SYNTHETIC_MODEL":
            result["model_state"] = "ARTIFICIAL_MODEL_COMPLETE" if not context.holds else "ARTIFICIAL_MODEL_NOT_READY"
            result["synthetic"] = {"label": "ARTIFICIAL_PREMISES_NOT_REAL_ISSUERS_OR_SOURCE_TRUTH",
                "modeled_population_count": len(caps) if pools is not None else None,
                "modeled_reference_pools": pools, "modeled_candidates": sorted(labelled, key=lambda r: _priority(r["issuer_id"])),
                "modeled_cap_receipts": cap_receipts, "modeled_history": history_receipt, "modeled_fx": fx_receipt,
                "modeled_exclusions": exclusions, "selection": selection,
                "seed": SEED, "seed_rotation": False,
                "hash_encoding": "SHA256(uint64be UTF8 byte lengths and exact bytes for domain, fixed seed, fields)",
                "real_identity_history_rights_and_evidence_authentication": False,
                "genuine_case_requirement_satisfied": False}
        result["holds"].extend(context.holds)
    except ContractError as exc:
        result["axes"]["receipt_structure_state"] = "REFUSED"
        result["model_state"] = "INPUT_REFUSED"
        result["holds"].append({"code": exc.code, "scope": exc.scope})
        if context is not None:
            result["holds"].extend(context.holds)
    return _finish(result)


def main(argv=None):
    """Explicit bounded regular-file reader; emits JSON, never writes artifacts."""
    import argparse
    import os
    import stat
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--adoption", required=True)
    args = parser.parse_args(argv)

    def read(path, limit):
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        fd = os.open(path, flags)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                _fail("REGULAR_FILE_REQUIRED", "cli_input")
            with os.fdopen(fd, "rb", closefd=False) as handle:
                raw = handle.read(limit + 1)
            if len(raw) > limit:
                _fail("INPUT_BYTE_LIMIT", "cli_input")
            return raw
        finally:
            os.close(fd)

    try:
        result = diagnose(read(args.input, MAX_INPUT), policy_bytes=read(args.policy, POLICY_LENGTH),
                          adoption_bytes=read(args.adoption, ADOPTION_LENGTH))
    except (OSError, ContractError):
        result = _base_result()
        result["holds"].append({"code": "CLI_INPUT_UNAVAILABLE_OR_REFUSED", "scope": "cli_input"})
    sys.stdout.buffer.write(canonical_bytes(result) + b"\n")
    # NOT_READY applies even when the artificial model succeeds.
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
